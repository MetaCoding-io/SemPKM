"""SPARQL API endpoints: query execution, history, saved queries, vocabulary.

Supports GET and POST (both form-encoded and JSON body) per the SPARQL
Protocol standard. Automatically injects common prefixes and scopes
queries to the current state graph to prevent event graph data leakage.

History is auto-saved on POST execution with deduplication and pruning.
Saved queries support full CRUD. Vocabulary returns classes/predicates
from installed Mental Model ontology graphs. POST results are enriched
with label/type/icon metadata for object IRIs.
"""

import hashlib
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.config import settings
from app.db.session import get_db_session
from app.dependencies import get_label_service, get_prefix_registry, get_search_service, get_triplestore_client
from app.services.icons import IconService
from app.services.labels import LabelService
from app.services.prefixes import PrefixRegistry
from app.services.search import SearchService
from app.federation.service import FederationService
from app.sparql.client import check_member_query_safety, inject_prefixes, scope_to_current_graph
from app.sparql.models import PromotedQueryView, SavedSparqlQuery, SharedQueryAccess, SparqlQueryHistory
from app.sparql.schemas import (
    QueryHistoryOut,
    SavedQueryCreate,
    SavedQueryOut,
    SavedQueryUpdate,
    ShareableUserOut,
    SharedQueryOut,
    ShareUpdateRequest,
    VocabularyItem,
    VocabularyOut,
)
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Models directory path -- mirrors the Docker mount used in main.py
_MODELS_DIR = "/app/models"

# Known vocabulary namespace prefixes that should NOT be treated as object IRIs
_VOCAB_PREFIXES = (
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "http://www.w3.org/2000/01/rdf-schema#",
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/2001/XMLSchema#",
    "http://www.w3.org/ns/shacl#",
    "http://www.w3.org/2004/02/skos/core#",
    "http://purl.org/dc/terms/",
    "https://schema.org/",
    "http://xmlns.com/foaf/0.1/",
    "http://www.w3.org/ns/prov#",
    "urn:sempkm:",
)


def _get_icon_service() -> IconService:
    """FastAPI dependency that returns an IconService with the models directory."""
    return IconService(models_dir=_MODELS_DIR)


def _enforce_sparql_role(user: User, query: str, all_graphs: bool) -> None:
    """Check user role permissions for SPARQL query execution.

    Args:
        user: The authenticated user.
        query: The SPARQL query string.
        all_graphs: Whether the user requested cross-graph access.

    Raises:
        HTTPException: 403 if the user's role does not permit the request.
    """
    if user.role == "guest":
        raise HTTPException(status_code=403, detail="SPARQL access denied")
    if user.role == "member":
        if all_graphs:
            raise HTTPException(
                status_code=403,
                detail="Requires owner role for all_graphs",
            )
        check_member_query_safety(query)


async def _resolve_user_shared_graphs(
    user: User, client: TriplestoreClient
) -> list[str] | None:
    """Resolve shared graph IRIs for a user's SPARQL scoping.

    If the user has a published WebID, queries FederationService for the
    list of shared graphs the user is a member of. Returns None on failure
    or if the user has no WebID (graceful fallback -- no shared graphs).

    Args:
        user: The authenticated user.
        client: Triplestore client instance.

    Returns:
        List of shared graph IRI strings, or None if not applicable.
    """
    if not getattr(user, "webid_published", False):
        return None

    try:
        from app.events.store import EventStore

        webid_uri = f"urn:sempkm:user:{user.id}"
        # Use webid_url if available, else fall back to user IRI
        if hasattr(user, "webid_url") and user.webid_url:
            webid_uri = user.webid_url

        service = FederationService(client, EventStore(client))
        graphs = await service.get_user_shared_graphs(webid_uri)
        return graphs if graphs else None
    except Exception:
        logger.warning("Failed to resolve shared graphs for user %s", user.id, exc_info=True)
        return None


