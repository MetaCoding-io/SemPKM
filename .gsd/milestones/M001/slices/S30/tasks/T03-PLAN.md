# T03: 30-dockview-phase-a-migration 03

**Slice:** S30 — **Milestone:** M001

## Description

Remove obsolete CSS rules from workspace.css that were only needed for the old Split.js/custom-drag editor-group system.
Then verify the full dockview migration works end-to-end via a human checkpoint.

Purpose: Complete the cleanup so no dead code remains. Then verify that all five Phase 30 success criteria pass
in the live application before marking the phase complete.

Output:
- workspace.css with .editor-group, .group-tab-bar, .group-editor-area, .gutter-editor-groups, drag indicator,
  and right-edge-drop-zone rules removed.
- Human-verified end-to-end dockview panel behavior.

## Must-Haves

- [ ] "User can open multiple object tabs and drag them to reorder or split into side-by-side groups using dockview native drag handles"
- [ ] "Workspace tab layout (group geometry) is automatically saved and restored after a browser reload"
- [ ] "Object tabs opened inside dockview panels continue to fire sempkm:tab-activated and sempkm:tabs-empty events"
- [ ] "CodeMirror and Cytoscape visualizations render correctly when their containing panel is shown after being hidden"
- [ ] "htmx attributes on content loaded inside dockview panels remain active after drag-to-new-group"
- [ ] "No old HTML5 drag event listeners (dragstart) remain in workspace-layout.js"
- [ ] "workspace.css contains no .editor-group, .group-tab-bar, or .gutter-editor-groups rules"

## Files

- `frontend/static/css/workspace.css`
