"""Lint API endpoints for querying structured SHACL validation results.

Provides paginated, filterable access to validation results via REST.
Endpoints: GET /api/lint/results, GET /api/lint/status, GET /api/lint/diff,
GET /api/lint/stream (SSE), plus lint filter CRUD endpoints for
suppressions, dismissals, and presets.
"""

import asyncio
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.config import TIMEOUT_DEFAULT
from app.dependencies import get_lint_broadcast, get_lint_filter_service, get_lint_service
from app.lint.broadcast import LintBroadcast
from app.lint.filter_service import LintFilterService
from app.lint.models import (
    DismissalResponse,
    DismissRequest,
    LintDiffResponse,
    LintResultsResponse,
    LintStatusResponse,
    PresetCreateRequest,
    PresetResponse,
    PresetUpdateRequest,
    SuppressionResponse,
    SuppressRequest,
)
from app.lint.service import LintService

router = APIRouter(prefix="/api/lint", tags=["lint"])


@router.get("/results", response_model=LintResultsResponse)
async def get_lint_results(
    page: int = 1,
    per_page: int = 50,
    severity: str | None = None,
    object_type: str | None = None,
    run_id: str | None = None,
    detail: str | None = None,
    search: str | None = None,
    sort: str = "severity",
    user: User = Depends(get_current_user),
    lint_service: LintService = Depends(get_lint_service),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
) -> LintResultsResponse:
    """Return paginated lint results with optional filtering.

    Query params:
        page: Page number (1-indexed, default 1).
        per_page: Results per page (default 50, max 200).
        severity: Filter by severity (Violation, Warning, Info).
        object_type: Filter by RDF type IRI of the focus node.
        run_id: Specific run IRI to query (defaults to latest).
        detail: Set to "full" to include source_shape, constraint_component, source_model.
        search: Keyword search across message, object IRI, and property path.
        sort: Sort order (severity, object, path). Default: severity.

    User's active suppressions and dismissals are automatically applied.
    """
    suppressed_rules, dismissed_pairs = await filter_service.get_user_filters(user.id)
    return await lint_service.get_results(
        page=page,
        per_page=per_page,
        severity=severity,
        object_type=object_type,
        run_id=run_id,
        detail=(detail == "full"),
        search=search,
        sort=sort,
        suppressed_rules=suppressed_rules or None,
        dismissed_pairs=dismissed_pairs or None,
    )


@router.get("/status", response_model=LintStatusResponse)
async def get_lint_status(
    user: User = Depends(get_current_user),
    lint_service: LintService = Depends(get_lint_service),
) -> LintStatusResponse:
    """Return lightweight summary of the latest lint run for polling."""
    return await lint_service.get_status()


@router.get("/diff", response_model=LintDiffResponse)
async def get_lint_diff(
    user: User = Depends(get_current_user),
    lint_service: LintService = Depends(get_lint_service),
) -> LintDiffResponse:
    """Return new and resolved issues comparing latest vs previous run."""
    return await lint_service.get_diff()


