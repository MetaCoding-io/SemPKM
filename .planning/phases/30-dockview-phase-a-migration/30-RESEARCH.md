# Phase 30: Dockview Phase A Migration - Research

**Researched:** 2026-03-02
**Domain:** dockview-core 4.11.0 integration replacing Split.js editor-group system; htmx re-wiring; custom drag-drop removal; CodeMirror/Cytoscape visibility refresh
**Confidence:** HIGH (based on direct codebase analysis of all critical files + milestone research already completed + committed DEC-04 decision)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOCK-01 | User can open and manage object tabs rendered in dockview-core panels (Phase A: editor-pane area replaces Split.js; old HTML5 drag system removed in same commit) | dockview `createComponent` + `htmx.ajax()` pattern replaces `recreateGroupSplit()`; `onDidActivePanelChange` dispatches `sempkm:tab-activated`; `onDidRemovePanel` dispatches `sempkm:tabs-empty`; drag system removal in same commit eliminates Pitfall 9 |
</phase_requirements>

---

## Summary

Phase 30 replaces the Split.js multi-group editor system in `workspace-layout.js` with dockview-core 4.11.0. The migration is tightly scoped: only the inner editor-pane area (the `#editor-groups-container` and everything inside it) changes. The outer three-column Split.js split (nav-pane / editor-pane / right-pane) managed by `workspace.js` is entirely untouched. The bottom panel, resize handle, and all right-pane content are also unchanged.

The key implementation unit is replacing the single function `recreateGroupSplit()` (workspace-layout.js lines 301-408) with a dockview initialization call. The `WorkspaceLayout` class is retained as a tab metadata sidecar (label, dirty, typeIcon), while dockview owns all layout geometry. The SemPKM custom events (`sempkm:tab-activated`, `sempkm:tabs-empty`) are rewired from the Split.js callbacks to dockview lifecycle event callbacks with identical payload shape, so all downstream consumers are unchanged.

The three highest-risk integration points are: (1) htmx attributes going silent after dockview panel DOM reparenting during drag (solved by `htmx.process()` in the `onDidLayoutChange` handler), (2) CodeMirror and Cytoscape rendering at zero-size when a hidden panel is re-shown (solved by `onDidVisibilityChange` + `editor.requestMeasure()` / `cy.resize()`), and (3) the HTML5 drag system in `workspace-layout.js` conflicting with dockview's internal drag system (solved by removing all `dragstart`/`dragend`/`dragover`/`drop` logic in the same commit that adds dockview). The research is HIGH confidence because all three solutions are confirmed via official dockview documentation and GitHub issues.

**Primary recommendation:** Replace `recreateGroupSplit()` wholesale with `new DockviewComponent(container, { createComponent, createTabComponent })`, wire `openTab()`/`openViewTab()`/`splitRight()` to `dockview.api.addPanel()`, remove the entire drag-drop section of `workspace-layout.js`, and activate the pre-built `dockview-sempkm-bridge.css` by loading it in `workspace.html`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dockview-core | 4.11.0 | IDE-style panel/tab management with native drag-to-reorder and group splitting | Committed in DEC-04; zero additional dependencies; `createComponent` API integrates cleanly with htmx.ajax |
| htmx | 2.0.4 (existing) | Content delivery into dockview panels via `htmx.ajax()` | Already in use; `htmx.process()` is the canonical re-init call for external DOM mutations |
| Split.js | 1.6.5 (existing) | Outer three-column split (nav/editor/right panes) — UNTOUCHED in Phase A | Phase A scope boundary: only inner editor groups are migrated |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| CodeMirror | existing (via editor.js) | Markdown/RDF editor in object panels | Needs `onDidVisibilityChange` + `requestMeasure()` when panel is re-shown after being hidden |
| Cytoscape.js | 3.33.1 (existing) | Graph visualization in view panels | Needs `onDidVisibilityChange` + `cy.resize()` + `cy.fit()` when panel is re-shown |
| lucide | 0.575.0 (existing) | Type icons in custom tab components | `lucide.createIcons({ root: tabEl })` in `createTabComponent` callback |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| dockview-core | GoldenLayout 2 | Ruled out in DEC-04 — DOM reparenting breaks htmx; no `createComponent` callback for htmx injection |
| CDN (jsdelivr) | npm bundle | CDN avoids build step; workspace page only; acceptable for PKM scale |
| `always` rendering mode | `onlyWhenVisible` (default) | `always` keeps panels in DOM (hidden with display:none) which avoids CodeMirror/Cytoscape zero-size bugs; slightly higher memory; acceptable at 1-4 panels |

**Installation:** No npm install needed. Load via CDN in workspace.html:
```html
<!-- CSS must load BEFORE dockview's CSS so bridge variables are in scope -->
<link rel="stylesheet" href="/static/css/dockview-sempkm-bridge.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/dockview-core@4.11.0/dist/styles/dockview.css">
<script src="https://cdn.jsdelivr.net/npm/dockview-core@4.11.0/dist/dockview-core.min.js"></script>
```

---

## Architecture Patterns

### Recommended Project Structure

The migration touches five existing files and activates one pre-built file. No new files are created in Phase A.

