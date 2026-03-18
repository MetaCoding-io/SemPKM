---
id: T03
parent: S04
milestone: M009
provides:
  - 11 unit tests covering browser app explorer and page endpoints
  - Fixed test SDK app fixture manifest using correct ui.pages schema
key_files:
  - backend/tests/test_app_browser.py
  - backend/tests/fixtures/test_sdk_app/manifest.yaml
key_decisions:
  - Fixture author field changed from bare string to AppAuthor object to match schema validation
patterns_established:
  - Browser endpoint test pattern: FastAPI + TestClient + Jinja2Blocks + mock app_registry/app_manager on app.state (no auth needed for browser endpoints)
observability_surfaces:
  - pytest tests/test_app_browser.py -v validates explorer filtering logic and page rendering correctness
duration: 10m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Unit tests and fixture fix

**Fixed test_sdk_app fixture manifest to use `ui.pages` schema and created 11 unit tests covering both browser app endpoints (explorer + page content).**

## What Happened

Fixed `backend/tests/fixtures/test_sdk_app/manifest.yaml` — replaced the incorrect `frontend.pages` block (which used wrong field names: `title`, `route`) with proper `ui.pages` entries using `AppPage` fields (`id`, `path`, `label`, `icon`, `nav`, `fragment`). Added `frontend.css` and `frontend.js` arrays for CSS/JS inclusion testing. Also fixed the `author` field from a bare string to an `AppAuthor` object (`name:` key) to match schema validation.

Created `backend/tests/test_app_browser.py` with 11 tests in two groups:
- **Explorer** (6 tests): empty registry, running app with pages, stopped apps excluded, non-nav pages excluded, multiple apps, mixed status
- **Page** (5 tests): unknown app 404, unknown page 404, correct fragment URL, CSS includes, JS includes

## Verification

- `pytest tests/test_app_browser.py -v` — 11/11 pass
- `pytest tests/ -v` — 1045/1045 pass, zero regressions
- `AppManifestSchema(**yaml.safe_load(open('manifest.yaml')))` — parses without error, `Pages: 1, CSS: ['styles.css'], JS: ['app.js']`
- Slice-level checks all pass:
  - `grep -c "apps_router" backend/app/browser/router.py` → 2 ✓
  - `grep -c "APPS" backend/app/templates/browser/workspace.html` → 1 ✓
  - `grep -c "app-page" frontend/static/js/workspace-layout.js` → 1 ✓
  - `grep -c "openAppPageTab" frontend/static/js/workspace.js` → 2 ✓
  - `grep "ui:" backend/tests/fixtures/test_sdk_app/manifest.yaml` → present ✓

## Diagnostics

- Run `pytest tests/test_app_browser.py -v` to verify browser endpoint behavior
- Test helper `_make_manifest()` accepts configurable `pages`, `css`, `js` for building test scenarios
- Test helper `_make_page()` builds `AppPage` instances with sensible defaults

## Deviations

- Fixture `author` field required change from bare string `"SemPKM Tests"` to `AppAuthor` object `{name: "SemPKM Tests"}` — the schema requires a dict, not a plain string. This was an existing bug in the fixture that the old `frontend.pages` structure masked.

## Known Issues

- DeprecationWarning on `TemplateResponse(name, {"request": request})` call signature in `apps.py` — Starlette/Jinja2Blocks now expects `TemplateResponse(request, name)`. Not a blocker; existing code throughout the codebase uses the old signature.

## Files Created/Modified

- `backend/tests/test_app_browser.py` — new: 11 unit tests for explorer and page endpoints
- `backend/tests/fixtures/test_sdk_app/manifest.yaml` — fixed: ui.pages schema, frontend.css/js, author format
