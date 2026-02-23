# Editor Groups Data Model Design

Design document for Phase 14's editor groups feature. This is DESIGN ONLY -- no implementation.

## 1. Problem Statement

Split.js has no dynamic pane API -- you cannot add/remove panes after initialization. To support VS Code-style editor groups (split right, up to 4 groups), we need a data model that drives Split.js destruction and recreation when the group count changes.

Currently, the workspace has a single `#editor-area` containing one tab bar and one content area. Editor groups require multiple independent editor areas, each with their own tab bar, that can be split horizontally within the `#editor-pane`.

## 2. WorkspaceLayout Class Design

```
WorkspaceLayout {
  groups: EditorGroup[]     // 1-4 groups
  activeGroupId: string     // Currently focused group

  addGroup(): string        // Returns new group ID; recreates Split.js
  removeGroup(id): void     // Removes group; redistributes its tabs; recreates Split.js
  getGroup(id): EditorGroup
  serialize(): object       // For sessionStorage persistence
  static restore(data): WorkspaceLayout
}

EditorGroup {
  id: string                // Unique group identifier
  tabs: Tab[]               // Ordered tab list
  activeTabId: string       // Currently visible tab in this group
  size: number              // Percentage width (Split.js sizes array)

  addTab(tab): void
  removeTab(tabId): void
  moveTab(tabId, toGroup): void  // Cross-group tab movement
}

Tab {
  id: string                // Tab identifier (object IRI or view:specIri)
  label: string
  dirty: boolean
  isView: boolean
  viewType?: string
  viewId?: string
}
```

### Key Behaviors

- `addGroup()`: Creates a new empty group, recalculates sizes (equal distribution), destroys and recreates the horizontal Split.js instance.
- `removeGroup(id)`: Moves all tabs from the removed group to the adjacent group (prefer left neighbor), destroys and recreates Split.js.
- `moveTab(tabId, toGroup)`: Removes tab from source group, adds to target group. If source group becomes empty, it is auto-removed.
- Maximum 4 groups enforced in `addGroup()`.

## 3. Split.js Recreation Strategy

When groups change (add/remove):

1. Save current state (all group tabs, sizes, active tabs)
2. Destroy current horizontal Split.js instance via cleanup registry
3. Create/remove DOM containers for groups
4. Recreate Split.js with new container array and calculated sizes
5. Restore tab content in each group via htmx

### DOM Structure Change

**Current (single group):**
```html
<div id="editor-pane">
  <div id="tab-bar">...</div>
  <div id="editor-area">...</div>
</div>
```

**With editor groups:**
```html
<div id="editor-pane">
  <div class="editor-group" id="group-1">
    <div class="group-tab-bar" id="tab-bar-group-1">...</div>
    <div class="group-editor-area" id="editor-area-group-1">...</div>
  </div>
  <!-- Split.js gutter inserted here -->
  <div class="editor-group" id="group-2">
    <div class="group-tab-bar" id="tab-bar-group-2">...</div>
    <div class="group-editor-area" id="editor-area-group-2">...</div>
  </div>
</div>
```

### Recreation Pseudocode

```javascript
function recreateGroupSplit() {
  // 1. Destroy existing horizontal split
  if (groupSplitInstance) {
    groupSplitInstance.destroy();
    groupSplitInstance = null;
  }

  // 2. Build DOM containers
  var editorPane = document.getElementById('editor-pane');
  editorPane.innerHTML = '';
  layout.groups.forEach(function(group) {
    var div = createGroupDOM(group);
    editorPane.appendChild(div);
  });

  // 3. Recreate Split.js
  var selectors = layout.groups.map(function(g) { return '#' + g.id; });
  var sizes = layout.groups.map(function(g) { return g.size; });

  if (selectors.length > 1) {
    groupSplitInstance = Split(selectors, {
      sizes: sizes,
      minSize: 200,
      gutterSize: 5,
      cursor: 'col-resize'
    });

    // Register cleanup
    registerCleanup('editor-pane', function() {
      groupSplitInstance.destroy();
    });
  }

  // 4. Restore content in each group
  layout.groups.forEach(function(group) {
    if (group.activeTabId) {
      loadTabInGroup(group.id, group.activeTabId);
    }
  });
}
```

## 4. SessionStorage Schema

