/**
 * SemPKM WorkspaceLayout
 *
 * Manages multiple editor groups (1-4 horizontal splits) within the editor pane.
 * Implements the data model from EDITOR-GROUPS-DESIGN.md (Phase 10, plan 10-03).
 *
 * Exposes on window:
 *   window._workspaceLayout   - the active WorkspaceLayout instance
 *   window.getActiveEditorArea()
 *   window.splitRight(groupId)
 *   window.setActiveGroup(groupId)
 *   window.initWorkspaceLayout()
 */

(function () {
  'use strict';

  var LAYOUT_KEY = 'sempkm_workspace_layout';

  // The horizontal Split.js instance between editor groups (null when 1 group)
  var groupSplitInstance = null;

  // Reference to the layout instance (set by initWorkspaceLayout)
  var layout = null;

  // -----------------------------------------------------------------------
  // Migration: old sempkm_open_tabs / sempkm_active_tab → sempkm_workspace_layout
  // -----------------------------------------------------------------------

  function migrateTabState() {
    if (sessionStorage.getItem(LAYOUT_KEY)) return; // already migrated

    var oldTabs = [];
    try {
      oldTabs = JSON.parse(sessionStorage.getItem('sempkm_open_tabs') || '[]');
    } catch (e) {
      oldTabs = [];
    }
    var oldActive = sessionStorage.getItem('sempkm_active_tab');

    var newLayout = {
      groups: [{
        id: 'group-1',
        tabs: oldTabs,
        activeTabId: oldActive || (oldTabs.length > 0 ? (oldTabs[0].iri || oldTabs[0].id) : null),
        size: 100
      }],
      activeGroupId: 'group-1'
    };

    try {
      sessionStorage.setItem(LAYOUT_KEY, JSON.stringify(newLayout));
      sessionStorage.removeItem('sempkm_open_tabs');
      sessionStorage.removeItem('sempkm_active_tab');
    } catch (e) {
      // sessionStorage blocked — continue without persisting
    }
  }

  // -----------------------------------------------------------------------
  // WorkspaceLayout class
  // -----------------------------------------------------------------------

  function WorkspaceLayout() {
    this.groups = [];
    this.activeGroupId = null;
  }

  /**
   * Add a new editor group (max 4). Returns new group id or null if at max.
   */
  WorkspaceLayout.prototype.addGroup = function () {
    if (this.groups.length >= 4) return null;

    var id = 'group-' + Date.now();
    var equalSize = 100 / (this.groups.length + 1);

    this.groups.forEach(function (g) { g.size = equalSize; });
    this.groups.push({ id: id, tabs: [], activeTabId: null, size: equalSize });

    this.save();
    recreateGroupSplit(this);
    return id;
  };

  /**
   * Remove a group. If last group, no-op. Tabs are redistributed to left neighbor.
   */
  WorkspaceLayout.prototype.removeGroup = function (groupId) {
    if (this.groups.length === 1) return; // never remove last group

    var idx = this.groups.findIndex(function (g) { return g.id === groupId; });
    if (idx === -1) return;

    var removed = this.groups.splice(idx, 1)[0];

    // Redistribute tabs to left neighbor (or first group if idx was 0)
    var neighborIdx = Math.max(0, idx - 1);
    var neighbor = this.groups[neighborIdx];
    removed.tabs.forEach(function (t) { neighbor.tabs.push(t); });

    // Recalculate equal sizes
    var equalSize = 100 / this.groups.length;
    this.groups.forEach(function (g) { g.size = equalSize; });

    // Update active group if the removed one was active
    if (this.activeGroupId === groupId) {
      this.activeGroupId = neighbor.id;
    }

    this.save();
    recreateGroupSplit(this);
  };

  /**
   * Move a tab from one group to another, optionally at a specific position.
   * If source group becomes empty and is not the last group, it is removed.
   */
  WorkspaceLayout.prototype.moveTab = function (tabId, sourceGroupId, targetGroupId, insertBeforeTabId) {
    var sourceGroup = this.getGroup(sourceGroupId);
    var targetGroup = this.getGroup(targetGroupId);
    if (!sourceGroup || !targetGroup) return;

    // Find and remove from source
    var tabIdx = sourceGroup.tabs.findIndex(function (t) { return (t.id || t.iri) === tabId; });
    if (tabIdx === -1) return;

    var tab = sourceGroup.tabs.splice(tabIdx, 1)[0];

    // Update source activeTabId if needed
    if (sourceGroup.activeTabId === tabId) {
      if (sourceGroup.tabs.length > 0) {
        var nextIdx = Math.min(tabIdx, sourceGroup.tabs.length - 1);
        sourceGroup.activeTabId = sourceGroup.tabs[nextIdx].id || sourceGroup.tabs[nextIdx].iri;
      } else {
        sourceGroup.activeTabId = null;
      }
    }

    // Insert into target at correct position
    if (insertBeforeTabId) {
      var insertIdx = targetGroup.tabs.findIndex(function (t) { return (t.id || t.iri) === insertBeforeTabId; });
      if (insertIdx !== -1) {
        targetGroup.tabs.splice(insertIdx, 0, tab);
      } else {
        targetGroup.tabs.push(tab);
      }
    } else {
      targetGroup.tabs.push(tab);
    }

    // If source is empty and there is more than one group, remove it
    if (sourceGroup.tabs.length === 0 && this.groups.length > 1) {
      this.removeGroup(sourceGroupId);
      // removeGroup already calls save() and recreateGroupSplit()
      return;
    }

    this.save();

    // Partial re-render of both tab bars
    renderGroupTabBar(sourceGroup);
    renderGroupTabBar(targetGroup);
  };

  /**
   * Add a tab object to a group.
   */
  WorkspaceLayout.prototype.addTabToGroup = function (tab, groupId) {
    var group = this.getGroup(groupId);
    if (!group) return;

    var tabId = tab.id || tab.iri;
    var existing = group.tabs.find(function (t) { return (t.id || t.iri) === tabId; });
    if (!existing) {
      // Normalize: ensure both .id and .iri are set
      if (!tab.id) tab.id = tab.iri;
      if (!tab.iri) tab.iri = tab.id;
      group.tabs.push(tab);
    }

    group.activeTabId = tabId;
    this.save();
    renderGroupTabBar(group);
  };

  /**
   * Remove a tab from a group. If it was the last tab and not the last group,
   * remove the group. If it was the last tab of the last group, show empty state.
   */
  WorkspaceLayout.prototype.removeTabFromGroup = function (tabId, groupId) {
    var group = this.getGroup(groupId);
    if (!group) return;

    var idx = group.tabs.findIndex(function (t) { return (t.id || t.iri) === tabId; });
    if (idx === -1) return;

    group.tabs.splice(idx, 1);

    // Update active tab for this group
    if (group.activeTabId === tabId) {
      if (group.tabs.length > 0) {
        var nextIdx = Math.min(idx, group.tabs.length - 1);
        group.activeTabId = group.tabs[nextIdx].id || group.tabs[nextIdx].iri;
      } else {
        group.activeTabId = null;
      }
    }

    // If group is now empty and it's not the only group, remove it
    if (group.tabs.length === 0 && this.groups.length > 1) {
      this.removeGroup(groupId);
      return;
    }

    this.save();
    renderGroupTabBar(group);

    // If tab was active, load the new active tab or show empty state
    if (this.activeGroupId === groupId) {
      if (group.activeTabId) {
        loadTabInGroup(groupId, group.activeTabId);
      } else {
        showGroupEmpty(groupId);
      }
    }
  };

  /**
   * Set the focused editor group.
   */
  WorkspaceLayout.prototype.setActiveGroup = function (groupId) {
    this.activeGroupId = groupId;

    // Update active class on group containers
    document.querySelectorAll('.editor-group').forEach(function (el) {
      el.classList.remove('editor-group-active');
    });
    var activeEl = document.getElementById(groupId);
    if (activeEl) activeEl.classList.add('editor-group-active');

    this.save();
  };

  /**
   * Get a group by id.
   */
  WorkspaceLayout.prototype.getGroup = function (groupId) {
    return this.groups.find(function (g) { return g.id === groupId; }) || null;
  };

  /**
   * Persist to sessionStorage.
   */
  WorkspaceLayout.prototype.save = function () {
    try {
      sessionStorage.setItem(LAYOUT_KEY, JSON.stringify({
        groups: this.groups,
        activeGroupId: this.activeGroupId
      }));
    } catch (e) {
      // sessionStorage might be blocked
    }
  };

  /**
   * Restore from sessionStorage. Returns WorkspaceLayout or null.
   */
  WorkspaceLayout.restore = function () {
    try {
      var raw = sessionStorage.getItem(LAYOUT_KEY);
      if (raw) {
        var data = JSON.parse(raw);
        var l = new WorkspaceLayout();
        l.groups = data.groups || [];
        l.activeGroupId = data.activeGroupId || null;
        return l;
      }
    } catch (e) {
      // corrupted storage — fall through to create fresh
    }
    return null;
  };

  // -----------------------------------------------------------------------
  // DOM: recreate editor groups and Split.js instance
  // -----------------------------------------------------------------------

  function recreateGroupSplit(layoutObj) {
    var editorPane = document.getElementById('editor-pane');
    if (!editorPane) return;

    // 1. Destroy existing horizontal split
    if (groupSplitInstance) {
      try { groupSplitInstance.destroy(); } catch (e) {}
      groupSplitInstance = null;
    }

    // 2. Run cleanup for any registered instances inside the pane
    //    (CodeMirror, per-group vertical Split.js, etc.)
    if (typeof window.runCleanup === 'function') {
      // Fire cleanup for each group container before clearing innerHTML
      var existingGroups = editorPane.querySelectorAll('.editor-group');
      existingGroups.forEach(function (el) {
        window.runCleanup(el.id);
      });
    }

    // 3. Clear and rebuild DOM
    //    Preserve #bottom-panel-slot if it exists
    var bottomPanelSlot = document.getElementById('bottom-panel-slot');
    editorPane.innerHTML = '';

    // Recreate the editor-groups-container
    var groupsContainer = document.createElement('div');
    groupsContainer.className = 'editor-groups-container';
    groupsContainer.id = 'editor-groups-container';
    editorPane.appendChild(groupsContainer);

    layoutObj.groups.forEach(function (group) {
      var div = document.createElement('div');
      div.className = 'editor-group';
      div.id = group.id;

      var tabBar = document.createElement('div');
      tabBar.className = 'group-tab-bar tab-bar-workspace';
      tabBar.id = 'tab-bar-' + group.id;

      var editorArea = document.createElement('div');
      editorArea.className = 'group-editor-area';
      editorArea.id = 'editor-area-' + group.id;

      div.appendChild(tabBar);
      div.appendChild(editorArea);
      groupsContainer.appendChild(div);

      // Wire group focus on click
      div.addEventListener('mousedown', function () {
        if (layout && layout.activeGroupId !== group.id) {
          layout.setActiveGroup(group.id);
        }
      });
    });

    // Restore bottom-panel-slot after rebuilding groups container
    if (bottomPanelSlot) {
      editorPane.appendChild(bottomPanelSlot);
    } else {
      // Create placeholder for Plan 03
      var slot = document.createElement('div');
      slot.id = 'bottom-panel-slot';
      editorPane.appendChild(slot);
    }

    // 4. Create horizontal Split.js between groups (only when 2+ groups)
    if (layoutObj.groups.length > 1) {
      var selectors = layoutObj.groups.map(function (g) { return '#' + g.id; });
      var sizes = layoutObj.groups.map(function (g) { return g.size; });

      groupSplitInstance = Split(selectors, {
        sizes: sizes,
        minSize: 200,
        gutterSize: 1,
        gutterClass: 'gutter-editor-groups',
        cursor: 'col-resize',
        onDragEnd: function (s) {
          layoutObj.groups.forEach(function (g, i) { g.size = s[i]; });
          layoutObj.save();
        }
      });
    }

    // 5. Render tab bars and restore active content in each group
    layoutObj.groups.forEach(function (group) {
      renderGroupTabBar(group);
      if (group.activeTabId) {
        loadTabInGroup(group.id, group.activeTabId);
      } else {
        showGroupEmpty(group.id);
      }
    });

    // 6. Apply active group styling
    layoutObj.setActiveGroup(layoutObj.activeGroupId);

    // 7. Wire right-edge drop zone on the groups container
    initRightEdgeDropZone();
  }

  // -----------------------------------------------------------------------
  // Drag-and-Drop state
  // -----------------------------------------------------------------------

  var isDragging = false;

  // -----------------------------------------------------------------------
  // Tab Drag initiation
  // -----------------------------------------------------------------------

  function initTabDrag(tabEl, tabId, groupId) {
    tabEl.setAttribute('draggable', 'true');

    tabEl.addEventListener('dragstart', function (e) {
      isDragging = true;
      e.dataTransfer.setData('text/plain', JSON.stringify({ tabId: tabId, sourceGroupId: groupId }));
      e.dataTransfer.effectAllowed = 'move';

      // Create custom ghost image: styled clone of the tab
      var ghost = tabEl.cloneNode(true);
      ghost.style.opacity = '0.7';
      ghost.style.position = 'fixed';
      ghost.style.top = '-1000px';
      document.body.appendChild(ghost);
      e.dataTransfer.setDragImage(ghost, 20, 10);
      setTimeout(function () { if (ghost.parentNode) { ghost.parentNode.removeChild(ghost); } }, 0);

      tabEl.classList.add('dragging');
    });

    tabEl.addEventListener('dragend', function () {
      tabEl.classList.remove('dragging');
      // Clear all drop indicators
      document.querySelectorAll('.drop-indicator').forEach(function (el) {
        el.classList.remove('drop-indicator-active');
      });
      document.querySelectorAll('.group-tab-bar').forEach(function (el) {
        el.classList.remove('tab-bar-drag-over');
      });
      // Reset isDragging after click event has fired (Pitfall 3)
      setTimeout(function () { isDragging = false; }, 0);

      // Hide right-edge drop zone
      var rightEdge = document.getElementById('right-edge-drop-zone');
      if (rightEdge) rightEdge.classList.remove('active');
    });
  }

  // -----------------------------------------------------------------------
  // Tab Bar drop zone
  // -----------------------------------------------------------------------

  function initTabBarDropZone(tabBarEl, targetGroupId) {
    tabBarEl.addEventListener('dragover', function (e) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      tabBarEl.classList.add('tab-bar-drag-over');
      _updateInsertionIndicator(tabBarEl, e.clientX);
    });

    tabBarEl.addEventListener('dragleave', function (e) {
      // Only remove drag-over state if leaving the tab bar entirely
      if (!tabBarEl.contains(e.relatedTarget)) {
        tabBarEl.classList.remove('tab-bar-drag-over');
        var indicator = tabBarEl.querySelector('.drop-indicator');
        if (indicator) indicator.classList.remove('drop-indicator-active');
      }
    });

    tabBarEl.addEventListener('drop', function (e) {
      e.preventDefault();
      tabBarEl.classList.remove('tab-bar-drag-over');
      var indicator = tabBarEl.querySelector('.drop-indicator');
      if (indicator) indicator.classList.remove('drop-indicator-active');

      var raw = e.dataTransfer.getData('text/plain');
      if (!raw) return;
      var data;
      try { data = JSON.parse(raw); } catch (err) { return; }

      // Determine insert position from indicator position
      var insertBeforeTabId = _getInsertBeforeTabId(tabBarEl, e.clientX);

      if (layout) {
        layout.moveTab(data.tabId, data.sourceGroupId, targetGroupId, insertBeforeTabId);
        // Load moved tab in target group
        loadTabInGroup(targetGroupId, data.tabId);
      }
    });
  }

  // -----------------------------------------------------------------------
  // Insertion indicator helper
  // -----------------------------------------------------------------------

  function _updateInsertionIndicator(tabBarEl, clientX) {
    var indicator = tabBarEl.querySelector('.drop-indicator');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.className = 'drop-indicator';
      tabBarEl.appendChild(indicator);
    }

    var tabs = tabBarEl.querySelectorAll('.workspace-tab');
    var found = false;
    var tabBarRect = tabBarEl.getBoundingClientRect();

    tabs.forEach(function (tab) {
      if (found) return;
      var rect = tab.getBoundingClientRect();
      var midX = rect.left + rect.width / 2;
      if (clientX < midX) {
        indicator.style.left = (rect.left - tabBarRect.left + tabBarEl.scrollLeft) + 'px';
        found = true;
      }
    });

    if (!found) {
      indicator.style.left = tabBarEl.scrollWidth + 'px';
    }

    indicator.classList.add('drop-indicator-active');
  }

  function _getInsertBeforeTabId(tabBarEl, clientX) {
    var tabs = tabBarEl.querySelectorAll('.workspace-tab');
    var result = null;

    tabs.forEach(function (tab) {
      if (result !== null) return;
      var rect = tab.getBoundingClientRect();
      var midX = rect.left + rect.width / 2;
      if (clientX < midX) {
        result = tab.getAttribute('data-tab-id');
      }
    });

    return result;
  }

  // -----------------------------------------------------------------------
  // Right-edge drop zone
  // -----------------------------------------------------------------------

  function initRightEdgeDropZone() {
    var container = document.getElementById('editor-groups-container');
    if (!container) return;

    // Create or get the right-edge indicator overlay
    var rightEdge = document.getElementById('right-edge-drop-zone');
    if (!rightEdge) {
      rightEdge = document.createElement('div');
      rightEdge.id = 'right-edge-drop-zone';
      container.style.position = 'relative';
      container.appendChild(rightEdge);
    }

    container.addEventListener('dragover', function (e) {
      if (!layout) return;
      var containerRect = container.getBoundingClientRect();
      var inRightZone = e.clientX > containerRect.right - 80;

      if (inRightZone && layout.groups.length < 4) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        rightEdge.classList.add('active');
      } else {
        rightEdge.classList.remove('active');
      }
    });

    container.addEventListener('dragleave', function (e) {
      if (!container.contains(e.relatedTarget)) {
        rightEdge.classList.remove('active');
      }
    });

    container.addEventListener('drop', function (e) {
      var containerRect = container.getBoundingClientRect();
      var inRightZone = e.clientX > containerRect.right - 80;

      if (!inRightZone || !layout) return;

      e.preventDefault();
      rightEdge.classList.remove('active');

      var raw = e.dataTransfer.getData('text/plain');
      if (!raw) return;
      var data;
      try { data = JSON.parse(raw); } catch (err) { return; }

      var newGroupId = layout.addGroup();
      if (!newGroupId) return; // at max groups
      var newGroup = layout.getGroup(newGroupId);
      if (!newGroup) return;

      layout.moveTab(data.tabId, data.sourceGroupId, newGroupId, null);
      loadTabInGroup(newGroupId, data.tabId);
    });
  }

  // -----------------------------------------------------------------------
  // Tab Bar rendering
  // -----------------------------------------------------------------------

  function renderGroupTabBar(group) {
    var tabBar = document.getElementById('tab-bar-' + group.id);
    if (!tabBar) return;

    // Clear tab bar
    tabBar.innerHTML = '';

    if (!group.tabs || group.tabs.length === 0) {
      var emptyEl = document.createElement('div');
      emptyEl.className = 'tab-empty-state';
      emptyEl.textContent = 'No objects open';
      tabBar.appendChild(emptyEl);
      initTabBarDropZone(tabBar, group.id);
      return;
    }

    group.tabs.forEach(function (tab) {
      var tabId = tab.id || tab.iri;
      var isActive = tabId === group.activeTabId;
      var isView = tab.isView || (tabId && tabId.indexOf('view:') === 0);

      var tabEl = document.createElement('div');
      tabEl.className = 'workspace-tab' + (isActive ? ' active' : '') + (isView ? ' view-tab' : '');
      tabEl.setAttribute('data-tab-id', tabId);
      tabEl.setAttribute('data-group-id', group.id);

      if (isView) {
        var vt = tab.viewType || '';
        var iconMap = { table: '\u25A6', card: '\u25E9', graph: '\u25C8' };
        var iconChar = iconMap[vt] || '\u25B6';
        var iconEl = document.createElement('span');
        iconEl.className = 'tab-view-icon';
        iconEl.setAttribute('title', 'View: ' + vt);
        iconEl.textContent = iconChar;
        tabEl.appendChild(iconEl);
      }

      var labelEl = document.createElement('span');
      labelEl.className = 'tab-label';
      labelEl.textContent = tab.label || tabId;
      tabEl.appendChild(labelEl);

      if (tab.dirty) {
        var dirtyEl = document.createElement('span');
        dirtyEl.className = 'tab-dirty';
        dirtyEl.setAttribute('title', 'Unsaved changes');
        tabEl.appendChild(dirtyEl);
      }

      var closeBtn = document.createElement('button');
      closeBtn.className = 'tab-close';
      closeBtn.setAttribute('title', 'Close tab');
      closeBtn.textContent = '\u00D7';
      closeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        closeTabInGroup(tabId, group.id);
      });
      tabEl.appendChild(closeBtn);

      // Click to switch tab (with isDragging guard per Pitfall 3)
      tabEl.addEventListener('click', function () {
        if (isDragging) return;
        switchTabInGroup(tabId, group.id);
      });

      // Context menu
      tabEl.addEventListener('contextmenu', function (e) {
        showTabContextMenu(e, tabId, group.id);
      });

      // Wire drag-and-drop
      initTabDrag(tabEl, tabId, group.id);

      tabBar.appendChild(tabEl);
    });

    // Make tab bar a drop zone
    initTabBarDropZone(tabBar, group.id);
  }

  // -----------------------------------------------------------------------
  // Tab content loading
  // -----------------------------------------------------------------------

  function loadTabInGroup(groupId, tabId) {
    var group = layout ? layout.getGroup(groupId) : null;
    if (!group) return;

    var tab = group.tabs.find(function (t) { return (t.id || t.iri) === tabId; });
    if (!tab) return;

    var editorArea = document.getElementById('editor-area-' + groupId);
    if (!editorArea) return;

    // Show loading state
    editorArea.innerHTML = '<div class="editor-skeleton">' +
      '<div class="skeleton-line" style="width: 60%"></div>' +
      '<div class="skeleton-line" style="width: 80%"></div>' +
      '<div class="skeleton-line" style="width: 40%"></div>' +
      '</div>';

    var url;

    if (tab.isView || (tabId && tabId.indexOf('view:') === 0)) {
      // View tab
      var viewId = tab.viewId || (tabId.indexOf('view:') === 0 ? tabId.substring(5) : tabId);
      var viewType = tab.viewType || 'table';
      if (viewType === 'table') url = '/browser/views/table/' + encodeURIComponent(viewId);
      else if (viewType === 'card') url = '/browser/views/card/' + encodeURIComponent(viewId);
      else if (viewType === 'graph') url = '/browser/views/graph/' + encodeURIComponent(viewId);
      else url = '/browser/views/table/' + encodeURIComponent(viewId);
    } else {
      // Object tab
      url = '/browser/object/' + encodeURIComponent(tabId);
    }

    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', url, {
        target: '#editor-area-' + groupId,
        swap: 'innerHTML'
      }).catch(function () {
        var el = document.getElementById('editor-area-' + groupId);
        if (el) el.innerHTML = '<div class="editor-empty"><p>Failed to load content.</p></div>';
      });
    } else {
      editorArea.innerHTML = '<div class="editor-empty"><p>Loading...</p></div>';
    }
  }

  function showGroupEmpty(groupId) {
    var editorArea = document.getElementById('editor-area-' + groupId);
    if (editorArea) {
      editorArea.innerHTML = '<div class="editor-empty">' +
        '<p>Select an object from the Explorer to open it here.</p>' +
        '<p class="hint">Or press <kbd>Ctrl</kbd>+<kbd>K</kbd> to open the command palette.</p>' +
        '</div>';
    }
  }

  // -----------------------------------------------------------------------
  // Public API functions
  // -----------------------------------------------------------------------

  /**
   * Returns the editor area element for the currently active group.
   * Replaces all hard-coded document.getElementById('editor-area') calls.
   */
  function getActiveEditorArea() {
    if (layout && layout.activeGroupId) {
      return document.getElementById('editor-area-' + layout.activeGroupId);
    }
    // Fallback: first group
    var firstGroup = document.querySelector('.group-editor-area');
    return firstGroup;
  }

  /**
   * Split the editor to the right of the given group.
   * Loads the active tab of the source group into the new group (duplicate allowed).
   */
  function splitRight(groupId) {
    if (!layout) return;

    var sourceGroup = layout.getGroup(groupId || layout.activeGroupId);
    if (!sourceGroup) return;

    var newGroupId = layout.addGroup();
    if (!newGroupId) return; // at max

    // Focus the new group
    layout.setActiveGroup(newGroupId);

    // If source had an active tab, duplicate it in the new group
    if (sourceGroup.activeTabId) {
      var sourceTab = sourceGroup.tabs.find(function (t) {
        return (t.id || t.iri) === sourceGroup.activeTabId;
      });
      if (sourceTab) {
        var dupTab = {
          id: sourceTab.id || sourceTab.iri,
          iri: sourceTab.iri || sourceTab.id,
          label: sourceTab.label,
          dirty: false,
          isView: sourceTab.isView || false,
          viewType: sourceTab.viewType,
          viewId: sourceTab.viewId
        };
        var newGroup = layout.getGroup(newGroupId);
        if (newGroup) {
          newGroup.tabs.push(dupTab);
          newGroup.activeTabId = dupTab.id;
          layout.save();
          renderGroupTabBar(newGroup);
          loadTabInGroup(newGroupId, dupTab.id);
        }
      }
    }
  }

  /**
   * Focus an editor group by id.
   */
  function setActiveGroup(groupId) {
    if (layout) {
      layout.setActiveGroup(groupId);
    }
  }

  /**
   * Switch to a tab within a specific group (called from rendered tab HTML).
   */
  function switchTabInGroup(tabId, groupId) {
    if (!layout) return;

    var group = layout.getGroup(groupId);
    if (!group) return;

    group.activeTabId = tabId;
    layout.activeGroupId = groupId;
    layout.save();

    renderGroupTabBar(group);
    layout.setActiveGroup(groupId);
    loadTabInGroup(groupId, tabId);
  }

  /**
   * Close a tab within a specific group (called from rendered tab HTML).
   */
  function closeTabInGroup(tabId, groupId) {
    if (!layout) return;
    layout.removeTabFromGroup(tabId, groupId);
  }

  /**
   * Show right-click context menu on a tab.
   * Pattern from 14-RESEARCH.md Pattern 6.
   */
  function showTabContextMenu(e, tabId, groupId) {
    e.preventDefault();
    e.stopPropagation();

    // Remove any existing context menu
    var existing = document.getElementById('tab-context-menu');
    if (existing) existing.remove();

    var menu = document.createElement('div');
    menu.id = 'tab-context-menu';
    menu.className = 'context-menu';

    // Build menu items
    var items = [
      { label: 'Close', action: function () { closeTabInGroup(tabId, groupId); } },
      { label: 'Close Others', action: function () { closeOtherTabsInGroup(tabId, groupId); } },
      { label: '---' },
      { label: 'Split Right', action: function () { splitRight(groupId); } }
    ];

    // Add "Move to Group" entries when multiple groups exist
    if (layout) {
      var otherGroups = layout.groups.filter(function (g) { return g.id !== groupId; });
      otherGroups.forEach(function (g, idx) {
        var label = 'Move to Group ' + (layout.groups.indexOf(g) + 1);
        items.push({ label: label, action: function () {
          layout.moveTab(tabId, groupId, g.id, null);
          loadTabInGroup(g.id, tabId);
        }});
      });
    }

    items.forEach(function (item) {
      if (item.label === '---') {
        var sep = document.createElement('div');
        sep.className = 'context-menu-separator';
        menu.appendChild(sep);
        return;
      }
      var li = document.createElement('div');
      li.className = 'context-menu-item';
      li.textContent = item.label;
      if (item.action) {
        li.addEventListener('click', function () {
          item.action();
          menu.remove();
        });
      }
      menu.appendChild(li);
    });

    // Append to body, then position (needs to be in DOM for getBoundingClientRect)
    document.body.appendChild(menu);
    var menuRect = menu.getBoundingClientRect();
    var x = Math.min(e.clientX, window.innerWidth - menuRect.width - 8);
    var y = Math.min(e.clientY, window.innerHeight - menuRect.height - 8);
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';

    // Dismiss on outside click
    function dismissClick(e2) {
      if (!menu.contains(e2.target)) {
        menu.remove();
        document.removeEventListener('click', dismissClick);
        document.removeEventListener('keydown', dismissKey);
      }
    }

    // Dismiss on Escape
    function dismissKey(e2) {
      if (e2.key === 'Escape') {
        menu.remove();
        document.removeEventListener('click', dismissClick);
        document.removeEventListener('keydown', dismissKey);
      }
    }

    setTimeout(function () {
      document.addEventListener('click', dismissClick);
      document.addEventListener('keydown', dismissKey);
    }, 0);
  }

  /**
   * Close all other tabs in a group, keeping only keepTabId.
   */
  function closeOtherTabsInGroup(keepTabId, groupId) {
    if (!layout) return;
    var group = layout.getGroup(groupId);
    if (!group) return;
    var toClose = group.tabs.filter(function (t) {
      return (t.id || t.iri) !== keepTabId;
    }).map(function (t) { return t.id || t.iri; });
    toClose.forEach(function (tabId) {
      layout.removeTabFromGroup(tabId, groupId);
    });
  }

  // -----------------------------------------------------------------------
  // Initialization
  // -----------------------------------------------------------------------

  function initWorkspaceLayout() {
    // 1. Migrate old tab state if needed
    migrateTabState();

    // 2. Restore or create fresh layout
    layout = WorkspaceLayout.restore();

    if (!layout) {
      layout = new WorkspaceLayout();
      layout.groups = [{ id: 'group-1', tabs: [], activeTabId: null, size: 100 }];
      layout.activeGroupId = 'group-1';
      layout.save();
    }

    // Ensure activeGroupId is valid
    if (!layout.getGroup(layout.activeGroupId)) {
      layout.activeGroupId = layout.groups.length > 0 ? layout.groups[0].id : 'group-1';
    }

    // 3. Build DOM and Split.js
    recreateGroupSplit(layout);

    // 4. Export layout instance
    window._workspaceLayout = layout;
  }

  // -----------------------------------------------------------------------
  // Utilities
  // -----------------------------------------------------------------------

  function _escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
  }

  function _escapeJs(str) {
    if (!str) return '';
    return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
  }

  // -----------------------------------------------------------------------
  // Window exports
  // -----------------------------------------------------------------------

  window._workspaceLayout = null; // set by initWorkspaceLayout()
  window.getActiveEditorArea = getActiveEditorArea;
  window.splitRight = splitRight;
  window.setActiveGroup = setActiveGroup;
  window.initWorkspaceLayout = initWorkspaceLayout;
  window.switchTabInGroup = switchTabInGroup;
  window.closeTabInGroup = closeTabInGroup;
  window.renderGroupTabBar = renderGroupTabBar;
  window.loadTabInGroup = loadTabInGroup;

})();
