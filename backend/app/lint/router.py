"""Lint API endpoints for querying structured SHACL validation results.

Provides paginated, filterable access to validation results via REST.
Endpoints: GET /api/lint/results, GET /api/lint/status, GET /api/lint/diff,
GET /api/lint/stream (SSE).
"""

import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_lint_broadcast, get_lint_service
from app.lint.broadcast import LintBroadcast
from app.lint.models import LintDiffResponse, LintResultsResponse, LintStatusResponse
from app.lint.service import LintService

router = APIRouter(prefix="/api/lint")


@router.get("/results", response_model=LintResultsResponse)
async def get_lint_results(
    page: int = 1,
    per_page: int = 50,
    severity: str | None = None,
    object_type: str | None = None,
    run_id: str | None = None,
    detail: str | None = None,
    user: User = Depends(get_current_user),
    lint_service: LintService = Depends(get_lint_service),
) -> LintResultsResponse:
    """Return paginated lint results with optional filtering.

    Query params:
        page: Page number (1-indexed, default 1).
        per_page: Results per page (default 50, max 200).
        severity: Filter by severity (Violation, Warning, Info).
        object_type: Filter by RDF type IRI of the focus node.
        run_id: Specific run IRI to query (defaults to latest).
        detail: Set to "full" to include source_shape, constraint_component, source_model.
    """
    return await lint_service.get_results(
        page=page,
        per_page=per_page,
        severity=severity,
        object_type=object_type,
        run_id=run_id,
        detail=(detail == "full"),
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

    async def event_generator():
        queue = broadcast.subscribe()
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event.format()
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent connection timeout
                    yield ": keepalive\n\n"
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
