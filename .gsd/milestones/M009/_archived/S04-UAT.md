# S04: Frontend Level 1 — Standalone Pages & Sidebar — UAT

**Milestone:** M009
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S04 is a wiring slice — backend endpoints, templates, and JS glue. Unit tests prove endpoint behavior with mocked registry/manager. Live runtime proof (real app serving fragments through the full proxy chain) is the job of S07. The artifacts here are fully testable without Docker.

## Preconditions

- Backend virtualenv available at `backend/.venv/`
- No running services required (tests use FastAPI TestClient with mocked app state)

## Smoke Test

```bash
cd backend && .venv/bin/pytest tests/test_app_browser.py -v
```
All 11 tests pass in <1s. This confirms both endpoints work with correct filtering, routing, and template rendering.

## Test Cases

### 1. Explorer returns pages from running apps

1. Run `cd backend && .venv/bin/pytest tests/test_app_browser.py::TestExplorer::test_explorer_running_app_with_pages -v`
2. **Expected:** Test passes — response contains the app page label and correct `openAppPageTab()` onclick with app_id, page_id, and label arguments.

### 2. Explorer excludes stopped apps

1. Run `cd backend && .venv/bin/pytest tests/test_app_browser.py::TestExplorer::test_explorer_excludes_stopped_apps -v`
2. **Expected:** Test passes — response body is empty (no tree-leaf items rendered) when the only installed app has status "stopped".

### 3. Explorer excludes pages without nav="apps"

1. Run `cd backend && .venv/bin/pytest tests/test_app_browser.py::TestExplorer::test_explorer_excludes_non_nav_pages -v`
2. **Expected:** Test passes — pages with `nav: null` do not appear in the explorer HTML output.

### 4. Page endpoint renders correct fragment URL

1. Run `cd backend && .venv/bin/pytest tests/test_app_browser.py::TestPage::test_page_renders_fragment_url -v`
2. **Expected:** Test passes — response body contains `hx-get="/app/{appId}/_fragments/{fragment}"` pointing to the correct proxy URL for the app's fragment endpoint.

### 5. Page endpoint includes CSS and JS

1. Run `cd backend && .venv/bin/pytest tests/test_app_browser.py::TestPage::test_page_includes_css -v`
2. Run `cd backend && .venv/bin/pytest tests/test_app_browser.py::TestPage::test_page_includes_js -v`
3. **Expected:** Both pass — response contains `<link>` tag with `/app-static/{appId}/{css}` href and `<script>` tag with `/app-static/{appId}/{js}` src.

### 6. Page endpoint returns 404 for unknown app

1. Run `cd backend && .venv/bin/pytest tests/test_app_browser.py::TestPage::test_page_unknown_app -v`
2. **Expected:** Test passes — response is HTTP 404 with detail "App {id} not found".

### 7. Page endpoint returns 404 for unknown page

1. Run `cd backend && .venv/bin/pytest tests/test_app_browser.py::TestPage::test_page_unknown_page -v`
2. **Expected:** Test passes — response is HTTP 404 with detail "Page {id} not found in app {appId}".

### 8. Router registration order is correct

1. Run `grep -n "include_router" backend/app/browser/router.py`
2. **Expected:** `apps_router` appears on a line number BEFORE `objects_router`. This prevents the objects catch-all from consuming `/apps/*` paths.

### 9. APPS section present in workspace.html

1. Run `grep -A3 "APPS" backend/app/templates/browser/workspace.html`
2. **Expected:** An APPS sidebar section with `hx-get="/browser/apps/explorer"` and `hx-trigger="load, appsRefreshed from:body"`.

### 10. openAppPageTab function exists and is exported

1. Run `grep -c "openAppPageTab" frontend/static/js/workspace.js`
2. **Expected:** At least 2 matches (function definition + `window.openAppPageTab` export).

### 11. special-panel factory routes app-page type

1. Run `grep "app-page" frontend/static/js/workspace-layout.js`
2. **Expected:** A case matching `specialType === 'app-page'` that constructs URL `/browser/apps/{appId}/page/{pageId}`.

### 12. Test fixture validates against schema

1. Run `cd backend && .venv/bin/python3 -c "import yaml; from app.apps.manifest import AppManifestSchema; m = AppManifestSchema(**yaml.safe_load(open('tests/fixtures/test_sdk_app/manifest.yaml'))); print(f'Pages: {len(m.ui.pages)}, CSS: {m.frontend.css}, JS: {m.frontend.js}')"`
2. **Expected:** Output shows `Pages: 1` (or more), CSS and JS arrays populated, no validation error.

### 13. Full test suite — no regressions

1. Run `cd backend && .venv/bin/pytest tests/ -v`
2. **Expected:** 1045 tests pass, zero failures.

## Edge Cases

### Explorer with multiple apps, mixed running/stopped status

1. Run `cd backend && .venv/bin/pytest tests/test_app_browser.py::TestExplorer::test_explorer_mixed_status -v`
2. **Expected:** Only pages from running apps appear. Stopped apps are completely excluded from the explorer HTML.

### Explorer with zero installed apps

1. Run `cd backend && .venv/bin/pytest tests/test_app_browser.py::TestExplorer::test_explorer_empty_registry -v`
2. **Expected:** Response is empty HTML — no tree-leaf items, no errors.

## Failure Signals

- `pytest tests/test_app_browser.py` has any failure — endpoint logic broken
- `grep -c "apps_router" backend/app/browser/router.py` returns anything other than 2 — router wiring broken
- `grep -c "openAppPageTab" frontend/static/js/workspace.js` returns less than 2 — JS function missing or not exported
- `grep -c "app-page" frontend/static/js/workspace-layout.js` returns 0 — special-panel factory missing app-page case
- `AppManifestSchema(**yaml.safe_load(open('manifest.yaml')))` raises ValidationError — fixture schema broken
- `objects_router` appears before `apps_router` in router.py `include_router` calls — apps URLs would be consumed by catch-all

## Requirements Proved By This UAT

- APP-07 (Frontend integration Level 1 — standalone pages) — partially proved. All backend endpoints, templates, sidebar section, and JS wiring are verified through unit tests and artifact inspection. Full end-to-end proof (real app fragment loading through nginx→API→AppProxy→UDS chain) requires S07.

## Not Proven By This UAT

- Live fragment loading through the full proxy chain (nginx → API → AppProxy → UDS → SDK app) — requires Docker stack with a running app (S07)
- Visual appearance of the APPS sidebar section in the live workspace — requires browser verification (S07)
- App CSS/JS actually loading and executing in the browser — requires live runtime (S07)
- Interaction between app page tabs and workspace features (contextual panels, layout persistence) — requires live runtime (S07)

## Notes for Tester

- DeprecationWarning on `TemplateResponse` call signature is expected — matches existing codebase pattern, not a bug.
- The `InsecureKeyLengthWarning` warnings in the test output are from `test_app_tokens.py` (S02 tests), not from S04. They use a 30-byte test secret which is below PyJWT's recommended 32-byte minimum. Not relevant to S04 verification.
- To manually test the sidebar in a live stack, ensure at least one app is installed and running. The explorer shows nothing until an app with `nav: "apps"` pages is running.
