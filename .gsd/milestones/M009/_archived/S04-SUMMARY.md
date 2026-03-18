---
id: S04
parent: M009
milestone: M009
provides:
  - Browser sub-router for app pages (GET /apps/explorer, GET /apps/{app_id}/page/{page_id})
  - APPS sidebar section in workspace.html with htmx lazy-load and appsRefreshed event trigger
  - apps_explorer.html template listing app pages with Lucide icons and openAppPageTab() onclick
  - app_page.html template with htmx fragment loading and CSS/JS includes from /app-static/{appId}/
  - openAppPageTab() global JS function for opening app pages as dockview tabs
  - specialType 'app-page' routing in workspace-layout.js special-panel factory
  - 11 unit tests covering explorer filtering and page rendering
  - Fixed test_sdk_app fixture manifest (ui.pages schema, author format)
requires:
  - slice: S02
    provides: AppProxy (fragment forwarding via UDS), SDK route handlers for serving fragments
  - slice: S03
    provides: nginx proxy config (/app/{appId}/ → API, /app-static/{appId}/ → static), admin install flow
affects:
  - S06
key_files:
  - backend/app/browser/apps.py
  - backend/app/browser/router.py
  - backend/app/templates/browser/apps_explorer.html
  - backend/app/templates/browser/app_page.html
  - backend/app/templates/browser/workspace.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - backend/tests/test_app_browser.py
  - backend/tests/fixtures/test_sdk_app/manifest.yaml
key_decisions:
  - Used request.app.state.templates (shared Jinja2Blocks instance) instead of local instance — matches all existing browser sub-routers
  - Tab key format app-page:{appId}:{pageId} for dedup — consistent with dashboard/workflow tab key patterns
  - apps_router registered before objects_router in browser/router.py to avoid catch-all path consumption (D052/D058/D136 pattern)
patterns_established:
  - App page tab opener follows identical structure to openDashboardTab (composite tabKey, dedup check, _tabMeta, addPanel with special-panel component)
  - appsRefreshed custom event on body for sidebar refresh signaling (matches dashboardsRefreshed, workflowsRefreshed pattern)
  - Browser endpoint test pattern for app platform — FastAPI TestClient + Jinja2Blocks + mock app_registry/app_manager on app.state
observability_surfaces:
  - Logger app.browser.apps logs WARNING on unknown app_id or page_id lookups
  - GET /browser/apps/explorer returns inspectable HTML of running app pages
  - 404 responses with descriptive detail for unknown app or page (e.g. "App {id} not found")
  - window.openAppPageTab callable from browser console for manual testing
  - window._dockview.panels.map(p => p.id) shows open app-page tab IDs
drill_down_paths:
  - .gsd/milestones/M009/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S04/tasks/T03-SUMMARY.md
duration: 33m
verification_result: passed
completed_at: 2026-03-16
---

# S04: Frontend Level 1 — Standalone Pages & Sidebar

**Wired the full htmx fragment loading chain for app standalone pages — sidebar discovery, dockview tab creation, and proxy-backed content loading — with 11 unit tests proving endpoint behavior.**

## What Happened

Three tasks assembled the complete frontend integration for Level 1 app pages:

**T01 (backend endpoints + templates):** Created `backend/app/browser/apps.py` with two endpoints. The explorer endpoint queries `AppRegistry.list_apps()`, filters to running apps via `AppManager.get_status()`, collects pages with `nav == "apps"`, and renders `apps_explorer.html`. The page content endpoint resolves the manifest, finds the matching page, and renders `app_page.html` with an htmx `hx-get` pointed at `/app/{appId}/_fragments/{fragment}` plus CSS `<link>` and JS `<script>` tags from `/app-static/{appId}/`. Registered `apps_router` in `browser/router.py` before `objects_router` to avoid catch-all path consumption. Added APPS section to `workspace.html` between WORKFLOWS and shared_nav_section with `hx-trigger="load, appsRefreshed from:body"`.

**T02 (workspace JS):** Added `openAppPageTab(appId, pageId, label)` to `workspace.js` following the `openDashboardTab()` pattern — composite tab key for dedup, existing-panel activation check, `_tabMeta` registration, `addPanel` with `special-panel` component. Added `app-page` case to `workspace-layout.js` special-panel factory routing to `/browser/apps/{appId}/page/{pageId}`.

**T03 (tests + fixture):** Fixed `manifest.yaml` from incorrect `frontend.pages` block to proper `ui.pages` with correct `AppPage` fields (`id`, `path`, `label`, `icon`, `nav`, `fragment`). Fixed `author` field from bare string to `AppAuthor` object. Created 11 unit tests: 6 explorer tests (empty, running with pages, stopped excluded, non-nav excluded, multiple apps, mixed status) and 5 page tests (unknown app 404, unknown page 404, correct fragment URL, CSS includes, JS includes).