```
frontend/static/js/
├── workspace-layout.js        # PRIMARY CHANGE: recreateGroupSplit() replaced;
│                              #   drag-drop section removed; WorkspaceLayout kept
│                              #   as metadata sidecar; dockview init added
├── workspace.js               # SECONDARY CHANGE: openTab/openViewTab/splitRight
│                              #   call dockview.api.addPanel(); event listeners
│                              #   wired to dockview callbacks
frontend/static/css/
├── dockview-sempkm-bridge.css # ACTIVATED: remove "STATUS: Pattern file" comment;
│                              #   already complete, just not loaded
├── workspace.css              # CLEANUP: remove .editor-group, .group-tab-bar,
│                              #   .group-editor-area, .gutter-editor-groups rules
backend/app/templates/browser/
├── workspace.html             # CHANGE: remove static group-1 HTML inside
│                              #   #editor-groups-container; add CDN links
```

### Pattern 1: dockview Component Registration

**What:** The `createComponent` factory registers panel content types and wires htmx content loading.
**When to use:** At dockview initialization (replaces `recreateGroupSplit()`).

```javascript
// Source: dockview.dev/docs/core/panels/
var dv = new DockviewComponent(
  document.getElementById('editor-groups-container'),
  {
    createComponent: function(options) {
      var init;
      if (options.name === 'object-editor') {
        init = function(params) {
          htmx.ajax('GET', '/browser/object/' + encodeURIComponent(params.params.iri), {
            target: params.containerElement,
            swap: 'innerHTML'
          });
          // htmx.ajax handles its own htmx.process() — no extra call needed here
          // Subscribe to visibility change for CodeMirror inside this panel
          params.api.onDidVisibilityChange(function(event) {
            if (event.isVisible && window._editorInstances) {
              var cm = window._editorInstances[params.params.iri];
              if (cm && cm.requestMeasure) cm.requestMeasure();
              else if (cm && cm.refresh) cm.refresh();
            }
          });
        };
      } else if (options.name === 'view-panel') {
        init = function(params) {
          var vt = params.params.viewType;
          var vid = params.params.viewId;
          var url = '/browser/views/' + vt + '/' + encodeURIComponent(vid);
          htmx.ajax('GET', url, {
            target: params.containerElement,
            swap: 'innerHTML'
          });
          // Cytoscape visibility refresh
          params.api.onDidVisibilityChange(function(event) {
            if (event.isVisible && window._cytoscapeInstances) {
              var cy = window._cytoscapeInstances[vid];
              if (cy) { cy.resize(); cy.fit(); }
            }
          });
        };
      } else if (options.name === 'special-panel') {
        init = function(params) {
          var url = '/browser/' + params.params.specialType;
          htmx.ajax('GET', url, {
            target: params.containerElement,
            swap: 'innerHTML'
          });
        };
      }
      return { init: init };
    }
  }
);

// Wire layout change → sessionStorage save + htmx re-process on reparented panels
dv.onDidLayoutChange(function() {
  try {
    sessionStorage.setItem('sempkm_workspace_layout_dv',
      JSON.stringify(dv.toJSON()));
  } catch(e) {}
  // Re-process htmx on ALL panel containers after any layout change
  // (drag-to-new-group causes DOM reparenting that silences htmx attributes)
  document.querySelectorAll('.dv-content-container').forEach(function(el) {
    htmx.process(el);
  });
});

// Wire active panel change → sempkm:tab-activated event
dv.onDidActivePanelChange(function(event) {
  if (!event) return;
  var panel = event;
  var tabId = panel.id;
  var params = panel.params || {};
  var isObjectTab = !params.isView && !params.isSpecial;
  document.dispatchEvent(new CustomEvent('sempkm:tab-activated', {
    detail: { tabId: tabId, groupId: panel.group && panel.group.id, isObjectTab: isObjectTab }
  }));
  // Update right pane for object tabs
  if (isObjectTab && typeof loadRightPaneSection === 'function') {
    loadRightPaneSection(tabId, 'relations');
    loadRightPaneSection(tabId, 'lint');
  }
});

// Wire panel remove → sempkm:tabs-empty event
dv.onDidRemovePanel(function() {
  var hasObjectPanel = dv.panels.some(function(p) {
    return !p.params.isView && !p.params.isSpecial;
  });
  if (!hasObjectPanel) {
    document.dispatchEvent(new CustomEvent('sempkm:tabs-empty'));
  }
});
```

### Pattern 2: openTab() with dockview.api.addPanel()

**What:** Replaces `layout.addTabToGroup()` + `loadTabInGroup()` with a single dockview API call.
**When to use:** In `workspace.js` `openTab()`, `openViewTab()`, `splitRight()`.

