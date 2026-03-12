# S30: Dockview Phase A Migration

**Goal:** Replace the Split.
**Demo:** Replace the Split.

## Must-Haves


## Tasks

- [x] **T01: 30-dockview-phase-a-migration 01** `est:2min`
  - Replace the Split.js/custom-drag editor-group system in workspace-layout.js with dockview-core 4.11.0.
This is the largest single change in Phase 30 and the prerequisite for all other plans.

Purpose: Deliver native drag-to-reorder, group splitting, and serialized layout persistence while eliminating
the ~400 lines of custom drag-drop and tab-bar-rendering code that are now replaced by dockview.

Output:
- workspace-layout.js rewritten: recreateGroupSplit() deleted, DockviewComponent init added, drag system deleted,
  WorkspaceLayout class retained as a tab metadata sidecar only.
- workspace.html: static group-1 HTML removed, CDN links added for dockview-core 4.11.0.
- dockview-sempkm-bridge.css: "STATUS: Pattern file" comment removed — file is now loaded by workspace.html.
- [x] **T02: 30-dockview-phase-a-migration 02** `est:3min`
  - Update workspace.js and object_tab.html to use the dockview API instead of the old WorkspaceLayout methods.
Plan 01 replaced the internals of workspace-layout.js; this plan updates the callers.

Purpose: Complete the migration so all tab operations (open, close, dirty-mark, type-icon push) go through
the dockview API and the _tabMeta sidecar.

Output:
- workspace.js: openTab(), openViewTab(), openSettingsTab(), openDocsTab(), closeTab(), markDirty(),
  markClean(), getActiveTabIri() all updated to use window._dockview and window._tabMeta.
- object_tab.html: typeIcon script updated to write into window._tabMeta instead of _workspaceLayout.groups.
- [x] **T03: 30-dockview-phase-a-migration 03** `est:~10min (CSS cleanup + browser verification across sessions)`
  - Remove obsolete CSS rules from workspace.css that were only needed for the old Split.js/custom-drag editor-group system.
Then verify the full dockview migration works end-to-end via a human checkpoint.

Purpose: Complete the cleanup so no dead code remains. Then verify that all five Phase 30 success criteria pass
in the live application before marking the phase complete.

Output:
- workspace.css with .editor-group, .group-tab-bar, .group-editor-area, .gutter-editor-groups, drag indicator,
  and right-edge-drop-zone rules removed.
- Human-verified end-to-end dockview panel behavior.

## Files Likely Touched

- `frontend/static/js/workspace-layout.js`
- `backend/app/templates/browser/workspace.html`
- `frontend/static/css/dockview-sempkm-bridge.css`
- `frontend/static/js/workspace.js`
- `backend/app/templates/browser/object_tab.html`
- `frontend/static/css/workspace.css`
