"""ETag conditional GET middleware for JSON API responses.

Computes weak ETags on GET responses to /api/ and /.well-known/ paths
with application/json content type.  Returns 304 Not Modified when the
client sends a matching If-None-Match header.

Delivers requirement PERF-09 (backend cache headers).
"""

import hashlib
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, StreamingResponse

logger = logging.getLogger(__name__)

# Responses larger than 1 MB are excluded from ETag computation to avoid
# excessive hashing cost and memory pressure.
_MAX_BODY_SIZE = 1_048_576  # 1 MB


class ConditionalGetMiddleware(BaseHTTPMiddleware):
    """Middleware that adds ETag headers and handles conditional GET (304)."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Only process GET requests
        if request.method != "GET":
            return await call_next(request)

        # Only process API and well-known paths
        path = request.url.path
        if not (path.startswith("/api/") or path.startswith("/.well-known/")):
            return await call_next(request)

        response = await call_next(request)

        # Skip streaming responses — body can't be read synchronously
        if isinstance(response, StreamingResponse):
            return response

        # Skip non-JSON responses
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Read the response body (consumes the body_iterator)
        body = b"".join([chunk async for chunk in response.body_iterator])

        # Skip large responses — rebuild response without ETag
        if len(body) > _MAX_BODY_SIZE:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        # Compute weak ETag from SHA-256 of body
        hash_hex = hashlib.sha256(body).hexdigest()[:16]
        etag = f'W/"{hash_hex}"'

        # Check If-None-Match header
        if_none_match = request.headers.get("if-none-match")
        if if_none_match is not None and (if_none_match == etag or if_none_match == "*"):
            return Response(
                status_code=304,
                headers={
                    "ETag": etag,
                    "Cache-Control": "no-cache",
                    "Vary": "Accept, Authorization",
                },
            )

        # Build new response with ETag headers (original body_iterator is consumed)
        new_response = Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
        new_response.headers["ETag"] = etag
        new_response.headers["Cache-Control"] = "no-cache"
        new_response.headers["Vary"] = "Accept, Authorization"

        return new_response
