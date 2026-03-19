# S03: Push Sync + Settings Polish + Admin Detail

**Goal:** Complete bidirectional sync: SemPKM task changes push back to Linear; settings page has full sync controls; sync history and stats are visible.
**Demo:** User edits a synced task's status in SemPKM, triggers push, and the change appears in Linear (via GraphQL mutation). Settings page shows team checkboxes, sync direction toggle, poll interval, "Sync Now" button, and last sync results. Admin detail page already shows task run history from the platform scheduler.

## Must-Haves

- Reverse field mapper: bpkm taskStatus → Linear state type, bpkm priority → Linear priority int
- `build_issue_update_input()` builds `IssueUpdateInput` fields from bpkm task properties, resolving stateId from workflow states
- `push_sync(ctx)` detects changed tasks (dcterms:modified > bpkm:lastSyncedAt), reverse-maps, executes `issueUpdate` mutations, updates lastSyncedAt
- Loop prevention: pull_sync skips issues whose updatedAt ≤ task's lastSyncedAt (prevents re-importing pushed changes)
- LinearClient gains `get_workflow_states(team_id)` and `update_issue(issue_id, input_dict)` convenience methods
- Pull sync stores Linear issue UUID (the `id` field) as `bpkm:externalUuid` so push sync can target the right issue
- Settings page: team multi-select checkboxes, sync direction radio (pull-only / bidirectional), poll interval dropdown, "Sync Now" button
- Settings page: sync stats section showing last sync time, result counts, total synced tasks
- `push-changes` task registered in manifest and wired in app.py
- ~45-55 unit tests covering all reverse mapping, push sync, and loop prevention logic

## Proof Level

- This slice proves: contract (unit tests for all pure logic + engine orchestration with mocked clients)
- Real runtime required: no (deferred to S04 E2E test)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v` — all tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py tests/test_push_sync.py -v` — all 81 existing + new tests pass together
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/field_mapper.py').read())"` — syntax valid
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/sync_engine.py').read())"` — syntax valid
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/linear_client.py').read())"` — syntax valid
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read())"` — syntax valid
- Verify `push-changes` task appears in `manifest.yaml`
- Verify settings template has team checkboxes, sync direction radios, poll interval select, Sync Now button, and sync stats section

## Observability / Diagnostics

- Runtime signals: Logger `linear_sync.sync` at INFO for push sync start/complete with counts (pushed/skipped/errors); WARNING for per-task push failures
- Inspection surfaces: StateClient keys `last_push_result` (JSON), `last_sync_at`, `sync_direction`, `poll_interval`; sync stats section on settings page
- Failure visibility: push_sync() return dict `{status, pushed, skipped, errors}` with per-task error details; last_push_result persisted in state for settings page display
- Redaction constraints: none (no secrets in sync metadata)

## Integration Closure

- Upstream surfaces consumed: `field_mapper.py` forward mapping constants (S02), `sync_engine.py` `_submit_commands_batched()` and `_find_existing_task()` (S02), `LinearClient` query/pagination (S01), `auth.py` `get_connection_status()` (S01)
- New wiring introduced in this slice: `push-changes` task handler in `app.py`, `push_sync()` import from `sync_engine.py`, settings form POST routes, sync-now route
- What remains before the milestone is truly usable end-to-end: S04 E2E test against mocked Linear API + user guide Chapter 34

## Tasks

- [ ] **T01: Reverse field mapper + LinearClient mutations + store issue UUID** `est:45m`
  - Why: Push sync needs reverse mapping functions (bpkm→Linear), LinearClient mutation methods, and the Linear issue UUID stored during pull sync. These are the foundational pieces everything else builds on.
  - Files: `apps/linear-sync/services/field_mapper.py`, `apps/linear-sync/services/linear_client.py`, `apps/linear-sync/services/sync_engine.py`, `backend/tests/test_push_sync.py`
  - Do: Add reverse mapping constants and functions to field_mapper.py. Add `get_workflow_states()` and `update_issue()` to LinearClient. Modify pull sync's `build_task_properties()` to store `bpkm:externalUuid` from `issue["id"]`. Write ~25 unit tests for all reverse mapping functions and LinearClient additions.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v` — all tests pass; existing tests still pass
  - Done when: Reverse mapping functions tested for all status/priority values + unknown inputs; `build_issue_update_input()` correctly resolves stateId from workflow states; LinearClient mutation methods tested; pull sync stores externalUuid

- [ ] **T02: Push sync engine with loop prevention and unit tests** `est:50m`
  - Why: The core push-back logic — detecting changed tasks, building mutations, executing them, preventing re-import loops. This is the main deliverable of the slice.
  - Files: `apps/linear-sync/services/sync_engine.py`, `backend/tests/test_push_sync.py`
  - Do: Add `push_sync(ctx)` to sync_engine.py with changed-task SPARQL detection, reverse field mapping, per-task `issueUpdate` mutation, lastSyncedAt update, and error isolation. Add loop prevention to `pull_sync()` — compare issue `updatedAt` with task's `lastSyncedAt` to skip provider-originated changes. Write ~25 unit tests for push_sync orchestration, change detection, loop prevention, error paths.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v` — all tests pass; `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py tests/test_push_sync.py -v` — full suite passes
  - Done when: push_sync() detects changed tasks, reverse-maps properties, executes mutations, updates lastSyncedAt; pull_sync() skips re-importing pushed changes; error isolation verified

- [ ] **T03: Settings page polish + push-changes wiring + sync stats** `est:40m`
  - Why: The user-facing settings controls and the runtime wiring that makes push sync actually run. Without this, push sync is dead code.
  - Files: `apps/linear-sync/app.py`, `apps/linear-sync/manifest.yaml`, `apps/linear-sync/frontend/templates/connect_status.html`, `apps/linear-sync/frontend/static/styles.css`
  - Do: Replace read-only team table with checkbox form POSTing to `/_fragments/settings/teams`. Add sync direction radios and poll interval select POSTing to `/_fragments/settings/sync-config`. Add "Sync Now" button triggering `/_fragments/sync-now`. Add sync stats section showing last sync time/results/total synced count. Add `push-changes` task to manifest.yaml. Wire `push_changes` task handler in app.py calling `push_sync(ctx)`. Add all new routes to app.py.
  - Verify: `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read())"` — syntax valid; manifest.yaml has `push-changes` task; connect_status.html has team checkboxes, sync direction, poll interval, Sync Now, and stats section
  - Done when: Settings page has full sync controls with working form submissions; push-changes task registered and wired; sync stats section displays state data

## Files Likely Touched

- `apps/linear-sync/services/field_mapper.py`
- `apps/linear-sync/services/linear_client.py`
- `apps/linear-sync/services/sync_engine.py`
- `apps/linear-sync/app.py`
- `apps/linear-sync/manifest.yaml`
- `apps/linear-sync/frontend/templates/connect_status.html`
- `apps/linear-sync/frontend/static/styles.css`
- `backend/tests/test_push_sync.py`
