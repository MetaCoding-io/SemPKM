"""Todoist Sync app — two-way sync between SemPKM tasks and Todoist.

Routes:
- /_fragments/connect              GET   — settings page connect form or status
- /_fragments/connect/api-token    POST  — authenticate via Todoist API token
- /_fragments/disconnect           POST  — disconnect and clear credentials
- /_fragments/projects             GET   — fetch projects and render checkboxes
- /_fragments/projects             POST  — save selected project IDs
- /_fragments/settings/sync-config POST  — save sync direction and poll interval
- /_fragments/settings/sync-now    POST  — trigger immediate pull+push sync
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse

from services.auth import (
    store_token,
    verify_token,
    get_connection_status,
    clear_credentials,
    TodoistAuthError,
)
from services.todoist_client import TodoistClient

logger = logging.getLogger("todoist.sync")

todoist_sync_app = App("todoist-sync")


def _make_client(ctx: AppContext) -> TodoistClient:
    """Create a TodoistClient wired to the app's HTTP and state clients."""
    return TodoistClient(http_client=ctx.http, state_client=ctx.state)


async def _render_connect_status(ctx: AppContext) -> HTMLResponse:
    """Render connect_status.html with connection state and sync stats.

    Reads token status, selected projects, sync settings, and last
    pull/push results, then passes all template variables.
    Shared by multiple routes.
    """
    status = await get_connection_status(ctx.state, ctx.http)

    # Read selected projects
    selected_json = await ctx.state.get("selected_projects")
    selected_projects = json.loads(selected_json) if selected_json else []

    # Read last pull result
    last_pull_json = await ctx.state.get("last_pull_result")
    last_pull_result = json.loads(last_pull_json) if last_pull_json else None

    # Read sync settings
    sync_direction = await ctx.settings.get("sync_direction") or "pull-only"
    poll_interval = await ctx.settings.get("poll_interval") or "15m"
    last_sync_at = await ctx.state.get("last_sync_at") or ""

    # Read last push result
    last_push_json = await ctx.state.get("last_push_result")
    last_push_result = json.loads(last_push_json) if last_push_json else None

    return HTMLResponse(ctx.render_template(
        "connect_status.html",
        connected=status["connected"],
        token_preview=status.get("token_preview", ""),
        projects_count=status.get("projects_count", 0),
        selected_projects=selected_projects,
        last_pull_result=last_pull_result,
        sync_direction=sync_direction,
        poll_interval=poll_interval,
        last_sync_at=last_sync_at,
        last_push_result=last_push_result,
    ))


@todoist_sync_app.route("/_fragments/connect")
async def connect_fragment(request: Request):
    """Render the connect/settings page fragment.

    If connected: render status panel with masked token and project count.
    If disconnected or on error: render connect form.
    """
    ctx: AppContext = request.app.state.ctx
    status = await get_connection_status(ctx.state, ctx.http)

    if status["connected"]:
        try:
            return await _render_connect_status(ctx)
        except Exception as exc:
            logger.warning("Failed to render status for connected account: %s", exc)
            return HTMLResponse(ctx.render_template(
                "connect.html",
                error=f"Connection error: {exc}. Please reconnect.",
            ))

    return HTMLResponse(ctx.render_template("connect.html", error=None))


@todoist_sync_app.route("/_fragments/connect/api-token", methods=["POST"])
async def connect_api_token(request: Request):
    """Authenticate with Todoist using an API token.

    Reads token from the form body, stores it, verifies via
    GET /rest/v2/projects, and returns the connected status fragment.
    """
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    token = form.get("token", "").strip()

    if not token:
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error="API token is required.",
        ))

    try:
        # Store the token first so subsequent calls can find it
        await store_token(ctx.state, token)

        # Verify the token by fetching projects
        result = await verify_token(ctx.http, token)
        logger.info(
            "Token verified — %d projects found",
            result["projects_count"],
        )

        response = await _render_connect_status(ctx)
        response.headers["HX-Trigger"] = "todoistConnected"
        return response

    except (TodoistAuthError, Exception) as exc:
        logger.warning("Token verification failed: %s", exc)
        # Clear the invalid token
        await clear_credentials(ctx.state)
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error="Invalid token. Please check and try again.",
        ))


