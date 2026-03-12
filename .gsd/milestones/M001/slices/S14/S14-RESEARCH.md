# Phase 14: Split Panes and Bottom Panel - Research

**Researched:** 2026-02-23
**Domain:** VS Code-style editor groups with horizontal split panes, tab drag-and-drop, and collapsible bottom panel
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Split visual design**
- When splitting, all groups resize to equal proportional widths (e.g., 3 groups = 33% each)
- Users can freely resize groups by dragging the divider, with a minimum width (~200px) per group
- Dividers use thin line style (1-2px subtle border), widening on hover to indicate draggability — VS Code style, not the thicker Split.js gutter
- Adding or removing groups uses a brief ~150ms smooth resize transition animation

**Tab drag behavior**
- Dragging a tab shows both a semi-transparent ghost tab following the cursor AND highlights the target tab bar's insertion point
- Dragging a tab toward the right edge of the editor area creates a new split group (like VS Code)
- Tabs are reorderable within the same group using the same drag mechanism
- Duplicate objects are allowed — the same object can be open in multiple groups independently

**Bottom panel layout**
- Default height is ~30% of editor area when first opened
- Panel has a maximize toggle button that expands to full editor height; click again to restore
- Panel tabs (SPARQL, Event Log, AI Copilot) use a different, more compact toolbar-tab style distinct from editor tabs — similar to VS Code's panel tabs
- Full state persistence across page reloads: open/closed state, height, and active tab all saved to localStorage

**Keyboard & discovery**
- All split/panel actions available in the command palette (Ctrl+K): Split Right, Close Group, Toggle Panel, Maximize Panel
- Full right-click context menu on tabs: Close, Close Others, Split Right, Move to Group →
- Ctrl+1/2/3/4 shortcuts to focus editor group by number (VS Code convention)
- No visual hints for splitting in default single-group view — power users discover via shortcuts, context menu, or command palette

### Claude's Discretion
- Exact drop zone highlighting colors and ghost tab opacity
- How "Move to Group →" submenu works when there's only one other group
- Exact minimum panel height when collapsed vs hidden
- Tab overflow behavior when too many tabs in a group

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WORK-01 | User can split the editor into multiple editor groups (horizontal split) via context menu "Split Right" or Ctrl+\ shortcut, up to 4 groups max | WorkspaceLayout class design from Phase 10 EDITOR-GROUPS-DESIGN.md; Split.js destroy-and-recreate strategy |
| WORK-02 | Each editor group has its own tab bar with independent tabs; tabs can be dragged between groups | HTML5 Drag-and-Drop API with dragstart/dragover/drop; dataTransfer for tab IDs; per-group tab state in WorkspaceLayout |
| WORK-03 | Closing the last tab in an editor group removes that group and remaining groups expand to fill space | WorkspaceLayout.removeGroup() redistributes tabs; Split.js recreated with new sizes; cleanup registry fires |
| WORK-04 | A bottom panel with tabbed interface exists below the editor area, toggled via Ctrl+J, with collapse/maximize controls | Separate bottom panel DOM area with localStorage persistence; mousedown resize handle; CSS flex layout |
| WORK-05 | Bottom panel has placeholder tabs for SPARQL console, Event Log, and AI Copilot | Static HTML tab panels with panel-tab styling distinct from editor tabs; SPARQL can embed existing app.js functionality |
</phase_requirements>

---

## Summary

Phase 14 builds on the EDITOR-GROUPS-DESIGN.md created in Phase 10 (plan 10-03). That document defines a complete WorkspaceLayout class, EditorGroup data model, Split.js recreation strategy, sessionStorage schema, and migration path from the current single-group tab state. The core technical challenge — that Split.js has no dynamic pane API and requires destroy-and-recreate — is already solved by the design.

The implementation has three distinct technical tracks: (1) the WorkspaceLayout class and multi-group editor area using Split.js; (2) tab drag-and-drop between groups using the HTML5 Drag-and-Drop API with visual feedback (ghost image + insertion indicator); and (3) the bottom panel with a custom resize handle, localStorage persistence, and VS Code-style panel tabs.

The project uses vanilla JS (IIFE pattern), no build step, Split.js 1.6.5 (already loaded), htmx 2.0.4, and the existing cleanup registry pattern. The new code must integrate with workspace.js (currently 1024 lines), potentially splitting it into workspace-layout.js and workspace-ui.js modules for maintainability.

