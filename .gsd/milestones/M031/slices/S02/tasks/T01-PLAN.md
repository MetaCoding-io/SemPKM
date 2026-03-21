---
estimated_steps: 4
estimated_files: 2
skills_used: []
---

# T01: Enable multiple generic view instances as separate dockview tabs

**Slice:** S02 — Multiple View Instances + Saved Views Fix
**Milestone:** M031

## Description

Currently `openGenericViewTab()` in `workspace.js` uses a fixed tab ID `generic-view:{renderer}` (e.g. `generic-view:table`). This means clicking "Table View" twice just activates the existing tab — it's impossible to have two table views open simultaneously with different scopes. This task changes the tab ID scheme to allow multiple instances.

The key change: when a `scopeQuery` is provided, the tab ID becomes `generic-view:{renderer}:scope:{scopeQuery}` — this allows one tab per renderer+scope combination. When no scope is provided (user clicks from explorer sidebar), a counter-based ID like `generic-view:{renderer}:{timestamp}` is used, so each click opens a fresh instance.

Tab labels must differentiate instances: when a scope query is set, append the query name to the label (e.g. "Table View — My Projects"). When no scope is set, the default label "Table View" is used for the first instance, and "Table View (2)", etc. for subsequent ones.

## Steps

1. Open `frontend/static/js/workspace.js` and find `openGenericViewTab()` at ~line 3217. Change the tab ID scheme:
   - When `scopeQuery` is provided: `tabKey = 'generic-view:' + renderer + ':scope:' + scopeQuery`. Deduplicate by scope — if a tab with this exact key exists, activate it.
   - When `scopeQuery` is NOT provided: `tabKey = 'generic-view:' + renderer + ':' + Date.now()`. Never deduplicate — each call opens a fresh tab.
   - Add an optional third parameter `scopeLabel` (string) to differentiate the tab title. When set, use `label + ' — ' + scopeLabel`. For scope-based tabs, the caller should pass the query name.

2. Update the function signature to accept additional parameters while remaining backward-compatible:
   ```javascript
   function openGenericViewTab(renderer, scopeQuery, scopeLabel) {
   ```
   The function is exported via `window.openGenericViewTab = openGenericViewTab;` — all callers use positional args, so adding a third optional param is safe.

3. Update `frontend/static/js/workspace-layout.js` to verify the special-panel init for `generic-view` (around line 237) still works correctly. The init block reads `params.params.renderer`, `params.params.selectedType`, and `params.params.scopeQuery` — this should continue working unchanged since we're only changing the tab key, not the params structure.

4. Verify the explorer sidebar links in `backend/app/templates/browser/views_explorer.html` — these call `openGenericViewTab('table')`, `openGenericViewTab('card')`, `openGenericViewTab('graph')` with no scope. With the new scheme, each click will create a new tab. This is the desired behavior per VIEW-10.

## Must-Haves

- [ ] Tab IDs are unique per renderer+scope combination
- [ ] Two calls to `openGenericViewTab('table')` from explorer create two separate dockview panels
- [ ] A scoped call `openGenericViewTab('table', 'some-query-id')` deduplicates correctly — second call activates existing tab
- [ ] Tab labels differentiate: scoped tabs show query name, unscoped duplicates are distinguishable
- [ ] `workspace-layout.js` special-panel init continues to work (renderer, selectedType, scopeQuery extracted from params)
- [ ] Backward compatible — existing callers with 1 or 2 args still work

## Verification

- `grep -c "var tabKey = 'generic-view:' + renderer;" frontend/static/js/workspace.js` returns 0 (old fixed pattern removed)
- `grep -q "generic-view:.*scope:" frontend/static/js/workspace.js` confirms new scoped pattern exists
- `node -e "var fs=require('fs'); var code=fs.readFileSync('frontend/static/js/workspace.js','utf8'); if(code.includes('generic-view:') && code.includes('Date.now')) console.log('OK'); else process.exit(1);"` — prints OK
- Manual: search for `openGenericViewTab` — function accepts 3 params (renderer, scopeQuery, scopeLabel)

## Inputs

- `frontend/static/js/workspace.js` — contains `openGenericViewTab()` at ~line 3217 with fixed `tabKey = 'generic-view:' + renderer`
- `frontend/static/js/workspace-layout.js` — contains special-panel init at ~line 237 that reads `params.params.renderer`, `params.params.selectedType`, `params.params.scopeQuery`
- `backend/app/templates/browser/views_explorer.html` — sidebar links calling `openGenericViewTab('table')` etc.

## Observability Impact

- **Tab panel IDs in DevTools:** Panel IDs in dockview now show `generic-view:{renderer}:{timestamp}` for unscoped or `generic-view:{renderer}:scope:{queryId}` for scoped tabs. Inspectable via browser DevTools → Elements → dockview panel containers.
- **Tab labels in UI:** Duplicate unscoped tabs display a numeric suffix ("Table View (2)"); scoped tabs display the query name ("Table View — My Projects"). Visible directly in the dockview tab bar.
- **Failure visibility:** If a duplicate scoped tab ID were somehow generated, dockview itself would log a console error — this is the existing dockview behavior and no additional instrumentation is needed. Unscoped tabs use `Date.now()` which is monotonically unique under normal usage (same-millisecond calls are astronomically unlikely from user clicks).

## Expected Output

- `frontend/static/js/workspace.js` — `openGenericViewTab()` updated with unique tab ID scheme and optional `scopeLabel` parameter
- `frontend/static/js/workspace-layout.js` — verified unchanged or minimally adjusted if needed for new tab ID format
