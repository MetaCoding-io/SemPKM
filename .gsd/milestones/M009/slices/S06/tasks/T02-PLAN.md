---
estimated_steps: 8
estimated_files: 6
---

# T02: Views explorer app contributions and command palette API

**Slice:** S06 — Frontend Level 2+3 — Workspace Contributions & Renderer Overrides
**Milestone:** M009

## Description

Extend the Views explorer to show app view contributions and create a command palette API for injecting app commands into ninja-keys. These complete the Level 2 workspace contributions (APP-08) alongside T01's right pane work. The views explorer is currently a static Jinja template and ninja-keys has hardcoded entries — both need app contribution wiring.

## Steps

1. **Add views explorer app contributions** to `backend/app/browser/apps.py`:
   - Create `GET /browser/apps/views/explorer` endpoint that queries `AppRegistry` for running apps with `ui.views` contributions.
   - For each running app, collect views from manifest's `ui.views` list. Each view has `id`, `label`, `icon`, `fragment`.
   - Return rendered HTML fragment — a list of `tree-leaf` entries under an "App Views" group heading.
   - Each entry calls `openAppViewTab('{app_id}', '{view_id}', '{label}')` onclick — following the same pattern as `openAppPageTab()` in `apps_explorer.html`.
   - Use Lucide icon from view declaration if present.

2. **Modify views explorer template** (`backend/app/templates/browser/views_explorer.html`):
   - After the generic views (Table, Cards, Graph) and before the Saved Views folder, add an htmx include: `<div hx-get="/browser/apps/views/explorer" hx-trigger="load, appsRefreshed from:body" hx-swap="innerHTML"></div>`.
   - This lazy-loads app view contributions and refreshes when apps change.
   - Alternative: if the views explorer endpoint already passes context to the template, the app views could be rendered inline via template variable. Choose whichever approach is cleaner given the existing code. The htmx lazy-load is simpler and self-contained.

3. **Create `app_view_tab.html` template** at `backend/app/templates/browser/app_view_tab.html`:
   - Similar structure to `app_page.html` (from S04) but for view contributions.
   - Loads the app's view fragment via htmx: `<div hx-get="/app/{app_id}/_fragments/{fragment}" hx-trigger="load" hx-swap="innerHTML"></div>`.
   - Include app CSS/JS from `/app-static/{appId}/` (same pattern as `app_page.html`).

4. **Add `GET /browser/apps/{app_id}/view/{view_id}` endpoint** in `apps.py`:
   - Resolves the view from the app's manifest `ui.views` list.
   - Renders `app_view_tab.html` with the app's fragment URL, CSS/JS paths.
   - Returns 404 with descriptive detail for unknown app or view.

5. **Add JS + layout wiring for app view tabs**:
   - In `workspace.js`, add `openAppViewTab(appId, viewId, label)` function following `openAppPageTab()` pattern:
     - Tab key: `app-view:{appId}:{viewId}`
     - Dedup check against `_tabMeta`
     - `addPanel` with `special-panel` component
     - Register in `_tabMeta`
   - In `workspace-layout.js`, add `app-view` case to the special-panel factory — routes to `/browser/apps/{appId}/view/{viewId}`.

6. **Create `GET /api/apps/commands` endpoint** in `apps.py`:
   - Query `AppRegistry` for running apps with `ui.commandPalette` entries.
   - Return JSON array: each entry has `{ id: "{appId}:{cmdId}", title: "...", icon: "...", section: "{appName}", actionType: "dialog|post|navigate", actionUrl: "..." }`.
   - `actionUrl` for dialog type: `/app/{appId}/_fragments/{fragment}`
   - `actionUrl` for post type: `/app/{appId}/_fragments/{fragment}` (POST)
   - `actionUrl` for navigate type: the URL as-is from manifest
   - Return `[]` when no apps have commands.

