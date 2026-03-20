# S02: Pull sync + settings UI

**Goal:** Jira issues sync to SemPKM as bpkm:Task objects with Markdown descriptions, correct status/priority/assignee, sprint as taskGroup, tags from labels+components. Epics become bpkm:Milestone objects with linked child tasks. Settings UI already built in S01 — this slice wires it to real sync logic.
**Demo:** User selects Jira projects, optionally enters a JQL filter, clicks Sync Now, and Jira issues appear as bpkm:Task objects. Epics appear as bpkm:Milestone objects with child tasks linked via bpkm:milestone edges. Sync stats update in the settings panel.

## Must-Haves

- `pull_sync(ctx)` function orchestrates JiraClient, field_mapper, person_matcher, adf_converter into a complete Jira→bpkm:Task pipeline
- Two-phase bulk create: Phase 1 creates objects (platform mints IRIs), Phase 2 discovers IRIs and submits body.set + edge.create
- Epic detection via `fields.issuetype.name == "Epic"` → creates bpkm:Milestone objects via `build_milestone_properties()`
- Epic→child linking via `fields.parent.key` (next-gen) or `fields.customfield_10014` (classic Epic Link)
- ADF description → Markdown body via `adf_to_markdown(fields.description)` with None safety
- JQL construction: `project in (KEY1, KEY2)` + optional user JQL + optional `AND updated >= "YYYY/MM/DD HH:mm"` for delta sync
- Assignee resolution via `PersonMatcher(graph, commands, jira_client).resolve(account_id, display_name)`
- Loop prevention: skip issues where `updatedAt <= lastSyncedAt`
- Per-issue error isolation (one bad issue doesn't kill the sync)
- `push_sync(ctx)` stub returns `{status: skipped, reason: "not yet implemented"}` (S03 implements real push)
- app.py `sync_now` route calls `pull_sync(ctx)` and conditionally `push_sync(ctx)` for bidirectional
- app.py `poll-tasks` handler calls `pull_sync(ctx)`
- app.py `push-changes` handler calls `push_sync(ctx)`
- Result dict uses `status: "success"` (not `"ok"`) to match connect_status.html template's `{% if last_pull_result.status in ['success', 'partial'] %}` check
- 60+ unit tests covering all sync paths with mocked clients

## Proof Level

- This slice proves: contract (sync engine tested with mocked clients, no live Jira)
- Real runtime required: no (unit tests with mocks; E2E deferred to S04)
- Human/UAT required: no

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023/backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py -v` — 60+ tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023/backend && .venv/bin/python -m pytest tests/test_jira_*.py -v` — all Jira tests pass (237 S01 + 60+ S02 = ~300+ total)
- `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read())"` — valid Python
- `python3 -c "import ast; ast.parse(open('apps/jira-sync/app.py').read())"` — valid Python
- `grep -c "pull_sync\|push_sync" apps/jira-sync/app.py` — shows imports wired in sync_now, poll-tasks, push-changes
- `grep -n "status.*error\|status.*partial\|failed_issues\|errors.*count\|WARNING" apps/jira-sync/services/sync_engine.py | head -20` — confirms failure-path signals (error status, partial status, failed_issues list, per-issue WARNING logging) are present in sync engine

## Observability / Diagnostics

- Runtime signals: Structured logging on sync phases (auth check, JQL construction, issue fetch count, epic/task classification, phase 1/2 submission, result summary). Per-issue error logged at WARNING level.
- Inspection surfaces: `last_pull_result` and `last_push_result` stored in `ctx.state` as JSON — inspectable via StateClient. Connect status template renders these as sync stats.
- Failure visibility: Result dict includes `status` (success/partial/error), `errors` list with per-issue `{issue_key, error}`, `failed_issues` list of keys, `duration_ms` for performance tracking.
- Redaction constraints: none (no secrets in sync data; auth credentials managed by S01 auth module)

## Integration Closure

- Upstream surfaces consumed: All 5 S01 service modules (`adf_converter.adf_to_markdown`, `field_mapper.build_task_properties/build_milestone_properties/compute_issue_slug`, `jira_client.JiraClient.search_all_issues`, `auth.get_connection_status`, `person_matcher.PersonMatcher.resolve`), plus `ctx.settings` for config and `ctx.state` for runtime state
- New wiring introduced in this slice: `sync_engine.py` orchestration module; app.py `sync_now`/`poll-tasks`/`push-changes` handlers wired to real sync functions
- What remains before the milestone is truly usable end-to-end: S03 (push sync + issue links), S04 (E2E tests + user guide)

## Tasks

- [x] **T01: Build sync_engine.py and wire app.py handlers** `est:1h`
  - Why: Creates the core pull sync engine that orchestrates all S01 services, plus wires app.py handlers to call it. This is all the production code for S02.
  - Files: `apps/jira-sync/services/sync_engine.py`, `apps/jira-sync/app.py`
  - Do: Build `pull_sync(ctx)` following Linear/GCal two-phase bulk pattern. Add Epic→Milestone creation, Epic→child linking, ADF→Markdown conversion, JQL construction with delta sync, loop prevention, per-issue error isolation. Add `push_sync(ctx)` stub. Wire app.py sync_now/poll-tasks/push-changes to real sync functions. Use `ctx.settings` for config, `ctx.state` for runtime state.
  - Verify: `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read())"` and `python3 -c "import ast; ast.parse(open('apps/jira-sync/app.py').read())"` both succeed
  - Done when: sync_engine.py has pull_sync + push_sync stub, app.py has all 3 handlers wired with lazy imports and try/except

- [x] **T02: Comprehensive unit tests for Jira sync engine** `est:1h`
  - Why: Validates all sync paths with mocked clients. Tests are the primary proof that pull_sync works correctly before E2E testing in S04.
  - Files: `backend/tests/test_jira_sync_engine.py`
  - Do: Write 60+ tests with mock clients (MockStateClient, MockSettingsClient, MockGraphClient, MockCommandClient, MockHttpClient) following test_gcal_sync_engine.py pattern. Cover: basic pull, Epic→Milestone, Epic→child linking, ADF description conversion, assignee resolution, JQL construction variants, delta sync, loop prevention, error isolation, not-connected skip, no-projects skip, empty results, sync_now wiring, push_sync stub.
  - Verify: `cd /home/james/Code/SemPKM/.gsd/worktrees/M023/backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py -v` — 60+ tests pass
  - Done when: All tests pass and combined `test_jira_*.py` suite shows 300+ passing tests

## Files Likely Touched

- `apps/jira-sync/services/sync_engine.py` (new — ~300 lines)
- `apps/jira-sync/app.py` (modify — wire 3 handlers, ~30 lines changed)
- `backend/tests/test_jira_sync_engine.py` (new — ~1500 lines, 60+ tests)