async def _execute_sparql(
    query: str,
    client: TriplestoreClient,
    all_graphs: bool = False,
    shared_graphs: list[str] | None = None,
) -> dict | None:
    """Process a SPARQL query: inject prefixes, scope to current graph, execute.

    Args:
        query: Raw SPARQL query string from the user.
        client: Triplestore client for query execution.
        all_graphs: If True, skip current graph scoping (admin/debug).
        shared_graphs: Optional list of shared graph IRIs to include
            in SPARQL FROM clauses so shared graph data is visible.

    Returns:
        Parsed SPARQL JSON results dict on success, or None on error
        (error response is returned directly by the caller).
    """
    if not query or not query.strip():
        return None

    # Apply prefix injection then graph scoping
    processed = inject_prefixes(query)
    processed = scope_to_current_graph(
        processed, all_graphs=all_graphs, shared_graphs=shared_graphs
    )

    logger.debug("Executing SPARQL: %s", processed[:200])

    return await client.query(processed)


async def _save_history(
    db: AsyncSession, user_id: uuid.UUID, query_text: str
) -> None:
    """Auto-save query to history with deduplication and pruning.

    - Dedup: if the most recent entry has the same stripped query, update its timestamp
    - Prune: keep at most 100 entries per user
    """
    stripped = query_text.strip()

    # Check most recent entry for deduplication
    result = await db.execute(
        select(SparqlQueryHistory)
        .where(SparqlQueryHistory.user_id == user_id)
        .order_by(SparqlQueryHistory.executed_at.desc())
        .limit(1)
    )
    most_recent = result.scalar_one_or_none()

    if most_recent and most_recent.query_text.strip() == stripped:
        # Update timestamp instead of inserting duplicate
        most_recent.executed_at = func.now()
    else:
        # Insert new entry
        entry = SparqlQueryHistory(
            user_id=user_id,
            query_text=stripped,
        )
        db.add(entry)
        await db.flush()

        # Prune: delete oldest entries beyond 100
        count_result = await db.execute(
            select(func.count())
            .select_from(SparqlQueryHistory)
            .where(SparqlQueryHistory.user_id == user_id)
        )
        total = count_result.scalar()
        if total and total > 100:
            # Find the 100th most recent executed_at
            cutoff_result = await db.execute(
                select(SparqlQueryHistory.executed_at)
                .where(SparqlQueryHistory.user_id == user_id)
                .order_by(SparqlQueryHistory.executed_at.desc())
                .offset(100)
                .limit(1)
            )
            cutoff_ts = cutoff_result.scalar_one_or_none()
            if cutoff_ts is not None:
                await db.execute(
                    delete(SparqlQueryHistory).where(
                        SparqlQueryHistory.user_id == user_id,
                        SparqlQueryHistory.executed_at <= cutoff_ts,
                    )
                )


def _is_object_iri(iri: str, base_namespace: str) -> bool:
    """Determine if an IRI represents a user data object (not a vocabulary term)."""
    if iri.startswith(base_namespace):
        return True
    # Exclude known vocabulary prefixes
    for vp in _VOCAB_PREFIXES:
        if iri.startswith(vp):
            return False
    return False


async def _enrich_sparql_results(
    raw_results: dict,
    label_service: LabelService,
    icon_service: IconService,
    prefix_registry: PrefixRegistry,
    client: TriplestoreClient,
    base_namespace: str,
) -> dict:
    """Add label/type/icon metadata for object IRIs found in SPARQL results.

    Scans all bindings for URI values, identifies object IRIs (those starting
    with base_namespace), resolves labels, types, and icons, then attaches
    an _enrichment dict to the response.
    """
    # Collect unique object IRIs from results
    object_iris: set[str] = set()
    bindings = raw_results.get("results", {}).get("bindings", [])

    for binding in bindings:
        for var_name, var_val in binding.items():
            if var_val.get("type") == "uri":
                iri = var_val["value"]
                if _is_object_iri(iri, base_namespace):
                    object_iris.add(iri)

    if not object_iris:
        raw_results["_enrichment"] = {}
        return raw_results

    # Resolve labels in batch
    labels = await label_service.resolve_batch(list(object_iris))

    # Resolve types via SPARQL VALUES query
    iri_types: dict[str, str] = {}
    if object_iris:
        values_clause = " ".join(f"<{iri}>" for iri in object_iris)
        type_query = f"""
            SELECT ?s ?type WHERE {{
                VALUES ?s {{ {values_clause} }}
                ?s a ?type .
            }}
        """
        try:
            processed = inject_prefixes(type_query)
            processed = scope_to_current_graph(processed, all_graphs=False)
            type_results = await client.query(processed)
            for b in type_results.get("results", {}).get("bindings", []):
                s = b.get("s", {}).get("value", "")
                t = b.get("type", {}).get("value", "")
                if s and t and s not in iri_types:
                    iri_types[s] = t
        except Exception:
            logger.warning("Failed to resolve types for enrichment", exc_info=True)

    # Build enrichment map
    enrichment: dict[str, dict] = {}
    for iri in object_iris:
        type_iri = iri_types.get(iri, "")
        icon_info = icon_service.get_type_icon(type_iri, "tab") if type_iri else {
            "icon": "circle", "color": "var(--color-text-faint)", "size": None
        }
        enrichment[iri] = {
            "label": labels.get(iri, ""),
            "type_iri": type_iri,
            "icon": icon_info,
            "qname": prefix_registry.compact(iri),
        }

    raw_results["_enrichment"] = enrichment
    return raw_results


