"""Pull sync engine — fetches Asana tasks and creates/updates bpkm:Task objects.

Orchestrates AsanaClient, field mapper, person matcher, and the bulk
command API into a complete pull sync pipeline.  Commands bypass the
SDK's ``CommandClient`` (which enforces IRI prefix checks) by posting
directly to ``/api/commands/bulk`` via the shared httpx client.

Two-phase bulk for new tasks:
  Phase 1: ``object.create`` commands (no IRI needed — platform assigns it)
  Phase 2: SPARQL-discover minted IRIs, then submit ``body.set`` + ``edge.create``

For existing tasks, all commands (patch, body, edge) go in one batch
because the IRI is already known from the SPARQL lookup.

Subtask recursion: ``_fetch_subtasks_recursive()`` walks the subtask
tree up to ``MAX_SUBTASK_DEPTH`` levels.  Each subtask is annotated
with ``_parent_gid`` so the sync engine can create ``dcterms:isPartOf``
edges linking child tasks to their parents.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

try:
    from services.field_mapper import (
        BPKM,
        build_task_properties,
        compute_task_slug,
        detect_milestone,
        extract_body,
        extract_assignee,
        extract_followers,
        extract_section_name,
        build_asana_patch,
        resolve_section_gid_for_status,
    )
    from services.person_matcher import PersonMatcher
    from services.auth import get_connection_status
    from services.asana_client import AsanaClient
except ImportError:
    from field_mapper import (
        BPKM,
        build_task_properties,
        compute_task_slug,
        detect_milestone,
        extract_body,
        extract_assignee,
        extract_followers,
        extract_section_name,
        build_asana_patch,
        resolve_section_gid_for_status,
    )
    from person_matcher import PersonMatcher
    from auth import get_connection_status
    from asana_client import AsanaClient

logger = logging.getLogger("asana.sync.engine")

BATCH_SIZE = 1000  # Max commands per bulk POST
MAX_SUBTASK_DEPTH = 5  # Limit subtask recursion depth

# Complete opt_fields for task fetching — every field needed by field_mapper
TASK_OPT_FIELDS = (
    "name,notes,html_notes,completed,completed_at,due_on,due_at,"
    "start_on,start_at,assignee,assignee.email,assignee.name,"
    "followers,followers.email,followers.name,"
    "tags,tags.name,"
    "memberships.section,memberships.section.name,"
    "custom_fields,custom_fields.name,custom_fields.gid,"
    "custom_fields.enum_value,custom_fields.enum_value.name,"
    "custom_fields.number_value,"
    "parent,permalink_url,resource_subtype,modified_at"
)


# ---------------------------------------------------------------------------
# SPARQL lookup
# ---------------------------------------------------------------------------


async def _find_existing_task(graph_client, slug: str) -> dict | None:
    """Check whether a Task with the given slug already exists.

    Uses ``STRENDS`` to match the slug suffix of the IRI without
    needing to know the platform's base namespace.

    Returns ``{"iri": ..., "status": ..., "externalId": ..., "lastSyncedAt": ...}``
    or None.
    """
    sparql = (
        "SELECT ?task ?status ?extId ?lastSynced WHERE {\n"
        f"  ?task a <{BPKM}Task> .\n"
        f'  ?task <{BPKM}externalProvider> "asana" .\n'
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


# ---------------------------------------------------------------------------
# Bulk submission
# ---------------------------------------------------------------------------


async def _submit_commands_batched(
    http_client,
    commands: list[dict],
) -> list[dict]:
    """Submit commands in batches of ≤ BATCH_SIZE.

    Posts directly to ``/api/commands/bulk`` via the shared httpx client,
    bypassing the SDK's IRI prefix checks.
    """
    if not commands:
        return []

    results = []
    for i in range(0, len(commands), BATCH_SIZE):
        batch = commands[i : i + BATCH_SIZE]
        payload = {
            "commands": batch,
            "summary": f"Asana sync: batch of {len(batch)} commands",
            "source": "asana-sync",
        }
        resp = await http_client.post("/api/commands/bulk", json=payload)
        resp.raise_for_status()
        results.append(resp.json())
    return results


# ---------------------------------------------------------------------------
# Field config reader
# ---------------------------------------------------------------------------


async def _read_field_config(state_client) -> dict:
    """Read field mapping configuration from StateClient.

    Reads all field mapping keys and assembles them into a dict
    suitable for ``build_task_properties(task, field_config, ...)``.

    Returns a dict with keys: ``status_source``, ``status_field_gid``,
    ``status_mapping``, ``priority_field_gid``, ``priority_mapping``,
    ``story_points_field_gid``.
    """
    status_source = await state_client.get("status_source") or "completed_only"
    status_field_gid = await state_client.get("status_field_gid") or ""
    priority_field_gid = await state_client.get("priority_field_gid") or ""
    story_points_field_gid = await state_client.get("story_points_field_gid") or ""

    status_mapping_json = await state_client.get("status_mapping")
    status_mapping = json.loads(status_mapping_json) if status_mapping_json else {}

    priority_mapping_json = await state_client.get("priority_mapping")
    priority_mapping = json.loads(priority_mapping_json) if priority_mapping_json else {}

    return {
        "status_source": status_source,
        "status_field_gid": status_field_gid,
        "status_mapping": status_mapping,
        "priority_field_gid": priority_field_gid,
        "priority_mapping": priority_mapping,
        "story_points_field_gid": story_points_field_gid,
    }


# ---------------------------------------------------------------------------
# Subtask recursion
# ---------------------------------------------------------------------------


async def _fetch_subtasks_recursive(
    client: AsanaClient,
    task_gid: str,
    opt_fields: str,
    depth: int = 0,
    max_depth: int = MAX_SUBTASK_DEPTH,
) -> list[dict]:
    """Fetch subtasks recursively up to *max_depth* levels.

    Each subtask dict is annotated with ``_parent_gid`` (the GID of its
    parent task) so the caller can create ``dcterms:isPartOf`` edges.

    Returns a flat list of all subtask dicts across all levels.
    """
    if depth >= max_depth:
        return []

    subtasks = await client.get_subtasks(task_gid, opt_fields)
    all_subtasks: list[dict] = []

    for subtask in subtasks:
        subtask["_parent_gid"] = task_gid
        all_subtasks.append(subtask)

        # Recurse into this subtask's children
        children = await _fetch_subtasks_recursive(
            client, subtask["gid"], opt_fields,
            depth=depth + 1, max_depth=max_depth,
        )
        all_subtasks.extend(children)

    return all_subtasks


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------


def _build_create_command(
    slug: str,
    type_iri: str,
    properties: dict,
) -> dict:
    """Build an ``object.create`` command for a new task."""
    return {
        "command": "object.create",
        "params": {
            "type": type_iri,
            "slug": slug,
            "properties": properties,
        },
    }


def _build_update_commands(
    existing_iri: str,
    properties: dict,
    body_text: str | None,
    assignee_iri: str | None,
    follower_iris: list[str] | None = None,
) -> list[dict]:
    """Build patch / body.set / edge.create commands for an existing task."""
    cmds: list[dict] = []

    # Always patch with current properties (idempotent)
    cmds.append({
        "command": "object.patch",
        "params": {"iri": existing_iri, "properties": properties},
    })

    if body_text:
        cmds.append({
            "command": "body.set",
            "params": {"iri": existing_iri, "body": body_text},
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

    if follower_iris:
        for f_iri in follower_iris:
            cmds.append({
                "command": "edge.create",
                "params": {
                    "source": existing_iri,
                    "predicate": f"{BPKM}followedBy",
                    "target": f_iri,
                },
            })

    return cmds


# ---------------------------------------------------------------------------
# Result builder
# ---------------------------------------------------------------------------


def _make_result(
    status: str,
    start_time: float,
    sync_timestamp: str,
    *,
    created: int = 0,
    updated: int = 0,
    unchanged: int = 0,
    errors: int = 0,
    error_details: list[dict] | None = None,
    reason: str | None = None,
) -> dict:
    """Build a structured pull result dict."""
    duration_ms = int((time.monotonic() - start_time) * 1000)
    result: dict = {
        "status": status,
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "errors": errors,
        "error_details": error_details or [],
        "duration_ms": duration_ms,
        "timestamp": sync_timestamp,
    }
    if reason:
        result["reason"] = reason
    return result


# ---------------------------------------------------------------------------
# Main pull sync
# ---------------------------------------------------------------------------


async def pull_sync(ctx) -> dict:
    """Run the full Asana → bpkm:Task pull sync pipeline.

    Steps:
      1. Check auth status
      2. Read selected project GIDs from state
      3. Read field mapping config from state
      4. Read ``last_sync_at`` for incremental sync
      5. Set up PersonMatcher and bulk HTTP client
      6. For each selected project:
         a. Fetch top-level tasks via ``client.get_tasks()``
         b. For each task: classify create/update, build properties
         c. Fetch subtasks recursively, process each the same way
      7. Phase 1: submit ``object.create`` commands for new tasks
      8. Phase 2: discover IRIs, submit ``body.set`` + ``edge.create``
      9. Submit update commands for existing tasks
     10. Update ``last_sync_at`` and ``last_pull_result`` in state
     11. Return result dict

    Per-task error isolation: exceptions on one task don't stop others.
    """
    start_time = time.monotonic()
    sync_timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Auth check
    status = await get_connection_status(ctx.state)
    if not status["connected"]:
        result = _make_result(
            "skipped", start_time, sync_timestamp,
            reason="not connected",
        )
        await ctx.state.set("last_pull_result", json.dumps(result))
        return result

    # 2. Read selected projects from state
    selected_json = await ctx.state.get("selected_projects")
    if not selected_json:
        result = _make_result(
            "skipped", start_time, sync_timestamp,
            reason="no projects selected",
        )
        await ctx.state.set("last_pull_result", json.dumps(result))
        return result

    selected_project_gids = json.loads(selected_json)
    if not selected_project_gids:
        result = _make_result(
            "skipped", start_time, sync_timestamp,
            reason="no projects selected",
        )
        await ctx.state.set("last_pull_result", json.dumps(result))
        return result

    # 3. Read field config
    field_config = await _read_field_config(ctx.state)

    # 4. Read incremental sync cursor
    last_sync_at = await ctx.state.get("last_sync_at")

    # 5. Set up PersonMatcher and HTTP client (bypass SDK for bulk)
    client = AsanaClient(http_client=ctx.http, state_client=ctx.state)
    person_matcher = PersonMatcher(ctx.graph, ctx.commands)
    http_client = ctx.commands._client  # D204 bypass

    create_commands: list[dict] = []
    update_commands: list[dict] = []
    created_count = 0
    updated_count = 0
    unchanged_count = 0
    error_count = 0
    error_details: list[dict] = []

    # Track phase-2 data: slug → body, slug → assignee IRI, slug → follower IRIs
    new_task_bodies: dict[str, str] = {}
    new_task_assignees: dict[str, str] = {}
    new_task_followers: dict[str, list[str]] = {}
    # Track subtask→parent relationships: child slug → parent slug
    subtask_parent_map: dict[str, str] = {}

    logger.info(
        "pull_sync: starting sync for %d projects",
        len(selected_project_gids),
    )

    # 6. Fetch and process tasks from each selected project
    for project_gid in selected_project_gids:
        try:
            tasks = await client.get_tasks(
                project_gid, TASK_OPT_FIELDS,
                modified_since=last_sync_at or None,
            )
        except Exception as exc:
            logger.warning(
                "Failed to fetch tasks from project %s: %s",
                project_gid, exc,
            )
            error_count += 1
            error_details.append({
                "task_gid": None,
                "project_gid": project_gid,
                "error": f"fetch failed: {exc}",
            })
            continue

        # Collect all tasks to process: top-level + subtasks
        all_tasks: list[dict] = []
        for task in tasks:
            all_tasks.append(task)
            # Fetch subtasks recursively
            try:
                subtasks = await _fetch_subtasks_recursive(
                    client, task["gid"], TASK_OPT_FIELDS,
                )
                all_tasks.extend(subtasks)
            except Exception as exc:
                logger.warning(
                    "Failed to fetch subtasks for task %s: %s",
                    task.get("gid"), exc,
                )
                # Non-fatal: continue processing the parent task

        # Process each task (top-level and subtasks)
        for task in all_tasks:
            task_gid = task.get("gid", "")
            try:
                slug = compute_task_slug(task)
                section_name = extract_section_name(task)
                type_iri, properties = build_task_properties(
                    task, field_config, section_name,
                    sync_time=sync_timestamp,
                )

                existing = await _find_existing_task(ctx.graph, slug)

                # Loop prevention: skip tasks not modified since last sync
                if existing and existing.get("lastSyncedAt"):
                    modified_at = task.get("modified_at", "")
                    if modified_at and modified_at <= existing["lastSyncedAt"]:
                        unchanged_count += 1
                        continue

                # Resolve assignee
                assignee_info = extract_assignee(task)
                assignee_iri = None
                if assignee_info:
                    assignee_iri = await person_matcher.match_or_create(
                        assignee_info["email"],
                        assignee_info.get("name"),
                    )

                # Resolve followers
                follower_infos = extract_followers(task)
                follower_iris: list[str] = []
                for finfo in follower_infos:
                    f_iri = await person_matcher.match_or_create(
                        finfo["email"], finfo.get("name"),
                    )
                    if f_iri:
                        follower_iris.append(f_iri)

                body_text = extract_body(task)

                # Track subtask→parent relationship
                parent_gid = task.get("_parent_gid")
                if parent_gid:
                    parent_slug = f"asana-{parent_gid}"
                    subtask_parent_map[slug] = parent_slug

                if existing:
                    update_cmds = _build_update_commands(
                        existing["iri"], properties, body_text,
                        assignee_iri, follower_iris,
                    )
                    # Add subtask→parent edge for existing tasks
                    if parent_gid:
                        parent_slug_val = f"asana-{parent_gid}"
                        parent_info = await _find_existing_task(
                            ctx.graph, parent_slug_val,
                        )
                        if parent_info:
                            update_cmds.append({
                                "command": "edge.create",
                                "params": {
                                    "source": existing["iri"],
                                    "predicate": "dcterms:isPartOf",
                                    "target": parent_info["iri"],
                                },
                            })
                    update_commands.extend(update_cmds)
                    updated_count += 1
                else:
                    create_commands.append(
                        _build_create_command(slug, type_iri, properties)
                    )
                    if body_text:
                        new_task_bodies[slug] = body_text
                    if assignee_iri:
                        new_task_assignees[slug] = assignee_iri
                    if follower_iris:
                        new_task_followers[slug] = follower_iris
                    created_count += 1

            except Exception as exc:
                error_count += 1
                error_details.append({
                    "task_gid": task_gid,
                    "project_gid": project_gid,
                    "error": str(exc),
                })
                logger.warning(
                    "Error processing task %s: %s", task_gid, exc,
                )

    # 7. Phase 1: submit object.create commands
    if create_commands:
        await _submit_commands_batched(http_client, create_commands)

    # 8. Phase 2: discover IRIs, submit body.set + edge.create
    phase2_commands: list[dict] = []

    # Collect all slugs that need phase-2 work
    phase2_slugs = set(
        list(new_task_bodies.keys())
        + list(new_task_assignees.keys())
        + list(new_task_followers.keys())
        + [s for s in subtask_parent_map if s not in update_commands]
    )

    for slug in phase2_slugs:
        task_info = await _find_existing_task(ctx.graph, slug)
        if not task_info:
            continue
        iri = task_info["iri"]

        # Body
        body = new_task_bodies.get(slug)
        if body:
            phase2_commands.append({
                "command": "body.set",
                "params": {"iri": iri, "body": body},
            })

        # Assignee
        a_iri = new_task_assignees.get(slug)
        if a_iri:
            phase2_commands.append({
                "command": "edge.create",
                "params": {
                    "source": iri,
                    "predicate": f"{BPKM}assignedTo",
                    "target": a_iri,
                },
            })

        # Followers
        f_iris = new_task_followers.get(slug)
        if f_iris:
            for f_iri in f_iris:
                phase2_commands.append({
                    "command": "edge.create",
                    "params": {
                        "source": iri,
                        "predicate": f"{BPKM}followedBy",
                        "target": f_iri,
                    },
                })

        # Subtask→parent edge
        if slug in subtask_parent_map:
            parent_slug = subtask_parent_map[slug]
            parent_info = await _find_existing_task(ctx.graph, parent_slug)
            if parent_info:
                phase2_commands.append({
                    "command": "edge.create",
                    "params": {
                        "source": iri,
                        "predicate": "dcterms:isPartOf",
                        "target": parent_info["iri"],
                    },
                })

    # 9. Submit update + phase-2 commands
    all_follow_up = update_commands + phase2_commands
    if all_follow_up:
        await _submit_commands_batched(http_client, all_follow_up)

    # 10. Update sync cursor and result
    if error_count == 0:
        overall_status = "success"
    elif created_count > 0 or updated_count > 0:
        overall_status = "partial"
    else:
        overall_status = "error"

    result = _make_result(
        overall_status,
        start_time,
        sync_timestamp,
        created=created_count,
        updated=updated_count,
        unchanged=unchanged_count,
        errors=error_count,
        error_details=error_details,
    )

    await ctx.state.set("last_pull_result", json.dumps(result))
    await ctx.state.set("last_sync_at", sync_timestamp)

    logger.info(
        "pull_sync complete: status=%s created=%d updated=%d "
        "unchanged=%d errors=%d duration_ms=%d",
        overall_status, created_count, updated_count,
        unchanged_count, error_count, result["duration_ms"],
    )

    return result


# ---------------------------------------------------------------------------
# Push sync — changed-task discovery
# ---------------------------------------------------------------------------


async def _find_changed_tasks(graph_client) -> list[dict]:
    """Find tasks synced from Asana that have local modifications.

    A task is considered changed when:
    - It has ``externalProvider = "asana"`` and ``externalUuid`` (was pulled)
    - Its ``dcterms:modified`` is greater than ``bpkm:lastSyncedAt``, or
      it has no ``lastSyncedAt`` (treat as changed)
    - Its ``syncDirection`` is not ``"pull-only"``

    Returns a list of dicts with keys:
    ``iri``, ``externalUuid``, ``status``, ``priority``, ``title``,
    ``dueDate``, ``lastSyncedAt``.
    """
    sparql = (
        "SELECT ?task ?uuid ?status ?priority ?title ?dueDate ?lastSynced ?syncDir WHERE {\n"
        f'  ?task a <{BPKM}Task> .\n'
        f'  ?task <{BPKM}externalProvider> "asana" .\n'
        f'  ?task <{BPKM}externalUuid> ?uuid .\n'
        f'  OPTIONAL {{ ?task <{BPKM}taskStatus> ?status }}\n'
        f'  OPTIONAL {{ ?task <{BPKM}priority> ?priority }}\n'
        f'  OPTIONAL {{ ?task <dcterms:title> ?title }}\n'
        f'  OPTIONAL {{ ?task <{BPKM}dueDate> ?dueDate }}\n'
        f'  OPTIONAL {{ ?task <{BPKM}lastSyncedAt> ?lastSynced }}\n'
        f'  OPTIONAL {{ ?task <{BPKM}syncDirection> ?syncDir }}\n'
        f'  OPTIONAL {{ ?task <dcterms:modified> ?modified }}\n'
        f'  FILTER(!BOUND(?syncDir) || ?syncDir != "pull-only")\n'
        f'  FILTER(!BOUND(?lastSynced) || !BOUND(?modified) || STR(?modified) > STR(?lastSynced))\n'
        "}"
    )
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])

    tasks = []
    for row in bindings:
        tasks.append({
            "iri": row["task"]["value"],
            "externalUuid": row["uuid"]["value"],
            "status": row.get("status", {}).get("value"),
            "priority": row.get("priority", {}).get("value"),
            "title": row.get("title", {}).get("value"),
            "dueDate": row.get("dueDate", {}).get("value"),
            "lastSyncedAt": row.get("lastSynced", {}).get("value"),
        })
    return tasks


# ---------------------------------------------------------------------------
# Main push sync
# ---------------------------------------------------------------------------


async def push_sync(ctx) -> dict:
    """Run the full bpkm:Task → Asana push sync pipeline.

    Steps:
      1. Check auth status
      2. Read sync direction — skip if pull-only
      3. Read field config + discovered enum fields / sections
      4. Find locally changed tasks via SPARQL
      5. For each changed task: build PATCH body + section move
      6. Update lastSyncedAt on each pushed task
      7. Store last_push_result in state

    Returns a result dict with ``status``, ``pushed``, ``skipped``,
    ``errors``, and ``error_details`` fields.
    """
    # 1. Auth check
    conn = await get_connection_status(ctx.state)
    if not conn["connected"]:
        result = {"status": "skipped", "reason": "not connected",
                  "pushed": 0, "skipped": 0, "errors": 0, "error_details": []}
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    # 2. Sync direction
    sync_direction = await ctx.state.get("sync_direction")
    if sync_direction == "pull-only":
        result = {"status": "skipped", "reason": "sync direction is pull-only",
                  "pushed": 0, "skipped": 0, "errors": 0, "error_details": []}
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    # 3. Read field config and discovered data
    field_config = await _read_field_config(ctx.state)

    discovered_enum_json = await ctx.state.get("discovered_enum_fields")
    discovered_enum_fields = json.loads(discovered_enum_json) if discovered_enum_json else []

    discovered_sections_json = await ctx.state.get("discovered_sections")
    discovered_sections = json.loads(discovered_sections_json) if discovered_sections_json else []

    # 4. Find changed tasks
    changed_tasks = await _find_changed_tasks(ctx.graph)
    if not changed_tasks:
        logger.info("push_sync: no changed tasks found")
        result = {"status": "ok", "pushed": 0, "skipped": 0, "errors": 0,
                  "error_details": []}
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    logger.info("push_sync: found %d changed tasks", len(changed_tasks))

    # 5. Build AsanaClient and push each task
    client = AsanaClient(http_client=ctx.http, state_client=ctx.state)
    http_client = ctx.commands._client  # D204 bypass for bulk commands

    pushed_count = 0
    skipped_count = 0
    error_count = 0
    error_details: list[dict] = []
    push_timestamp = datetime.now(timezone.utc).isoformat()

    for task in changed_tasks:
        task_gid = task["externalUuid"]
        task_iri = task["iri"]

        try:
            # Build bpkm properties dict from the task's current values
            bpkm_props: dict = {}
            if task.get("title"):
                bpkm_props["dcterms:title"] = task["title"]
            if task.get("status"):
                bpkm_props[f"{BPKM}taskStatus"] = task["status"]
            if task.get("priority"):
                bpkm_props[f"{BPKM}priority"] = task["priority"]
            if task.get("dueDate"):
                bpkm_props[f"{BPKM}dueDate"] = task["dueDate"]

            # --- Path 1: Custom field PATCH ---
            patch = build_asana_patch(
                bpkm_props, field_config, discovered_enum_fields,
            )

            did_push = False

            if patch:
                await client.patch_task(task_gid, patch)
                logger.info("push_sync: pushed task %s via PATCH", task_gid)
                did_push = True

            # --- Path 2: Section move (when status_source == "section") ---
            if (
                field_config.get("status_source") == "section"
                and task.get("status")
            ):
                section_gid = resolve_section_gid_for_status(
                    task["status"], field_config, discovered_sections,
                )
                if section_gid:
                    await client.add_task_to_section(section_gid, task_gid)
                    logger.info(
                        "push_sync: section move for task %s → section %s",
                        task_gid, section_gid,
                    )
                    did_push = True
                else:
                    logger.warning(
                        "push_sync: section GID not found for status '%s' "
                        "on task %s — skipping section move",
                        task["status"], task_gid,
                    )

            if not did_push:
                skipped_count += 1
                continue

            # Update lastSyncedAt on the pushed task
            update_cmds = [{
                "command": "object.patch",
                "params": {
                    "iri": task_iri,
                    "properties": {f"{BPKM}lastSyncedAt": push_timestamp},
                },
            }]
            await _submit_commands_batched(http_client, update_cmds)

            pushed_count += 1

        except Exception as exc:
            error_count += 1
            error_details.append({
                "iri": task_iri,
                "task_gid": task_gid,
                "error": str(exc),
            })
            logger.warning(
                "push_sync: error pushing task %s: %s", task_gid, exc,
            )

    # 7. Determine overall status and store result
    if error_count == 0:
        overall_status = "ok"
    elif pushed_count > 0:
        overall_status = "partial"
    else:
        overall_status = "error"

    result = {
        "status": overall_status,
        "pushed": pushed_count,
        "skipped": skipped_count,
        "errors": error_count,
        "error_details": error_details,
    }
    await ctx.state.set("last_push_result", json.dumps(result))

    logger.info(
        "push_sync complete: status=%s pushed=%d skipped=%d errors=%d",
        overall_status, pushed_count, skipped_count, error_count,
    )

    return result
