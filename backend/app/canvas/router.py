"""Canvas API endpoints for save/load (C1)."""

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.canvas.schemas import CanvasPutBody, CanvasResponse
from app.canvas.service import CanvasService
from app.db.session import get_db_session
from app.dependencies import get_view_spec_service
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
