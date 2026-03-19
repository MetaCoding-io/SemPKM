"""Linear Sync app — two-way sync between SemPKM objects and Linear issues.

Routes:
- /_fragments/connect          GET   — settings page connect form or status
- /_fragments/connect/api-key  POST  — authenticate via API key
- /_fragments/oauth-callback   GET   — OAuth callback handler
- /_fragments/connect/disconnect POST — disconnect and clear credentials
"""

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
import logging

from services.linear_client import LinearClient, LinearAPIError, LinearAuthError
from services.auth import (
    build_oauth_authorize_url,
    exchange_code,
    store_auth_tokens,
    store_workspace_info,
    get_connection_status,
    clear_auth_state,
)

logger = logging.getLogger("linear_sync")

linear_sync_app = App("linear-sync")


def _make_client(ctx: AppContext) -> LinearClient:
    """Create a LinearClient wired to the app's HTTP and state clients."""
    return LinearClient(
        http_client=ctx.http,
        state_client=ctx.state,
        client_id=None,   # populated from settings when OAuth is configured
        client_secret=None,
    )


@linear_sync_app.route("/_fragments/connect")
async def connect_fragment(request: Request):
    """Render the connect/settings page fragment.

    If connected: fetch teams and render status page.
    If disconnected or on error: render connect form.
    """
    ctx: AppContext = request.app.state.ctx
    status = await get_connection_status(ctx.state)

    if status["connected"]:
        try:
            client = _make_client(ctx)
            teams = await client.get_teams()
            return HTMLResponse(ctx.render_template(
                "connect_status.html",
                workspace_name=status["workspace_name"] or "Unknown",
                auth_method=status["auth_method"],
                teams=teams,
            ))
        except (LinearAPIError, Exception) as exc:
            logger.warning("Failed to fetch teams for connected account: %s", exc)
            # Fall through to connect form with error
            return HTMLResponse(ctx.render_template(
                "connect.html",
                error=f"Connection error: {exc}. Please reconnect.",
            ))

    return HTMLResponse(ctx.render_template("connect.html", error=None))


@linear_sync_app.route("/_fragments/connect/api-key", methods=["POST"])
async def connect_api_key(request: Request):
    """Authenticate with Linear using an API key.

    Reads api_key from the form body, verifies it by calling get_viewer(),
    fetches organization info, and stores everything in state.
    """
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    api_key = form.get("api_key", "").strip()

    if not api_key:
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error="API key is required.",
        ))

    try:
        # Store the key first so LinearClient can find it
        await ctx.state.set("api_key", api_key)
        await ctx.state.set("auth_method", "api_key")

        client = _make_client(ctx)

        # Verify: fetch viewer profile
        viewer = await client.get_viewer()
        logger.info("API key verified for user: %s", viewer.get("name", "unknown"))

        # Fetch organization/workspace info
        org = await client.get_organization()
        await store_workspace_info(
            ctx.state,
            workspace_name=org.get("name", "Unknown"),
            workspace_id=org.get("id", ""),
        )

        # Fetch teams for the status display
        teams = await client.get_teams()

        response = HTMLResponse(ctx.render_template(
            "connect_status.html",
            workspace_name=org.get("name", "Unknown"),
            auth_method="api_key",
            teams=teams,
        ))
        response.headers["HX-Trigger"] = "linearConnected"
        return response

    except LinearAuthError as exc:
        logger.warning("API key verification failed: %s", exc)
        # Clear the invalid key
        await clear_auth_state(ctx.state)
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error="Invalid API key. Please check and try again.",
        ))
    except (LinearAPIError, Exception) as exc:
        logger.warning("API key connection error: %s", exc)
        await clear_auth_state(ctx.state)
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error=f"Connection failed: {exc}",
        ))


@linear_sync_app.route("/_fragments/oauth-callback")
async def oauth_callback(request: Request):
    """Handle Linear OAuth callback.

    Exchanges the authorization code for tokens, verifies the connection,
    and stores workspace info. Returns an HTML page that redirects back
    to the settings page.
    """
    ctx: AppContext = request.app.state.ctx
    code = request.query_params.get("code")
    state_param = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        logger.warning("OAuth callback error from Linear: %s", error)
        return HTMLResponse(
            _oauth_result_page(
                success=False,
                message=f"Linear denied access: {error}",
            )
        )

    if not code:
        return HTMLResponse(
            _oauth_result_page(
                success=False,
                message="Missing authorization code.",
            )
        )

    try:
        # TODO: read client_id/secret from app settings when OAuth config is added
        client_id = await ctx.state.get("oauth_client_id") or ""
        client_secret = await ctx.state.get("oauth_client_secret") or ""
        redirect_uri = await ctx.state.get("oauth_redirect_uri") or ""

        tokens = await exchange_code(
            ctx.http,
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )

        await store_auth_tokens(
            ctx.state,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            auth_method="oauth",
        )

        # Verify and fetch workspace info
        client = _make_client(ctx)
        org = await client.get_organization()
        await store_workspace_info(
            ctx.state,
            workspace_name=org.get("name", "Unknown"),
            workspace_id=org.get("id", ""),
        )

        logger.info("OAuth connection established for workspace: %s", org.get("name"))
        return HTMLResponse(
            _oauth_result_page(
                success=True,
                message=f"Connected to {org.get('name', 'Linear')}!",
            )
        )

    except (LinearAuthError, LinearAPIError) as exc:
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


@linear_sync_app.route("/_fragments/connect/disconnect", methods=["POST"])
async def disconnect(request: Request):
    """Disconnect from Linear and clear stored credentials."""
    ctx: AppContext = request.app.state.ctx
    await clear_auth_state(ctx.state)
    logger.info("Disconnected from Linear")
    return HTMLResponse(ctx.render_template("connect.html", error=None))


def _oauth_result_page(success: bool, message: str) -> str:
    """Generate a minimal HTML page for the OAuth callback result.

    On success, auto-redirects to the app's settings page after 2 seconds.
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
<head><title>Linear Sync — {'Connected' if success else 'Error'}</title></head>
<body style="font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #1a1a1a; color: #eee;">
  <div style="text-align: center; max-width: 400px;">
    <h2 class="{status_class}">{message}</h2>
    {'<p>Redirecting to settings…</p>' if success else '<p><a href="/browser/">Return to workspace</a></p>'}
  </div>
  {redirect_script}
</body>
</html>"""


@linear_sync_app.task("poll-tasks")
async def poll_tasks(ctx: AppContext):
    """Poll Linear for updated issues and sync changes to SemPKM."""
    from services.sync_engine import pull_sync

    logger.info("poll-tasks: starting pull sync")
    try:
        result = await pull_sync(ctx)
        logger.info("poll-tasks: completed — %s", result)
        return result
    except Exception as exc:
        logger.error("poll-tasks: sync failed — %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}


@linear_sync_app.on_startup
def on_startup(ctx: AppContext):
    logger.info("Linear Sync app started: %s", ctx.app_id)


@linear_sync_app.on_shutdown
def on_shutdown(ctx: AppContext):
    logger.info("Linear Sync app stopped: %s", ctx.app_id)
