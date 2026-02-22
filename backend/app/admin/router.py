"""Admin portal routes for model management and webhook configuration.

Serves Jinja2 templates with htmx partial rendering for in-place updates.
Uses ModelService and WebhookService via FastAPI dependency injection.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from app.dependencies import get_model_service, get_webhook_service
from app.services.models import ModelService
from app.services.webhooks import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")


def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an htmx partial request."""
    return request.headers.get("HX-Request") == "true"


@router.get("/")
async def admin_index(request: Request):
    """Render the admin portal landing page with links to Models and Webhooks."""
    templates = request.app.state.templates
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "admin/index.html", block_name="content"
        )
    return templates.TemplateResponse(request, "admin/index.html")


@router.get("/models")
async def admin_models(
    request: Request,
    model_service: ModelService = Depends(get_model_service),
):
    """Render model management page with table of installed models."""
    models = await model_service.list_models()
    context = {"request": request, "models": models}
    if _is_htmx_request(request):
        return templates_response(request, "admin/models.html", context, block_name="content")
    return templates_response(request, "admin/models.html", context)


@router.post("/models/install")
async def admin_models_install(
    request: Request,
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
        context["success"] = f"Model '{result.model_id}' installed successfully."
        if result.warnings:
            context["success"] += " Warnings: " + "; ".join(result.warnings)

    return templates_response(request, "admin/models.html", context, block_name="model_table")


@router.delete("/models/{model_id}")
async def admin_models_remove(
    request: Request,
    model_id: str,
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
        context["success"] = f"Model '{model_id}' removed."

    return templates_response(request, "admin/models.html", context, block_name="model_table")


def templates_response(request: Request, template: str, context: dict, block_name: str | None = None):
    """Render a template with optional block-level rendering."""
    templates = request.app.state.templates
    if block_name:
        return templates.TemplateResponse(request, template, context, block_name=block_name)
    return templates.TemplateResponse(request, template, context)
