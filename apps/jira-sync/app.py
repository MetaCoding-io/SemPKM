"""Jira Sync app — two-way sync between SemPKM objects and Jira issues.

Routes:
- /_fragments/connect                  GET   — settings page connect form or status
- /_fragments/connect/credentials      POST  — authenticate via email + token + site_url
- /_fragments/connect/disconnect       POST  — disconnect and clear credentials
- /_fragments/settings/projects        POST  — save selected project keys
- /_fragments/settings/sync-config     POST  — save sync direction and poll interval
- /_fragments/settings/sync-now        POST  — trigger immediate sync (placeholder until S02)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse

from services.jira_client import JiraClient, JiraAuthError, JiraAPIError
from services.auth import (
    store_credentials,
    get_credentials,
    get_connection_status,
    clear_credentials,
)

logger = logging.getLogger("jira_sync")

jira_sync_app = App("jira-sync")


def _make_client(ctx: AppContext) -> JiraClient:
    """Create a JiraClient wired to the app's HTTP and state clients."""
    return JiraClient(
        http_client=ctx.http,
        state_client=ctx.state,
    )


async def _render_connect_status(ctx: AppContext) -> HTMLResponse:
    """Render connect_status.html with full sync state.

    Reads projects from Jira API plus all sync state keys, and passes
    them as template variables.  Shared by connect_fragment and the
    settings POST routes so every re-render is consistent.
    """
    client = _make_client(ctx)
    status = await get_connection_status(ctx.state, client)

    projects: list[dict] = []
    try:
        projects = await client.get_projects()
    except Exception as exc:
        logger.warning("Failed to fetch projects for connected account: %s", exc)

    # Read sync state
    selected_projects_json = await ctx.settings.get("selected_projects")
    selected_projects = json.loads(selected_projects_json) if selected_projects_json else []
    sync_direction = await ctx.settings.get("sync_direction") or "pull-only"
    poll_interval = await ctx.settings.get("poll_interval") or "15m"
    jql_filter = await ctx.settings.get("jql_filter") or ""
    last_sync_at = await ctx.state.get("last_sync_at") or ""

    # Parse last pull result
    last_pull_json = await ctx.state.get("last_pull_result")
    last_pull_result = json.loads(last_pull_json) if last_pull_json else None

    # Parse last push result
    last_push_json = await ctx.state.get("last_push_result")
    last_push_result = json.loads(last_push_json) if last_push_json else None

    return HTMLResponse(ctx.render_template(
        "connect_status.html",
        email=status.get("email", ""),
        display_name=status.get("display_name", ""),
        token_preview=status.get("token_preview", ""),
        site_url=status.get("site_url", ""),
        projects=projects,
        selected_projects=selected_projects,
        sync_direction=sync_direction,
        poll_interval=poll_interval,
        jql_filter=jql_filter,
        last_sync_at=last_sync_at,
        last_pull_result=last_pull_result,
        last_push_result=last_push_result,
    ))


@jira_sync_app.route("/_fragments/connect")
async def connect_fragment(request: Request):
    """Render the connect/settings page fragment.

    If connected: fetch projects and sync state, render full settings panel.
    If disconnected or on error: render connect form.
    """
    ctx: AppContext = request.app.state.ctx
    client = _make_client(ctx)
    status = await get_connection_status(ctx.state, client)

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


@jira_sync_app.route("/_fragments/connect/credentials", methods=["POST"])
async def connect_credentials(request: Request):
    """Authenticate with Jira using email + API token + site URL.

    Reads email, token, site_url from the form body, stores them,
    verifies via GET /rest/api/3/myself, and returns the connected
    status fragment.
    """
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    email = form.get("email", "").strip()
    token = form.get("token", "").strip()
    site_url = form.get("site_url", "").strip()

    if not email or not token or not site_url:
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error="Email, API token, and site URL are all required.",
        ))

    # Normalize site_url to include protocol
    if not site_url.startswith("http"):
        site_url = f"https://{site_url}"
    site_url = site_url.rstrip("/")

    try:
        # Store credentials first so JiraClient can find them
        await store_credentials(ctx.state, email, token, site_url)

        client = _make_client(ctx)
        user = await client.get_myself()
        logger.info(
            "Jira credentials verified for user: %s (%s)",
            user.get("displayName", "unknown"),
            user.get("emailAddress", "unknown"),
        )

        response = await _render_connect_status(ctx)
        response.headers["HX-Trigger"] = "jiraConnected"
        return response

    except (JiraAuthError, JiraAPIError, Exception) as exc:
        logger.warning("Jira credential verification failed: %s", exc)
        # Clear the invalid credentials
        await clear_credentials(ctx.state)
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error="Could not connect to Jira. Please check your email, token, and site URL.",
        ))


