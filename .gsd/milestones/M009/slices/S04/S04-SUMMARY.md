---
id: S04
parent: M009
milestone: M009
provides:
  - Browser sub-router with GET /apps/explorer and GET /apps/{app_id}/page/{page_id} endpoints
  - APPS sidebar section in workspace.html with htmx lazy-load and appsRefreshed event
  - openAppPageTab() JS function for opening app pages as dockview tabs
  - specialType 'app-page' routing in workspace-layout.js special-panel factory
  - Explorer and page content Jinja2 templates (apps_explorer.html, app_page.html)
  - 11 unit tests covering both browser app endpoints
requires:
  - slice: S02
    provides: AppProxy (fragment forwarding via nginx→API→UDS chain), SDK route handlers
  - slice: S03
    provides: nginx proxy config (/app/{appId}/ and /app-static/{appId}/), admin install flow
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
key_decisions:
  - Used request.app.state.templates pattern (not standalone Jinja2Blocks) to match all existing browser sub-routers
  - apps_router placed after sparql_result_router and before objects_router to avoid catch-all {iri:path} consumption
  - Tab key format app-page:{appId}:{pageId} matches dashboard:{id} convention for tab dedup
patterns_established:
  - App page fragment loading via htmx hx-get to /app/{app_id}/_fragments/{fragment} proxy URL
  - App CSS/JS included via /app-static/{app_id}/ paths in page template
  - appsRefreshed custom event on body for sidebar refresh signaling
  - openAppPageTab() follows openDashboardTab() pattern — tab key, dedup check, _tabMeta, special-panel component
observability_surfaces:
  - Logger app.browser.apps logs WARNING on unknown app_id or page_id lookups
  - GET /browser/apps/explorer returns HTML list of app pages for sidebar inspection
  - 404 responses with descriptive detail for unknown app or page
  - window.openAppPageTab callable from browser console for tab creation testing
drill_down_paths:
  - .gsd/milestones/M009/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S04/tasks/T03-SUMMARY.md
duration: 36m
verification_result: passed
completed_at: 2026-03-18
---

# S04: Frontend Level 1 — Standalone Pages & Sidebar

**Workspace [APPS] sidebar section with htmx-loaded app pages served through the platform proxy chain as dockview tabs**

## What Happened

Three tasks delivered the full frontend Level 1 integration for the app platform:

**T01 (backend + templates):** Created `backend/app/browser/apps.py` with two endpoints. `GET /apps/explorer` queries the app registry for running apps, filters to pages with `nav == "apps"`, and renders the sidebar section body. `GET /apps/{app_id}/page/{page_id}` looks up the manifest, finds the matching page, and renders a dockview tab wrapper with an htmx `hx-get` pointing to `/app/{app_id}/_fragments/{fragment}` (the proxy chain from S02/S03). The page template includes CSS via `/app-static/{app_id}/` paths and JS tags from the manifest's `frontend` section. The APPS section was added to `workspace.html` between WORKFLOWS and the shared nav section, lazy-loaded on `load, appsRefreshed from:body`. Router registration order places `apps_router` before `objects_router` to prevent the catch-all `{iri:path}` pattern from consuming `/apps/*` URLs.

**T02 (workspace JS):** Added `openAppPageTab(appId, pageId, label)` to `workspace.js` following the `openDashboardTab()` pattern — tab key `app-page:{appId}:{pageId}` for dedup, `_tabMeta` tracking, and `special-panel` creation. Added the `app-page` case in `workspace-layout.js`'s special-panel factory to route to `/browser/apps/{appId}/page/{pageId}`.

**T03 (tests + fixture):** Created 11 unit tests in `test_app_browser.py` — 6 for the explorer endpoint (empty state, running/stopped filtering, nav filtering, multi-app, mixed status) and 5 for the page endpoint (unknown app/page 404s, fragment URL rendering, CSS/JS inclusion). The test fixture manifest was already correct with `ui.pages` from prior work.

## Verification