**Primary recommendation:** Implement WorkspaceLayout as a new workspace-layout.js module (not inline in workspace.js), use HTML5 native drag-and-drop for tab DnD, implement the bottom panel resize with mousedown/mousemove/mouseup pointer events, and persist bottom panel state to localStorage (not sessionStorage).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Split.js | 1.6.5 | Horizontal resizable panes between editor groups | Already loaded; destroy/recreate pattern established in Phase 10 design |
| HTML5 Drag-and-Drop API | Browser native | Tab dragging within and between groups | No dependency needed; sufficient for the use case |
| localStorage | Browser native | Bottom panel state persistence (open/closed, height, active tab) | Per user decision; survives page reloads |
| sessionStorage | Browser native | Editor group layout persistence (groups, tabs, sizes) | Existing pattern from workspace.js |
| ninja-keys | 1.2.2 (pinned) | Command palette entries for split/panel actions | Already integrated; entries must be added for WORK-01 shortcuts |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pointer Events API | Browser native | Resize handle for bottom panel | mousemove/mouseup/mousedown for drag-resize without library |
| CSS transitions | Browser native | ~150ms group add/remove animation | `transition: flex 150ms ease-out` on editor groups |
| CSS custom properties | Browser native | Bottom panel dimensions, theme integration | Reuse existing --color-* tokens from theme.css |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTML5 native DnD | SortableJS | SortableJS is more featureful but adds a CDN dependency; native DnD is sufficient for tab-between-tab-bar movement |
| Custom resize handle (mousedown) | Split.js for bottom panel | Split.js is horizontal-only (col-resize); bottom panel needs row-resize; custom handle is 20 lines of JS |
| workspace-layout.js (new module) | Extending workspace.js | workspace.js is already 1024 lines; a new module is cleaner and doesn't break existing functions |

**Installation:** No new packages needed. All required capabilities are browser-native or already loaded.

---

## Architecture Patterns

### Recommended Project Structure

The existing file layout should be extended, not replaced:

```
frontend/static/js/
├── workspace.js           # REFACTOR: keep existing openTab/closeTab/switchTab exports
│                          # but delegate to WorkspaceLayout; remove old tab state vars
├── workspace-layout.js    # NEW: WorkspaceLayout class, EditorGroup, tab state model
│                          # Uses the design from EDITOR-GROUPS-DESIGN.md verbatim
└── (workspace.js remains the entrypoint and global API surface)

frontend/static/css/
├── workspace.css          # ADD: .editor-group, .group-tab-bar, .group-editor-area,
│                          # .gutter-thin (VS Code style), .bottom-panel, .panel-tab,
│                          # .panel-tab-bar, .drop-indicator, .ghost-tab
└── (theme.css stays as-is; all new selectors use existing CSS custom properties)

backend/app/templates/browser/
└── workspace.html         # MODIFY: change #editor-pane internal structure to
                           # .editor-groups-container (single group initially),
                           # ADD: #bottom-panel section below #editor-pane
```

### Pattern 1: WorkspaceLayout Class (from EDITOR-GROUPS-DESIGN.md)

**What:** A JavaScript class managing 1-4 editor groups, each with its own tab list, active tab, and Split.js percentage size.
**When to use:** Every time a tab is opened, closed, moved, or a group is split/removed.

```javascript
// workspace-layout.js
// Based on EDITOR-GROUPS-DESIGN.md (Phase 10, plan 10-03)

var LAYOUT_KEY = 'sempkm_workspace_layout';

function WorkspaceLayout() {
  this.groups = [];
  this.activeGroupId = null;
}

WorkspaceLayout.prototype.addGroup = function() {
  if (this.groups.length >= 4) return null;
  var id = 'group-' + (Date.now());
  var equalSize = 100 / (this.groups.length + 1);
  this.groups.forEach(function(g) { g.size = equalSize; });
  this.groups.push({ id: id, tabs: [], activeTabId: null, size: equalSize });
  this.save();
  return id;
};

WorkspaceLayout.prototype.removeGroup = function(groupId) {
  var idx = this.groups.findIndex(function(g) { return g.id === groupId; });
  if (idx === -1 || this.groups.length === 1) return;
  var removed = this.groups.splice(idx, 1)[0];
  // Redistribute tabs to adjacent group (prefer left neighbor)
  var neighborIdx = Math.max(0, idx - 1);
  var neighbor = this.groups[neighborIdx];
  removed.tabs.forEach(function(t) { neighbor.tabs.push(t); });
  // Recalculate equal sizes
  var equalSize = 100 / this.groups.length;
  this.groups.forEach(function(g) { g.size = equalSize; });
  if (this.activeGroupId === groupId) this.activeGroupId = neighbor.id;
  this.save();
};

WorkspaceLayout.prototype.save = function() {
  try {
    sessionStorage.setItem(LAYOUT_KEY, JSON.stringify({
      groups: this.groups,
      activeGroupId: this.activeGroupId
    }));
  } catch(e) {}
};

WorkspaceLayout.restore = function() {
  try {
    var raw = sessionStorage.getItem(LAYOUT_KEY);
    if (raw) {
      var data = JSON.parse(raw);
      var layout = new WorkspaceLayout();
      layout.groups = data.groups || [];
      layout.activeGroupId = data.activeGroupId || null;
      return layout;
    }
  } catch(e) {}
  return null;
};
```

### Pattern 2: Split.js Destroy-and-Recreate for Groups

