"""Context API — update, query, and stream real-time user context.

Endpoints:
- POST /api/context/update   — upsert context (rate-limited)
- GET  /api/context/current   — read current context with staleness
- GET  /api/context/stream    — SSE stream for live context events
"""

import asyncio
import dataclasses
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user_or_api
from app.auth.models import User
from app.auth.rate_limit import limiter
from app.context.broadcast import ContextBroadcast
from app.context.service import ContextService
from app.dependencies import get_context_broadcast, get_context_service
from app.lint.broadcast import SSEEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context", tags=["context"])


# ── Request / Response models ────────────────────────────────────


class ContextUpdateRequest(BaseModel):
    """Payload for POST /api/context/update.

    All fields are optional — only provided fields are persisted.
    """

    location_zone: str | None = Field(
        None, max_length=100, description="Coarse location label"
    )
    activity: str | None = Field(
        None, max_length=50, description="Activity state"
    )
    time_period: str | None = Field(
        None, max_length=50, description="Time-of-day bucket"
    )
    calendar_event: str | None = Field(
        None, max_length=500, description="Current/next calendar event"
    )
    calendar_busy: bool | None = Field(
        None, description="Whether the user is in a busy slot"
    )
    device_id: str | None = Field(
        None, max_length=100, description="Opaque device identifier"
    )


# ── Endpoints ────────────────────────────────────────────────────


@router.post("/update")
@limiter.limit("12/minute")
async def update_context(
    body: ContextUpdateRequest,
    request: Request,
    user: User = Depends(get_current_user_or_api),
    service: ContextService = Depends(get_context_service),
    broadcast: ContextBroadcast = Depends(get_context_broadcast),
):
    """Upsert the caller's context snapshot.

    Only the fields present in the request body are written; absent
    fields leave the stored value unchanged.  After persisting, the
    updated context is broadcast to all SSE subscribers.

    Rate-limited to 12 requests / minute per IP (≈ 1 per 5 s).
    """
    # Build kwargs from explicitly-provided fields only
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=422,
            detail="At least one context field must be provided",
        )

    ctx = await service.update(user.id, **fields)

    # Publish SSE event to all connected clients
    await broadcast.publish(
        SSEEvent(
            event="context_update",
            data=dataclasses.asdict(ctx),
        )
    )

    return dataclasses.asdict(ctx)


@router.get("/current")
async def get_current_context(
    user: User = Depends(get_current_user_or_api),
    service: ContextService = Depends(get_context_service),
):
    """Return the caller's current context snapshot.

    Returns ``{"context": null}`` if the user has never posted
    context.  The ``is_stale`` field indicates whether the context
    has exceeded its TTL (default 15 min).
    """
    ctx = await service.get_current(user.id)
    if ctx is None:
        return {"context": None}
    return {"context": dataclasses.asdict(ctx)}


@router.get("/stream")
async def context_stream(
    request: Request,
    user: User = Depends(get_current_user_or_api),
    broadcast: ContextBroadcast = Depends(get_context_broadcast),
):
    """SSE stream for real-time context update notifications.

    Clients receive ``context_update`` events whenever any user's
    context changes.  The stream sends 30 s keepalives and shuts
    down cleanly on server reload.
    """
    shutdown_event = request.app.state.shutdown_event

    async def event_generator():
        queue = broadcast.subscribe()
        try:
            while not shutdown_event.is_set():
                if await request.is_disconnected():
                    break
                try:
                    get_task = asyncio.ensure_future(queue.get())
                    shutdown_task = asyncio.ensure_future(shutdown_event.wait())
                    done, pending = await asyncio.wait(
                        {get_task, shutdown_task},
                        timeout=30.0,
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
