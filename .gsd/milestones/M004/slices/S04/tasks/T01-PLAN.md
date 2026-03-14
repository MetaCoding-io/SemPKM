---
estimated_steps: 4
estimated_files: 1
---

# T01: Fix showTypePicker to always create a fresh panel and clean up on object creation

**Slice:** S04 — Create-New-Object Tab Fix
**Milestone:** M004

## Description

The core bug fix. `showTypePicker()` (workspace.js:1631) currently gets the active editor area and does an htmx swap of `/browser/types` directly into it, destroying whatever content was there. The only time a new panel is created is when the workspace is completely empty (`!editorArea`). This task makes the new-panel creation unconditional and adds cleanup of the temporary panel when the real object tab opens.

## Steps

1. **Add module-level tracker variable** — near the top of the workspace.js IIFE (near other state vars like `lastClickedLeaf`), add `var _newObjectPanelId = null;` to track the current temporary panel ID.

2. **Refactor `showTypePicker()` to always create a new panel** — Remove the `if (!editorArea)` conditional around the `addPanel` block. The flow becomes:
   - If dockview exists: always create a new panel with `id: '__new-object-' + Date.now()`, `component: 'empty'`, `title: 'New Object'`. Register in `_tabMeta`. Store the panel ID in `_newObjectPanelId`.
   - Get the new panel's editor area via `getActiveEditorArea()` (the new panel is active immediately after `addPanel`).
   - If no dockview: fall back to `document.getElementById('editor-area-group-1')` (existing fallback).
   - Proceed with htmx ajax swap into the editor area as before.

3. **Update `objectCreated` handler to close temp panel** — Inside the `setTimeout` callback (after `openTab(detail.iri, label, 'edit')`), add: if `_newObjectPanelId` is set, call `closeTab(_newObjectPanelId)` and reset `_newObjectPanelId = null`. This ensures the temp panel is cleaned up after the real object tab opens and the success message has been visible.

4. **Verify in browser** — Start Docker stack, open workspace, open an existing object, press Alt+N, confirm old tab survives. Create an object, confirm temp tab closes and real tab opens.

## Must-Haves

- [ ] `showTypePicker()` always creates a new dockview panel (not just when workspace is empty)
- [ ] Temp panel ID tracked in `_newObjectPanelId`
- [ ] `objectCreated` handler closes temp panel after opening real object tab
- [ ] Tutorial `startCreateObjectTour()` still works (no changes needed — it calls `showTypePicker()` which now creates a fresh panel, and `getActiveEditorArea()` returns the new panel's element)
- [ ] htmx target resolution still works (`hx-target="closest .group-editor-area"` matches the new panel's element)

## Verification

- Open workspace in browser → open a seed object tab → press Alt+N → old tab still in tab bar, type picker in new tab
- Create an object from type picker → temp "New Object" tab closes, real object tab opens
- Both htmx swaps (type picker load, form submit) land inside the temp panel, not the old tab

## Observability Impact

- Signals added/changed: None (this is a JS-only UI fix, no new logging beyond optional console.debug)
- How a future agent inspects this: `window._dockview.panels.map(p => p.id)` in browser console — temp panels identifiable by `__new-object-` prefix; `window._newObjectPanelId` is `null` when no creation flow is active (note: variable is inside IIFE, not globally accessible — use panel list instead)
- Failure state exposed: if cleanup fails, an orphaned "New Object" empty tab remains visible in the tab bar — obvious visual signal

## Inputs

- `frontend/static/js/workspace.js` — current `showTypePicker()` at line ~1631, `objectCreated` handler at line ~2271
- S04 research analysis of the bug root cause and fix approach

## Expected Output

- `frontend/static/js/workspace.js` — modified `showTypePicker()` that always creates a fresh panel; modified `objectCreated` handler that closes the temp panel
