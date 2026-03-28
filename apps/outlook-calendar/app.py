"""Outlook Calendar app — Microsoft OAuth 2.0 connect flow and calendar selection.

Routes:
- /_fragments/connect              GET   — settings page: connect form or status
- /_fragments/connect/credentials  POST  — save Azure AD credentials
- /_fragments/connect/microsoft    POST  — initiate OAuth redirect to Microsoft
- /_fragments/oauth-callback       GET   — OAuth callback (code exchange)
- /_fragments/connect/disconnect   POST  — disconnect and clear credentials
- /_fragments/settings/calendars   POST  — save selected calendar IDs
- /_fragments/settings/sync-config POST  — save sync configuration
- /_fragments/sync-now             POST  — trigger immediate sync
"""

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
import json
import logging
import uuid
from datetime import datetime, timezone

from services.auth import (
    build_authorize_url,
    exchange_code,
    store_auth_tokens,
    get_connection_status,
    clear_auth_state,
)
from services.outlook_client import (
    OutlookClient,
    OutlookAPIError,
    OutlookAuthError,
)

logger = logging.getLogger("outlook_calendar.app")

outlook_calendar_app = App("outlook-calendar")


def _redirect_uri(ctx: AppContext) -> str:
    """Compute OAuth redirect URI from the platform URL."""
    return f"{ctx.platform_url.rstrip('/')}/app/outlook-calendar/_fragments/oauth-callback"


def _render_connect(ctx: AppContext, **kwargs) -> str:
    """Render connect.html with redirect_uri always injected."""
    kwargs.setdefault("redirect_uri", _redirect_uri(ctx))
    return ctx.render_template("connect.html", **kwargs)


def _make_client(ctx: AppContext) -> OutlookClient:
    """Create an OutlookClient wired to the app's HTTP and state clients."""
    return OutlookClient(
        http_client=ctx.http,
        state_client=ctx.state,
        client_id=None,
        client_secret=None,
    )


async def _make_client_with_creds(ctx: AppContext) -> OutlookClient:
    """Create an OutlookClient with client_id/secret from state (for token refresh)."""
    client_id = await ctx.state.get("client_id") or ""
    client_secret = await ctx.state.get("client_secret") or ""
    return OutlookClient(
        http_client=ctx.http,
        state_client=ctx.state,
        client_id=client_id,
        client_secret=client_secret,
    )


async def _render_connect_status(ctx: AppContext) -> HTMLResponse:
    """Render connect_status.html with calendar list, sync config, and sync stats."""
    status = await get_connection_status(ctx.state)
    client = await _make_client_with_creds(ctx)
    calendars = await client.get_calendar_list()

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
        microsoft_email=status["microsoft_email"] or "Unknown",
        auth_method=status["auth_method"],
        token_expiry=status["token_expiry"],
        calendars=calendars,
        selected_calendars=selected_calendars,
        sync_direction=sync_direction,
        poll_interval=poll_interval,
        last_sync_at=last_sync_at,
        last_pull_result=last_pull_result,
        last_push_result=last_push_result,
    ))


@outlook_calendar_app.route("/_fragments/connect")
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
        except (OutlookAPIError, OutlookAuthError, Exception) as exc:
            logger.warning("Failed to render connect status: %s", exc)
            return HTMLResponse(_render_connect(ctx,
                error=f"Connection error: {exc}. Please reconnect.",
                success=None,
                has_credentials=bool(await ctx.state.get("client_id")),
            ))

    has_credentials = bool(await ctx.state.get("client_id"))
    return HTMLResponse(_render_connect(ctx,
        error=None,
        success=None,
        has_credentials=has_credentials,
    ))


