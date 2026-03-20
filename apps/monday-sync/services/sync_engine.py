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
        build_reverse_column_values,
        compute_slug,
        BPKM,
    )
    from services.person_matcher import PersonMatcher
    from services.auth import get_connection_status
    from services.monday_client import MondayClient
    from services.loop_guard import LoopGuard
except ImportError:
    from field_mapper import (
        build_task_properties,
        build_reverse_column_values,
        compute_slug,
        BPKM,
    )
    from person_matcher import PersonMatcher
    from auth import get_connection_status
    from monday_client import MondayClient
    from loop_guard import LoopGuard

logger = logging.getLogger("monday_sync.sync")

BATCH_SIZE = 1000  # Max commands per bulk POST

# Module-level LoopGuard singleton — shared between push and pull sync
_loop_guard = LoopGuard(ttl_seconds=30)


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


async def _find_task_by_monday_item_id(
    graph_client, item_id: int | str,
) -> str | None:
    """Find a Monday-synced Task IRI by the Monday.com item ID.

    Looks up tasks whose ``externalUrl`` contains ``/pulses/{item_id}``.

    Returns:
        Task IRI string, or None if not found.
    """
    sparql = (
        "SELECT ?task WHERE {\n"
        f"  ?task a <{BPKM}Task> .\n"
        f'  ?task <{BPKM}externalProvider> "monday" .\n'
        f"  ?task <{BPKM}externalUrl> ?url .\n"
        f'  FILTER(CONTAINS(STR(?url), "/pulses/{item_id}"))\n'
        "} LIMIT 1"
    )
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    return bindings[0]["task"]["value"]


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
# URL parsing helpers
# ---------------------------------------------------------------------------


def parse_external_url(url: str | None) -> tuple[str, str] | None:
    """Parse board_id and item_id from a Monday.com URL.

    Expected format: ``https://monday.com/boards/{board_id}/pulses/{item_id}``

    Returns:
        ``(board_id, item_id)`` as strings, or ``None`` if parsing fails.
    """
    if not url or not isinstance(url, str):
        return None
    try:
        parts = url.split("/")
        # Find /boards/{id}/pulses/{id} segments
        boards_idx = None
        for i, part in enumerate(parts):
            if part == "boards" and i + 1 < len(parts):
                boards_idx = i
                break
        if boards_idx is None:
            return None
        board_id = parts[boards_idx + 1]
        if not board_id:
            return None
        # Find /pulses/{id} after /boards/{id}
        pulses_idx = None
        for i in range(boards_idx + 2, len(parts)):
            if parts[i] == "pulses" and i + 1 < len(parts):
                pulses_idx = i
                break
        if pulses_idx is None:
            return None
        item_id = parts[pulses_idx + 1].rstrip("/")
        if not item_id:
            return None
        return (board_id, item_id)
    except (IndexError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Push sync SPARQL helpers
# ---------------------------------------------------------------------------


async def _find_changed_tasks(graph_client) -> list[dict]:
    """Find Monday-synced tasks with local modifications.

    A task is changed when:
    - ``externalProvider = "monday"``
    - ``dcterms:modified > bpkm:lastSyncedAt`` (or no lastSyncedAt)

    Returns a list of dicts with keys:
    ``iri``, ``extUrl``, ``status``, ``priority``, ``title``,
    ``dueDate``, ``lastSynced``.
    """
    sparql = (
        "SELECT ?task ?extUrl ?status ?priority ?title ?dueDate ?lastSynced WHERE {\n"
        f'  ?task a <{BPKM}Task> .\n'
        f'  ?task <{BPKM}externalProvider> "monday" .\n'
        f'  ?task <{BPKM}externalUrl> ?extUrl .\n'
        f'  OPTIONAL {{ ?task <{BPKM}taskStatus> ?status }}\n'
        f'  OPTIONAL {{ ?task <{BPKM}priority> ?priority }}\n'
        f'  OPTIONAL {{ ?task <dcterms:title> ?title }}\n'
        f'  OPTIONAL {{ ?task <{BPKM}dueDate> ?dueDate }}\n'
        f'  OPTIONAL {{ ?task <{BPKM}lastSyncedAt> ?lastSynced }}\n'
        f'  OPTIONAL {{ ?task <dcterms:modified> ?modified }}\n'
        f'  FILTER(!BOUND(?lastSynced) || !BOUND(?modified) || STR(?modified) > STR(?lastSynced))\n'
        "}"
    )
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])

    tasks = []
    for row in bindings:
        tasks.append({
            "iri": row["task"]["value"],
            "extUrl": row.get("extUrl", {}).get("value"),
            "status": row.get("status", {}).get("value"),
            "priority": row.get("priority", {}).get("value"),
            "title": row.get("title", {}).get("value"),
            "dueDate": row.get("dueDate", {}).get("value"),
            "lastSynced": row.get("lastSynced", {}).get("value"),
        })
    return tasks


