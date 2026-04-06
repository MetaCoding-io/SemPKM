# S02: Closed Tab Recovery

**Goal:** Add a closed-tab stack that captures panel metadata on close, and provide keyboard shortcut and command palette entry to reopen the last closed tab.
**Demo:** After this: Close a tab → Ctrl+Shift+T → tab reopens with same content. F1 → 'Reopen Closed Tab' → same result.

## Tasks
- [x] **T01: Added closed-tab recovery stack with Ctrl+Shift+T reopen and command palette entry** — Implement the closed-tab recovery stack and reopener.

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
  - Estimate: 30min
  - Files: frontend/static/js/workspace-layout.js, frontend/static/js/workspace.js
  - Verify: Start dev stack. Open /browser/. Open 3 object tabs. Close the last one. Press Ctrl+Shift+T → it reopens. Close a view tab, press Ctrl+Shift+T → view tab reopens. F1 → 'Reopen' → entry appears. Press Ctrl+Shift+T with no closed tabs → nothing happens, no error in console.
- [ ] **T02: E2E tests for closed tab recovery** — Write Playwright E2E tests proving closed tab recovery works.

1. Create e2e/tests/55-browser-history/closed-tab.spec.ts
2. Test cases:
   a. Open an object tab, close it, press Ctrl+Shift+T → tab reopens with same IRI
   b. Close 3 tabs in sequence, press Ctrl+Shift+T 3 times → all reopen in reverse order
   c. Press Ctrl+Shift+T with no closed tabs → no error, no new tab
   d. Close a tab, reopen it manually (click in explorer), then Ctrl+Shift+T → skips already-open tab
3. Use dockview.ts helpers for tab operations
  - Estimate: 20min
  - Files: e2e/tests/55-browser-history/closed-tab.spec.ts
  - Verify: cd e2e && npx playwright test tests/55-browser-history/closed-tab.spec.ts --headed
