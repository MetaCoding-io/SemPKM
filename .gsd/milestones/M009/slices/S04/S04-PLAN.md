# S04: Frontend Level 1 — Standalone Pages & Sidebar

**Goal:** Installed apps with page declarations appear in the workspace [Apps] sidebar section. Clicking an app page loads the app's fragment content through the platform proxy into the workspace via htmx.
**Demo:** An app with `ui.pages` entries shows up in the APPS sidebar. Clicking a page entry opens a dockview tab that loads the app's fragment via the nginx→API→AppProxy→UDS chain. App CSS/JS are included when the page is active.

## Must-Haves

- Browser sub-router at `backend/app/browser/apps.py` with explorer endpoint (list app pages) and page content endpoint (dockview tab wrapper)
- Explorer endpoint filters to installed apps with `nav: "apps"` pages and running status
- APPS section in workspace.html between WORKFLOWS and shared_nav_section, htmx lazy-loaded
- `openAppPageTab()` JS function following `openDashboardTab()` pattern
- `specialType: 'app-page'` handling in workspace-layout.js special-panel factory
- `app_page.html` template with htmx `hx-get` pointing to proxy URL + app CSS/JS includes
- Test fixture manifest corrected from `frontend.pages` to `ui.pages` with proper AppPage fields
- Unit tests for both browser endpoints

## Proof Level

- This slice proves: integration (htmx fragment loading chain wired through proxy)
- Real runtime required: no (unit tests with mock registry/manager; Docker integration in S07)
- Human/UAT required: no (S07 exercises in live Docker stack)

## Verification

- `cd backend && python -m pytest tests/test_app_browser.py -v` — all tests pass
- `cd backend && python -m pytest tests/ -v --timeout=30` — no regressions
- `grep -c "apps_router" backend/app/browser/router.py` → 2 (import + include)
- `grep -c "APPS" backend/app/templates/browser/workspace.html` → at least 1
- `grep -c "app-page" frontend/static/js/workspace-layout.js` → at least 1
- `grep -c "openAppPageTab" frontend/static/js/workspace.js` → at least 2 (definition + window export)
- `grep "ui:" backend/tests/fixtures/test_sdk_app/manifest.yaml` → present (fixture fixed)
- Diagnostic: `curl -s /browser/apps/nonexistent/page/foo` → 404 with descriptive detail (failure-path check)

## Observability / Diagnostics

- Runtime signals: Logger `app.browser.apps` logs page lookup misses at WARNING (unknown app/page)
- Inspection surfaces: `/browser/apps/explorer` returns HTML list of app pages (visible in sidebar)
- Failure visibility: 404 response for unknown app_id or page_id with descriptive detail
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `AppRegistry` (manifest lookup), `AppManager.get_status()` (running filter), `AppProxy` (fragment forwarding via existing nginx→API→UDS chain from S02/S03)
- New wiring introduced: `apps_router` in `browser/router.py`, APPS section in workspace.html, `openAppPageTab()` + `specialType: 'app-page'` in workspace JS
- What remains before the milestone is truly usable end-to-end: S05 (permissions/scheduler), S06 (L2+3 contributions), S07 (integration proof with real app in Docker)

## Tasks