7. **Inject app commands into ninja-keys** in `workspace.js`:
   - In `initCommandPalette()` (around line 1307), after the existing static entries setup and the `_addTypeCreateEntries()` call, add:
     ```javascript
     fetch('/api/apps/commands')
       .then(r => r.json())
       .then(commands => {
         const ninja = document.querySelector('ninja-keys');
         if (!ninja || !commands.length) return;
         const appEntries = commands.map(cmd => ({
           id: cmd.id,
           title: cmd.title,
           icon: cmd.icon || '',
           section: cmd.section,
           handler: () => {
             if (cmd.actionType === 'dialog') {
               // htmx GET fragment into modal (use existing modal pattern)
               htmx.ajax('GET', cmd.actionUrl, {target: '#modal-container', swap: 'innerHTML'});
             } else if (cmd.actionType === 'post') {
               htmx.ajax('POST', cmd.actionUrl, {target: '#modal-container', swap: 'innerHTML'});
             } else if (cmd.actionType === 'navigate') {
               window.location.href = cmd.actionUrl;
             }
           }
         }));
         ninja.data = [...ninja.data, ...appEntries];
       })
       .catch(err => console.warn('Failed to load app commands:', err));
     ```
   - Adjust the above pattern to match actual ninja-keys data format — check the existing `_addTypeCreateEntries()` function for the exact entry shape used.

8. **Write tests** in `backend/tests/test_app_views_commands.py`:
   - Test: views explorer with running app that has views → returns view entries HTML
   - Test: views explorer with no apps → returns empty or no entries
   - Test: views explorer excludes stopped apps
   - Test: app view tab endpoint returns correct template with fragment URL
   - Test: app view tab 404 for unknown app
   - Test: command palette JSON with app commands → correct format
   - Test: command palette JSON with no apps → empty array
   - Test: command palette excludes stopped apps
   - Use same test pattern as T01: FastAPI TestClient + mock app_registry/app_manager.

## Must-Haves

- [ ] App view entries appear in views explorer HTML (lazy-loaded via htmx)
- [ ] `openAppViewTab()` JS function opens app views as dockview tabs
- [ ] `app-view` special-panel type routed in workspace-layout.js
- [ ] `GET /api/apps/commands` returns correct JSON array of command entries
- [ ] ninja-keys data extended with app command entries after workspace init
- [ ] Command action dispatch handles dialog, post, and navigate types
- [ ] Tests covering views explorer and command palette with/without apps

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/test_app_views_commands.py -v` — all tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/ -x --timeout=30` — zero regressions
- `grep -c "openAppViewTab" frontend/static/js/workspace.js` → ≥1
- `grep -c "app-view" frontend/static/js/workspace-layout.js` → ≥1
- `grep -c "/api/apps/commands" backend/app/browser/apps.py` → ≥1

## Inputs

- `backend/app/browser/apps.py` — existing endpoints from S04 + T01's right pane endpoint. New endpoints added here.
- `backend/app/templates/browser/views_explorer.html` — current static views explorer template. Needs app views injection point.
- `backend/app/templates/browser/app_page.html` — reference template for `app_view_tab.html` (htmx fragment loading + CSS/JS includes).
- `frontend/static/js/workspace.js` — `openAppPageTab()` function is the pattern for `openAppViewTab()`. `initCommandPalette()` at ~line 1307 sets up ninja-keys. `_addTypeCreateEntries()` shows how to push entries into ninja-keys data.
- `frontend/static/js/workspace-layout.js` — special-panel factory with existing `app-page` case from S04.
- S04 summary: tab key format `app-page:{appId}:{pageId}`, dedup via `_tabMeta`, `appsRefreshed` custom event pattern.

## Expected Output

- `backend/app/browser/apps.py` — 3 new endpoints: views explorer, view tab content, commands API
- `backend/app/templates/browser/views_explorer.html` — modified with app views htmx include
- `backend/app/templates/browser/app_view_tab.html` — new template for app view tabs
- `frontend/static/js/workspace.js` — `openAppViewTab()` function + command palette injection in `initCommandPalette()`
- `frontend/static/js/workspace-layout.js` — `app-view` case in special-panel factory
- `backend/tests/test_app_views_commands.py` — ≥8 tests covering views and commands

## Observability Impact

- **Logger `app.browser.apps` at DEBUG level** logs app view count from `views_explorer_apps()` and command count from `commands_list()` on each request.
- **Logger `app.browser.apps` at WARNING level** logs 404s for unknown app/view in `app_view_tab()`.
- **`GET /browser/apps/views/explorer`** — curl directly to inspect rendered HTML for app view entries.
- **`GET /api/apps/commands`** — returns JSON array of registered commands from running apps; empty array `[]` when no apps have commands. Inspectable via curl or browser devtools Network tab.
- **Browser console** — `console.warn('Failed to load app commands:', err)` on fetch failure from `_loadAppCommandEntries()`.
- **ninja-keys data** — In browser devtools: `document.querySelector('ninja-keys').data.filter(d => d.id.startsWith('appcmd:'))` shows injected app commands.
