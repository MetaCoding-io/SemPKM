"""Task template router — REST API + htmx browser routes.

API routes (``/api/task-templates``):
  - GET  /                    — list all templates
  - POST /                    — create template
  - GET  /{template_id}       — get single template
  - PATCH /{template_id}      — update template fields
  - DELETE /{template_id}     — delete template
  - POST /{template_id}/instantiate — create objects from template

Browser routes (``/browser/task-templates``):
  - GET /picker               — htmx partial for template selection
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, TypeAdapter
from rdflib import URIRef

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.commands.dispatcher import dispatch
from app.commands.schemas import Command
from app.config import settings
from app.events.store import EventStore, Operation
from app.task_templates.service import TaskTemplateService

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api/task-templates", tags=["task-templates-api"])
browser_router = APIRouter(prefix="/browser/task-templates", tags=["task-templates"])

_command_adapter = TypeAdapter(Command)


def _get_template_service(request: Request) -> TaskTemplateService:
    """Get template service from app state."""
    return request.app.state.template_service


# -----------------------------------------------------------------------
# Pydantic request models
# -----------------------------------------------------------------------


class CreateTemplateRequest(BaseModel):
    title: str
    target_class: str
    default_properties: dict | None = None
    subtask_definitions: list[dict] | None = None


class UpdateTemplateRequest(BaseModel):
    title: str | None = None
    target_class: str | None = None
    default_properties: dict | None = None
    subtask_definitions: list[dict] | None = None


class InstantiateRequest(BaseModel):
    overrides: dict | None = None


# -----------------------------------------------------------------------
# API routes
# -----------------------------------------------------------------------


@api_router.get("")
async def list_templates(
    user: User = Depends(get_current_user),
    service: TaskTemplateService = Depends(_get_template_service),
):
    """List all task templates."""
    templates = await service.list_all()
    return JSONResponse(content=templates)


@api_router.post("")
async def create_template(
    body: CreateTemplateRequest,
    user: User = Depends(get_current_user),
    service: TaskTemplateService = Depends(_get_template_service),
):
    """Create a new task template."""
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    template = await service.create(
        title=body.title.strip(),
        target_class=body.target_class,
        default_properties=body.default_properties,
        subtask_definitions=body.subtask_definitions,
    )
    return JSONResponse(content=template, status_code=201)


@api_router.get("/{template_id:path}")
async def get_template(
    template_id: str,
    user: User = Depends(get_current_user),
    service: TaskTemplateService = Depends(_get_template_service),
):
    """Get a single task template by IRI."""
    template = await service.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return JSONResponse(content=template)


@api_router.patch("/{template_id:path}")
async def update_template(
    template_id: str,
    body: UpdateTemplateRequest,
    user: User = Depends(get_current_user),
    service: TaskTemplateService = Depends(_get_template_service),
):
    """Update fields on an existing template."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    result = await service.update(template_id, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return JSONResponse(content=result)


@api_router.delete("/{template_id:path}")
async def delete_template(
    template_id: str,
    user: User = Depends(get_current_user),
    service: TaskTemplateService = Depends(_get_template_service),
):
    """Delete a task template."""
    deleted = await service.delete(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    return JSONResponse(content={"deleted": True})


@api_router.post("/{template_id:path}/instantiate")
async def instantiate_template(
    request: Request,
    template_id: str,
    user: User = Depends(get_current_user),
    service: TaskTemplateService = Depends(_get_template_service),
):
    """Instantiate a template: create objects via the batch command pipeline.

    Builds command dicts from the template, dispatches them through the
    same ``dispatch()`` + ``EventStore.commit()`` pipeline as
    ``POST /api/commands``, and returns the created IRIs.
    """
    # Parse optional overrides from JSON body (if provided)
    overrides: dict | None = None
    try:
        body = await request.json()
        overrides = body.get("overrides")
    except Exception:
        pass  # no body or invalid JSON — fine, use template defaults

    try:
        command_dicts = await service.instantiate(template_id, overrides)
    except ValueError as e:
        logger.warning("Template instantiate failed: %s", e)
        raise HTTPException(status_code=404, detail="Template not found")

    # Dispatch through the batch command pipeline
    client = request.app.state.triplestore_client
    try:
        commands = [_command_adapter.validate_python(cd) for cd in command_dicts]

        operations: list[Operation] = []
        command_iris: list[str] = []
        slot_map: dict[str, str] = {}

        for cmd in commands:
            # Resolve @slot: references on edge.create commands
            if cmd.command == "edge.create":
                for field_name in ("source", "target"):
                    value = getattr(cmd.params, field_name)
                    if isinstance(value, str) and value.startswith("@slot:"):
                        slot_name = value[6:]
                        if slot_name not in slot_map:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Unresolved slot reference: @slot:{slot_name}",
                            )
                        object.__setattr__(cmd.params, field_name, slot_map[slot_name])

            operation = await dispatch(cmd, settings.base_namespace)
            operations.append(operation)

            primary_iri = operation.affected_iris[0] if operation.affected_iris else ""
            command_iris.append(primary_iri)

            # Record slot mapping
            if cmd.command == "object.create" and getattr(cmd, "slot", None):
                slot_map[cmd.slot] = primary_iri

        # Commit all operations atomically
        event_store = EventStore(client)
        user_iri = URIRef(f"urn:sempkm:user:{user.id}")
        event_result = await event_store.commit(
            operations,
            performed_by=user_iri,
            performed_by_role=user.role,
        )

        # Trigger async validation
        validation_queue = request.app.state.validation_queue
        await validation_queue.enqueue(
            event_iri=str(event_result.event_iri),
            timestamp=event_result.timestamp,
        )

        logger.info(
            "Template %s instantiated → %d objects, event=%s",
            template_id,
            len(command_iris),
            event_result.event_iri,
        )

        return JSONResponse(
            content={
                "created_iris": command_iris,
                "event_iri": str(event_result.event_iri),
                "template_id": template_id,
            },
            status_code=201,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Template instantiation failed for %s", template_id)
        raise HTTPException(
            status_code=500,
            detail=f"Instantiation failed: {str(e)}",
        )


# -----------------------------------------------------------------------
# Browser routes (htmx partials)
# -----------------------------------------------------------------------


@browser_router.get("/picker")
async def template_picker(
    request: Request,
    user: User = Depends(get_current_user),
    service: TaskTemplateService = Depends(_get_template_service),
):
    """Render the template picker partial for command palette / modal use."""
    templates_engine = request.app.state.templates
    template_list = await service.list_all()
    context = {
        "request": request,
        "templates": template_list,
    }
    return templates_engine.TemplateResponse(
        request, "browser/template_picker.html", context,
    )
