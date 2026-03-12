# T01: 14-split-panes-and-bottom-panel 01

**Slice:** S14 — **Milestone:** M001

## Description

Build the WorkspaceLayout foundation: a new workspace-layout.js module implementing the EditorGroup data model, Split.js destroy-and-recreate strategy, sessionStorage migration from old tab keys, and DOM restructure to support multiple editor groups. Wires workspace.js global functions to delegate to WorkspaceLayout and reassigns keyboard shortcuts.

Purpose: All subsequent Phase 14 work (tab DnD, bottom panel) depends on this multi-group DOM structure and state model existing.
Output: workspace-layout.js module, updated workspace.html DOM structure, updated workspace.css group styles, updated workspace.js delegation wiring.

## Must-Haves

- [ ] "User can split the editor into a second group via Ctrl+\\ or 'Split Right' context menu action"
- [ ] "Closing the last tab in a non-primary group removes that group and redistributes its tabs to the left neighbor"
- [ ] "All groups resize to equal proportional widths when a group is added or removed, with a 150ms animation"
- [ ] "Up to 4 editor groups can exist simultaneously, each with its own tab bar and editor area"
- [ ] "Existing single-group tab state migrates transparently from old sempkm_open_tabs storage to sempkm_workspace_layout"
- [ ] "Ctrl+1/2/3/4 focuses the corresponding editor group"

## Files

- `frontend/static/js/workspace-layout.js`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/workspace.html`