@todoist_sync_app.route("/_fragments/disconnect", methods=["POST"])
async def disconnect_handler(request: Request):
    """Disconnect from Todoist and clear stored credentials."""
    ctx: AppContext = request.app.state.ctx
    await clear_credentials(ctx.state)
    logger.info("Disconnected from Todoist")
    return HTMLResponse(ctx.render_template("connect.html", error=None))


@todoist_sync_app.route("/_fragments/projects", methods=["GET"])
async def get_projects(request: Request):
    """Fetch projects from Todoist and render checkboxes.

    Returns an HTML fragment with checkboxes for each project,
    pre-checked based on current selection in state.
    """
    ctx: AppContext = request.app.state.ctx
    client = _make_client(ctx)

    try:
        projects = await client.get_projects()
    except Exception as exc:
        logger.warning("Failed to fetch projects: %s", exc)
        return HTMLResponse(
            '<p class="error-text">Failed to load projects. Please try again.</p>'
        )

    # Read current selection
    selected_json = await ctx.state.get("selected_projects")
    selected_ids = json.loads(selected_json) if selected_json else []

    return HTMLResponse(ctx.render_template(
        "projects.html",
        projects=projects,
        selected_ids=selected_ids,
    ))


@todoist_sync_app.route("/_fragments/projects", methods=["POST"])
async def save_projects(request: Request):
    """Save selected project IDs to state."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    project_ids = form.getlist("project_ids")
    await ctx.state.set("selected_projects", json.dumps(project_ids))
    logger.info("Saved sync projects: %s", project_ids)
    return await _render_connect_status(ctx)


@todoist_sync_app.route("/_fragments/settings/sync-config", methods=["POST"])
async def save_sync_config(request: Request):
    """Save sync direction and poll interval settings."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    sync_direction = form.get("sync_direction", "pull-only")
    poll_interval = form.get("poll_interval", "15m")
    await ctx.settings.set("sync_direction", sync_direction)
    await ctx.settings.set("poll_interval", poll_interval)
    logger.info("Saved sync config: direction=%s interval=%s", sync_direction, poll_interval)
    return await _render_connect_status(ctx)


@todoist_sync_app.route("/_fragments/settings/sync-now", methods=["POST"])
async def sync_now(request: Request):
    """Trigger an immediate pull + push sync."""
    from services.sync_engine import pull_sync, push_sync

    ctx: AppContext = request.app.state.ctx
    logger.info("Manual sync triggered")

    try:
        result = await pull_sync(ctx)
        await ctx.state.set("last_pull_result", json.dumps(result))
    except Exception as exc:
        logger.error("Manual pull sync failed: %s", exc, exc_info=True)
        result = {
            "status": "error",
            "message": str(exc),
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "errors": 1,
            "error_details": [{"error": str(exc)}],
            "duration_ms": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await ctx.state.set("last_pull_result", json.dumps(result))

    sync_direction = await ctx.settings.get("sync_direction")
    if sync_direction == "bidirectional":
        try:
            push_result = await push_sync(ctx)
            await ctx.state.set("last_push_result", json.dumps(push_result))
        except Exception as exc:
            logger.error("Manual push sync failed: %s", exc, exc_info=True)
            push_result = {"status": "error", "message": str(exc)}
            await ctx.state.set("last_push_result", json.dumps(push_result))

    await ctx.state.set("last_sync_at", datetime.now(timezone.utc).isoformat())
    return await _render_connect_status(ctx)


@todoist_sync_app.task("poll-tasks")
async def poll_tasks(ctx: AppContext):
    """Poll Todoist for updated tasks and sync changes to SemPKM."""
    from services.sync_engine import pull_sync

    logger.info("poll-tasks: starting pull sync")
    try:
        result = await pull_sync(ctx)
        logger.info("poll-tasks: completed — %s", result)
        return result
    except Exception as exc:
        logger.error("poll-tasks: sync failed — %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}


@todoist_sync_app.task("push-changes")
async def push_changes(ctx: AppContext):
    """Push local task changes back to Todoist."""
    from services.sync_engine import push_sync

    logger.info("push-changes: starting push sync")
    try:
        result = await push_sync(ctx)
        logger.info("push-changes: completed — %s", result)
        return result
    except Exception as exc:
        logger.error("push-changes: push failed — %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}


@todoist_sync_app.on_startup
def on_startup(ctx: AppContext):
    logger.info("Todoist Sync app started: %s", ctx.app_id)


@todoist_sync_app.on_shutdown
def on_shutdown(ctx: AppContext):
    logger.info("Todoist Sync app stopped: %s", ctx.app_id)
