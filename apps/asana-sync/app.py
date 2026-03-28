"""Asana Sync app — OAuth 2.0 / PAT connect flow, project selection, and field mapping.

Routes:
- /_fragments/connect              GET   — settings page: connect form or status
- /_fragments/connect/credentials  POST  — save Asana OAuth client credentials
- /_fragments/connect/asana        POST  — initiate OAuth redirect to Asana
- /_fragments/oauth-callback       GET   — OAuth callback (code exchange)
- /_fragments/connect/pat          POST  — connect via Personal Access Token
- /_fragments/connect/disconnect   POST  — disconnect and clear credentials
- /_fragments/settings/projects    POST  — save selected project GIDs
- /_fragments/settings/discover-fields  POST — discover custom fields from selected projects
- /_fragments/settings/field-mapping    POST — save status/priority/story-points mapping config
"""

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
import json
import logging
import uuid
from datetime import datetime, timezone

from services.auth import (
    build_asana_authorize_url,
    exchange_code,
    store_auth_tokens,
    get_connection_status,
    clear_auth_state,
    verify_pat,
)
from services.asana_client import AsanaClient, AsanaAPIError, AsanaAuthError
from services.sync_engine import pull_sync, push_sync

logger = logging.getLogger("asana.sync.app")

asana_sync_app = App("asana-sync")


def _redirect_uri(ctx: AppContext) -> str:
    """Compute OAuth redirect URI from the platform URL."""
    return f"{ctx.platform_url.rstrip('/')}/app/asana-sync/_fragments/oauth-callback"


def _render_connect(ctx: AppContext, **kwargs) -> str:
    """Render connect.html with redirect_uri always injected."""
    kwargs.setdefault("redirect_uri", _redirect_uri(ctx))
    return ctx.render_template("connect.html", **kwargs)


def _make_client(ctx: AppContext) -> AsanaClient:
    """Create an AsanaClient wired to the app's HTTP and state clients."""
    return AsanaClient(
        http_client=ctx.http,
        state_client=ctx.state,
    )


async def _make_client_with_creds(ctx: AppContext) -> AsanaClient:
    """Create an AsanaClient with client_id/secret from state (for token refresh)."""
    client_id = await ctx.state.get("client_id") or ""
    client_secret = await ctx.state.get("client_secret") or ""
    return AsanaClient(
        http_client=ctx.http,
        state_client=ctx.state,
        client_id=client_id,
        client_secret=client_secret,
    )


async def _render_connect_status(ctx: AppContext) -> HTMLResponse:
    """Render connect_status.html with connection info, project selection, and field mapping."""
    status = await get_connection_status(ctx.state)
    client = await _make_client_with_creds(ctx)

    # Fetch workspaces with their projects for selection UI
    workspaces = []
    try:
        ws_list = await client.get_workspaces()
        for ws in ws_list:
            projects = await client.get_projects(ws["gid"])
            workspaces.append({
                "gid": ws["gid"],
                "name": ws.get("name", "Unnamed Workspace"),
                "projects": projects,
            })
    except (AsanaAPIError, AsanaAuthError) as exc:
        logger.warning("Failed to fetch workspaces/projects: %s", exc)

    # Read selected projects
    selected_json = await ctx.state.get("selected_projects")
    selected_projects = json.loads(selected_json) if selected_json else []

    # Read discovered field data (populated by discover-fields route)
    enum_fields_json = await ctx.state.get("discovered_enum_fields")
    number_fields_json = await ctx.state.get("discovered_number_fields")
    sections_json = await ctx.state.get("discovered_sections")

    discovered_enum_fields = json.loads(enum_fields_json) if enum_fields_json else []
    discovered_number_fields = json.loads(number_fields_json) if number_fields_json else []
    discovered_sections = json.loads(sections_json) if sections_json else []

    fields_discovered = len(discovered_enum_fields) > 0 or len(discovered_sections) > 0

    # Read saved mapping configuration
    status_source = await ctx.state.get("status_source") or ""
    status_field_gid = await ctx.state.get("status_field_gid") or ""
    status_mapping_json = await ctx.state.get("status_mapping")
    status_mapping = json.loads(status_mapping_json) if status_mapping_json else {}

    priority_field_gid = await ctx.state.get("priority_field_gid") or ""
    priority_mapping_json = await ctx.state.get("priority_mapping")
    priority_mapping = json.loads(priority_mapping_json) if priority_mapping_json else {}

    story_points_field_gid = await ctx.state.get("story_points_field_gid") or ""

    # Sync configuration and results
    sync_direction = await ctx.state.get("sync_direction") or "pull-only"
    poll_interval = await ctx.state.get("poll_interval") or "15m"
    last_sync_at = await ctx.state.get("last_sync_at") or ""

    last_pull_json = await ctx.state.get("last_pull_result")
    last_pull_result = json.loads(last_pull_json) if last_pull_json else None
    last_push_json = await ctx.state.get("last_push_result")
    last_push_result = json.loads(last_push_json) if last_push_json else None

    return HTMLResponse(ctx.render_template(
        "connect_status.html",
        asana_email=status["asana_email"] or "Unknown",
        auth_method=status["auth_method"],
        token_expiry=status["token_expiry"],
        workspaces=workspaces,
        selected_projects=selected_projects,
        # Field discovery data
        discovered_enum_fields=discovered_enum_fields,
        discovered_number_fields=discovered_number_fields,
        discovered_sections=discovered_sections,
        fields_discovered=fields_discovered,
        # Saved mapping configuration
        status_source=status_source,
        status_field_gid=status_field_gid,
        status_mapping=status_mapping,
        priority_field_gid=priority_field_gid,
        priority_mapping=priority_mapping,
        story_points_field_gid=story_points_field_gid,
        # Sync configuration and results
        sync_direction=sync_direction,
        poll_interval=poll_interval,
        last_sync_at=last_sync_at,
        last_pull_result=last_pull_result,
        last_push_result=last_push_result,
    ))