```javascript
// Source: dockview.dev/docs/core/panels/
function openTab(objectIri, label, mode) {
  var dv = window._dockview;
  if (!dv) return;

  // Check if already open — focus it if so
  var existing = dv.panels.find(function(p) { return p.id === objectIri; });
  if (existing) {
    existing.api.setActive();
    return;
  }

  dv.api.addPanel({
    id: objectIri,
    component: 'object-editor',
    params: { iri: objectIri, isView: false, isSpecial: false },
    title: label || objectIri
    // No 'position' = opens in active group (default behavior)
  });
}

function openViewTab(viewId, viewLabel, viewType) {
  var tabKey = 'view:' + viewId;
  var dv = window._dockview;
  if (!dv) return;

  var existing = dv.panels.find(function(p) { return p.id === tabKey; });
  if (existing) {
    existing.api.setActive();
    return;
  }

  dv.api.addPanel({
    id: tabKey,
    component: 'view-panel',
    params: { viewId: viewId, viewType: viewType, isView: true, isSpecial: false },
    title: viewLabel
  });
}

function splitRight(groupId) {
  // dockview native: addPanel to a new group to the right
  var dv = window._dockview;
  if (!dv) return;
  var activePanel = dv.activePanel;
  if (!activePanel) return;

  dv.api.addPanel({
    id: activePanel.id + '-split-' + Date.now(),
    component: activePanel.component,
    params: Object.assign({}, activePanel.params),
    title: activePanel.title,
    position: { referencePanel: activePanel.id, direction: 'right' }
  });
}
```

### Pattern 3: Layout Restore in onReady

**What:** Safely restore persisted dockview layout on page load with fallback to default.
**When to use:** In `initWorkspaceLayout()` (the new version), wrapped in `try/catch`.

```javascript
// Source: dockview.dev/docs/core/state/load/
function initWorkspaceLayout() {
  var container = document.getElementById('editor-groups-container');
  var dv = new DockviewComponent(container, { createComponent: createComponentFn });

  // Restore or build default
  var saved = null;
  try {
    var raw = sessionStorage.getItem('sempkm_workspace_layout_dv');
    if (raw) saved = JSON.parse(raw);
  } catch (e) { /* corrupted JSON */ }

  if (saved) {
    try {
      dv.fromJSON(saved);
    } catch (err) {
      console.warn('SemPKM: saved dockview layout incompatible, rebuilding.', err);
      sessionStorage.removeItem('sempkm_workspace_layout_dv');
      // Do NOT call dv.clear() here — causes second error in dockview
      buildDefaultLayout(dv);
    }
  } else {
    buildDefaultLayout(dv);
  }

  window._dockview = dv;
  window._workspaceLayout = { _dv: dv }; // minimal shim for compatibility
}

function buildDefaultLayout(dv) {
  // Single empty panel in group-1 (shows empty state)
  // No panels needed — dockview shows empty group by default
  // OR open with the welcome state handled by the empty group UI
}
```

### Pattern 4: Custom Tab Component with WorkspaceLayout Metadata

**What:** Retain tab label, dirty marker, and type icon from WorkspaceLayout sidecar.
**When to use:** `createTabComponent` in the dockview config.

```javascript
// Source: dockview.dev/docs/core/tabs/
createTabComponent: function(options) {
  return {
    init: function(params) {
      var meta = window._tabMeta && window._tabMeta[params.panel.id];
      var label = (meta && meta.label) || params.panel.title || params.panel.id;
      var dirty = meta && meta.dirty;

      var span = document.createElement('span');
      span.className = 'dv-tab-label';
      span.textContent = label;

      if (dirty) {
        var dot = document.createElement('span');
        dot.className = 'tab-dirty';
        span.appendChild(dot);
      }

      if (meta && meta.typeIcon) {
        var icon = document.createElement('i');
        icon.setAttribute('data-lucide', meta.typeIcon);
        if (typeof lucide !== 'undefined') {
          lucide.createIcons({ root: span });
        }
        params.containerElement.insertBefore(icon, params.containerElement.firstChild);
      }

      params.containerElement.appendChild(span);
    }
  };
}
```

### Anti-Patterns to Avoid

- **Querying dockview internal DOM by class name:** Classes like `dv-content-container`, `dv-tabs-and-actions-container` are not part of the public API. Use dockview's public API (`dv.panels`, `panel.api`, `panel.group.api`) for all behavioral integration. CSS customization via `--dv-*` variables only.
- **Running both drag systems in parallel:** Even briefly having both the custom HTML5 drag and dockview drag active causes conflicting `drop` event handling, stuck `isDragging` state, and panels disappearing. Remove the entire drag section in the same commit.
- **Calling `api.clear()` after a failed `fromJSON()`:** This causes a second "Invalid grid element" error in dockview, leaving the workspace blank. Instead, remove the key from sessionStorage and call `buildDefaultLayout()`.
- **Using `closest` selectors in hx-target attributes inside panels:** After drag-to-new-group, dockview reparents `params.containerElement` — any `hx-target` that climbs ancestors (`closest .group-editor-area`) points to a different ancestor. Use explicit container element references instead.
- **Storing type icon inline styles instead of CSS rules:** Per CLAUDE.md, Lucide SVGs shrink to 0px width in flex containers without `flex-shrink: 0`. Always add tab icon CSS in `dockview-sempkm-bridge.css`, never inline styles.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tab drag-to-reorder within a group | Custom HTML5 dragstart/drop on tab elements | dockview native drag | Already works out-of-the-box; custom system conflicts with dockview's event handling |
| Tab drag-to-split into new group | Right-edge drop zone (existing in workspace-layout.js) | dockview native group splitting via drag | dockview handles this natively; custom drop zone causes dual-drag conflicts |
| Panel resize sash between groups | Split.js between editor groups | dockview native sash | dockview has its own sash system; Split.js and dockview sashes conflict |
| Tab bar rendering | Custom `renderGroupTabBar()` function | dockview native tab bar + optional `createTabComponent` | dockview renders tab bars; custom renderer only needed for typeIcon/dirty metadata |
| Layout serialization | Custom JSON format (current `sempkm_workspace_layout`) | `dockview.toJSON()` + `dockview.fromJSON()` | dockview's format handles group geometry, sash sizes, panel positions natively |

