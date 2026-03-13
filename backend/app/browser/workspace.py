"""Workspace sub-router — layout, navigation tree, icons, and views."""

import logging
from typing import Callable
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.session import get_db_session
from app.dependencies import (
    get_label_service,
    get_shapes_service,
    get_view_spec_service,
)
from app.services.icons import IconService
from app.services.labels import LabelService
from app.services.shapes import ShapesService
from app.views.service import ViewSpecService

from ._helpers import _is_htmx_request, _validate_iri, get_icon_service

logger = logging.getLogger(__name__)

workspace_router = APIRouter(tags=["workspace"])


# ---------------------------------------------------------------------------
# Explorer mode handlers
# ---------------------------------------------------------------------------

async def _handle_by_type(
    request: Request,
    shapes_service: ShapesService,
    icon_svc: IconService,
) -> HTMLResponse:
    """Render the nav tree grouped by RDF type (default explorer mode)."""
    templates = request.app.state.templates
    types = await shapes_service.get_types()
    type_icons = icon_svc.get_icon_map(context="tree")

    return templates.TemplateResponse(
        request,
        "browser/nav_tree.html",
        {"request": request, "types": types, "type_icons": type_icons},
    )


async def _handle_hierarchy(request: Request, **_kwargs) -> HTMLResponse:
    """Placeholder for hierarchy explorer mode."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/explorer_placeholder.html",
        {
            "request": request,
            "mode_label": "Hierarchy",
            "icon_name": "compass",
        },
    )


async def _handle_by_tag(request: Request, **_kwargs) -> HTMLResponse:
    """Placeholder for by-tag explorer mode."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/explorer_placeholder.html",
        {
            "request": request,
            "mode_label": "Tag",
            "icon_name": "tag",
        },
    )


EXPLORER_MODES: dict[str, Callable] = {
    "by-type": _handle_by_type,
    "hierarchy": _handle_hierarchy,
    "by-tag": _handle_by_tag,
}


@workspace_router.get("/icons")
async def icons_data(
    request: Request,
    user: User = Depends(get_current_user),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return icon map for all contexts as JSON for client-side caching."""
    return JSONResponse(content={
        "tree": icon_svc.get_icon_map("tree"),
        "tab": icon_svc.get_icon_map("tab"),
        "graph": icon_svc.get_icon_map("graph"),
    })


@workspace_router.get("/")
async def workspace(
    request: Request,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Render the IDE-style workspace with three-column layout.

    Queries available object types from ShapesService for the navigation
    tree. Full page for direct navigation, content block only for htmx.
    """
    templates = request.app.state.templates
    types = await shapes_service.get_types()
    type_icons = icon_svc.get_icon_map(context="tree")
    from app.config import settings

    context = {
        "request": request,
        "types": types,
        "type_icons": type_icons,
        "active_page": "browser",
        "user": user,
        "base_namespace": settings.base_namespace,
    }

    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "browser/workspace.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "browser/workspace.html", context)


@workspace_router.get("/nav-tree")
async def nav_tree(
    request: Request,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return the nav tree partial (type nodes only, collapsed).

    Used by refreshNavTree() in workspace.js to reload the OBJECTS section.
    Delegates to the by-type handler for consistency.
    """
    return await _handle_by_type(request, shapes_service, icon_svc)


@workspace_router.get("/explorer/tree")
async def explorer_tree(
    request: Request,
    mode: str = "by-type",
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return explorer tree content for the requested mode.

    Dispatches to the appropriate handler from EXPLORER_MODES.
    Returns 400 for unknown modes.
    """
    handler = EXPLORER_MODES.get(mode)
    if handler is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown explorer mode: {mode}",
        )

    logger.debug("Explorer tree requested: mode=%s", mode)
    return await handler(
        request=request,
        shapes_service=shapes_service,
        icon_svc=icon_svc,
    )


@workspace_router.get("/tree/{type_iri:path}")
async def tree_children(
    request: Request,
    type_iri: str,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    label_service: LabelService = Depends(get_label_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Load objects of a given type for the navigation tree.

    Queries the current graph for instances of the specified type,
    resolves labels via LabelService, and returns tree leaf nodes
    as an htmx partial.
    """
    templates = request.app.state.templates
    client = request.app.state.triplestore_client
    decoded_iri = unquote(type_iri)
    if not _validate_iri(decoded_iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    sparql = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?obj WHERE {{
      GRAPH <urn:sempkm:current> {{
        ?obj rdf:type <{decoded_iri}> .
      }}
    }}
    """

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("Failed to query objects for type %s", decoded_iri, exc_info=True)
        bindings = []

    obj_iris = [b["obj"]["value"] for b in bindings]
    labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}

    objects = [
        {"iri": iri, "label": labels.get(iri, iri)}
        for iri in obj_iris
    ]

    type_icon = icon_svc.get_type_icon(decoded_iri, context="tree")

    # Resolve type label for nav tree tooltip (phase 19-02)
    type_labels = await label_service.resolve_batch([decoded_iri])
    type_label = type_labels.get(decoded_iri, "")

    context = {"request": request, "objects": objects, "type_icon": type_icon, "type_label": type_label}
    return templates.TemplateResponse(
        request, "browser/tree_children.html", context
    )


@workspace_router.get("/my-views")
async def my_views(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    view_spec_service: ViewSpecService = Depends(get_view_spec_service),
):
    """Return promoted view entries for the 'My Views' nav tree section.

    Renders browser/my_views.html with the user's promoted ViewSpecs
    including query_id for the demote action.
    """
    templates = request.app.state.templates

    specs = await view_spec_service.get_user_promoted_view_specs(user.id, db)

    if not specs:
        return HTMLResponse(
            content='<div class="tree-empty">No promoted views yet</div>'
        )

    # Also fetch query_ids for demote buttons by querying PromotedQueryView
    from sqlalchemy import select as sa_select

    from app.sparql.models import PromotedQueryView

    pv_result = await db.execute(
        sa_select(PromotedQueryView)
        .where(PromotedQueryView.user_id == user.id)
    )
    pv_rows = pv_result.scalars().all()
    # Map spec_iri -> query_id for the template
    query_id_map = {
        f"urn:sempkm:user-view:{pv.id}": str(pv.query_id) for pv in pv_rows
    }

    context = {
        "request": request,
        "specs": specs,
        "query_id_map": query_id_map,
    }
    return templates.TemplateResponse(
        request, "browser/my_views.html", context
    )
