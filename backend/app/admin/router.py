"""Admin portal routes for model management and webhook configuration.

Serves Jinja2 templates with htmx partial rendering for in-place updates.
Uses ModelService and WebhookService via FastAPI dependency injection.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from app.auth.dependencies import require_role
from app.auth.models import User
from app.dependencies import get_model_service, get_webhook_service
from app.services.models import ModelService
from app.services.webhooks import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")

# Available webhook event types
WEBHOOK_EVENT_TYPES = ["object.changed", "edge.changed", "validation.completed"]


def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an htmx partial request."""
    return request.headers.get("HX-Request") == "true"


@router.get("/")
async def admin_index(request: Request, user: User = Depends(require_role("owner"))):
    """Render the admin portal landing page with links to Models and Webhooks."""
    templates = request.app.state.templates
    context = {"active_page": "admin", "user": user}
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "admin/index.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "admin/index.html", context)


@router.get("/models")
async def admin_models(
    request: Request,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
):
    """Render model management page with table of installed models."""
    models = await model_service.list_models()
    context = {"request": request, "models": models, "user": user}
    if _is_htmx_request(request):
        return templates_response(request, "admin/models.html", context, block_name="content")
    return templates_response(request, "admin/models.html", context)


@router.get("/models/{model_id}")
async def admin_model_detail(
    request: Request,
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
):
    """Render read-only detail dashboard for an installed Mental Model."""
    detail = await model_service.get_model_detail(model_id)
    if detail is None:
        models = await model_service.list_models()
        context = {"request": request, "models": models, "error": f"Model '{model_id}' not found.", "user": user}
        return templates_response(request, "admin/models.html", context)

    # Get icon data from IconService
    from app.services.icons import IconService
    icon_svc = IconService(models_dir="/app/models")
    icon_map = icon_svc.get_icon_map("tree")

    # Attach icon/color to each type
    for t in detail["types"]:
        icon_info = icon_map.get(t["iri"], {"icon": "circle", "color": "#999"})
        t["icon"] = icon_info["icon"]
        t["color"] = icon_info["color"]

    # Build type-centric detail: merge shapes, views, relationships per type
    type_map = {}
    for t in detail["types"]:
        type_map[t["local_name"]] = {
            **t,
            "fields": [],
            "field_count": 0,
            "views": [],
            "relationships": [],
        }

    for shape in detail["shapes"]:
        tc = shape["target_class"]
        if tc in type_map:
            type_map[tc]["fields"] = shape["properties"]
            type_map[tc]["field_count"] = shape["property_count"]

    for v in detail["views"]:
        tc = v["target_class"]
        if tc in type_map:
            type_map[tc]["views"].append(v)

    for p in detail["properties"]:
        if p["prop_type"] == "Object":
            domain = p["domain"]
            if domain in type_map:
                type_map[domain]["relationships"].append(p)

    # Fetch live analytics (instance counts, top nodes)
    type_iris = [t["iri"] for t in detail["types"]]
    analytics = await model_service.get_type_analytics(type_iris)
    for td in type_map.values():
        a = analytics.get(td["iri"], {"count": 0, "top_nodes": []})
        td["instance_count"] = a["count"]
        td["top_nodes"] = a["top_nodes"]

    detail["type_details"] = list(type_map.values())

    # Stats
    detail["stats"] = {
        "types": len(detail["types"]),
        "properties": len(detail["properties"]),
        "views": len(detail["views"]),
        "shapes": len(detail["shapes"]),
    }

    context = {"request": request, "detail": detail, "user": user}
    if _is_htmx_request(request):
        return templates_response(request, "admin/model_detail.html", context, block_name="content")
    return templates_response(request, "admin/model_detail.html", context)


@router.get("/models/{model_id}/ontology-diagram")
async def admin_model_ontology_diagram(
    request: Request,
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
):
    """Render SVG ontology relationship diagram for a model.

    Shows type-to-type relationships derived from OWL ObjectProperties.
    Returns an htmx partial with inline SVG.
    """
    detail = await model_service.get_model_detail(model_id)
    if detail is None:
        return HTMLResponse(
            '<div class="diagram-empty"><p>Model not found.</p></div>',
            status_code=404,
        )

    # Get icon data from IconService for type colors
    from app.services.icons import IconService
    icon_svc = IconService(models_dir="/app/models")
    icon_map = icon_svc.get_icon_map("tree")

    # Build type info with colors
    type_info = {}
    for t in detail["types"]:
        icon_data = icon_map.get(t["iri"], {"icon": "circle", "color": "#999"})
        type_info[t["local_name"]] = {
            "label": t["label"],
            "color": icon_data["color"],
        }

    # Filter to ObjectProperties only, building edges
    edges = []
    for p in detail["properties"]:
        if p["prop_type"] == "Object" and p["domain"] and p["range"]:
            edges.append({
                "from": p["domain"],
                "to": p["range"],
                "label": p["label"],
                "inverse": p.get("inverse", ""),
            })

    # Compute node positions -- circular layout
    type_names = list(type_info.keys())
    node_count = len(type_names)
    import math
    # SVG dimensions
    svg_w, svg_h = 700, 500
    cx, cy = svg_w / 2, svg_h / 2
    radius = min(svg_w, svg_h) * 0.35
    nodes = {}
    for i, name in enumerate(type_names):
        angle = (2 * math.pi * i / node_count) - math.pi / 2  # start from top
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        nodes[name] = {
            "x": round(x, 1),
            "y": round(y, 1),
            "label": type_info[name]["label"],
            "color": type_info[name]["color"],
        }

    context = {
        "request": request,
        "model_id": model_id,
        "nodes": nodes,
        "edges": edges,
        "svg_w": svg_w,
        "svg_h": svg_h,
    }
    return templates_response(request, "admin/model_ontology_diagram.html", context)


