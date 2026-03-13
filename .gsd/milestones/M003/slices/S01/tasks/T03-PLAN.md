---
estimated_steps: 5
estimated_files: 3
---

# T03: Update refreshNavTree, clear selection on mode switch, persist mode

**Slice:** S01 — Explorer Mode Infrastructure
**Milestone:** M003

## Description

Update `refreshNavTree()` in `workspace.js` to be mode-aware (reads current dropdown value and hits the mode endpoint), add selection clearing on mode switch, persist mode choice in localStorage, and ensure command palette type-create entries remain available across all modes. This task closes the backwards-compatibility and state-management requirements.

## Steps

1. **Make `refreshNavTree()` mode-aware:**
   - Read `document.getElementById('explorer-mode-select')` value; default to `'by-type'` if element doesn't exist
   - Change the htmx.ajax target URL from `/browser/nav-tree` to `/browser/explorer/tree?mode={currentMode}`
   - Keep the htmx.ajax target as `#section-objects .explorer-section-body` (now has `id="explorer-tree-body"`)
   - After swap callback: call `lucide.createIcons()` AND `_addTypeCreateEntries(ninja)` as before
   - The old `/browser/nav-tree` endpoint still exists as a fallback but is no longer the primary path

2. **Clear selection on mode switch:**
   - Add event listener in the workspace init block: `document.getElementById('explorer-mode-select').addEventListener('change', function() { clearSelection(); })`
   - This fires before the htmx swap so selection state is cleaned up proactively
   - Also reset `lastClickedLeaf = null` to prevent stale shift-click range anchors

3. **Persist mode in localStorage:**
   - On mode change: `localStorage.setItem('sempkm_explorer_mode', this.value)`
   - On workspace init (in the existing DOMContentLoaded or workspace init block):
     - Read `localStorage.getItem('sempkm_explorer_mode')`
     - If value exists and matches a valid option in the dropdown, set `dropdown.value = storedMode`
     - If stored mode differs from default ('by-type'), trigger `htmx.trigger(dropdown, 'change')` to load the stored mode's tree
     - If stored mode is 'by-type', do nothing — the server-rendered tree is already correct

4. **Ensure command palette always has type-create entries:**
   - After htmx swap for ANY mode (not just by-type), call `_addTypeCreateEntries(ninja)` in the post-swap handler
   - Type-create entries are populated from the type nodes in the DOM; when not in by-type mode, we need to fetch them separately
   - Solution: `_addTypeCreateEntries` already queries `#section-objects .tree-node[data-type-iri]` — if those don't exist (non-by-type mode), the entries are already stale-cached in ninja.data from the last by-type render, which is acceptable. No additional fetch needed.

5. **Handle htmx afterSwap for selection re-apply:**
   - The existing `afterSwap` handler in workspace.js (if present) re-applies `.selected` class to tree-leaf elements matching `selectedIris` — since we clear selection on mode switch, this is moot for mode changes
   - Verify the `htmx:afterSwap` event on `#explorer-tree-body` calls `lucide.createIcons()` — this may already be handled by the `hx-on::after-swap` attribute added in T02, but the `refreshNavTree` path also needs it

## Must-Haves

- [ ] `refreshNavTree()` uses `/browser/explorer/tree?mode={currentMode}` URL
- [ ] `refreshNavTree()` falls back to old URL if dropdown element doesn't exist
- [ ] `clearSelection()` called on mode dropdown change event
- [ ] `lastClickedLeaf` reset to null on mode switch
- [ ] Mode persisted in `localStorage` key `sempkm_explorer_mode`
- [ ] Stored mode restored on page load, triggering htmx load if non-default
- [ ] Command palette type-create entries remain available after mode switch
- [ ] `lucide.createIcons()` called after every tree swap path (refreshNavTree + dropdown change)

## Verification

- Open workspace, switch to "By Tag" mode, reload page → dropdown shows "By Tag", placeholder content visible
- Call `refreshNavTree()` from browser console while in "By Tag" mode → placeholder reloads (not by-type tree)
- Switch to by-type, call `refreshNavTree()` → types reload correctly
- Select 2 objects via Ctrl+click, switch mode → selection badge hidden, `selectedIris.size === 0`
- Open command palette (Alt+N or Ctrl+K) → "Create new..." entries visible regardless of current mode
- `localStorage.getItem('sempkm_explorer_mode')` reflects the last selected mode

## Observability Impact

- Signals added/changed: None — client-side only, no new server signals
- How a future agent inspects this: `localStorage.getItem('sempkm_explorer_mode')` shows persisted mode; `document.getElementById('explorer-mode-select').value` shows active mode; `window.selectedIris?.size` shows selection state
- Failure state exposed: If `refreshNavTree` fetches wrong URL, browser network tab shows the request URL; if mode restore fails, dropdown shows default "By Type" (safe fallback)

## Inputs

- `frontend/static/js/workspace.js` — current `refreshNavTree()` at line 1128, `clearSelection()` at line 1034, `selectedIris` at line 988
- `backend/app/templates/browser/workspace.html` — T02 added `#explorer-mode-select` and `#explorer-tree-body`
- T01 backend endpoint at `/browser/explorer/tree?mode={mode}` is deployed and working

## Expected Output

- `frontend/static/js/workspace.js` — `refreshNavTree()` mode-aware, change listener with `clearSelection()`, localStorage persist/restore
- `backend/app/templates/browser/workspace.html` — possible minor adjustment to init script block for mode restore
