# T02: 30-dockview-phase-a-migration 02

**Slice:** S30 — **Milestone:** M001

## Description

Update workspace.js and object_tab.html to use the dockview API instead of the old WorkspaceLayout methods.
Plan 01 replaced the internals of workspace-layout.js; this plan updates the callers.

Purpose: Complete the migration so all tab operations (open, close, dirty-mark, type-icon push) go through
the dockview API and the _tabMeta sidecar.

Output:
- workspace.js: openTab(), openViewTab(), openSettingsTab(), openDocsTab(), closeTab(), markDirty(),
  markClean(), getActiveTabIri() all updated to use window._dockview and window._tabMeta.
- object_tab.html: typeIcon script updated to write into window._tabMeta instead of _workspaceLayout.groups.

## Must-Haves

- [ ] "Clicking a nav tree node opens a new dockview panel with the object content loaded via htmx"
- [ ] "Clicking the same node again focuses the existing panel (no duplicate tab created)"
- [ ] "The Settings and Docs tabs open in dockview panels via openSettingsTab() and openDocsTab()"
- [ ] "markDirty() and markClean() update the tab title metadata in window._tabMeta (not the old WorkspaceLayout.groups)"
- [ ] "getActiveTabIri() returns the panel ID of the currently active dockview panel"
- [ ] "object_tab.html pushes typeIcon into window._tabMeta without referencing window._workspaceLayout.groups"

## Files

- `frontend/static/js/workspace.js`
- `backend/app/templates/browser/object_tab.html`
