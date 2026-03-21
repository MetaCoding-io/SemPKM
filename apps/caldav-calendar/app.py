"""CalDAV Calendar app — HTTP Basic connect flow and calendar selection.

Routes:
- /_fragments/connect              GET   — settings page: connect form or status
- /_fragments/connect/credentials  POST  — submit server URL + username + password
- /_fragments/connect/disconnect   POST  — disconnect and clear credentials
- /_fragments/settings/calendars   POST  — save selected calendar IDs
- /_fragments/settings/sync-config POST  — save sync direction + poll interval
- /_fragments/sync-now             POST  — trigger immediate sync
"""

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse
import json
import logging
from datetime import datetime, timezone

from services.auth import (
    check_connection,
    store_credentials,
    get_connection_status,
    clear_auth_state,
)
from services.caldav_client import CalDAVClient, CalDAVError, CalDAVAuthError
from services.sync_engine import pull_sync, push_sync

logger = logging.getLogger("caldav_calendar.app")

caldav_calendar_app = App("caldav-calendar")


def _make_client(ctx: AppContext) -> CalDAVClient:
    """Create a CalDAVClient wired to the app's HTTP and state clients."""
    return CalDAVClient(
        http_client=ctx.http,
        state_client=ctx.state,
    )


async def _render_connect_status(ctx: AppContext) -> HTMLResponse:
    """Render connect_status.html with calendar list, sync config, and stats.

    Runs the full discovery chain to populate the calendar list.
    Falls back to connect.html with error on CalDAV failures.
    """
    status = await get_connection_status(ctx.state)
    server_url = await ctx.state.get("server_url")

    # Run calendar discovery
    client = _make_client(ctx)
    calendars = await client.discover_calendars(server_url)

    # Read selected calendars
    selected_json = await ctx.state.get("selected_calendars")
    selected_calendars = json.loads(selected_json) if selected_json else []

    # Read sync config
    sync_direction = await ctx.state.get("sync_direction") or "pull-only"
    poll_interval = await ctx.state.get("poll_interval") or "15m"
    last_sync_at = await ctx.state.get("last_sync_at") or ""

    # Parse result JSONs
    last_pull_json = await ctx.state.get("last_pull_result")
    last_pull_result = json.loads(last_pull_json) if last_pull_json else None
    last_push_json = await ctx.state.get("last_push_result")
    last_push_result = json.loads(last_push_json) if last_push_json else None

    return HTMLResponse(ctx.render_template(
        "connect_status.html",
        username=status["username"] or "Unknown",
        server_url=server_url or "",
        auth_method=status["auth_method"] or "basic",
        calendars=calendars,
        selected_calendars=selected_calendars,
        sync_direction=sync_direction,
        poll_interval=poll_interval,
        last_sync_at=last_sync_at,
        last_pull_result=last_pull_result,
        last_push_result=last_push_result,
    ))


@caldav_calendar_app.route("/_fragments/connect")
async def connect_fragment(request: Request):
    """Render the connect/settings page fragment.

    If connected: fetch calendars and render status panel.
    If disconnected or on error: render connect form.
    """
    ctx: AppContext = request.app.state.ctx
    status = await get_connection_status(ctx.state)

    if status["connected"]:
        try:
            return await _render_connect_status(ctx)
        except (CalDAVError, CalDAVAuthError, Exception) as exc:
            logger.warning("Failed to render connect status: %s", exc)
            return HTMLResponse(ctx.render_template(
                "connect.html",
                error=f"Connection error: {exc}. Please reconnect.",
                success=None,
            ))

    return HTMLResponse(ctx.render_template(
        "connect.html",
        error=None,
        success=None,
    ))


