---
id: T01
parent: S04
milestone: M004
provides:
  - showTypePicker always creates a fresh dockview panel instead of overwriting existing tab
  - objectCreated handler cleans up temp panel after real object tab opens
key_files:
  - frontend/static/js/workspace.js
key_decisions:
  - Temp panel IDs use `__new-object-{timestamp}` prefix for easy identification in panel list
  - Cleanup happens inside the existing setTimeout callback (after openTab) rather than a separate listener
patterns_established:
  - Module-level `_newObjectPanelId` tracker variable for temp panel lifecycle
observability_surfaces:
  - console.debug('[workspace] showTypePicker: created temp panel', panelId) logs temp panel creation
  - Orphaned temp panels visible as "New Object" tabs in tab bar (obvious failure signal)
  - window._dockview.panels shows all panels; temp panels identifiable by __new-object- prefix
duration: 20m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Fix showTypePicker to always create a fresh panel and clean up on object creation

**Refactored `showTypePicker()` to always create a new dockview panel and added temp panel cleanup in `objectCreated` handler.**

## What Happened

The bug: `showTypePicker()` only created a new panel when the workspace was completely empty (`!editorArea`). Otherwise it swapped the type picker HTML directly into the active editor area, destroying whatever content was there.

Three changes in `frontend/static/js/workspace.js`:

1. **Added `_newObjectPanelId` tracker** (line ~1016) — module-level variable near other state vars to track the current temporary panel ID.

2. **Refactored `showTypePicker()`** — Removed the `if (!editorArea)` conditional. The dockview `addPanel` block now runs unconditionally when `window._dockview` exists. Creates a panel with `id: '__new-object-' + Date.now()`, stores it in `_newObjectPanelId`, and adds a `console.debug` log. Falls back to `document.getElementById('editor-area-group-1')` only when dockview is unavailable.

3. **Updated `objectCreated` handler** — After `openTab()` in the existing `setTimeout` callback, added cleanup: if `_newObjectPanelId` is set, calls `closeTab(_newObjectPanelId)` and resets the tracker to `null`.

## Verification

Browser verification (full flow):
- ✅ Opened workspace → activated "Knowledge Management" tab → pressed Alt+N
- ✅ Old "Knowledge Management" tab remained in tab bar with content intact
- ✅ New "New Object" tab created with type picker ("Create New Object")
- ✅ Panel count went from 3 → 4 (new `__new-object-*` panel added)
- ✅ Switched back to Knowledge Management tab — all content (Label, Definition, Tags, etc.) preserved
- ✅ Created a "Test Project for Tab Fix" via the type picker form
- ✅ After 1.5s delay: temp "New Object" panel closed, real "Test Project for Tab Fix" tab opened in edit mode
- ✅ `hasNewObjectPanel: false` confirmed — no orphaned temp panel
- ✅ Console log present: `[workspace] showTypePicker: created temp panel __new-object-1773498627490`

Slice-level verification (partial — T01 of 2):
- Manual browser check: PASSED (all flows verified above)
- E2E test: NOT YET (T02 creates the E2E test)

## Diagnostics

- `console.debug('[workspace] showTypePicker: created temp panel', panelId)` logs every temp panel creation
- `window._dockview.api.panels.map(p => p.id)` in browser console — temp panels have `__new-object-` prefix
- If cleanup fails, orphaned "New Object" tab remains visible in tab bar — obvious visual signal

## Deviations

None.

## Known Issues

- Right pane sections (Relations, Lint, Comments) show `{"detail":"Invalid IRI"}` when the temp "New Object" panel is active — expected since the temp panel ID (`__new-object-*`) is not a valid object IRI. This clears when the real object tab opens.

## Files Created/Modified

- `frontend/static/js/workspace.js` — Added `_newObjectPanelId` tracker, refactored `showTypePicker()` to always create fresh panel, updated `objectCreated` handler to close temp panel