- [x] **T01: Browser sub-router, templates, and workspace wiring** `est:45m`
  - Why: Creates the full backend endpoint layer and workspace HTML — the APPS sidebar section and dockview page content endpoint. This is the server-side half of the slice.
  - Files: `backend/app/browser/apps.py`, `backend/app/browser/router.py`, `backend/app/templates/browser/apps_explorer.html`, `backend/app/templates/browser/app_page.html`, `backend/app/templates/browser/workspace.html`
  - Do: (1) Create `backend/app/browser/apps.py` with `apps_router` (no prefix) containing `GET /apps/explorer` (queries `request.app.state.app_registry.list_apps()`, filters to running apps via `request.app.state.app_manager.get_status()`, collects pages with `nav == "apps"` from manifests, renders `apps_explorer.html`) and `GET /apps/{app_id}/page/{page_id}` (looks up manifest, finds matching page, renders `app_page.html` with htmx div pointing to `/app/{app_id}/_fragments/{page.fragment}` plus CSS/JS from `manifest.frontend`). (2) Create `apps_explorer.html` listing pages with `onclick="openAppPageTab(…)"` and Lucide icons, following `dashboard_explorer.html` pattern. (3) Create `app_page.html` with htmx `hx-get` to proxy URL for fragment content, plus `<link>` tags for each `manifest.frontend.css` and `<script>` tags for each `manifest.frontend.js` using `/app-static/{appId}/` paths. (4) Register `apps_router` in `browser/router.py` **before** `objects_router` (D052/D058/D136 pattern). (5) Add APPS section to `workspace.html` between WORKFLOWS and shared_nav_section with `hx-get="/browser/apps/explorer"` and `hx-trigger="load, appsRefreshed from:body"`.
  - Verify: `python3 -c "import ast; ast.parse(open('backend/app/browser/apps.py').read())"` — syntax OK; `grep -c "apps_router" backend/app/browser/router.py` → 2
  - Done when: Both endpoints exist, templates render, APPS section is in workspace.html, router include order is correct

- [x] **T02: Workspace JS — openAppPageTab + special-panel handler** `est:20m`
  - Why: Creates the client-side JS that opens app pages as dockview tabs. Without this, clicking sidebar entries does nothing.
  - Files: `frontend/static/js/workspace.js`, `frontend/static/js/workspace-layout.js`
  - Do: (1) Add `openAppPageTab(appId, pageId, label)` to `workspace.js` after `openDashboardTab()`. Pattern: tab key `app-page:{appId}:{pageId}`, check for existing panel, create `special-panel` with `params: { specialType: 'app-page', appId: appId, pageId: pageId }`. Export as `window.openAppPageTab = openAppPageTab`. (2) Add `specialType === 'app-page'` case in `workspace-layout.js` special-panel factory: `url = '/browser/apps/' + params.params.appId + '/page/' + params.params.pageId`.
  - Verify: `grep -c "openAppPageTab" frontend/static/js/workspace.js` → at least 2; `grep -c "app-page" frontend/static/js/workspace-layout.js` → at least 1
  - Done when: `openAppPageTab()` is defined and exported, special-panel factory routes `app-page` type to the correct browser endpoint URL

- [x] **T03: Unit tests and fixture fix** `est:30m`
  - Why: Proves the browser endpoints work correctly and fixes the test fixture manifest so page data tests are valid.
  - Files: `backend/tests/test_app_browser.py`, `backend/tests/fixtures/test_sdk_app/manifest.yaml`
  - Do: (1) Fix `manifest.yaml` — replace `frontend.pages` block with `ui.pages` using correct AppPage fields (`id`, `path`, `label`, `icon`, `nav`, `fragment`). Keep existing `frontend` section for `staticDir`/`css`/`js`. (2) Create `test_app_browser.py` following `test_app_admin.py` pattern — mock AppRegistry and AppManager on `app.state`, use `Jinja2Blocks` with real template directory. Tests: explorer returns empty when no apps; explorer shows pages from running app with `nav: "apps"`; explorer excludes stopped apps; explorer excludes pages with `nav: null`; page endpoint returns 404 for unknown app; page endpoint returns 404 for unknown page; page endpoint renders template with correct proxy URL and CSS/JS includes; explorer returns pages from multiple running apps.
  - Verify: `cd backend && python -m pytest tests/test_app_browser.py -v` — all pass; `cd backend && python -m pytest tests/ -v --timeout=30` — no regressions
  - Done when: All test cases pass, fixture validates against AppManifestSchema, no existing tests broken

## Files Likely Touched

- `backend/app/browser/apps.py` (new)
- `backend/app/browser/router.py`
- `backend/app/templates/browser/apps_explorer.html` (new)
- `backend/app/templates/browser/app_page.html` (new)
- `backend/app/templates/browser/workspace.html`
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `backend/tests/test_app_browser.py` (new)
- `backend/tests/fixtures/test_sdk_app/manifest.yaml`
