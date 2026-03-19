"""Pull sync engine — fetches Linear issues and creates/updates bpkm:Task objects.

Orchestrates LinearClient, field mapper, person matcher, and the bulk
command API into a complete pull sync pipeline.  Commands bypass the
SDK's ``CommandClient`` (which enforces IRI prefix checks) by posting
directly to ``/api/commands/bulk`` via the shared httpx client.

Two-phase bulk for new issues:
  Phase 1: ``object.create`` commands (no IRI needed — platform assigns it)
  Phase 2: SPARQL-discover minted IRIs, then submit ``body.set`` / ``edge.create``

For existing issues, all commands (patch, body, edge) go in one batch
because the IRI is already known from the SPARQL lookup.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

try:
    from services.field_mapper import (
        build_issue_query,
        build_task_properties,
        compute_issue_slug,
        BPKM,
    )
    from services.person_matcher import PersonMatcher
    from services.auth import get_connection_status
    from services.linear_client import LinearClient
except ImportError:
    from field_mapper import (
        build_issue_query,
        build_task_properties,
        compute_issue_slug,
        BPKM,
    )
    from person_matcher import PersonMatcher
    from auth import get_connection_status
    from linear_client import LinearClient

logger = logging.getLogger("linear_sync.sync")

BATCH_SIZE = 1000  # Max commands per bulk POST


# ---------------------------------------------------------------------------
# SPARQL lookup
# ---------------------------------------------------------------------------


async def _find_existing_task(graph_client, slug: str) -> dict | None:
    """Check whether a Task with the given slug already exists.

    Uses ``STRENDS`` to match the slug suffix of the IRI without
    needing to know the platform's base namespace.

    Returns ``{"iri": ..., "status": ..., "externalId": ...}`` or None.
    """
    sparql = (
        "SELECT ?task ?status ?extId WHERE {\n"
        f"  ?task a <{BPKM}Task> .\n"
        f"  ?task <{BPKM}externalProvider> \"linear\" .\n"
        f'  FILTER(STRENDS(STR(?task), "/Task/{slug}"))\n'
        f"  OPTIONAL {{ ?task <{BPKM}taskStatus> ?status }}\n"
        f"  OPTIONAL {{ ?task <{BPKM}externalId> ?extId }}\n"
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
    }


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
    description: str | None,
    assignee_iri: str | None,
) -> list[dict]:
    """Build patch / body.set / edge.create commands for an existing task."""
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
# Main pull sync
# ---------------------------------------------------------------------------


async def pull_sync(ctx) -> dict:
    """Run the full Linear → bpkm:Task pull sync pipeline.

    Steps:
      1. Check auth status
      2. Read sync cursor and team list from state
      3. Fetch issues from Linear via paginated GraphQL
      4. For each issue: classify as create / update / trashed
      5. Phase 1: submit object.create commands
      6. Phase 2: discover IRIs of new tasks, submit body.set / edge.create
      7. Submit update commands
      8. Store new sync cursor

    Returns a result dict with ``status``, ``created``, ``updated``,
    ``unchanged``, and ``errors`` fields.
    """
    # 1. Auth check
    status = await get_connection_status(ctx.state)
    if not status["connected"]:
        return {"status": "skipped", "reason": "not connected"}

    workspace_id = status.get("workspace_id") or ""

    # 2. Read sync state
    last_sync_at = await ctx.state.get("last_sync_at")
    sync_teams_json = await ctx.state.get("sync_teams")
    if not sync_teams_json:
        return {"status": "skipped", "reason": "no teams selected"}
    sync_teams = json.loads(sync_teams_json)

    # 3. Build query and fetch issues
    client = LinearClient(http_client=ctx.http, state_client=ctx.state)
    query, variables = build_issue_query(sync_teams, last_sync_at or None)
    issues = await client.query_paginated(
        query, variables, "issues.nodes", "issues.pageInfo"
    )

    logger.info("pull_sync: fetched %d issues from Linear", len(issues))

    # 4. Process issues
    person_matcher = PersonMatcher(ctx.graph, ctx.commands)
    http_client = ctx.commands._client  # bypass SDK for bulk commands

    create_commands: list[dict] = []
    update_commands: list[dict] = []
    created_count = 0
    updated_count = 0
    unchanged_count = 0
    errors: list[dict] = []
    new_issue_descriptions: dict[str, str] = {}  # slug → description
    new_issue_assignees: dict[str, dict] = {}  # slug → {email, name}

    sync_timestamp = datetime.now(timezone.utc).isoformat()

    for issue in issues:
        try:
            slug = compute_issue_slug(workspace_id, issue["id"])
            existing = await _find_existing_task(ctx.graph, slug)
            properties = build_task_properties(
                issue, workspace_id, sync_time=sync_timestamp
            )

            # Trashed handling
            if issue.get("trashed"):
                if existing:
                    update_commands.append({
                        "command": "object.patch",
                        "params": {
                            "iri": existing["iri"],
                            "properties": {f"{BPKM}taskStatus": "cancelled"},
                        },
                    })
                    updated_count += 1
                continue

            # Resolve assignee (may create Person)
            assignee = issue.get("assignee")
            assignee_iri = None
            if assignee and assignee.get("email"):
                assignee_iri = await person_matcher.match_or_create(
                    assignee["email"], assignee.get("displayName")
                )

            description = issue.get("description") or None

            if existing:
                # Update existing task
                update_commands.extend(
                    _build_update_commands(
                        existing["iri"], properties, description, assignee_iri
                    )
                )
                updated_count += 1
            else:
                # New task
                create_commands.append(_build_create_command(slug, properties))
                if description:
                    new_issue_descriptions[slug] = description
                if assignee_iri:
                    new_issue_assignees[slug] = assignee_iri
                created_count += 1

        except Exception as e:
            errors.append({
                "issue_id": issue.get("id", "unknown"),
                "error": str(e),
            })
            logger.warning("Error processing issue %s: %s", issue.get("id"), e)

    # 5. Phase 1: submit create commands
    if create_commands:
        await _submit_commands_batched(
            http_client,
            create_commands,
            f"Linear sync: created {len(create_commands)} tasks",
            "linear-sync",
        )

    # 6. Phase 2: discover IRIs of new tasks, submit body.set / edge.create
    phase2_commands: list[dict] = []
    for slug, desc in new_issue_descriptions.items():
        task_info = await _find_existing_task(ctx.graph, slug)
        if task_info:
            phase2_commands.append({
                "command": "body.set",
                "params": {"iri": task_info["iri"], "body": desc},
            })

    for slug, p_iri in new_issue_assignees.items():
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

    # 7. Submit update + phase 2 commands
    all_follow_up = update_commands + phase2_commands
    if all_follow_up:
        await _submit_commands_batched(
            http_client,
            all_follow_up,
            f"Linear sync: updated {updated_count} tasks, {len(phase2_commands)} follow-ups",
            "linear-sync",
        )

    # 8. Update sync cursor
    await ctx.state.set("last_sync_at", sync_timestamp)

    result = {
        "status": "ok",
        "created": created_count,
        "updated": updated_count,
        "unchanged": unchanged_count,
        "errors": errors,
    }
    logger.info("Pull sync complete: %s", result)
    return result