```json
{
  "groups": [
    {
      "id": "group-1",
      "tabs": [
        {"id": "urn:example:obj1", "label": "Object 1", "dirty": false, "isView": false},
        {"id": "urn:example:obj3", "label": "Object 3", "dirty": true, "isView": false}
      ],
      "activeTabId": "urn:example:obj1",
      "size": 50
    },
    {
      "id": "group-2",
      "tabs": [
        {"id": "urn:example:obj2", "label": "Object 2", "dirty": false, "isView": false},
        {"id": "view:urn:example:graph1", "label": "Knowledge Graph", "dirty": false, "isView": true, "viewType": "graph", "viewId": "urn:example:graph1"}
      ],
      "activeTabId": "urn:example:obj2",
      "size": 50
    }
  ],
  "activeGroupId": "group-1"
}
```

**Storage key:** `sempkm_workspace_layout`

## 5. Migration from Current Tab State

Current sessionStorage keys used by workspace.js:
- `sempkm_open_tabs` -- array of tab objects
- `sempkm_active_tab` -- IRI of active tab

### Migration Path

On first load with new code:

1. Check if `sempkm_workspace_layout` exists. If yes, use it (already migrated).
2. Read `sempkm_open_tabs` and `sempkm_active_tab`.
3. Create a single group (`group-1`) containing all existing tabs.
4. Set `activeGroupId` to `group-1`.
5. Set `group-1.activeTabId` to the value of `sempkm_active_tab`.
6. Set `group-1.size` to 100 (full width, single group).
7. Save as `sempkm_workspace_layout`.
8. Delete old keys (`sempkm_open_tabs`, `sempkm_active_tab`).

```javascript
function migrateTabState() {
  if (sessionStorage.getItem('sempkm_workspace_layout')) return; // already migrated

  var oldTabs = JSON.parse(sessionStorage.getItem('sempkm_open_tabs') || '[]');
  var oldActive = sessionStorage.getItem('sempkm_active_tab');

  var layout = {
    groups: [{
      id: 'group-1',
      tabs: oldTabs,
      activeTabId: oldActive || (oldTabs.length > 0 ? oldTabs[0].iri : null),
      size: 100
    }],
    activeGroupId: 'group-1'
  };

  sessionStorage.setItem('sempkm_workspace_layout', JSON.stringify(layout));
  sessionStorage.removeItem('sempkm_open_tabs');
  sessionStorage.removeItem('sempkm_active_tab');
}
```

## 6. Interaction with Cleanup Registry

Each editor group registers its own Split.js vertical split (form/editor) in the cleanup registry using the pattern established in plan 10-03. The horizontal Split.js between groups is managed by WorkspaceLayout and destroyed/recreated on group changes.

### Cleanup Hierarchy

1. **Horizontal group split** (managed by WorkspaceLayout): registered under `editor-pane` ID.
2. **Vertical form/editor splits** (per tab, existing pattern): registered under `object-split-{safe_id}` ID.
3. **CodeMirror instances** (per tab): registered under `body-editor-{safe_id}` ID.
4. **Cytoscape instances** (per graph view): registered under the graph container ID.

When a group is removed, the cleanup registry fires for the group's DOM container, cascading to all nested registered cleanups (vertical splits, editors, graphs within that group).

## 7. Phase 14 Implementation Notes

- workspace.js grows a `WorkspaceLayout` class (or separate workspace-layout.js module)
- `#editor-pane` DOM structure changes from single `#editor-area` to multiple `div.editor-group` containers
- Tab drag between groups uses HTML5 drag-and-drop API (dataTransfer with tab ID)
- Each group has its own `#tab-bar-{groupId}` and `#editor-area-{groupId}`
- `openTab()` adds to the active group by default; "Open in Split" adds to a new/different group
- Keyboard shortcut for splitting: `Ctrl+\` (matching VS Code convention)
- Right-click tab context menu: "Move to Group...", "Split Right"

### Backward Compatibility

The single-group case (default) should behave identically to the current workspace. The WorkspaceLayout class wraps the existing tab management, so existing `openTab()`, `closeTab()`, `switchTab()` functions continue to work by operating on the active group.

### Performance Considerations

- Split.js recreation is fast (< 5ms) since it only manipulates gutters and event listeners
- Tab content is preserved if the DOM container persists; only destroyed tabs need re-fetching
- SessionStorage writes occur on tab/group change, not on every frame

---

*This document is referenced by Phase 14 plans and prevents the Split.js "no dynamic pane" pitfall.*
*Created during Phase 10, Plan 03 execution.*
