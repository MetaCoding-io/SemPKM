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
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dashboard.service import DashboardService, DashboardData
from app.dashboard.models import VALID_LAYOUTS, VALID_BLOCK_TYPES
from app.dashboard.registry import BLOCK_REGISTRY
from app.dashboard.migration import migrate_layout_to_gridstack

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
    "gridstack": {
        "css_class": "dashboard-layout-gridstack",
        "slots": ["canvas"],
        "grid_template": '"canvas"',
        "columns": "1fr",
    },
}


def _get_dashboard_service(request: Request) -> DashboardService:
    """Get dashboard service from app state."""
    return request.app.state.dashboard_service


def _block_types_for_template() -> list[dict]:
    """Serialize BlockRegistry specs into dicts for the builder template."""
    result = []
    for spec in BLOCK_REGISTRY.all_specs():
        result.append({
            "type_name": spec.type_name,
            "label": spec.label,
            "icon": spec.icon,
            "category": spec.category,
            "default_w": spec.default_w,
            "default_h": spec.default_h,
            "config_schema": {k: v.__name__ for k, v in spec.config_schema.items()},
        })
    return result


def _block_types_by_category() -> dict[str, list[dict]]:
    """Group block-type dicts by category for the builder palette."""
    cats: dict[str, list[dict]] = {}
    for bt in _block_types_for_template():
        cats.setdefault(bt["category"], []).append(bt)
    return cats


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
        "block_types": _block_types_for_template(),
        "block_categories": _block_types_by_category(),
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
        "block_types": _block_types_for_template(),
        "block_categories": _block_types_by_category(),
    }
    return templates.TemplateResponse(
        request, "browser/dashboard_builder.html", context
    )


