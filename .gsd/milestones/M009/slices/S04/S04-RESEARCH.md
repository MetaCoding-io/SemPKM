# S04: Frontend Level 1 — Standalone Pages & Sidebar — Research

**Date:** 2026-03-16
**Researcher:** GSD auto-mode

## Summary

S04 is a straightforward application of established workspace patterns to add an APPS sidebar section and dockview tab loading for app pages. The workspace already has 5 sidebar explorer sections (FAVORITES, OBJECTS, VIEWS, DASHBOARDS, WORKFLOWS) — adding APPS follows the identical pattern. App page content loads via the existing `special-panel` dockview mechanism, with the fragment URL going through the already-working nginx→API→AppProxy→UDS chain from S02/S03.

The main work is: (1) a new browser sub-router endpoint listing installed app pages, (2) an `apps_explorer.html` template for the sidebar section, (3) `openAppPageTab()` JS function and `specialType: 'app-page'` handling in workspace-layout.js, (4) wiring the APPS section into `workspace.html`, and (5) loading app-specific CSS/JS when an app page tab is active. All patterns are proven and well-documented in existing code.

One discovery: the test SDK app fixture (`backend/tests/fixtures/test_sdk_app/manifest.yaml`) has page declarations under `frontend.pages` instead of `ui.pages` — the Pydantic `AppManifestSchema` puts pages under `ui.pages`. The fixture needs updating for S04's tests to exercise page data properly.

## Recommendation

4-task build: (1) browser sub-router + apps explorer endpoint + template, (2) workspace.html APPS section wiring, (3) workspace JS (`openAppPageTab` + `specialType: 'app-page'` in workspace-layout.js) with app CSS/JS injection, (4) unit tests + fixture fix. All tasks are independent enough to parallelize after T01 establishes the endpoint.

## Implementation Landscape

### Key Files — Existing (to modify)

| File | What Changes |
|------|-------------|
| `backend/app/templates/browser/workspace.html` (218 lines) | Add APPS section between WORKFLOWS and shared_nav_section, with htmx lazy-load like DASHBOARDS |
| `backend/app/browser/router.py` (33 lines) | Import and include `apps_router` before `objects_router` (D052/D058/D136 pattern) |
| `frontend/static/js/workspace-layout.js` (~330 lines) | Add `specialType: 'app-page'` handling in the `special-panel` factory — load `/app/{appId}/_fragments/{fragment}` |
| `frontend/static/js/workspace.js` (~4000 lines) | Add `openAppPageTab(appId, pageId, label, icon)` function following `openDashboardTab()` pattern |
| `backend/tests/fixtures/test_sdk_app/manifest.yaml` | Fix page declarations: move from `frontend.pages` to `ui.pages` with proper `AppPage` fields |

### Key Files — New (to create)

| File | Purpose |
|------|---------|
| `backend/app/browser/apps.py` | Browser sub-router: `GET /browser/apps/explorer` (sidebar list) + `GET /browser/apps/{app_id}/page/{page_id}` (app page dockview content) |
| `backend/app/templates/browser/apps_explorer.html` | APPS sidebar section body — lists pages from running apps with `openAppPageTab()` onclick |
| `backend/app/templates/browser/app_page.html` | Dockview tab content template — container div with htmx `hx-get` to load fragment from proxy, plus app CSS/JS includes |
| `backend/tests/test_app_browser.py` | Unit tests for the browser apps endpoints |

### Build Order

**T01 — Browser sub-router + explorer endpoint + templates:**
Create `backend/app/browser/apps.py` with two endpoints:
1. `GET /browser/apps/explorer` — queries `request.app.state.app_registry` for all apps, filters to running apps via `request.app.state.app_manager`, collects pages with `nav: "apps"` from manifests. Returns `apps_explorer.html` partial.
2. `GET /browser/apps/{app_id}/page/{page_id}` — looks up app manifest, finds the matching page declaration, renders `app_page.html` which contains an htmx `hx-get` div pointing to `/app/{app_id}/_fragments/{fragment}` plus app CSS/JS `<link>`/`<script>` tags using `/app-static/{appId}/` paths from manifest `frontend.css`/`frontend.js`.

Register in `browser/router.py` before `objects_router`.

**T02 — Workspace HTML wiring:**
Add APPS section to `workspace.html` between WORKFLOWS and `shared_nav_section.html`. Pattern matches DASHBOARDS: `hx-get="/browser/apps/explorer"` with `hx-trigger="load, appsRefreshed from:body"`.

