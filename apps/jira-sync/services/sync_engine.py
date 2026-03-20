"""Pull sync engine — fetches Jira issues and creates/updates bpkm:Task objects.

Orchestrates JiraClient, field mapper, person matcher, and ADF converter
into a complete Jira → bpkm:Task pull sync pipeline.  Commands bypass the
SDK's ``CommandClient`` (which enforces IRI prefix checks) by posting
directly to ``/api/commands/bulk`` via the shared httpx client.

Two-phase bulk for new issues:
  Phase 1: ``object.create`` commands (no IRI needed — platform assigns it)
  Phase 2: SPARQL-discover minted IRIs, then submit ``body.set`` / ``edge.create``
  Phase 3: Epic→child linking (``bpkm:milestone`` edges from Tasks to Milestones)

For existing issues, all commands (patch, body, edge) go in one batch
because the IRI is already known from the SPARQL lookup.

Jira-specific additions over Linear/GCal pattern:
  - Epic → bpkm:Milestone object creation
  - Epic → child linking via ``fields.parent.key`` (next-gen) or
    ``fields.customfield_10014`` (classic Epic Link)
  - ADF → Markdown description conversion
  - JQL query construction from selected projects + user JQL filter
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

try:
    from services.adf_converter import adf_to_markdown, markdown_to_adf
    from services.field_mapper import (
        build_task_properties,
        build_milestone_properties,
        build_issue_patch,
        compute_issue_slug,
        BPKM,
    )
    from services.person_matcher import PersonMatcher
    from services.auth import get_connection_status
    from services.jira_client import JiraClient
except ImportError:
    from adf_converter import adf_to_markdown, markdown_to_adf
    from field_mapper import (
        build_task_properties,
        build_milestone_properties,
        build_issue_patch,
        compute_issue_slug,
        BPKM,
    )
    from person_matcher import PersonMatcher
    from auth import get_connection_status
    from jira_client import JiraClient

logger = logging.getLogger("jira_sync.sync")

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
        f'  ?task <{BPKM}externalProvider> "jira" .\n'
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


async def _find_existing_milestone(graph_client, slug: str) -> dict | None:
    """Check whether a Milestone with the given slug already exists.

    Uses ``STRENDS`` to match the slug suffix of the IRI.

    Returns ``{"iri"}`` or None.
    """
    sparql = (
        "SELECT ?m WHERE {\n"
        f"  ?m a <{BPKM}Milestone> .\n"
        f'  ?m <{BPKM}externalProvider> "jira" .\n'
        f'  FILTER(STRENDS(STR(?m), "/Milestone/{slug}"))\n'
        "} LIMIT 1"
    )
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    return {"iri": bindings[0]["m"]["value"]}


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------


def _build_create_command(slug: str, properties: dict, obj_type: str) -> dict:
    """Build an ``object.create`` command for a new Task or Milestone.

    Args:
        slug: Deterministic slug for the object.
        properties: Property dict (full IRI keys).
        obj_type: Full IRI type, e.g. ``{BPKM}Task`` or ``{BPKM}Milestone``.
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
# JQL builder
# ---------------------------------------------------------------------------


def _build_jql(
    project_keys: list[str],
    jql_filter: str | None = None,
    last_sync_at: str | None = None,
) -> str:
    """Construct a JQL query string from project keys and optional filters.

    Args:
        project_keys: List of Jira project keys (e.g. ``["PROJ", "ENG"]``).
        jql_filter: Optional user-supplied JQL fragment to AND-combine.
        last_sync_at: Optional ISO 8601 timestamp for delta sync — only
            issues updated after this time are fetched.

    Returns:
        Complete JQL string ready for ``search_all_issues()``.
    """
    # Base: project in (KEY1, KEY2)
    quoted_keys = ", ".join(f'"{k}"' for k in project_keys)
    jql = f"project in ({quoted_keys})"

    # Append user-supplied JQL filter
    if jql_filter and jql_filter.strip():
        jql += f" AND ({jql_filter.strip()})"

    # Append delta sync filter — convert ISO 8601 to Jira JQL date format
    if last_sync_at:
        jql_date = _iso_to_jql_date(last_sync_at)
        if jql_date:
            jql += f' AND updated >= "{jql_date}"'

    return jql


def _iso_to_jql_date(iso_timestamp: str) -> str | None:
    """Convert ISO 8601 timestamp to Jira JQL date format.

    Jira expects ``YYYY/MM/DD HH:mm`` — strips T separator, timezone,
    and seconds.

    Args:
        iso_timestamp: e.g. ``"2024-06-15T14:30:00+00:00"``

    Returns:
        e.g. ``"2024/06/15 14:30"`` or None if parsing fails.
    """
    try:
        # Handle both timezone-aware and naive ISO timestamps
        ts = iso_timestamp.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y/%m/%d %H:%M")
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Main pull sync
# ---------------------------------------------------------------------------


