---
id: T02
parent: S06
milestone: M009
provides:
  - GET /browser/apps/views/explorer — HTML fragment of app view entries for Views sidebar
  - GET /browser/apps/{app_id}/view/{view_id} — dockview tab content for app views
  - GET /api/apps/commands — JSON array of command palette entries from running apps
  - openAppViewTab() JS function for opening app views as dockview tabs
  - app-view special-panel type in workspace-layout.js
  - _loadAppCommandEntries() injects app commands into ninja-keys
key_files:
  - backend/app/browser/apps.py
  - backend/app/templates/browser/app_views_explorer.html
  - backend/app/templates/browser/app_view_tab.html
  - backend/app/templates/browser/views_explorer.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - backend/app/main.py
  - backend/tests/test_app_views_commands.py
key_decisions:
  - Used separate APIRouter with /api prefix (app_commands_router) for commands JSON endpoint to keep it outside /browser prefix; mounted directly on main app
  - Views explorer uses htmx lazy-load with appsRefreshed event rather than inline rendering — keeps views_explorer.html template simple and self-contained
  - Command palette entry IDs use appcmd:{appId}:{cmdId} prefix to avoid collisions with platform entries
patterns_established:
  - App view tabs follow same pattern as app page tabs — special-panel component with htmx fragment loading
  - Command palette async fetch + merge pattern for dynamic entries from apps
observability_surfaces:
  - Logger app.browser.apps at DEBUG: "Views explorer: N app view(s) from running apps"
  - Logger app.browser.apps at DEBUG: "Command palette: N app command(s) from running apps"
  - Logger app.browser.apps at WARNING: 404s for unknown app/view in app_view_tab()
  - GET /api/apps/commands returns inspectable JSON array (empty [] when no apps)
  - Browser console: console.warn('Failed to load app commands:', err) on fetch failure
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Views explorer app contributions and command palette API

**Added views explorer app view entries, app view tab dockview integration, and command palette JSON API with ninja-keys injection**

## What Happened

Added three new endpoints to `apps.py`: views explorer returns HTML fragment of app view entries from running apps, app view tab renders dockview content with htmx fragment loading, and commands API returns JSON array of command palette entries. Modified the views explorer template to include an htmx lazy-load div that fetches app view contributions and refreshes on `appsRefreshed` events. Created `app_view_tab.html` template mirroring `app_page.html`. Added `openAppViewTab()` JS function following `openAppPageTab()` pattern, and `app-view` case in the workspace-layout special-panel factory. Added `_loadAppCommandEntries()` that fetches `/api/apps/commands` and merges entries into ninja-keys data with handlers for dialog, post, and navigate action types. The commands router needed a separate `app_commands_router` with `/api` prefix since the existing `commands_router` name was taken by the platform's command module.

## Verification

- 15/15 tests pass in `test_app_views_commands.py` covering views explorer (running/stopped/empty/multiple apps), app view tab (valid/unknown app/unknown view/CSS+JS includes), and commands API (running/stopped/empty/post/navigate/multiple/keywords)
- 1373/1373 full suite tests pass with zero regressions
- All modified `.py` files pass `ast.parse()` syntax check
- Endpoint module imports cleanly
- grep checks: `openAppViewTab` ≥1 in workspace.js, `app-view` ≥1 in workspace-layout.js, `/api/apps/commands` ≥1 in apps.py

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `backend/.venv/bin/python -m pytest backend/tests/test_app_views_commands.py -v` | 0 | ✅ pass | 0.31s |
| 2 | `backend/.venv/bin/python -m pytest backend/tests/test_right_pane_sections.py -v` | 0 | ✅ pass | 0.30s |
| 3 | `backend/.venv/bin/python -m pytest backend/tests/ -x` | 0 | ✅ pass | 40.13s |
| 4 | `python3 -c "import ast; ast.parse(open('backend/app/browser/apps.py').read())"` | 0 | ✅ pass | <1s |
| 5 | `python3 -c "import ast; ast.parse(open('backend/app/main.py').read())"` | 0 | ✅ pass | <1s |
| 6 | `grep -c "openAppViewTab" frontend/static/js/workspace.js` → 2 | 0 | ✅ pass | <1s |
| 7 | `grep -c "app-view" frontend/static/js/workspace-layout.js` → 1 | 0 | ✅ pass | <1s |
| 8 | `grep -c "/api/apps/commands" backend/app/browser/apps.py` → 1 | 0 | ✅ pass | <1s |

## Diagnostics

- `GET /browser/apps/views/explorer` — curl to inspect rendered HTML of app view entries. Returns empty HTML when no apps have views.
- `GET /api/apps/commands` — returns JSON array; inspectable via `curl localhost:8000/api/apps/commands`. Empty `[]` when no running apps have commands.
- Browser devtools: `document.querySelector('ninja-keys').data.filter(d => d.id.startsWith('appcmd:'))` shows injected app commands.
- Logger `app.browser.apps` at DEBUG level shows view count and command count on each request.

## Deviations

- Used `app_commands_router` instead of `commands_router` because `commands_router` name was already taken by `app.commands.router` in main.py. Mounted directly on the main app instead of under the browser router since it uses `/api` prefix.
- Template named `app_views_explorer.html` (plural) instead of plan's suggested approach of adding directly to the existing views explorer template — the htmx lazy-load approach is cleaner as a separate fragment.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/apps.py` — added 3 endpoints: views explorer, app view tab, commands API + app_commands_router
- `backend/app/main.py` — imported and registered app_commands_router
- `backend/app/templates/browser/app_views_explorer.html` — new template for app view entries in Views sidebar
- `backend/app/templates/browser/app_view_tab.html` — new template for app view dockview tab content
- `backend/app/templates/browser/views_explorer.html` — added htmx lazy-load div for app view contributions
- `frontend/static/js/workspace.js` — added openAppViewTab() function and _loadAppCommandEntries() with ninja-keys injection
- `frontend/static/js/workspace-layout.js` — added app-view case to special-panel factory
- `backend/tests/test_app_views_commands.py` — 15 tests covering views explorer, app view tab, and command palette API
