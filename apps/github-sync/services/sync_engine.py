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
        build_issue_patch,
        build_task_properties,
        compute_issue_slug,
        extract_linked_issue_numbers,
        get_assignee_info,
        is_pull_request,
        parse_external_url,
    )
    from services.person_matcher import PersonMatcher
    from services.auth import get_connection_status
    from services.github_client import GitHubClient
except ImportError:
    from field_mapper import (
        BPKM,
        build_issue_patch,
        build_task_properties,
        compute_issue_slug,
        extract_linked_issue_numbers,
        get_assignee_info,
        is_pull_request,
        parse_external_url,
    )
    from person_matcher import PersonMatcher
    from auth import get_connection_status
    from github_client import GitHubClient

logger = logging.getLogger("github_sync.sync")

BATCH_SIZE = 1000  # Max commands per bulk POST


# ---------------------------------------------------------------------------
# SPARQL lookup
# ---------------------------------------------------------------------------


async def _find_existing_task(
    graph_client, slug: str, *, provider: str | None = "github"
) -> dict | None:
    """Check whether a Task with the given slug already exists.

    Uses ``STRENDS`` to match the slug suffix of the IRI without
    needing to know the platform's base namespace.

    When *provider* is a string, the SPARQL filters by that
    ``bpkm:externalProvider`` value.  When *provider* is ``None``,
    the lookup matches by slug only — useful for finding tasks
    regardless of whether they originated as issues or PRs.

    Returns ``{"iri": ..., "title": ..., "status": ...}`` or None.
    """
    provider_clause = ""
    if provider is not None:
        provider_clause = (
            f'  ?task <{BPKM}externalProvider> "{provider}" .\n'
        )
    sparql = (
        "SELECT ?task ?title ?status ?lastSynced WHERE {\n"
        f"  ?task a <{BPKM}Task> .\n"
        f"{provider_clause}"
        f'  FILTER(STRENDS(STR(?task), "/Task/{slug}"))\n'
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
# Push sync — find locally modified tasks
# ---------------------------------------------------------------------------


async def _find_changed_tasks(graph_client) -> list[dict]:
    """Find tasks synced from GitHub that have local modifications.

    A task is considered changed when:
    - It has ``externalProvider = "github"`` and ``externalUuid`` (was pulled)
    - Its ``dcterms:modified`` > ``bpkm:lastSyncedAt``, or it has no
      ``lastSyncedAt`` (treat as changed)
    - Its ``syncDirection`` is not ``"pull-only"``

    Returns a list of dicts with keys:
    ``iri``, ``externalUuid``, ``externalUrl``, ``externalId``,
    ``status``, ``title``, ``tags``, ``lastSyncedAt``.
    """
    sparql = (
        "SELECT ?task ?uuid ?url ?extId ?status ?title ?tags ?lastSynced ?syncDir ?modified WHERE {\n"
        f'  ?task a <{BPKM}Task> .\n'
        f'  ?task <{BPKM}externalProvider> "github" .\n'
        f'  ?task <{BPKM}externalUuid> ?uuid .\n'
        f'  OPTIONAL {{ ?task <{BPKM}externalUrl> ?url }}\n'
        f'  OPTIONAL {{ ?task <{BPKM}externalId> ?extId }}\n'
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
            "externalUuid": row["uuid"]["value"],
            "externalUrl": row.get("url", {}).get("value"),
            "externalId": row.get("extId", {}).get("value"),
            "status": row.get("status", {}).get("value"),
            "title": row.get("title", {}).get("value"),
            "tags": row.get("tags", {}).get("value"),
            "lastSyncedAt": row.get("lastSynced", {}).get("value"),
        })
    return tasks


# ---------------------------------------------------------------------------
# Main push sync
# ---------------------------------------------------------------------------


async def push_sync(ctx) -> dict:
    """Run the full bpkm:Task → GitHub push sync pipeline.

    Steps:
      1. Check auth status
      2. Read sync_direction from settings — skip if "pull-only"
      3. Find locally changed tasks via SPARQL
      4. For each changed task: reverse map → PATCH issue
      5. Update lastSyncedAt on each pushed task
      6. Store last_push_result in state

    Returns a result dict with ``status``, ``pushed``, ``skipped``,
    ``errors``, and ``timestamp`` fields.
    """
    push_timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Auth check
    github_client = GitHubClient(
        http_client=ctx.http, state_client=ctx.state
    )
    status = await get_connection_status(ctx.state, github_client)
    if not status["connected"]:
        result = {
            "status": "skipped",
            "pushed": 0,
            "skipped": 0,
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
            # Build task_props from SPARQL result fields
            task_props: dict = {}
            if task.get("title"):
                task_props["dcterms:title"] = task["title"]
            if task.get("status"):
                task_props[f"{BPKM}taskStatus"] = task["status"]
            if task.get("tags"):
                # tags come as a single string from SPARQL; wrap in list
                task_props[f"{BPKM}tags"] = (
                    task["tags"] if isinstance(task["tags"], list)
                    else [task["tags"]]
                )

            # Reverse map to GitHub PATCH body
            patch_data = build_issue_patch(task_props)
            if not patch_data:
                skipped_count += 1
                continue

            # Parse external URL to get owner/repo/number
            parsed = parse_external_url(task.get("externalUrl"))
            if not parsed:
                errors.append({
                    "iri": task["iri"],
                    "error": f"Could not parse external URL: {task.get('externalUrl')}",
                })
                logger.warning(
                    "push_sync: could not parse URL for task %s: %s",
                    task["iri"], task.get("externalUrl"),
                )
                continue

            owner, repo, number = parsed

            # PATCH the issue on GitHub
            await github_client.patch_issue(owner, repo, number, patch_data)

            # Update lastSyncedAt on the pushed task
            update_cmds = [{
                "command": "object.patch",
                "params": {
                    "iri": task["iri"],
                    "properties": {f"{BPKM}lastSyncedAt": push_timestamp},
                },
            }]
            await _submit_commands_batched(http_client, update_cmds)

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
        "errors": errors,
        "timestamp": push_timestamp,
    }

    await ctx.state.set("last_push_result", json.dumps(result))
    logger.info(
        "Push sync complete: status=%s pushed=%d skipped=%d errors=%d",
        overall_status, pushed_count, skipped_count, len(errors),
    )
    return result


