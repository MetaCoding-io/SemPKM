"""Canvas API endpoints for save/load (C1)."""

import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.canvas.schemas import (
    BatchEdge,
    BatchEdgesRequest,
    BatchEdgesResponse,
    CanvasPutBody,
    CanvasResponse,
    SessionCreateBody,
    SessionListResponse,
    WikilinkResolveRequest,
    WikilinkResolveResponse,
)
from app.canvas.service import CanvasService
from app.db.session import get_db_session
from app.dependencies import (
    get_label_service,
    get_shapes_service,
    get_triplestore_client,
    get_view_spec_service,
)
from app.services.labels import LabelService
from app.services.shapes import NodeShapeForm, PropertyShape, ShapesService
from app.triplestore.client import TriplestoreClient
from app.views.service import ViewSpecService
from app.rdf.namespaces import CURRENT_GRAPH

logger = logging.getLogger(__name__)

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
      GRAPH <{CURRENT_GRAPH}> {{
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
# Property building (pure-function helper, unit-testable)
# ------------------------------------------------------------------

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
SEMPKM_BODY = "urn:sempkm:body"

# Well-known predicates excluded from unmatched output
_SKIP_PREDICATES = {RDF_TYPE, SEMPKM_BODY}


def _local_name(iri: str) -> str:
    """Extract local name from an IRI (fragment or last path segment)."""
    if "#" in iri:
        return iri.rsplit("#", 1)[-1]
    if "/" in iri:
        return iri.rsplit("/", 1)[-1]
    return iri


def _is_body_property(prop: PropertyShape) -> bool:
    """Check if a SHACL property represents a body field."""
    return bool(prop.name and prop.name.lower() == "body")


def build_property_list(
    bindings: list[dict],
    inferred_bindings: list[dict],
    form: NodeShapeForm | None,
    labels: dict[str, str],
) -> list[dict]:
    """Build the property list from SPARQL bindings, SHACL form, and resolved labels.

    This is a pure function — all I/O (SPARQL queries, label resolution) happens
    in the calling endpoint. This function only transforms data.

    Args:
        bindings: SPARQL results from urn:sempkm:current graph
        inferred_bindings: SPARQL results from urn:sempkm:inferred graph
        form: SHACL NodeShapeForm (or None if no type matched)
        labels: Pre-resolved IRI→label mapping for reference values

    Returns:
        List of property dicts with name, path, values, datatype, source keys.
    """
    # --- Parse current-graph bindings ---
    values: dict[str, list[dict]] = {}
    type_iris: list[str] = []
    matched_predicates: set[str] = set()

    for b in bindings:
        pred = b["p"]["value"]
        obj = b["o"]
        obj_val = obj["value"]
        obj_type = obj.get("type", "literal")

        if pred == RDF_TYPE:
            type_iris.append(obj_val)
            continue
        if pred == SEMPKM_BODY:
            continue

        entry = {"value": obj_val}
        if obj_type == "uri":
            ref_label = labels.get(obj_val)
            if ref_label:
                entry["ref_label"] = ref_label
        values.setdefault(pred, []).append(entry)

    # --- Parse inferred-graph bindings (deduplicate against current) ---
    inferred_values: dict[str, list[dict]] = {}
    current_triples = set()
    for pred, val_list in values.items():
        for v in val_list:
            current_triples.add((pred, v["value"]))

    for b in inferred_bindings:
        pred = b["p"]["value"]
        obj = b["o"]
        obj_val = obj["value"]
        obj_type = obj.get("type", "literal")

        if pred == RDF_TYPE or pred == SEMPKM_BODY:
            continue
        if (pred, obj_val) in current_triples:
            continue

        entry = {"value": obj_val}
        if obj_type == "uri":
            ref_label = labels.get(obj_val)
            if ref_label:
                entry["ref_label"] = ref_label
        inferred_values.setdefault(pred, []).append(entry)

    # --- Build properties from SHACL form (ordered by sh:order) ---
    properties: list[dict] = []

    if form:
        for prop in form.properties:
            if _is_body_property(prop):
                matched_predicates.add(prop.path)
                continue
            prop_vals = values.get(prop.path, [])
            if not prop_vals:
                continue
            matched_predicates.add(prop.path)
            properties.append({
                "name": prop.name,
                "path": prop.path,
                "values": prop_vals,
                "datatype": prop.datatype,
                "source": "current",
            })

    # --- Unmatched current predicates (in graph but not in SHACL form) ---
    for pred, val_list in values.items():
        if pred in matched_predicates or pred in _SKIP_PREDICATES:
            continue
        properties.append({
            "name": _local_name(pred),
            "path": pred,
            "values": val_list,
            "datatype": None,
            "source": "current",
        })

    # --- Inferred properties ---
    for pred, val_list in inferred_values.items():
        if pred in matched_predicates or pred in _SKIP_PREDICATES:
            continue
        properties.append({
            "name": _local_name(pred),
            "path": pred,
            "values": val_list,
            "datatype": None,
            "source": "inferred",
        })

    return properties


@router.get("/properties")
async def get_node_properties(
    iri: str = Query(..., description="Object IRI"),
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    shapes_service: ShapesService = Depends(get_shapes_service),
    label_service: LabelService = Depends(get_label_service),
):
    """Return SHACL-derived property data for an object node."""
    if not _is_valid_iri(iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    # --- Query current graph ---
    current_sparql = f"""
    SELECT ?p ?o WHERE {{
      GRAPH <{CURRENT_GRAPH}> {{
        <{iri}> ?p ?o .
      }}
    }}
    """
    try:
        result = await client.query(current_sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("Failed to query properties for %s", iri, exc_info=True)
        bindings = []

    # --- Query inferred graph ---
    inferred_sparql = f"""
    SELECT ?p ?o WHERE {{
      GRAPH <urn:sempkm:inferred> {{
        <{iri}> ?p ?o .
      }}
    }}
    """
    try:
        inf_result = await client.query(inferred_sparql)
        inferred_bindings = inf_result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning(
            "Failed to query inferred properties for %s", iri, exc_info=True
        )
        inferred_bindings = []

    # --- Extract type IRIs and resolve SHACL form ---
    type_iris: list[str] = []
    for b in bindings:
        if b["p"]["value"] == RDF_TYPE:
            type_iris.append(b["o"]["value"])

    form: NodeShapeForm | None = None
    if type_iris:
        for type_iri in type_iris:
            form = await shapes_service.get_form_for_type(type_iri)
            if form:
                break

    # --- Resolve type label ---
    type_label: str | None = None
    if type_iris:
        type_labels = await label_service.resolve_batch(type_iris)
        for t_iri in type_iris:
            if t_iri in type_labels:
                type_label = type_labels[t_iri]
                break

    # --- Collect all IRI values for label resolution ---
    all_iri_values: list[str] = []
    for b in bindings + inferred_bindings:
        if b["o"].get("type") == "uri" and b["p"]["value"] != RDF_TYPE:
            all_iri_values.append(b["o"]["value"])

    ref_labels: dict[str, str] = {}
    if all_iri_values:
        ref_labels = await label_service.resolve_batch(all_iri_values)

    # --- Build property list ---
    properties = build_property_list(bindings, inferred_bindings, form, ref_labels)

    return {"type_label": type_label, "properties": properties}


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
# Wiki-link resolution
# ------------------------------------------------------------------


@router.post("/resolve-wikilinks", response_model=WikilinkResolveResponse)
async def resolve_wikilinks(
    body: WikilinkResolveRequest,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Resolve wiki-link title text to object IRIs via label matching."""
    if not body.titles:
        return WikilinkResolveResponse(resolved={})

    # Build SPARQL string literals for each title (properly escaped)
    escaped_titles = []
    for title in body.titles:
        safe = title.replace("\\", "\\\\").replace('"', '\\"')
        escaped_titles.append(f'"{safe}"')
    titles_list = ", ".join(escaped_titles)

    sparql = f"""
    SELECT ?title ?iri WHERE {{
      GRAPH <{CURRENT_GRAPH}> {{
        ?iri ?labelProp ?title .
        VALUES ?labelProp {{
          <http://purl.org/dc/terms/title>
          <http://www.w3.org/2000/01/rdf-schema#label>
          <http://www.w3.org/2004/02/skos/core#prefLabel>
          <https://schema.org/name>
          <http://xmlns.com/foaf/0.1/name>
        }}
      }}
      FILTER(?title IN ({titles_list}))
    }}
    """

    resolved: dict[str, str | None] = {t: None for t in body.titles}

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        for binding in bindings:
            title_val = binding.get("title", {}).get("value", "")
            iri_val = binding.get("iri", {}).get("value", "")
            # First match wins (don't overwrite if already resolved)
            if title_val in resolved and resolved[title_val] is None and iri_val:
                resolved[title_val] = iri_val
    except Exception:
        pass  # Return what we have (all None if query failed)

    return WikilinkResolveResponse(resolved=resolved)


# ------------------------------------------------------------------
# Batch edge discovery
# ------------------------------------------------------------------


@router.post("/batch-edges", response_model=BatchEdgesResponse)
async def batch_edges(
    body: BatchEdgesRequest,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Find all RDF edges between a given set of IRIs."""
    # Validate IRIs and build SPARQL VALUES entries
    valid_iris = [iri for iri in body.iris if _is_valid_iri(iri)]
    if not valid_iris:
        return BatchEdgesResponse(edges=[])

    values_clause = " ".join(f"<{iri}>" for iri in valid_iris)

    sparql = f"""
    SELECT DISTINCT ?s ?p ?o ?plabel WHERE {{
      {{
        GRAPH <{CURRENT_GRAPH}> {{
          ?s ?p ?o .
          FILTER(isIRI(?o))
        }}
      }}
      UNION
      {{
        GRAPH <urn:sempkm:inferred> {{
          ?s ?p ?o .
          FILTER(isIRI(?o))
        }}
      }}
      VALUES ?s {{ {values_clause} }}
      VALUES ?o {{ {values_clause} }}
      OPTIONAL {{
        GRAPH <{CURRENT_GRAPH}> {{
          ?p <http://www.w3.org/2000/01/rdf-schema#label> ?plabel .
        }}
      }}
    }}
    """

    seen: set[tuple[str, str, str]] = set()
    edges: list[BatchEdge] = []

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        for binding in bindings:
            s = binding.get("s", {}).get("value", "")
            p = binding.get("p", {}).get("value", "")
            o = binding.get("o", {}).get("value", "")
            key = (s, p, o)
            if key in seen:
                continue
            seen.add(key)

            plabel = binding.get("plabel", {}).get("value", "")
            if not plabel:
                # Fallback: extract local name from predicate IRI
                if "#" in p:
                    plabel = p.rsplit("#", 1)[-1]
                elif "/" in p:
                    plabel = p.rsplit("/", 1)[-1]
                else:
                    plabel = p

            edges.append(
                BatchEdge(
                    source=s,
                    target=o,
                    predicate=p,
                    predicate_label=plabel,
                )
            )
    except Exception:
        pass  # Return whatever we collected

    return BatchEdgesResponse(edges=edges)


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
