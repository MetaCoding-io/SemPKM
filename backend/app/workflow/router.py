"""Workflow router — runner UI and API endpoints for WorkflowSpec.

Provides:
- GET /browser/workflow/{id}/run — render workflow runner (stepper + step content)
- GET /browser/workflow/{id}/step/{index} — render individual step content
- GET /api/workflow — list user's workflows (JSON)
- POST /api/workflow — create workflow (JSON)
- PATCH /api/workflow/{id} — update workflow (JSON)
- DELETE /api/workflow/{id} — delete workflow
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.workflow.service import WorkflowService, WorkflowData

logger = logging.getLogger(__name__)

browser_router = APIRouter(prefix="/browser/workflow", tags=["workflow"])
api_router = APIRouter(prefix="/api/workflow", tags=["workflow-api"])


def _get_workflow_service(request: Request) -> WorkflowService:
    """Get workflow service from app state."""
    return request.app.state.workflow_service


# ---------------------------------------------------------------------------
# Browser routes (htmx partials)
# ---------------------------------------------------------------------------


@browser_router.get("/{workflow_id}/run")
async def run_workflow(
    request: Request,
    workflow_id: str,
    user: User = Depends(get_current_user),
):
    """Render the workflow runner with stepper bar and first step content."""
    templates = request.app.state.templates
    service = _get_workflow_service(request)

    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")

    workflow = await service.get(wid)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if not workflow.steps:
        return HTMLResponse('<div class="workflow-empty">This workflow has no steps defined.</div>')

    # Build step metadata for stepper bar
    step_meta = []
    for i, step in enumerate(workflow.steps):
        step_meta.append({
            "index": i,
            "label": step.get("label", f"Step {i + 1}"),
            "type": step.get("type", "view"),
        })

    context = {
        "request": request,
        "workflow": workflow,
        "steps": step_meta,
        "total_steps": len(workflow.steps),
        "workflow_id": workflow_id,
    }

    return templates.TemplateResponse(
        request, "browser/workflow_runner.html", context
    )


@browser_router.get("/{workflow_id}/step/{step_index}")
async def render_step(
    request: Request,
    workflow_id: str,
    step_index: int,
    user: User = Depends(get_current_user),
):
    """Render a single workflow step's content.

    Step types:
    - view: loads a ViewSpec via htmx
    - dashboard: loads a dashboard via htmx
    - form: loads a SHACL create form via htmx
    """
    service = _get_workflow_service(request)

    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")

    workflow = await service.get(wid)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if step_index < 0 or step_index >= len(workflow.steps):
        raise HTTPException(status_code=404, detail="Step not found")

    step = workflow.steps[step_index]
    step_type = step.get("type", "view")
    config = step.get("config", {})

    if step_type == "view":
        spec_iri = config.get("spec_iri", "")
        renderer = config.get("renderer_type", "table")
        if not spec_iri:
            return HTMLResponse('<div class="workflow-step-error">No view spec configured for this step.</div>')
        view_url = f"/browser/views/{renderer}/{spec_iri}"
        return HTMLResponse(
            f'<div class="workflow-step workflow-step-view"'
            f' hx-get="{view_url}" hx-trigger="load" hx-swap="innerHTML">'
            f'<div class="workflow-step-loading">Loading view...</div></div>'
        )

    elif step_type == "dashboard":
        dashboard_id = config.get("dashboard_id", "")
        if not dashboard_id:
            return HTMLResponse('<div class="workflow-step-error">No dashboard configured for this step.</div>')
        dash_url = f"/browser/dashboard/{dashboard_id}"
        return HTMLResponse(
            f'<div class="workflow-step workflow-step-dashboard"'
            f' hx-get="{dash_url}" hx-trigger="load" hx-swap="innerHTML">'
            f'<div class="workflow-step-loading">Loading dashboard...</div></div>'
        )

    elif step_type == "form":
        target_class = config.get("target_class", "")
        if not target_class:
            return HTMLResponse('<div class="workflow-step-error">No target class configured for this step.</div>')
        form_url = f"/browser/objects/create-form?type_iri={target_class}"
        return HTMLResponse(
            f'<div class="workflow-step workflow-step-form"'
            f' hx-get="{form_url}" hx-trigger="load" hx-swap="innerHTML">'
            f'<div class="workflow-step-loading">Loading form...</div></div>'
        )

    return HTMLResponse('<div class="workflow-step-error">Unknown step type.</div>')


# ---------------------------------------------------------------------------
# API routes (JSON)
# ---------------------------------------------------------------------------


@api_router.get("")
async def list_workflows(
    user: User = Depends(get_current_user),
    service: WorkflowService = Depends(_get_workflow_service),
):
    """List all workflows for the current user."""
    workflows = await service.list_for_user(user.id)
    return JSONResponse(content=[
        {"id": w.id, "name": w.name, "description": w.description, "step_count": len(w.steps)}
        for w in workflows
    ])


@api_router.post("")
async def create_workflow(
    request: Request,
    user: User = Depends(get_current_user),
    service: WorkflowService = Depends(_get_workflow_service),
):
    """Create a new workflow."""
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    try:
        workflow = await service.create(
            user_id=user.id,
            name=name,
            steps=body.get("steps", []),
            description=body.get("description", ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(
        content={"id": workflow.id, "name": workflow.name},
        status_code=201,
    )


@api_router.patch("/{workflow_id}")
async def update_workflow(
    request: Request,
    workflow_id: str,
    user: User = Depends(get_current_user),
    service: WorkflowService = Depends(_get_workflow_service),
):
    """Update a workflow."""
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")

    body = await request.json()
    updates = {}
    if "name" in body:
        updates["name"] = body["name"]
    if "description" in body:
        updates["description"] = body["description"]
    if "steps" in body:
        updates["steps"] = body["steps"]

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    try:
        result = await service.update(wid, user.id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return JSONResponse(content={"id": result.id, "name": result.name})


@api_router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    user: User = Depends(get_current_user),
    service: WorkflowService = Depends(_get_workflow_service),
):
    """Delete a workflow."""
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")

    deleted = await service.delete(wid, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return JSONResponse(content={"deleted": True})
