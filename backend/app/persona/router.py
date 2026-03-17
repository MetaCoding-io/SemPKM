"""Persona router — API and browser endpoints for workspace personas.

Provides:
- GET  /api/personas             — list personas (metadata only)
- POST /api/personas             — create persona (auto-activates)
- GET  /api/personas/{id}        — get persona (full payload)
- PUT  /api/personas/{id}        — update persona name
- DELETE /api/personas/{id}      — delete persona
- POST /api/personas/{id}/activate   — activate persona
- POST /api/personas/{id}/save-state — save workspace state to persona

- GET  /browser/personas/selector — render persona selector partial
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.persona.service import PersonaService

logger = logging.getLogger(__name__)

browser_router = APIRouter(prefix="/browser/personas", tags=["personas"])
api_router = APIRouter(prefix="/api/personas", tags=["personas-api"])


def _get_persona_service(request: Request) -> PersonaService:
    """Get persona service from app state."""
    return request.app.state.persona_service


# ---------------------------------------------------------------------------
# API routes (JSON)
# ---------------------------------------------------------------------------


@api_router.get("")
async def list_personas(
    request: Request,
    user: User = Depends(get_current_user),
):
    """List all personas for the current user (metadata only)."""
    service = _get_persona_service(request)
    personas = await service.list_for_user(user.id)
    return JSONResponse(content=[
        {
            "id": p.id,
            "name": p.name,
            "is_active": p.is_active,
            "created_at": p.created_at,
        }
        for p in personas
    ])


@api_router.post("")
async def create_persona(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Create a new persona and auto-activate it."""
    service = _get_persona_service(request)
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    persona = await service.create(
        user_id=user.id,
        name=name,
        layout_json=body.get("layout_json", ""),
        sidebar_positions_json=body.get("sidebar_positions_json", ""),
        explorer_mode=body.get("explorer_mode", "by-type"),
    )

    # Auto-activate newly created persona
    activated = await service.activate(uuid.UUID(persona.id), user.id)
    if activated:
        persona = activated

    logger.info("Persona created and activated: %s (user=%s)", persona.name, user.id)
    return JSONResponse(
        content={
            "id": persona.id,
            "name": persona.name,
            "is_active": persona.is_active,
            "layout_json": persona.layout_json,
            "sidebar_positions_json": persona.sidebar_positions_json,
            "explorer_mode": persona.explorer_mode,
            "created_at": persona.created_at,
        },
        status_code=201,
    )


@api_router.get("/{persona_id}")
async def get_persona(
    persona_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Get a persona by ID (full payload including layout data)."""
    service = _get_persona_service(request)
    persona = await service.get(persona_id)
    if not persona or persona.user_id != str(user.id):
        raise HTTPException(status_code=404, detail="Persona not found")

    return JSONResponse(content={
        "id": persona.id,
        "name": persona.name,
        "is_active": persona.is_active,
        "layout_json": persona.layout_json,
        "sidebar_positions_json": persona.sidebar_positions_json,
        "explorer_mode": persona.explorer_mode,
        "created_at": persona.created_at,
        "updated_at": persona.updated_at,
    })


@api_router.put("/{persona_id}")
async def update_persona(
    persona_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Update a persona's name."""
    service = _get_persona_service(request)
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    result = await service.update(persona_id, user.id, name=name)
    if not result:
        raise HTTPException(status_code=404, detail="Persona not found")

    return JSONResponse(content={
        "id": result.id,
        "name": result.name,
        "is_active": result.is_active,
        "updated_at": result.updated_at,
    })


@api_router.delete("/{persona_id}")
async def delete_persona(
    persona_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Delete a persona."""
    service = _get_persona_service(request)
    deleted = await service.delete(persona_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Persona not found")

    logger.info("Persona deleted: %s (user=%s)", persona_id, user.id)
    return JSONResponse(content=None, status_code=204)


@api_router.post("/{persona_id}/activate")
async def activate_persona(
    persona_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Activate a persona, deactivating all others."""
    service = _get_persona_service(request)
    result = await service.activate(persona_id, user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Persona not found")

    return JSONResponse(content={
        "id": result.id,
        "name": result.name,
        "is_active": result.is_active,
        "layout_json": result.layout_json,
        "sidebar_positions_json": result.sidebar_positions_json,
        "explorer_mode": result.explorer_mode,
    })


@api_router.post("/{persona_id}/save-state")
async def save_persona_state(
    persona_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Save current workspace state to a persona."""
    service = _get_persona_service(request)
    body = await request.json()

    result = await service.save_state(
        persona_id=persona_id,
        user_id=user.id,
        layout_json=body.get("layout_json"),
        sidebar_positions_json=body.get("sidebar_positions_json"),
        explorer_mode=body.get("explorer_mode"),
    )
    if not result:
        raise HTTPException(status_code=404, detail="Persona not found")

    return JSONResponse(content={
        "id": result.id,
        "name": result.name,
        "is_active": result.is_active,
        "layout_json": result.layout_json,
        "sidebar_positions_json": result.sidebar_positions_json,
        "explorer_mode": result.explorer_mode,
    })


# ---------------------------------------------------------------------------
# Browser routes (htmx partials)
# ---------------------------------------------------------------------------


@browser_router.get("/selector")
async def persona_selector(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Render persona selector partial for the user popover."""
    templates = request.app.state.templates
    service = _get_persona_service(request)
    personas = await service.list_for_user(user.id)

    return templates.TemplateResponse(
        request,
        "components/_persona_selector.html",
        {"request": request, "personas": personas},
    )