## Verification

- `pytest tests/test_app_browser.py -v` — 11/11 pass
- `pytest tests/ -v` — 1045/1045 pass, zero regressions
- `grep -c "apps_router" backend/app/browser/router.py` → 2 ✓
- `grep -c "APPS" backend/app/templates/browser/workspace.html` → 1 ✓
- `grep -c "app-page" frontend/static/js/workspace-layout.js` → 1 ✓
- `grep -c "openAppPageTab" frontend/static/js/workspace.js` → 2 ✓
- `grep "ui:" backend/tests/fixtures/test_sdk_app/manifest.yaml` → present ✓
- Fixture parses against `AppManifestSchema` without error

## Requirements Advanced

- APP-07 (Frontend integration Level 1 — standalone pages) — All server-side and client-side wiring complete. Explorer endpoint filters to running apps with nav="apps" pages, page content endpoint renders htmx fragment loader with CSS/JS includes, APPS sidebar section added to workspace, dockview tab creation wired. Unit tests prove endpoint behavior. Full end-to-end validation deferred to S07 (requires running app in Docker).

## Requirements Validated

- none — APP-07 needs live Docker stack proof in S07

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T01 used `request.app.state.templates` (shared Jinja2Blocks instance) instead of plan's suggestion to use a local `Jinja2Blocks` instance. All existing browser sub-routers use the shared instance — following codebase convention.
- T03 fixed the `author` field in `manifest.yaml` from bare string to `AppAuthor` object — the schema requires a dict, not a plain string. This was a pre-existing fixture bug masked by the old `frontend.pages` structure.

## Known Limitations

- DeprecationWarning on `TemplateResponse(name, {"request": request})` call signature in `apps.py` — Starlette/Jinja2Blocks now expects `TemplateResponse(request, name)`. Existing codebase uses the old signature throughout; not fixing in isolation.
- No live runtime proof yet — unit tests use mock registry/manager. Full proxy chain (nginx → API → AppProxy → UDS → SDK app) exercised in S07.
- E2E tests and user guide docs deferred to S07/S08 per roadmap design (S04 is a backend/frontend wiring slice, not a user-visible feature slice in isolation).

## Follow-ups

- S06 consumes the `app_page.html` pattern and APPS sidebar for Level 2+3 contributions (workspace widgets, right pane sections, renderer overrides)
- S07 exercises the full chain in Docker with a real test app

## Files Created/Modified

- `backend/app/browser/apps.py` — new: browser sub-router with explorer and page endpoints
- `backend/app/browser/router.py` — modified: added apps_router import and include before objects_router
- `backend/app/templates/browser/apps_explorer.html` — new: sidebar explorer listing app pages
- `backend/app/templates/browser/app_page.html` — new: dockview tab with htmx fragment loader + CSS/JS includes
- `backend/app/templates/browser/workspace.html` — modified: added APPS sidebar section
- `frontend/static/js/workspace.js` — modified: added openAppPageTab() + window export
- `frontend/static/js/workspace-layout.js` — modified: added app-page specialType in special-panel factory
- `backend/tests/test_app_browser.py` — new: 11 unit tests for browser app endpoints
- `backend/tests/fixtures/test_sdk_app/manifest.yaml` — modified: ui.pages schema, frontend.css/js, author format

## Forward Intelligence

### What the next slice should know
- The `app_page.html` template pattern (htmx div + CSS/JS includes) is the reference for all three frontend integration levels. S06 should reuse the CSS/JS inclusion pattern for right-pane sections and renderer override fragments.
- `appsRefreshed` is the custom event for sidebar refresh. S06 should dispatch this event when app contributions change.
- The explorer endpoint only shows pages with `nav == "apps"`. Pages with `nav: null` are invisible in the sidebar — this is intentional for pages that are only reachable via command palette or direct URL.

### What's fragile
- Router registration order in `browser/router.py` — `apps_router` must stay before `objects_router`. The objects router has `{object_iri:path}` catch-all patterns that would consume `/apps/*` URLs if it wins priority.
- The `TemplateResponse` call signature deprecation — when Starlette drops the old signature, all browser sub-routers (not just apps.py) will need updating.

### Authoritative diagnostics
- `pytest tests/test_app_browser.py -v` — 11 tests proving explorer filtering logic and page rendering correctness
- `GET /browser/apps/explorer` in a running stack — directly inspectable HTML of the sidebar content
- Logger `app.browser.apps` at WARNING — page lookup misses for unknown app/page

### What assumptions changed
- Plan assumed `Jinja2Blocks` local instance for templates — actual codebase uses shared `request.app.state.templates` throughout. No impact on functionality.
- Test fixture `author` field was a bare string, not an `AppAuthor` object — schema validation caught this during T03.
