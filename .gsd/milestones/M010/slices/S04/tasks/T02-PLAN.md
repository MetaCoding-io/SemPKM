---
estimated_steps: 4
estimated_files: 2
---

# T02: Fix navigate action to open app pages as dockview tabs

**Slice:** S04 — Workspace contributions + custom renderer
**Milestone:** M010

## Description

The "Open RSS Reader" command palette entry uses `actionType: "navigate"` with `path: "/reader"`. The current JS handler does `window.location.href = cmd.actionUrl`, which navigates away from the workspace SPA. The fix is twofold: (1) enhance the `commands_list()` API to include `appId` and `pageId` when a navigate command's path matches an app page, and (2) update the JS handler to call `openAppPageTab()` instead of `window.location.href` when those fields are present. This is a platform-wide fix that benefits all apps with navigate commands.

## Steps

1. **Enhance `commands_list()` in `backend/app/browser/apps.py`**:
   - In the navigate branch (`elif cmd.actionType == "navigate" and cmd.path:`), after setting `entry["actionUrl"] = cmd.path`, check if the path matches any of the app's pages
   - The manifest has `ui.pages` with `path` fields. Iterate `manifest.ui.pages` and check if `cmd.path` matches `page.path`
   - If a match is found, add `entry["appId"] = app_id` and `entry["pageId"] = page.id` to the JSON entry
   - If no match, leave the entry as-is (backwards compatible — external URLs or admin paths still do `window.location.href`)

   The logic is approximately:
   ```python
   elif cmd.actionType == "navigate" and cmd.path:
       entry["actionUrl"] = cmd.path
       # Check if path matches an app page → enable dockview tab opening
       for page in manifest.ui.pages:
           if page.path == cmd.path:
               entry["appId"] = app_id
               entry["pageId"] = page.id
               break
   ```

2. **Update `_loadAppCommandEntries()` in `frontend/static/js/workspace.js`**:
   - In the navigate branch of the handler function, check if `cmd.appId` is truthy
   - If yes: call `openAppPageTab(cmd.appId, cmd.pageId, cmd.title)` — this opens the page as a dockview tab within the SPA
   - If no: fall through to existing `window.location.href = cmd.actionUrl` behavior (for non-app-page navigate commands)

   The updated JS is approximately:
   ```javascript
   } else if (cmd.actionType === 'navigate') {
       if (cmd.appId) {
           openAppPageTab(cmd.appId, cmd.pageId, cmd.title);
       } else {
           window.location.href = cmd.actionUrl;
       }
   }
   ```

3. **Verify existing tests still pass**:
   - Run `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v`
   - The existing `test_navigate_command_format` test uses a path `/admin/apps/nav-app/settings` which does NOT match any app page, so `appId`/`pageId` should NOT be present — backwards compatible

4. **Verify syntax**:
   - `python3 -c "import ast; ast.parse(open('backend/app/browser/apps.py').read())"` — syntax OK

## Must-Haves

- [ ] `commands_list()` includes `appId` and `pageId` in navigate command JSON when path matches an app page
- [ ] `commands_list()` does NOT include `appId`/`pageId` when path doesn't match an app page (backwards compat)
- [ ] JS handler calls `openAppPageTab()` when `cmd.appId` is present
- [ ] JS handler falls back to `window.location.href` when `cmd.appId` is absent
- [ ] Existing tests in `test_app_views_commands.py` still pass (zero regressions)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v` — all existing tests pass
- `python3 -c "import ast; ast.parse(open('backend/app/browser/apps.py').read())"` — syntax OK
- Grep for `openAppPageTab` in `workspace.js` inside `_loadAppCommandEntries` → confirms the fix is wired

## Inputs

- `backend/app/browser/apps.py` — current `commands_list()` function (lines 246-284). The navigate branch at line 281-282 sets `actionUrl = cmd.path`. The manifest is available via `app_registry.get_manifest(app_id)` and has `manifest.ui.pages` with each page having `.path` and `.id` attributes.
- `frontend/static/js/workspace.js` — current `_loadAppCommandEntries()` function (lines 1795-1834). The navigate branch at line 1817-1818 does `window.location.href = cmd.actionUrl`. The `openAppPageTab(appId, pageId, label)` function exists at line 737 and is already `window.openAppPageTab = openAppPageTab`.
- `backend/tests/test_app_views_commands.py` — existing test `test_navigate_command_format` at line 313 tests a navigate command with path `/admin/apps/nav-app/settings` — this should NOT match any app page, so `appId`/`pageId` should not appear in the response.

## Expected Output

- `backend/app/browser/apps.py` — `commands_list()` enhanced with app page matching for navigate commands
- `frontend/static/js/workspace.js` — `_loadAppCommandEntries()` handler updated to dispatch navigate commands with `appId` to `openAppPageTab()`

## Observability Impact

- **New JSON fields:** Navigate commands whose path matches an app page now include `appId` and `pageId` in the `/api/apps/commands` response. Inspectable via browser DevTools Network tab or `curl /api/apps/commands | jq`.
- **Behavioral change:** Navigate commands with `appId` open as dockview tabs (SPA) instead of full-page navigations. Observable via dockview panel creation (no browser location change).
- **Failure visibility:** If `openAppPageTab()` fails (missing function, JS error), the browser console will show the error. The fallback `window.location.href` path is only taken when `appId` is absent, so a broken match won't silently degrade — it either opens a tab or navigates away.
- **Backwards compatibility:** Commands whose path doesn't match any app page continue to use `window.location.href` — no `appId`/`pageId` in JSON, no behavior change.
