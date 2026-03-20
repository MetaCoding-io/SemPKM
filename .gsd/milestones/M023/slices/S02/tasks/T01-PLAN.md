---
estimated_steps: 8
estimated_files: 2
---

# T01: Build sync_engine.py and wire app.py handlers

**Slice:** S02 — Pull sync + settings UI
**Milestone:** M023

## Description

Create the Jira pull sync engine that orchestrates all 5 S01 service modules (ADF converter, field mapper, Jira client, auth, person matcher) into a complete Jira→bpkm:Task pull pipeline. This follows the proven two-phase bulk create pattern from `apps/linear-sync/services/sync_engine.py` and `apps/google-calendar/services/sync_engine.py`. Jira-specific additions are: Epic→Milestone object creation, Epic→child linking, ADF→Markdown description conversion, and JQL query construction from selected projects + user JQL filter.

Also wire the app.py handlers (sync_now, poll-tasks, push-changes) to call the real sync functions instead of returning placeholder responses.

**Relevant skills:** none (standard Python async module)

## Steps

1. **Create `apps/jira-sync/services/sync_engine.py`** with the module docstring and imports. Use try/except ImportError for `services.X` vs flat imports (same pattern as GCal/Linear sync engines). Import: `adf_to_markdown` from `adf_converter`, `build_task_properties`, `build_milestone_properties`, `compute_issue_slug`, `BPKM` from `field_mapper`, `PersonMatcher` from `person_matcher`, `get_connection_status` from `auth`, `JiraClient` from `jira_client`.

2. **Add SPARQL lookup helpers:**
   - `_find_existing_task(graph_client, slug)` — find bpkm:Task with externalProvider "jira" using `STRENDS(STR(?task), "/Task/{slug}")`. Return `{"iri", "status", "externalId", "lastSyncedAt"}` or None.
   - `_find_existing_milestone(graph_client, slug)` — same but for bpkm:Milestone using `STRENDS(STR(?m), "/Milestone/{slug}")`. Return `{"iri"}` or None.

3. **Add command builder helpers:**
   - `_build_create_command(slug, properties, obj_type)` — `object.create` with type parameter (either `{BPKM}Task` or `{BPKM}Milestone`).
   - `_build_update_commands(existing_iri, properties, description, assignee_iri)` — returns list of `object.patch`, optional `body.set`, optional `edge.create` for assignedTo.
   - `_submit_commands_batched(http_client, commands, summary, source)` — batched POST to `/api/commands/bulk` with BATCH_SIZE=1000 (copy from Linear/GCal).

4. **Add JQL builder helper:**
   - `_build_jql(project_keys, jql_filter, last_sync_at)` — constructs JQL string:
     - Base: `project in (KEY1, KEY2)` (quoted keys)
     - If `jql_filter` provided: append ` AND ({jql_filter})`
     - If `last_sync_at` provided: append ` AND updated >= "YYYY/MM/DD HH:mm"` (convert ISO 8601 to Jira JQL date format — strip T, timezone, seconds)
   - Returns the full JQL string.

5. **Build `pull_sync(ctx)` function (~180 lines):**
   - Step 1: Check auth via `get_connection_status(ctx.state, client)` — skip if not connected
   - Step 2: Read config from `ctx.settings` (NOT ctx.state): `selected_projects`, `jql_filter`, `sync_direction`. Read `last_sync_at` from `ctx.state`.
   - Step 3: Build JQL via `_build_jql()`, call `client.search_all_issues(jql)` to get all matching issues
   - Step 4: Separate Epics from non-Epic issues by checking `fields.issuetype.name == "Epic"` (case-insensitive)
   - Step 5: Create PersonMatcher with 3 args: `PersonMatcher(ctx.graph, ctx.commands, client)` — Jira-specific, takes jira_client as 3rd arg
   - Step 6: Process Epics first — for each Epic:
     - `compute_issue_slug(project_key, epic_key)` for slug
     - Check existing via `_find_existing_milestone()`
     - `build_milestone_properties(epic, sync_time=sync_timestamp)` for properties
     - If new: add to create commands with type `{BPKM}Milestone`
     - If existing: add patch command
   - Step 7: Process non-Epic issues — for each issue:
     - Loop prevention: if existing and `issue.updated <= existing.lastSyncedAt`, skip (unchanged)
     - Resolve assignee: `person_matcher.resolve(fields.assignee.accountId, fields.assignee.displayName)` — fields.assignee can be None
     - Convert description: `adf_to_markdown(fields.description)` — fields.description can be None, adf_to_markdown(None) returns ""
     - `build_task_properties(issue, person_iri=assignee_iri, sync_time=sync_timestamp)`
     - If new: create command + defer body.set and assignee edge to Phase 2
     - If existing: update commands (patch + body.set + assignee edge)
     - Track Epic parent for linking: check `fields.parent.key` (next-gen) or `fields.customfield_10014` (classic Epic Link)
   - Step 8: Phase 1 — submit create commands (Tasks + Milestones) via `_submit_commands_batched()`
   - Step 9: Phase 2 — discover minted IRIs for new objects, submit `body.set` + `edge.create` commands
   - Step 10: Phase 3 — Epic→child linking: for each issue with a parent Epic, find the Milestone IRI and create `edge.create` with predicate `{BPKM}milestone` from Task to Milestone
   - Step 11: Submit all follow-up commands (updates + phase2 + epic links)
   - Step 12: Store `last_sync_at` in `ctx.state`, store `last_pull_result` in `ctx.state`
   - **Result dict keys must match template expectations:** `status` ("success"/"partial"/"error"/"skipped"), `created`, `updated`, `skipped`, `errors` (count), `failed_issues` (list of issue keys), `duration_ms` (elapsed time in ms). The template checks `{% if last_pull_result.status in ['success', 'partial'] %}` — do NOT use "ok".

