# S03: Push Sync + Settings UI — Research

**Date:** 2026-03-19
**Status:** Complete

## Summary

S02 exceeded its scope and shipped the complete push_sync implementation (RSVP push-back with change detection, reverse field mapping, PATCH calls, loop prevention) along with all route handlers (sync-config, sync-now, push-changes task) and the full settings UI (connect_status.html with direction radios, poll interval dropdown, Sync Now button, sync stats display). All htmx URLs already use the `/app/outlook-calendar/` prefix. 177 unit tests pass, including 12 push-specific tests.

What remains for S03 is route-handler unit tests — verifying that the app.py wiring correctly reads state, calls sync functions, and passes the right template context. This follows the M017 GitHub Sync pattern where `TestRenderConnectStatus`, `TestSyncNowBidirectional`, `TestSyncNowPullOnly`, `TestPushChangesHandler`, and `TestSyncConfigRoute` (15 tests total) validated the route-handler layer separately from the sync engine.

## Recommendation

Write ~15 route-handler unit tests for the Outlook app.py following the M017 GitHub Sync test pattern. These test the _render_connect_status template context assembly, sync_now bidirectional/pull-only dispatch, push_changes task handler, and save_sync_config state persistence. No new production code is needed — everything is already implemented and functional.

## Implementation Landscape

### Key Files

- `apps/outlook-calendar/app.py` — All route handlers already implemented: `save_sync_config` (POST sync-config), `sync_now` (POST sync-now), `push_changes` (task handler), `_render_connect_status` (template context builder). No changes needed.
- `apps/outlook-calendar/frontend/templates/connect_status.html` — Full settings UI with calendar selection, direction radios, poll interval dropdown, Sync Now button, sync stats. No changes needed.
- `apps/outlook-calendar/frontend/static/styles.css` — Complete styling for all settings sections. No changes needed.
- `apps/outlook-calendar/services/sync_engine.py` — `push_sync()` fully implemented with RSVP push-back, change detection SPARQL, reverse field mapping. No changes needed.
- `backend/tests/test_outlook_sync_engine.py` — 60 existing tests including 12 push tests. Add ~15 route-handler tests here (new test classes at the bottom of the file).
- `backend/tests/test_github_sync_engine.py` (reference) — Lines 1972–2250 contain `TestRenderConnectStatus`, `TestSyncNowBidirectional`, `TestSyncNowPullOnly`, `TestPushChangesHandler`, `TestSyncConfigRoute` — the pattern to clone.

### Build Order

Single task: write route-handler unit tests for app.py. No sequencing needed — all production code exists.

1. Read `backend/tests/test_github_sync_engine.py` lines 1972+ for the `_RenderableAppContext` mock pattern, `_MockRequest`, and test class structure.
2. Adapt the GitHub mock scaffolding for Outlook (different state key names: `microsoft_email` instead of `github_username`, different module imports).
3. Write test classes: `TestRenderConnectStatus` (~5 tests), `TestSyncNowBidirectional` (~3 tests), `TestSyncNowPullOnly` (~2 tests), `TestPushChangesHandler` (~3 tests), `TestSyncConfigRoute` (~2 tests).
4. Run `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -v --tb=short` — expect ~75 tests (60 existing + 15 new).

### Verification Approach

- `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -v --tb=short` — all tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_outlook_*.py -v --tb=short` — full Outlook test suite (177 existing + ~15 new ≈ 192 tests)
- Grep-verify htmx URLs: `rg "hx-post\|hx-get" apps/outlook-calendar/frontend/templates/ | grep -v "/app/outlook-calendar/"` — must return empty

## Constraints

- Route-handler tests must import from `apps/outlook-calendar/app.py` which lives outside `backend/`. The existing `test_outlook_sync_engine.py` already solves this with `importlib` and `sys.path` manipulation — reuse that pattern.
- The `_render_connect_status` function in Outlook app.py uses `microsoft_email` (not `google_email`) and reads from an `OutlookClient` (not `GCalClient`). The mock context must match these field names.
- Outlook's connect_status template receives `calendars` with `.name` and `.isDefaultCalendar` fields (vs Google's `.summary` and `.primary`) — mock data must match.
