"""FastAPI router for app proxy forwarding and token renewal.

Exposes:
- ``ANY /app/{app_id}/{path:path}`` — catch-all proxy to app subprocesses
- ``POST /api/apps/{app_id}/token/renew`` — JWT token renewal with grace period
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.apps.proxy import AppNotReachableError
from app.apps.tokens import generate_app_token, get_app_secret, validate_app_token

logger = logging.getLogger(__name__)

app_proxy_router = APIRouter(tags=["app-proxy"])


@app_proxy_router.api_route(
    "/app/{app_id}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
async def proxy_to_app(app_id: str, path: str, request: Request):
    """Forward any HTTP request to the app subprocess via UDS proxy.

    Returns 503 if the app is not in 'running' status.
    Returns 502 if the app's socket is unreachable.
    """
    manager = request.app.state.app_manager
    proxy = request.app.state.app_proxy

    # Check app is running
    try:
        status = await manager.get_status(app_id)
    except ValueError:
        return JSONResponse(
            status_code=404,
            content={"detail": f"App {app_id} not found"},
        )

    if status["status"] != "running":
        return JSONResponse(
            status_code=503,
            content={"detail": f"App {app_id} is not running"},
        )

    try:
        return await proxy.forward(app_id, path, request)
    except AppNotReachableError:
        return JSONResponse(
            status_code=502,
            content={"detail": f"App {app_id} not reachable"},
        )


@app_proxy_router.post("/api/apps/{app_id}/token/renew")
async def renew_app_token(app_id: str, request: Request):
    """Renew a JWT token for an app subprocess.

    The app presents its current (possibly recently-expired) token in the
    ``Authorization: Bearer {token}`` header.  If valid (or within 300s
    grace), a fresh token is generated and returned.
    """
    manager = request.app.state.app_manager

    # Extract bearer token
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "Missing or malformed Authorization header"},
        )

    old_token = auth_header[len("Bearer "):]
    secret = get_app_secret(app_id)

    # Validate with 300s grace period for renewal
    claims = validate_app_token(old_token, secret, grace_seconds=300)
    if claims is None:
        return JSONResponse(
            status_code=401,
            content={"detail": "Token expired beyond grace period or invalid"},
        )

    # Generate fresh token
    permissions = claims.get("permissions", {})
    new_token = generate_app_token(app_id, permissions, secret)

    # Store in manager's token dict
    manager._tokens[app_id] = new_token

    logger.debug("Token renewed for app %s", app_id)
    return JSONResponse(
        status_code=200,
        content={"token": new_token},
    )