# ---------------------------------------------------------------------------
# SPARQL query endpoints
# ---------------------------------------------------------------------------


@router.get("/sparql")
async def sparql_get(
    query: str = Query(..., description="SPARQL query string"),
    all_graphs: bool = Query(False, description="Skip current graph scoping"),
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
) -> Response:
    """Execute a SPARQL query via GET (query as URL parameter).

    Standard SPARQL Protocol GET endpoint. Queries are automatically
    scoped to the current state graph unless all_graphs=true.
    Guests are denied access; members cannot use all_graphs or FROM/GRAPH clauses.

    If the user has a published WebID, shared graph data is also included
    in query results via additional FROM clauses.
    """
    _enforce_sparql_role(user, query, all_graphs)

    if not query or not query.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Empty query"},
        )

    # Resolve user's shared graphs for SPARQL scoping
    user_shared_graphs = await _resolve_user_shared_graphs(user, client)

    try:
        result = await _execute_sparql(
            query, client, all_graphs=all_graphs,
            shared_graphs=user_shared_graphs,
        )
        if result is None:
            return JSONResponse(status_code=400, content={"error": "Empty query"})
        return JSONResponse(
            content=result,
            media_type="application/sparql-results+json",
        )
    except Exception as e:
        error_msg = str(e)
        logger.warning("SPARQL query failed: %s", error_msg)
        if "400" in error_msg or "MalformedQuery" in error_msg:
            return JSONResponse(
                status_code=400,
                content={"error": f"Malformed SPARQL query: {error_msg}"},
            )
        return JSONResponse(
            status_code=502,
            content={"error": f"Triplestore error: {error_msg}"},
        )