**What:** When a group is added or removed, destroy the current horizontal Split.js instance and recreate it with new group selectors.
**When to use:** addGroup(), removeGroup() trigger this; single-group case skips Split.js entirely.

```javascript
// In workspace-layout.js or workspace.js
var groupSplitInstance = null;

function recreateGroupSplit(layout) {
  // 1. Destroy existing
  if (groupSplitInstance) {
    groupSplitInstance.destroy();
    groupSplitInstance = null;
  }

  // 2. Build DOM containers
  var editorPane = document.getElementById('editor-pane');
  editorPane.innerHTML = '';
  layout.groups.forEach(function(group) {
    var div = document.createElement('div');
    div.className = 'editor-group';
    div.id = group.id;
    div.innerHTML = '<div class="group-tab-bar" id="tab-bar-' + group.id + '"></div>' +
                    '<div class="group-editor-area" id="editor-area-' + group.id + '"></div>';
    editorPane.appendChild(div);
  });

  // 3. Recreate Split.js (only when 2+ groups)
  if (layout.groups.length > 1) {
    var selectors = layout.groups.map(function(g) { return '#' + g.id; });
    var sizes = layout.groups.map(function(g) { return g.size; });
    groupSplitInstance = Split(selectors, {
      sizes: sizes,
      minSize: 200,
      gutterSize: 1,          // Visually thin; CSS widens hit target on hover
      cursor: 'col-resize',
      onDragEnd: function(s) {
        layout.groups.forEach(function(g, i) { g.size = s[i]; });
        layout.save();
      }
    });
  }

  // 4. Restore content in each group
  layout.groups.forEach(function(group) {
    renderGroupTabBar(group);
    if (group.activeTabId) loadTabInGroup(group.id, group.activeTabId);
  });
}
```

### Pattern 3: VS Code-Style Thin Gutter with Hover Expand

**What:** Split.js gutterSize: 1 with CSS pseudo-element to make the invisible hit target wider on hover.
**When to use:** Every horizontal divider between editor groups.

```css
/* workspace.css additions */
/* Groups container: flex-row, no overflow */
.editor-groups-container {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

/* Individual group */
.editor-group {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  /* Smooth transition when groups are added/removed */
  transition: flex 150ms ease-out;
}

/* VS Code-style thin gutter */
.gutter.gutter-horizontal.gutter-editor-groups {
  width: 1px;
  background: var(--color-border);
  cursor: col-resize;
  position: relative;
  flex-shrink: 0;
  transition: background 0.15s;
}

.gutter.gutter-horizontal.gutter-editor-groups::after {
  content: '';
  position: absolute;
  top: 0;
  left: -4px;      /* 4px of invisible hit area on each side */
  right: -4px;
  bottom: 0;
  z-index: 1;
}

.gutter.gutter-horizontal.gutter-editor-groups:hover {
  background: var(--color-primary);
  width: 2px;      /* Widens on hover like VS Code */
}
```

### Pattern 4: HTML5 Tab Drag-and-Drop

**What:** Native dragstart/dragover/drop events on tab elements with visual feedback (ghost image + insertion indicator).
**When to use:** Every tab in every group's tab bar has draggable="true".

```javascript
// Drag initiation on tab element
function initTabDrag(tabEl, tabId, groupId) {
  tabEl.setAttribute('draggable', 'true');

  tabEl.addEventListener('dragstart', function(e) {
    e.dataTransfer.setData('text/plain', JSON.stringify({ tabId: tabId, sourceGroupId: groupId }));
    e.dataTransfer.effectAllowed = 'move';

    // Create custom ghost: a styled clone of the tab
    var ghost = tabEl.cloneNode(true);
    ghost.style.opacity = '0.7';
    ghost.style.position = 'fixed';
    ghost.style.top = '-1000px';
    document.body.appendChild(ghost);
    e.dataTransfer.setDragImage(ghost, 20, 10);
    setTimeout(function() { document.body.removeChild(ghost); }, 0);

    tabEl.classList.add('dragging');
  });

  tabEl.addEventListener('dragend', function() {
    tabEl.classList.remove('dragging');
    // Clear all drop indicators
    document.querySelectorAll('.drop-indicator').forEach(function(el) {
      el.classList.remove('drop-indicator-active');
    });
  });
}

// Drop zone on tab bars
function initTabBarDropZone(tabBarEl, targetGroupId) {
  tabBarEl.addEventListener('dragover', function(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    tabBarEl.classList.add('tab-bar-drag-over');
    // Show insertion indicator at drop position
    _updateInsertionIndicator(tabBarEl, e.clientX);
  });

  tabBarEl.addEventListener('dragleave', function() {
    tabBarEl.classList.remove('tab-bar-drag-over');
  });

  tabBarEl.addEventListener('drop', function(e) {
    e.preventDefault();
    tabBarEl.classList.remove('tab-bar-drag-over');
    var data = JSON.parse(e.dataTransfer.getData('text/plain'));
    // Move tab from source group to target group
    layout.moveTab(data.tabId, data.sourceGroupId, targetGroupId);
    recreateGroupSplit(layout);
  });
}

function _updateInsertionIndicator(tabBarEl, clientX) {
  var tabs = tabBarEl.querySelectorAll('.workspace-tab');
  // Find which tab the cursor is before/after
  var indicator = tabBarEl.querySelector('.drop-indicator');
  if (!indicator) {
    indicator = document.createElement('div');
    indicator.className = 'drop-indicator';
    tabBarEl.appendChild(indicator);
  }
  // Position the insertion line
  var found = false;
  tabs.forEach(function(tab) {
    var rect = tab.getBoundingClientRect();
    var midX = rect.left + rect.width / 2;
    if (!found && clientX < midX) {
      indicator.style.left = (rect.left - tabBarEl.getBoundingClientRect().left) + 'px';
      found = true;
    }
  });
  if (!found) {
    indicator.style.left = tabBarEl.scrollWidth + 'px';
  }
  indicator.classList.add('drop-indicator-active');
}
```

