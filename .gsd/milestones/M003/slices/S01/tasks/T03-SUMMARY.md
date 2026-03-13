---
id: T03
parent: S01
milestone: M003
provides:
  - Mode-aware refreshNavTree() using /browser/explorer/tree?mode={currentMode}
  - Selection clearing and lastClickedLeaf reset on explorer mode switch
  - Explorer mode persistence in localStorage key sempkm_explorer_mode
  - Mode restore on page load with htmx trigger for non-default modes
  - Command palette type-create entries preserved across mode switches
key_files:
  - frontend/static/js/workspace.js
key_decisions:
  - "_addTypeCreateEntries early-returns when no type nodes exist in DOM, preserving cached entries from the last by-type render rather than wiping them"
  - "initExplorerMode() added as a dedicated init function called from init(), keeping mode state management isolated"
patterns_established:
  - "Explorer mode init pattern: addEventListener('change') for clear+persist, then localStorage restore with option validation and conditional htmx.trigger"
  - "EXPLORER_MODE_KEY constant ('sempkm_explorer_mode') used consistently for localStorage"
observability_surfaces:
  - "localStorage.getItem('sempkm_explorer_mode') — shows persisted explorer mode"
  - "document.getElementById('explorer-mode-select').value — shows active dropdown mode"
  - "document.querySelectorAll('.tree-leaf.selected').length — shows selection count (should be 0 after mode switch)"
duration: 1 session
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: Update refreshNavTree, clear selection on mode switch, persist mode

**Made refreshNavTree() mode-aware, added selection clearing on mode switch, and persisted/restored explorer mode in localStorage.**

## What Happened

1. **refreshNavTree() was already mode-aware** — T02 had already updated it to read `#explorer-mode-select` and use `/browser/explorer/tree?mode=` URL. Verified this was correct and complete.

2. **Added initExplorerMode() function** with:
   - `change` event listener on `#explorer-mode-select` that calls `clearSelection()`, resets `lastClickedLeaf = null`, and persists mode to localStorage
   - Mode restore logic on page load: reads `sempkm_explorer_mode` from localStorage, validates it against dropdown options, sets the value, and triggers `htmx.trigger(dropdown, 'change')` if non-default

3. **Extended htmx:afterSwap listener** to call `_addTypeCreateEntries(ninja)` when the swap target is `#explorer-tree-body`, ensuring command palette entries are refreshed after any tree swap (dropdown change or refreshNavTree).

4. **Fixed _addTypeCreateEntries** to early-return when no `.tree-node[data-type-iri]` elements exist in the DOM. Without this fix, switching to non-by-type modes would strip all type-create entries from the command palette (the function filtered them out then found no nodes to repopulate from). The fix preserves cached entries from the last by-type render.

## Verification

**Browser verification (all PASS):**
- Opened workspace, default mode is "By Type" with nav tree visible
- Ctrl+click-selected 2 objects → badge shows "2 selected"
- Switched to "By Tag" → selection cleared (0 selected), badge hidden, placeholder content visible, localStorage shows "by-tag"
- Reloaded page → dropdown shows "By Tag", placeholder content loads (mode persisted and restored)
- Called `refreshNavTree()` from console in "By Tag" mode → placeholder reloads (not by-type tree)
- Switched to "By Type", called `refreshNavTree()` → type nodes reload correctly
- Checked `ninja.data.filter(d => d.id.startsWith('create-type-'))` after switching to non-by-type mode → 4 entries preserved
- Switched to "Hierarchy" → localStorage shows "hierarchy", selection cleared, create entries preserved

**Unit tests:**
- `docker compose exec api python -m pytest tests/test_explorer_modes.py -v` — 8/8 passed

**E2E tests:**
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — all 5 tests are `test.fixme` stubs (for T04), E2E test stack (port 3901) not running

**Slice-level verification status:**
- ✅ Unit tests: 8/8 passed
- ⏭️ E2E tests: stubs only (T04 will implement), test stack unavailable
- ✅ Manual curl: endpoints respond correctly (verified via browser; direct curl gets auth redirect as expected)

## Diagnostics

- `localStorage.getItem('sempkm_explorer_mode')` — shows persisted mode
- `document.getElementById('explorer-mode-select').value` — shows active mode
- Browser network tab shows request URL for `refreshNavTree()` calls (verifies correct mode param)
- If mode restore fails, dropdown falls back to "By Type" (server-rendered default)

## Deviations

- **Fixed _addTypeCreateEntries early-return**: The task plan assumed type-create entries would be "stale-cached in ninja.data from the last by-type render." In reality, the function actively removes all `create-type-*` entries before repopulating, so switching to a non-by-type mode wiped them. Added an early-return guard when `typeNodes.length === 0`.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js` — Added `initExplorerMode()` function with change listener (clearSelection + lastClickedLeaf reset + localStorage persist) and mode restore on init; extended htmx:afterSwap to call `_addTypeCreateEntries` on tree body swaps; fixed `_addTypeCreateEntries` to preserve entries when no type nodes exist
