# S02: Push Sync + Settings UI

**Goal:** Todoist tasks can be completed/reopened bidirectionally, and the settings UI controls sync direction, poll interval, and displays push results.
**Demo:** User completes a task in SemPKM → push_sync detects the status change → calls Todoist close endpoint. User reopens → calls reopen endpoint. Settings page has direction radios, poll interval dropdown, push stats section, and bidirectional Sync Now.

## Must-Haves

- `push_sync()` function that detects locally changed Todoist tasks via SPARQL, branches on status change direction (close/reopen), updates non-status fields via `update_task()`, and updates `lastSyncedAt` to prevent loops
- `_find_changed_tasks()` SPARQL query for todoist tasks with `modified > lastSyncedAt`
- Close/reopen ordering: status change first, then field update
- Loop prevention in pull_sync via `lastSyncedAt` comparison (skip tasks whose remote `updated_at` is ≤ `lastSyncedAt`)
- Settings route `/_fragments/settings/sync-config` POST saving `sync_direction` and `poll_interval` via `ctx.settings`
- `sync_now` handler calls push after pull when direction is bidirectional
- `push_changes` task handler wired to real `push_sync()`
- `_render_connect_status` passes `sync_direction`, `poll_interval`, `last_push_result` to template
- Settings UI: direction radios (pull-only/bidirectional), poll interval dropdown, push result stats section
- All htmx URLs use `/app/todoist-sync/` prefix
- 50+ unit tests covering push pipeline, close/reopen branching, settings route, template context

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018 && python -m pytest backend/tests/test_todoist_push_sync.py -v` — 50+ tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018 && python -m pytest backend/tests/test_todoist_*.py -v` — all Todoist tests (168 existing + 50+ new ≈ 218+) pass together in <3s
- `rg "hx-" apps/todoist-sync/frontend/templates/ | grep -v "/app/todoist-sync/"` — returns empty (htmx URL prefix check)
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018 && python -m pytest backend/tests/test_todoist_push_sync.py -v -k "error"` — push error isolation and result structure tests pass (diagnostic/failure-path check)

## Observability / Diagnostics

- Runtime signals: `todoist.sync` logger — INFO per push with pushed/skipped/errors counts, WARNING on individual task push failures
- Inspection surfaces: `last_push_result` state key — JSON with status, pushed, skipped, closed, reopened, updated, errors, timestamp
- Failure visibility: per-task error details in `last_push_result.errors` array with IRI and error message; push stats rendered in settings UI
- Redaction constraints: none (no secrets in push flow)

## Integration Closure

- Upstream surfaces consumed: `apps/todoist-sync/services/sync_engine.py` (pull_sync, _find_existing_task, _submit_commands_batched), `services/field_mapper.py` (BPKM_TO_TODOIST_STATUS, build_todoist_task_data), `services/todoist_client.py` (close_task, reopen_task, update_task), `services/auth.py` (get_connection_status)
- New wiring introduced: `push_sync()` in sync_engine.py, `sync_config` POST route in app.py, bidirectional sync_now, real push_changes task handler
- What remains before the milestone is truly usable end-to-end: S03 (E2E test + mock Todoist API server + user guide)

## Tasks

- [x] **T01: Implement push_sync engine with close/reopen branching and unit tests** `est:45m`
  - Why: Core push sync logic is the only novel piece in this milestone — Todoist uses separate close/reopen endpoints instead of PATCH for status changes. This task delivers the engine and proves it with comprehensive unit tests.
  - Files: `apps/todoist-sync/services/sync_engine.py`, `backend/tests/test_todoist_push_sync.py`
  - Do: Add `_find_changed_tasks()` SPARQL (todoist provider, modified > lastSyncedAt filter), `push_sync()` with auth check → direction check → find changed → for each: detect status change → close/reopen or update → lastSyncedAt update → store result. Add loop prevention to `pull_sync`. Write 35+ unit tests covering: `_find_changed_tasks` SPARQL parsing, push pipeline (not connected skip, pull-only skip, no changes, successful push with close, successful push with reopen, field-only update, combined status+field update ordering), loop prevention in pull, `lastSyncedAt` update after push, result structure.
  - Verify: `python -m pytest backend/tests/test_todoist_push_sync.py -v` — 35+ tests pass; `python -m pytest backend/tests/test_todoist_*.py -v` — all Todoist tests pass together
  - Done when: `push_sync()` correctly branches close/reopen/update and all push unit tests pass

- [x] **T02: Wire settings route, update app.py handlers, and add settings UI controls** `est:30m`
  - Why: Connects push_sync to the app's route handlers and gives users control over sync direction and poll interval. Completes the slice by wiring the engine (T01) into the UI and scheduler.
  - Files: `apps/todoist-sync/app.py`, `apps/todoist-sync/frontend/templates/connect_status.html`, `backend/tests/test_todoist_push_sync.py`
  - Do: Add `/_fragments/settings/sync-config` POST route saving direction/interval via `ctx.settings`. Update `_render_connect_status` to read `sync_direction`, `poll_interval`, `last_push_result` and pass to template. Update `sync_now` to call `push_sync` after pull when bidirectional. Replace `push_changes` placeholder with real `push_sync()` call. Add sync config section to `connect_status.html` (direction radios, poll interval dropdown) and push result stats section. All htmx URLs prefixed with `/app/todoist-sync/`. Write 15+ additional tests covering: sync-config route saves, bidirectional sync_now calls push, push_changes handler, template context variables, htmx prefix verification.
  - Verify: `python -m pytest backend/tests/test_todoist_push_sync.py -v` — 50+ total tests pass; `rg "hx-" apps/todoist-sync/frontend/templates/ | grep -v "/app/todoist-sync/"` — empty
  - Done when: Settings UI renders with direction/interval/push stats, sync_now runs bidirectional, push_changes calls real push_sync, all tests pass

## Files Likely Touched

- `apps/todoist-sync/services/sync_engine.py`
- `apps/todoist-sync/app.py`
- `apps/todoist-sync/frontend/templates/connect_status.html`
- `backend/tests/test_todoist_push_sync.py`