**Key insight:** The entire drag system, tab bar DOM manipulation, and group size tracking in `workspace-layout.js` (approximately 400 lines of the 1073-line file) can be deleted outright and replaced by dockview's built-in behavior. This is a net code reduction.

---

## What Gets Removed vs Kept

### Removed from workspace-layout.js

The following sections of `workspace-layout.js` are **deleted wholesale** (not migrated):

| Section | Lines (approx) | Replaced by |
|---------|----------------|-------------|
| `var groupSplitInstance = null` | Line 21 | dockview owns group geometry |
| `migrateTabState()` | Lines 30-58 | No longer needed — new dockview sessionStorage key |
| `WorkspaceLayout.prototype.addGroup` | Lines 72-84 | `dv.api.addPanel({ position: { direction: 'right' } })` |
| `WorkspaceLayout.prototype.removeGroup` | Lines 89-113 | dockview auto-removes empty groups |
| `WorkspaceLayout.prototype.moveTab` | Lines 119-164 | dockview native drag handles moves |
| `WorkspaceLayout.prototype.addTabToGroup` | Lines 169-185 | `dv.api.addPanel()` |
| `recreateGroupSplit()` | Lines 301-408 | `new DockviewComponent(container, config)` |
| `isDragging` + `initTabDrag()` | Lines 414-456 | dockview handles tab drag |
| `initTabBarDropZone()` | Lines 462-499 | dockview handles drop |
| `_updateInsertionIndicator()` | Lines 505-532 | dockview has its own drag indicator |
| `_getInsertBeforeTabId()` | Lines 534-548 | dockview handles |
| `initRightEdgeDropZone()` | Lines 554-609 | dockview group splitting |
| `renderGroupTabBar()` | Lines 615-710 | dockview native + optional `createTabComponent` |
| `loadTabInGroup()` | Lines 716-774 | `createComponent` callback |
| `showGroupEmpty()` | Lines 776-784 | dockview shows empty group UI |
| `splitRight()` | Lines 818-855 | Reimplemented via `dv.api.addPanel({ position: { direction: 'right' } })` |
| `closeTabInGroup()` | Lines 906-909 | `panel.api.close()` |

### Kept from workspace-layout.js (retained or adapted)

| Section | Keep or Adapt | Reason |
|---------|---------------|--------|
| `WorkspaceLayout` class (skeleton) | Adapt to thin sidecar | Tab metadata (label, dirty, typeIcon) registry keyed by panel ID |
| `WorkspaceLayout.prototype.getGroup` | Remove (dockview owns groups) | dockview has `dv.api.getGroup()` |
| `WorkspaceLayout.prototype.save/restore` | Adapt | Save `dv.toJSON()` instead of custom format |
| `switchTabInGroup()` | Adapt | Call `panel.api.setActive()` |
| `setActiveGroup()` | Adapt | dockview manages active group natively |
| `showTabContextMenu()` | Keep mostly intact | Right-click menu is not dockview territory; update action callbacks |
| `closeOtherTabsInGroup()` | Adapt | Iterate `dv.panels`, call `panel.api.close()` |
| `getActiveEditorArea()` | Adapt | Return `dv.activePanel.view.contentContainer` |
| `initWorkspaceLayout()` | Replace | New dockview init logic |
| Window exports | Keep same names | Callers in HTML templates unchanged |

---

## Critical File Inventory

### workspace-layout.js (1073 lines, primary target)

Full read completed. Key findings:

1. **`recreateGroupSplit()` (lines 301-408):** The sole function being replaced. It destroys the old Split.js instance, rebuilds DOM, creates a new Split.js, calls `renderGroupTabBar()` per group, and restores active tab. All of this is replaced by `new DockviewComponent(container, config)`.

2. **Drag system (lines 414-609):** Four distinct functions (`initTabDrag`, `initTabBarDropZone`, `_updateInsertionIndicator`, `_getInsertBeforeTabId`, `initRightEdgeDropZone`) plus the `isDragging` global. All deleted.

3. **`renderGroupTabBar()` (lines 615-710):** Builds tab DOM including type icons via `data-lucide`, dirty markers, close buttons, drag init, context menu. Replaced by dockview native tab bars + optional `createTabComponent` for metadata rendering. Note the inline `tabIconEl.style.width = '14px'` at line 657 — **this is an existing CLAUDE.md violation** (inline style on Lucide icon in flex container). The `createTabComponent` replacement must use CSS class instead.

