# S05: App Catalog Pages

**Goal:** Browsable app catalog accessible from the workspace, showing all available apps with detail pages and install/uninstall actions.
**Demo:** User clicks "App Catalog" in APPS explorer section, sees a card grid of all 10 non-test apps (installed and available). Clicking an app card navigates to a detail page showing description, version, author, permissions, model dependencies, and install/uninstall button. Install/uninstall actions re-render the detail page with updated status.

## Must-Haves

- Catalog list page showing all apps from `apps/` directory (excluding `test-app`) with name, description, icon, and status badge (installed/available/running)
- Detail page for each app showing full manifest info: description, version, author, license, permissions, model dependencies, settings, background tasks
- Install button on detail page for uninstalled apps (owner-only, calls `app_manager.install()`)
- Uninstall button on detail page for installed apps (owner-only, calls `app_manager.uninstall()`)
- "App Catalog" entry in the APPS explorer section that opens a dockview special-panel tab
- Catalog router mounted in `browser/router.py` BEFORE `objects_router` (catch-all concern)
- htmx navigation within the catalog tab (list → detail → back, install/uninstall re-render)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_catalog.py -v` — unit tests for catalog router endpoints (list, detail, install routing, uninstall routing)
- `rg -c "catalog_router" backend/app/browser/router.py` returns 2 (import + include)
- `rg -c "openCatalogTab" frontend/static/js/workspace.js` returns >= 2 (function + window exposure)
- `rg -c "catalog" frontend/static/js/workspace-layout.js` returns >= 1 (specialType routing)

## Tasks

- [x] **T01: Backend catalog router, templates, and unit tests** `est:2h`
  - Why: The entire backend for the app catalog — router with list/detail/install/uninstall endpoints, Jinja2 templates for the card grid and detail page, and unit tests proving the endpoints work.
  - Files: `backend/app/browser/catalog.py`, `backend/app/browser/router.py`, `backend/app/templates/browser/catalog_page.html`, `backend/app/templates/browser/catalog_detail.html`, `backend/tests/test_catalog.py`
  - Do: Create `catalog.py` with 4 endpoints: `GET /catalog` scans `apps_dir` for all manifests + merges with installed app status from `app_manager`; `GET /catalog/{app_id}` renders detail page; `POST /catalog/{app_id}/install` and `POST /catalog/{app_id}/uninstall` require owner role. Templates follow `docs_page.html` card grid pattern. Mount router in `browser/router.py` before `objects_router`. Write unit tests covering list, detail, 404, and auth guards.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_catalog.py -v`
  - Done when: All unit tests pass, catalog router is mounted, templates render without errors.

- [x] **T02: Frontend integration — JS, CSS, explorer entry** `est:1h`
  - Why: Wires the catalog into the workspace UI — adds the tab-opening function, special-panel routing, explorer sidebar entry, and CSS styling for catalog cards and detail page.
  - Files: `frontend/static/js/workspace.js`, `frontend/static/js/workspace-layout.js`, `backend/app/templates/browser/workspace.html`, `frontend/static/css/workspace.css`
  - Do: Add `openCatalogTab()` function following `openDocsTab()` pattern in workspace.js. Add `specialType === 'catalog'` case in workspace-layout.js (default URL `/browser/catalog` already works). Add "App Catalog" tree-leaf entry in the APPS explorer section of workspace.html (static entry before the htmx-loaded app pages). Add `.catalog-*` CSS rules reusing `.docs-*` patterns with catalog-specific status badge styling.
  - Verify: `rg -c "openCatalogTab" frontend/static/js/workspace.js` returns >= 2 && `rg "catalog" frontend/static/js/workspace-layout.js | grep -q specialType`
  - Done when: Clicking "App Catalog" in explorer opens a dockview tab that loads the catalog page via htmx. Card clicks navigate to detail view within the same tab.

## Observability / Diagnostics

- **Catalog list endpoint** logs warnings for manifests that fail to parse (logger `app.browser.catalog`, level WARNING with exc_info)
- **Install/uninstall endpoints** log success at INFO with app_id + user email, failures at ERROR with app_id + exception message
- **Status detection** reads `app_manager.registry` for install state and `app_manager._processes` for running state — no new DB queries needed
- **Error rendering** surfaces install/uninstall failure messages in the detail template via the `error` context variable (visible to users as a red alert box)
- **No secrets** are logged or rendered — only app_id, version, and user email appear in log messages

## Files Likely Touched

- `backend/app/browser/catalog.py` (new)
- `backend/app/browser/router.py`
- `backend/app/templates/browser/catalog_page.html` (new)
- `backend/app/templates/browser/catalog_detail.html` (new)
- `backend/tests/test_catalog.py` (new)
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `backend/app/templates/browser/workspace.html`
- `frontend/static/css/workspace.css`