### Pattern 5: Bottom Panel Resize Handle

**What:** A thin drag handle above the bottom panel; mousedown starts resize, mousemove updates height, mouseup ends resize. Height stored in localStorage.
**When to use:** The bottom panel is shown (not collapsed/hidden).

```javascript
// Bottom panel state
var PANEL_KEY = 'sempkm_bottom_panel';
var panelState = { open: false, height: 30, activeTab: 'sparql', maximized: false };

function savePanelState() {
  try { localStorage.setItem(PANEL_KEY, JSON.stringify(panelState)); } catch(e) {}
}

function restorePanelState() {
  try {
    var raw = localStorage.getItem(PANEL_KEY);
    if (raw) panelState = Object.assign(panelState, JSON.parse(raw));
  } catch(e) {}
}

function initBottomPanelResize() {
  var handle = document.getElementById('panel-resize-handle');
  var panel = document.getElementById('bottom-panel');
  var editorArea = document.getElementById('editor-pane');
  if (!handle || !panel) return;

  var startY, startHeight;

  handle.addEventListener('mousedown', function(e) {
    startY = e.clientY;
    startHeight = panel.getBoundingClientRect().height;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'row-resize';

    function onMove(e) {
      var delta = startY - e.clientY;
      var workspaceHeight = editorArea.parentElement.getBoundingClientRect().height;
      var newHeight = startHeight + delta;
      // Clamp between 80px and 80% of workspace
      newHeight = Math.max(80, Math.min(workspaceHeight * 0.8, newHeight));
      panel.style.height = newHeight + 'px';
      panelState.height = (newHeight / workspaceHeight * 100);
    }

    function onUp() {
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
      savePanelState();
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    }

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    e.preventDefault();
  });
}

function toggleBottomPanel() {
  panelState.open = !panelState.open;
  panelState.maximized = false;
  _applyPanelState();
  savePanelState();
}

function maximizeBottomPanel() {
  panelState.maximized = !panelState.maximized;
  _applyPanelState();
  savePanelState();
}

function _applyPanelState() {
  var panel = document.getElementById('bottom-panel');
  var workspace = document.getElementById('workspace-vertical');
  if (!panel) return;
  if (!panelState.open) {
    panel.style.display = 'none';
  } else if (panelState.maximized) {
    panel.style.display = '';
    panel.style.height = '100%';
    panel.style.flex = '1';
  } else {
    panel.style.display = '';
    panel.style.height = panelState.height + '%';
  }
}
```

### Pattern 6: Right-Click Context Menu on Tabs

**What:** Listen for contextmenu on the tab bar; prevent default; show a positioned custom menu. Dismiss on click-outside or Escape.
**When to use:** User right-clicks any tab in any group.

```javascript
function showTabContextMenu(e, tabId, groupId) {
  e.preventDefault();
  var existing = document.getElementById('tab-context-menu');
  if (existing) existing.remove();

  var menu = document.createElement('div');
  menu.id = 'tab-context-menu';
  menu.className = 'context-menu';

  var items = [
    { label: 'Close', action: function() { closeTabInGroup(tabId, groupId); } },
    { label: 'Close Others', action: function() { closeOtherTabsInGroup(tabId, groupId); } },
    { label: '---' },
    { label: 'Split Right', action: function() { splitRight(groupId); } },
  ];

  // "Move to Group" submenu (only when multiple groups exist)
  var otherGroups = layout.groups.filter(function(g) { return g.id !== groupId; });
  if (otherGroups.length > 0) {
    items.push({ label: 'Move to Group \u2192', submenu: otherGroups });
  }

  items.forEach(function(item) {
    if (item.label === '---') {
      var sep = document.createElement('div');
      sep.className = 'context-menu-separator';
      menu.appendChild(sep);
      return;
    }
    var li = document.createElement('div');
    li.className = 'context-menu-item';
    li.textContent = item.label;
    if (item.action) li.addEventListener('click', function() { item.action(); menu.remove(); });
    menu.appendChild(li);
  });

  // Position near cursor, clamp to viewport
  document.body.appendChild(menu);
  var menuRect = menu.getBoundingClientRect();
  var x = Math.min(e.clientX, window.innerWidth - menuRect.width - 8);
  var y = Math.min(e.clientY, window.innerHeight - menuRect.height - 8);
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';

  // Dismiss on outside click or Escape
  function dismiss(e2) {
    if (!menu.contains(e2.target)) { menu.remove(); document.removeEventListener('click', dismiss); }
  }
  setTimeout(function() { document.addEventListener('click', dismiss); }, 0);
}
```