4. **`loadTabInGroup()` (lines 716-774):** Constructs URL from tab type, calls `htmx.ajax()` targeting `'#editor-area-' + groupId`. Replaced by the `createComponent` callback in dockview config where `params.containerElement` is the direct target.

5. **`initWorkspaceLayout()` (lines 1017-1041):** Called on page load. Calls `migrateTabState()`, restores from sessionStorage, calls `recreateGroupSplit()`. Replaced by dockview init with `fromJSON()` restore pattern.

6. **Window exports (lines 1063-1072):** `window.splitRight`, `window.setActiveGroup`, `window.initWorkspaceLayout`, `window.switchTabInGroup`, `window.closeTabInGroup`, `window.renderGroupTabBar`, `window.loadTabInGroup`. All must remain exported with same names for HTML template callers.

### workspace.js (large file, secondary target)

Key functions that change:

- `openTab()`: calls `layout.addTabToGroup()` → changed to `dv.api.addPanel()`
- `openViewTab()`: calls `layout.addTabToGroup()` → changed to `dv.api.addPanel()`
- `closeTab()`: calls `layout.removeTabFromGroup()` → changed to `panel.api.close()`
- `switchTab()`: calls `window.switchTabInGroup()` → changed to `panel.api.setActive()`
- `markDirty()` / `markClean()`: updates tab metadata sidecar + calls `window.renderGroupTabBar()` → update `window._tabMeta[iri].dirty` + `createTabComponent` refresh
- `getActiveTabIri()`: reads `layout.activeGroupId` → reads `dv.activePanel.id`

Functions that do NOT change:
- All Split.js outer pane management (`initSplit`, `togglePane`, `_rebuildFromCanonical`)
- Bottom panel management (`initBottomPanel`, `toggleBottomPanel`, `maximizeBottomPanel`, `initBottomPanelResize`)
- `loadRightPaneSection()` — stays the same, still uses fetch() to `#relations-content` and `#lint-content`
- Command palette (`ninja-keys`) initialization
- Keyboard shortcuts

### workspace.html

Current structure inside `#editor-groups-container`:
```html
<div class="editor-groups-container" id="editor-groups-container">
    <div class="editor-group" id="group-1">
        <div class="group-tab-bar tab-bar-workspace" id="tab-bar-group-1">...</div>
        <div class="group-editor-area" id="editor-area-group-1">...</div>
    </div>
</div>
```

After Phase A:
```html
<div class="editor-groups-container" id="editor-groups-container">
    <!-- dockview creates all internal DOM -->
</div>
```

The `#editor-pane` div's structure is otherwise unchanged. The `#panel-resize-handle`, `#bottom-panel`, and all right-pane content remain exactly as-is.

CDN additions in `{% block head %}` of workspace.html (NOT in base.html — dockview is workspace-only):
```html
<link rel="stylesheet" href="/static/css/dockview-sempkm-bridge.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/dockview-core@4.11.0/dist/styles/dockview.css">
<script src="https://cdn.jsdelivr.net/npm/dockview-core@4.11.0/dist/dockview-core.min.js"></script>
```

### dockview-sempkm-bridge.css

Already complete. Contains all `--dv-*` → SemPKM token mappings. Only change needed: remove the "STATUS: Pattern file — NOT loaded" comment and the usage instructions comment. The CSS content itself needs no changes.

### workspace.css

Sections to remove after Phase A (dockview owns these now):

- `.editor-group` (line 288-297)
- `.group-tab-bar` (line 300-313)
- `.group-tab-bar::-webkit-scrollbar` (lines 315-321)
- `.group-tab-bar::-webkit-scrollbar-thumb` (lines 319-322)
- `.group-editor-area` (lines 324-329)
- `.editor-group.editor-group-active > .group-tab-bar` (lines 332-334) — dockview has `--dv-paneview-active-outline-color`
- `.gutter.gutter-horizontal.gutter-editor-groups` (lines 337-360) — dockview sash replaces Split.js gutter

Keep:
- `.editor-groups-container` (lines 280-285) — dockview mounts into this element; it must remain `display: flex; flex: 1; overflow: hidden; min-height: 0`
- `.editor-column` (lines 272-277) — outer flex container for groups + bottom panel; unchanged
- All tab styles under `.tab-bar-workspace` / `.workspace-tab` (they may still be used elsewhere or can be removed if purely editor-group-specific — audit before removing)

Also remove from workspace.css:
- `.group-tab-bar.tab-bar-drag-over` (line 1696) — drag system gone
- Drag indicator CSS if present (`.drop-indicator`, `.drop-indicator-active`)
- `#right-edge-drop-zone` styles if present

---

## Common Pitfalls

### Pitfall 1: htmx Attributes Silenced After Dockview Panel Init/Reparent

**What goes wrong:** When a user drags a panel to a new group, dockview physically moves `params.containerElement` in the DOM. Any `hx-*` attributes that reference ancestor elements (via `hx-target="closest .something"`) now point to different ancestors. Clicks on htmx elements in moved panels produce no network requests.

**Why it happens:** htmx does not use MutationObserver — it only processes nodes it controls. External DOM reparenting is invisible to htmx.

