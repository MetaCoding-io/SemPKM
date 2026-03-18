---
id: T01
parent: S04
milestone: M009
provides:
  - Browser sub-router with GET /apps/explorer and GET /apps/{app_id}/page/{page_id} endpoints
  - APPS sidebar section in workspace.html with htmx lazy-load
  - Explorer and page content Jinja2 templates
  - Unit tests for both endpoints (10 passing)
key_files:
  - backend/app/browser/apps.py
  - backend/app/browser/router.py
  - backend/app/templates/browser/apps_explorer.html
  - backend/app/templates/browser/app_page.html
  - backend/app/templates/browser/workspace.html
  - backend/tests/test_app_browser.py
key_decisions:
  - Used request.app.state.templates pattern (not standalone Jinja2Blocks instance) to match all existing browser sub-routers
  - apps_router placed after sparql_result_router and before objects_router to avoid catch-all {iri:path} consumption
patterns_established:
  - App page fragment loading via htmx hx-get to /app/{app_id}/_fragments/{fragment} proxy URL
  - App CSS/JS included via /app-static/{app_id}/ paths in page template
  - appsRefreshed custom event on body for sidebar refresh signaling
observability_surfaces:
  - Logger app.browser.apps logs WARNING on unknown app_id or page_id lookups
  - GET /browser/apps/explorer returns HTML list of app pages for sidebar inspection
  - 404 responses with descriptive detail for unknown app or page
duration: 18m
verification_result: passed
completed_at: 2026-03-18T09:45:00-04:00
blocker_discovered: false
---

# T01: Browser sub-router, templates, and workspace wiring

**Created apps browser sub-router with explorer and page endpoints, APPS sidebar section in workspace.html, and 10 unit tests**

## What Happened

Created `backend/app/browser/apps.py` with two endpoints: `GET /apps/explorer` lists pages from running apps with `nav == "apps"` for the sidebar, and `GET /apps/{app_id}/page/{page_id}` renders a dockview tab wrapper with htmx fragment loading and app CSS/JS includes. Created both Jinja2 templates (`apps_explorer.html` and `app_page.html`). Registered `apps_router` in `browser/router.py` before `objects_router` to prevent URL consumption by the catch-all pattern. Added the APPS explorer section to `workspace.html` between WORKFLOWS and shared_nav_section with htmx lazy-load on `load, appsRefreshed from:body`. Created `test_app_browser.py` with 10 tests covering empty state, running/stopped app filtering, nav filtering, multi-app display, error handling, 404 responses, and CSS/JS inclusion.

## Verification

- Python syntax check on `apps.py` and `router.py` — both pass
- `grep -c "apps_router" backend/app/browser/router.py` → 2 (import + include)
- `grep -c "APPS" backend/app/templates/browser/workspace.html` → 1
- Router include order verified: apps_router (line 32) before objects_router (line 33)
- All 10 unit tests pass in `test_app_browser.py`
- Full test suite: 1252 passed, 0 failures

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('backend/app/browser/apps.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('backend/app/browser/router.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `grep -c "apps_router" backend/app/browser/router.py` → 2 | 0 | ✅ pass | <1s |
| 4 | `grep -c "APPS" backend/app/templates/browser/workspace.html` → 1 | 0 | ✅ pass | <1s |
| 5 | `grep -n "include_router" backend/app/browser/router.py` — apps before objects | 0 | ✅ pass | <1s |
| 6 | `.venv/bin/python -m pytest tests/test_app_browser.py -v` — 10/10 passed | 0 | ✅ pass | 0.6s |
| 7 | `.venv/bin/python -m pytest tests/ -v` — 1252 passed | 0 | ✅ pass | 41s |

### Slice-level checks (partial — T01 is intermediate)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | `test_app_browser.py` — all tests pass | ✅ | 10/10 |
| 2 | Full test suite — no regressions | ✅ | 1252 passed |
| 3 | `apps_router` count in router.py → 2 | ✅ | |
| 4 | APPS in workspace.html → ≥1 | ✅ | |
| 5 | `app-page` in workspace-layout.js | ⬜ | T02 |
| 6 | `openAppPageTab` in workspace.js | ⬜ | T02 |
| 7 | `ui:` in fixture manifest.yaml | ⬜ | T03 |

## Diagnostics

- **Sidebar inspection:** `GET /browser/apps/explorer` returns HTML body of the APPS sidebar — fetch directly to verify running app state
- **Page loading:** `GET /browser/apps/{app_id}/page/{page_id}` returns htmx wrapper that loads fragment from `/app/{app_id}/_fragments/{fragment}`
- **Failure paths:** 404 with descriptive `detail` messages visible in browser network tab and server logs
- **Refresh event:** `htmx.trigger(document.body, 'appsRefreshed')` triggers sidebar refresh

## Deviations

None — implementation followed the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/apps.py` — new browser sub-router with explorer and page endpoints
- `backend/app/browser/router.py` — added apps_router import and include before objects_router
- `backend/app/templates/browser/apps_explorer.html` — new explorer section body template
- `backend/app/templates/browser/app_page.html` — new dockview tab content template
- `backend/app/templates/browser/workspace.html` — added APPS section between WORKFLOWS and shared_nav_section
- `backend/tests/test_app_browser.py` — new test file with 10 tests for both endpoints
