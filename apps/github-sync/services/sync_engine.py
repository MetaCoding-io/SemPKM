"""Pull sync engine — fetches GitHub issues and creates/updates bpkm:Task objects.

Orchestrates GitHubClient, field mapper, person matcher, and the bulk
command API into a complete pull sync pipeline.  Commands bypass the
SDK's ``CommandClient`` (which enforces IRI prefix checks) by posting
directly to ``/api/commands/bulk`` via the shared httpx client.

Two-phase bulk for new issues:
  Phase 1: ``object.create`` commands (no IRI needed — platform assigns it)
  Phase 2: SPARQL-discover minted IRIs, then submit ``body.set``

For existing issues, all commands (patch, body) go in one batch
because the IRI is already known from the SPARQL lookup.
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
        compute_issue_slug,
        get_assignee_info,
        is_pull_request,
    )
    from services.person_matcher import PersonMatcher
    from services.auth import get_connection_status
    from services.github_client import GitHubClient
except ImportError:
    from field_mapper import (
        BPKM,
        build_task_properties,
        compute_issue_slug,
        get_assignee_info,
        is_pull_request,
    )
    from person_matcher import PersonMatcher
    from auth import get_connection_status
    from github_client import GitHubClient

logger = logging.getLogger("github_sync.sync")

BATCH_SIZE = 1000  # Max commands per bulk POST


# ---------------------------------------------------------------------------
# SPARQL lookup
# ---------------------------------------------------------------------------


async def _find_existing_task(graph_client, slug: str) -> dict | None:
    """Check whether a Task with the given slug already exists.

    Uses ``STRENDS`` to match the slug suffix of the IRI without
    needing to know the platform's base namespace.

    Returns ``{"iri": ..., "title": ..., "status": ...}`` or None.
    """
    sparql = (
        "SELECT ?task ?title ?status WHERE {\n"
        f"  ?task a <{BPKM}Task> .\n"
        f"  ?task <{BPKM}externalProvider> \"github\" .\n"
        f'  FILTER(STRENDS(STR(?task), "/Task/{slug}"))\n'
        f"  OPTIONAL {{ ?task <dcterms:title> ?title }}\n"
        f"  OPTIONAL {{ ?task <{BPKM}taskStatus> ?status }}\n"
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
            "summary": f"GitHub sync: batch of {len(batch)} commands",
            "source": "github-sync",
        }
        resp = await http_client.post("/api/commands/bulk", json=payload)
        resp.raise_for_status()
        results.append(resp.json())
    return results


# ---------------------------------------------------------------------------
# Main pull sync
# ---------------------------------------------------------------------------


async def pull_sync(ctx) -> dict:
    """Run the full GitHub → bpkm:Task pull sync pipeline.

    Steps:
      1. Check auth status
      2. Read selected repos and sync cursor from state/settings
      3. Fetch issues from GitHub via paginated REST API
      4. Filter out pull requests
      5. For each issue: classify as create / update
      6. Phase 1: submit object.create commands
      7. Phase 2: discover IRIs of new tasks, submit body.set
      8. Submit update commands
      9. Store sync cursor and result in state

    Returns a result dict with ``status``, ``created``, ``updated``,
    ``skipped``, ``errors``, ``failed_issues``, ``duration_ms``,
    and ``timestamp`` fields.
    """
    start_time = time.monotonic()
    sync_timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Auth check
    github_client = GitHubClient(
        http_client=ctx.http, state_client=ctx.state
    )
    status = await get_connection_status(ctx.state, github_client)
    if not status["connected"]:
        result = _make_result(
            "skipped", start_time, sync_timestamp,
            reason="not connected",
        )
        await ctx.state.set("last_pull_result", json.dumps(result))
        return result

    # 2. Read sync state
    selected_repos_json = await ctx.settings.get("selected_repos")
    if not selected_repos_json:
        result = _make_result(
            "skipped", start_time, sync_timestamp,
            reason="no repos selected",
        )
        await ctx.state.set("last_pull_result", json.dumps(result))
        return result
    selected_repos = json.loads(selected_repos_json)

    last_sync_at = await ctx.state.get("last_sync_at")

    # 3. Fetch issues from each repo
    person_matcher = PersonMatcher(ctx.graph, ctx.commands)
    http_client = ctx.commands._client  # bypass SDK for bulk commands

    create_commands: list[dict] = []
    update_commands: list[dict] = []
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    failed_issues: list[str] = []
    new_issue_bodies: dict[str, str] = {}  # slug → body markdown

    for repo_full_name in selected_repos:
        parts = repo_full_name.split("/", 1)
        if len(parts) != 2:
            logger.warning("Invalid repo format, skipping: %s", repo_full_name)
            skipped_count += 1
            continue
        owner, repo = parts

        try:
            issues = await github_client.fetch_issues(
                owner, repo, since=last_sync_at
            )
        except Exception as exc:
            logger.warning(
                "Failed to fetch issues from %s: %s", repo_full_name, exc
            )
            error_count += 1
            failed_issues.append(f"{repo_full_name}(fetch)")
            continue

        # 4. Filter out pull requests
        real_issues = [i for i in issues if not is_pull_request(i)]
        skipped_count += len(issues) - len(real_issues)

        # 5. Process each issue
        for issue in real_issues:
            issue_ref = f"{repo_full_name}#{issue.get('number', '?')}"
            try:
                slug = compute_issue_slug(repo_full_name, issue["number"])
                existing = await _find_existing_task(ctx.graph, slug)

                # Resolve assignee
                assignee_info = get_assignee_info(issue)
                person_iri = await person_matcher.match(assignee_info)

                properties = build_task_properties(
                    issue, repo_full_name, person_iri=person_iri
                )

                body_text = issue.get("body") or None

                if existing:
                    # Update existing task
                    update_commands.extend(
                        _build_update_commands(
                            existing["iri"], properties, body_text
                        )
                    )
                    updated_count += 1
                else:
                    # New task
                    create_commands.append(
                        _build_create_command(slug, properties)
                    )
                    if body_text:
                        new_issue_bodies[slug] = body_text
                    created_count += 1

            except Exception as exc:
                error_count += 1
                failed_issues.append(issue_ref)
                logger.warning(
                    "Error processing issue %s: %s", issue_ref, exc
                )

    # 6. Phase 1: submit create commands
    if create_commands:
        await _submit_commands_batched(http_client, create_commands)

    # 7. Phase 2: discover IRIs of new tasks, submit body.set
    phase2_commands: list[dict] = []
    for slug, body in new_issue_bodies.items():
        task_info = await _find_existing_task(ctx.graph, slug)
        if task_info:
            phase2_commands.append({
                "command": "body.set",
                "params": {"iri": task_info["iri"], "body": body},
            })

    # 8. Submit update + phase 2 commands
    all_follow_up = update_commands + phase2_commands
    if all_follow_up:
        await _submit_commands_batched(http_client, all_follow_up)

    # 9. Update sync cursor
    await ctx.state.set("last_sync_at", sync_timestamp)

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
        skipped=skipped_count,
        errors=error_count,
        failed_issues=failed_issues,
    )

    await ctx.state.set("last_pull_result", json.dumps(result))
    logger.info(
        "Pull sync complete: status=%s created=%d updated=%d skipped=%d errors=%d",
        overall_status, created_count, updated_count, skipped_count, error_count,
    )
    return result


def _make_result(
    status: str,
    start_time: float,
    timestamp: str,
    *,
    created: int = 0,
    updated: int = 0,
    skipped: int = 0,
    errors: int = 0,
    failed_issues: list[str] | None = None,
    reason: str | None = None,
) -> dict:
    """Build a structured pull result dict."""
    duration_ms = int((time.monotonic() - start_time) * 1000)
    result: dict = {
        "status": status,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "failed_issues": failed_issues or [],
        "duration_ms": duration_ms,
        "timestamp": timestamp,
    }
    if reason:
        result["reason"] = reason
    return result