@outlook_calendar_app.route("/_fragments/connect/credentials", methods=["POST"])
async def save_credentials(request: Request):
    """Save Azure AD application (client) ID and client secret."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    client_id = form.get("client_id", "").strip()
    client_secret = form.get("client_secret", "").strip()

    if not client_id or not client_secret:
        return HTMLResponse(_render_connect(ctx,
            error="Both Application (Client) ID and Client Secret are required.",
            success=None,
            has_credentials=False,
        ))

    await ctx.state.set("client_id", client_id)
    await ctx.state.set("client_secret", client_secret)
    logger.info("Azure AD credentials saved")

    return HTMLResponse(_render_connect(ctx,
        error=None,
        success="Credentials saved. You can now connect with Microsoft.",
        has_credentials=True,
    ))


@outlook_calendar_app.route("/_fragments/connect/microsoft", methods=["POST"])
async def initiate_oauth(request: Request):
    """Generate OAuth state, build authorize URL, and redirect to Microsoft."""
    ctx: AppContext = request.app.state.ctx

    client_id = await ctx.state.get("client_id")
    if not client_id:
        return HTMLResponse(_render_connect(ctx,
            error="Save your Azure AD credentials first.",
            success=None,
            has_credentials=False,
        ))

    # Generate CSRF state parameter
    oauth_state = str(uuid.uuid4())
    await ctx.state.set("oauth_state", oauth_state)

    authorize_url = build_authorize_url(
        client_id=client_id,
        redirect_uri=_redirect_uri(ctx),
        state=oauth_state,
    )

    logger.info("Redirecting to Microsoft OAuth consent screen")
    return RedirectResponse(url=authorize_url, status_code=303)


@outlook_calendar_app.route("/_fragments/oauth-callback")
async def oauth_callback(request: Request):
    """Handle Microsoft OAuth callback.

    Exchanges the authorization code for tokens, fetches the user's
    calendar list to find their default calendar email, stores everything,
    and renders the result page.
    """
    ctx: AppContext = request.app.state.ctx
    code = request.query_params.get("code")
    state_param = request.query_params.get("state")
    error = request.query_params.get("error")
    error_description = request.query_params.get("error_description", "")

    if error:
        logger.warning(
            "OAuth callback error from Microsoft: %s — %s", error, error_description
        )
        return HTMLResponse(
            _oauth_result_page(
                success=False,
                message=f"Microsoft denied access: {error_description or error}",
            )
        )

    if not code:
        return HTMLResponse(
            _oauth_result_page(
                success=False,
                message="Missing authorization code.",
            )
        )

    # Verify CSRF state parameter
    expected_state = await ctx.state.get("oauth_state")
    if not expected_state or state_param != expected_state:
        logger.warning(
            "OAuth state mismatch: expected=%s got=%s",
            expected_state,
            state_param,
        )
        return HTMLResponse(
            _oauth_result_page(
                success=False,
                message="OAuth state mismatch — possible CSRF attack. Please try again.",
            )
        )

    try:
        client_id = await ctx.state.get("client_id") or ""
        client_secret = await ctx.state.get("client_secret") or ""

        tokens = await exchange_code(
            ctx.http,
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=_redirect_uri(ctx),
        )

        # Temporarily store the access token so OutlookClient can use it
        await ctx.state.set("access_token", tokens["access_token"])

        # Fetch calendar list to find the default calendar owner
        client = OutlookClient(
            http_client=ctx.http,
            state_client=ctx.state,
            client_id=client_id,
            client_secret=client_secret,
        )
        calendars = await client.get_calendar_list()

        # Microsoft Graph doesn't expose the user's email directly in
        # calendar list — use the default calendar's owner or fall back.
        # The /me endpoint gives us displayName + mail, but we'd need
        # an extra scope. For now, use "owner" from the default calendar.
        microsoft_email = ""
        for cal in calendars:
            if cal.get("isDefaultCalendar"):
                microsoft_email = cal.get("name", "Default Calendar")
                break

        # Now store all tokens properly via auth helper
        await store_auth_tokens(
            ctx.state,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token", ""),
            expires_in=tokens.get("expires_in"),
            microsoft_email=microsoft_email,
        )

        # Clear the one-time oauth_state
        await ctx.state.set("oauth_state", "")

        logger.info("OAuth connection established for %s", microsoft_email)
        return HTMLResponse(
            _oauth_result_page(
                success=True,
                message=f"Connected to Outlook Calendar ({microsoft_email})!",
            )
        )

    except (OutlookAuthError, OutlookAPIError) as exc:
        logger.warning("OAuth callback failed: %s", exc)
        return HTMLResponse(
            _oauth_result_page(
                success=False,
                message=f"Authentication failed: {exc}",
            )
        )
    except Exception as exc:
        logger.error("Unexpected error in OAuth callback: %s", exc)
        return HTMLResponse(
            _oauth_result_page(
                success=False,
                message=f"Unexpected error: {exc}",
            )
        )


@outlook_calendar_app.route("/_fragments/connect/disconnect", methods=["POST"])
async def disconnect(request: Request):
    """Disconnect from Microsoft and clear stored credentials/tokens."""
    ctx: AppContext = request.app.state.ctx
    # Clear auth tokens
    await clear_auth_state(ctx.state)
    # Also clear selected calendars and sync state
    await ctx.state.set("selected_calendars", "")
    logger.info("Disconnected from Outlook Calendar")
    has_credentials = bool(await ctx.state.get("client_id"))
    return HTMLResponse(_render_connect(ctx,
        error=None,
        success=None,
        has_credentials=has_credentials,
    ))


@outlook_calendar_app.route("/_fragments/settings/calendars", methods=["POST"])
async def save_calendars(request: Request):
    """Save selected calendar IDs and re-render status."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    calendar_ids = form.getlist("calendar_ids")
    await ctx.state.set("selected_calendars", json.dumps(calendar_ids))
    logger.info("Saved selected calendars: %d calendars", len(calendar_ids))
    return await _render_connect_status(ctx)


