"""Linear Sync app — two-way sync between SemPKM objects and Linear issues.

Routes:
- /_fragments/connect          GET   — settings page connect form
- /_fragments/connect/api-key  POST  — authenticate via API key
- /_fragments/oauth-callback   GET   — OAuth callback handler
- /_fragments/connect/disconnect POST — disconnect and clear credentials
"""

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
import logging

logger = logging.getLogger("linear_sync")

linear_sync_app = App("linear-sync")


@linear_sync_app.route("/_fragments/connect")
async def connect_fragment(request: Request):
    """Render the connect/settings page fragment."""
    ctx: AppContext = request.app.state.ctx
    return HTMLResponse(ctx.render_template("connect.html"))


@linear_sync_app.route("/_fragments/connect/api-key", methods=["POST"])
async def connect_api_key(request: Request):
    """Authenticate with Linear using an API key."""
    return JSONResponse(
        {"detail": "API key authentication not yet implemented"},
        status_code=501,
    )


@linear_sync_app.route("/_fragments/oauth-callback")
async def oauth_callback(request: Request):
    """Handle Linear OAuth callback."""
    return JSONResponse(
        {"detail": "OAuth callback not yet implemented"},
        status_code=501,
    )


@linear_sync_app.route("/_fragments/connect/disconnect", methods=["POST"])
async def disconnect(request: Request):
    """Disconnect from Linear and clear stored credentials."""
    return JSONResponse(
        {"detail": "Disconnect not yet implemented"},
        status_code=501,
    )


@linear_sync_app.task("poll-tasks")
def poll_tasks(ctx: AppContext):
    """Poll Linear for updated issues and sync changes to SemPKM."""
    logger.info("poll-tasks executed for %s (not yet implemented)", ctx.app_id)
    return {"status": "noop", "reason": "sync not yet implemented"}


@linear_sync_app.on_startup
def on_startup(ctx: AppContext):
    logger.info("Linear Sync app started: %s", ctx.app_id)


@linear_sync_app.on_shutdown
def on_shutdown(ctx: AppContext):
    logger.info("Linear Sync app stopped: %s", ctx.app_id)
