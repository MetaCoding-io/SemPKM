---
id: T03
parent: S03
milestone: M018
provides:
  - Settings UI with sync configuration (direction, poll interval), manual sync trigger, and sync stats display
  - sync-config and sync-now routes in app.py
  - Real poll-events task handler calling pull_sync()
  - Extended _render_connect_status() with sync state variables
key_files:
  - apps/google-calendar/app.py
  - apps/google-calendar/frontend/templates/connect_status.html
  - apps/google-calendar/frontend/static/styles.css
key_decisions:
  - "Push sync in sync-now and poll-events returns a skipped placeholder result when bidirectional — S04 scope"
patterns_established:
  - "Same sync settings UI pattern as linear-sync: direction radios, poll interval select, sync-now form, sync-stats section"
observability_surfaces:
  - "Sync Stats section in settings UI — shows last_sync_at, pull result (status/created/updated/unchanged/errors), push result"
  - "State keys: sync_direction, poll_interval, last_sync_at, last_pull_result, last_push_result — queryable via ctx.state.get()"
  - "poll-events handler logs start/completion/failure at INFO/ERROR, persists result to state, returns structured dict"
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Wire settings UI, sync routes, and poll-events task handler

**Added sync configuration UI, manual sync trigger, sync stats display, settings routes, and real poll-events task handler to google-calendar app**

## What Happened

Extended the google-calendar app in three files, following the linear-sync patterns exactly:

1. **Template** — Added three sections to `connect_status.html` between Calendar Selection and Disconnect: Sync Configuration (direction radios: pull-only/bidirectional, poll interval select: 5m/15m/30m/1h), Manual Sync (Sync Now button with htmx indicator), and Sync Stats (last sync time, last pull result with created/updated/unchanged/errors, last push result placeholder).

2. **Routes** — Added `POST /_fragments/settings/sync-config` (saves direction + interval to state, re-renders) and `POST /_fragments/sync-now` (calls real `pull_sync()`, stores result, handles bidirectional placeholder, persists timestamp, re-renders). Wired `poll-events` task handler to call `pull_sync()` with proper error handling, state persistence, and structured logging.

3. **Styles** — Added sync-config, sync-now, and sync-stats CSS sections scoped under `.gcal-sync-settings`, matching linear-sync's visual design.

4. **Extended `_render_connect_status()`** to read and pass `sync_direction`, `poll_interval`, `last_sync_at`, `last_pull_result`, `last_push_result` template variables from app state.

## Verification

- Jinja2 template syntax check: passes (no parse errors)
- All htmx URLs use `/app/google-calendar/` prefix (4 URLs verified)
- Full test suite: 1609 passed in 8.34s with zero regressions
- Slice-level test checks: 64 field mapper, 36 sync engine, 11 person matcher — all pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from jinja2 import ..."` (template syntax) | 0 | ✅ pass | 3.5s |
| 2 | `grep -n 'hx-post\|hx-get' ... connect_status.html` (URL prefix check) | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/python -m pytest -x` (full suite) | 0 | ✅ pass | 8.3s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_gcal_field_mapper.py -v` | 0 | ✅ pass | <1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_gcal_sync_engine.py -v` | 0 | ✅ pass | <1s |
| 6 | `cd backend && .venv/bin/python -m pytest tests/test_gcal_person_matcher.py -v` | 0 | ✅ pass | <1s |

## Diagnostics

- **Settings UI:** Navigate to google-calendar app settings when connected — sync config, manual sync, and stats sections visible below calendar selection.
- **State inspection:** `ctx.state.get("sync_direction")`, `ctx.state.get("poll_interval")`, `ctx.state.get("last_sync_at")`, `ctx.state.get("last_pull_result")`, `ctx.state.get("last_push_result")` — all populated after a sync run.
- **Logs:** `google_calendar.app` at INFO for manual sync trigger, config saves. `google_calendar.sync` at INFO/WARNING for pull sync details (from sync_engine).
- **Error shapes:** Manual sync errors are caught, stored as `{"status": "error", "message": "..."}` in `last_pull_result`, and visible in the Sync Stats section.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/google-calendar/app.py` — Added sync-config route, sync-now route, real poll-events handler, datetime import, extended _render_connect_status()
- `apps/google-calendar/frontend/templates/connect_status.html` — Added Sync Configuration, Manual Sync, and Sync Stats sections
- `apps/google-calendar/frontend/static/styles.css` — Added sync-config, sync-now, sync-stats, and disconnect CSS sections
- `.gsd/milestones/M018/slices/S03/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