@router.post("/sparql")
async def sparql_post(
    request: Request,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    db: AsyncSession = Depends(get_db_session),
    label_service: LabelService = Depends(get_label_service),
    prefix_registry: PrefixRegistry = Depends(get_prefix_registry),
    icon_service: IconService = Depends(_get_icon_service),
) -> Response:
    """Execute a SPARQL query via POST with history and enrichment.

    Accepts two content types:
    - application/x-www-form-urlencoded: Standard SPARQL Protocol (query=...)
    - application/json: Convenience format ({"query": "...", "all_graphs": false})

    On success: saves query to history (with dedup/prune) and enriches
    results with label/type/icon metadata for object IRIs.
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            query = body.get("query", "")
            all_graphs = body.get("all_graphs", False)
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid JSON body"},
            )
    else:
        # Default: form-encoded (application/x-www-form-urlencoded)
        form = await request.form()
        query = form.get("query", "")
        all_graphs = form.get("all_graphs", "false").lower() == "true"

    _enforce_sparql_role(user, query, all_graphs)

    if not query or not query.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Empty query"},
        )

    # Resolve user's shared graphs for SPARQL scoping
    user_shared_graphs = await _resolve_user_shared_graphs(user, client)

    try:
        result = await _execute_sparql(
            query, client, all_graphs=all_graphs,
            shared_graphs=user_shared_graphs,
        )
        if result is None:
            return JSONResponse(status_code=400, content={"error": "Empty query"})

        # Save to history (fire-and-forget -- errors don't affect the response)
        try:
            await _save_history(db, user.id, query)
        except Exception:
            logger.warning("Failed to save SPARQL query history", exc_info=True)

        # Enrich results with labels/types/icons for object IRIs
        try:
            result = await _enrich_sparql_results(
                result, label_service, icon_service, prefix_registry, client,
                settings.base_namespace,
            )
        except Exception:
            logger.warning("Failed to enrich SPARQL results", exc_info=True)

        return JSONResponse(
            content=result,
            media_type="application/sparql-results+json",
        )

    except Exception as e:
        error_msg = str(e)
        logger.warning("SPARQL query failed: %s", error_msg)
        if "400" in error_msg or "MalformedQuery" in error_msg:
            return JSONResponse(
                status_code=400,
                content={"error": f"Malformed SPARQL query: {error_msg}"},
            )
        return JSONResponse(
            status_code=502,
            content={"error": f"Triplestore error: {error_msg}"},
        )


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------


@router.get("/sparql/history")
async def sparql_history_list(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[QueryHistoryOut]:
    """List user's SPARQL query history (most recent first, limit 100).

    Rejects guest users via role check.
    """
    _enforce_sparql_role(user, "", False)
    result = await db.execute(
        select(SparqlQueryHistory)
        .where(SparqlQueryHistory.user_id == user.id)
        .order_by(SparqlQueryHistory.executed_at.desc())
        .limit(100)
    )
    rows = result.scalars().all()
    return [QueryHistoryOut.model_validate(r) for r in rows]


@router.delete("/sparql/history")
async def sparql_history_clear(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Clear all SPARQL query history for the current user."""
    _enforce_sparql_role(user, "", False)
    await db.execute(
        delete(SparqlQueryHistory).where(SparqlQueryHistory.user_id == user.id)
    )
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Saved query endpoints
# ---------------------------------------------------------------------------


@router.get("/sparql/users")
async def list_shareable_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[ShareableUserOut]:
    """List all non-guest users for the share picker."""
    _enforce_sparql_role(user, "", False)
    result = await db.execute(
        select(User).where(User.role != "guest")
    )
    rows = result.scalars().all()
    return [ShareableUserOut.model_validate(r) for r in rows]