@router.post("/models/install")
async def admin_models_install(
    request: Request,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
    path: str = Form(...),
):
    """Install a Mental Model from a filesystem path.

    Returns the updated model table partial for htmx swap.
    """
    result = await model_service.install(Path(path))
    models = await model_service.list_models()
    context = {"request": request, "models": models}

    if not result.success:
        error_msg = "; ".join(result.errors)
        context["error"] = error_msg
        logger.warning("Model install failed: %s", error_msg)
    else:
        # Invalidate ViewSpec cache after successful model install
        request.app.state.view_spec_service.invalidate_cache()
        context["success"] = f"Model '{result.model_id}' installed successfully."
        if result.warnings:
            context["success"] += " Warnings: " + "; ".join(result.warnings)

    return templates_response(request, "admin/models.html", context, block_name="model_table")


@router.delete("/models/{model_id}")
async def admin_models_remove(
    request: Request,
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
):
    """Remove an installed Mental Model.

    Returns the updated model table partial for htmx swap.
    Handles 404 (not installed) and 409 (user data exists) errors.
    """
    result = await model_service.remove(model_id)
    models = await model_service.list_models()
    context = {"request": request, "models": models}

    if not result.success:
        error_msg = "; ".join(result.errors)
        context["error"] = error_msg
        logger.warning("Model remove failed for '%s': %s", model_id, error_msg)
    else:
        # Invalidate ViewSpec cache after successful model removal
        request.app.state.view_spec_service.invalidate_cache()
        context["success"] = f"Model '{model_id}' removed."

    return templates_response(request, "admin/models.html", context, block_name="model_table")


# ---- Webhook endpoints ----


@router.get("/webhooks")
async def admin_webhooks(
    request: Request,
    user: User = Depends(require_role("owner")),
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """Render webhook configuration page with list of configured webhooks."""
    webhooks = await webhook_service.list_configs()
    context = {
        "request": request,
        "webhooks": webhooks,
        "event_types": WEBHOOK_EVENT_TYPES,
        "user": user,
    }
    if _is_htmx_request(request):
        return templates_response(request, "admin/webhooks.html", context, block_name="content")
    return templates_response(request, "admin/webhooks.html", context)


@router.post("/webhooks")
async def admin_webhooks_create(
    request: Request,
    user: User = Depends(require_role("owner")),
    webhook_service: WebhookService = Depends(get_webhook_service),
    target_url: str = Form(...),
    events: list[str] = Form(default=[]),
    filters: str = Form(default=""),
):
    """Create a new webhook configuration.

    Accepts target URL, event types (multi-select), and optional filters.
    Returns updated webhook list partial for htmx swap.
    """
    # Parse comma-separated filters into list
    filter_list = [f.strip() for f in filters.split(",") if f.strip()] if filters else []

    context: dict = {
        "request": request,
        "event_types": WEBHOOK_EVENT_TYPES,
    }

    if not events:
        webhooks = await webhook_service.list_configs()
        context["webhooks"] = webhooks
        context["error"] = "Please select at least one event type."
        return templates_response(request, "admin/webhooks.html", context, block_name="webhook_list")

    try:
        await webhook_service.create_config(
            target_url=target_url,
            events=events,
            filters=filter_list if filter_list else None,
        )
        context["success"] = f"Webhook created for {target_url}."
    except Exception as e:
        context["error"] = f"Failed to create webhook: {e}"
        logger.warning("Webhook creation failed: %s", e)

    webhooks = await webhook_service.list_configs()
    context["webhooks"] = webhooks
    return templates_response(request, "admin/webhooks.html", context, block_name="webhook_list")


@router.delete("/webhooks/{webhook_id}")
async def admin_webhooks_delete(
    request: Request,
    webhook_id: str,
    user: User = Depends(require_role("owner")),
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """Delete a webhook configuration.

    Returns updated webhook list partial for htmx swap.
    """
    context: dict = {
        "request": request,
        "event_types": WEBHOOK_EVENT_TYPES,
    }

    deleted = await webhook_service.delete_config(webhook_id)
    if not deleted:
        context["error"] = f"Webhook '{webhook_id}' not found."
    else:
        context["success"] = "Webhook deleted."

    webhooks = await webhook_service.list_configs()
    context["webhooks"] = webhooks
    return templates_response(request, "admin/webhooks.html", context, block_name="webhook_list")


@router.post("/webhooks/{webhook_id}/toggle")
async def admin_webhooks_toggle(
    request: Request,
    webhook_id: str,
    user: User = Depends(require_role("owner")),
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """Toggle a webhook's enabled/disabled state.

    Returns updated webhook list partial for htmx swap.
    """
    context: dict = {
        "request": request,
        "event_types": WEBHOOK_EVENT_TYPES,
    }

    try:
        current = await webhook_service.get_config(webhook_id)
        if current is None:
            context["error"] = f"Webhook '{webhook_id}' not found."
        else:
            new_enabled = not current.enabled
            await webhook_service.update_config(webhook_id, enabled=new_enabled)
            state = "enabled" if new_enabled else "disabled"
            context["success"] = f"Webhook {state}."
    except Exception as e:
        context["error"] = f"Failed to toggle webhook: {e}"
        logger.warning("Webhook toggle failed for '%s': %s", webhook_id, e)

    webhooks = await webhook_service.list_configs()
    context["webhooks"] = webhooks
    return templates_response(request, "admin/webhooks.html", context, block_name="webhook_list")


def templates_response(request: Request, template: str, context: dict, block_name: str | None = None):
    """Render a template with optional block-level rendering."""
    templates = request.app.state.templates
    if block_name:
        return templates.TemplateResponse(request, template, context, block_name=block_name)
    return templates.TemplateResponse(request, template, context)