# ---------------------------------------------------------------------------
# Main pull sync
# ---------------------------------------------------------------------------


async def pull_sync(ctx) -> dict:
    """Run the full GitHub → bpkm:Task pull sync pipeline.

    Steps:
      1. Check auth status
      2. Read selected repos and sync cursor from state/settings
      3. Fetch issues from GitHub via paginated REST API
      4. For each issue/PR: classify as create / update
      5. Phase 1: submit object.create commands
      6. Phase 2: discover IRIs of new tasks, submit body.set
      7. Submit update commands
      8. Phase 3: fetch timelines for issues, create bpkm:dependsOn edges
      9. Store sync cursor and result in state

    Returns a result dict with ``status``, ``created``, ``updated``,
    ``skipped``, ``errors``, ``edges_created``, ``failed_issues``,
    ``duration_ms``, and ``timestamp`` fields.
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
    synced_issues: list[tuple[str, int]] = []  # (repo_full_name, issue_number)

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

        # 5. Process each issue (issues and PRs alike)
        for issue in issues:
            issue_ref = f"{repo_full_name}#{issue.get('number', '?')}"
            try:
                slug = compute_issue_slug(repo_full_name, issue["number"])
                existing = await _find_existing_task(ctx.graph, slug)

                # Loop prevention: skip if we just pushed this task
                # and the remote hasn't been updated since
                if existing and existing.get("lastSyncedAt"):
                    issue_updated = issue.get("updated_at", "")
                    if issue_updated and issue_updated <= existing["lastSyncedAt"]:
                        skipped_count += 1
                        continue

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

                # Track non-PR items for timeline queries in phase 3
                if not is_pull_request(issue):
                    synced_issues.append((repo_full_name, issue["number"]))

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

    # 9. Phase 3: link-discovery — fetch timelines for issues, create edges
    edge_commands: list[dict] = []
    edges_created = 0
    for repo_full_name, issue_number in synced_issues:
        r_owner, r_repo = repo_full_name.split("/", 1)
        try:
            timeline = await github_client.fetch_timeline(
                r_owner, r_repo, issue_number
            )
            linked_prs = extract_linked_issue_numbers(
                timeline, repo_full_name
            )
            for pr_repo, pr_number in linked_prs:
                pr_slug = compute_issue_slug(pr_repo, pr_number)
                pr_task = await _find_existing_task(
                    ctx.graph, pr_slug, provider=None
                )
                if not pr_task:
                    logger.debug(
                        "PR task not found for %s#%d, skipping edge",
                        pr_repo, pr_number,
                    )
                    continue
                issue_slug = compute_issue_slug(
                    repo_full_name, issue_number
                )
                issue_task = await _find_existing_task(
                    ctx.graph, issue_slug, provider=None
                )
                if not issue_task:
                    logger.debug(
                        "Issue task not found for %s#%d, skipping edge",
                        repo_full_name, issue_number,
                    )
                    continue
                edge_commands.append({
                    "command": "edge.create",
                    "params": {
                        "source": pr_task["iri"],
                        "target": issue_task["iri"],
                        "predicate": f"{BPKM}dependsOn",
                    },
                })
                edges_created += 1
        except Exception as exc:
            logger.warning(
                "Error fetching timeline for %s#%d: %s",
                repo_full_name, issue_number, exc,
            )
            error_count += 1
            failed_issues.append(
                f"{repo_full_name}#{issue_number}(timeline)"
            )

    if edge_commands:
        await _submit_commands_batched(http_client, edge_commands)

    # 10. Update sync cursor
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
        edges_created=edges_created,
    )

    await ctx.state.set("last_pull_result", json.dumps(result))
    logger.info(
        "Pull sync complete: status=%s created=%d updated=%d skipped=%d errors=%d edges=%d",
        overall_status, created_count, updated_count, skipped_count, error_count, edges_created,
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
    edges_created: int = 0,
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
        "edges_created": edges_created,
        "failed_issues": failed_issues or [],
        "duration_ms": duration_ms,
        "timestamp": timestamp,
    }
    if reason:
        result["reason"] = reason
    return result
