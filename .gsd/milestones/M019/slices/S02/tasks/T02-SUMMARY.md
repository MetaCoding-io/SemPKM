---
id: T02
parent: S02
milestone: M019
provides:
  - sync-config POST route saving direction/interval via ctx.settings
  - bidirectional sync_now handler calling push after pull
  - real push_changes task handler wired to push_sync
  - _render_connect_status enriched with sync settings and push result
  - settings UI with direction radios, poll interval dropdown, push stats
key_files:
  - apps/todoist-sync/app.py
  - apps/todoist-sync/frontend/templates/connect_status.html
  - backend/tests/test_todoist_push_sync.py
key_decisions:
  - Moved sync-now route from /_fragments/sync-now to /_fragments/settings/sync-now to match github-sync pattern
  - Settings stored via ctx.settings (not ctx.state) per plan — user-configurable vs internal sync bookkeeping distinction
patterns_established:
  - Todoist app.py route/handler structure mirrors github-sync exactly for consistency
observability_surfaces:
  - sync_direction and poll_interval readable via ctx.settings.get()
  - last_push_result state key rendered in connect_status.html push stats section
  - last_sync_at timestamp updated on every sync_now call
  - push_changes task handler logs result via todoist.sync logger
duration: 18m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Wire settings route, update app.py handlers, and add settings UI controls

**Wired push_sync into app routes, added sync-config/bidirectional sync_now/push_changes handlers, and extended settings UI with direction radios, poll interval dropdown, and push stats section — 71 tests pass**

## What Happened

Connected T01's push_sync engine to the Todoist app's HTTP route handlers and settings UI, following the github-sync reference implementation exactly:

1. Added `/_fragments/settings/sync-config` POST route that saves `sync_direction` and `poll_interval` via `ctx.settings.set()`.
2. Enriched `_render_connect_status()` to read and pass `sync_direction`, `poll_interval`, `last_push_result`, and `last_sync_at` to the template.
3. Updated `sync_now` handler to call `push_sync()` after `pull_sync()` when direction is "bidirectional", with try/except for error isolation. Updates `last_sync_at` timestamp on every call.
4. Replaced the `push_changes` placeholder with a real handler that imports and calls `push_sync()` with proper logging and error handling.
5. Rewrote `connect_status.html` to add sync configuration section (direction radios, poll interval dropdown), updated sync-now path to `/_fragments/settings/sync-now`, and added push stats section with closed/reopened/errors display.
6. Added 25 tests across 5 new test classes: `TestSyncConfigRoute` (5), `TestSyncNowBidirectional` (5), `TestPushChangesHandler` (3), `TestRenderConnectStatus` (9), `TestHtmxPrefixVerification` (3).

## Verification

- 71 tests in `test_todoist_push_sync.py` pass (46 from T01 + 25 from T02)
- 239 total Todoist tests pass in 0.48s
- All `hx-post`/`hx-get` URLs in templates use `/app/todoist-sync/` prefix
- Error isolation tests confirm push failures don't crash sync_now handler

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest backend/tests/test_todoist_push_sync.py -v` | 0 | ✅ pass | 0.35s |
| 2 | `python -m pytest backend/tests/test_todoist_*.py -v` | 0 | ✅ pass | 0.48s |
| 3 | `rg "hx-(post\|get)=" apps/todoist-sync/frontend/templates/ \| grep -v "/app/todoist-sync/"` | 1 (empty) | ✅ pass | <0.1s |
| 4 | `python -m pytest backend/tests/test_todoist_push_sync.py -v -k "error"` | 0 | ✅ pass | 0.24s |

## Diagnostics

- **Sync settings:** `await ctx.settings.get("sync_direction")` and `await ctx.settings.get("poll_interval")` — readable from any handler
- **Push result:** `await ctx.state.get("last_push_result")` — JSON with status, pushed, skipped, closed, reopened, updated, errors, timestamp
- **Last sync:** `await ctx.state.get("last_sync_at")` — ISO timestamp of most recent sync_now call
- **Logger:** `todoist.sync` — INFO for sync config saves and push-changes completion, ERROR for failures

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/todoist-sync/app.py` — Added sync-config route, bidirectional sync_now, real push_changes handler, enriched _render_connect_status
- `apps/todoist-sync/frontend/templates/connect_status.html` — Added sync config section, updated sync-now path, added push stats section
- `backend/tests/test_todoist_push_sync.py` — Added 25 route/handler/template tests (71 total)
- `.gsd/milestones/M019/slices/S02/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
