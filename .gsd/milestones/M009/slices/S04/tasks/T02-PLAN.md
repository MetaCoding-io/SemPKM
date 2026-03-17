---
estimated_steps: 4
estimated_files: 2
---

# T02: Workspace JS — openAppPageTab + special-panel handler

**Slice:** S04 — Frontend Level 1 — Standalone Pages & Sidebar
**Milestone:** M009

## Description

Add the client-side JavaScript to open app pages as dockview tabs. Two changes: (1) an `openAppPageTab()` function in workspace.js following the `openDashboardTab()` pattern, and (2) a `specialType === 'app-page'` case in workspace-layout.js's special-panel factory.

## Steps

1. Add `openAppPageTab(appId, pageId, label)` function to `frontend/static/js/workspace.js`, placed immediately after the `openDashboardTab` function and its `window.openDashboardTab = openDashboardTab;` export (around line 740). Implementation:

   ```javascript
   function openAppPageTab(appId, pageId, label) {
     var tabKey = 'app-page:' + appId + ':' + pageId;
     var dv = window._dockview;
     if (!dv) return;

     var existing = dv.panels.find(function(p) { return p.id === tabKey; });
     if (existing) { existing.api.setActive(); return; }

     if (!window._tabMeta) window._tabMeta = {};
     window._tabMeta[tabKey] = { label: label || 'App Page', dirty: false };

     dv.api.addPanel({
       id: tabKey,
       component: 'special-panel',
       params: { specialType: 'app-page', appId: appId, pageId: pageId, isView: false, isSpecial: true },
       title: label || 'App Page'
     });
   }
   window.openAppPageTab = openAppPageTab;
   ```

2. Add `specialType === 'app-page'` handling to `frontend/static/js/workspace-layout.js` in the special-panel factory's `init` function. Add this block after the `generic-view` block (around line 243) and before the final `htmx.ajax` call:

   ```javascript
   // App page panels — load from browser apps sub-router
   if (st === 'app-page' && params.params.appId && params.params.pageId) {
     url = '/browser/apps/' + params.params.appId + '/page/' + params.params.pageId;
   }
   ```

3. Verify: `grep -c "openAppPageTab" frontend/static/js/workspace.js` should return at least 2 (definition + window export).

4. Verify: `grep -c "app-page" frontend/static/js/workspace-layout.js` should return at least 1.

## Must-Haves

- [ ] `openAppPageTab(appId, pageId, label)` defined in workspace.js
- [ ] `window.openAppPageTab` exported for global access (used by onclick in explorer template)
- [ ] Tab key format `app-page:{appId}:{pageId}` prevents duplicate tabs for same page
- [ ] Existing panel activated if already open (dedup check)
- [ ] `specialType: 'app-page'` routed to `/browser/apps/{appId}/page/{pageId}` in workspace-layout.js

## Verification

- `grep -c "openAppPageTab" frontend/static/js/workspace.js` → at least 2
- `grep -c "app-page" frontend/static/js/workspace-layout.js` → at least 1
- No syntax errors in JS (no build step; visual review of placement)

## Inputs

- `frontend/static/js/workspace.js` — `openDashboardTab()` at ~line 721 as pattern reference
- `frontend/static/js/workspace-layout.js` — special-panel factory at ~line 206 with existing specialType dispatch

## Observability Impact

- **New signal:** `window.openAppPageTab` is globally accessible — call it from the browser console with `openAppPageTab('test-app', 'main', 'Test')` to verify tab creation without needing the sidebar.
- **Tab key format:** `app-page:{appId}:{pageId}` is visible in dockview panel IDs — inspect `window._dockview.panels.map(p => p.id)` to see open app-page tabs.
- **Failure visibility:** If the backend route is missing or returns an error, the htmx swap into the panel element will show the error response body directly in the tab content area (standard htmx error surfacing for special-panel components).
- **No new logs or persisted state** — this is client-side tab wiring only.

## Expected Output

- `frontend/static/js/workspace.js` — modified: `openAppPageTab()` function + window export added after `openDashboardTab()`
- `frontend/static/js/workspace-layout.js` — modified: `app-page` specialType case added in special-panel factory