### Pattern 7: Bottom Panel DOM Structure

**What:** The workspace HTML must gain a vertical split structure to allow the bottom panel to resize against the editor area.

```html
<!-- Modified workspace.html structure -->
<div class="workspace-container" id="workspace">
  <!-- Left pane: Navigation tree (unchanged) -->
  <div class="workspace-pane" id="nav-pane">...</div>

  <!-- Center+Bottom: vertical flex container -->
  <div class="editor-column" id="editor-column">
    <!-- Editor pane (top, flex: 1 or explicit height) -->
    <div class="workspace-pane" id="editor-pane">
      <!-- editor groups injected here by JS -->
      <div class="editor-groups-container">
        <div class="editor-group" id="group-1">
          <div class="group-tab-bar" id="tab-bar-group-1"></div>
          <div class="group-editor-area" id="editor-area-group-1"></div>
        </div>
      </div>
    </div>

    <!-- Resize handle: thin strip at panel top -->
    <div class="panel-resize-handle" id="panel-resize-handle"></div>

    <!-- Bottom panel (hidden by default) -->
    <div class="bottom-panel" id="bottom-panel" style="display: none;">
      <div class="panel-header">
        <div class="panel-tab-bar" id="panel-tab-bar">
          <button class="panel-tab active" data-panel="sparql">SPARQL</button>
          <button class="panel-tab" data-panel="event-log">Event Log</button>
          <button class="panel-tab" data-panel="ai-copilot">AI Copilot</button>
        </div>
        <div class="panel-controls">
          <button class="panel-btn" id="panel-maximize-btn" title="Maximize Panel">&#8679;</button>
          <button class="panel-btn" id="panel-close-btn" title="Close Panel">&#10005;</button>
        </div>
      </div>
      <div class="panel-content">
        <div class="panel-pane active" id="panel-sparql">
          <!-- SPARQL placeholder -->
          <div class="panel-placeholder">SPARQL Console (coming in Phase 17)</div>
        </div>
        <div class="panel-pane" id="panel-event-log">
          <div class="panel-placeholder">Event Log (coming in Phase 16)</div>
        </div>
        <div class="panel-pane" id="panel-ai-copilot">
          <div class="panel-placeholder">AI Copilot (coming in v2.1)</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Right pane: Details (unchanged) -->
  <div class="workspace-pane" id="right-pane">...</div>
</div>
```

### Anti-Patterns to Avoid

- **Nested Split.js instances for vertical layout:** Do not use Split.js for the editor-pane/bottom-panel split. The bottom panel needs a custom resize handle (Split.js only does col-resize or row-resize within a flat container, and adding the panel to the existing main Split.js instance would require destroying the entire workspace split). Use a custom mousedown handler instead.
- **Storing bottom panel state in sessionStorage:** User decision requires persistence across page reloads — use localStorage.
- **Trying to update Split.js pane count after init:** Split.js has no `addPane()` or `removePane()` — always destroy and recreate.
- **Using position: absolute for the editor groups:** The groups must participate in normal flex flow so they can animate with `transition: flex 150ms`.
- **Modifying workspace.js global functions:** `openTab()`, `closeTab()`, `switchTab()` are exported as `window.*` and called from htmx onclick attributes. Do not change their signatures — delegate internally to the WorkspaceLayout.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pane resizing between groups | Custom drag handler | Split.js (already loaded) | Split.js handles the edge cases: minSize, cursor, multi-pane percentage distribution |
| Drag image customization | Manual DOM positioning | `dataTransfer.setDragImage()` | Browser API; automatically cleaned up on dragend |
| Tab insertion point calculation | Complex DOM math | `getBoundingClientRect()` on each tab + cursor X position | Standard, reliable, works with overflow tabs |
| localStorage serialization | Custom encoding | `JSON.stringify` / `JSON.parse` | No nested complexity; panel state is flat |
| Context menu positioning | Library | Manual clientX/clientY clamped to viewport | 10 lines of JS; no library needed for this menu |
| Theme-aware gutter styling | Inline styles | CSS custom properties (existing) | `var(--color-border)` and `var(--color-primary)` already defined |

