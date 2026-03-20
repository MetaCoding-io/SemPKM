"""Monday.com Sync app — two-way sync between SemPKM objects and Monday.com board items.

Routes:
- /_fragments/connect                          GET   — settings page connect form or status
- /_fragments/connect/credentials              POST  — authenticate via API token
- /_fragments/connect/disconnect               POST  — disconnect and clear credentials
- /_fragments/settings/configure-columns       GET   — column mapping form (type-filtered)
- /_fragments/settings/save-column-mapping     POST  — save column mapping per board
- /_fragments/settings/configure-labels        GET   — label mapping form (status/priority)
- /_fragments/settings/save-label-mapping      POST  — save label mappings per board
- /_fragments/settings/boards                  POST  — save selected board IDs
- /_fragments/settings/sync-config             POST  — save sync direction and poll interval
- /_fragments/settings/sync-now                POST  — trigger immediate sync
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse

from services.auth import (
    store_credentials,
    get_credentials,
    get_connection_status,
    clear_credentials,
)

logger = logging.getLogger("monday_sync")

# ---------------------------------------------------------------------------
# Column-mapping constants
# ---------------------------------------------------------------------------

COLUMN_TYPE_COMPATIBILITY = {
    "taskStatus": ["status"],
    "priority": ["status", "color"],
    "dueDate": ["date", "timeline"],
    "assignedTo": ["people"],
    "description": ["text", "long_text"],
    "estimatedEffort": ["numbers"],
    "tags": ["tags", "dropdown"],
    "dependency": ["dependency"],
}

BPKM_PROPERTY_LABELS = {
    "taskStatus": "Status",
    "priority": "Priority",
    "dueDate": "Due Date",
    "assignedTo": "Assignee",
    "description": "Description",
    "estimatedEffort": "Estimated Effort",
    "tags": "Tags",
}

BPKM_STATUS_VALUES = ["todo", "in-progress", "done", "blocked", "cancelled"]
BPKM_PRIORITY_VALUES = ["critical", "high", "medium", "low"]

monday_sync_app = App("monday-sync")


def _make_client(ctx: AppContext):
    """Create a MondayClient wired to the app's HTTP and state clients."""
    from services.monday_client import MondayClient

    return MondayClient(
        http_client=ctx.http,
        state_client=ctx.state,
    )


async def _render_connect_status(ctx: AppContext) -> HTMLResponse:
    """Render connect_status.html with full sync state.

    Reads boards from Monday.com API plus all sync state keys, and
    passes them as template variables.
    """
    client = _make_client(ctx)
    status = await get_connection_status(ctx.state, client)

    boards: list[dict] = []
    try:
        boards = await client.get_boards()
    except Exception as exc:
        logger.warning("Failed to fetch boards for connected account: %s", exc)

    # Read sync state
    selected_boards_json = await ctx.settings.get("selected_boards")
    selected_boards = json.loads(selected_boards_json) if selected_boards_json else []
    sync_direction = await ctx.settings.get("sync_direction") or "pull-only"
    poll_interval = await ctx.settings.get("poll_interval") or "15m"
    last_sync_at = await ctx.state.get("last_sync_at") or ""

    # Parse last pull result
    last_pull_json = await ctx.state.get("last_pull_result")
    last_pull_result = json.loads(last_pull_json) if last_pull_json else None

    # Parse last push result
    last_push_json = await ctx.state.get("last_push_result")
    last_push_result = json.loads(last_push_json) if last_push_json else None

    # Compute which boards have column mappings configured
    configured_boards: set[str] = set()
    for bid in selected_boards:
        mapping_json = await ctx.settings.get(f"column_mapping_{bid}")
        if mapping_json:
            configured_boards.add(str(bid))

    return HTMLResponse(ctx.render_template(
        "connect_status.html",
        display_name=status.get("display_name", ""),
        email=status.get("email", ""),
        token_preview=status.get("token_preview", ""),
        boards=boards,
        selected_boards=selected_boards,
        sync_direction=sync_direction,
        poll_interval=poll_interval,
        last_sync_at=last_sync_at,
        last_pull_result=last_pull_result,
        last_push_result=last_push_result,
        configured_boards=configured_boards,
    ))


