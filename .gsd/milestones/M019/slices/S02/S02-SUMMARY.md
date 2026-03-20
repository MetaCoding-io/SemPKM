---
id: S02
parent: M019
milestone: M019
provides:
  - push_sync() engine with close/reopen branching for Todoist status changes
  - _find_changed_tasks() SPARQL query detecting locally modified Todoist tasks
  - Loop prevention in pull_sync via lastSyncedAt comparison
  - sync-config POST route saving direction/interval via ctx.settings
  - Bidirectional sync_now handler calling push after pull
  - Real push_changes task handler wired to push_sync
  - Settings UI with direction radios, poll interval dropdown, push stats section
requires:
  - slice: S01
    provides: auth module, TodoistClient, field_mapper (bidirectional mappings), person_matcher, pull_sync, route handlers, templates
affects:
  - S03
key_files:
  - apps/todoist-sync/services/sync_engine.py
  - apps/todoist-sync/app.py
  - apps/todoist-sync/frontend/templates/connect_status.html
  - backend/tests/test_todoist_push_sync.py
key_decisions:
  - Used externalId (not externalUuid) in _find_changed_tasks — Todoist pull_sync only populates externalId via field_mapper
  - Moved sync-now route from /_fragments/sync-now to /_fragments/settings/sync-now to match github-sync pattern
  - Settings stored via ctx.settings (user-configurable) vs ctx.state (internal sync bookkeeping) — same distinction as Linear/GitHub apps
patterns_established:
  - Todoist close/reopen endpoints called before update_task for combined status+field changes (status first, then field update)
  - Route/handler structure mirrors github-sync exactly for cross-app consistency
observability_surfaces:
  - last_push_result state key — JSON with status, pushed, skipped, closed, reopened, updated, errors, timestamp
  - todoist.sync logger — INFO per push cycle with aggregate counts, WARNING per task failure
  - sync_direction and poll_interval readable via ctx.settings.get()
  - last_sync_at state key — ISO timestamp of most recent sync_now call
drill_down_paths:
  - .gsd/milestones/M019/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M019/slices/S02/tasks/T02-SUMMARY.md
duration: 38m
verification_result: passed
completed_at: 2026-03-19
---

# S02: Push Sync + Settings UI

**Todoist tasks completable/reopenable bidirectionally with settings UI for sync direction, poll interval, and push result stats — proven by 71 push-specific + 239 total Todoist unit tests**

## What Happened

Two tasks delivered the complete push sync pipeline and settings integration:

**T01 (push engine + tests):** Added `_find_changed_tasks()` SPARQL query finding bpkm:Task objects with `externalProvider="todoist"` where `dcterms:modified > bpkm:lastSyncedAt`. Implemented `push_sync()` pipeline: auth check → direction check → find changed → per-task: detect status change → call `close_task()` or `reopen_task()` via dedicated Todoist endpoints → build reverse-mapped update body → call `update_task()` for non-status fields → update `lastSyncedAt`. Added loop prevention to `pull_sync()` — existing tasks with `lastSyncedAt >= remote updated_at` are skipped. 46 unit tests covering all pipeline paths.

**T02 (routes + settings UI):** Added `/_fragments/settings/sync-config` POST route saving direction/interval via `ctx.settings`. Enriched `_render_connect_status()` to pass `sync_direction`, `poll_interval`, `last_push_result`, `last_sync_at` to template. Updated `sync_now` to run `push_sync()` after `pull_sync()` when bidirectional. Replaced `push_changes` placeholder with real handler. Rewrote `connect_status.html` with sync configuration section (direction radios, poll interval dropdown) and push stats section. 25 additional tests.

Key deviation from plan: Used `externalId` instead of `externalUuid` in `_find_changed_tasks()` because Todoist pull_sync (via `build_task_properties`) only populates `externalId`. The plan referenced the github-sync pattern which uses `externalUuid`, but that doesn't apply to Todoist.

## Verification

| # | Check | Result |
|---|-------|--------|
| 1 | `python -m pytest backend/tests/test_todoist_push_sync.py -v` — 71 tests | ✅ 71 passed (0.71s) |
| 2 | `python -m pytest backend/tests/test_todoist_*.py -v` — all Todoist tests | ✅ 239 passed (0.83s) |
| 3 | `rg "hx-(post\|get)=" apps/todoist-sync/frontend/templates/ \| grep -v "/app/todoist-sync/"` | ✅ empty (all htmx URLs prefixed) |
| 4 | `python -m pytest backend/tests/test_todoist_push_sync.py -v -k "error"` — error isolation | ✅ 6 passed (0.65s) |

## Requirements Advanced

- TD-03 (push sync) — push_sync() correctly branches close/reopen/update with per-task error isolation and lastSyncedAt loop prevention
- TD-07 (settings UI) — direction radios, poll interval dropdown, push stats section, Sync Now runs bidirectional when configured

## Requirements Validated

- None formally validated yet — TD requirements not yet registered in REQUIREMENTS.md. S02 provides unit-test evidence for TD-03 and TD-07; formal validation deferred to S03 (E2E test + user guide).

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

Used `externalId` instead of `externalUuid` in `_find_changed_tasks()` SPARQL — correct for Todoist (pull_sync only populates externalId). Plan assumed github-sync pattern which uses externalUuid.

## Known Limitations

- Push sync only handles status changes and basic field updates (title, priority, labels, due date). It does not create new tasks in Todoist from SemPKM-originated tasks — only syncs changes to tasks that were originally pulled from Todoist.
- No E2E test coverage yet (S03 scope).
- No user guide documentation yet (S03 scope).

## Follow-ups

- None — S03 covers E2E test, mock server, and user guide.

## Files Created/Modified

- `apps/todoist-sync/services/sync_engine.py` — Added `_find_changed_tasks()`, `push_sync()`, loop prevention in `pull_sync()`, imports for `BPKM_TO_TODOIST_STATUS` and `build_todoist_task_data`
- `apps/todoist-sync/app.py` — Added sync-config route, bidirectional sync_now, real push_changes handler, enriched `_render_connect_status`
- `apps/todoist-sync/frontend/templates/connect_status.html` — Added sync config section (direction radios, poll interval dropdown), updated sync-now path, added push stats section
- `backend/tests/test_todoist_push_sync.py` — New test file with 71 tests (46 engine + 25 route/handler/template)

## Forward Intelligence

### What the next slice should know
- The app is fully functional: auth, pull sync, push sync, settings UI all wired. S03 only needs to build the mock server, E2E test, and user guide — no app code changes needed.
- 239 unit tests pass in <1s. The mock patterns from `test_todoist_push_sync.py` (MockResponse, MockState, MockSettings, MockCommandsClient) are reusable for the mock API server design.
- The Todoist REST API v2 is simpler than all prior sync targets — no pagination, no OAuth, no GraphQL. The mock server can be very lightweight.

### What's fragile
- The `externalId` vs `externalUuid` divergence from github-sync could confuse future agents comparing implementations. The Todoist app uses `externalId` exclusively — `externalUuid` is never set.
- htmx URL prefix (`/app/todoist-sync/`) is enforced by unit tests but verified only statically (grep). A real browser test in S03 will prove the routing end-to-end.

### Authoritative diagnostics
- `last_push_result` state key — JSON with status, pushed, skipped, closed, reopened, updated, errors, timestamp. The single most useful diagnostic for push issues.
- `todoist.sync` logger — INFO per cycle, WARNING per task failure. Check container logs.

### What assumptions changed
- Plan assumed `externalUuid` field usage (github-sync pattern) — Todoist actually uses `externalId` only. This is correct and intentional.