**Key insight:** The hardest problem in this phase (dynamic Split.js panes) was already solved in Phase 10 with the destroy-and-recreate pattern. Don't reopen that question.

---

## Common Pitfalls

### Pitfall 1: `#editor-area` Hard-Coded References in workspace.js

**What goes wrong:** workspace.js has multiple references to `document.getElementById('editor-area')` for loading object content via htmx. With multiple groups, each has its own `#editor-area-{groupId}`. Code that targets `#editor-area` will load content into the wrong element.
**Why it happens:** The existing single-group assumption is baked into every htmx load function.
**How to avoid:** Add `getActiveEditorArea()` helper that returns `document.getElementById('editor-area-' + layout.activeGroupId)`. Replace all `editor-area` references to use this helper.
**Warning signs:** Content loads into the wrong group; all groups show the same object.

### Pitfall 2: Split.js Gutter Size vs. Hit Target

**What goes wrong:** `gutterSize: 1` makes the visible gutter 1px, but the actual draggable hit target is also only 1px — impossible to grab.
**Why it happens:** Split.js uses the gutterSize for both visual width and pointer events area.
**How to avoid:** Use `gutterSize: 1` with a CSS `::after` pseudo-element that expands the invisible hit area to ~9px (4px on each side). The user sees a 1-2px line; the pointer target is 9px wide.
**Warning signs:** Users cannot reliably grab the divider to resize groups.

### Pitfall 3: Drag-and-Drop on Tabs with `onclick` Handlers

**What goes wrong:** Tabs have inline `onclick="switchTab('...')"` handlers. A click at the end of a drag fires the `click` event, switching the tab unexpectedly.
**Why it happens:** The HTML5 DnD spec fires click after drop if the mouse doesn't move far enough to trigger dragstart.
**How to avoid:** Track `isDragging` flag on dragstart; in the click handler, bail if `isDragging` is true. On dragend, reset after a microtask: `setTimeout(function() { isDragging = false; }, 0)`.
**Warning signs:** Tabs switch to wrong active state after a short drag that didn't complete.

### Pitfall 4: Tab Context Menu vs. Text Selection

**What goes wrong:** The browser's native context menu appears on top of or before the custom context menu.
**Why it happens:** `contextmenu` event must be cancelled with `e.preventDefault()` before showing the custom menu.
**How to avoid:** In the `contextmenu` listener: `e.preventDefault(); e.stopPropagation();` before building the menu DOM.
**Warning signs:** Both native and custom menus appear simultaneously.

### Pitfall 5: Bottom Panel Height in Percentage vs. Pixels

**What goes wrong:** Storing panel height as a percentage (`30%`) doesn't render correctly if the workspace height changes (window resize), or the panel initializes before the workspace layout is stable.
**Why it happens:** CSS `height: 30%` requires the parent to have a defined height; flex parents with `flex: 1` may not provide a stable pixel height on first render.
**How to avoid:** Store height as a percentage in state; on apply, convert to pixels using `parentElement.getBoundingClientRect().height * (percent / 100)`. Set `style.height` in pixels, not percent.
**Warning signs:** Bottom panel appears with zero height or incorrect height on first open.

### Pitfall 6: sessionStorage Layout Migration

**What goes wrong:** Existing users have `sempkm_open_tabs` and `sempkm_active_tab` in sessionStorage. New code reads `sempkm_workspace_layout` which doesn't exist — workspace appears empty.
**Why it happens:** The new WorkspaceLayout uses a different storage key.
**How to avoid:** The migration function from EDITOR-GROUPS-DESIGN.md (section 5) must run at init before `restore()` is called. Check for old keys and convert.
**Warning signs:** Existing open tabs disappear after the Phase 14 deployment.

### Pitfall 7: Ctrl+\ Keyboard Conflict

**What goes wrong:** The existing `workspace.js` already binds `Ctrl+\` to `toggleSidebar()`. Phase 14 needs `Ctrl+\` for "Split Right".
**Why it happens:** The existing keyboard handler maps `Ctrl+\` to sidebar toggle (line 503 of workspace.js). The CONTEXT.md says `Ctrl+\` is the split shortcut.
**How to avoid:** Reassign `Ctrl+\` to `splitRight()` in the new keyboard handler. Move sidebar toggle to a different shortcut (sidebar collapse is already available as `Ctrl+B` per Phase 12). Update command palette entry.
**Warning signs:** `Ctrl+\` opens split group instead of sidebar — which is the CORRECT behavior per Phase 14 spec; old sidebar toggle must be verified to still work via `Ctrl+B`.

### Pitfall 8: Cleanup Registry on Group Removal

**What goes wrong:** When `removeGroup()` is called and `editorPane.innerHTML = ''` is executed to rebuild the DOM, CodeMirror and Split.js instances inside the removed group are not properly destroyed — they remain attached to detached DOM elements.
**Why it happens:** The cleanup registry fires on `htmx:beforeCleanupElement`, but manually setting `.innerHTML = ''` does not fire that event.
**How to avoid:** Before setting `editorPane.innerHTML = ''`, manually call `window.runCleanup()` for each group container that will be removed. Or: trigger cleanup by dispatching a synthetic `htmx:beforeCleanupElement` event (fragile). Better: maintain explicit references to all Split.js and CodeMirror instances per group and destroy them manually.
**Warning signs:** Memory leaks; old CodeMirror instances respond to keyboard events in removed groups.

---

## Code Examples

### Tab Bar Insertion Indicator CSS

```css
/* workspace.css */