@monday_sync_app.route("/_fragments/connect")
async def connect_fragment(request: Request):
    """Render the connect/settings page fragment.

    If connected: fetch boards and sync state, render full settings panel.
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


@monday_sync_app.route("/_fragments/connect/credentials", methods=["POST"])
async def connect_credentials(request: Request):
    """Authenticate with Monday.com using API token.

    Reads api_token from the form body, stores it, verifies via the
    ``me`` GraphQL query, and returns the connected status fragment.
    """
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    api_token = form.get("api_token", "").strip()

    if not api_token:
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error="API token is required.",
        ))

    try:
        # Store credentials first so MondayClient can find them
        await store_credentials(ctx.state, api_token)

        client = _make_client(ctx)
        user = await client.get_me()
        logger.info(
            "Monday.com credentials verified for user: %s (%s)",
            user.get("name", "unknown"),
            user.get("email", "unknown"),
        )

        response = await _render_connect_status(ctx)
        response.headers["HX-Trigger"] = "mondayConnected"
        return response

    except Exception as exc:
        logger.warning("Monday.com credential verification failed: %s", exc)
        # Clear the invalid credentials
        await clear_credentials(ctx.state)
        return HTMLResponse(ctx.render_template(
            "connect.html",
            error="Could not connect to Monday.com. Please check your API token.",
        ))


@monday_sync_app.route("/_fragments/settings/configure-columns")
async def configure_columns(request: Request):
    """Render column mapping form with type-filtered dropdowns per bpkm property."""
    ctx: AppContext = request.app.state.ctx
    board_id = request.query_params.get("board_id", "").strip()
    if not board_id:
        return HTMLResponse(
            '<div class="alert alert-error">Missing board_id parameter.</div>'
        )

    client = _make_client(ctx)
    try:
        columns = await client.get_board_columns(int(board_id))
    except Exception as exc:
        logger.warning("Failed to fetch columns for board %s: %s", board_id, exc)
        return HTMLResponse(
            '<div class="alert alert-error">Could not fetch board columns.</div>'
        )

    # Build type-filtered compatible columns for each bpkm property
    compatible_columns: dict[str, list[dict]] = {}
    for bpkm_prop, allowed_types in COLUMN_TYPE_COMPATIBILITY.items():
        compatible_columns[bpkm_prop] = [
            col for col in columns if col.get("type") in allowed_types
        ]

    # Read existing mapping
    mapping_json = await ctx.settings.get(f"column_mapping_{board_id}")
    current_mapping = json.loads(mapping_json) if mapping_json else {}

    # Find board name
    boards = await client.get_boards()
    board_name = board_id
    for b in boards:
        if str(b.get("id")) == str(board_id):
            board_name = b.get("name", board_id)
            break

    return HTMLResponse(ctx.render_template(
        "configure_columns.html",
        board_id=board_id,
        board_name=board_name,
        property_labels=BPKM_PROPERTY_LABELS,
        compatible_columns=compatible_columns,
        current_mapping=current_mapping,
    ))


@monday_sync_app.route("/_fragments/settings/save-column-mapping", methods=["POST"])
async def save_column_mapping(request: Request):
    """Save per-board column mapping from form submission."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    board_id = form.get("board_id", "").strip()
    if not board_id:
        return HTMLResponse(
            '<div class="alert alert-error">Missing board_id.</div>'
        )

    column_mapping: dict[str, str] = {}
    for bpkm_prop in BPKM_PROPERTY_LABELS:
        value = form.get(f"mapping_{bpkm_prop}", "").strip()
        if value:
            column_mapping[bpkm_prop] = value

    await ctx.settings.set(
        f"column_mapping_{board_id}", json.dumps(column_mapping)
    )
    logger.info(
        "Saved column mapping for board %s: %d fields mapped",
        board_id, len(column_mapping),
    )
    return await _render_connect_status(ctx)


