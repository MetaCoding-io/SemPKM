# S03: Push Sync + Settings UI — UAT

**Milestone:** M020
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This slice is test-only — no production code changes, no UI changes, no Docker stack needed. All verification is through pytest execution.

## Preconditions

- Working directory is the M018 worktree at `.gsd/worktrees/M018/`
- Python virtual environment exists at `backend/.venv/`
- No Docker stack required — all tests are pure-function unit tests with mocked dependencies

## Smoke Test

Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -v --tb=short`
Expected: 75 tests pass (60 existing + 15 new route-handler tests) in <1s

## Test Cases

### 1. Route-handler tests pass alongside existing sync engine tests

1. `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -v --tb=short`
2. **Expected:** 75 passed, 0 failed, 0 errors. The 15 new tests (TestRenderConnectStatus, TestSyncNowBidirectional, TestSyncNowPullOnly, TestPushChangesHandler, TestSyncConfigRoute) pass alongside the 60 existing tests.

### 2. Full Outlook test suite passes with no regressions

1. `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short`
2. **Expected:** 192 passed, 1 skipped (markdownify optional dependency), 0 failed.

### 3. Template context assembly passes correct state to connect_status

1. `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "TestRenderConnectStatus" -v`
2. **Expected:** 5 tests pass — sync_direction, poll_interval, last_push_result, defaults, and last_pull_result all verified in template kwargs.

### 4. Bidirectional sync dispatches push after pull

1. `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "TestSyncNowBidirectional" -v`
2. **Expected:** 3 tests pass — push_sync called when direction=bidirectional, last_sync_at updated after both, push error isolated (doesn't crash sync_now).

### 5. Pull-only mode skips push

1. `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "TestSyncNowPullOnly" -v`
2. **Expected:** 2 tests pass — push_sync NOT called when direction=pull-only or when no direction is set.

### 6. Push-changes task handler works and reports errors

1. `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "TestPushChangesHandler" -v`
2. **Expected:** 2 tests pass — push_changes calls push_sync and returns structured error dict on failure.

### 7. Sync config route persists settings

1. `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "TestSyncConfigRoute" -v`
2. **Expected:** 3 tests pass — save_sync_config stores direction and interval, defaults on missing form data, returns HTML response.

## Edge Cases

### Push error isolation

1. `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "test_push_error_isolated" -v`
2. **Expected:** Test passes — push_sync raising an exception writes `status="error"` to `last_push_result` state key but does NOT prevent `last_sync_at` from being updated (pull succeeded).

### Error dict structure

1. `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "test_error_returns_error_dict" -v`
2. **Expected:** Test passes — push_changes returns dict with `status="error"` and `message` containing exception detail.

## Failure Signals

- Any test failure in the 15 new route-handler tests indicates broken app.py wiring
- Failures in the 60 existing sync engine tests would indicate the new scaffolding code polluted test isolation
- Import errors in `_load_app_module()` would indicate app.py added new top-level imports not covered by mocks

## Requirements Proved By This UAT

- None directly — this UAT proves the test infrastructure works. The route-handler behaviors tested here support the broader M020 milestone DoD (Settings UI functional, RSVP push-back changes Outlook responseStatus).

## Not Proven By This UAT

- No live runtime verification — all tests use mocked dependencies
- No Docker stack or browser UI interaction
- No real Microsoft Graph API calls
- Template rendering correctness (only template kwargs are verified, not rendered HTML)

## Notes for Tester

- The 1 skipped test (`test_html_body_with_markdownify`) is expected — it requires the optional `markdownify` package
- Route-handler tests are at the bottom of `test_outlook_sync_engine.py` — search for `TestRenderConnectStatus` to find the start of S03 additions
- The `_load_app_module()` helper is reusable for future Outlook app.py test additions