@browser_router.get("/{dashboard_id}")
async def render_dashboard(
    request: Request,
    dashboard_id: str,
    embed: int = Query(default=0),
    user: User = Depends(get_current_user),
):
    """Render a dashboard page with GridStack layout and lazy-loaded blocks.

    If the dashboard uses a legacy CSS Grid layout, it is auto-migrated to
    GridStack positions on first access and the result is persisted.
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

    # --- Auto-migrate legacy layouts to GridStack on first access ----------
    blocks = dashboard.blocks
    if dashboard.layout != "gridstack":
        old_layout = dashboard.layout
        blocks = migrate_layout_to_gridstack(old_layout, blocks)
        logger.info(
            "Auto-migrated dashboard %s from layout '%s' to gridstack",
            dashboard.id, old_layout,
        )
        # Persist the migrated layout so future loads skip migration
        await service.update(
            did, user.id,
            layout="gridstack",
            blocks=blocks,
        )

    # Build flat block list with index + position for the template
    template_blocks = []
    for i, block in enumerate(blocks):
        template_blocks.append({
            "index": i,
            "type": block.get("type", "divider"),
            "config": block.get("config", {}),
            "x": block.get("x", 0),
            "y": block.get("y", 0),
            "w": block.get("w", 6),
            "h": block.get("h", 4),
        })

    context = {
        "request": request,
        "dashboard": dashboard,
        "blocks": template_blocks,
        "dashboard_id": dashboard_id,
    }

    if embed:
        fragment_html = templates.env.get_template(
            "browser/dashboard_page.html"
        ).render(context)
        wrapper_context = {"request": request, "content": fragment_html}
        response = templates.TemplateResponse(
            request, "browser/embed_wrapper.html", wrapper_context
        )
        response.headers["X-Embed-Mode"] = "1"
        return response

    return templates.TemplateResponse(
        request, "browser/dashboard_page.html", context
    )


@browser_router.get("/{dashboard_id}/block/{block_index}")
async def render_block(
    request: Request,
    dashboard_id: str,
    block_index: int,
    context_iri: str = Query(default=""),
    context_var: str = Query(default=""),
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
        content = config.get("content", "")
        return HTMLResponse(
            f'<div class="dashboard-block dashboard-block-markdown" data-md-block>'
            f'<script type="text/plain" class="md-source">{content}</script>'
            f'<div class="md-rendered">Loading\u2026</div></div>'
        )

    elif block_type == "view-embed":
        spec_iri = config.get("spec_iri", "")
        renderer = config.get("renderer_type", "table")
        height = config.get("height", "400px")
        emits_context = config.get("emits_context", False)
        listens_to_context = config.get("listens_to_context", "")
        if not spec_iri:
            return HTMLResponse('<div class="dashboard-block dashboard-block-error">No view spec configured</div>')
        # Render the view inline via htmx, with dashboard_mode=1
        view_url = f"/browser/views/{renderer}/{spec_iri}?dashboard_mode=1"
        # Forward context params from the slot re-fetch into the view URL
        if context_iri and listens_to_context:
            view_url += f"&context_iri={quote(context_iri, safe='')}&context_var={quote(listens_to_context, safe='')}"
        # Build data attributes for cross-view context
        data_attrs = ""
        if emits_context:
            data_attrs += ' data-emits-context="1"'
        if listens_to_context:
            data_attrs += f' data-listens-to-context="{listens_to_context}"'
            data_attrs += f' data-dashboard-id="{dashboard_id}"'
        return HTMLResponse(
            f'<div class="dashboard-block dashboard-block-view" style="height:{height};overflow:auto"'
            f'{data_attrs}'
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
        import html as html_mod
        query = config.get("query", "")
        label = config.get("label", "Result")
        if not query:
            return HTMLResponse('<div class="dashboard-block dashboard-block-error">No query configured</div>')
        escaped_query = html_mod.escape(query, quote=True)
        escaped_label = html_mod.escape(label)
        return HTMLResponse(
            f'<div class="dashboard-block dashboard-block-sparql"'
            f' data-sparql-query="{escaped_query}" data-sparql-table>'
            f'<span class="dashboard-sparql-label">{escaped_label}</span>'
            f'<div class="sparql-table-container"></div></div>'
        )

    elif block_type == "stat-card":
        import html as html_mod
        query = config.get("query", "")
        label = config.get("label", "")
        icon = config.get("icon", "hash")
        color = config.get("color", "")
        if not query:
            return HTMLResponse('<div class="dashboard-block dashboard-block-error">No query configured</div>')
        escaped_query = html_mod.escape(query, quote=True)
        escaped_label = html_mod.escape(label)
        escaped_icon = html_mod.escape(icon)
        color_style = f' style="color:{html_mod.escape(color)}"' if color else ""
        return HTMLResponse(
            f'<div class="dashboard-block dashboard-block-stat-card"'
            f' data-sparql-query="{escaped_query}">'
            f'<span class="stat-card-icon"><i data-lucide="{escaped_icon}"></i></span>'
            f'<span class="stat-card-label">{escaped_label}</span>'
            f'<span class="stat-card-value" data-stat-target{color_style}>\u2026</span>'
            f'</div>'
        )

    elif block_type == "chart":
        import html as html_mod
        query = config.get("query", "")
        chart_type = config.get("chart_type", "bar")
        label = config.get("label", "")
        if not query:
            return HTMLResponse('<div class="dashboard-block dashboard-block-error">No query configured</div>')
        escaped_query = html_mod.escape(query, quote=True)
        escaped_type = html_mod.escape(chart_type)
        label_html = ""
        if label:
            label_html = f'<span class="chart-label">{html_mod.escape(label)}</span>'
        return HTMLResponse(
            f'<div class="dashboard-block dashboard-block-chart"'
            f' data-chart-query="{escaped_query}"'
            f' data-chart-type="{escaped_type}">'
            f'<canvas class="chart-canvas"></canvas>'
            f'{label_html}</div>'
        )

    elif block_type == "heading":
        import html as html_mod
        text = config.get("text", "")
        level_str = config.get("level", "2")
        subtitle = config.get("subtitle", "")
        align = config.get("align", "left")
        # Clamp heading level to 1-4
        try:
            level = int(level_str)
        except (ValueError, TypeError):
            level = 2
        level = max(1, min(4, level))
        escaped_text = html_mod.escape(text)
        escaped_align = html_mod.escape(align)
        subtitle_html = ""
        if subtitle:
            subtitle_html = f'<p class="heading-subtitle">{html_mod.escape(subtitle)}</p>'
        return HTMLResponse(
            f'<div class="dashboard-block dashboard-block-heading"'
            f' style="text-align:{escaped_align}">'
            f'<h{level}>{escaped_text}</h{level}>'
            f'{subtitle_html}</div>'
        )

    elif block_type == "form-group":
        slots = config.get("slots", [])
        edges = config.get("edges", [])
        if not slots:
            return HTMLResponse(
                '<div class="dashboard-block dashboard-block-error">'
                'No slots configured for form-group</div>'
            )
        context = {
            "request": request,
            "dashboard_id": dashboard_id,
            "block_index": block_index,
            "slots": slots,
            "edges": edges,
        }
        return templates.TemplateResponse(
            request, "browser/dashboard_form_group.html", context
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
        logger.warning("Dashboard create failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid dashboard data")

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
        logger.warning("Dashboard update failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid dashboard data")

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