@jira_sync_app.route("/_fragments/settings/projects", methods=["POST"])
async def save_projects(request: Request):
    """Save selected project keys for sync."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    project_keys = form.getlist("project_keys")
    await ctx.settings.set("selected_projects", json.dumps(project_keys))
    logger.info("Saved sync projects: %s", project_keys)
    return await _render_connect_status(ctx)


@jira_sync_app.route("/_fragments/settings/sync-config", methods=["POST"])
async def save_sync_config(request: Request):
    """Save sync direction, poll interval, and JQL filter settings."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    sync_direction = form.get("sync_direction", "pull-only")
    poll_interval = form.get("poll_interval", "15m")
    jql_filter = form.get("jql_filter", "").strip()
    await ctx.settings.set("sync_direction", sync_direction)
    await ctx.settings.set("poll_interval", poll_interval)
    await ctx.settings.set("jql_filter", jql_filter)
    logger.info(
        "Saved sync config: direction=%s interval=%s jql=%s",
        sync_direction, poll_interval, jql_filter or "(none)",
    )
    return await _render_connect_status(ctx)


@jira_sync_app.route("/_fragments/settings/sync-now", methods=["POST"])
async def sync_now(request: Request):
    """Trigger an immediate pull + push sync."""
    from services.sync_engine import pull_sync, push_sync

    ctx: AppContext = request.app.state.ctx
    logger.info("Manual sync triggered")

    try:
        pull_result = await pull_sync(ctx)
        await ctx.state.set("last_pull_result", json.dumps(pull_result))
    except Exception as exc:
        logger.error("Manual pull sync failed: %s", exc, exc_info=True)
        pull_result = {"status": "error", "message": str(exc)}
        await ctx.state.set("last_pull_result", json.dumps(pull_result))

    sync_direction = await ctx.settings.get("sync_direction") or "pull-only"
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


@jira_sync_app.route("/_fragments/connect/disconnect", methods=["POST"])
async def disconnect_handler(request: Request):
    """Disconnect from Jira and clear stored credentials."""
    ctx: AppContext = request.app.state.ctx
    await clear_credentials(ctx.state)
    logger.info("Disconnected from Jira")
    return HTMLResponse(ctx.render_template("connect.html", error=None))


@jira_sync_app.task("poll-tasks")
async def poll_tasks(ctx: AppContext):
    """Poll Jira for updated issues and sync changes to SemPKM."""
    from services.sync_engine import pull_sync

    logger.info("poll-tasks: starting pull sync")
    try:
        result = await pull_sync(ctx)
        logger.info("poll-tasks: completed — %s", result)
        return result
    except Exception as exc:
        logger.error("poll-tasks: sync failed — %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}


@jira_sync_app.task("push-changes")
async def push_changes(ctx: AppContext):
    """Push local task changes back to Jira."""
    from services.sync_engine import push_sync

    logger.info("push-changes: starting push sync")
    try:
        result = await push_sync(ctx)
        logger.info("push-changes: completed — %s", result)
        return result
    except Exception as exc:
        logger.error("push-changes: push failed — %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}


@jira_sync_app.on_startup
def on_startup(ctx: AppContext):
    logger.info("Jira Sync app started: %s", ctx.app_id)


@jira_sync_app.on_shutdown
def on_shutdown(ctx: AppContext):
    logger.info("Jira Sync app stopped: %s", ctx.app_id)