async def pull_sync(ctx) -> dict:
    """Run the full Jira → bpkm:Task/Milestone pull sync pipeline.

    Steps:
      1. Check auth status
      2. Read config from ctx.settings, runtime state from ctx.state
      3. Build JQL and fetch all matching issues
      4. Separate Epics from non-Epic issues
      5. Create PersonMatcher
      6. Process Epics → Milestone objects
      7. Process non-Epic issues → Task objects (with loop prevention)
      8. Phase 1: submit create commands (Tasks + Milestones)
      9. Phase 2: discover minted IRIs, submit body.set + edge.create
     10. Phase 3: Epic→child linking
     11. Submit all follow-up commands
     12. Store last_sync_at and last_pull_result

    Returns a result dict with ``status``, ``created``, ``updated``,
    ``skipped``, ``errors``, ``failed_issues``, and ``duration_ms``.
    """
    start_time = time.monotonic()

    # 1. Auth check
    client = JiraClient(http_client=ctx.http, state_client=ctx.state)
    status = await get_connection_status(ctx.state, client)
    if not status["connected"]:
        logger.info("pull_sync: skipping — not connected")
        return _make_result("skipped", start_time, reason="not connected")

    # 2. Read config from settings, runtime state from state
    selected_projects_json = await ctx.settings.get("selected_projects")
    selected_projects = json.loads(selected_projects_json) if selected_projects_json else []
    jql_filter = await ctx.settings.get("jql_filter") or ""
    sync_direction = await ctx.settings.get("sync_direction") or "pull-only"
    last_sync_at = await ctx.state.get("last_sync_at")

    if not selected_projects:
        logger.info("pull_sync: skipping — no projects selected")
        return _make_result("skipped", start_time, reason="no projects selected")

    # 3. Build JQL and fetch issues
    jql = _build_jql(selected_projects, jql_filter or None, last_sync_at)
    logger.info("pull_sync: JQL = %s", jql)

    all_issues = await client.search_all_issues(jql)
    logger.info("pull_sync: fetched %d issues from Jira", len(all_issues))

    if not all_issues:
        return _make_result("success", start_time)

    # 4. Separate Epics from non-Epic issues
    epics: list[dict] = []
    tasks: list[dict] = []
    for issue in all_issues:
        fields = issue.get("fields", {})
        issue_type = fields.get("issuetype", {})
        type_name = (issue_type.get("name") or "").lower()
        if type_name == "epic":
            epics.append(issue)
        else:
            tasks.append(issue)

    logger.info(
        "pull_sync: classified %d epics, %d non-epic issues",
        len(epics), len(tasks),
    )

    # 5. Create PersonMatcher (Jira-specific: 3 args — graph, commands, jira_client)
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
    failed_issues: list[str] = []

    # Deferred for Phase 2
    new_task_descriptions: dict[str, str] = {}   # slug → markdown description
    new_task_assignees: dict[str, str] = {}       # slug → person IRI

    # Deferred for Phase 3 (Epic→child linking)
    issue_epic_map: dict[str, str] = {}           # issue slug → epic slug
    epic_slug_map: dict[str, str] = {}            # epic key → epic slug

    # ---- 6. Process Epics → Milestone objects ----
    for epic in epics:
        try:
            epic_key = epic.get("key", "")
            fields = epic.get("fields", {})
            project_key = fields.get("project", {}).get("key", "")

            slug = compute_issue_slug(project_key, epic_key)
            epic_slug_map[epic_key] = slug

            existing = await _find_existing_milestone(ctx.graph, slug)
            properties = build_milestone_properties(epic, sync_time=sync_timestamp)

            if existing:
                # Update existing milestone
                update_commands.append({
                    "command": "object.patch",
                    "params": {"iri": existing["iri"], "properties": properties},
                })
                updated_count += 1
            else:
                # Create new milestone
                create_commands.append(
                    _build_create_command(slug, properties, f"{BPKM}Milestone")
                )
                created_count += 1

        except Exception as e:
            issue_key = epic.get("key", "unknown")
            failed_issues.append(issue_key)
            error_count += 1
            logger.warning("Error processing epic %s: %s", issue_key, e)

    # ---- 7. Process non-Epic issues → Task objects ----
    for issue in tasks:
        try:
            issue_key = issue.get("key", "")
            fields = issue.get("fields", {})
            project_key = fields.get("project", {}).get("key", "")

            slug = compute_issue_slug(project_key, issue_key)
            existing = await _find_existing_task(ctx.graph, slug)

            # Loop prevention: skip unchanged issues
            if existing and existing.get("lastSyncedAt"):
                issue_updated = fields.get("updated", "")
                if issue_updated and issue_updated <= existing["lastSyncedAt"]:
                    skipped_count += 1
                    continue

            # Resolve assignee
            assignee = fields.get("assignee")
            assignee_iri = None
            if assignee and assignee.get("accountId"):
                assignee_iri = await person_matcher.resolve(
                    assignee["accountId"],
                    assignee.get("displayName"),
                )

            # Convert ADF description to Markdown
            raw_description = fields.get("description")
            description = adf_to_markdown(raw_description)

            # Build task properties
            properties = build_task_properties(
                issue, person_iri=assignee_iri, sync_time=sync_timestamp,
            )

            # Track Epic parent for Phase 3 linking
            parent_epic_key = _get_parent_epic_key(fields)
            if parent_epic_key:
                issue_epic_map[slug] = parent_epic_key

            if existing:
                # Update existing task
                update_commands.extend(
                    _build_update_commands(
                        existing["iri"], properties, description, assignee_iri,
                    )
                )
                updated_count += 1
            else:
                # New task — Phase 1 create, defer body + edges to Phase 2
                create_commands.append(
                    _build_create_command(slug, properties, f"{BPKM}Task")
                )
                if description:
                    new_task_descriptions[slug] = description
                if assignee_iri:
                    new_task_assignees[slug] = assignee_iri
                created_count += 1

        except Exception as e:
            issue_key = issue.get("key", "unknown")
            failed_issues.append(issue_key)
            error_count += 1
            logger.warning("Error processing issue %s: %s", issue_key, e)

    # ---- 8. Phase 1: submit create commands (Tasks + Milestones) ----
    if create_commands:
        logger.info("pull_sync: Phase 1 — submitting %d create commands", len(create_commands))
        await _submit_commands_batched(
            http_client,
            create_commands,
            f"Jira sync: created {len(create_commands)} objects",
            "jira-sync",
        )

    # ---- 9. Phase 2: discover minted IRIs, submit body.set + edge.create ----
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

    # ---- 10. Phase 3: Epic→child linking ----
    epic_link_commands: list[dict] = []
    for issue_slug, epic_key in issue_epic_map.items():
        epic_slug = epic_slug_map.get(epic_key)
        if not epic_slug:
            continue

        # Find the Milestone IRI for the epic
        milestone_info = await _find_existing_milestone(ctx.graph, epic_slug)
        if not milestone_info:
            continue

        # Find the Task IRI for the issue
        task_info = await _find_existing_task(ctx.graph, issue_slug)
        if not task_info:
            continue

        epic_link_commands.append({
            "command": "edge.create",
            "params": {
                "source": task_info["iri"],
                "predicate": f"{BPKM}milestone",
                "target": milestone_info["iri"],
            },
        })

    if epic_link_commands:
        logger.info(
            "pull_sync: Phase 3 — %d epic→child links", len(epic_link_commands)
        )

    # ---- Phase 4: Issue link processing (dependsOn edges) ----
    issue_link_commands = await _process_issue_links(all_issues, ctx.graph)
    if issue_link_commands:
        logger.info(
            "pull_sync: Phase 4 — %d issue link (dependsOn) edges",
            len(issue_link_commands),
        )

    # ---- 11. Submit all follow-up commands ----
    all_follow_up = update_commands + phase2_commands + epic_link_commands + issue_link_commands
    if all_follow_up:
        logger.info(
            "pull_sync: submitting %d follow-up commands "
            "(updates=%d, phase2=%d, epic-links=%d, issue-links=%d)",
            len(all_follow_up),
            len(update_commands),
            len(phase2_commands),
            len(epic_link_commands),
            len(issue_link_commands),
        )
        await _submit_commands_batched(
            http_client,
            all_follow_up,
            f"Jira sync: {updated_count} updates, "
            f"{len(phase2_commands)} follow-ups, "
            f"{len(epic_link_commands)} epic links, "
            f"{len(issue_link_commands)} issue links",
            "jira-sync",
        )

    # ---- 12. Store sync state ----
    await ctx.state.set("last_sync_at", sync_timestamp)

    result = _make_result(
        _compute_status(created_count, updated_count, skipped_count, error_count),
        start_time,
        created=created_count,
        updated=updated_count,
        skipped=skipped_count,
        errors=error_count,
        failed_issues=failed_issues,
        issue_links=len(issue_link_commands),
    )
    logger.info("Pull sync complete: %s", result)
    await ctx.state.set("last_pull_result", json.dumps(result))
    return result