**How to avoid:**
- In `dv.onDidLayoutChange`, call `htmx.process()` on all panel containers:
  ```javascript
  dv.onDidLayoutChange(function() {
    document.querySelectorAll('.dv-content-container').forEach(function(el) {
      htmx.process(el);
    });
  });
  ```
- For content loaded via `htmx.ajax()` in `createComponent.init()`, htmx processes its own swaps — no extra call needed for initial load.
- Audit all templates rendered inside panels for `hx-target="closest ..."` and replace with ID-based targets.

**Warning signs:** htmx-powered buttons work when panel first opens but stop working after drag-to-new-group. No network requests in DevTools after moving a panel.

### Pitfall 2: CodeMirror and Cytoscape Render at Zero-Size When Panel Re-shown

**What goes wrong:** dockview's default `onlyWhenVisible` mode removes hidden panels from the DOM. When re-shown, CodeMirror shows as a blank strip or single line; Cytoscape shows a blank white box because they measured container dimensions at 0px during detachment.

**Why it happens:** Both measure their viewport from the DOM at init time. `ResizeObserver` fires with `contentRect.width = 0` while detached and does not re-fire when the container is reattached at its true size.

**How to avoid:** Two options (both documented in PITFALLS.md):

Option A (preferred for SemPKM scale): Use `always` rendering mode for all panels, which keeps panels in DOM with `display:none` when hidden:
```javascript
// In DockviewComponent config:
disableAutoResizing: false,  // (check current dockview API for renderMode option)
```
_Note:_ Check exact API for rendering mode in dockview 4.11.0 — may be a panel-level option `renderer: 'onlyWhenVisible' | 'always'`.

Option B (fine-grained): Subscribe to `onDidVisibilityChange` in each panel's `createComponent.init()`:
```javascript
params.api.onDidVisibilityChange(function(event) {
  if (event.isVisible) {
    // CodeMirror 6:
    if (cm) cm.requestMeasure();
    // CodeMirror 5:
    if (cm) cm.refresh();
    // Cytoscape:
    if (cy) { cy.resize(); cy.fit(); }
  }
});
```

**Warning signs:** CodeMirror appears as a single text line; gutter line numbers are misaligned; Cytoscape graph is blank white after switching back to a graph tab.

### Pitfall 3: Dual Drag-and-Drop Conflict

**What goes wrong:** workspace-layout.js has a full custom HTML5 drag system (`dragstart`, `dragend`, `dragover`, `dragleave`, `drop` on `.workspace-tab` elements, plus `initRightEdgeDropZone()` on the container). Running both systems simultaneously causes: panels disappearing on drop, `isDragging` state getting stuck, and unexpected group creation from dockview intercepting drops the custom system was handling.

**How to avoid:** Remove the entire HTML5 drag section from workspace-layout.js in the **same commit** that adds dockview. The removals:
- `var isDragging = false` (line 414)
- `initTabDrag()` function (lines 420-456)
- `initTabBarDropZone()` function (lines 462-499)
- `_updateInsertionIndicator()` function (lines 505-532)
- `_getInsertBeforeTabId()` function (lines 534-548)
- `initRightEdgeDropZone()` function (lines 554-609)
- All `initTabDrag(tabEl, tabId, group.id)` call sites in `renderGroupTabBar()`

**Code review gate:** After the commit, search `workspace-layout.js` for `dragstart` — there must be zero matches.

### Pitfall 4: sessionStorage Key Collision with Old Layout Format

**What goes wrong:** The existing layout key `sempkm_workspace_layout` stores the old custom JSON format `{ groups: [...], activeGroupId: '...' }`. dockview's `toJSON()` produces a completely different format. If the old key is used for dockview state, `fromJSON()` will fail on pages loaded from old session data.

**How to avoid:** Use a new key `sempkm_workspace_layout_dv` for dockview state. Do NOT attempt to migrate the old format — just ignore it and start fresh. The old key (`sempkm_workspace_layout`) can be removed from sessionStorage on first dockview init:
```javascript
sessionStorage.removeItem('sempkm_workspace_layout');  // clear old format
```

### Pitfall 5: CDN Load Order — Bridge CSS Before dockview CSS

**What goes wrong:** `dockview-sempkm-bridge.css` sets `--dv-*` CSS variable values. If the dockview CSS loads first, dockview's own variable defaults are set before the bridge overrides them. Depending on specificity, the bridge overrides may or may not win.

**How to avoid:** The correct load order (per the existing comment in `dockview-sempkm-bridge.css`) is:
```html
1. /css/theme.css          (sets --color-* / --tab-* / --panel-* tokens)
2. /css/dockview-sempkm-bridge.css  (maps --dv-* to SemPKM tokens, in :root)
3. dockview CDN CSS        (uses --dv-* variables, which now reference SemPKM tokens)
```
Since workspace.html uses `{% block head %}`, the CDN links go in the block AFTER base.html loads theme.css. But `dockview-sempkm-bridge.css` must be a static file loaded before the CDN CSS, not after.

### Pitfall 6: Inline Lucide Icon Styles in Tab Components (CLAUDE.md Violation)

