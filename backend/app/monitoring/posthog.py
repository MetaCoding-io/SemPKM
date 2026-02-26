"""PostHog analytics and error monitoring integration.

Provides initialization, shutdown, and helper functions for capturing
events and exceptions to PostHog from the FastAPI backend.
"""

import logging
import traceback

import posthog

from app.config import settings

logger = logging.getLogger(__name__)

_enabled = False


def init_posthog() -> None:
    """Initialize the PostHog client if enabled and an API key is configured."""
    global _enabled
    if not settings.posthog_enabled:
        logger.info("PostHog disabled via POSTHOG_ENABLED flag")
        return
    if not settings.posthog_api_key:
        logger.warning("PostHog enabled but POSTHOG_API_KEY not set — skipping")
        return

    posthog.api_key = settings.posthog_api_key
    posthog.host = settings.posthog_host
    _enabled = True
    logger.info("PostHog initialized (host=%s)", settings.posthog_host)


def shutdown_posthog() -> None:
    """Flush pending events and shut down the PostHog client."""
    if _enabled:
        posthog.shutdown()
        logger.info("PostHog client shut down")


def is_enabled() -> bool:
    """Return True if PostHog is initialized and active."""
    return _enabled


def capture_event(
    distinct_id: str,
    event: str,
    properties: dict | None = None,
) -> None:
    """Capture a named event in PostHog.

    Args:
        distinct_id: User or system identifier.
        event: Event name (e.g. "command_executed").
        properties: Optional dict of event properties.
    """
    if not _enabled:
        return
    posthog.capture(distinct_id, event, properties=properties or {})


def capture_exception(
    exc: Exception,
    *,
    distinct_id: str = "backend",
    context: dict | None = None,
) -> None:
    """Capture an exception as a PostHog event with full traceback.

    Args:
        exc: The exception to report.
        distinct_id: User or system identifier.
        context: Additional context properties (endpoint, method, etc.).
    """
    if not _enabled:
        return

    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    properties = {
        "$exception_type": type(exc).__name__,
        "$exception_message": str(exc),
        "$exception_stack_trace_raw": "".join(tb),
        "$exception_source": "backend",
        **(context or {}),
    }
    posthog.capture(distinct_id, "$exception", properties=properties)