@caldav_calendar_app.route("/_fragments/connect/credentials", methods=["POST"])
async def save_credentials(request: Request):
    """Submit CalDAV server URL, username, and password.

    Tests connection via PROPFIND, stores credentials on success,
    runs calendar discovery and renders the status page.
    """
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    server_url = form.get("server_url", "").strip()
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()

    if not server_url or not username or not password:
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error="Server URL, username, and password are all required.",
            success=None,
        ))

    # Test connection via PROPFIND
    result = await check_connection(ctx.http, server_url, username, password)

    if not result["success"]:
        logger.warning(
            "Connection test failed for %s@%s: %s",
            username, server_url, result["message"],
        )
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error=result["message"],
            success=None,
        ))

    # Connection succeeded — store credentials
    await store_credentials(ctx.state, server_url, username, password)
    logger.info("CalDAV credentials stored for %s@%s", username, server_url)

    # Render connected status with calendar list
    try:
        return await _render_connect_status(ctx)
    except (CalDAVError, Exception) as exc:
        logger.warning("Calendar discovery failed after connect: %s", exc)
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error=f"Connected but calendar discovery failed: {exc}",
            success=None,
        ))


@caldav_calendar_app.route("/_fragments/connect/disconnect", methods=["POST"])
async def disconnect(request: Request):
    """Disconnect from CalDAV and clear all stored credentials and state."""
    ctx: AppContext = request.app.state.ctx
    await clear_auth_state(ctx.state)
    await ctx.state.set("selected_calendars", "")
    await ctx.state.set("sync_direction", "")
    await ctx.state.set("poll_interval", "")
    await ctx.state.set("last_sync_at", "")
    await ctx.state.set("last_pull_result", "")
    await ctx.state.set("last_push_result", "")
    logger.info("Disconnected from CalDAV server")
    return HTMLResponse(ctx.render_template(
        "connect.html",
        error=None,
        success=None,
    ))


@caldav_calendar_app.route("/_fragments/settings/calendars", methods=["POST"])
async def save_calendars(request: Request):
    """Save selected calendar hrefs and re-render status."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    calendar_ids = form.getlist("calendar_ids")
    await ctx.state.set("selected_calendars", json.dumps(calendar_ids))
    logger.info("Saved selected calendars: %d calendars", len(calendar_ids))
    return await _render_connect_status(ctx)


@caldav_calendar_app.route("/_fragments/settings/sync-config", methods=["POST"])
async def save_sync_config(request: Request):
    """Save sync direction and poll interval settings."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    sync_direction = form.get("sync_direction", "pull-only")
    poll_interval = form.get("poll_interval", "15m")
    await ctx.state.set("sync_direction", sync_direction)
    await ctx.state.set("poll_interval", poll_interval)
    logger.info(
        "Saved sync config: direction=%s interval=%s",
        sync_direction, poll_interval,
    )
    return await _render_connect_status(ctx)


@caldav_calendar_app.route("/_fragments/sync-now", methods=["POST"])
async def sync_now(request: Request):
    """Trigger an immediate sync.

    Calls pull_sync (and optionally push_sync for bidirectional) and
    stores results in state so the UI can show last-sync feedback.
    """
    ctx: AppContext = request.app.state.ctx
    logger.info("Manual sync triggered")

    pull_result = await pull_sync(ctx)
    await ctx.state.set("last_pull_result", json.dumps(pull_result))

    sync_direction = await ctx.state.get("sync_direction")
    if sync_direction == "bidirectional":
        push_result = await push_sync(ctx)
        await ctx.state.set("last_push_result", json.dumps(push_result))

    await ctx.state.set("last_sync_at", datetime.now(timezone.utc).isoformat())
    return await _render_connect_status(ctx)


# ── Task handlers ──


@caldav_calendar_app.task("poll-events")
async def poll_events(ctx: AppContext):
    """Poll CalDAV server for updated events and sync to SemPKM."""
    logger.info("poll-events: task fired")
    pull_result = await pull_sync(ctx)

    sync_direction = await ctx.state.get("sync_direction")
    if sync_direction == "bidirectional":
        push_result = await push_sync(ctx)
        return {"pull": pull_result, "push": push_result}

    return pull_result


@caldav_calendar_app.task("push-changes")
async def push_changes(ctx: AppContext):
    """Push local changes back to CalDAV server."""
    logger.info("push-changes: task fired")
    return await push_sync(ctx)


# ── Lifecycle hooks ──


@caldav_calendar_app.on_startup
def on_startup(ctx: AppContext):
    logger.info("CalDAV Calendar app started: %s", ctx.app_id)


@caldav_calendar_app.on_shutdown
def on_shutdown(ctx: AppContext):
    logger.info("CalDAV Calendar app stopped: %s", ctx.app_id)
