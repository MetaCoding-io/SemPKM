---
id: T02
parent: S03
milestone: M017
provides:
  - sync-config POST route saving sync_direction and poll_interval via ctx.settings
  - bidirectional sync_now (pull + push when direction=bidirectional)
  - real push_changes task handler wired to push_sync()
  - _render_connect_status with sync_direction, poll_interval, last_push_result
  - connect_status.html with direction radios, poll interval dropdown, push stats
key_files:
  - apps/github-sync/app.py
  - apps/github-sync/frontend/templates/connect_status.html
  - backend/tests/test_github_sync_engine.py
key_decisions:
  - sync_direction and poll_interval stored in ctx.settings (not ctx.state), matching github-sync's existing settings pattern (selected_repos uses ctx.settings)
  - push_sync import deferred inside sync_now and push_changes handlers (same as linear-sync pattern) to avoid circular imports at module load
patterns_established:
  - _StubApp test helper for loading app.py via importlib — passthrough decorators let tests call route handlers directly as async functions
  - _RenderableAppContext captures template render calls for assertion without needing real Jinja2
observability_surfaces:
  - sync_direction in SettingsClient — read via ctx.settings.get("sync_direction"), default "pull-only"
  - poll_interval in SettingsClient — read via ctx.settings.get("poll_interval"), default "15m"
  - last_push_result in StateClient — JSON with status/pushed/skipped/errors/timestamp, displayed in template
  - Logger github_sync at INFO for sync config changes, push start/complete; ERROR for push failures with exc_info
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Settings UI routes, template polish, and route tests

**Wired push sync into app routes with sync-config settings, bidirectional sync_now, real push_changes handler, and settings UI with direction radios, poll interval dropdown, and push result stats — 15 new tests all passing (204 total suite).**

## What Happened

Added the `/_fragments/settings/sync-config` POST route to `apps/github-sync/app.py` that reads `sync_direction` and `poll_interval` from form data and stores them via `ctx.settings.set()`. Updated `sync_now` to check sync_direction after pull — when "bidirectional", it imports and calls `push_sync()` with its own try/except, then stores the result in state and sets `last_sync_at` after both complete. Replaced the stub `push_changes` task handler with a real implementation that calls `push_sync()` from `services.sync_engine`. Extended `_render_connect_status()` to read sync_direction, poll_interval, and last_push_result and pass them all to the template.

Updated `connect_status.html` to replace the placeholder sync direction section with a real form containing direction radio buttons (pull-only / bidirectional), a poll interval `<select>` dropdown, and a Save Config submit button. Added a push result stats group in the sync stats section that shows status, pushed count, skipped count, and error count — matching the linear-sync template pattern exactly. All htmx URLs use the `/app/github-sync/` proxy prefix.

Wrote 15 new tests covering: `_render_connect_status` passing new fields (5 tests), `sync_now` bidirectional behavior including push error isolation (3 tests), `sync_now` pull-only behavior (2 tests), `push_changes` handler (2 tests), and `sync-config` route settings persistence (3 tests). Used a `_StubApp` class with passthrough decorators to load `app.py` via importlib, and a `_RenderableAppContext` that captures template renders for assertion.

## Verification

- Full test suite: 204 tests pass (78 in sync_engine file, 126 across other files)
- Template verification: radio inputs for sync_direction ✓, select for poll_interval ✓, last_push_result stats ✓
- No stub text ("push sync not implemented yet") remains in app.py ✓
- All htmx URLs use `/app/github-sync/` prefix ✓

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py tests/test_github_client.py tests/test_github_auth.py tests/test_github_person_matcher.py -v` | 0 | ✅ pass | 12s |
| 2 | `rg '"push sync not implemented yet"' apps/github-sync/app.py` | 1 (no matches) | ✅ pass | <1s |
| 3 | `rg '/app/github-sync/' apps/github-sync/frontend/templates/connect_status.html` | 0 (4 matches) | ✅ pass | <1s |
| 4 | `rg 'name="sync_direction"' apps/github-sync/frontend/templates/connect_status.html` | 0 (2 matches) | ✅ pass | <1s |
| 5 | `rg 'name="poll_interval"' apps/github-sync/frontend/templates/connect_status.html` | 0 (1 match) | ✅ pass | <1s |

## Diagnostics

- **Settings inspection**: `ctx.settings.get("sync_direction")` returns "pull-only" or "bidirectional". `ctx.settings.get("poll_interval")` returns "5m"/"15m"/"30m"/"1h".
- **Push result inspection**: `ctx.state.get("last_push_result")` returns JSON string with `{status, pushed, skipped, errors, timestamp}`. The template renders this in the push stats section.
- **Logging**: `github_sync` logger emits INFO on sync config changes ("Saved sync config: direction=X interval=Y"), push-changes task start/complete, and manual sync trigger. ERROR with exc_info on push failures.
- **Error isolation**: Push errors in sync_now don't prevent last_sync_at from updating. Error result is stored separately in last_push_result.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/github-sync/app.py` — added sync-config route, updated sync_now with bidirectional push, replaced push_changes stub, extended _render_connect_status with new template vars
- `apps/github-sync/frontend/templates/connect_status.html` — replaced placeholder sync direction with real radio/select form and push result stats section
- `backend/tests/test_github_sync_engine.py` — added 15 new tests for route/handler behavior with _StubApp and _RenderableAppContext helpers
- `.gsd/milestones/M017/slices/S03/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
