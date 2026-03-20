# S02 — Pull sync + settings UI — Research

**Date:** 2026-03-19
**Status:** Complete

## Summary

S02 wires the pull sync engine that orchestrates all 5 service modules from S01 (ADF converter, field mapper, Jira client, auth, person matcher) into a complete Jira → bpkm:Task pull pipeline. This also includes Epic → bpkm:Milestone mapping, Sprint → taskGroup, Component → tags, and the settings UI wiring (project selection, JQL filter, sync direction, Sync Now button).

This is well-understood work. Three existing sync engines (Linear, GitHub, Google Calendar) provide the exact pattern: two-phase bulk create, SPARQL slug lookup, edge creation, per-issue error isolation, loop prevention via lastSyncedAt. The Jira-specific additions are: (1) Epic→Milestone object creation with parent→child edge linking, (2) ADF→Markdown description conversion during pull, and (3) JQL query construction from selected project keys + user JQL filter.

## Recommendation

Clone the GCal sync engine structure (it's the most recent and cleanest). The Jira sync engine is simpler in some ways (no OAuth token refresh, no syncToken/410 recovery) but adds Epic→Milestone mapping which is novel. Build sync_engine.py as a single file, wire it into app.py's task handlers and sync-now route, then test with mocked clients using the same mock pattern as `test_gcal_sync_engine.py`.

Important: The jira-sync app.py uses `ctx.settings` for configuration (selected_projects, sync_direction, poll_interval, jql_filter) — this is a `SettingsClient` which adds a `settings:` key prefix to `StateClient`. The sync engine must use `ctx.settings` for reading config and `ctx.state` for runtime state (last_sync_at, last_pull_result).

## Implementation Landscape

### Key Files

**To create:**
- `apps/jira-sync/services/sync_engine.py` — `pull_sync(ctx)` function. Orchestrates JiraClient, field_mapper, person_matcher, adf_converter. Two-phase bulk create. Epic→Milestone with parent→child edge. Sprint→taskGroup and labels+components→tags already handled in field_mapper's `build_task_properties()`.
- `backend/tests/test_jira_sync_engine.py` — Unit tests with mocked clients (MockStateClient, MockSettingsClient, MockGraphClient, MockCommandClient, MockHttpClient). Cover: basic pull, Epic→Milestone, loop prevention, JQL construction, error isolation, empty states, skip conditions.

**To modify:**
- `apps/jira-sync/app.py` — Wire `sync_now` route to call `pull_sync(ctx)` + optionally `push_sync(ctx)` if bidirectional. Wire `poll-tasks` task handler to call `pull_sync(ctx)`. Wire `push-changes` task handler to call `push_sync(ctx)` (still a stub returning skipped for S02; S03 implements it). Follow the exact pattern from `apps/linear-sync/app.py` lines 295-320 (lazy import + try/except + result storage + re-render).

**Existing files consumed (read-only):**
- `apps/jira-sync/services/adf_converter.py` — `adf_to_markdown(adf_doc)` for converting issue descriptions
- `apps/jira-sync/services/field_mapper.py` — `build_task_properties()`, `build_milestone_properties()`, `compute_issue_slug()`, `BPKM` constant
- `apps/jira-sync/services/jira_client.py` — `JiraClient` with `search_all_issues(jql)`, `get_issue()`, error hierarchy
- `apps/jira-sync/services/auth.py` — `get_connection_status(state, client)`
- `apps/jira-sync/services/person_matcher.py` — `PersonMatcher(graph, commands, jira_client).resolve(account_id, display_name, email)`
- `apps/jira-sync/frontend/templates/connect_status.html` — Already has project selection, JQL filter, sync direction, poll interval, Sync Now button, and sync stats display. No template changes needed.

**Reference implementations:**
- `apps/google-calendar/services/sync_engine.py` — Best reference for two-phase bulk, edge creation, loop prevention
- `apps/linear-sync/services/sync_engine.py` — Best reference for pull_sync/push_sync structure, task→SPARQL lookup
- `apps/linear-sync/app.py` lines 295-395 — sync_now, poll-tasks, push-changes wiring pattern
- `backend/tests/test_gcal_sync_engine.py` — Best reference for sync engine test structure with mock clients

### Build Order

**1. sync_engine.py — pull_sync function (~250 lines)**

Core algorithm:
1. Check auth via `get_connection_status(ctx.state, client)`
2. Read config from `ctx.settings`: `selected_projects`, `jql_filter`, `sync_direction`
3. Read last_sync_at from `ctx.state`
4. Build JQL query: `project in (PROJ1, PROJ2)` + optional user JQL filter + optional `AND updated >= "{last_sync_at}"` for delta sync
5. Call `client.search_all_issues(jql)` — returns all matching issues
6. Separate Epics from non-Epic issues by checking `fields.issuetype.name == "Epic"`
7. Phase 1a — Create Milestone objects for new Epics via `build_milestone_properties(epic)`
8. Phase 1b — Create Task objects for new issues via `build_task_properties(issue, person_iri, sync_time)`
9. For each issue: convert description via `adf_to_markdown(fields.description)`, resolve assignee via `person_matcher.resolve(account_id, display_name, email)`
10. Phase 2 — Discover minted IRIs, submit body.set + edge.create (assignedTo edges)
11. Phase 3 — Link child issues to parent Epics via `bpkm:milestone` edge (if issue has `fields.parent` or Epic Link custom field pointing to an Epic)
12. Store `last_sync_at` and `last_pull_result` in `ctx.state`

**Key Jira-specific details:**
- **Epic detection:** `fields.issuetype.name == "Epic"` — Epics are regular issues with a special issue type
- **Epic→child linking:** Issues reference their Epic parent via `fields.parent.key` (next-gen projects) or `fields.customfield_10014` (classic Epic Link). The sync engine should check both.
- **JQL construction:** `project in (KEY1, KEY2)` is the base filter. Append user's JQL filter with AND if provided. Append `AND updated >= "YYYY-MM-DD HH:MM"` for delta sync. The Jira date format for JQL is `"YYYY/MM/DD HH:mm"` or `"YYYY-MM-DD HH:mm"`.
- **Description is ADF JSON:** `fields.description` is an ADF document dict (not a string). Call `adf_to_markdown(fields.description)` to get the markdown body.
- **Assignee accountId lookup:** `fields.assignee.accountId` — pass to `person_matcher.resolve(account_id, display_name)` (email is None in issue payloads; PersonMatcher calls Jira API internally).

**2. Wire app.py — modify 3 handlers (~30 lines changed)**

Replace the sync_now placeholder with real sync call. Replace poll-tasks and push-changes stubs. Copy the exact pattern from linear-sync/app.py.

**3. Tests (~60-80 tests)**

Mock clients following test_gcal_sync_engine.py pattern:
- `MockStateClient` — in-memory key-value store
- `MockSettingsClient` — same but with `settings:` prefix awareness (or just another MockStateClient)
- `MockGraphClient` — returns SPARQL results by slug lookup, supports Task and Milestone type queries
- `MockCommandClient` — records submitted commands, exposes `_client` for bulk bypass
- `MockHttpClient` — records bulk POST calls

Test categories:
- Pull sync happy path: issues → tasks with correct properties
- Epic detection and Milestone creation
- Epic→child linking via parent field
- ADF description → markdown body.set
- Assignee resolution via PersonMatcher
- Sprint → taskGroup mapping (already in field_mapper, verify it flows through)
- Labels + components → tags (already in field_mapper, verify it flows through)
- Delta sync with last_sync_at
- JQL construction: projects only, projects + user filter, delta append
- Loop prevention: skip issues where updatedAt <= lastSyncedAt
- Error isolation: one bad issue doesn't kill the whole sync
- Not connected → skip
- No projects selected → skip
- Empty issue list → ok with 0 counts
- Sync Now wiring in app.py (pull_sync called, result stored, status re-rendered)

### Verification Approach

```bash
cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py -v
```

All tests should pass. Combined with existing S01 tests:

```bash
cd backend && .venv/bin/python -m pytest tests/test_jira_*.py -v
```

Should show 237 (existing) + 60-80 (new) = ~300+ tests passing.

Structural checks:
- `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read())"` — valid Python
- `grep -c "pull_sync\|push_sync" apps/jira-sync/app.py` — should show imports wired in sync_now, poll-tasks, push-changes

## Constraints

- **`ctx.settings` for config, `ctx.state` for runtime** — The Jira app.py stores selected_projects, sync_direction, poll_interval, jql_filter under `ctx.settings` (which adds `settings:` key prefix). But last_sync_at, last_pull_result, last_push_result use `ctx.state` (no prefix). The sync engine must use the correct client for each key.
- **Two-phase bulk create** — Platform-minted IRIs use `urn:sempkm:object:` prefix which SDK CommandClient rejects (D204). Must bypass SDK by posting to `/api/commands/bulk` via `ctx.commands._client`.
- **PersonMatcher takes 3 args** — Jira's PersonMatcher constructor is `PersonMatcher(graph_client, command_client, jira_client)` — different from Linear/GitHub/GCal which take only 2 (graph, commands). The `jira_client` is needed because Jira issues only include opaque `accountId`, not email.
- **No template changes needed** — The connect_status.html template already renders all settings controls and sync stats. It supports `last_pull_result` with `created`, `updated`, `skipped`, `errors`, `failed_issues`, `duration_ms` fields. The sync engine result dict should use matching keys.
- **Milestone type IRI** — `build_milestone_properties()` exists in field_mapper.py. The object.create command needs `type: "{BPKM}Milestone"`. Verify this type exists in the basic-pkm model.

## Common Pitfalls

- **Confusing `ctx.settings` and `ctx.state`** — The Jira app.py stores config under `ctx.settings` (prefixed). If the sync engine reads `selected_projects` from `ctx.state`, it will always get None. Copy the key names exactly from app.py's `_render_connect_status()`.
- **PersonMatcher constructor arity** — Jira PersonMatcher takes `(graph, commands, jira_client)` not `(graph, commands)`. The `jira_client` is needed for accountId → email lookups.
- **ADF description can be None** — `fields.description` may be `None` for issues without a description. `adf_to_markdown(None)` returns `""` (safe), but don't try to `body.set` an empty string.
- **Epic parent field varies** — Next-gen Jira projects use `fields.parent` (a dict with `key` and `id`). Classic projects use `fields.customfield_10014` (the Epic Link custom field — a string like "PROJ-42"). Check both fields to find the parent Epic.
- **JQL date format** — Jira JQL `updated >=` accepts `"YYYY-MM-DD HH:mm"` or `"YYYY/MM/DD HH:mm"`. ISO 8601 format with `T` and timezone suffix does NOT work in JQL. Must strip the `T` and timezone.
- **Milestone object type** — When creating Milestone objects for Epics, the `compute_issue_slug()` will produce the same format as Tasks (`jira-{hash}`). This is correct — the slug is deterministic regardless of type. But the SPARQL lookup must search for `bpkm:Milestone` type, not `bpkm:Task`.

## Sources

- `apps/google-calendar/services/sync_engine.py` — Two-phase bulk create, edge creation, loop prevention pattern
- `apps/linear-sync/app.py` — sync_now, poll-tasks, push-changes handler wiring
- `backend/sdk/sempkm_app_sdk/clients/settings.py` — SettingsClient adds `settings:` key prefix to StateClient
- `apps/jira-sync/services/field_mapper.py` — `build_task_properties()`, `build_milestone_properties()`, `compute_issue_slug()`
