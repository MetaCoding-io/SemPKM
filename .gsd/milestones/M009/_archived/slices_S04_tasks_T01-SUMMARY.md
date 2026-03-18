---
id: T01
parent: S04
milestone: M009
provides:
  - Browser sub-router for app pages (GET /apps/explorer, GET /apps/{app_id}/page/{page_id})
  - APPS sidebar section in workspace.html with htmx lazy-load
  - Explorer and page tab Jinja2 templates
key_files:
  - backend/app/browser/apps.py
  - backend/app/browser/router.py
  - backend/app/templates/browser/apps_explorer.html
  - backend/app/templates/browser/app_page.html
  - backend/app/templates/browser/workspace.html
key_decisions:
  - Used request.app.state.templates (shared instance) instead of local Jinja2Blocks — matches all other browser sub-routers
patterns_established:
  - apps_router registered before objects_router to avoid catch-all path consumption (D052/D058/D136)
  - appsRefreshed custom event on body for sidebar refresh signaling
observability_surfaces:
  - Logger app.browser.apps logs WARNING on unknown app_id or page_id lookups
  - GET /browser/apps/explorer returns inspectable HTML of running app pages
  - 404 responses with descriptive detail for unknown app or page
duration: 15m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Browser sub-router, templates, and workspace wiring

**Created apps browser sub-router with explorer and page endpoints, two Jinja2 templates, registered router before objects catch-all, and added APPS sidebar section to workspace.html.**

## What Happened

Built the full server-side layer for standalone app pages:

1. Created `backend/app/browser/apps.py` with `apps_router` containing two endpoints:
   - `GET /apps/explorer` — queries registry for running apps, filters pages with `nav == "apps"`, renders `apps_explorer.html`
   - `GET /apps/{app_id}/page/{page_id}` — resolves manifest + page, builds fragment URL and CSS/JS lists, renders `app_page.html`
2. Created `apps_explorer.html` — tree-leaf items with Lucide icons and `openAppPageTab()` onclick
3. Created `app_page.html` — htmx load trigger pointed at `/app/{app_id}/_fragments/{fragment}` with CSS link and JS script includes
4. Registered `apps_router` in `browser/router.py` at line 31 — before `objects_router` at line 32
5. Added APPS explorer section to `workspace.html` between WORKFLOWS and shared_nav_section, with `hx-trigger="load, appsRefreshed from:body"`

## Verification

- `python3 -c "import ast; ast.parse(open('backend/app/browser/apps.py').read())"` — OK
- `python3 -c "import ast; ast.parse(open('backend/app/browser/router.py').read())"` — OK
- `grep -c "apps_router" backend/app/browser/router.py` → 2 (import + include)
- `grep -c "APPS" backend/app/templates/browser/workspace.html` → 1
- `grep -n "include_router" backend/app/browser/router.py` — apps_router at line 31, objects_router at line 32

### Slice-level checks (T01 scope):
- ✅ `grep -c "apps_router" backend/app/browser/router.py` → 2
- ✅ `grep -c "APPS" backend/app/templates/browser/workspace.html` → 1
- ⏳ `grep -c "app-page" frontend/static/js/workspace-layout.js` → 0 (T02/T03 scope)
- ⏳ `grep -c "openAppPageTab" frontend/static/js/workspace.js` → 0 (T02 scope)
- ⏳ `pytest tests/test_app_browser.py` — not yet created (T03 scope)

## Diagnostics

- Fetch `GET /browser/apps/explorer` directly to see rendered app pages HTML
- 404 for `GET /browser/apps/nonexistent/page/foo` with detail "App nonexistent not found"
- Logger `app.browser.apps` at WARNING for page lookup misses

## Deviations

- Plan said "Use Jinja2Blocks for the templates instance" but all existing browser sub-routers use `request.app.state.templates` (the shared instance). Followed the existing codebase pattern instead.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/apps.py` — new browser sub-router with 2 endpoints
- `backend/app/templates/browser/apps_explorer.html` — new explorer section template
- `backend/app/templates/browser/app_page.html` — new dockview tab content template
- `backend/app/browser/router.py` — added apps_router import and include before objects_router
- `backend/app/templates/browser/workspace.html` — added APPS sidebar section between WORKFLOWS and shared_nav_section
- `.gsd/milestones/M009/slices/S04/tasks/T01-PLAN.md` — added Observability Impact section
- `.gsd/milestones/M009/slices/S04/S04-PLAN.md` — added diagnostic verification step, marked T01 done