@outlook_calendar_app.route("/_fragments/settings/sync-config", methods=["POST"])
async def save_sync_config(request: Request):
    """Save sync direction and poll interval settings."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    sync_direction = form.get("sync_direction", "pull-only")
    poll_interval = form.get("poll_interval", "15m")
    await ctx.state.set("sync_direction", sync_direction)
    await ctx.state.set("poll_interval", poll_interval)
    logger.info("Saved sync config: direction=%s interval=%s", sync_direction, poll_interval)
    return await _render_connect_status(ctx)


@outlook_calendar_app.route("/_fragments/sync-now", methods=["POST"])
async def sync_now(request: Request):
    """Trigger an immediate pull sync (and push if bidirectional)."""
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

    sync_direction = await ctx.state.get("sync_direction")
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


def _oauth_result_page(success: bool, message: str) -> str:
    """Generate a minimal HTML page for the OAuth callback result.

    On success, auto-redirects to the workspace after 2 seconds.
    """
    status_class = "success" if success else "error"
    redirect_script = ""
    if success:
        redirect_script = (
            '<script>setTimeout(function() { '
            'window.location.href = "/browser/"; '
            '}, 2000);</script>'
        )
    return f"""<!DOCTYPE html>
<html>
<head><title>Outlook Calendar — {'Connected' if success else 'Error'}</title></head>
<body style="font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #1a1a1a; color: #eee;">
  <div style="text-align: center; max-width: 400px;">
    <h2 class="{status_class}">{message}</h2>
    {'<p>Redirecting to workspace…</p>' if success else '<p><a href="/browser/">Return to workspace</a></p>'}
  </div>
  {redirect_script}
</body>
</html>"""


# ── Skeleton task handlers for S03/S04 ──

@outlook_calendar_app.task("poll-events")
async def poll_events(ctx: AppContext):
    """Poll Outlook Calendar for updated events and sync to SemPKM."""
    from services.sync_engine import pull_sync, push_sync

    logger.info("poll-events: starting pull sync")
    try:
        pull_result = await pull_sync(ctx)
        await ctx.state.set("last_pull_result", json.dumps(pull_result))
        await ctx.state.set("last_sync_at", datetime.now(timezone.utc).isoformat())

        sync_direction = await ctx.state.get("sync_direction")
        if sync_direction == "bidirectional":
            logger.info("poll-events: starting push sync")
            push_result = await push_sync(ctx)
            await ctx.state.set("last_push_result", json.dumps(push_result))

        logger.info("poll-events: completed — %s", pull_result)
        return pull_result
    except Exception as exc:
        logger.error("poll-events: sync failed — %s", exc, exc_info=True)
        error_result = {"status": "error", "message": str(exc)}
        await ctx.state.set("last_pull_result", json.dumps(error_result))
        await ctx.state.set("last_sync_at", datetime.now(timezone.utc).isoformat())
        return error_result


@outlook_calendar_app.task("push-changes")
async def push_changes(ctx: AppContext):
    """Push local changes back to Outlook Calendar."""
    from services.sync_engine import push_sync

    logger.info("push-changes: starting push sync")
    try:
        result = await push_sync(ctx)
        await ctx.state.set("last_push_result", json.dumps(result))
        logger.info("push-changes: completed — %s", result)
        return result
    except Exception as exc:
        logger.error("push-changes: push sync failed — %s", exc, exc_info=True)
        error_result = {"status": "error", "message": str(exc)}
        await ctx.state.set("last_push_result", json.dumps(error_result))
        return error_result


@outlook_calendar_app.on_startup
def on_startup(ctx: AppContext):
    logger.info("Outlook Calendar app started: %s", ctx.app_id)


@outlook_calendar_app.on_shutdown
def on_shutdown(ctx: AppContext):
    logger.info("Outlook Calendar app stopped: %s", ctx.app_id)