# ---------------------------------------------------------------------------
# Parent Epic resolution
# ---------------------------------------------------------------------------


def _get_parent_epic_key(fields: dict) -> str | None:
    """Extract the parent Epic key from issue fields.

    Checks two sources:
    - ``fields.parent.key`` — next-gen Jira projects
    - ``fields.customfield_10014`` — classic Epic Link custom field

    Returns the epic issue key string or None.
    """
    # Next-gen: parent field
    parent = fields.get("parent")
    if parent and isinstance(parent, dict):
        parent_type = parent.get("fields", {}).get("issuetype", {}).get("name", "")
        if parent_type.lower() == "epic":
            return parent.get("key")

    # Classic: customfield_10014 (Epic Link)
    epic_link = fields.get("customfield_10014")
    if epic_link and isinstance(epic_link, str):
        return epic_link

    return None


# ---------------------------------------------------------------------------
# Issue link processing (Phase 4)
# ---------------------------------------------------------------------------


async def _process_issue_links(
    issues: list[dict], graph_client,
) -> list[dict]:
    """Create ``bpkm:dependsOn`` edges from Jira "Blocks" issue links.

    For each issue, inspects ``fields.issuelinks`` and processes links
    whose type name contains "block" (case-insensitive).  Only links
    with an ``inwardIssue`` key are processed — this means the current
    issue "is blocked by" the inward issue.  Processing only inward
    links avoids creating duplicate edges when both sides of the link
    are synced.

    Edge direction: ``source = current (blocked) task``,
    ``target = blocker task`` (the inwardIssue).

    Args:
        issues: Full list of Jira issues (tasks + epics).
        graph_client: Graph client for SPARQL lookups.

    Returns:
        List of ``edge.create`` command dicts.
    """
    edge_commands: list[dict] = []

    for issue in issues:
        issue_key = issue.get("key", "")
        fields = issue.get("fields", {})
        project_key = fields.get("project", {}).get("key", "")
        issue_links = fields.get("issuelinks", []) or []

        for link in issue_links:
            try:
                # Only process "Blocks"-family links
                link_type_name = link.get("type", {}).get("name", "")
                if "block" not in link_type_name.lower():
                    continue

                # Dedup: only process inwardIssue (current is blocked BY inward)
                inward = link.get("inwardIssue")
                if not inward:
                    continue

                blocker_key = inward.get("key", "")
                if not blocker_key:
                    continue

                # Extract project key from blocker issue key (e.g. "PROJ" from "PROJ-456")
                blocker_project = blocker_key.rsplit("-", 1)[0] if "-" in blocker_key else ""
                if not blocker_project:
                    continue

                # Compute slugs for both issues
                current_slug = compute_issue_slug(project_key, issue_key)
                blocker_slug = compute_issue_slug(blocker_project, blocker_key)

                # Look up both Task IRIs
                current_task = await _find_existing_task(graph_client, current_slug)
                if not current_task:
                    logger.debug(
                        "Issue link skip: current task %s not found in graph",
                        issue_key,
                    )
                    continue

                blocker_task = await _find_existing_task(graph_client, blocker_slug)
                if not blocker_task:
                    logger.debug(
                        "Issue link skip: blocker task %s not found in graph",
                        blocker_key,
                    )
                    continue

                edge_commands.append({
                    "command": "edge.create",
                    "params": {
                        "source": current_task["iri"],
                        "predicate": f"{BPKM}dependsOn",
                        "target": blocker_task["iri"],
                    },
                })

            except Exception as exc:
                logger.warning(
                    "Error processing issue link on %s: %s", issue_key, exc,
                )

    return edge_commands


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
    failed_issues: list[str] | None = None,
    reason: str | None = None,
    issue_links: int = 0,
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
        "failed_issues": failed_issues or [],
        "duration_ms": elapsed_ms,
        "issue_links": issue_links,
    }
    if reason:
        result["reason"] = reason
    return result


