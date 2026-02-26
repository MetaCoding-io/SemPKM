"""PostHog error-capturing middleware for FastAPI.

Intercepts unhandled exceptions during request processing and reports
them to PostHog with request context (method, path, user). Expected
HTTP errors (4xx) are not reported — only genuine 5xx server errors.
"""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse

from app.monitoring.posthog import capture_exception, is_enabled

logger = logging.getLogger(__name__)


class PostHogErrorMiddleware(BaseHTTPMiddleware):
    """Middleware that captures unhandled exceptions to PostHog."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not is_enabled():
            return await call_next(request)

        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Extract user identifier if available from auth cookie
            distinct_id = "anonymous"
            try:
                session_token = request.cookies.get("sempkm_session")
                if session_token:
                    distinct_id = f"session:{session_token[:8]}"
            except Exception:
                pass

            context = {
                "request_method": request.method,
                "request_path": request.url.path,
                "request_query": str(request.url.query),
            }

            capture_exception(exc, distinct_id=distinct_id, context=context)
            logger.exception("Unhandled exception captured by PostHog middleware")
            raise
