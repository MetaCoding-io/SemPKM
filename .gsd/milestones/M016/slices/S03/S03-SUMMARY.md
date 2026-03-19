---
id: S03
parent: M016
milestone: M016
provides:
  - Reverse field mapping (bpkm→Linear) for status, priority, title, dueDate
  - build_issue_update_input() constructing issueUpdate mutation inputs with workflow state resolution
  - LinearClient.get_workflow_states() and update_issue() GraphQL mutation methods
  - bpkm:externalUuid stored during pull sync for push targeting
  - push_sync(ctx) orchestrator with SPARQL change detection, per-task mutations, lastSyncedAt tracking
  - Loop prevention in pull_sync() — skips issues where updatedAt ≤ lastSyncedAt
  - push-changes scheduled task handler in app.py
  - Settings page with team checkboxes, sync direction radios, poll interval select, Sync Now button, sync stats
  - 3 new POST routes for settings persistence (teams, sync-config, sync-now)
  - _render_connect_status() shared helper for consistent template re-renders
requires:
  - slice: S02
    provides: field_mapper.py forward mapping constants, sync_engine.py _submit_commands_batched() and _find_existing_task(), pull_sync() infrastructure, IRI minting pattern
  - slice: S01
    provides: LinearClient with authenticated GraphQL transport, StateClient token storage, auth.py get_connection_status()
affects:
  - S04
key_files:
  - apps/linear-sync/services/field_mapper.py
  - apps/linear-sync/services/linear_client.py
  - apps/linear-sync/services/sync_engine.py
  - apps/linear-sync/app.py
  - apps/linear-sync/manifest.yaml
  - apps/linear-sync/frontend/templates/connect_status.html
  - apps/linear-sync/frontend/static/styles.css
  - backend/tests/test_push_sync.py
key_decisions:
  - "D205: REVERSE_STATUS_MAP maps todo→backlog (most common default); unknown status defaults to backlog; unknown priority returns None"
  - "D206: Loop prevention via updatedAt ≤ lastSyncedAt string comparison on ISO-8601 timestamps"
  - "D207: Shared _render_connect_status() helper for full template re-render on every settings POST"
  - "push_sync uses first team_id from sync_teams for workflow state lookup (single-team push simplification for v1)"
  - "Per-task error isolation in push_sync — errors accumulated, processing continues"
patterns_established:
  - "push_sync follows same auth-check → state-read → process → store-result pattern as pull_sync"
  - "Settings form POST routes return full connect_status.html re-render via shared helper — htmx replaces #connect-content"
  - "_find_changed_tasks SPARQL filters bidirectional tasks with modified > lastSyncedAt"
observability_surfaces:
  - "StateClient keys: last_push_result (JSON with status/pushed/skipped/errors), last_pull_result (JSON with status/created/updated/unchanged/errors)"
  - "StateClient keys: sync_teams, sync_direction, poll_interval, last_sync_at"
  - "Settings page sync stats section shows last sync time, pull/push result counts, error counts"
  - "Logger linear_sync.sync at INFO for push sync start/complete with counts; WARNING for per-task failures"
drill_down_paths:
  - .gsd/milestones/M016/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M016/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M016/slices/S03/tasks/T03-SUMMARY.md
duration: 60m
verification_result: passed
completed_at: 2026-03-18
---

# S03: Push Sync + Settings Polish + Admin Detail

**Bidirectional sync complete: reverse field mapping, push_sync() with change detection and loop prevention, full settings control panel with team/direction/interval configuration and sync stats**

## What Happened

Three tasks built the push sync pipeline bottom-up.

**T01** added the foundational reverse mapping layer. `REVERSE_STATUS_MAP` and `REVERSE_PRIORITY_MAP` translate bpkm task properties back to Linear enum values. `build_issue_update_input()` constructs the `issueUpdate` mutation payload, resolving Linear `stateId` from a workflow states lookup keyed by `(team_id, state_type)`. Unknown status values default to `backlog`; unknown priorities produce `None` (field omitted rather than forced to an incorrect value). `LinearClient` gained two methods: `get_workflow_states(team_id)` for fetching a team's workflow state definitions, and `update_issue(issue_id, input_dict)` for the `issueUpdate` GraphQL mutation. Pull sync was modified to store `bpkm:externalUuid` from Linear's issue `id` field — push sync needs this UUID because Linear mutations take UUID, not the human-readable identifier. 44 unit tests.

**T02** built the push sync orchestrator. `_find_changed_tasks()` runs a SPARQL query to find tasks where `dcterms:modified > bpkm:lastSyncedAt`, filtering out pull-only tasks. `_resolve_workflow_states()` fetches states for each synced team and builds a `(team_id, state_type) → state_id` lookup. `push_sync(ctx)` ties it all together: auth check → read sync state → find changed tasks → fetch workflow states → per-task reverse mapping and mutation → update lastSyncedAt → store `last_push_result`. Per-task error isolation ensures a single mutation failure doesn't abort the batch.

Loop prevention was added to `pull_sync()`: after finding an existing task, if the issue's `updatedAt ≤ lastSyncedAt`, the issue is skipped — preventing re-import of push-originated changes. `_find_existing_task()` was extended to return `lastSyncedAt`. Pull sync also gained `last_pull_result` storage (paralleling push). 25 unit tests.

**T03** wired everything to runtime. `manifest.yaml` gained the `push-changes` task (15m interval with retry policy). `app.py` got a `push_changes` handler calling `push_sync(ctx)`, plus three POST routes: `/_fragments/settings/teams` for team selection, `/_fragments/settings/sync-config` for direction and interval, and `/_fragments/sync-now` for manual sync. A shared `_render_connect_status()` helper reads all sync state and re-renders the full template — every route returns consistent state via htmx `#connect-content` swap.

