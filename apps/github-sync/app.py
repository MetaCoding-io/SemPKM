"""GitHub Sync app — pull sync between SemPKM objects and GitHub issues.

Routes:
- /_fragments/connect          GET   — settings page connect form or status
- /_fragments/connect/api-key  POST  — authenticate via PAT
- /_fragments/connect/disconnect POST — disconnect and clear credentials
- /_fragments/settings/repos   POST  — save selected repositories
- /_fragments/settings/sync-now POST — trigger immediate pull sync
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse

from services.github_client import GitHubClient, GitHubAuthError, GitHubAPIError
from services.auth import (
    store_pat,
    verify_pat,
    get_connection_status,
    disconnect,
)

logger = logging.getLogger("github_sync")

github_sync_app = App("github-sync")


def _make_client(ctx: AppContext) -> GitHubClient:
    """Create a GitHubClient wired to the app's HTTP and state clients."""
    return GitHubClient(
        http_client=ctx.http,
        state_client=ctx.state,
    )


async def _render_connect_status(ctx: AppContext) -> HTMLResponse:
    """Render connect_status.html with full sync state.

    Reads repos from GitHub API plus all sync state keys, and passes
    them as template variables.  Shared by connect_fragment and the
    settings POST routes so every re-render is consistent.
    """
    client = _make_client(ctx)
    status = await get_connection_status(ctx.state, client)

    repos: list[dict] = []
    try:
        repos = await client.fetch_repos()
    except Exception as exc:
        logger.warning("Failed to fetch repos for connected account: %s", exc)

    # Read sync state
    selected_repos_json = await ctx.settings.get("selected_repos")
    selected_repos = json.loads(selected_repos_json) if selected_repos_json else []
    last_sync_at = await ctx.state.get("last_sync_at") or ""

    # Parse last pull result
    last_pull_json = await ctx.state.get("last_pull_result")
    last_pull_result = json.loads(last_pull_json) if last_pull_json else None

    return HTMLResponse(ctx.render_template(
        "connect_status.html",
        username=status.get("username", ""),
        pat_preview=status.get("pat_preview", ""),
        repos=repos,
        selected_repos=selected_repos,
        last_sync_at=last_sync_at,
        last_pull_result=last_pull_result,
    ))


@github_sync_app.route("/_fragments/connect")
async def connect_fragment(request: Request):
    """Render the connect/settings page fragment.

    If connected: fetch repos and sync state, render full settings panel.
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


@github_sync_app.route("/_fragments/connect/api-key", methods=["POST"])
async def connect_api_key(request: Request):
    """Authenticate with GitHub using a Personal Access Token.

    Reads pat from the form body, stores it, verifies via GET /user,
    and returns the connected status fragment.
    """
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    pat = form.get("pat", "").strip()

    if not pat:
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error="Personal Access Token is required.",
        ))

    try:
        # Store the PAT first so GitHubClient can find it
        await store_pat(ctx.state, pat)

        client = _make_client(ctx)
        user = await verify_pat(client)
        logger.info("PAT verified for user: %s", user.get("login", "unknown"))

        response = await _render_connect_status(ctx)
        response.headers["HX-Trigger"] = "githubConnected"
        return response

    except (GitHubAuthError, Exception) as exc:
        logger.warning("PAT verification failed: %s", exc)
        # Clear the invalid PAT
        await disconnect(ctx.state)
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error="Invalid token. Please check and try again.",
        ))


@github_sync_app.route("/_fragments/settings/repos", methods=["POST"])
async def save_repos(request: Request):
    """Save selected repository full names for sync."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    repo_names = form.getlist("repo_names")
    await ctx.settings.set("selected_repos", json.dumps(repo_names))
    logger.info("Saved sync repos: %s", repo_names)
    return await _render_connect_status(ctx)


@github_sync_app.route("/_fragments/settings/sync-now", methods=["POST"])
async def sync_now(request: Request):
    """Trigger an immediate pull sync."""
    from services.sync_engine import pull_sync

    ctx: AppContext = request.app.state.ctx
    logger.info("Manual sync triggered")

    try:
        result = await pull_sync(ctx)
    except Exception as exc:
        logger.error("Manual pull sync failed: %s", exc, exc_info=True)
        result = {
            "status": "error",
            "message": str(exc),
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 1,
            "failed_issues": [],
            "duration_ms": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await ctx.state.set("last_pull_result", json.dumps(result))

    return await _render_connect_status(ctx)


@github_sync_app.route("/_fragments/connect/disconnect", methods=["POST"])
async def disconnect_handler(request: Request):
    """Disconnect from GitHub and clear stored credentials."""
    ctx: AppContext = request.app.state.ctx
    await disconnect(ctx.state)
    logger.info("Disconnected from GitHub")
    return HTMLResponse(ctx.render_template("connect.html", error=None))


@github_sync_app.task("poll-tasks")
async def poll_tasks(ctx: AppContext):
    """Poll GitHub for updated issues and sync changes to SemPKM."""
    from services.sync_engine import pull_sync

    logger.info("poll-tasks: starting pull sync")
    try:
        result = await pull_sync(ctx)
        logger.info("poll-tasks: completed — %s", result)
        return result
    except Exception as exc:
        logger.error("poll-tasks: sync failed — %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}


@github_sync_app.task("push-changes")
async def push_changes(ctx: AppContext):
    """Push local task changes back to GitHub (not yet implemented)."""
    logger.info("push-changes: push sync not implemented yet")
    return {"status": "skipped", "reason": "push sync not implemented yet"}


@github_sync_app.on_startup
def on_startup(ctx: AppContext):
    logger.info("GitHub Sync app started: %s", ctx.app_id)


@github_sync_app.on_shutdown
def on_shutdown(ctx: AppContext):
    logger.info("GitHub Sync app stopped: %s", ctx.app_id)