@router.get("/sparql/saved")
async def saved_query_list(
    include_shared: bool = Query(False, description="Include queries shared with me"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[SavedQueryOut] | dict:
    """List user's saved SPARQL queries (newest first).

    When include_shared=true, returns a JSON object with two keys:
    my_queries (list[SavedQueryOut]) and shared_with_me (list[SharedQueryOut]).
    When include_shared=false (default), returns list[SavedQueryOut] for backward compat.
    """
    _enforce_sparql_role(user, "", False)

    # Own queries
    result = await db.execute(
        select(SavedSparqlQuery)
        .where(SavedSparqlQuery.user_id == user.id)
        .order_by(SavedSparqlQuery.created_at.desc())
    )
    my_rows = result.scalars().all()
    my_queries = [SavedQueryOut.model_validate(r) for r in my_rows]

    if not include_shared:
        return my_queries

    # Shared with me
    shared_result = await db.execute(
        select(SharedQueryAccess, SavedSparqlQuery, User)
        .join(SavedSparqlQuery, SharedQueryAccess.query_id == SavedSparqlQuery.id)
        .join(User, SavedSparqlQuery.user_id == User.id)
        .where(SharedQueryAccess.shared_with_user_id == user.id)
        .order_by(SavedSparqlQuery.updated_at.desc())
    )
    shared_rows = shared_result.all()
    shared_queries = []
    for access, query, owner in shared_rows:
        is_updated = (
            access.last_viewed_at is None
            or query.updated_at > access.last_viewed_at
        )
        shared_queries.append(SharedQueryOut(
            id=query.id,
            name=query.name,
            description=query.description,
            query_text=query.query_text,
            created_at=query.created_at,
            updated_at=query.updated_at,
            owner_name=owner.display_name or owner.email,
            is_updated=is_updated,
        ))

    return {
        "my_queries": [q.model_dump(mode="json") for q in my_queries],
        "shared_with_me": [q.model_dump(mode="json") for q in shared_queries],
    }


@router.post("/sparql/saved", status_code=201)
async def saved_query_create(
    body: SavedQueryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SavedQueryOut:
    """Create a new saved SPARQL query."""
    _enforce_sparql_role(user, "", False)
    saved = SavedSparqlQuery(
        user_id=user.id,
        name=body.name,
        description=body.description,
        query_text=body.query_text,
    )
    db.add(saved)
    await db.flush()
    await db.refresh(saved)
    return SavedQueryOut.model_validate(saved)


@router.put("/sparql/saved/{query_id}")
async def saved_query_update(
    query_id: uuid.UUID,
    body: SavedQueryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SavedQueryOut:
    """Update a saved SPARQL query. Only updates provided fields."""
    _enforce_sparql_role(user, "", False)
    result = await db.execute(
        select(SavedSparqlQuery).where(
            SavedSparqlQuery.id == query_id,
            SavedSparqlQuery.user_id == user.id,
        )
    )
    saved = result.scalar_one_or_none()
    if saved is None:
        raise HTTPException(status_code=404, detail="Saved query not found")

    if body.name is not None:
        saved.name = body.name
    if body.description is not None:
        saved.description = body.description
    if body.query_text is not None:
        saved.query_text = body.query_text

    await db.flush()
    await db.refresh(saved)
    return SavedQueryOut.model_validate(saved)


@router.delete("/sparql/saved/{query_id}")
async def saved_query_delete(
    query_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Delete a saved SPARQL query. Returns 404 if not found or not owned."""
    _enforce_sparql_role(user, "", False)
    result = await db.execute(
        select(SavedSparqlQuery).where(
            SavedSparqlQuery.id == query_id,
            SavedSparqlQuery.user_id == user.id,
        )
    )
    saved = result.scalar_one_or_none()
    if saved is None:
        raise HTTPException(status_code=404, detail="Saved query not found")

    await db.delete(saved)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Sharing endpoints
# ---------------------------------------------------------------------------


@router.get("/sparql/saved/{query_id}/shares")
async def get_query_shares(
    query_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[uuid.UUID]:
    """List user IDs this query is currently shared with. Owner-only."""
    _enforce_sparql_role(user, "", False)

    # Verify ownership
    result = await db.execute(
        select(SavedSparqlQuery).where(
            SavedSparqlQuery.id == query_id,
            SavedSparqlQuery.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Saved query not found")

    shares_result = await db.execute(
        select(SharedQueryAccess.shared_with_user_id)
        .where(SharedQueryAccess.query_id == query_id)
    )
    return list(shares_result.scalars().all())


@router.put("/sparql/saved/{query_id}/shares")
async def update_query_shares(
    query_id: uuid.UUID,
    body: ShareUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Set sharing for a query. Replaces all current shares. Owner-only."""
    _enforce_sparql_role(user, "", False)

    # Verify ownership
    result = await db.execute(
        select(SavedSparqlQuery).where(
            SavedSparqlQuery.id == query_id,
            SavedSparqlQuery.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Saved query not found")

    # Filter out self-sharing
    target_user_ids = [uid for uid in body.user_ids if uid != user.id]

    # Remove all existing shares
    await db.execute(
        delete(SharedQueryAccess).where(SharedQueryAccess.query_id == query_id)
    )

    # Create new shares
    for uid in target_user_ids:
        db.add(SharedQueryAccess(query_id=query_id, shared_with_user_id=uid))

    await db.flush()
    return Response(status_code=200)


@router.post("/sparql/saved/{query_id}/mark-viewed", status_code=204)
async def mark_shared_query_viewed(
    query_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Mark a shared query as viewed by the current user (clears Updated badge)."""
    _enforce_sparql_role(user, "", False)

    result = await db.execute(
        select(SharedQueryAccess).where(
            SharedQueryAccess.query_id == query_id,
            SharedQueryAccess.shared_with_user_id == user.id,
        )
    )
    access = result.scalar_one_or_none()
    if access is not None:
        access.last_viewed_at = func.now()
        await db.flush()

    return Response(status_code=204)


@router.post("/sparql/saved/{query_id}/fork", status_code=201)
async def fork_shared_query(
    query_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SavedQueryOut:
    """Fork a shared query as the current user's own copy."""
    _enforce_sparql_role(user, "", False)

    # Verify the query is shared with this user
    result = await db.execute(
        select(SharedQueryAccess).where(
            SharedQueryAccess.query_id == query_id,
            SharedQueryAccess.shared_with_user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Shared query not found")

    # Get the original query
    query_result = await db.execute(
        select(SavedSparqlQuery).where(SavedSparqlQuery.id == query_id)
    )
    original = query_result.scalar_one_or_none()
    if original is None:
        raise HTTPException(status_code=404, detail="Original query not found")

    # Create the fork
    forked = SavedSparqlQuery(
        user_id=user.id,
        name=f"Copy of {original.name}",
        description=original.description,
        query_text=original.query_text,
    )
    db.add(forked)
    await db.flush()
    await db.refresh(forked)
    return SavedQueryOut.model_validate(forked)


# ---------------------------------------------------------------------------
# Promotion endpoints
# ---------------------------------------------------------------------------

_VALID_RENDERERS = {"table", "card", "graph"}


@router.post("/sparql/saved/{query_id}/promote", status_code=201)
async def promote_query(
    query_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Promote a saved query to a named view in the nav tree.

    Creates a PromotedQueryView linking the saved query to view metadata.
    Only the query owner can promote. Returns 409 if already promoted.
    """
    _enforce_sparql_role(user, "", False)

    # Verify ownership
    result = await db.execute(
        select(SavedSparqlQuery).where(
            SavedSparqlQuery.id == query_id,
            SavedSparqlQuery.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Saved query not found")

    # Check if already promoted
    existing = await db.execute(
        select(PromotedQueryView).where(PromotedQueryView.query_id == query_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Query is already promoted")

    # Parse body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    display_label = body.get("display_label", "").strip()
    renderer_type = body.get("renderer_type", "table")

    if not display_label:
        raise HTTPException(status_code=400, detail="display_label is required")
    if renderer_type not in _VALID_RENDERERS:
        raise HTTPException(
            status_code=400,
            detail=f"renderer_type must be one of: {', '.join(sorted(_VALID_RENDERERS))}",
        )

    pv = PromotedQueryView(
        query_id=query_id,
        user_id=user.id,
        display_label=display_label,
        renderer_type=renderer_type,
    )
    db.add(pv)
    await db.flush()
    await db.refresh(pv)

    return JSONResponse(
        status_code=201,
        content={
            "id": str(pv.id),
            "spec_iri": f"urn:sempkm:user-view:{pv.id}",
        },
    )


@router.delete("/sparql/saved/{query_id}/promote")
async def demote_query(
    query_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Demote a promoted view back to just a saved query.

    Deletes the PromotedQueryView row. The underlying saved query remains intact.
    Only the query owner can demote.
    """
    _enforce_sparql_role(user, "", False)

    # Verify ownership of the saved query
    sq_result = await db.execute(
        select(SavedSparqlQuery).where(
            SavedSparqlQuery.id == query_id,
            SavedSparqlQuery.user_id == user.id,
        )
    )
    if sq_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Saved query not found")

    result = await db.execute(
        select(PromotedQueryView).where(PromotedQueryView.query_id == query_id)
    )
    pv = result.scalar_one_or_none()
    if pv is None:
        raise HTTPException(status_code=404, detail="Query is not promoted")

    await db.delete(pv)
    return Response(status_code=204)


@router.get("/sparql/saved/{query_id}/promotion")
async def get_promotion_status(
    query_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Check if a saved query is promoted. Owner-only."""
    _enforce_sparql_role(user, "", False)

    # Verify ownership
    sq_result = await db.execute(
        select(SavedSparqlQuery).where(
            SavedSparqlQuery.id == query_id,
            SavedSparqlQuery.user_id == user.id,
        )
    )
    if sq_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Saved query not found")

    result = await db.execute(
        select(PromotedQueryView).where(PromotedQueryView.query_id == query_id)
    )
    pv = result.scalar_one_or_none()

    if pv:
        return JSONResponse(content={
            "promoted": True,
            "view_id": str(pv.id),
            "spec_iri": f"urn:sempkm:user-view:{pv.id}",
            "display_label": pv.display_label,
            "renderer_type": pv.renderer_type,
        })

    return JSONResponse(content={
        "promoted": False,
        "view_id": None,
        "spec_iri": None,
        "display_label": None,
        "renderer_type": None,
    })


# ---------------------------------------------------------------------------
# Vocabulary endpoint
# ---------------------------------------------------------------------------


@router.get("/sparql/vocabulary")
async def get_sparql_vocabulary(
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    prefix_registry: PrefixRegistry = Depends(get_prefix_registry),
    label_service: LabelService = Depends(get_label_service),
) -> VocabularyOut:
    """Return classes, predicates, and prefixes from installed Mental Model ontology graphs.

    Queries all graphs matching urn:sempkm:model:*:ontology for OWL classes
    and properties. Returns compacted QNames with badges and labels.
    """
    _enforce_sparql_role(user, "", False)

    vocab_query = """
        SELECT DISTINCT ?entity ?type ?label WHERE {
            GRAPH ?g {
                ?entity a ?type .
                FILTER(?type IN (
                    <http://www.w3.org/2002/07/owl#Class>,
                    <http://www.w3.org/2002/07/owl#ObjectProperty>,
                    <http://www.w3.org/2002/07/owl#DatatypeProperty>,
                    <http://www.w3.org/2002/07/owl#AnnotationProperty>
                ))
                OPTIONAL { ?entity <http://www.w3.org/2000/01/rdf-schema#label> ?label }
            }
            FILTER(
                STRSTARTS(STR(?g), "urn:sempkm:model:") &&
                STRENDS(STR(?g), ":ontology")
            )
        }
    """

    items: list[VocabularyItem] = []

    try:
        results = await client.query(vocab_query)
        bindings = results.get("results", {}).get("bindings", [])

        # Deduplicate by entity IRI (may appear with multiple labels)
        seen: set[str] = set()
        for b in bindings:
            entity_iri = b.get("entity", {}).get("value", "")
            if not entity_iri or entity_iri in seen:
                continue
            seen.add(entity_iri)

            type_iri = b.get("type", {}).get("value", "")
            label_val = b.get("label", {}).get("value") if "label" in b else None

            # Determine badge
            if "Class" in type_iri:
                badge = "C"
            elif "DatatypeProperty" in type_iri:
                badge = "D"
            else:
                badge = "P"

            qname = prefix_registry.compact(entity_iri)

            items.append(VocabularyItem(
                qname=qname,
                full_iri=entity_iri,
                badge=badge,
                label=label_val,
            ))

    except Exception:
        logger.warning("Failed to fetch vocabulary from ontology graphs", exc_info=True)

    # Sort items by qname for consistent ordering
    items.sort(key=lambda x: x.qname)

    # Model version: hash of sorted entity IRIs for cache-busting
    entity_hash = hashlib.md5(
        "|".join(sorted(i.full_iri for i in items)).encode()
    ).hexdigest()
    model_version = int(entity_hash[:8], 16)

    return VocabularyOut(
        prefixes=prefix_registry.get_all_prefixes(),
        items=items,
        model_version=model_version,
    )


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------


@router.get("/search")
async def search_knowledge_base(
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    fuzzy: bool = Query(False, description="Enable fuzzy (typo-tolerant) matching for tokens >=5 chars"),
    user: User = Depends(get_current_user),
    search_service: SearchService = Depends(get_search_service),
) -> JSONResponse:
    """Full-text keyword search across the current knowledge base.

    Searches all literal values in urn:sempkm:current using LuceneSail.
    Results are ranked by relevance score and include IRI, type, label, and snippet.

    When fuzzy=true, tokens with 5+ characters receive ~1 edit-distance expansion
    for typo tolerance. Short tokens (<5 chars) always use exact match.

    Returns:
        JSON: {"results": [{"iri", "type", "label", "snippet", "score"}], "count": N,
               "query": q, "fuzzy": bool}
    """
    results = await search_service.search(query=q, limit=limit, fuzzy=fuzzy)
    return JSONResponse(content={
        "query": q,
        "fuzzy": fuzzy,
        "count": len(results),
        "results": [
            {
                "iri": r.iri,
                "type": r.type,
                "label": r.label,
                "snippet": r.snippet,
                "score": r.score,
            }
            for r in results
        ],
    })