6. **Build `push_sync(ctx)` stub:**
   - Check auth, check sync_direction (skip if pull-only)
   - Return `{"status": "skipped", "reason": "Push sync not yet implemented (S03)"}`
   - Store result in `ctx.state` as `last_push_result`
   - S03 will replace this with real push logic.

7. **Modify `apps/jira-sync/app.py` — wire 3 handlers:**
   - `sync_now` route: lazy import `from services.sync_engine import pull_sync, push_sync`. Call `pull_sync(ctx)` in try/except, store result. If `sync_direction == "bidirectional"`, also call `push_sync(ctx)`. Update `last_sync_at`. Re-render connect status. Follow the exact pattern from `apps/linear-sync/app.py` lines 300-325.
   - `poll-tasks` handler: lazy import `pull_sync`, call it, return result. Match linear-sync pattern.
   - `push-changes` handler: lazy import `push_sync`, call it, return result. Match linear-sync pattern.
   - **Critical:** Use `ctx.settings` (not `ctx.state`) for reading sync_direction in sync_now — this is a SettingsClient with `settings:` key prefix.

8. **Verify both files parse correctly:**
   - `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read())"`
   - `python3 -c "import ast; ast.parse(open('apps/jira-sync/app.py').read())"`

## Must-Haves

- [ ] `pull_sync(ctx)` function with two-phase bulk create, Epic→Milestone, Epic→child linking, ADF→Markdown, JQL construction, loop prevention, per-issue error isolation
- [ ] `push_sync(ctx)` stub returning skipped status
- [ ] `_build_jql()` constructs correct JQL with project keys, optional user filter, optional delta timestamp
- [ ] SPARQL lookup helpers for Task and Milestone by slug
- [ ] app.py sync_now calls pull_sync + conditionally push_sync
- [ ] app.py poll-tasks calls pull_sync
- [ ] app.py push-changes calls push_sync
- [ ] Result dict uses `status: "success"` (not "ok") to match connect_status.html template
- [ ] Uses `ctx.settings` for config (selected_projects, sync_direction, poll_interval, jql_filter) and `ctx.state` for runtime state (last_sync_at, last_pull_result)
- [ ] PersonMatcher constructed with 3 args: `(ctx.graph, ctx.commands, client)` — jira_client is the 3rd dependency

## Verification

- `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read())"` — valid Python
- `python3 -c "import ast; ast.parse(open('apps/jira-sync/app.py').read())"` — valid Python
- `grep -c "from services.sync_engine import" apps/jira-sync/app.py` — at least 3 occurrences (in sync_now, poll-tasks, push-changes)
- `grep "pull_sync\|push_sync" apps/jira-sync/app.py | wc -l` — at least 6 lines (imports + calls)

## Observability Impact

- Signals added/changed: Structured logging at INFO for sync phases (auth check, JQL, issue count, classification, phase 1/2/3 results, final summary). WARNING for per-issue errors and skip conditions.
- How a future agent inspects this: `ctx.state.get("last_pull_result")` and `ctx.state.get("last_push_result")` — JSON strings with status, counts, errors, duration. Also rendered in connect_status.html sync stats section.
- Failure state exposed: Result dict `errors` count + `failed_issues` list identifies which issues failed and why. `status: "partial"` when some succeed and some fail. `status: "error"` when all fail.

## Inputs

- `apps/jira-sync/services/adf_converter.py` — `adf_to_markdown(adf_doc)` function (S01 T01)
- `apps/jira-sync/services/field_mapper.py` — `build_task_properties()`, `build_milestone_properties()`, `compute_issue_slug()`, `BPKM` constant (S01 T02)
- `apps/jira-sync/services/jira_client.py` — `JiraClient` with `search_all_issues(jql)` (S01 T03)
- `apps/jira-sync/services/auth.py` — `get_connection_status(state, client)` (S01 T03)
- `apps/jira-sync/services/person_matcher.py` — `PersonMatcher(graph, commands, jira_client).resolve(account_id, display_name)` (S01 T03)
- `apps/jira-sync/app.py` — existing app with placeholder handlers (S01 T04)
- `apps/linear-sync/services/sync_engine.py` — reference implementation for two-phase bulk, ~529 lines
- `apps/linear-sync/app.py` lines 300-395 — reference for sync_now/poll-tasks/push-changes wiring pattern
- `apps/google-calendar/services/sync_engine.py` — reference for two-phase bulk + edge creation, ~715 lines

## Expected Output

- `apps/jira-sync/services/sync_engine.py` — new file, ~300 lines, with `pull_sync()`, `push_sync()` stub, SPARQL helpers, command builders, JQL builder, batched submission
- `apps/jira-sync/app.py` — modified, ~30 lines changed in 3 handlers (sync_now, poll-tasks, push-changes) to call real sync functions