- `grep -c "apps_router" backend/app/browser/router.py` → 2 ✅
- `grep -c "APPS" backend/app/templates/browser/workspace.html` → 1 ✅
- `grep -c "app-page" frontend/static/js/workspace-layout.js` → 1 ✅
- `grep -c "openAppPageTab" frontend/static/js/workspace.js` → 2 ✅
- `grep "ui:" backend/tests/fixtures/test_sdk_app/manifest.yaml` → present ✅
- `python -m pytest tests/test_app_browser.py -v` → 11/11 passed ✅
- `python -m pytest tests/ -v` → 1253 passed, 0 failures ✅
- Logger `app.browser.apps` emits WARNING for unknown app_id and page_id lookups ✅
- 404 responses include descriptive detail messages ✅

## Requirements Advanced

- APP-07 (Frontend integration Level 1 — standalone pages) — Full backend + frontend wiring delivered: APPS sidebar section, dockview tab creation, htmx fragment loading through proxy chain. Unit-tested but not yet exercised against a live app in Docker (S07).

## Requirements Validated

- None — APP-07 requires live Docker verification with a real app serving fragments (S07 scope).

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

None — all three tasks followed the slice plan exactly. The fixture manifest was already correctly structured from S02 work, so T03's fixture fix was a no-op verification.

## Known Limitations

- The APPS sidebar and page loading are unit-tested with mocked registry/manager but not yet exercised against a real running app in Docker. S07 will provide integration proof.
- No E2E Playwright test for this slice — deferred to S07 which tests the full install → page → admin flow.
- No user guide docs for this slice — deferred to S08 which documents all frontend integration levels together.

## Follow-ups

- S06 will extend this pattern to Level 2 (workspace contributions — right pane sections, views, command palette) and Level 3 (renderer overrides).
- S07 will exercise the full chain with a real test app in Docker.

## Files Created/Modified

- `backend/app/browser/apps.py` — new browser sub-router with explorer and page endpoints
- `backend/app/browser/router.py` — added apps_router import and include before objects_router
- `backend/app/templates/browser/apps_explorer.html` — new explorer section body template
- `backend/app/templates/browser/app_page.html` — new dockview tab content template with htmx fragment loading + CSS/JS includes
- `backend/app/templates/browser/workspace.html` — added APPS section between WORKFLOWS and shared_nav_section
- `frontend/static/js/workspace.js` — added openAppPageTab() function + window export
- `frontend/static/js/workspace-layout.js` — added app-page specialType case in special-panel factory
- `backend/tests/test_app_browser.py` — new test file with 11 tests for both endpoints

## Forward Intelligence

### What the next slice should know
- The `app_page.html` template loads fragments via `hx-get="/app/{app_id}/_fragments/{fragment}"`. S06's Level 2 contributions (right pane sections, views) should follow the same fragment-loading pattern but with different proxy paths.
- The `appsRefreshed` custom event triggers sidebar reload — S06 should trigger this when app contributions change (e.g. after install/uninstall).
- `openAppPageTab()` uses `specialType: 'app-page'` in the special-panel factory. S06 will need additional specialType values for workspace contributions if they open as tabs.

### What's fragile
- Router registration order in `browser/router.py` — apps_router must stay before objects_router. If new routers are added between them with overlapping path patterns, URL consumption issues could arise.
- The explorer endpoint relies on `app_manager.get_status()` returning `{"status": "running"}` — any change to the status dict structure would break filtering.

### Authoritative diagnostics
- `python -m pytest tests/test_app_browser.py -v` — validates explorer filtering logic and page rendering in <1s
- `GET /browser/apps/explorer` in browser — directly inspects what the sidebar would show
- Browser console: `openAppPageTab('test-app', 'main', 'Test')` — tests tab creation without the sidebar

### What assumptions changed
- Assumed fixture manifest needed fixing from `frontend.pages` to `ui.pages` — it was already correct from S02 work. T03's fixture fix was a verification pass, not a code change.
