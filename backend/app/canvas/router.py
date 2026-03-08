"""Canvas API endpoints for save/load (C1)."""

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.canvas.schemas import (
    CanvasPutBody,
    CanvasResponse,
    SessionCreateBody,
    SessionListResponse,
)
from app.canvas.service import CanvasService
from app.db.session import get_db_session
from app.dependencies import get_triplestore_client, get_view_spec_service
from app.triplestore.client import TriplestoreClient
from app.views.service import ViewSpecService

router = APIRouter(prefix="/api/canvas", tags=["canvas"])


def _is_valid_iri(value: str) -> bool:
    """Validate a basic IRI shape before SPARQL interpolation."""
    if not value:
        return False
    parsed = urlparse(value)
    if not parsed.scheme:
        return False
    if any(ch in value for ch in '<>"\n\r\t '):
        return False
    if parsed.scheme in ("http", "https"):
        return bool(parsed.netloc)
    if parsed.scheme == "urn":
        return bool(parsed.path)
    return False


def get_canvas_service() -> CanvasService:
    """FastAPI dependency returning a CanvasService instance."""
    return CanvasService()


@router.get("/subgraph")
async def get_canvas_subgraph(
    root_uri: str = Query(..., description="Root resource URI"),
    depth: int = Query(1, ge=1, le=2),
    user: User = Depends(get_current_user),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
):
    """Return a neighborhood subgraph for canvas expansion."""
    if not _is_valid_iri(root_uri):
        raise HTTPException(status_code=400, detail="Invalid root_uri")

    frontier = {root_uri}
    expanded: set[str] = set()
    seen_nodes: dict[str, dict] = {}
    seen_edges: dict[tuple[str, str, str], str] = {}

    for _ in range(depth):
        if not frontier:
            break

        next_frontier: set[str] = set()
        for iri in frontier:
            if iri in expanded:
                continue
            expanded.add(iri)

            result = await view_spec_service.expand_neighbors(iri)
            for node in result.get("nodes", []):
                node_id = node.get("id")
                if node_id and node_id not in seen_nodes:
                    seen_nodes[node_id] = node
                if node_id and node_id not in expanded:
                    next_frontier.add(node_id)
            for edge in result.get("edges", []):
                source = edge.get("source", "")
                target = edge.get("target", "")
                predicate = edge.get("predicate", "")
                key = (source, target, predicate)
                if source and target and key not in seen_edges:
                    seen_edges[key] = edge.get("predicate_label") or predicate

        frontier = next_frontier

    edges_out = [
        {
            "source": s,
            "target": t,
            "predicate": p,
            "predicate_label": label,
        }
        for ((s, t, p), label) in seen_edges.items()
    ]

    return {
        "root_uri": root_uri,
        "depth": depth,
        "nodes": list(seen_nodes.values()),
        "edges": edges_out,
    }


@router.get("/body")
async def get_node_body(
    iri: str = Query(..., description="Object IRI"),
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Return the urn:sempkm:body text for a given object IRI."""
    if not _is_valid_iri(iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    sparql = f"""
    SELECT ?body WHERE {{
      GRAPH <urn:sempkm:current> {{
        <{iri}> ?p ?body .
        FILTER(STRENDS(STR(?p), ":body") || STR(?p) = "urn:sempkm:body")
      }}
    }} LIMIT 1
    """
    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        body = bindings[0]["body"]["value"] if bindings else ""
    except Exception:
        body = ""

    return {"iri": iri, "body": body}


# ------------------------------------------------------------------
# Session management endpoints (MUST be before /{canvas_id} routes)
# ------------------------------------------------------------------


@router.get("/sessions/list", response_model=SessionListResponse)
async def list_canvas_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    service: CanvasService = Depends(get_canvas_service),
):
    """List all saved canvas sessions, with one-time migration of default canvas."""
    await service.migrate_default_canvas(user.id, db)
    sessions = await service.list_sessions(user.id, db)
    active = await service.get_active_session_id(user.id, db)
    return SessionListResponse(sessions=sessions, active_session_id=active)


@router.post("/sessions")
async def create_canvas_session(
    body: SessionCreateBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    service: CanvasService = Depends(get_canvas_service),
):
    """Create a new named canvas session."""
    session_id = await service.save_session_as(user.id, body.name, body.document, db)
    return {"session_id": session_id, "name": body.name}


@router.delete("/sessions/{session_id}")
async def delete_canvas_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    service: CanvasService = Depends(get_canvas_service),
):
    """Delete a saved canvas session."""
    deleted = await service.delete_session(user.id, session_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}


@router.put("/sessions/{session_id}/activate")
async def activate_canvas_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    service: CanvasService = Depends(get_canvas_service),
):
    """Set a session as the active canvas session."""
    await service.set_active_session(user.id, session_id, db)
    return {"active_session_id": session_id}


# ------------------------------------------------------------------
# Canvas document endpoints
# ------------------------------------------------------------------


@router.get("/{canvas_id}", response_model=CanvasResponse)
async def get_canvas_document(
    canvas_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    service: CanvasService = Depends(get_canvas_service),
):
    """Load a user-scoped canvas document by canvas_id."""
    document, updated_at = await service.load_document(user.id, canvas_id, db)
    return CanvasResponse(canvas_id=canvas_id, document=document, updated_at=updated_at)


@router.put("/{canvas_id}", response_model=CanvasResponse)
async def put_canvas_document(
    canvas_id: str,
    body: CanvasPutBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    service: CanvasService = Depends(get_canvas_service),
):
    """Save a user-scoped canvas document by canvas_id."""
    updated_at = await service.save_document(user.id, canvas_id, body.document, db)
    return CanvasResponse(canvas_id=canvas_id, document=body.document, updated_at=updated_at)
