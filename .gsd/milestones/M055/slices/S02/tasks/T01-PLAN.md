---
estimated_steps: 18
estimated_files: 2
skills_used: []
---

# T01: Closed-tab stack capture and reopen dispatch

Implement the closed-tab recovery stack and reopener.

1. In workspace-layout.js, add a module-level _closedTabStack array (max 20 entries)
2. Modify the onDidRemovePanel handler to accept the panel argument and capture metadata BEFORE _tabMeta is deleted:
   - Read panel.id, panel.params (component, isView, isSpecial, viewId, viewType, etc.), and _tabMeta[panel.id].label
   - Push { id, component: panel.params component type string, params: panel.params, label } onto _closedTabStack
   - If stack exceeds 20 entries, shift the oldest
3. Note: closeTab() in workspace.js deletes _tabMeta[objectIri] AFTER panel.api.close(). The onDidRemovePanel fires synchronously during close(). So _tabMeta should still be available. Verify this.
4. Create reopenClosedTab() function:
   - Pop from _closedTabStack. If empty, return.
   - Based on the component field, dispatch to the correct opener:
     - 'object-editor' → openTab(entry.id, entry.label)
     - 'view-panel' → openViewTab(entry.params.viewId, entry.label, entry.params.viewType)
     - 'special-panel' → call the specific openDocsTab/openCanvasTab/openSettingsTab based on entry.id pattern
     - Dashboard/workflow/app tabs → openDashboardTab/openWorkflowTab etc.
   - If the tab is already open (user reopened it manually), skip and try next entry
5. Export reopenClosedTab on window.SemPKM
6. In workspace.js initKeyboardShortcuts, add Ctrl+Shift+T handler that calls reopenClosedTab()
7. In workspace.js initCommandPalette, add 'Reopen Closed Tab' entry with handler calling reopenClosedTab()

## Inputs

- `frontend/static/js/workspace-layout.js (onDidRemovePanel, _tabMeta)`
- `frontend/static/js/workspace.js (openTab, openViewTab, initKeyboardShortcuts, initCommandPalette)`

## Expected Output

- `frontend/static/js/workspace-layout.js (modified — closed tab stack + reopen)`
- `frontend/static/js/workspace.js (modified — Ctrl+Shift+T + command palette entry)`

## Verification

Start dev stack. Open /browser/. Open 3 object tabs. Close the last one. Press Ctrl+Shift+T → it reopens. Close a view tab, press Ctrl+Shift+T → view tab reopens. F1 → 'Reopen' → entry appears. Press Ctrl+Shift+T with no closed tabs → nothing happens, no error in console.