**T03 — Workspace JS:**
Add `openAppPageTab(appId, pageId, label)` to `workspace.js` following `openDashboardTab()` pattern — uses `special-panel` with `specialType: 'app-page'`, `appId`, `pageId` params. Add handling in `workspace-layout.js`'s special-panel factory for `specialType === 'app-page'` → `url = '/browser/apps/' + params.params.appId + '/page/' + params.params.pageId`.

**T04 — Tests + fixture fix:**
Fix test SDK app fixture to use `ui.pages` structure. Write unit tests for both browser endpoints (explorer list, page content). Test: empty registry → no apps in explorer, running app with pages → pages listed, stopped app → not listed, page 404 for unknown app/page.

### Verification Approach

**Unit tests:**
- `pytest tests/test_app_browser.py -v` — all endpoints return correct HTML, filter by running status, handle missing apps/pages
- Existing tests still pass (no regressions from router.py or workspace.py changes)

**Structural verification:**
- `grep -c "apps_router" backend/app/browser/router.py` → 2 (import + include)
- `grep -c "APPS" backend/app/templates/browser/workspace.html` → at least 1
- `grep -c "app-page" frontend/static/js/workspace-layout.js` → at least 1
- `grep -c "openAppPageTab" frontend/static/js/workspace.js` → at least 2 (definition + window export)

**Integration verification (Docker, S07 scope):**
- Install test app → verify APPS section appears in sidebar
- Click app page → dockview tab opens with fragment content from proxy
- App CSS loaded (inspect network tab)

## Constraints

- **Browser router include order:** `apps_router` MUST be included before `objects_router` in `browser/router.py` — objects_router has `{iri:path}` catch-all that would consume `/apps/` URLs (D052, D058, D136 pattern).
- **App page content goes through the existing proxy chain:** nginx `/app/{appId}/` → FastAPI `app_proxy_router` → `AppProxy.forward()` → UDS. The browser sub-router only serves the workspace template wrapper — the actual fragment content is loaded by htmx from the proxy URL.
- **Only running apps with `nav: "apps"` pages should appear in the sidebar.** Stopped apps and pages with `nav: null` should be excluded.
- **App CSS/JS paths use `/app-static/{appId}/` URLs** — nginx already serves these (S03's `alias /app/data/apps-static/`). The `app_page.html` template includes `<link>` and `<script>` tags from `manifest.frontend.css` and `manifest.frontend.js`.
- **Test fixture `backend/tests/fixtures/test_sdk_app/manifest.yaml`** has page data under `frontend.pages` (wrong) instead of `ui.pages` (correct per `AppManifestSchema`). Must fix before writing page-related tests.

## Common Pitfalls

- **Dockview tab ID collisions** — `openAppPageTab()` should use `app-page:{appId}:{pageId}` as the tab key (matching the `dashboard:{id}` pattern). Check for existing panel before creating a new one.
- **htmx `hx-trigger="load"` on hidden tabs** — When a dockview tab is created but not yet visible, htmx `load` may fire before the element is in the DOM. The existing special-panel factory handles this by calling `htmx.ajax('GET', url, {target: el, swap: 'innerHTML'})` imperatively in `init()`, which avoids this issue.
- **Lucide icon re-rendering** — The APPS section header and explorer entries use Lucide icons. After htmx swap, call `lucide.createIcons()` via `hx-on::after-swap` (same as OBJECTS section pattern).
- **AppRegistry vs AppManager for status** — `AppRegistry.list_apps()` returns all registered app IDs (including stopped apps). To show only running apps, the endpoint must also check `AppManager.get_status()`. Alternatively, show all installed apps but indicate status — the acceptance criteria says "installed apps with page declarations appear," which suggests showing all installed, not just running.

## Sources

- `backend/app/templates/browser/workspace.html` — sidebar section patterns (DASHBOARDS, WORKFLOWS)
- `backend/app/templates/browser/dashboard_explorer.html` — explorer body template pattern
- `frontend/static/js/workspace-layout.js:206-240` — special-panel factory with specialType dispatch
- `frontend/static/js/workspace.js:720-750` — `openDashboardTab()` as reference for `openAppPageTab()`
- `backend/app/browser/router.py` — sub-router coordinator with include-order constraints
- `backend/app/apps/manifest.py` — `AppManifestSchema.ui.pages` → list of `AppPage` (id, path, label, icon, nav, fragment)
- `backend/app/apps/proxy.py` — `AppProxy.forward()` handles the actual fragment proxying
- `.gsd/design/APP-PLATFORM-DESIGN.md:715-760` — Level 1 standalone pages design spec