@asana_sync_app.route("/_fragments/connect")
async def connect_fragment(request: Request):
    """Render the connect/settings page fragment.

    If connected: fetch workspaces/projects and render status panel.
    If disconnected or on error: render connect form.
    """
    ctx: AppContext = request.app.state.ctx
    status = await get_connection_status(ctx.state)

    if status["connected"]:
        try:
            return await _render_connect_status(ctx)
        except (AsanaAPIError, AsanaAuthError, Exception) as exc:
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


@asana_sync_app.route("/_fragments/connect/credentials", methods=["POST"])
async def save_credentials(request: Request):
    """Save Asana OAuth client_id and client_secret."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    client_id = form.get("client_id", "").strip()
    client_secret = form.get("client_secret", "").strip()

    if not client_id or not client_secret:
        return HTMLResponse(_render_connect(ctx,
            error="Both Client ID and Client Secret are required.",
            success=None,
            has_credentials=False,
        ))

    await ctx.state.set("client_id", client_id)
    await ctx.state.set("client_secret", client_secret)
    logger.info("Asana OAuth credentials saved")

    return HTMLResponse(_render_connect(ctx,
        error=None,
        success="Credentials saved. You can now connect with Asana.",
        has_credentials=True,
    ))


@asana_sync_app.route("/_fragments/connect/asana", methods=["POST"])
async def initiate_oauth(request: Request):
    """Generate OAuth state, build authorize URL, and redirect to Asana."""
    ctx: AppContext = request.app.state.ctx

    client_id = await ctx.state.get("client_id")
    if not client_id:
        return HTMLResponse(_render_connect(ctx,
            error="Save your Asana OAuth credentials first.",
            success=None,
            has_credentials=False,
        ))

    # Generate CSRF state parameter
    oauth_state = str(uuid.uuid4())
    await ctx.state.set("oauth_state", oauth_state)

    authorize_url = build_asana_authorize_url(
        client_id=client_id,
        redirect_uri=_redirect_uri(ctx),
        state=oauth_state,
    )

    logger.info("Redirecting to Asana OAuth consent screen")
    return RedirectResponse(url=authorize_url, status_code=303)


@asana_sync_app.route("/_fragments/oauth-callback")
async def oauth_callback(request: Request):
    """Handle Asana OAuth callback.

    Exchanges the authorization code for tokens, fetches the user's
    identity, stores everything, and renders the result page.
    """
    ctx: AppContext = request.app.state.ctx
    code = request.query_params.get("code")
    state_param = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        logger.warning("OAuth callback error from Asana: %s", error)
        return HTMLResponse(
            _oauth_result_page(
                success=False,
                message=f"Asana denied access: {error}",
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

        # Temporarily store the access token so AsanaClient can use it
        await ctx.state.set("access_token", tokens["access_token"])

        # Fetch user identity via /users/me
        client = AsanaClient(
            http_client=ctx.http,
            state_client=ctx.state,
            client_id=client_id,
            client_secret=client_secret,
        )
        user = await client.get_user_me()
        asana_email = user.get("email", "")

        # Store all tokens via auth helper
        await store_auth_tokens(
            ctx.state,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token", ""),
            expires_in=tokens.get("expires_in"),
            asana_email=asana_email,
        )

        # Clear the one-time oauth_state
        await ctx.state.set("oauth_state", "")

        logger.info("OAuth connection established for %s", asana_email)
        return HTMLResponse(
            _oauth_result_page(
                success=True,
                message=f"Connected to Asana ({asana_email})!",
            )
        )

    except (AsanaAuthError, AsanaAPIError) as exc:
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


@asana_sync_app.route("/_fragments/connect/pat", methods=["POST"])
async def connect_pat(request: Request):
    """Connect via Personal Access Token — verify and store."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    api_key = form.get("api_key", "").strip()

    if not api_key:
        return HTMLResponse(_render_connect(ctx,
            error="Please enter your Personal Access Token.",
            success=None,
            has_credentials=bool(await ctx.state.get("client_id")),
        ))

    try:
        user_info = await verify_pat(ctx.http, api_key)
        asana_email = user_info.get("email", "")

        # Store PAT as access_token with auth_method="pat"
        await store_auth_tokens(
            ctx.state,
            access_token=api_key,
            refresh_token="",
            expires_in=None,
            asana_email=asana_email,
            auth_method="pat",
        )

        logger.info("PAT connection established for %s", asana_email)
        return await _render_connect_status(ctx)

    except AsanaAuthError as exc:
        logger.warning("PAT verification failed: %s", exc)
        return HTMLResponse(_render_connect(ctx,
            error=f"Invalid token: {exc}",
            success=None,
            has_credentials=bool(await ctx.state.get("client_id")),
        ))


