"""Pull sync engine — fetches Todoist tasks and creates/updates bpkm:Task objects.

Orchestrates TodoistClient, field mapper, person matcher, and the bulk
command API into a complete pull sync pipeline.  Commands bypass the
SDK's ``CommandClient`` (which enforces IRI prefix checks) by posting
directly to ``/api/commands/bulk`` via the shared httpx client.

Two-phase bulk for new tasks:
  Phase 1: ``object.create`` commands (no IRI needed — platform assigns it)
  Phase 2: SPARQL-discover minted IRIs, then submit ``body.set`` + ``edge.create``

For existing tasks, all commands (patch, body) go in one batch
because the IRI is already known from the SPARQL lookup.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone

try:
    from services.field_mapper import (
        BPKM,
        BPKM_TO_TODOIST_STATUS,
        build_task_properties,
        build_todoist_task_data,
        compute_task_slug,
    )
    from services.person_matcher import PersonMatcher
    from services.auth import get_connection_status
    from services.todoist_client import TodoistClient
except ImportError:
    from field_mapper import (
        BPKM,
        BPKM_TO_TODOIST_STATUS,
        build_task_properties,
        build_todoist_task_data,
        compute_task_slug,
    )
    from person_matcher import PersonMatcher
    from auth import get_connection_status
    from todoist_client import TodoistClient

logger = logging.getLogger("todoist.sync")

BATCH_SIZE = 1000  # Max commands per bulk POST


# ---------------------------------------------------------------------------
# SPARQL lookup
# ---------------------------------------------------------------------------


async def _find_existing_task(graph_client, external_id: str) -> dict | None:
    """Check whether a Task with the given externalId already exists.

    Uses ``bpkm:externalId`` + ``bpkm:externalProvider = "todoist"``
    to find tasks created by prior syncs.

    Returns ``{"iri": ..., "title": ..., "status": ...}`` or None.
    """
    sparql = (
        "SELECT ?task ?title ?status ?lastSynced WHERE {\n"
        f"  ?task a <{BPKM}Task> .\n"
        f'  ?task <{BPKM}externalProvider> "todoist" .\n'
        f'  ?task <{BPKM}externalId> "{external_id}" .\n'
        f"  OPTIONAL {{ ?task <dcterms:title> ?title }}\n"
        f"  OPTIONAL {{ ?task <{BPKM}taskStatus> ?status }}\n"
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
        "title": row.get("title", {}).get("value"),
        "status": row.get("status", {}).get("value"),
        "lastSyncedAt": row.get("lastSynced", {}).get("value"),
    }


async def _find_changed_tasks(graph_client) -> list[dict]:
    """Find Todoist tasks that have been locally modified since last sync.

    A task is considered changed when:
    - It has ``externalProvider = "todoist"`` and ``externalId`` set (was pulled)
    - Its ``dcterms:modified`` > ``bpkm:lastSyncedAt``, or it has no
      ``lastSyncedAt`` (treat as changed)
    - Its ``syncDirection`` is not ``"pull-only"``

    Returns a list of dicts with keys:
    ``iri``, ``externalId``, ``status``, ``title``, ``tags``, ``lastSyncedAt``.
    """
    sparql = (
        "SELECT ?task ?extId ?status ?title ?tags ?lastSynced ?syncDir ?modified WHERE {\n"
        f'  ?task a <{BPKM}Task> .\n'
        f'  ?task <{BPKM}externalProvider> "todoist" .\n'
        f'  ?task <{BPKM}externalId> ?extId .\n'
        f'  OPTIONAL {{ ?task <{BPKM}taskStatus> ?status }}\n'
        f'  OPTIONAL {{ ?task <dcterms:title> ?title }}\n'
        f'  OPTIONAL {{ ?task <{BPKM}tags> ?tags }}\n'
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
            "externalId": row["extId"]["value"],
            "status": row.get("status", {}).get("value"),
            "title": row.get("title", {}).get("value"),
            "tags": row.get("tags", {}).get("value"),
            "lastSyncedAt": row.get("lastSynced", {}).get("value"),
        })
    return tasks


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------


def _build_create_command(slug: str, properties: dict) -> dict:
    """Build an ``object.create`` command for a new task."""
    return {
        "command": "object.create",
        "params": {
            "type": f"{BPKM}Task",
            "slug": slug,
            "properties": properties,
        },
    }


def _build_update_commands(
    existing_iri: str,
    properties: dict,
    body_text: str | None,
) -> list[dict]:
    """Build patch / body.set commands for an existing task."""
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

    return cmds


# ---------------------------------------------------------------------------
# Bulk submission
# ---------------------------------------------------------------------------


async def _submit_commands_batched(
    http_client,
    commands: list[dict],
    *,
    request_id: str | None = None,
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
            "summary": f"Todoist sync: batch of {len(batch)} commands",
            "source": "todoist-sync",
        }
        headers = {}
        if request_id:
            headers["X-Request-Id"] = request_id

        resp = await http_client.post(
            "/api/commands/bulk", json=payload, headers=headers
        )
        resp.raise_for_status()
        results.append(resp.json())
    return results


# ---------------------------------------------------------------------------
# Main pull sync
# ---------------------------------------------------------------------------


async def pull_sync(ctx) -> dict:
    """Run the full Todoist → bpkm:Task pull sync pipeline.

    Steps:
      1. Check auth status
      2. Read selected project IDs from state
      3. Fetch tasks from each selected project via Todoist REST API
      4. Fetch labels for lookup (label name resolution)
      5. For each task: classify as create / update
      6. Phase 1: submit object.create commands
      7. Phase 2: discover IRIs of new tasks, submit body.set + edge.create
      8. Submit update commands
      9. Store sync result in state

    Returns a result dict with ``status``, ``created``, ``updated``,
    ``unchanged``, ``errors``, ``error_details``, ``duration_ms``,
    and ``timestamp`` fields.
    """
    start_time = time.monotonic()
    sync_timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Auth check
    client = TodoistClient(http_client=ctx.http, state_client=ctx.state)
    status = await get_connection_status(ctx.state, ctx.http)
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

    selected_project_ids = json.loads(selected_json)
    if not selected_project_ids:
        result = _make_result(
            "skipped", start_time, sync_timestamp,
            reason="no projects selected",
        )
        await ctx.state.set("last_pull_result", json.dumps(result))
        return result

    # 3. Fetch labels for lookup (used by field_mapper)
    labels_lookup: dict[str, str] = {}
    try:
        labels = await client.get_labels()
        labels_lookup = {lb["id"]: lb["name"] for lb in labels}
    except Exception as exc:
        logger.warning("Failed to fetch labels: %s", exc)

    # 4. Build project name lookup
    project_lookup: dict[str, str] = {}
    try:
        projects = await client.get_projects()
        project_lookup = {p["id"]: p["name"] for p in projects}
    except Exception as exc:
        logger.warning("Failed to fetch projects for name lookup: %s", exc)

    # 5. Set up person matcher and bulk client
    person_matcher = PersonMatcher(ctx.graph, ctx.commands)
    http_client = ctx.commands._client  # bypass SDK for bulk commands

    create_commands: list[dict] = []
    update_commands: list[dict] = []
    created_count = 0
    updated_count = 0
    unchanged_count = 0
    error_count = 0
    error_details: list[dict] = []
    new_task_bodies: dict[str, str] = {}  # slug → description
    new_task_assignees: dict[str, str] = {}  # slug → person IRI

    # 6. Fetch and process tasks from each selected project
    for project_id in selected_project_ids:
        try:
            tasks = await client.get_tasks(project_id=project_id)
        except Exception as exc:
            logger.warning(
                "Failed to fetch tasks from project %s: %s",
                project_id, exc,
            )
            error_count += 1
            error_details.append({
                "task_id": None,
                "project_id": project_id,
                "error": f"fetch failed: {exc}",
            })
            continue

        for task in tasks:
            task_id = str(task.get("id", ""))
            task_ref = f"todoist:{task_id}"
            try:
                external_id = task_id
                existing = await _find_existing_task(ctx.graph, external_id)

                # Loop prevention: skip tasks whose remote updated_at
                # is not newer than our lastSyncedAt (we just pushed)
                if existing and existing.get("lastSyncedAt"):
                    remote_updated = task.get("updated_at")
                    if remote_updated and remote_updated <= existing["lastSyncedAt"]:
                        unchanged_count += 1
                        continue

                # Build properties
                properties = build_task_properties(
                    task,
                    labels_lookup=labels_lookup,
                    project_lookup=project_lookup,
                    sync_time=sync_timestamp,
                )

                # Resolve assignee if present
                assignee_id = task.get("assignee_id")
                person_iri = None
                if assignee_id:
                    # Build minimal assignee info from task data
                    assignee_info = {
                        "name": str(assignee_id),
                        "email": None,
                    }
                    person_iri = await person_matcher.match(assignee_info)

                body_text = task.get("description") or None
                slug = compute_task_slug(task_id)

                if existing:
                    # Check if anything actually changed
                    update_cmds = _build_update_commands(
                        existing["iri"], properties, body_text
                    )
                    if person_iri:
                        update_cmds.append({
                            "command": "edge.create",
                            "params": {
                                "source": existing["iri"],
                                "target": person_iri,
                                "predicate": f"{BPKM}assignedTo",
                            },
                        })
                    update_commands.extend(update_cmds)
                    updated_count += 1
                else:
                    # New task
                    create_commands.append(
                        _build_create_command(slug, properties)
                    )
                    if body_text:
                        new_task_bodies[slug] = body_text
                    if person_iri:
                        new_task_assignees[slug] = person_iri
                    created_count += 1

            except Exception as exc:
                error_count += 1
                error_details.append({
                    "task_id": task_id,
                    "error": str(exc),
                })
                logger.warning(
                    "Error processing task %s: %s", task_ref, exc,
                )

    # 7. Phase 1: submit create commands with idempotency header
    if create_commands:
        request_id = str(uuid.uuid4())
        await _submit_commands_batched(
            http_client, create_commands, request_id=request_id
        )

    # 8. Phase 2: discover IRIs of new tasks, submit body.set + edge.create
    phase2_commands: list[dict] = []
    for slug in list(new_task_bodies.keys()) + [
        s for s in new_task_assignees if s not in new_task_bodies
    ]:
        # Deduplicate: only look up each slug once
        pass

    # Collect unique slugs that need phase 2 work
    phase2_slugs = set(list(new_task_bodies.keys()) + list(new_task_assignees.keys()))
    for slug in phase2_slugs:
        # Reconstruct the external_id from slug to find the task
        # We need to search by the slug pattern in the IRI
        task_info = await _find_task_by_slug(ctx.graph, slug)
        if task_info:
            iri = task_info["iri"]
            body = new_task_bodies.get(slug)
            if body:
                phase2_commands.append({
                    "command": "body.set",
                    "params": {"iri": iri, "body": body},
                })
            person_iri = new_task_assignees.get(slug)
            if person_iri:
                phase2_commands.append({
                    "command": "edge.create",
                    "params": {
                        "source": iri,
                        "target": person_iri,
                        "predicate": f"{BPKM}assignedTo",
                    },
                })

    # 9. Submit update + phase 2 commands
    all_follow_up = update_commands + phase2_commands
    if all_follow_up:
        await _submit_commands_batched(http_client, all_follow_up)

    # Determine overall status
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
    logger.info(
        "Pull sync complete: status=%s created=%d updated=%d unchanged=%d errors=%d",
        overall_status, created_count, updated_count, unchanged_count, error_count,
    )
    return result


async def _find_task_by_slug(graph_client, slug: str) -> dict | None:
    """Find a task by slug suffix in its IRI.

    Uses STRENDS to match ``/Task/{slug}`` at the end of the IRI.
    """
    sparql = (
        "SELECT ?task WHERE {\n"
        f"  ?task a <{BPKM}Task> .\n"
        f'  FILTER(STRENDS(STR(?task), "/Task/{slug}"))\n'
        "} LIMIT 1"
    )
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    return {"iri": bindings[0]["task"]["value"]}


# ---------------------------------------------------------------------------
# Main push sync
# ---------------------------------------------------------------------------


async def push_sync(ctx) -> dict:
    """Run the full bpkm:Task → Todoist push sync pipeline.

    Steps:
      1. Check auth status
      2. Read sync_direction from settings — skip if "pull-only"
      3. Find locally changed tasks via SPARQL
      4. For each changed task:
         a. Detect status change → close/reopen via dedicated endpoints
         b. Build reverse-mapped field update → update_task for non-status fields
         c. Update lastSyncedAt on the task
      5. Store last_push_result in state

    Status changes are processed before field updates because Todoist's
    close/reopen endpoints may reset certain fields (e.g., completed_at).

    Returns a result dict with ``status``, ``pushed``, ``skipped``,
    ``closed``, ``reopened``, ``updated``, ``errors``, and ``timestamp``.
    """
    push_timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Auth check
    client = TodoistClient(http_client=ctx.http, state_client=ctx.state)
    status = await get_connection_status(ctx.state, ctx.http)
    if not status["connected"]:
        result = {
            "status": "skipped",
            "pushed": 0,
            "skipped": 0,
            "closed": 0,
            "reopened": 0,
            "updated": 0,
            "errors": [],
            "timestamp": push_timestamp,
            "reason": "not connected",
        }
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    # 2. Read sync direction from settings
    sync_direction = await ctx.settings.get("sync_direction")
    if sync_direction == "pull-only":
        result = {
            "status": "skipped",
            "pushed": 0,
            "skipped": 0,
            "closed": 0,
            "reopened": 0,
            "updated": 0,
            "errors": [],
            "timestamp": push_timestamp,
            "reason": "sync direction is pull-only",
        }
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    # 3. Find changed tasks
    changed_tasks = await _find_changed_tasks(ctx.graph)
    if not changed_tasks:
        logger.info("push_sync: no changed tasks found")
        result = {
            "status": "ok",
            "pushed": 0,
            "skipped": 0,
            "closed": 0,
            "reopened": 0,
            "updated": 0,
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
    closed_count = 0
    reopened_count = 0
    updated_count = 0
    errors: list[dict] = []

    for task in changed_tasks:
        try:
            external_id = task["externalId"]
            did_something = False

            # 4a. Detect and apply status change (close/reopen first)
            task_status = task.get("status")
            if task_status:
                is_completed = BPKM_TO_TODOIST_STATUS.get(task_status)
                if is_completed is True:
                    await client.close_task(external_id)
                    closed_count += 1
                    did_something = True
                elif is_completed is False:
                    await client.reopen_task(external_id)
                    reopened_count += 1
                    did_something = True

            # 4b. Build reverse-mapped update body for non-status fields
            task_props: dict = {}
            if task.get("title"):
                task_props["dcterms:title"] = task["title"]
            if task.get("tags"):
                task_props[f"{BPKM}tags"] = (
                    task["tags"] if isinstance(task["tags"], list)
                    else [task["tags"]]
                )

            update_data = build_todoist_task_data(task_props)
            if update_data:
                await client.update_task(external_id, update_data)
                updated_count += 1
                did_something = True

            if not did_something:
                skipped_count += 1
                continue

            # 4c. Update lastSyncedAt on the pushed task
            sync_cmds = [{
                "command": "object.patch",
                "params": {
                    "iri": task["iri"],
                    "properties": {f"{BPKM}lastSyncedAt": push_timestamp},
                },
            }]
            await _submit_commands_batched(http_client, sync_cmds)

            pushed_count += 1

        except Exception as e:
            errors.append({"iri": task["iri"], "error": str(e)})
            logger.warning(
                "push_sync: error pushing task %s: %s", task["iri"], e,
            )

    # Determine overall status
    if not errors:
        overall_status = "ok"
    elif pushed_count > 0:
        overall_status = "partial"
    else:
        overall_status = "error"

    result = {
        "status": overall_status,
        "pushed": pushed_count,
        "skipped": skipped_count,
        "closed": closed_count,
        "reopened": reopened_count,
        "updated": updated_count,
        "errors": errors,
        "timestamp": push_timestamp,
    }

    await ctx.state.set("last_push_result", json.dumps(result))
    logger.info(
        "Push sync complete: status=%s pushed=%d skipped=%d closed=%d "
        "reopened=%d updated=%d errors=%d",
        overall_status, pushed_count, skipped_count, closed_count,
        reopened_count, updated_count, len(errors),
    )
    return result


def _make_result(
    status: str,
    start_time: float,
    timestamp: str,
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
        "timestamp": timestamp,
    }
    if reason:
        result["reason"] = reason
    return result