The `connect_status.html` template was rewritten as a full sync control panel: team checkboxes with pre-checked state, direction radios (pull-only/bidirectional), interval dropdown (5m/15m/30m/1h), Sync Now button with htmx loading indicator, and sync stats showing last sync time, result counts, and errors.

## Verification

- 69 tests in `test_push_sync.py` — all pass (44 T01 + 25 T02)
- 150 tests across full Linear sync suite (`test_field_mapper.py` + `test_person_matcher.py` + `test_sync_engine.py` + `test_push_sync.py`) — all pass
- 6 failure-path tests pass (unknown status defaults, missing workflow states, unknown priority returns None, per-task error isolation)
- All 4 Python source files pass `ast.parse()` syntax validation
- `manifest.yaml` contains `push-changes` task entry
- `connect_status.html` contains team checkboxes, sync direction, poll interval, Sync Now, and sync stats references (16 matches across those identifiers)

## Requirements Advanced

- SYNC-03 (push sync) — push_sync() detects changed tasks, reverse-maps properties, executes issueUpdate mutations with loop prevention. Fully implemented with contract verification (150 unit tests). Runtime verification deferred to S04 E2E test.
- SYNC-04 (settings UI) — settings page has team selection, sync direction toggle, poll interval configuration, Sync Now button, and sync stats display. All controls persist via StateClient and POST routes.
- SYNC-05 (admin sync history) — sync run history visible through platform scheduler's existing Task History display (push-changes task now registered). Sync stats section on settings page shows last sync results.

## Requirements Validated

- None newly validated — SYNC-03/04/05 are advanced but await S04 E2E integration test for full validation.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- T03 added `_render_connect_status()` shared helper not explicitly in the plan — necessary for consistent re-renders across 4 routes.
- T03 updated `connect_api_key` success path to pass sync state variables — not planned but required for correct template rendering after initial connect.
- T01 delivered 44 tests (plan estimated ~25) due to more thorough coverage of constant values and edge cases.

## Known Limitations

- Push sync uses the first team_id from `sync_teams` for workflow state lookup — single-team push only in v1. Multi-team push would need per-task team_id resolution from Linear issue metadata.
- No runtime verification yet — all push sync logic is tested via unit tests with mocked clients. Real Linear API integration deferred to S04 E2E test with mocked API.
- Settings page UI is not yet rendered in a running Docker stack — T03 verified via syntax checks, grep, and test suite only.

## Follow-ups

- S04: E2E Playwright test against mocked Linear API proving install → configure → poll → push → verify flow
- S04: User guide Chapter 34 documenting the full Linear sync workflow

## Files Created/Modified

- `apps/linear-sync/services/field_mapper.py` — Added REVERSE_STATUS_MAP, REVERSE_PRIORITY_MAP, reverse_status(), reverse_priority(), build_issue_update_input(), and bpkm:externalUuid in build_task_properties()
- `apps/linear-sync/services/linear_client.py` — Added get_workflow_states(team_id) and update_issue(issue_id, input_dict) methods
- `apps/linear-sync/services/sync_engine.py` — Added _find_changed_tasks(), _resolve_workflow_states(), push_sync(), loop prevention in pull_sync(), last_pull_result storage, lastSyncedAt in _find_existing_task()
- `apps/linear-sync/app.py` — Added push_changes handler, 3 settings POST routes, _render_connect_status helper, updated connect_fragment and connect_api_key to pass sync state
- `apps/linear-sync/manifest.yaml` — Added push-changes task with 15m interval and retry policy
- `apps/linear-sync/frontend/templates/connect_status.html` — Rewritten as full sync control panel
- `apps/linear-sync/frontend/static/styles.css` — Added styles for team checkboxes, sync config form, sync now section, sync stats card
- `backend/tests/test_push_sync.py` — Created with 69 unit tests covering reverse mapping, push sync orchestration, change detection, loop prevention, error paths

## Forward Intelligence

### What the next slice should know
- The complete Linear sync app is now feature-complete: OAuth/API key auth (S01), pull sync with delta cursor (S02), push sync with loop prevention (S03). S04's job is to prove it works end-to-end against mocked API and document it.
- All sync state lives in StateClient keys: `access_token`, `refresh_token`, `workspace_id`, `workspace_name`, `sync_teams`, `sync_direction`, `poll_interval`, `last_sync_at`, `last_pull_result`, `last_push_result`.
- The sync engine imports are split: `pull_sync` and `push_sync` in `sync_engine.py`, field mapping in `field_mapper.py`, API client in `linear_client.py`, person matching in `person_matcher.py`.

### What's fragile
- `_find_changed_tasks()` SPARQL relies on string comparison of ISO-8601 timestamps — if the triplestore normalizes datetime formats differently, comparisons could break. Unit tests use mock SPARQL results, so this is untested against a real triplestore.
- push_sync's single-team workflow state lookup (first team from sync_teams) — multi-team workspaces will need per-task team resolution from stored issue metadata.

### Authoritative diagnostics
- `last_push_result` and `last_pull_result` state keys — JSON dicts with `{status, pushed/created, skipped/updated, errors}`. These are the primary runtime diagnostic surface for sync health.
- `test_push_sync.py` — 69 tests covering all pure logic paths; run this first when debugging push sync issues.

### What assumptions changed
- Plan estimated ~50 total tests across T01+T02; actual is 69 (T01: 44, T02: 25) due to more exhaustive constant coverage. This is better than expected.
- Admin detail page sync history was not explicitly built — the platform's existing Task History display covers it automatically when push-changes task is registered.