@monday_sync_app.route("/_fragments/settings/configure-labels")
async def configure_labels(request: Request):
    """Render label mapping form for status and priority columns."""
    ctx: AppContext = request.app.state.ctx
    board_id = request.query_params.get("board_id", "").strip()
    if not board_id:
        return HTMLResponse(
            '<div class="alert alert-error">Missing board_id parameter.</div>'
        )

    # Read column mapping to find status/priority column IDs
    mapping_json = await ctx.settings.get(f"column_mapping_{board_id}")
    if not mapping_json:
        return HTMLResponse(
            '<div class="alert alert-error">No column mapping configured for this board. Configure columns first.</div>'
        )
    column_mapping = json.loads(mapping_json)

    status_col_id = column_mapping.get("taskStatus")
    priority_col_id = column_mapping.get("priority")

    if not status_col_id and not priority_col_id:
        return HTMLResponse(
            '<div class="alert alert-error">No status or priority columns mapped. Configure columns first.</div>'
        )

    client = _make_client(ctx)
    try:
        columns = await client.get_board_columns(int(board_id))
    except Exception as exc:
        logger.warning("Failed to fetch columns for board %s: %s", board_id, exc)
        return HTMLResponse(
            '<div class="alert alert-error">Could not fetch board columns.</div>'
        )

    # Build column lookup
    col_by_id = {col["id"]: col for col in columns}

    def _parse_labels(col_id: str | None) -> list[tuple[str, str]]:
        """Parse labels from a column's settings_str. Returns [(index, label_text), ...]."""
        if not col_id or col_id not in col_by_id:
            return []
        col = col_by_id[col_id]
        settings_str = col.get("settings_str", "")
        if not settings_str:
            return []
        try:
            settings = json.loads(settings_str)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "Malformed settings_str for column %s on board %s",
                col_id, board_id,
            )
            return []
        labels = settings.get("labels", {})
        if not isinstance(labels, dict):
            return []
        return sorted(labels.items(), key=lambda x: x[0])

    status_labels = _parse_labels(status_col_id)
    priority_labels = _parse_labels(priority_col_id)

    # Read existing label mappings
    label_json = await ctx.settings.get(f"label_mapping_{board_id}")
    label_mapping = json.loads(label_json) if label_json else {}
    current_status_mapping = label_mapping.get("status_label_mapping", {})
    current_priority_mapping = label_mapping.get("priority_label_mapping", {})

    # Find board name
    boards = await client.get_boards()
    board_name = board_id
    for b in boards:
        if str(b.get("id")) == str(board_id):
            board_name = b.get("name", board_id)
            break

    return HTMLResponse(ctx.render_template(
        "configure_labels.html",
        board_id=board_id,
        board_name=board_name,
        status_labels=status_labels,
        priority_labels=priority_labels,
        bpkm_status_values=BPKM_STATUS_VALUES,
        bpkm_priority_values=BPKM_PRIORITY_VALUES,
        current_status_mapping=current_status_mapping,
        current_priority_mapping=current_priority_mapping,
    ))