@asana_sync_app.route("/_fragments/connect/disconnect", methods=["POST"])
async def disconnect(request: Request):
    """Disconnect from Asana and clear stored credentials/tokens."""
    ctx: AppContext = request.app.state.ctx
    await clear_auth_state(ctx.state)
    # Clear selected projects and field mapping configuration
    await ctx.state.set("selected_projects", "")
    await ctx.state.set("discovered_enum_fields", "")
    await ctx.state.set("discovered_number_fields", "")
    await ctx.state.set("discovered_sections", "")
    await ctx.state.set("status_source", "")
    await ctx.state.set("status_field_gid", "")
    await ctx.state.set("status_mapping", "")
    await ctx.state.set("priority_field_gid", "")
    await ctx.state.set("priority_mapping", "")
    await ctx.state.set("story_points_field_gid", "")
    logger.info("Disconnected from Asana")
    has_credentials = bool(await ctx.state.get("client_id"))
    return HTMLResponse(_render_connect(ctx,
        error=None,
        success=None,
        has_credentials=has_credentials,
    ))


@asana_sync_app.route("/_fragments/settings/projects", methods=["POST"])
async def save_projects(request: Request):
    """Save selected project GIDs and re-render status."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    project_gids = form.getlist("project_gids")
    await ctx.state.set("selected_projects", json.dumps(project_gids))
    logger.info("Saved selected projects: %d projects", len(project_gids))
    return await _render_connect_status(ctx)


@asana_sync_app.route("/_fragments/settings/discover-fields", methods=["POST"])
async def discover_fields(request: Request):
    """Discover custom fields and sections from selected projects.

    Calls get_custom_fields() and get_sections() for each selected project,
    unions fields across projects (deduplicating by GID), separates by type
    (enum vs number), and persists the discovered data for the mapping UI.
    """
    ctx: AppContext = request.app.state.ctx
    client = await _make_client_with_creds(ctx)

    selected_json = await ctx.state.get("selected_projects")
    selected_projects = json.loads(selected_json) if selected_json else []

    if not selected_projects:
        logger.warning("discover-fields called with no selected projects")
        return await _render_connect_status(ctx)

    # Union custom fields across projects, deduplicate by GID
    fields_by_gid: dict[str, dict] = {}
    sections_by_gid: dict[str, dict] = {}

    for project_gid in selected_projects:
        try:
            custom_fields = await client.get_custom_fields(project_gid)
            for cf in custom_fields:
                gid = cf.get("gid", "")
                if gid and gid not in fields_by_gid:
                    fields_by_gid[gid] = {
                        "gid": gid,
                        "name": cf.get("name", "Unnamed Field"),
                        "resource_subtype": cf.get("resource_subtype", ""),
                        "enum_options": [
                            {"name": opt.get("name", ""), "gid": opt.get("gid", "")}
                            for opt in cf.get("enum_options", []) or []
                        ],
                    }
        except (AsanaAPIError, AsanaAuthError) as exc:
            logger.warning(
                "Failed to fetch custom fields for project %s: %s",
                project_gid, exc,
            )

        try:
            sections = await client.get_sections(project_gid)
            for sec in sections:
                gid = sec.get("gid", "")
                if gid and gid not in sections_by_gid:
                    sections_by_gid[gid] = {
                        "gid": gid,
                        "name": sec.get("name", "Unnamed Section"),
                    }
        except (AsanaAPIError, AsanaAuthError) as exc:
            logger.warning(
                "Failed to fetch sections for project %s: %s",
                project_gid, exc,
            )

    # Separate fields by type
    enum_fields = [
        f for f in fields_by_gid.values()
        if f["resource_subtype"] == "enum"
    ]
    number_fields = [
        f for f in fields_by_gid.values()
        if f["resource_subtype"] == "number"
    ]
    all_sections = list(sections_by_gid.values())

    # Persist discovered data
    await ctx.state.set("discovered_enum_fields", json.dumps(enum_fields))
    await ctx.state.set("discovered_number_fields", json.dumps(number_fields))
    await ctx.state.set("discovered_sections", json.dumps(all_sections))

    logger.info(
        "Discovered fields: %d enum, %d number, %d sections across %d projects",
        len(enum_fields), len(number_fields), len(all_sections),
        len(selected_projects),
    )

    return await _render_connect_status(ctx)


@asana_sync_app.route("/_fragments/settings/field-mapping", methods=["POST"])
async def save_field_mapping(request: Request):
    """Save status/priority/story-points field mapping configuration.

    Reads form data for status source selection, status/priority enum-to-bpkm
    value mappings, and story points field selection. Persists each as a
    separate JSON key in StateClient.
    """
    ctx: AppContext = request.app.state.ctx
    form = await request.form()

    # ── Status configuration ──
    status_source = form.get("status_source", "completed_only")
    status_field_gid = form.get("status_field_gid", "")
    story_points_field_gid = form.get("story_points_field_gid", "")
    priority_field_gid = form.get("priority_field_gid", "")

    # Build status mapping from form keys like status_map_<option_name>=<bpkm_value>
    status_mapping: dict[str, str] = {}
    if status_source in ("custom_field", "section"):
        for key in form.keys():
            if key.startswith("status_map_"):
                option_name = key[len("status_map_"):]
                bpkm_value = form.get(key, "")
                if option_name and bpkm_value:
                    status_mapping[option_name] = bpkm_value

    # Build priority mapping from form keys like priority_map_<option_name>=<bpkm_value>
    priority_mapping: dict[str, str] = {}
    if priority_field_gid:
        for key in form.keys():
            if key.startswith("priority_map_"):
                option_name = key[len("priority_map_"):]
                bpkm_value = form.get(key, "")
                if option_name and bpkm_value:
                    priority_mapping[option_name] = bpkm_value

    # Persist all mapping configuration
    await ctx.state.set("status_source", status_source)
    await ctx.state.set("status_field_gid", status_field_gid)
    await ctx.state.set("status_mapping", json.dumps(status_mapping))
    await ctx.state.set("priority_field_gid", priority_field_gid)
    await ctx.state.set("priority_mapping", json.dumps(priority_mapping))
    await ctx.state.set("story_points_field_gid", story_points_field_gid)

    logger.info(
        "Saved field mapping: status_source=%s, status_mappings=%d, "
        "priority_mappings=%d, story_points=%s",
        status_source, len(status_mapping), len(priority_mapping),
        "yes" if story_points_field_gid else "no",
    )

    return await _render_connect_status(ctx)


@asana_sync_app.route("/_fragments/settings/sync-config", methods=["POST"])
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
<head><title>Asana — {'Connected' if success else 'Error'}</title></head>
<body style="font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #1a1a1a; color: #eee;">
  <div style="text-align: center; max-width: 400px;">
    <h2 class="{status_class}">{message}</h2>
    {'<p>Redirecting to workspace…</p>' if success else '<p><a href="/browser/">Return to workspace</a></p>'}
  </div>
  {redirect_script}
</body>
</html>"""


# ── Task handlers ──

@asana_sync_app.task("poll-tasks")
async def poll_tasks(ctx: AppContext):
    """Poll Asana for updated tasks and sync to SemPKM."""
    logger.info("poll-tasks: starting pull sync")
    result = await pull_sync(ctx)
    return result


@asana_sync_app.task("push-changes")
async def push_changes(ctx: AppContext):
    """Push local changes back to Asana."""
    logger.info("push-changes: starting push sync")
    result = await push_sync(ctx)
    return result


@asana_sync_app.route("/_fragments/sync-now", methods=["POST"])
async def sync_now(request: Request):
    """Trigger an immediate pull + optional push sync."""
    ctx: AppContext = request.app.state.ctx
    logger.info("sync-now: manual sync triggered")

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


@asana_sync_app.on_startup
def on_startup(ctx: AppContext):
    logger.info("Asana Sync app started: %s", ctx.app_id)


@asana_sync_app.on_shutdown
def on_shutdown(ctx: AppContext):
    logger.info("Asana Sync app stopped: %s", ctx.app_id)
