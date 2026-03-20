"""Pull sync engine — fetches Monday.com items and creates/updates bpkm:Task objects.

Orchestrates MondayClient, field mapper, person matcher, and auth
into a complete Monday.com → bpkm:Task pull sync pipeline.  Commands
bypass the SDK's ``CommandClient`` (which enforces IRI prefix checks)
by posting directly to ``/api/commands/bulk`` via the shared httpx client.

Two-phase bulk for new items:
  Phase 1: ``object.create`` commands (no IRI needed — platform assigns it)
  Phase 2: SPARQL-discover minted IRIs, then submit ``body.set`` / ``edge.create``
  Phase 3: Subitem → parentTask edge creation

For existing items, all commands (patch, body, edge) go in one batch
because the IRI is already known from the SPARQL lookup.

Monday.com-specific differences from Jira pattern:
  - Per-board iteration with per-board column mapping config
  - Group title from ``item["group"]["title"]`` (not column values)
  - Subitems → parentTask edges (analogous to Jira Epic→child)
  - No delta query — content comparison for change detection
  - Column mapping is user-configurable per board
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

try:
    from services.field_mapper import (
        build_task_properties,
        compute_slug,
        BPKM,
    )
    from services.person_matcher import PersonMatcher
    from services.auth import get_connection_status
    from services.monday_client import MondayClient
except ImportError:
    from field_mapper import (
        build_task_properties,
        compute_slug,
        BPKM,
    )
    from person_matcher import PersonMatcher
    from auth import get_connection_status
    from monday_client import MondayClient

logger = logging.getLogger("monday_sync.sync")

BATCH_SIZE = 1000  # Max commands per bulk POST


# ---------------------------------------------------------------------------
# SPARQL lookup helpers
# ---------------------------------------------------------------------------


async def _find_existing_task(graph_client, slug: str) -> dict | None:
    """Check whether a Task with the given slug already exists.

    Uses ``STRENDS`` to match the slug suffix of the IRI without
    needing to know the platform's base namespace.

    Returns ``{"iri", "status", "externalId", "lastSyncedAt"}`` or None.
    """
    sparql = (
        "SELECT ?task ?status ?extId ?lastSynced WHERE {\n"
        f"  ?task a <{BPKM}Task> .\n"
        f'  ?task <{BPKM}externalProvider> "monday" .\n'
        f'  FILTER(STRENDS(STR(?task), "/Task/{slug}"))\n'
        f"  OPTIONAL {{ ?task <{BPKM}taskStatus> ?status }}\n"
        f"  OPTIONAL {{ ?task <{BPKM}externalId> ?extId }}\n"
        f"  OPTIONAL {{ ?task <{BPKM}lastSyncedAt> ?lastSynced }}\n"
        "} LIMIT 1"
    )
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    row = bindings[0]
    return {
        "iri": row["task"]["value"],
        "status": row.get("status", {}).get("value"),
        "externalId": row.get("extId", {}).get("value"),
        "lastSyncedAt": row.get("lastSynced", {}).get("value"),
    }


async def _find_all_tasks_for_board(
    graph_client, board_id: int | str,
) -> list[dict]:
    """Find all Monday-synced tasks linked to a specific board.

    Uses ``CONTAINS`` on the ``externalUrl`` to match tasks belonging
    to the given board.  Returns a list of dicts with task IRIs and
    key property values for content comparison.

    Returns:
        List of dicts with keys: ``iri``, ``status``, ``priority``,
        ``dueDate``, ``title``, ``lastSynced``.
    """
    sparql = (
        "SELECT ?task ?status ?priority ?dueDate ?title ?lastSynced WHERE {\n"
        f"  ?task a <{BPKM}Task> .\n"
        f'  ?task <{BPKM}externalProvider> "monday" .\n'
        f"  ?task <{BPKM}externalUrl> ?url .\n"
        f'  FILTER(CONTAINS(STR(?url), "/boards/{board_id}/"))\n'
        f"  OPTIONAL {{ ?task <{BPKM}taskStatus> ?status }}\n"
        f"  OPTIONAL {{ ?task <{BPKM}priority> ?priority }}\n"
        f"  OPTIONAL {{ ?task <{BPKM}dueDate> ?dueDate }}\n"
        f"  OPTIONAL {{ ?task <dcterms:title> ?title }}\n"
        f"  OPTIONAL {{ ?task <{BPKM}lastSyncedAt> ?lastSynced }}\n"
        "}"
    )
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    tasks = []
    for row in bindings:
        tasks.append({
            "iri": row["task"]["value"],
            "status": row.get("status", {}).get("value"),
            "priority": row.get("priority", {}).get("value"),
            "dueDate": row.get("dueDate", {}).get("value"),
            "title": row.get("title", {}).get("value"),
            "lastSynced": row.get("lastSynced", {}).get("value"),
        })
    return tasks


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------


def _has_changes(existing: dict, new_properties: dict) -> bool:
    """Determine whether an existing task needs updating.

    Since Monday.com has no ``updatedAt`` filter for delta queries,
    change detection compares key property values.  For the initial
    implementation, always returns True — the two-phase bulk is
    idempotent, so correctness is prioritised over performance.

    A future optimisation can compare status/priority/title to skip
    no-op updates.

    Args:
        existing: Dict from ``_find_existing_task()`` with ``iri``,
            ``status``, ``externalId``, ``lastSyncedAt``.
        new_properties: Property dict built by ``build_task_properties()``.

    Returns:
        True if the task should be updated (always True for now).
    """
    # Idempotent: always process — correctness over performance.
    # Future optimisation: compare existing["status"] vs
    # new_properties.get(f"{BPKM}taskStatus"), etc.
    return True


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------


def _build_create_command(slug: str, properties: dict, obj_type: str) -> dict:
    """Build an ``object.create`` command for a new Task.

    Args:
        slug: Deterministic slug for the object.
        properties: Property dict (full IRI keys).
        obj_type: Full IRI type, e.g. ``{BPKM}Task``.
    """
    return {
        "command": "object.create",
        "params": {
            "type": obj_type,
            "slug": slug,
            "properties": properties,
        },
    }


def _build_update_commands(
    existing_iri: str,
    properties: dict,
    description: str | None,
    assignee_iri: str | None,
) -> list[dict]:
    """Build patch / body.set / edge.create commands for an existing object."""
    cmds: list[dict] = []

    # Always patch with current properties (idempotent)
    cmds.append({
        "command": "object.patch",
        "params": {"iri": existing_iri, "properties": properties},
    })

    if description:
        cmds.append({
            "command": "body.set",
            "params": {"iri": existing_iri, "body": description},
        })

    if assignee_iri:
        cmds.append({
            "command": "edge.create",
            "params": {
                "source": existing_iri,
                "predicate": f"{BPKM}assignedTo",
                "target": assignee_iri,
            },
        })

    return cmds


# ---------------------------------------------------------------------------
# Bulk submission
# ---------------------------------------------------------------------------


async def _submit_commands_batched(
    http_client,
    commands: list[dict],
    summary: str,
    source: str,
) -> list[dict]:
    """Submit commands in batches of ≤ BATCH_SIZE.

    Posts directly to ``/api/commands/bulk`` via the shared httpx client,
    bypassing the SDK's IRI prefix checks.
    """
    results = []
    for i in range(0, len(commands), BATCH_SIZE):
        batch = commands[i : i + BATCH_SIZE]
        payload = {
            "commands": batch,
            "summary": summary,
            "source": source,
        }
        resp = await http_client.post("/api/commands/bulk", json=payload)
        resp.raise_for_status()
        results.append(resp.json())
    return results


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------


def _compute_status(
    created: int, updated: int, skipped: int, errors: int,
) -> str:
    """Determine the overall sync status string.

    - ``"success"`` — at least one create/update and no errors
    - ``"partial"`` — some succeeded and some failed
    - ``"error"`` — all items failed
    - ``"success"`` — no items processed (empty is still success)
    """
    total_processed = created + updated + skipped
    if errors == 0:
        return "success"
    if total_processed > 0:
        return "partial"
    return "error"


def _make_result(
    status: str,
    start_time: float,
    *,
    created: int = 0,
    updated: int = 0,
    skipped: int = 0,
    errors: int = 0,
    failed_items: list[str] | None = None,
    reason: str | None = None,
    parent_links: int = 0,
) -> dict:
    """Build a standardised result dict for pull_sync.

    Keys match the connect_status.html template expectations.
    """
    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    result: dict = {
        "status": status,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "failed_items": failed_items or [],
        "duration_ms": elapsed_ms,
        "parent_links": parent_links,
    }
    if reason:
        result["reason"] = reason
    return result


# ---------------------------------------------------------------------------
# Main pull sync
# ---------------------------------------------------------------------------


async def pull_sync(ctx) -> dict:
    """Run the full Monday.com → bpkm:Task pull sync pipeline.

    Steps:
      1. Check auth status
      2. Read selected boards from settings
      3. Create PersonMatcher
      4. Per-board iteration:
         a. Read column mapping config for the board
         b. Read label mappings for status/priority
         c. Fetch all items (paginated)
         d. Process each item → Task (create or update)
         e. Fetch and process subitems → Task + parentTask edge
      5. Phase 1: submit create commands
      6. Phase 2: discover minted IRIs, submit body.set + edge.create
      7. Phase 3: subitem → parentTask edge creation
      8. Submit all follow-up commands
      9. Store last_sync_at and last_pull_result

    Returns a result dict with ``status``, ``created``, ``updated``,
    ``skipped``, ``errors``, ``failed_items``, ``parent_links``,
    and ``duration_ms``.
    """
    start_time = time.monotonic()

    # 1. Auth check
    client = MondayClient(http_client=ctx.http, state_client=ctx.state)
    status = await get_connection_status(ctx.state, client)
    if not status["connected"]:
        logger.info("pull_sync: skipping — not connected")
        return _make_result("skipped", start_time, reason="not connected")

    # 2. Read selected boards
    selected_boards_json = await ctx.settings.get("selected_boards")
    selected_boards = (
        json.loads(selected_boards_json) if selected_boards_json else []
    )
    if not selected_boards:
        logger.info("pull_sync: skipping — no boards selected")
        return _make_result("skipped", start_time, reason="no boards selected")

    # 3. Create PersonMatcher (Monday.com: graph, commands, monday_client)
    person_matcher = PersonMatcher(ctx.graph, ctx.commands, client)
    http_client = ctx.commands._client  # bypass SDK for bulk commands

    sync_timestamp = datetime.now(timezone.utc).isoformat()

    # Tracking
    create_commands: list[dict] = []
    update_commands: list[dict] = []
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    failed_items: list[str] = []

    # Deferred for Phase 2
    new_task_descriptions: dict[str, str] = {}   # slug → description
    new_task_assignees: dict[str, str] = {}       # slug → person IRI

    # Deferred for Phase 3 (subitem → parentTask)
    subitem_parent_map: dict[str, str] = {}       # subitem_slug → parent_slug

    # ---- 4. Per-board iteration ----
    for board_id_str in selected_boards:
        board_id = int(board_id_str)

        # Read column mapping config for this board
        mapping_json = await ctx.settings.get(f"column_mapping_{board_id}")
        if not mapping_json:
            logger.warning(
                "No column mapping for board %s, skipping", board_id,
            )
            continue
        mapping_config = json.loads(mapping_json)
        column_mapping = mapping_config.get("column_mapping", {})

        # Read label mappings
        label_json = await ctx.settings.get(f"label_mapping_{board_id}")
        label_config = json.loads(label_json) if label_json else {}
        status_label_mapping = label_config.get("status_label_mapping")
        priority_label_mapping = label_config.get("priority_label_mapping")

        # Fetch all items from this board (paginated)
        items = await client.get_all_board_items(board_id)
        logger.info("Board %s: fetched %d items", board_id, len(items))

        # Collect parent item IDs for subitem fetching
        parent_item_ids = [
            int(item["id"]) for item in items if item.get("id")
        ]

        # ---- Process each item ----
        for item in items:
            try:
                item_id = str(item.get("id", ""))
                item_name = item.get("name", "")
                slug = compute_slug(item_name, item_id)

                existing = await _find_existing_task(ctx.graph, slug)

                # Build properties using stored mapping
                properties, assignee_user_id = build_task_properties(
                    item,
                    column_mapping,
                    status_label_mapping=status_label_mapping,
                    priority_label_mapping=priority_label_mapping,
                    board_id=board_id,
                    sync_time=sync_timestamp,
                )

                # Set taskGroup from item.group.title (NOT column_values)
                group_info = item.get("group")
                if group_info and isinstance(group_info, dict):
                    group_title = group_info.get("title")
                    if group_title:
                        properties[f"{BPKM}taskGroup"] = group_title

                # Resolve assignee
                assignee_iri = None
                if assignee_user_id:
                    try:
                        assignee_iri = await person_matcher.resolve(
                            str(assignee_user_id), item_name,
                        )
                    except Exception as exc:
                        logger.warning(
                            "Assignee resolution failed for %s: %s",
                            item_id, exc,
                        )

                # Description from column mapping (if mapped)
                description = properties.pop(f"{BPKM}description", None)

                if existing:
                    # Content comparison — skip if unchanged
                    changed = _has_changes(existing, properties)
                    if not changed:
                        skipped_count += 1
                        continue

                    update_commands.extend(
                        _build_update_commands(
                            existing["iri"], properties,
                            description, assignee_iri,
                        )
                    )
                    updated_count += 1
                else:
                    create_commands.append(
                        _build_create_command(
                            slug, properties, f"{BPKM}Task",
                        )
                    )
                    if description:
                        new_task_descriptions[slug] = description
                    if assignee_iri:
                        new_task_assignees[slug] = assignee_iri
                    created_count += 1

            except Exception as e:
                failed_items.append(str(item.get("id", "unknown")))
                error_count += 1
                logger.warning(
                    "Error processing item %s: %s", item.get("id"), e,
                )

        # ---- Fetch and process subitems for this board ----
        if parent_item_ids:
            try:
                subitems = await client.get_subitems(parent_item_ids)
                logger.info(
                    "Board %s: fetched %d subitems",
                    board_id, len(subitems),
                )
                for subitem in subitems:
                    try:
                        sub_id = str(subitem.get("id", ""))
                        sub_name = subitem.get("name", "")
                        sub_slug = compute_slug(sub_name, sub_id)
                        parent_id = str(subitem.get("parent_item_id", ""))

                        # Find parent slug from the items list
                        parent_item = next(
                            (
                                i
                                for i in items
                                if str(i.get("id")) == parent_id
                            ),
                            None,
                        )
                        if parent_item:
                            parent_slug = compute_slug(
                                parent_item["name"], parent_id,
                            )
                            subitem_parent_map[sub_slug] = parent_slug

                        existing = await _find_existing_task(
                            ctx.graph, sub_slug,
                        )

                        sub_props, sub_assignee_id = build_task_properties(
                            subitem,
                            column_mapping,
                            status_label_mapping=status_label_mapping,
                            priority_label_mapping=priority_label_mapping,
                            board_id=board_id,
                            sync_time=sync_timestamp,
                        )

                        # Subitem group from group.title
                        sub_group = subitem.get("group")
                        if sub_group and isinstance(sub_group, dict):
                            gt = sub_group.get("title")
                            if gt:
                                sub_props[f"{BPKM}taskGroup"] = gt

                        sub_assignee_iri = None
                        if sub_assignee_id:
                            try:
                                sub_assignee_iri = (
                                    await person_matcher.resolve(
                                        str(sub_assignee_id), sub_name,
                                    )
                                )
                            except Exception:
                                pass

                        sub_desc = sub_props.pop(
                            f"{BPKM}description", None,
                        )

                        if existing:
                            if not _has_changes(existing, sub_props):
                                skipped_count += 1
                                continue
                            update_commands.extend(
                                _build_update_commands(
                                    existing["iri"],
                                    sub_props,
                                    sub_desc,
                                    sub_assignee_iri,
                                )
                            )
                            updated_count += 1
                        else:
                            create_commands.append(
                                _build_create_command(
                                    sub_slug, sub_props, f"{BPKM}Task",
                                )
                            )
                            if sub_desc:
                                new_task_descriptions[sub_slug] = sub_desc
                            if sub_assignee_iri:
                                new_task_assignees[sub_slug] = (
                                    sub_assignee_iri
                                )
                            created_count += 1

                    except Exception as e:
                        failed_items.append(
                            str(subitem.get("id", "unknown")),
                        )
                        error_count += 1
                        logger.warning(
                            "Error processing subitem %s: %s",
                            subitem.get("id"), e,
                        )
            except Exception as exc:
                logger.warning(
                    "Subitem fetch failed for board %s: %s", board_id, exc,
                )

    # ---- Phase 1: submit create commands ----
    if create_commands:
        logger.info(
            "Phase 1: submitting %d create commands", len(create_commands),
        )
        await _submit_commands_batched(
            http_client,
            create_commands,
            f"Monday.com sync: created {len(create_commands)} tasks",
            "monday-sync",
        )

    # ---- Phase 2: discover minted IRIs, submit body.set + edge.create ----
    phase2_commands: list[dict] = []

    for slug, desc in new_task_descriptions.items():
        task_info = await _find_existing_task(ctx.graph, slug)
        if task_info:
            phase2_commands.append({
                "command": "body.set",
                "params": {"iri": task_info["iri"], "body": desc},
            })

    for slug, p_iri in new_task_assignees.items():
        task_info = await _find_existing_task(ctx.graph, slug)
        if task_info:
            phase2_commands.append({
                "command": "edge.create",
                "params": {
                    "source": task_info["iri"],
                    "predicate": f"{BPKM}assignedTo",
                    "target": p_iri,
                },
            })

    # ---- Phase 3: subitem → parentTask edges ----
    parent_link_commands: list[dict] = []
    for sub_slug, parent_slug in subitem_parent_map.items():
        sub_info = await _find_existing_task(ctx.graph, sub_slug)
        parent_info = await _find_existing_task(ctx.graph, parent_slug)
        if sub_info and parent_info:
            parent_link_commands.append({
                "command": "edge.create",
                "params": {
                    "source": sub_info["iri"],
                    "predicate": f"{BPKM}parentTask",
                    "target": parent_info["iri"],
                },
            })

    if parent_link_commands:
        logger.info(
            "Phase 3: %d subitem→parentTask edges",
            len(parent_link_commands),
        )

    # ---- Submit all follow-up commands ----
    all_follow_up = update_commands + phase2_commands + parent_link_commands
    if all_follow_up:
        logger.info(
            "Submitting %d follow-up commands "
            "(updates=%d, phase2=%d, parent-links=%d)",
            len(all_follow_up),
            len(update_commands),
            len(phase2_commands),
            len(parent_link_commands),
        )
        await _submit_commands_batched(
            http_client,
            all_follow_up,
            f"Monday.com sync: {updated_count} updates, "
            f"{len(phase2_commands)} follow-ups, "
            f"{len(parent_link_commands)} parent links",
            "monday-sync",
        )

    # ---- Store sync state ----
    await ctx.state.set("last_sync_at", sync_timestamp)

    result = _make_result(
        _compute_status(created_count, updated_count, skipped_count, error_count),
        start_time,
        created=created_count,
        updated=updated_count,
        skipped=skipped_count,
        errors=error_count,
        failed_items=failed_items,
        parent_links=len(parent_link_commands),
    )
    logger.info("Pull sync complete: %s", result)
    await ctx.state.set("last_pull_result", json.dumps(result))
    return result


# ---------------------------------------------------------------------------
# Push sync — stub for S03
# ---------------------------------------------------------------------------


async def push_sync(ctx) -> dict:
    """Push stub — real push sync implemented in S03."""
    return {"status": "skipped", "reason": "not implemented"}