@monday_sync_app.route("/_fragments/settings/save-label-mapping", methods=["POST"])
async def save_label_mapping(request: Request):
    """Save per-board status and priority label mappings."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    board_id = form.get("board_id", "").strip()
    if not board_id:
        return HTMLResponse(
            '<div class="alert alert-error">Missing board_id.</div>'
        )

    # Re-read column mapping to know which columns to parse labels from
    mapping_json = await ctx.settings.get(f"column_mapping_{board_id}")
    column_mapping = json.loads(mapping_json) if mapping_json else {}

    status_col_id = column_mapping.get("taskStatus")
    priority_col_id = column_mapping.get("priority")

    # Fetch columns to get the label indices
    client = _make_client(ctx)
    columns = await client.get_board_columns(int(board_id))
    col_by_id = {col["id"]: col for col in columns}

    def _get_label_indices(col_id: str | None) -> list[str]:
        if not col_id or col_id not in col_by_id:
            return []
        col = col_by_id[col_id]
        settings_str = col.get("settings_str", "")
        if not settings_str:
            return []
        try:
            settings = json.loads(settings_str)
        except (json.JSONDecodeError, TypeError):
            return []
        labels = settings.get("labels", {})
        if not isinstance(labels, dict):
            return []
        return sorted(labels.keys())

    # Build status label mapping: label_text → bpkm value
    status_label_mapping: dict[str, str] = {}
    if status_col_id and status_col_id in col_by_id:
        for idx in _get_label_indices(status_col_id):
            col = col_by_id[status_col_id]
            settings = json.loads(col.get("settings_str", "{}"))
            label_text = settings.get("labels", {}).get(idx, "")
            bpkm_val = form.get(f"status_label_{idx}", "").strip()
            if bpkm_val:
                status_label_mapping[label_text] = bpkm_val

    # Build priority label mapping
    priority_label_mapping: dict[str, str] = {}
    if priority_col_id and priority_col_id in col_by_id:
        for idx in _get_label_indices(priority_col_id):
            col = col_by_id[priority_col_id]
            settings = json.loads(col.get("settings_str", "{}"))
            label_text = settings.get("labels", {}).get(idx, "")
            bpkm_val = form.get(f"priority_label_{idx}", "").strip()
            if bpkm_val:
                priority_label_mapping[label_text] = bpkm_val

    label_mapping = {
        "status_label_mapping": status_label_mapping,
        "priority_label_mapping": priority_label_mapping,
    }
    await ctx.settings.set(
        f"label_mapping_{board_id}", json.dumps(label_mapping)
    )
    logger.info(
        "Saved label mapping for board %s: %d status labels, %d priority labels",
        board_id, len(status_label_mapping), len(priority_label_mapping),
    )
    return await _render_connect_status(ctx)


@monday_sync_app.route("/_fragments/settings/boards", methods=["POST"])
async def save_boards(request: Request):
    """Save selected board IDs for sync."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    board_ids = form.getlist("board_ids")
    await ctx.settings.set("selected_boards", json.dumps(board_ids))
    logger.info("Saved sync boards: %s", board_ids)
    return await _render_connect_status(ctx)


@monday_sync_app.route("/_fragments/settings/sync-config", methods=["POST"])
async def save_sync_config(request: Request):
    """Save sync direction and poll interval settings."""
    ctx: AppContext = request.app.state.ctx
    form = await request.form()
    sync_direction = form.get("sync_direction", "pull-only")
    poll_interval = form.get("poll_interval", "15m")
    await ctx.settings.set("sync_direction", sync_direction)
    await ctx.settings.set("poll_interval", poll_interval)
    logger.info(
        "Saved sync config: direction=%s interval=%s",
        sync_direction, poll_interval,
    )
    return await _render_connect_status(ctx)


@monday_sync_app.route("/_fragments/settings/sync-now", methods=["POST"])
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


@monday_sync_app.route("/_fragments/connect/disconnect", methods=["POST"])
async def disconnect_handler(request: Request):
    """Disconnect from Monday.com and clear stored credentials."""
    ctx: AppContext = request.app.state.ctx
    await clear_credentials(ctx.state)
    logger.info("Disconnected from Monday.com")
    return HTMLResponse(ctx.render_template("connect.html", error=None))


@monday_sync_app.task("poll-tasks")
async def poll_tasks(ctx: AppContext):
    """Poll Monday.com for updated items and sync changes to SemPKM."""
    from services.sync_engine import pull_sync

    logger.info("poll-tasks: starting pull sync")
    try:
        result = await pull_sync(ctx)
        logger.info("poll-tasks: completed — %s", result)
        return result
    except Exception as exc:
        logger.error("poll-tasks: sync failed — %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}


@monday_sync_app.task("push-changes")
async def push_changes(ctx: AppContext):
    """Push local task changes back to Monday.com."""
    from services.sync_engine import push_sync

    logger.info("push-changes: starting push sync")
    try:
        result = await push_sync(ctx)
        logger.info("push-changes: completed — %s", result)
        return result
    except Exception as exc:
        logger.error("push-changes: push failed — %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}


@monday_sync_app.on_startup
def on_startup(ctx: AppContext):
    logger.info("Monday.com Sync app started: %s", ctx.app_id)


@monday_sync_app.on_shutdown
def on_shutdown(ctx: AppContext):
    logger.info("Monday.com Sync app stopped: %s", ctx.app_id)
