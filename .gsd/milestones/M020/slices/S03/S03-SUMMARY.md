---
id: S03
parent: M020
milestone: M020
provides:
  - 15 route-handler unit tests proving app.py wiring layer (template context, sync dispatch, push handler, config persistence)
requires:
  - slice: S02
    provides: sync_engine.py (pull_sync, push_sync), field_mapper.py, person_matcher.py, outlook_client.py, auth.py — the service layer tested by these route-handler tests
affects:
  - S04
key_files:
  - backend/tests/test_outlook_sync_engine.py
key_decisions:
  - Manual monkey-patching of _sync_engine.pull_sync/push_sync via try/finally instead of unittest.mock.patch.object — app.py late imports resolve from sys.modules which points to _sync_engine, so direct attribute replacement works
patterns_established:
  - Outlook route tests use _patch_make_client() context manager to monkey-patch _app_module._make_client_with_creds, avoiding real OutlookClient construction during _render_connect_status calls
  - Named helper _make_route_connected_state avoids collision with existing _make_connected_state used by sync engine tests
observability_surfaces:
  - test_push_error_isolated verifies last_push_result state key stores error dict with status="error" and message detail
  - test_error_returns_error_dict verifies push_changes task returns parseable error dict
  - test_calls_push_sync verifies last_push_result state key written after successful push
drill_down_paths:
  - .gsd/milestones/M020/slices/S03/tasks/T01-SUMMARY.md
duration: 12m
verification_result: passed
completed_at: 2026-03-19
---

# S03: Push Sync + Settings UI

**15 route-handler unit tests prove the Outlook Calendar app.py wiring layer — template context assembly, bidirectional/pull-only sync dispatch, push-changes task handler, error isolation, and sync-config persistence.**

## What Happened

Added 15 route-handler unit tests to the existing `test_outlook_sync_engine.py` file, following the M017 GitHub Sync route-test pattern adapted for Outlook's `ctx.state`-only approach (no `ctx.settings`).

The test scaffolding includes `_MockRequest`/`_MockFormData` (Starlette stubs), `_load_app_module()` (loads app.py with stubbed SDK/Starlette/services), `_RenderableAppContext` (adds `render_template` support), `_make_route_connected_state()` (auth state dict), and `_MockCalendarClient` + `_patch_make_client()` (avoids real OutlookClient construction).

Five test classes cover the full route-handler surface:
1. **TestRenderConnectStatus** (5 tests) — verifies sync_direction, poll_interval, last_push_result, last_pull_result, and defaults all pass correctly into template context
2. **TestSyncNowBidirectional** (3 tests) — verifies push_sync runs after pull_sync when direction=bidirectional, last_sync_at updates, and push errors don't crash sync_now
3. **TestSyncNowPullOnly** (2 tests) — verifies push_sync is NOT called when direction=pull-only or unset
4. **TestPushChangesHandler** (2 tests) — verifies push_changes task handler calls push_sync and returns parseable error dicts on failure
5. **TestSyncConfigRoute** (3 tests) — verifies save_sync_config persists direction+interval and re-renders connect_status

## Verification

- `pytest tests/test_outlook_sync_engine.py -v` — 75 passed (60 existing + 15 new) in 0.32s
- `pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v` — 192 passed, 1 skipped in 0.39s
- Error isolation verified: `test_push_error_isolated` confirms push failure writes `status="error"` to `last_push_result` without blocking `last_sync_at`
- Diagnostic surface verified: `test_error_returns_error_dict` confirms push_changes returns structured error with message detail

## Requirements Advanced

- No new requirements advanced — this slice adds test coverage for already-implemented route handlers

## Requirements Validated

- No requirements moved to validated — S03 is a test-only slice verifying existing wiring

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Added `RedirectResponse` stub to starlette.responses mock — not in the plan but required because app.py imports it at module level

## Known Limitations

- Route-handler tests use manual monkey-patching rather than unittest.mock.patch.object due to late-import resolution through sys.modules — works correctly but is slightly more verbose
- The 1 skipped test in the full suite is the markdownify HTML→Markdown test (optional dependency)

## Follow-ups

- None — S04 (E2E Tests + User Guide) is the next and final slice

## Files Created/Modified

- `backend/tests/test_outlook_sync_engine.py` — Added 15 route-handler tests + scaffolding (~250 lines appended)

## Forward Intelligence

### What the next slice should know
- The full Outlook test suite is 192 tests (117 field mapper + 75 sync engine + person matcher) — all pass in <0.4s
- The route-handler test pattern (`_load_app_module` + `_RenderableAppContext` + monkey-patching) matches the M017 GitHub Sync pattern and the M016 Linear Sync pattern — use the same approach for any E2E mock server integration
- app.py imports `RedirectResponse` from starlette.responses — any module-level mock must include it

### What's fragile
- The `_load_app_module()` mock wiring is sensitive to import order — if app.py adds new top-level imports from starlette or the SDK, the mock setup needs matching stubs

### Authoritative diagnostics
- `pytest tests/test_outlook_sync_engine.py -k "TestRenderConnect or TestSyncNow or TestPushChanges or TestSyncConfig" -v` — exercises only the 15 route-handler tests added in this slice
- The `_rendered` list on `_RenderableAppContext` captures all template render calls — inspect `ctx._rendered[-1]` for debugging

### What assumptions changed
- None — the slice plan accurately predicted scope and approach