**What goes wrong:** The existing `renderGroupTabBar()` at line 657 sets `tabIconEl.style.width = '14px'` and `tabIconEl.style.height = '14px'` on a Lucide SVG inside a flex container. Per CLAUDE.md, this causes the icon to render as 0px width because the flex layout overrides inline styles without `flex-shrink: 0`.

**How to avoid:** In the new `createTabComponent`, add Lucide icon sizing to `dockview-sempkm-bridge.css`:
```css
/* In dockview-sempkm-bridge.css */
.dv-tab .tab-type-icon {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    stroke: currentColor;
    margin-right: 4px;
}
```

---

## Code Examples

### Verified Patterns from Official Sources

#### Panel Addition with Direction
```javascript
// Source: dockview.dev/docs/core/panels/
// Open panel to the right of existing panel (split right)
dv.api.addPanel({
  id: 'new-panel-id',
  component: 'object-editor',
  params: { iri: someIri },
  title: 'Panel Title',
  position: {
    referencePanel: existingPanelId,
    direction: 'right'   // 'left' | 'right' | 'above' | 'below' | 'within'
  }
});
```

#### Panel Close
```javascript
// Source: dockview.dev/docs/core/panels/
var panel = dv.getGroupPanel(panelId);
if (panel) panel.api.close();
```

#### Layout Serialization
```javascript
// Source: dockview.dev/docs/core/state/save/
var layoutJson = dv.toJSON();  // Returns plain JS object
sessionStorage.setItem('sempkm_workspace_layout_dv', JSON.stringify(layoutJson));

// Restore:
var saved = JSON.parse(sessionStorage.getItem('sempkm_workspace_layout_dv'));
dv.fromJSON(saved);  // Must be called inside onReady callback or after init
```

#### Panel Visibility Change
```javascript
// Source: dockview.dev/docs/core/panels/rendering/
params.api.onDidVisibilityChange(function(event) {
  // event.isVisible: boolean
  if (event.isVisible) {
    // Panel is now in DOM and sized correctly
    // Safe to call cm.requestMeasure() or cy.resize()
  }
});
```

#### htmx Re-processing After Layout Change
```javascript
// Source: htmx.org/api/#process
// Required after any external DOM mutation that introduces hx-* attributes
htmx.process(containerElement);  // re-registers all htmx behavior in subtree
```

---

## What to Verify (Success Criteria Checklist)

These map directly to the phase success criteria in the additional_context:

1. **User can open multiple object tabs and drag them to reorder or split into side-by-side groups using dockview native drag handles**
   - Verify: Open 3 objects, drag a tab to split into a second group, drag another tab to reorder within group. All operations succeed without blank panels.

2. **Workspace tab layout (group geometry) is automatically saved and restored after a browser reload**
   - Verify: Open 2 tabs in 2 groups, reload page. Same 2 groups with same relative sizes load. Content of each tab is restored.

3. **Object tabs opened inside dockview panels continue to fire `sempkm:tab-activated` and `sempkm:tabs-empty` events with the same payload shape as before**
   - Verify: Add `document.addEventListener('sempkm:tab-activated', console.log)` in browser console. Open a tab — event fires with `{ tabId, groupId, isObjectTab: true }`. Close all object tabs — `sempkm:tabs-empty` fires.

4. **CodeMirror and Cytoscape visualizations render correctly when their containing panel is shown after being hidden (no zero-size blank panels)**
   - Verify: Open an object with a Markdown editor; open a graph view. Switch to another tab. Switch back. Both render at full size with correct gutter alignment.

5. **htmx attributes on content loaded inside dockview panels remain active (forms submit, relations load, linting works)**
   - Verify: Open an object with edit form. Drag the panel to a new group. Click the edit form submit button — network request fires. Relations panel in right pane updates on tab switch.

---

## Open Questions

1. **Exact dockview 4.11.0 API for rendering mode per panel**
   - What we know: PITFALLS.md confirms `onlyWhenVisible` vs `always` modes exist; confirmed in dockview docs and GitHub issues.
   - What's unclear: The exact API property name and where it's set (global config vs per-panel) in version 4.11.0 specifically — may be `renderer: 'always'` in panel options or a global config key.
   - Recommendation: Check `https://dockview.dev/docs/core/panels/rendering/` at implementation time to verify exact property name for 4.11.0.

2. **Custom tab component refresh mechanism after markDirty()**
   - What we know: `createTabComponent` is called once at panel creation. The dirty state can change later (user edits).
   - What's unclear: How to refresh the tab component DOM after dirty state changes without recreating the panel. dockview may have `panel.api.updateParameters()` which re-triggers the tab component.
   - Recommendation: Store a reference to the tab DOM element and update it directly via `window._tabMeta[panelId].dirty = true; refreshTabEl(panelId)`. A simpler approach: the dirty indicator is appended to `params.containerElement` in `createTabComponent` — keep a reference and toggle its class.

3. **`dv.panels` API shape — is it an array or iterable?**
   - What we know: The ARCHITECTURE.md examples use `dv.panels.some(...)` suggesting it's an array.
   - What's unclear: Whether `dv.panels` is a standard Array or a custom iterable in 4.11.0.
   - Recommendation: Use `Array.from(dv.panels)` defensively if needed, or check TypeDocs at `https://dockview.dev/typedocs/` for the exact type.