@router.get("/stream")
async def lint_stream(
    request: Request,
    user: User = Depends(get_current_user),
    broadcast: LintBroadcast = Depends(get_lint_broadcast),
):
    """SSE stream for real-time lint event notifications.

    Clients receive `validation_complete` events when a validation run
    finishes. The event data contains summary counts only (not full
    results) to keep the stream lightweight.

    Auto-reconnects are handled by the browser EventSource API.
    """

    shutdown_event = request.app.state.shutdown_event

    async def event_generator():
        queue = broadcast.subscribe()
        try:
            while not shutdown_event.is_set():
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                try:
                    # Race queue.get() against shutdown signal so the
                    # generator exits promptly during uvicorn reload.
                    get_task = asyncio.ensure_future(queue.get())
                    shutdown_task = asyncio.ensure_future(shutdown_event.wait())
                    done, pending = await asyncio.wait(
                        {get_task, shutdown_task},
                        timeout=TIMEOUT_DEFAULT,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
                    if shutdown_task in done:
                        break
                    if get_task in done:
                        yield get_task.result().format()
                    else:
                        # Timeout — send keepalive
                        yield ": keepalive\n\n"
                except asyncio.CancelledError:
                    break
        finally:
            broadcast.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Suppression endpoints
# ---------------------------------------------------------------------------


@router.post("/suppress", response_model=SuppressionResponse, status_code=201)
async def create_suppression(
    body: SuppressRequest,
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
) -> SuppressionResponse:
    """Suppress all lint results for a given rule source IRI."""
    try:
        data = await filter_service.add_suppression(user.id, body.rule_source_iri)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return SuppressionResponse(
        id=data.id,
        rule_source_iri=data.rule_source_iri,
        created_at=data.created_at,
    )


@router.delete("/suppress/{suppression_id}", status_code=200)
async def delete_suppression(
    suppression_id: _uuid.UUID,
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
):
    """Remove a single suppression by ID."""
    deleted = await filter_service.delete_suppression(suppression_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Suppression not found")
    return {"ok": True}


@router.get("/suppressions", response_model=list[SuppressionResponse])
async def list_suppressions(
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
) -> list[SuppressionResponse]:
    """List all active suppressions for the authenticated user."""
    items = await filter_service.list_suppressions(user.id)
    return [
        SuppressionResponse(
            id=s.id,
            rule_source_iri=s.rule_source_iri,
            created_at=s.created_at,
        )
        for s in items
    ]


@router.delete("/suppressions", status_code=200)
async def clear_suppressions(
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
):
    """Clear all suppressions for the authenticated user."""
    count = await filter_service.clear_suppressions(user.id)
    return {"deleted": count}


# ---------------------------------------------------------------------------
# Dismissal endpoints
# ---------------------------------------------------------------------------


@router.post("/dismiss", response_model=DismissalResponse, status_code=201)
async def create_dismissal(
    body: DismissRequest,
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
) -> DismissalResponse:
    """Dismiss a specific lint result (object + rule pair)."""
    try:
        data = await filter_service.add_dismissal(
            user.id, body.object_iri, body.rule_source_iri
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return DismissalResponse(
        id=data.id,
        object_iri=data.object_iri,
        rule_source_iri=data.rule_source_iri,
        created_at=data.created_at,
    )


@router.delete("/dismiss/{dismissal_id}", status_code=200)
async def delete_dismissal(
    dismissal_id: _uuid.UUID,
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
):
    """Remove a single dismissal by ID."""
    deleted = await filter_service.delete_dismissal(dismissal_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dismissal not found")
    return {"ok": True}


@router.get("/dismissals", response_model=list[DismissalResponse])
async def list_dismissals(
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
) -> list[DismissalResponse]:
    """List all active dismissals for the authenticated user."""
    items = await filter_service.list_dismissals(user.id)
    return [
        DismissalResponse(
            id=d.id,
            object_iri=d.object_iri,
            rule_source_iri=d.rule_source_iri,
            created_at=d.created_at,
        )
        for d in items
    ]


@router.delete("/dismissals", status_code=200)
async def clear_dismissals(
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
):
    """Clear all dismissals for the authenticated user."""
    count = await filter_service.clear_dismissals(user.id)
    return {"deleted": count}


# ---------------------------------------------------------------------------
# Preset endpoints
# ---------------------------------------------------------------------------


@router.post("/presets", response_model=PresetResponse, status_code=201)
async def create_preset(
    body: PresetCreateRequest,
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
) -> PresetResponse:
    """Create a named filter preset."""
    try:
        data = await filter_service.create_preset(
            user.id, body.name, body.suppressed_rules
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return PresetResponse(
        id=data.id,
        name=data.name,
        suppressed_rules=data.suppressed_rules,
        created_at=data.created_at,
        updated_at=data.updated_at,
    )


@router.get("/presets", response_model=list[PresetResponse])
async def list_presets(
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
) -> list[PresetResponse]:
    """List all filter presets for the authenticated user."""
    items = await filter_service.list_presets(user.id)
    return [
        PresetResponse(
            id=p.id,
            name=p.name,
            suppressed_rules=p.suppressed_rules,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in items
    ]


@router.put("/presets/{preset_id}", response_model=PresetResponse)
async def update_preset(
    preset_id: _uuid.UUID,
    body: PresetUpdateRequest,
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
) -> PresetResponse:
    """Update a preset's name and/or rules."""
    data = await filter_service.update_preset(
        preset_id, user.id, name=body.name, suppressed_rules=body.suppressed_rules
    )
    if data is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    return PresetResponse(
        id=data.id,
        name=data.name,
        suppressed_rules=data.suppressed_rules,
        created_at=data.created_at,
        updated_at=data.updated_at,
    )


@router.delete("/presets/{preset_id}", status_code=200)
async def delete_preset(
    preset_id: _uuid.UUID,
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
):
    """Delete a preset by ID."""
    deleted = await filter_service.delete_preset(preset_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"ok": True}


@router.post("/presets/{preset_id}/apply", status_code=200)
async def apply_preset(
    preset_id: _uuid.UUID,
    user: User = Depends(get_current_user),
    filter_service: LintFilterService = Depends(get_lint_filter_service),
):
    """Apply a preset: replace all suppressions with the preset's rule list."""
    applied = await filter_service.apply_preset(preset_id, user.id)
    if not applied:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"ok": True}
