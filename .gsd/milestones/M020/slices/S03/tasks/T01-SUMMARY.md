---
id: T01
parent: S03
milestone: M020
provides:
  - 15 route-handler unit tests for Outlook Calendar app.py wiring layer
key_files:
  - backend/tests/test_outlook_sync_engine.py
key_decisions:
  - Manual monkey-patching of _sync_engine.pull_sync/push_sync instead of unittest.mock.patch.object — the late `from services.sync_engine import pull_sync` inside app.py route handlers resolves from sys.modules which points to _sync_engine, so direct attribute replacement works and is restored in try/finally blocks
  - Named route-test helper `_make_route_connected_state` to avoid collision with existing `_make_connected_state` used by sync engine tests
patterns_established:
  - Outlook route tests use `_patch_make_client()` context manager to monkey-patch `_app_module._make_client_with_creds` — this avoids constructing a real OutlookClient during `_render_connect_status` calls
observability_surfaces:
  - test_push_error_isolated verifies last_push_result state key stores error dict with status="error" and message detail
  - test_error_returns_error_dict verifies push_changes task returns parseable error dict
  - test_calls_push_sync verifies last_push_result state key written after successful push
duration: 12m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Write route-handler unit tests for Outlook app.py

**Added 15 route-handler unit tests for Outlook Calendar app.py covering template context assembly, sync dispatch (bidirectional/pull-only), push-changes task handler, error isolation, and sync-config persistence.**

## What Happened

Appended ~250 lines to `backend/tests/test_outlook_sync_engine.py` following the M017 GitHub Sync route-test pattern, adapted for Outlook's `ctx.state`-only approach (no `ctx.settings`).

Scaffolding added:
- `_MockRequest` / `_MockFormData` — minimal Starlette request stubs
- `_load_app_module()` — loads `apps/outlook-calendar/app.py` with stubbed `sempkm_app_sdk`, `starlette.requests`, `starlette.responses` (including `RedirectResponse`), and wires `services.sync_engine`, `services.outlook_client`, `services.auth` into `sys.modules`
- `_RenderableAppContext(MockAppContext)` — adds `render_template` support for route tests
- `_make_route_connected_state()` — builds auth state dict for route tests (named to avoid collision with existing `_make_connected_state`)
- `_MockCalendarClient` + `_patch_make_client()` — monkey-patches `_make_client_with_creds` to avoid real OutlookClient construction

Five test classes:
1. `TestRenderConnectStatus` (5 tests) — sync_direction, poll_interval, last_push_result, defaults, last_pull_result
2. `TestSyncNowBidirectional` (3 tests) — push dispatch, last_sync_at, push error isolation
3. `TestSyncNowPullOnly` (2 tests) — pull-only and no-direction-set skip push
4. `TestPushChangesHandler` (2 tests) — success path and error path
5. `TestSyncConfigRoute` (3 tests) — save, defaults, and re-render

## Verification

- `pytest tests/test_outlook_sync_engine.py -v --tb=short` — 75 passed (60 existing + 15 new)
- `pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short` — 192 passed, 1 skipped
- `test_push_error_isolated` confirms push failure writes `status="error"` to `last_push_result` state key and doesn't block `last_sync_at` — proves diagnostic surface
- `test_error_returns_error_dict` confirms push_changes returns parseable error dict with message detail

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -v --tb=short` | 0 | ✅ pass (75 passed) | 0.36s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short` | 0 | ✅ pass (192 passed, 1 skipped) | 0.38s |

## Diagnostics

- Run `pytest tests/test_outlook_sync_engine.py -k "TestRenderConnect or TestSyncNow or TestPushChanges or TestSyncConfig" -v` to exercise only route-handler tests
- The `_rendered` list on `_RenderableAppContext` captures all template render calls — inspect `ctx._rendered[-1]` for template name and kwargs in any test
- Push error isolation is verified by checking `last_push_result` state key contains `status="error"` and `message` with exception detail

## Deviations

- Used manual try/finally monkey-patching of `_sync_engine.pull_sync`/`push_sync` instead of `unittest.mock.patch.object` — the app.py late imports resolve from `sys.modules["services.sync_engine"]` which is `_sync_engine`, so direct attribute replacement works cleanly and avoids import-time issues with the mock context manager
- Added `RedirectResponse` stub to starlette.responses (plan didn't mention it but app.py imports it at module level)

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_outlook_sync_engine.py` — Added 15 route-handler tests + scaffolding (~250 lines appended)
- `.gsd/milestones/M020/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
