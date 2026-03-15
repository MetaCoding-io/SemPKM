"""Dashboard router — rendering and API endpoints for DashboardSpec.

Provides:
- GET /browser/dashboard/new — dashboard builder form (create mode)
- GET /browser/dashboard/{id}/edit — dashboard builder form (edit mode)
- GET /browser/dashboard/{id} — render dashboard page (htmx partial)
- GET /browser/dashboard/{id}/block/{index} — render individual block
- GET /api/dashboard — list user's dashboards (JSON)
- POST /api/dashboard — create dashboard (JSON)
- PATCH /api/dashboard/{id} — update dashboard (JSON)
- DELETE /api/dashboard/{id} — delete dashboard
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dashboard.service import DashboardService, DashboardData
from app.dashboard.models import VALID_LAYOUTS, VALID_BLOCK_TYPES

logger = logging.getLogger(__name__)

browser_router = APIRouter(prefix="/browser/dashboard", tags=["dashboard"])
api_router = APIRouter(prefix="/api/dashboard", tags=["dashboard-api"])


# ---------------------------------------------------------------------------
# Layout definitions — CSS Grid template areas for each layout
# ---------------------------------------------------------------------------

LAYOUT_DEFINITIONS = {
    "single": {
        "css_class": "dashboard-layout-single",
        "slots": ["main"],
        "grid_template": '"main"',
        "columns": "1fr",
    },
    "sidebar-main": {
        "css_class": "dashboard-layout-sidebar-main",
        "slots": ["sidebar", "main"],
        "grid_template": '"sidebar main"',
        "columns": "300px 1fr",
    },
    "grid-2x2": {
        "css_class": "dashboard-layout-grid-2x2",
        "slots": ["top-left", "top-right", "bottom-left", "bottom-right"],
        "grid_template": '"top-left top-right" "bottom-left bottom-right"',
        "columns": "1fr 1fr",
    },
    "grid-3": {
        "css_class": "dashboard-layout-grid-3",
        "slots": ["left", "center", "right"],
        "grid_template": '"left center right"',
        "columns": "1fr 1fr 1fr",
    },
    "top-bottom": {
        "css_class": "dashboard-layout-top-bottom",
        "slots": ["top", "bottom"],
        "grid_template": '"top" "bottom"',
        "columns": "1fr",
    },
}


def _get_dashboard_service(request: Request) -> DashboardService:
    """Get dashboard service from app state."""
    return request.app.state.dashboard_service


# ---------------------------------------------------------------------------
# Browser routes (htmx partials)
# ---------------------------------------------------------------------------


@browser_router.get("/explorer")
async def dashboard_explorer(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Render DASHBOARDS section content for the explorer sidebar."""
    templates = request.app.state.templates
    service = _get_dashboard_service(request)
    dashboards = await service.list_for_user(user.id)
    context = {
        "request": request,
        "dashboards": dashboards,
    }
    return templates.TemplateResponse(
        request, "browser/dashboard_explorer.html", context
    )