/* Drop insertion line between tabs */
.drop-indicator {
  display: none;
  position: absolute;
  width: 2px;
  top: 4px;
  bottom: 4px;
  background: var(--color-accent);
  border-radius: 1px;
  pointer-events: none;
  z-index: 10;
}

.drop-indicator.drop-indicator-active {
  display: block;
}

/* Tab bar becomes highlighted when a tab is dragged over */
.group-tab-bar.tab-bar-drag-over {
  background: var(--color-accent-subtle);
  outline: 1px dashed var(--color-accent);
}

/* Tab being dragged fades out in its source position */
.workspace-tab.dragging {
  opacity: 0.4;
}
```

### Panel Tab Bar (Distinct from Editor Tabs)

```css
/* workspace.css: panel tabs use a different, more compact style */

.bottom-panel {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  overflow: hidden;
  flex-shrink: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  height: 28px;                    /* Shorter than editor tab bar (36px) */
  background: var(--color-surface-recessed);
  border-bottom: 1px solid var(--color-border);
  padding: 0 4px;
  user-select: none;
}

.panel-tab-bar {
  display: flex;
  align-items: center;
  gap: 0;
  flex: 1;
  overflow: hidden;
}

/* Panel tabs: flat, no border-radius, smaller text — VS Code panel tab style */
.panel-tab {
  height: 28px;
  padding: 0 12px;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--color-text-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.1s, border-color 0.1s;
}

.panel-tab.active {
  color: var(--color-text);
  border-bottom-color: var(--color-accent);
}

.panel-tab:hover:not(.active) {
  color: var(--color-text);
  background: var(--color-surface-hover);
}

/* Panel controls (maximize, close) */
.panel-controls {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: auto;
}

.panel-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  border-radius: 3px;
  font-size: 0.9rem;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}

.panel-btn:hover {
  background: var(--color-surface-hover);
  color: var(--color-text);
}

/* Resize handle above panel */
.panel-resize-handle {
  height: 4px;
  background: transparent;
  cursor: row-resize;
  flex-shrink: 0;
  transition: background 0.15s;
}

.panel-resize-handle:hover {
  background: var(--color-primary);
}

/* Panel content area */
.panel-content {
  flex: 1;
  overflow: auto;
  position: relative;
}

.panel-pane {
  display: none;
  height: 100%;
  padding: 12px;
}

.panel-pane.active {
  display: block;
}

.panel-placeholder {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  font-style: italic;
  padding: 16px;
  text-align: center;
}
```

### Context Menu CSS

```css
/* workspace.css */
.context-menu {
  position: fixed;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-shadow: var(--shadow-elevated);
  min-width: 160px;
  z-index: 10000;
  padding: 4px 0;
}

.context-menu-item {
  padding: 6px 16px;
  font-size: 0.83rem;
  cursor: pointer;
  color: var(--color-text);
  transition: background 0.1s;
}

.context-menu-item:hover {
  background: var(--color-primary-subtle);
}

.context-menu-separator {
  height: 1px;
  background: var(--color-border);
  margin: 4px 0;
}
```

### Keyboard Shortcut Registration (additions to workspace.js)

```javascript
// Add to initKeyboardShortcuts() in workspace.js

// Ctrl+\ : Split Right (reassigned from sidebar toggle -- sidebar uses Ctrl+B)
if (mod && e.key === '\\') {
  e.preventDefault();
  splitRight(layout.activeGroupId);
}

// Ctrl+J: Toggle bottom panel
if (mod && e.key === 'j') {
  e.preventDefault();
  toggleBottomPanel();
}

