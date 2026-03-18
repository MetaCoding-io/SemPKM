---
id: T03
parent: S04
milestone: M009
provides:
  - 11 unit tests covering both browser app endpoints (explorer and page)
  - Fixed test fixture manifest using correct ui.pages schema
key_files:
  - backend/tests/test_app_browser.py
  - backend/tests/fixtures/test_sdk_app/manifest.yaml
key_decisions: []
patterns_established:
  - Sync TestClient approach for browser sub-router tests (no auth needed — workspace fragments don't require login)
observability_surfaces:
  - pytest tests/test_app_browser.py -v validates explorer filtering (status, nav) and page rendering (fragment URL, CSS/JS inclusion)
duration: 10m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Unit tests and fixture fix

**Created 11 unit tests for browser app endpoints and verified fixture manifest uses correct ui.pages schema.**

## What Happened

The test fixture manifest (`manifest.yaml`) was already correctly structured with `ui.pages` from a prior session — no changes needed there. Created `backend/tests/test_app_browser.py` with 11 tests split across two classes:

**Explorer endpoint (6 tests):** empty registry shows "No apps installed", running app with `nav="apps"` pages appears, stopped apps excluded, non-nav pages excluded, multiple running apps both appear, mixed status filters correctly.

**Page endpoint (5 tests):** unknown app returns 404, unknown page returns 404, correct fragment proxy URL rendered, CSS includes present, JS includes present.

Used a simpler test setup than `test_app_admin.py` — plain `FastAPI` + `TestClient` (sync) with `MagicMock` registry and `AsyncMock` manager, since browser endpoints don't require auth. Helper functions `_make_manifest()` and `_make_page()` keep individual tests compact.

## Verification

- `cd backend && python -m pytest tests/test_app_browser.py -v` — 11/11 passed (0.29s)
- `cd backend && python -m pytest tests/ -v` — 1253/1253 passed, no regressions (39.45s)
- `python3 -c "from app.apps.manifest import AppManifestSchema; ..."` — manifest parses without error, reports Pages: 1, CSS: ['styles.css'], JS: ['app.js']
- All slice-level grep checks pass: `apps_router` count=2, `APPS` count=1, `app-page` count=1, `openAppPageTab` count=2, `ui:` present in fixture

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest tests/test_app_browser.py -v` | 0 | ✅ pass | 0.29s |
| 2 | `python -m pytest tests/ -v` | 0 | ✅ pass | 39.45s |
| 3 | `python3 -c "...AppManifestSchema(...)"` | 0 | ✅ pass | 3.7s |
| 4 | `grep -c "apps_router" backend/app/browser/router.py` → 2 | 0 | ✅ pass | <1s |
| 5 | `grep -c "APPS" backend/app/templates/browser/workspace.html` → 1 | 0 | ✅ pass | <1s |
| 6 | `grep -c "app-page" frontend/static/js/workspace-layout.js` → 1 | 0 | ✅ pass | <1s |
| 7 | `grep -c "openAppPageTab" frontend/static/js/workspace.js` → 2 | 0 | ✅ pass | <1s |
| 8 | `grep "ui:" backend/tests/fixtures/test_sdk_app/manifest.yaml` → present | 0 | ✅ pass | <1s |

## Diagnostics

- Run `cd backend && python -m pytest tests/test_app_browser.py -v` to verify browser app endpoint behavior
- Individual test names describe the exact scenario being tested (e.g. `test_explorer_excludes_stopped_apps`)
- Test failures pinpoint regressions in `app.browser.apps` endpoint behavior — explorer filtering logic or page rendering

## Deviations

None. The fixture manifest was already correctly structured from the prior session's work.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_app_browser.py` — new: 11 unit tests for explorer and page browser endpoints
- `backend/tests/fixtures/test_sdk_app/manifest.yaml` — verified correct (no changes needed)
