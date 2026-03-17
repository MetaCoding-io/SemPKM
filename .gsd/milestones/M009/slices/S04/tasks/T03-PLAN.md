---
estimated_steps: 6
estimated_files: 2
---

# T03: Unit tests and fixture fix

**Slice:** S04 — Frontend Level 1 — Standalone Pages & Sidebar
**Milestone:** M009

## Description

Fix the test SDK app fixture manifest to use the correct `ui.pages` schema (instead of the wrong `frontend.pages`), and create comprehensive unit tests for both browser app endpoints.

## Steps

1. Fix `backend/tests/fixtures/test_sdk_app/manifest.yaml`. Replace the current `frontend.pages` block with proper `ui.pages` entries using `AppPage` fields. The manifest should have:
   - Existing fields preserved: `appId`, `name`, `version`, `description`, `author`, `dependencies`, `backend`, `permissions`, `tasks`
   - `frontend` section with: `staticDir: "frontend/static"`, `css: ["styles.css"]`, `js: ["app.js"]` (to test CSS/JS inclusion)
   - `ui` section with `pages` list containing one page:
     ```yaml
     ui:
       pages:
         - id: "main"
           path: "/main"
           label: "Main Page"
           icon: "layout"
           nav: "apps"
           fragment: "main"
     ```
   - Remove the old `frontend.pages` block entirely

2. Verify the fixed manifest parses correctly: `cd backend && python3 -c "import yaml; from app.apps.manifest import AppManifestSchema; data = yaml.safe_load(open('tests/fixtures/test_sdk_app/manifest.yaml')); m = AppManifestSchema(**data); print(f'Pages: {len(m.ui.pages)}, CSS: {m.frontend.css}, JS: {m.frontend.js}')"` — should print `Pages: 1, CSS: ['styles.css'], JS: ['app.js']`.

3. Create `backend/tests/test_app_browser.py` following the `test_app_admin.py` pattern:
   - Use `FastAPI` + `TestClient` + `Jinja2Blocks` pointed at real template directory
   - Mock `AppRegistry` and `AppManager` on `app.state`
   - Helper `_make_manifest()` that builds an `AppManifestSchema` with configurable `ui.pages` and `frontend.css`/`frontend.js`
   - No auth needed — browser endpoints don't require login (they're workspace fragments)

4. Write these test functions in `test_app_browser.py`:

   **Explorer endpoint tests:**
   - `test_explorer_empty_registry` — no apps registered → response contains "No apps installed"
   - `test_explorer_running_app_with_pages` — one running app with a page (nav="apps") → page label appears in response
   - `test_explorer_excludes_stopped_apps` — app registered but status="stopped" → no pages in response
   - `test_explorer_excludes_non_nav_pages` — running app with page where nav=None → no pages in response
   - `test_explorer_multiple_apps` — two running apps each with pages → both apps' pages appear
   - `test_explorer_mixed_status` — one running + one stopped → only running app's pages appear

   **Page endpoint tests:**
   - `test_page_unknown_app` — unknown app_id → 404 with "not found" in detail
   - `test_page_unknown_page` — valid app but invalid page_id → 404 with "not found" in detail
   - `test_page_renders_fragment_url` — valid app + valid page → response contains `/app/{app_id}/_fragments/{fragment}`
   - `test_page_includes_css` — manifest has `frontend.css: ["styles.css"]` → response contains `/app-static/{app_id}/styles.css`
   - `test_page_includes_js` — manifest has `frontend.js: ["app.js"]` → response contains `/app-static/{app_id}/app.js`

   The mock setup pattern for each test:
   - `app.state.app_registry` = mock with `list_apps()` returning app IDs and `get_manifest()` returning manifests
   - `app.state.app_manager` = `AsyncMock` with `get_status()` returning status dicts

5. Run: `cd backend && python -m pytest tests/test_app_browser.py -v` — all 11 tests pass.

6. Run full suite: `cd backend && python -m pytest tests/ -v --timeout=30` — no regressions. Pay attention to any test that imports from the fixture manifest — they should still pass with the corrected schema.

## Must-Haves

- [ ] Fixture manifest uses `ui.pages` (not `frontend.pages`) with valid AppPage fields
- [ ] Fixture manifest includes `frontend.css` and `frontend.js` for CSS/JS inclusion testing
- [ ] Explorer tests cover: empty, running with pages, stopped excluded, non-nav excluded, multiple apps, mixed status
- [ ] Page tests cover: unknown app 404, unknown page 404, correct fragment URL, CSS includes, JS includes
- [ ] All existing tests still pass (no regressions from fixture change)

## Verification

- `cd backend && python -m pytest tests/test_app_browser.py -v` — all pass
- `cd backend && python -m pytest tests/ -v --timeout=30` — no regressions
- `python3 -c "import yaml; from app.apps.manifest import AppManifestSchema; AppManifestSchema(**yaml.safe_load(open('backend/tests/fixtures/test_sdk_app/manifest.yaml')))"` — no ValidationError

## Inputs

- `backend/app/browser/apps.py` — the endpoints being tested (created in T01)
- `backend/app/templates/browser/apps_explorer.html` — template rendered by explorer endpoint (created in T01)
- `backend/app/templates/browser/app_page.html` — template rendered by page endpoint (created in T01)
- `backend/tests/test_app_admin.py` — test pattern reference (FastAPI + TestClient + Jinja2Blocks + mock app.state)
- `backend/tests/fixtures/test_sdk_app/manifest.yaml` — current fixture with incorrect `frontend.pages` structure
- `backend/app/apps/manifest.py` — `AppPage` model fields: id, path, label, icon, nav (default "apps"), fragment

## Observability Impact

- **Test coverage signals:** `pytest tests/test_app_browser.py -v` validates both browser app endpoints — explorer filtering logic (status, nav) and page rendering (fragment URL, CSS/JS inclusion). Failures pinpoint regressions in `app.browser.apps` endpoint behavior.
- **Fixture correctness:** The fixed `test_sdk_app/manifest.yaml` now parses through `AppManifestSchema` validation — any future schema changes that break the fixture will surface as `ValidationError` in `test_sdk_integration.py`.

## Expected Output

- `backend/tests/fixtures/test_sdk_app/manifest.yaml` — fixed to use `ui.pages` with valid AppPage fields
- `backend/tests/test_app_browser.py` — new test file with 11 unit tests covering both endpoints
