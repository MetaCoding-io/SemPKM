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