4. **Bottom panel `#panel-resize-handle` interaction with dockview**
   - What we know: The resize handle is a sibling of `#editor-groups-container` inside `#editor-pane` (confirmed from workspace.html). Dockview is mounted only inside `#editor-groups-container`.
   - What's unclear: Whether dockview's own sash events (`mousedown`) will conflict with the bottom panel resize handle's `mousedown` handler in `initBottomPanelResize()`.
   - Recommendation: The resize handle is at a different DOM level (sibling, not child of the dockview container), so there should be no conflict. Verify by testing bottom panel resize after Phase A implementation.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Split.js between editor groups (splitpane) | dockview-core 4.11.0 (panel management) | Phase A (this phase) | Native tab drag, group splitting, serialization; removes ~400 lines of custom code |
| Custom HTML5 drag-drop tab system | dockview native drag | Phase A (this phase) | Eliminates conflict-prone dragstart/dragover/drop event chain |
| Custom `sempkm_workspace_layout` JSON format | `dockview.toJSON()` / `dv.fromJSON()` | Phase A (this phase) | Richer layout state (group geometry, sash sizes) included automatically |
| `#editor-area-{groupId}` as htmx target | `params.containerElement` as htmx target | Phase A (this phase) | Target is the direct dockview panel element — no ID lookup needed |

**Deprecated/outdated after Phase A:**
- `sempkm_workspace_layout` sessionStorage key: superseded by `sempkm_workspace_layout_dv`
- `.editor-group` / `.group-tab-bar` / `.group-editor-area` CSS classes: dockview creates its own DOM with `--dv-*` styled elements
- `migrateTabState()`: migration from pre-editor-groups format no longer needed
- `isDragging` global flag: no longer needed; dockview handles click-vs-drag internally

---

## Sources

### Primary (HIGH confidence)

- [dockview.dev/docs/](https://dockview.dev/docs/) — `createComponent`, `addPanel`, `toJSON`/`fromJSON`, `onDidLayoutChange`, `onDidActivePanelChange`, `onDidVisibilityChange`, rendering modes; used for all dockview API patterns
- [dockview TypeDocs v4](https://dockview.dev/typedocs/) — type-level API reference for `DockviewComponent`, `IDockviewPanel`, `IDockviewPanelApi`
- [dockview GitHub Issue #341](https://github.com/mathuo/dockview/issues/341) — `fromJSON()` broken state after `api.clear()` in catch block; HIGH confidence for Pitfall 3 / fromJSON pattern
- [dockview GitHub Issue #718](https://github.com/mathuo/dockview/issues/718) — `always` rendering mode; HIGH confidence for CodeMirror/Cytoscape fix
- [dockview GitHub Issue #996](https://github.com/mathuo/dockview/issues/996) — panel content loss on DOM reparenting; HIGH confidence for htmx re-process pattern
- [htmx `htmx.process()` API](https://htmx.org/api/#process) — canonical re-init call for external DOM mutations; HIGH confidence
- SemPKM `frontend/static/js/workspace-layout.js` — direct analysis (1073 lines); HIGH confidence for line-level change mapping
- SemPKM `frontend/static/js/workspace.js` — direct analysis; HIGH confidence for `openTab`/`openViewTab`/`splitRight` call sites
- SemPKM `backend/app/templates/browser/workspace.html` — direct analysis; HIGH confidence for HTML structure changes
- SemPKM `frontend/static/css/dockview-sempkm-bridge.css` — direct analysis; complete and ready to activate
- SemPKM `frontend/static/css/workspace.css` — direct analysis; editor-group CSS sections identified for removal
- SemPKM `.planning/research/SUMMARY.md` — milestone research; HIGH confidence for architecture decisions and pitfall catalog
- SemPKM `.planning/research/ARCHITECTURE.md` — architecture details; HIGH confidence for data flow and file change inventory
- SemPKM `.planning/research/PITFALLS.md` — pitfall catalog; HIGH confidence for all 9 pitfalls and their solutions
- SemPKM `CLAUDE.md` — project guidelines; HIGH confidence for Lucide icon flex-shrink rule (applies to tab component)
- SemPKM `.planning/REQUIREMENTS.md` — DOCK-01 requirement definition
- SemPKM `.planning/STATE.md` — DEC-04 locked decision, current position (Phase 29 complete)

### Secondary (MEDIUM confidence)

- SemPKM `.planning/research/ARCHITECTURE.md` section "Component Registration" code examples — synthesized from official dockview docs + direct codebase analysis; MEDIUM (exact 4.11.0 API property names require verification at implementation time)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — dockview-core 4.11.0 committed in DEC-04; CDN delivery verified; bridge CSS pre-built; no new dependencies
- Architecture: HIGH — based on direct 1073-line codebase analysis of workspace-layout.js + workspace.html structure; line-level change mapping produced
- Pitfalls: HIGH — confirmed via dockview GitHub issues #341/#718/#996 + official htmx docs + direct codebase inspection of drag system conflict

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (dockview 4.11.0 is a pinned version — API stable; 30-day validity)