@browser_router.get("/new")
async def dashboard_builder_new(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Render dashboard builder form in create mode (empty fields)."""
    templates = request.app.state.templates
    context = {
        "request": request,
        "dashboard": None,
        "layout_definitions": LAYOUT_DEFINITIONS,
        "valid_block_types": sorted(VALID_BLOCK_TYPES),
    }
    return templates.TemplateResponse(
        request, "browser/dashboard_builder.html", context
    )


@browser_router.get("/{dashboard_id}/edit")
async def dashboard_builder_edit(
    request: Request,
    dashboard_id: str,
    user: User = Depends(get_current_user),
):
    """Render dashboard builder form in edit mode (pre-populated fields)."""
    templates = request.app.state.templates
    service = _get_dashboard_service(request)

    try:
        did = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID")

    dashboard = await service.get(did)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    context = {
        "request": request,
        "dashboard": dashboard,
        "layout_definitions": LAYOUT_DEFINITIONS,
        "valid_block_types": sorted(VALID_BLOCK_TYPES),
    }
    return templates.TemplateResponse(
        request, "browser/dashboard_builder.html", context
    )


@browser_router.get("/{dashboard_id}")
async def render_dashboard(
    request: Request,
    dashboard_id: str,
    user: User = Depends(get_current_user),
):
    """Render a dashboard page with CSS Grid layout and lazy-loaded blocks."""
    templates = request.app.state.templates
    service = _get_dashboard_service(request)

    try:
        did = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID")

    dashboard = await service.get(did)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    layout_def = LAYOUT_DEFINITIONS.get(dashboard.layout, LAYOUT_DEFINITIONS["single"])

    # Assign blocks to slots (sequential assignment)
    slots = layout_def["slots"]
    block_slots = []
    for i, block in enumerate(dashboard.blocks):
        slot = block.get("slot") or (slots[i % len(slots)] if slots else "main")
        block_slots.append({
            "index": i,
            "slot": slot,
            "type": block.get("type", "divider"),
            "config": block.get("config", {}),
        })

    context = {
        "request": request,
        "dashboard": dashboard,
        "layout": layout_def,
        "block_slots": block_slots,
        "dashboard_id": dashboard_id,
    }

    return templates.TemplateResponse(
        request, "browser/dashboard_page.html", context
    )


@browser_router.get("/{dashboard_id}/block/{block_index}")
async def render_block(
    request: Request,
    dashboard_id: str,
    block_index: int,
    user: User = Depends(get_current_user),
):
    """Render a single dashboard block by index.

    Block types:
    - view-embed: loads an existing view via htmx include
    - markdown: renders markdown to HTML
    - create-form: renders SHACL form for target class
    - object-embed: renders object detail
    - divider: renders <hr>
    """
    templates = request.app.state.templates
    service = _get_dashboard_service(request)

    try:
        did = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID")

    dashboard = await service.get(did)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    if block_index < 0 or block_index >= len(dashboard.blocks):
        raise HTTPException(status_code=404, detail="Block not found")

    block = dashboard.blocks[block_index]
    block_type = block.get("type", "divider")
    config = block.get("config", {})

    if block_type == "markdown":
        import html
        content = config.get("content", "")
        # Basic markdown-ish rendering: paragraphs + HTML escaping
        escaped = html.escape(content)
        paragraphs = escaped.split("\n\n")
        html_content = "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs if p.strip())
        return HTMLResponse(
            f'<div class="dashboard-block dashboard-block-markdown">{html_content}</div>'
        )

    elif block_type == "view-embed":
        spec_iri = config.get("spec_iri", "")
        renderer = config.get("renderer_type", "table")
        height = config.get("height", "400px")
        if not spec_iri:
            return HTMLResponse('<div class="dashboard-block dashboard-block-error">No view spec configured</div>')
        # Render the view inline via htmx
        view_url = f"/browser/views/{renderer}/{spec_iri}"
        return HTMLResponse(
            f'<div class="dashboard-block dashboard-block-view" style="height:{height};overflow:auto"'
            f' hx-get="{view_url}" hx-trigger="load" hx-swap="innerHTML">'
            f'<div class="dashboard-block-loading">Loading view...</div></div>'
        )

    elif block_type == "create-form":
        target_class = config.get("target_class", "")
        if not target_class:
            return HTMLResponse('<div class="dashboard-block dashboard-block-error">No target class configured</div>')
        form_url = f"/browser/objects/create-form?type_iri={target_class}"
        return HTMLResponse(
            f'<div class="dashboard-block dashboard-block-form"'
            f' hx-get="{form_url}" hx-trigger="load" hx-swap="innerHTML">'
            f'<div class="dashboard-block-loading">Loading form...</div></div>'
        )

    elif block_type == "object-embed":
        object_iri = config.get("object_iri", "")
        mode = config.get("mode", "read")
        if not object_iri:
            return HTMLResponse('<div class="dashboard-block dashboard-block-error">No object configured</div>')
        obj_url = f"/browser/objects/{object_iri}"
        return HTMLResponse(
            f'<div class="dashboard-block dashboard-block-object"'
            f' hx-get="{obj_url}" hx-trigger="load" hx-swap="innerHTML">'
            f'<div class="dashboard-block-loading">Loading object...</div></div>'
        )

    elif block_type == "divider":
        return HTMLResponse('<hr class="dashboard-block dashboard-block-divider">')

    elif block_type == "sparql-result":
        query = config.get("query", "")
        label = config.get("label", "Result")
        if not query:
            return HTMLResponse('<div class="dashboard-block dashboard-block-error">No query configured</div>')
        return HTMLResponse(
            f'<div class="dashboard-block dashboard-block-sparql">'
            f'<span class="dashboard-sparql-label">{label}</span>'
            f'<span class="dashboard-sparql-value" data-query="{query}">...</span></div>'
        )

    return HTMLResponse('<div class="dashboard-block dashboard-block-error">Unknown block type</div>')


# ---------------------------------------------------------------------------
# API routes (JSON)
# ---------------------------------------------------------------------------


@api_router.get("")
async def list_dashboards(
    user: User = Depends(get_current_user),
    service: DashboardService = Depends(_get_dashboard_service),
):
    """List all dashboards for the current user."""
    dashboards = await service.list_for_user(user.id)
    return JSONResponse(content=[
        {"id": d.id, "name": d.name, "description": d.description, "layout": d.layout}
        for d in dashboards
    ])


@api_router.post("")
async def create_dashboard(
    request: Request,
    user: User = Depends(get_current_user),
    service: DashboardService = Depends(_get_dashboard_service),
):
    """Create a new dashboard."""
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    try:
        dashboard = await service.create(
            user_id=user.id,
            name=name,
            layout=body.get("layout", "single"),
            blocks=body.get("blocks", []),
            description=body.get("description", ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(
        content={"id": dashboard.id, "name": dashboard.name},
        status_code=201,
    )


@api_router.patch("/{dashboard_id}")
async def update_dashboard(
    request: Request,
    dashboard_id: str,
    user: User = Depends(get_current_user),
    service: DashboardService = Depends(_get_dashboard_service),
):
    """Update a dashboard."""
    try:
        did = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID")

    body = await request.json()
    updates = {}
    if "name" in body:
        updates["name"] = body["name"]
    if "description" in body:
        updates["description"] = body["description"]
    if "layout" in body:
        updates["layout"] = body["layout"]
    if "blocks" in body:
        updates["blocks"] = body["blocks"]

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    try:
        result = await service.update(did, user.id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    return JSONResponse(content={"id": result.id, "name": result.name})


@api_router.delete("/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: str,
    user: User = Depends(get_current_user),
    service: DashboardService = Depends(_get_dashboard_service),
):
    """Delete a dashboard."""
    try:
        did = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID")

    deleted = await service.delete(did, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    return JSONResponse(content={"deleted": True})
