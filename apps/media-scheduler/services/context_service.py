"""Context subscription service — SSE client for real-time context updates.

Connects to the platform's ``GET /api/context/stream`` SSE endpoint and
triggers plan re-generation when context changes.  Handles:

- SSE text-protocol parsing (event + data fields)
- Debounced re-evaluation (120 s default; immediate for location_zone changes)
- Exponential-backoff reconnection on connection loss (max 300 s)
- Concurrent-generation protection via ``asyncio.Lock``

Lifecycle:
- ``start_context_listener(ctx)`` — spawns the background SSE listener task
- ``stop_context_listener()`` — cancels listener + any pending debounce
- ``get_context_subscription_status()`` — inspection surface for agents/health

Constants:
- ``DEBOUNCE_SECONDS`` — default debounce window (120 s)
- ``MAX_BACKOFF_SECONDS`` — reconnect backoff ceiling (300 s)
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("context_service")

# ── Import generate_plan (same importlib fallback as other services) ──

try:
    from services.plan_service import generate_plan
except ModuleNotFoundError:
    import importlib.util as _ilu
    import pathlib as _pl

    _psvc = _pl.Path(__file__).resolve().parent / "plan_service.py"
    _psp = _ilu.spec_from_file_location("_plan_service_ctx_fallback", _psvc)
    _pfm = _ilu.module_from_spec(_psp)
    _psp.loader.exec_module(_pfm)
    generate_plan = _pfm.generate_plan


# ── Constants ──

DEBOUNCE_SECONDS: float = 120.0
MAX_BACKOFF_SECONDS: float = 300.0


# ── Module-level state ──

_listener_task: asyncio.Task | None = None
_debounce_task: asyncio.Task | None = None
_last_context: dict[str, Any] = {}
_prev_context: dict[str, Any] = {}
_plan_lock: asyncio.Lock | None = None
_reconnect_count: int = 0
_last_event_at: str | None = None
_connected: bool = False


# ── SSE parsing ──


def parse_sse_lines(lines: list[str]) -> tuple[str | None, dict | None]:
    """Extract event type and JSON data from SSE text lines.

    Follows the SSE wire format:
    - ``event: <type>`` sets the event type
    - ``data: <json>`` sets the data payload
    - Lines starting with ``:`` are comments (ignored)
    - Empty lines are event terminators (ignored here since we
      receive a batch of lines for one event)

    Returns:
        Tuple of ``(event_type, parsed_data)`` or ``(None, None)``
        if the lines don't form a complete event.
    """
    event_type: str | None = None
    data_parts: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(":"):
            continue
        if stripped.startswith("event:"):
            event_type = stripped[len("event:"):].strip()
        elif stripped.startswith("data:"):
            data_parts.append(stripped[len("data:"):].strip())

    if not data_parts:
        return (None, None)

    raw_data = "\n".join(data_parts)
    try:
        parsed = json.loads(raw_data)
    except (json.JSONDecodeError, ValueError):
        logger.warning("context_service.sse_parse_error raw=%s", raw_data[:200])
        return (event_type, None)

    return (event_type, parsed)


# ── Event handling ──


async def _on_context_event(ctx: Any, context_data: dict) -> None:
    """Handle an incoming context_update event.

    - Stores latest context in module state
    - If ``location_zone`` changed → trigger immediate regeneration
    - Otherwise → start/restart the debounce timer
    """
    global _last_context, _prev_context, _debounce_task

    _prev_context = _last_context.copy()
    _last_context = context_data

    # Detect location_zone change (immediate trigger per D349)
    old_zone = _prev_context.get("location_zone")
    new_zone = context_data.get("location_zone")

    if new_zone is not None and new_zone != old_zone:
        logger.info(
            "context_service.location_zone_changed old=%s new=%s — immediate regeneration",
            old_zone,
            new_zone,
        )
        # Cancel any pending debounce
        if _debounce_task is not None and not _debounce_task.done():
            _debounce_task.cancel()
            _debounce_task = None
            logger.debug("context_service.debounce_cancelled reason=location_zone_change")
        await _trigger_regeneration(ctx)
        return

    # Non-location change → debounce
    if _debounce_task is not None and not _debounce_task.done():
        _debounce_task.cancel()
        logger.debug("context_service.debounce_restarted")
    _debounce_task = asyncio.create_task(_debounce_regenerate(ctx))


async def _debounce_regenerate(ctx: Any) -> None:
    """Wait for the debounce window then trigger plan regeneration."""
    try:
        await asyncio.sleep(DEBOUNCE_SECONDS)
        logger.info("context_service.debounce_fired after=%.0fs", DEBOUNCE_SECONDS)
        await _trigger_regeneration(ctx)
    except asyncio.CancelledError:
        logger.debug("context_service.debounce_cancelled")
        raise


async def _trigger_regeneration(ctx: Any) -> None:
    """Acquire the plan lock and call generate_plan with current context."""
    global _plan_lock

    if _plan_lock is None:
        _plan_lock = asyncio.Lock()

    if _plan_lock.locked():
        logger.warning("context_service.plan_lock_contention — generation already in progress")

    async with _plan_lock:
        try:
            logger.info(
                "context_service.plan_generation_started context_keys=%s",
                list(_last_context.keys()),
            )
            result = await generate_plan(ctx, context_override=_last_context)
            logger.info(
                "context_service.plan_generation_completed plan_iri=%s entries=%s",
                result.get("plan_iri", "?"),
                result.get("entries_created", "?"),
            )
        except Exception:
            logger.error(
                "context_service.plan_generation_failed",
                exc_info=True,
            )


# ── SSE listener with reconnect ──


async def _listen_sse(ctx: Any) -> None:
    """Connect to the platform SSE stream and dispatch context events.

    On connection error: log, increment reconnect counter, sleep with
    exponential backoff (max 300 s), and retry.  Resets reconnect
    counter on successful connection.
    """
    global _reconnect_count, _connected, _last_event_at

    while True:
        try:
            client = ctx._get_platform_client()
            logger.info("context_service.sse_connecting url=/api/context/stream")

            async with client.stream("GET", "/api/context/stream") as response:
                _connected = True
                _reconnect_count = 0
                logger.info("context_service.sse_connected status=%d", response.status_code)

                event_lines: list[str] = []
                async for raw_line in response.aiter_lines():
                    line = raw_line.strip()

                    if line == "":
                        # Blank line = event boundary
                        if event_lines:
                            event_type, data = parse_sse_lines(event_lines)
                            if event_type == "context_update" and data is not None:
                                _last_event_at = datetime.now(timezone.utc).isoformat()
                                await _on_context_event(ctx, data)
                            event_lines = []
                        continue

                    # Skip keepalive comments
                    if line.startswith(":"):
                        continue

                    event_lines.append(line)

        except asyncio.CancelledError:
            _connected = False
            logger.info("context_service.sse_cancelled")
            raise

        except Exception as exc:
            _connected = False
            _reconnect_count += 1
            backoff = min(2 ** _reconnect_count, MAX_BACKOFF_SECONDS)
            logger.warning(
                "context_service.sse_connection_error error=%s reconnect_count=%d backoff=%.0fs",
                str(exc)[:200],
                _reconnect_count,
                backoff,
            )
            await asyncio.sleep(backoff)


# ── Lifecycle management ──


def start_context_listener(ctx: Any) -> asyncio.Task:
    """Spawn the background SSE listener task.

    Creates the plan lock if it doesn't exist yet.  Returns the
    asyncio.Task so the caller can optionally await or cancel it.
    """
    global _listener_task, _plan_lock

    if _plan_lock is None:
        _plan_lock = asyncio.Lock()

    _listener_task = asyncio.create_task(_listen_sse(ctx), name="context_sse_listener")
    logger.info("context_service.listener_started")
    return _listener_task


def stop_context_listener() -> None:
    """Cancel the SSE listener and any pending debounce timer.

    Resets all module-level state to initial values.
    """
    global _listener_task, _debounce_task, _connected
    global _last_context, _prev_context, _reconnect_count, _last_event_at

    if _listener_task is not None and not _listener_task.done():
        _listener_task.cancel()
        logger.info("context_service.listener_cancelled")
    _listener_task = None

    if _debounce_task is not None and not _debounce_task.done():
        _debounce_task.cancel()
        logger.debug("context_service.debounce_cancelled reason=stop")
    _debounce_task = None

    _connected = False
    _last_context = {}
    _prev_context = {}
    _reconnect_count = 0
    _last_event_at = None


def get_context_subscription_status() -> dict[str, Any]:
    """Return current SSE subscription state for inspection.

    Returns:
        Dict with keys: ``connected``, ``last_event_at``,
        ``debounce_pending``, ``reconnect_count``.
    """
    return {
        "connected": _connected,
        "last_event_at": _last_event_at,
        "debounce_pending": (
            _debounce_task is not None and not _debounce_task.done()
        ),
        "reconnect_count": _reconnect_count,
    }