# ---------------------------------------------------------------------------
# Push sync — SPARQL change detection helpers
# ---------------------------------------------------------------------------


async def _find_changed_tasks(graph_client) -> list[dict]:
    """Find Jira-synced tasks that have local modifications.

    A task is considered changed when:
    - It has ``externalProvider = "jira"`` and ``externalId`` (was pulled)
    - Its ``dcterms:modified`` is greater than ``bpkm:lastSyncedAt``, or
      it has no ``lastSyncedAt`` (treat as changed)
    - Its ``syncDirection`` is not ``"pull-only"``

    Returns a list of dicts with keys:
    ``iri``, ``externalId``, ``status``, ``priority``, ``title``,
    ``lastSyncedAt``.
    """
    sparql = (
        "SELECT ?task ?extId ?status ?priority ?title ?lastSynced ?syncDir WHERE {\n"
        f'  ?task a <{BPKM}Task> .\n'
        f'  ?task <{BPKM}externalProvider> "jira" .\n'
        f'  ?task <{BPKM}externalId> ?extId .\n'
        f'  OPTIONAL {{ ?task <{BPKM}taskStatus> ?status }}\n'
        f'  OPTIONAL {{ ?task <{BPKM}priority> ?priority }}\n'
        f'  OPTIONAL {{ ?task <dcterms:title> ?title }}\n'
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
            "priority": row.get("priority", {}).get("value"),
            "title": row.get("title", {}).get("value"),
            "lastSyncedAt": row.get("lastSynced", {}).get("value"),
        })
    return tasks