// Ctrl+1/2/3/4: Focus editor group by number
if (mod && ['1', '2', '3', '4'].indexOf(e.key) !== -1) {
  e.preventDefault();
  var groupIndex = parseInt(e.key) - 1;
  if (layout.groups[groupIndex]) {
    setActiveGroup(layout.groups[groupIndex].id);
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `#editor-area` with one tab bar | Multi-group DOM with per-group tab bars | Phase 14 | `getActiveEditorArea()` needed everywhere htmx targets editor content |
| `sempkm_open_tabs` + `sempkm_active_tab` in sessionStorage | `sempkm_workspace_layout` with groups array | Phase 14 | Migration function required on first load |
| Split.js gutterSize: 5 (existing workspace panes) | gutterSize: 1 with CSS hit-target expansion | Phase 14 (editor group gutters only) | Existing nav/right pane gutters stay at 5px; only inter-group gutters change |
| `Ctrl+\` = Toggle Sidebar | `Ctrl+\` = Split Right | Phase 14 | Sidebar toggle stays on `Ctrl+B` (Phase 12); command palette updated |

**Deprecated/outdated for Phase 14:**
- `sempkm_open_tabs` and `sempkm_active_tab` sessionStorage keys: replaced by `sempkm_workspace_layout` (but migration code reads them on first load)
- Direct `document.getElementById('editor-area')` references in workspace.js: must become `getActiveEditorArea()` calls
- Single `#tab-bar` element: replaced by per-group `#tab-bar-{groupId}` elements

---

## Open Questions

1. **How does "Split Right" from the context menu populate the new group?**
   - What we know: "Split Right" creates a new group. The context menu is right-clicked on a specific tab.
   - What's unclear: Does "Split Right" move the right-clicked tab to the new group (VS Code behavior), or does the new group start empty?
   - Recommendation: VS Code moves the tab. Implement as "move right-clicked tab to new group". This is consistent with `Ctrl+\` which should move the active tab.

2. **Tab overflow behavior when too many tabs in a group**
   - What we know: User left this as Claude's Discretion.
   - What's unclear: Clip with scroll (`overflow-x: auto`) vs. shrink tab widths vs. show a dropdown.
   - Recommendation: `overflow-x: auto` with `scrollbar-width: thin` (already used in `.tab-bar-workspace`). Clipping is acceptable for MVP.

3. **Drag to create new group from right edge**
   - What we know: CONTEXT.md says "Dragging a tab toward the right edge of the editor area creates a new split group."
   - What's unclear: The exact trigger zone (last N pixels of `#editor-column`? or last N pixels of the last group's tab bar?). Also whether this has a visual indicator.
   - Recommendation: Monitor dragover on `#editor-column` right edge (last 80px). Show a subtle drop zone indicator (semi-transparent rectangle) when dragging near right edge. On drop: `addGroup()`, then move tab.

4. **Maximized panel height vs. editor height relationship**
   - What we know: "Maximize toggle button that expands to full editor height."
   - What's unclear: Does maximize hide the editor groups entirely, or does the editor column still show (at 0px)?
   - Recommendation: Maximize sets `flex: 1` on `#bottom-panel` and `height: 0; overflow: hidden` on `#editor-pane`. This hides editor groups but they are still in the DOM (content preserved).

5. **Ctrl+\ conflict resolution**
   - What we know: Current workspace.js binds `Ctrl+\` to `toggleSidebar()`. Phase 14 CONTEXT.md says it should be "Split Right".
   - Recommendation: Reassign `Ctrl+\` to `splitRight()` in Phase 14. `Ctrl+B` remains sidebar toggle. Update command palette entries.

---

## Sources

### Primary (HIGH confidence)
- `.planning/phases/10-bug-fixes-and-cleanup-architecture/EDITOR-GROUPS-DESIGN.md` — Full WorkspaceLayout class design, Split.js strategy, sessionStorage schema, migration path (written by project, authoritative)
- `frontend/static/js/workspace.js` — Current tab management code (1024 lines, read in full)
- `frontend/static/css/workspace.css` — Current styles, existing CSS custom property tokens
- `backend/app/templates/browser/workspace.html` — Current DOM structure
- `base.html` — Full dependency list: Split.js 1.6.5, htmx 2.0.4, ninja-keys 1.2.2 (pinned)
- Split.js README (https://github.com/nathancahill/split/blob/master/packages/splitjs/README.md) — Confirmed: no dynamic pane API; destroy/recreate required
- MDN HTML5 Drag-and-Drop API (https://web.dev/articles/drag-and-drop) — dragstart, dragover, drop event model; `setDragImage()` for ghost

### Secondary (MEDIUM confidence)
- WebSearch: Split.js gutterStyle + CSS hover expansion pattern — confirmed pseudo-element approach for wider hit target
- WebSearch: HTML5 contextmenu event + `preventDefault()` + viewport-clamped positioning — standard pattern for custom context menus
- WebSearch: CSS flex transition for add/remove element — `transition: flex 150ms ease-out` works for group animation

### Tertiary (LOW confidence)
- WebSearch: Bottom panel resize with mousedown/mousemove — multiple CodePen examples confirm the pattern, but specific edge cases (panel height in %, resize during sidebar collapse) not verified

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries already in project; no new dependencies
- Architecture: HIGH — EDITOR-GROUPS-DESIGN.md is authoritative and detailed; existing patterns (cleanup registry, Split.js recreation) are proven
- Pitfalls: HIGH for Pitfalls 1-6 (derived from reading actual code); MEDIUM for Pitfall 7-8 (derived from patterns, not tested)
- Code examples: HIGH for CSS patterns; MEDIUM for JS patterns (pseudocode level, not production-tested)

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable tech; no fast-moving dependencies)