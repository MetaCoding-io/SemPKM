---
id: T03
parent: S03
milestone: M016
provides:
  - push-changes task handler in app.py calling push_sync(ctx) — makes push sync reachable at runtime
  - POST /_fragments/settings/teams route for team selection persistence
  - POST /_fragments/settings/sync-config route for sync direction + poll interval persistence
  - POST /_fragments/sync-now route for immediate manual pull + push sync
  - Full sync control panel in connect_status.html — team checkboxes, direction radios, interval select, Sync Now, stats
  - _render_connect_status() shared helper for consistent re-renders across all settings routes
key_files:
  - apps/linear-sync/app.py
  - apps/linear-sync/manifest.yaml
  - apps/linear-sync/frontend/templates/connect_status.html
  - apps/linear-sync/frontend/static/styles.css
key_decisions:
  - "Shared _render_connect_status() helper reads all sync state and re-renders full template — every POST route returns consistent state without duplicating the data-fetching logic"
  - "Manual sync (/_fragments/sync-now) runs pull first, then push only if sync_direction is bidirectional — matches the scheduled task separation"
patterns_established:
  - "Settings form POST routes return full connect_status.html re-render via shared helper — htmx replaces #connect-content with the updated panel"
observability_surfaces:
  - "Settings page sync stats section — shows last sync time, pull/push result counts, error counts"
  - "State keys: sync_teams, sync_direction, poll_interval, last_sync_at, last_pull_result, last_push_result — all readable via StateClient"
  - "Logger linear_sync at INFO for team/config saves, manual sync start; ERROR with exc_info on sync failures"
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Settings page polish + push-changes wiring + sync stats

**Added push-changes task handler, 3 settings POST routes, and full sync control panel with team checkboxes, direction/interval config, Sync Now button, and sync stats display**

## What Happened

Transformed the read-only settings page into a full sync control panel. The manifest now registers both `poll-tasks` and `push-changes` as scheduled tasks. The app module has a `push_changes` handler calling `push_sync(ctx)`, plus three new POST routes: `/_fragments/settings/teams` (saves selected team IDs), `/_fragments/settings/sync-config` (saves direction + poll interval), and `/_fragments/sync-now` (triggers immediate pull+push). All routes use a shared `_render_connect_status()` helper that reads the full sync state from StateClient and re-renders the template.

The connect_status.html template was rewritten from a static teams table to a multi-section control panel: team checkboxes with pre-checked state, sync direction radios (pull-only/bidirectional), poll interval dropdown (5m/15m/30m/1h), Sync Now button with htmx loading indicator, and a sync stats card showing last sync time, pull/push result counts, and error counts. CSS was extended with styles for all new controls.

## Verification

- `app.py` parses without syntax errors
- `manifest.yaml` contains `push-changes` task entry
- `connect_status.html` contains `team_ids`, `sync_direction`, `sync-now`, and `sync-stats` references
- All 89 push sync + sync engine tests pass (0 failures)
- All 150 tests across field_mapper + person_matcher + sync_engine + push_sync pass
- All 6 failure-path tests pass (unknown status/priority defaults, missing workflow states, error isolation)
- All 4 Python module syntax checks pass (field_mapper, sync_engine, linear_client, app)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read())"` | 0 | ✅ pass | 3s |
| 2 | `grep -c "push-changes" apps/linear-sync/manifest.yaml` | 0 | ✅ pass (1 match) | <1s |
| 3 | `grep -c "team_ids" apps/linear-sync/frontend/templates/connect_status.html` | 0 | ✅ pass (1 match) | <1s |
| 4 | `grep -c "sync_direction" apps/linear-sync/frontend/templates/connect_status.html` | 0 | ✅ pass (4 matches) | <1s |
| 5 | `grep -c "sync-now" apps/linear-sync/frontend/templates/connect_status.html` | 0 | ✅ pass (5 matches) | <1s |
| 6 | `grep -c "sync-stats" apps/linear-sync/frontend/templates/connect_status.html` | 0 | ✅ pass (1 match) | <1s |
| 7 | `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py tests/test_sync_engine.py -v` | 0 | ✅ pass (89 passed) | 2s |
| 8 | `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py tests/test_push_sync.py -v` | 0 | ✅ pass (150 passed) | 2.5s |
| 9 | `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "error or unknown or missing"` | 0 | ✅ pass (6 passed) | <1s |
| 10 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/field_mapper.py').read())"` | 0 | ✅ pass | <1s |
| 11 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/sync_engine.py').read())"` | 0 | ✅ pass | <1s |
| 12 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/linear_client.py').read())"` | 0 | ✅ pass | <1s |

## Diagnostics

- **Settings page state:** All sync configuration is visible on the settings page — team selection, direction, interval, last sync time, pull/push result counts. Inspect by loading `/_fragments/connect`.
- **State keys:** Read `sync_teams`, `sync_direction`, `poll_interval`, `last_sync_at`, `last_pull_result`, `last_push_result` via StateClient to see current sync configuration and last run results.
- **Manual sync errors:** Caught per-engine and stored in `last_pull_result`/`last_push_result` state keys with `status: "error"`. Visible in the sync stats section.
- **Task scheduling:** `push-changes` task runs on 15m interval alongside `poll-tasks`. Both visible in the admin detail page's Task History section.

## Deviations

- Updated `connect_api_key` success path to pass all sync state variables to the template (not in plan but necessary for consistent rendering after initial connect).
- Added `_render_connect_status()` shared helper (not explicitly in plan steps but implied by the need for consistent re-renders across 4 different routes).

## Known Issues

None.

## Files Created/Modified

- `apps/linear-sync/manifest.yaml` — added `push-changes` task with 15m interval and retry policy
- `apps/linear-sync/app.py` — added push_changes handler, 3 settings POST routes, _render_connect_status helper, updated connect_fragment and connect_api_key to pass sync state
- `apps/linear-sync/frontend/templates/connect_status.html` — rewritten as full sync control panel with team checkboxes, direction radios, interval select, Sync Now button, sync stats
- `apps/linear-sync/frontend/static/styles.css` — added styles for team checkboxes, sync config form, sync now section, sync stats card
- `.gsd/milestones/M016/slices/S03/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
