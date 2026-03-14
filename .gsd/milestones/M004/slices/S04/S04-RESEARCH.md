# S04: Create-New-Object Tab Fix — Research

**Date:** 2026-03-14

## Summary

The "Create New Object" flow currently overwrites the active tab's content instead of opening a fresh dockview tab. The root cause is in `showTypePicker()` (workspace.js:1631): it gets the active editor area via `window.getActiveEditorArea()` and does an htmx swap of `/browser/types` directly into it. If a tab is already open (e.g. viewing an object), that tab's content is destroyed. The only time a new tab is created is when the workspace is completely empty (`!editorArea`).

The fix is straightforward: `showTypePicker()` should always create a new dockview panel (with a unique `__new-object-{timestamp}` ID and an `empty` component), make it active, then load the type picker into that fresh panel's editor area. When the object is created, the `objectCreated` event handler already calls `openTab()` which creates the real object tab — but the orphaned `__new-object-*` panel must be cleaned up. This matches the existing pattern for special tabs (ontology, canvas, VFS) which always `addPanel` first, then load content.

## Recommendation

**Approach: Always create a fresh "New Object" panel, then load type picker into it. Clean up the temporary panel after creation completes.**

1. Modify `showTypePicker()` to always create a new dockview panel (not just when empty), load type picker into it
2. Track the temporary panel ID so the `objectCreated` handler can close it before opening the real object tab
3. The type picker's `hx-target="closest .group-editor-area"` and the object form's identical target continue to work because they target the DOM ancestor — which is the new panel's `element`

Alternative considered: Making the type picker + create form a "special panel" component. This would be cleaner architecturally but changes the component factory and is over-engineering for a bug fix. The current htmx swap pattern works fine once the target is a fresh panel.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Creating dockview panels | `dv.api.addPanel()` with `component: 'empty'` | Already used on line 1640 for the empty-workspace case |
| Panel cleanup | `panel.api.close()` via `closeTab()` | Already used throughout workspace.js |
| Tab metadata | `window._tabMeta[id]` sidecar | Standard pattern for all tab types |

## Existing Code and Patterns

- `frontend/static/js/workspace.js:1631-1662` — `showTypePicker()` — **the function to fix**. Currently gets active editor area and swaps into it. Only creates a new panel when workspace is empty.
- `frontend/static/js/workspace.js:80-110` — `openTab()` — creates a dockview panel for an object. Pattern to follow for dedup check (`panels.find`) and metadata registration.
- `frontend/static/js/workspace.js:1637-1645` — Empty-workspace new panel creation — already uses `__new-object-{timestamp}` ID and `component: 'empty'`. This exact pattern just needs to run **always**, not only when `!editorArea`.
- `frontend/static/js/workspace.js:2269-2280` — `objectCreated` event handler — opens the real object tab after 1500ms delay. Needs to also close the temporary `__new-object-*` panel.
- `frontend/static/js/workspace-layout.js:144-230` — `createComponentFn` — the dockview component factory. The `empty` component fallback (line 228) returns `{ element: el, init: function () {} }` — a blank `.group-editor-area` div. Perfect for the type picker's `hx-target="closest .group-editor-area"`.
- `backend/app/templates/browser/type_picker.html` — Type picker template. Uses `hx-target="closest .group-editor-area"` on type cards — no changes needed since the new panel's element has this class.
- `backend/app/templates/forms/object_form.html:60` — Object create form also uses `hx-target="closest .group-editor-area"` — stays inside the same panel, no changes needed.
- `frontend/static/js/tutorials.js:172-213` — `startCreateObjectTour()` calls `window.showTypePicker()` — must continue to work. Tour uses `getActiveEditorArea()` to detect the swap target, so it will naturally pick up the new panel.
- `backend/app/templates/browser/workspace.html:50` — Plus button in nav tree opens command palette (not `showTypePicker()` directly). Command palette entry calls `showTypePicker()`.

## Constraints

- **Panel ID uniqueness**: Dockview requires unique panel IDs. Using `__new-object-{Date.now()}` is safe — collision requires two calls in the same millisecond.
- **htmx target resolution**: Both type picker and object form use `hx-target="closest .group-editor-area"`. The dockview `createComponentFn` adds this class to every panel's root element. No template changes needed.
- **objectCreated timing**: The `objectCreated` handler has a 1500ms `setTimeout` before calling `openTab()`. The temporary panel should be closed inside this same callback (after `openTab`), not before — so the success message remains visible.
- **Tutorial compatibility**: `startCreateObjectTour()` calls `window.showTypePicker()` and then listens for `htmx:afterSwap` on the active editor area. The tour's `afterSwapHandler` checks `e.detail.target` identity against `getActiveEditorArea()`. Since the new panel becomes active immediately after `addPanel`, `getActiveEditorArea()` returns the new panel's element — the tour continues to work.
- **Layout persistence**: Dockview serializes layout to `localStorage`. Temporary `__new-object-*` panels will appear in saved layouts if the user closes the browser mid-creation. This is already the case today (empty-workspace path). Acceptable — these panels are harmless empty tabs.

## Common Pitfalls

- **Overwriting dirty tabs** — The current bug: user is editing an object, hits Alt+N, and the edit form is destroyed with unsaved changes. The fix eliminates this entirely since the type picker always goes into a fresh panel.
- **Orphaned temporary panels** — If user opens type picker but never creates an object (navigates away, closes picker), the `__new-object-*` panel stays open. This is acceptable — it shows as an empty "New Object" tab that the user can close manually. The `objectCreated` handler cleans up on the happy path.
- **Multiple type pickers** — If user presses Alt+N twice, two `__new-object-*` panels are created. This is fine — each gets a unique ID. Only the most recent one's ID needs tracking for cleanup. Could optionally reuse an existing `__new-object-*` panel if one is already active (nice-to-have, not required).

## Open Risks

- **E2E test coverage**: No existing E2E test for the "create new object" flow that specifically verifies tab preservation. S04's UAT should include: (1) open an object tab, (2) hit "New Object", (3) verify old tab still exists with its content, (4) create the object, (5) verify new object tab opens and temporary tab closes. An E2E spec is optional for this low-risk slice but would be valuable.
- **Tutorial breakage**: The `startCreateObjectTour` listens for `htmx:afterSwap` on `getActiveEditorArea()`. If the new panel's element hasn't been registered in dockview's active panel tracking by the time the htmx swap fires, the target check could fail. Dockview's `addPanel` is synchronous, so `getActiveEditorArea()` should return the new element immediately — but this should be verified in browser.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| dockview-core | none found | N/A — vanilla JS API, well-documented in codebase |
| htmx | none found | N/A — patterns already established in codebase |

## Sources

- `showTypePicker()` function analysis (source: `frontend/static/js/workspace.js:1631-1662`)
- Dockview component factory (source: `frontend/static/js/workspace-layout.js:144-230`)
- Type picker template (source: `backend/app/templates/browser/type_picker.html`)
- Object create form (source: `backend/app/templates/forms/object_form.html:55-66`)
- objectCreated event handler (source: `frontend/static/js/workspace.js:2269-2280`)
- Tutorial integration (source: `frontend/static/js/tutorials.js:170-220`)
