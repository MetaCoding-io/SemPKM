# T01: 30-dockview-phase-a-migration 01

**Slice:** S30 — **Milestone:** M001

## Description

Replace the Split.js/custom-drag editor-group system in workspace-layout.js with dockview-core 4.11.0.
This is the largest single change in Phase 30 and the prerequisite for all other plans.

Purpose: Deliver native drag-to-reorder, group splitting, and serialized layout persistence while eliminating
the ~400 lines of custom drag-drop and tab-bar-rendering code that are now replaced by dockview.

Output:
- workspace-layout.js rewritten: recreateGroupSplit() deleted, DockviewComponent init added, drag system deleted,
  WorkspaceLayout class retained as a tab metadata sidecar only.
- workspace.html: static group-1 HTML removed, CDN links added for dockview-core 4.11.0.
- dockview-sempkm-bridge.css: "STATUS: Pattern file" comment removed — file is now loaded by workspace.html.

## Must-Haves

- [ ] "Opening an object from the nav tree creates a tab inside a dockview panel (not the old .editor-group DOM)"
- [ ] "Dragging a tab to a new position reorders it using dockview native drag (no custom HTML5 drag events)"
- [ ] "Reloading the browser restores the previous panel group geometry via dockview.fromJSON() from sessionStorage"
- [ ] "sempkm:tab-activated fires with { tabId, groupId, isObjectTab } when switching tabs in dockview"
- [ ] "sempkm:tabs-empty fires when the last object tab is closed"
- [ ] "CodeMirror editor is visible and sized correctly after switching away from its tab and back"

## Files

- `frontend/static/js/workspace-layout.js`
- `backend/app/templates/browser/workspace.html`
- `frontend/static/css/dockview-sempkm-bridge.css`