async def _get_task_body(graph_client, iri: str) -> str | None:
    """Read task body text from the graph by IRI.

    Queries ``<iri> <urn:sempkm:body> ?body`` and returns the body
    text string, or None if no body is stored.
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
# Push sync — main pipeline
# ---------------------------------------------------------------------------


async def push_sync(ctx) -> dict:
    """Push local task changes back to Jira.

    Pipeline:
      1. Check auth status
      2. Check sync direction — skip if pull-only
      3. Find locally changed tasks via SPARQL
      4. For each changed task:
         a. Read body text via SPARQL
         b. Convert body to ADF via markdown_to_adf()
         c. Build reverse field mapping (title/priority + description)
         d. Call JiraClient.update_issue()
         e. Update lastSyncedAt on the pushed task
      5. Store last_push_result in state

    Per D237: push is limited to title/description/priority — no status
    transitions.

    Returns a result dict with ``status``, ``pushed``, ``skipped``,
    ``errors``, and ``timestamp`` fields.
    """
    # 1. Auth check
    client = JiraClient(http_client=ctx.http, state_client=ctx.state)
    status = await get_connection_status(ctx.state, client)
    if not status["connected"]:
        result = {"status": "skipped", "reason": "not connected"}
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    # 2. Check sync direction
    sync_direction = await ctx.settings.get("sync_direction") or "pull-only"
    if sync_direction == "pull-only":
        result = {"status": "skipped", "reason": "sync direction is pull-only"}
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    # 3. Find changed tasks
    changed_tasks = await _find_changed_tasks(ctx.graph)
    if not changed_tasks:
        logger.info("push_sync: no changed tasks found")
        result = {
            "status": "success",
            "pushed": 0,
            "skipped": 0,
            "errors": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    logger.info("push_sync: found %d changed tasks", len(changed_tasks))

    # 4. Push each changed task
    http_client = ctx.commands._client  # bypass SDK for bulk commands
    pushed_count = 0
    skipped_count = 0
    errors: list[dict] = []

    push_timestamp = datetime.now(timezone.utc).isoformat()

    for task in changed_tasks:
        try:
            # 4a. Read body text via SPARQL
            body_text = await _get_task_body(ctx.graph, task["iri"])

            # 4b. Convert body to ADF
            adf_doc = None
            if body_text:
                adf_doc = markdown_to_adf(body_text)

            # 4c. Build task properties dict from SPARQL result
            task_props: dict = {}
            if task.get("title"):
                task_props["dcterms:title"] = task["title"]
            if task.get("priority"):
                task_props[f"{BPKM}priority"] = task["priority"]

            # Reverse map to Jira fields
            fields = build_issue_patch(task_props, description_adf=adf_doc)

            if not fields:
                skipped_count += 1
                continue

            # 4d. Call Jira API — externalId IS the issue key
            await client.update_issue(task["externalId"], fields)

            # 4e. Update lastSyncedAt on the pushed task
            update_cmds = [{
                "command": "object.patch",
                "params": {
                    "iri": task["iri"],
                    "properties": {f"{BPKM}lastSyncedAt": push_timestamp},
                },
            }]
            await _submit_commands_batched(
                http_client, update_cmds,
                f"Jira push sync: update lastSyncedAt for {task['iri']}",
                "jira-sync",
            )

            pushed_count += 1

        except Exception as e:
            errors.append({"iri": task["iri"], "error": str(e)})
            logger.warning(
                "push_sync: error pushing task %s: %s", task["iri"], e
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
