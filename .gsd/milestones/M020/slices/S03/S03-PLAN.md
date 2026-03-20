# S03: Push Sync + Settings UI

**Goal:** Route-handler layer for Outlook Calendar app.py is verified by unit tests covering template context assembly, sync dispatch (bidirectional and pull-only), push-changes task handler, and sync-config persistence.
**Demo:** ~15 new route-handler unit tests pass alongside the 177 existing Outlook tests, proving the app.py wiring works correctly.

## Must-Haves

- `TestRenderConnectStatus` class (~5 tests) verifying `_render_connect_status` passes sync_direction, poll_interval, last_pull_result, last_push_result, and defaults to template context
- `TestSyncNowBidirectional` class (~3 tests) verifying sync_now calls push_sync after pull_sync when direction is bidirectional, sets last_sync_at, and isolates push errors
- `TestSyncNowPullOnly` class (~2 tests) verifying sync_now does NOT call push_sync when direction is pull-only or unset
- `TestPushChangesHandler` class (~2 tests) verifying the push-changes task handler calls push_sync and handles errors
- `TestSyncConfigRoute` class (~3 tests) verifying save_sync_config persists direction and interval and re-renders connect_status

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -v --tb=short` — all tests pass (60 existing + ~15 new ≈ 75)
- `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short` — full Outlook suite (~192 tests) passes
- At least one test verifies error isolation (push failure doesn't crash sync_now)
- At least one test verifies diagnostic surface (last_push_result state key stores error detail)

## Observability / Diagnostics

- Runtime signals: `last_push_result` state key stores structured JSON with status/pushed/skipped/errors/timestamp; route handlers log sync config saves and manual sync triggers via `outlook_calendar.app` logger
- Inspection surfaces: Tests verify state keys are set after sync_now and push_changes — the same keys that production monitoring reads
- Failure visibility: `test_push_error_isolated` and `test_error_returns_error_dict` prove that failures produce parseable error dicts with status="error" and message detail
- Redaction constraints: None — mock data only, no real tokens

## Integration Closure

- Upstream surfaces consumed: `apps/outlook-calendar/app.py` (all route handlers), `apps/outlook-calendar/services/sync_engine.py` (pull_sync, push_sync), `apps/outlook-calendar/services/auth.py` (get_connection_status), `apps/outlook-calendar/services/outlook_client.py` (OutlookClient)
- New wiring introduced in this slice: None — tests only, no production code changes
- What remains before the milestone is truly usable end-to-end: S04 (E2E tests + user guide)

## Tasks

- [x] **T01: Write route-handler unit tests for Outlook app.py** `est:30m`
  - Why: The sync engine, field mapper, and person matcher have 177 tests, but the app.py route-handler layer (template context assembly, sync dispatch, error isolation, config persistence) has zero tests. This follows the M017 GitHub Sync pattern where route-handler tests caught wiring bugs separately from service-layer tests.
  - Files: `backend/tests/test_outlook_sync_engine.py`
  - Do: Add `_RenderableAppContext`, `_MockRequest`, `_MockFormData`, `_load_app_module()`, and 5 test classes at the bottom of the existing test file. Clone the GitHub Sync test scaffolding pattern, adapting for Outlook's `ctx.state`-only approach (no `ctx.settings`), `microsoft_email`/`auth_method` state keys, and OutlookClient monkey-patching for `_render_connect_status`. The `_load_app_module` must stub `sempkm_app_sdk`, `starlette`, and wire `services.sync_engine`/`services.outlook_client`/`services.auth` module names.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -v --tb=short` — ~75 tests pass (60 existing + 15 new)
  - Done when: All 5 test classes pass and cover the 5 must-haves above

## Files Likely Touched

- `backend/tests/test_outlook_sync_engine.py`
