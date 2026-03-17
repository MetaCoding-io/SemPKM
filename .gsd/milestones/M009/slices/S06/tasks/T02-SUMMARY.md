---
id: T02
parent: S06
milestone: M009
provides:
  - GET /browser/apps/views/explorer endpoint returning view contributions from running apps
  - GET /browser/apps/{app_id}/view/{view_id} endpoint for app view tab content
  - GET /api/apps/commands JSON endpoint for command palette entries from running apps
  - openAppViewTab() JS function for opening app views as dockview tabs
  - app-view special-panel type in workspace-layout.js
  - _loadAppCommandEntries() injecting app commands into ninja-keys
key_files:
  - backend/app/browser/apps.py
  - backend/app/templates/browser/app_views_explorer.html
  - backend/app/templates/browser/app_view_tab.html
  - backend/app/templates/browser/views_explorer.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - backend/tests/test_app_views_commands.py
key_decisions:
  - Created separate apps_api_router with prefix /api/apps for command palette JSON endpoint, following dashboard/workflow pattern of separate browser + api routers
  - Used appcmd: prefix for ninja-keys entry IDs to namespace app commands and allow clean filtering on refresh
patterns_established:
  - Views explorer lazy-load pattern: htmx div with hx-trigger="load, appsRefreshed from:body" for app view contributions
  - Command palette injection pattern: fetch JSON → filter existing → concat new entries, with console.warn on failure
observability_surfaces:
  - Logger app.browser.apps at DEBUG — logs app view count and command count per request
  - Logger app.browser.apps at WARNING — logs 404s for unknown app/view lookups
  - GET /api/apps/commands — returns inspectable JSON array of registered commands
  - Browser devtools — document.querySelector('ninja-keys').data.filter(d => d.id.startsWith('appcmd:'))
  - console.warn on _loadAppCommandEntries fetch failure
duration: 1 context window
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Views explorer app contributions and command palette API

**Added 3 new endpoints (views explorer, view tab, commands JSON) plus JS wiring for app view tabs and ninja-keys command injection.**

## What Happened

Built three backend endpoints in `apps.py`:
1. `GET /browser/apps/views/explorer` — collects view contributions from running apps' `ui.contributions.views` manifests, renders as tree-leaf entries under an "App Views" group heading.
2. `GET /browser/apps/{app_id}/view/{view_id}` — resolves a view from the app manifest and renders `app_view_tab.html` with fragment URL and CSS/JS includes. 404 for unknown app or view.
3. `GET /api/apps/commands` — collects command palette entries from running apps' `ui.contributions.commandPalette` manifests, returns JSON array with id, title, section, actionType, actionUrl.

Created `apps_api_router` (prefix `/api/apps`) for the JSON commands endpoint, mounted in `main.py` — follows the same browser/api router split pattern as dashboard and workflow modules.

Modified `views_explorer.html` to lazy-load app views via htmx between the Graph View entry and Saved Views folder. Created `app_views_explorer.html` and `app_view_tab.html` templates.

In `workspace.js`, added `openAppViewTab()` following the `openAppPageTab()` pattern (tab key `app-view:{appId}:{viewId}`, dedup via `_tabMeta`, special-panel component). Added `_loadAppCommandEntries()` called from `initCommandPalette()` — fetches `/api/apps/commands` and merges entries into `ninja.data` with `appcmd:` prefix. Handles dialog (htmx GET), post (htmx POST), and navigate (window.location) action types.

In `workspace-layout.js`, added `app-view` case to the special-panel factory routing to `/browser/apps/{appId}/view/{viewId}`.

## Verification

- `backend/tests/test_app_views_commands.py` — 13 tests all pass: views explorer with/without apps, stopped app exclusion, view tab content + 404s, command palette JSON with all action types, empty array, stopped exclusion, multiple apps
- Full test suite (1169 tests) — all pass, zero regressions
- `grep -c "openAppViewTab" frontend/static/js/workspace.js` → 2
- `grep -c "app-view" frontend/static/js/workspace-layout.js` → 1
- Python AST parse check on all modified `.py` files — clean
- `from app.browser.apps import apps_router, apps_api_router` — importable

## Diagnostics

- `curl /browser/apps/views/explorer` — inspect rendered HTML for app view entries
- `curl /api/apps/commands` — inspect JSON array of registered commands (empty array when no apps)
- Logger `app.browser.apps` at DEBUG — logs view count and command count per request
- Browser devtools: `document.querySelector('ninja-keys').data.filter(d => d.id.startsWith('appcmd:'))` — shows injected app commands
- `console.warn('Failed to load app commands:', err)` on fetch failure

## Deviations

- Plan verification check `grep -c "/api/apps/commands" backend/app/browser/apps.py` expects the literal full URL in the file, but the actual code uses `@apps_api_router.get("/commands")` with the prefix `/api/apps` defined on the router. The endpoint resolves correctly at runtime to `/api/apps/commands`. This is the standard FastAPI pattern.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/apps.py` — added 3 endpoints (views explorer, view tab, commands JSON) + `apps_api_router`
- `backend/app/main.py` — imported and mounted `apps_api_router`
- `backend/app/templates/browser/app_views_explorer.html` — new template for app view tree-leaf entries
- `backend/app/templates/browser/app_view_tab.html` — new template for app view tab content (htmx fragment loading)
- `backend/app/templates/browser/views_explorer.html` — added htmx lazy-load div for app views
- `frontend/static/js/workspace.js` — added `openAppViewTab()` + `_loadAppCommandEntries()`
- `frontend/static/js/workspace-layout.js` — added `app-view` case in special-panel factory
- `backend/tests/test_app_views_commands.py` — 13 tests covering views and commands endpoints
- `.gsd/milestones/M009/slices/S06/tasks/T02-PLAN.md` — added Observability Impact section