async def _get_task_body(graph_client, iri: str) -> str | None:
    """Read task body text from the graph by IRI.

    Queries ``<iri> <urn:sempkm:body> ?body`` and returns the body
    text string, or ``None`` if no body is stored.
    """
    sparql = (
        "SELECT ?body WHERE {\n"
        f"  <{iri}> <urn:sempkm:body> ?body\n"
        "} LIMIT 1"
    )
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    return bindings[0].get("body", {}).get("value")


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
# Dependency edge processing
# ---------------------------------------------------------------------------


async def _process_dependencies(
    graph_client,
    dependency_pairs: list[tuple[str, list[int]]],
) -> list[dict]:
    """Create ``bpkm:dependsOn`` edge commands from dependency column data.

    For each ``(source_iri, dependency_item_ids)`` pair, looks up the
    target task IRI by Monday.com item ID and creates an ``edge.create``
    command.

    Args:
        graph_client: Graph client for SPARQL lookups.
        dependency_pairs: List of ``(source_task_iri, [dep_item_id, ...])``
            tuples.

    Returns:
        List of ``edge.create`` command dicts.
    """
    commands: list[dict] = []
    for source_iri, dep_ids in dependency_pairs:
        for dep_id in dep_ids:
            try:
                target_iri = await _find_task_by_monday_item_id(
                    graph_client, dep_id,
                )
                if target_iri is None:
                    logger.debug(
                        "Dependency target item %s not found in graph, "
                        "skipping edge from %s",
                        dep_id, source_iri,
                    )
                    continue
                commands.append({
                    "command": "edge.create",
                    "params": {
                        "source": source_iri,
                        "predicate": f"{BPKM}dependsOn",
                        "target": target_iri,
                    },
                })
            except Exception as exc:
                logger.warning(
                    "Error processing dependency %s → %s: %s",
                    source_iri, dep_id, exc,
                )
    return commands


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
    dependency_edges: int = 0,
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
        "dependency_edges": dependency_edges,
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

    # Tag resolution: collect tag IDs per board, resolve in batch
    # Dependency edge processing: collect (source_iri, dep_item_ids) pairs
    dependency_pairs: list[tuple[str, list[int]]] = []

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
        # Track items with tag IDs for post-loop batch resolution
        all_tag_ids: set[int] = set()
        # Track properties dicts that contain tag ID lists (for substitution)
        props_with_tags: list[dict] = []

        for item in items:
            try:
                item_id = str(item.get("id", ""))

                # LoopGuard echo check — skip items recently pushed
                if _loop_guard.is_echo(item_id, "*"):
                    logger.debug(
                        "LoopGuard: skipping echo for item %s", item_id,
                    )
                    skipped_count += 1
                    continue

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

                # Pop dependency item IDs before creating commands
                dep_item_ids = properties.pop("_dependency_item_ids", None)

                # Collect tag IDs for batch resolution
                tag_value = properties.get(f"{BPKM}tags")
                if isinstance(tag_value, list) and tag_value and all(
                    isinstance(t, int) for t in tag_value
                ):
                    all_tag_ids.update(tag_value)
                    props_with_tags.append(properties)

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

                    # Collect dependency pairs for existing items
                    if dep_item_ids:
                        dependency_pairs.append(
                            (existing["iri"], dep_item_ids)
                        )

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
                    # Collect dependency pairs for new items (slug-based,
                    # resolved to IRI after Phase 1)
                    if dep_item_ids:
                        # Store slug temporarily; resolve to IRI in Phase 4
                        dependency_pairs.append(
                            (f"__slug__{slug}", dep_item_ids)
                        )
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

                        # LoopGuard echo check — skip subitems recently pushed
                        if _loop_guard.is_echo(sub_id, "*"):
                            logger.debug(
                                "LoopGuard: skipping echo for subitem %s",
                                sub_id,
                            )
                            skipped_count += 1
                            continue

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

        # ---- Tag resolution for this board ----
        if all_tag_ids:
            try:
                tag_list = await client.get_tags(list(all_tag_ids))
                tag_id_to_name: dict[int, str] = {
                    int(t["id"]): t["name"]
                    for t in tag_list
                    if isinstance(t, dict) and "id" in t and "name" in t
                }
                # Substitute tag IDs with names in all tracked properties
                for props in props_with_tags:
                    tag_ids = props.get(f"{BPKM}tags", [])
                    if isinstance(tag_ids, list):
                        resolved = [
                            tag_id_to_name.get(tid, str(tid))
                            for tid in tag_ids
                        ]
                        props[f"{BPKM}tags"] = ", ".join(resolved)
            except Exception as exc:
                logger.warning(
                    "Tag resolution failed for board %s: %s — "
                    "falling back to tag IDs",
                    board_id, exc,
                )
                # Fall back: convert integer IDs to comma-separated strings
                for props in props_with_tags:
                    tag_ids = props.get(f"{BPKM}tags", [])
                    if isinstance(tag_ids, list):
                        props[f"{BPKM}tags"] = ", ".join(
                            str(tid) for tid in tag_ids
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

    # ---- Phase 4: dependency edges ----
    dep_edge_commands: list[dict] = []
    if dependency_pairs:
        # Resolve slug-based source references to IRIs
        resolved_pairs: list[tuple[str, list[int]]] = []
        for source_ref, dep_ids in dependency_pairs:
            if source_ref.startswith("__slug__"):
                slug = source_ref[len("__slug__"):]
                task_info = await _find_existing_task(ctx.graph, slug)
                if task_info:
                    resolved_pairs.append((task_info["iri"], dep_ids))
            else:
                resolved_pairs.append((source_ref, dep_ids))
        dep_edge_commands = await _process_dependencies(
            ctx.graph, resolved_pairs,
        )
        if dep_edge_commands:
            logger.info(
                "Phase 4: %d dependency edges", len(dep_edge_commands),
            )

    # ---- Submit all follow-up commands ----
    all_follow_up = (
        update_commands + phase2_commands
        + parent_link_commands + dep_edge_commands
    )
    if all_follow_up:
        logger.info(
            "Submitting %d follow-up commands "
            "(updates=%d, phase2=%d, parent-links=%d, dep-edges=%d)",
            len(all_follow_up),
            len(update_commands),
            len(phase2_commands),
            len(parent_link_commands),
            len(dep_edge_commands),
        )
        await _submit_commands_batched(
            http_client,
            all_follow_up,
            f"Monday.com sync: {updated_count} updates, "
            f"{len(phase2_commands)} follow-ups, "
            f"{len(parent_link_commands)} parent links, "
            f"{len(dep_edge_commands)} dep edges",
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
        dependency_edges=len(dep_edge_commands),
    )
    logger.info("Pull sync complete: %s", result)
    await ctx.state.set("last_pull_result", json.dumps(result))
    return result


# ---------------------------------------------------------------------------
# Push sync — full pipeline (MON-09 / MON-10)
# ---------------------------------------------------------------------------


async def push_sync(ctx, monday_client=None) -> dict:
    """Push local task changes back to Monday.com.

    Pipeline:
      1. Check auth status
      2. Check sync direction — skip if pull-only
      3. Find locally changed tasks via SPARQL
      4. For each changed task:
         a. Parse Monday.com URL → board_id, item_id
         b. Load column mapping and label mapping for the board
         c. Build reverse column values from SPARQL properties
         d. Call ``change_multiple_column_values`` mutation
         e. Mark in LoopGuard (prevents echo on next pull)
         f. Update ``lastSyncedAt`` on the task
      5. Store ``last_push_result`` in state

    Args:
        ctx: SyncContext with state, settings, graph, commands, http.
        monday_client: Optional MondayClient for testing. If None,
            one is created from ``ctx.http`` and ``ctx.state``.

    Returns:
        Result dict with ``status``, ``pushed``, ``skipped``,
        ``errors``, and ``timestamp``.
    """
    # 1. Auth check
    if monday_client is None:
        monday_client = MondayClient(http_client=ctx.http, state_client=ctx.state)
    status = await get_connection_status(ctx.state, monday_client)
    if not status["connected"]:
        logger.info("push_sync: skipping — not connected")
        result = {"status": "skipped", "reason": "not connected"}
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    # 2. Check sync direction
    sync_direction = await ctx.settings.get("sync_direction") or "pull-only"
    if sync_direction == "pull-only":
        logger.info("push_sync: skipping — sync direction is pull-only")
        result = {"status": "skipped", "reason": "sync direction is pull-only"}
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    # 3. Find changed tasks
    changed_tasks = await _find_changed_tasks(ctx.graph)

    push_timestamp = datetime.now(timezone.utc).isoformat()

    if not changed_tasks:
        logger.info("push_sync: no changed tasks found")
        result = {
            "status": "success",
            "pushed": 0,
            "skipped": 0,
            "errors": [],
            "timestamp": push_timestamp,
        }
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    logger.info("push_sync: found %d changed tasks", len(changed_tasks))

    # 4. Push each changed task
    http_client = ctx.commands._client  # bypass SDK for bulk commands
    pushed_count = 0
    skipped_count = 0
    errors: list[dict] = []

    for task in changed_tasks:
        try:
            # 4a. Parse external URL → board_id, item_id
            parsed = parse_external_url(task.get("extUrl"))
            if parsed is None:
                logger.warning(
                    "push_sync: cannot parse URL for task %s: %s",
                    task["iri"], task.get("extUrl"),
                )
                skipped_count += 1
                continue
            board_id, item_id = parsed

            # 4b. Load column mapping for this board
            mapping_json = await ctx.settings.get(
                f"column_mapping_{board_id}",
            )
            if not mapping_json:
                logger.warning(
                    "push_sync: no column mapping for board %s, "
                    "skipping task %s",
                    board_id, task["iri"],
                )
                skipped_count += 1
                continue
            mapping_config = json.loads(mapping_json)
            column_mapping = mapping_config.get("column_mapping", {})

            # 4b-2. Load label mapping for reverse status/priority
            label_json = await ctx.settings.get(
                f"label_mapping_{board_id}",
            )
            label_config = json.loads(label_json) if label_json else {}
            status_label_mapping = label_config.get(
                "status_label_mapping", {},
            )
            priority_label_mapping = label_config.get(
                "priority_label_mapping", {},
            )

            # Build reverse mappings by inverting the label dicts
            reverse_status = (
                {v: k for k, v in status_label_mapping.items()}
                if status_label_mapping
                else None
            )
            reverse_priority = (
                {v: k for k, v in priority_label_mapping.items()}
                if priority_label_mapping
                else None
            )

            # 4c. Build task properties dict from SPARQL result
            task_props: dict = {}
            if task.get("title"):
                task_props["dcterms:title"] = task["title"]
            if task.get("status"):
                task_props[f"{BPKM}taskStatus"] = task["status"]
            if task.get("priority"):
                task_props[f"{BPKM}priority"] = task["priority"]
            if task.get("dueDate"):
                task_props[f"{BPKM}dueDate"] = task["dueDate"]

            # 4c-2. Build reverse column values
            column_values = build_reverse_column_values(
                task_props,
                column_mapping,
                reverse_status_mapping=reverse_status,
                reverse_priority_mapping=reverse_priority,
            )

            if not column_values:
                logger.debug(
                    "push_sync: no column values to push for %s",
                    task["iri"],
                )
                skipped_count += 1
                continue

            # 4d. Call Monday.com mutation
            await monday_client.change_multiple_column_values(
                int(board_id),
                int(item_id),
                json.dumps(column_values),
            )

            # 4e. Mark in LoopGuard
            _loop_guard.mark_pushed(item_id, "*")

            # 4f. Update lastSyncedAt on the task
            update_cmds = [{
                "command": "object.patch",
                "params": {
                    "iri": task["iri"],
                    "properties": {
                        f"{BPKM}lastSyncedAt": push_timestamp,
                    },
                },
            }]
            await _submit_commands_batched(
                http_client, update_cmds,
                f"Monday.com push sync: update lastSyncedAt for {task['iri']}",
                "monday-sync",
            )

            pushed_count += 1

        except Exception as e:
            errors.append({"iri": task["iri"], "error": str(e)})
            logger.warning(
                "push_sync: error pushing task %s: %s", task["iri"], e,
            )

    # 5. Build and store result
    if errors and pushed_count == 0 and skipped_count == 0:
        result_status = "error"
    elif errors:
        result_status = "partial"
    else:
        result_status = "success"

    result = {
        "status": result_status,
        "pushed": pushed_count,
        "skipped": skipped_count,
        "errors": errors,
        "timestamp": push_timestamp,
    }

    await ctx.state.set("last_push_result", json.dumps(result))
    logger.info("Push sync complete: %s", result)
    return result
