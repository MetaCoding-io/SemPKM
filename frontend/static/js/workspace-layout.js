/**
 * SemPKM WorkspaceLayout (dockview-core 4.11.0)
 *
 * Replaces Split.js/custom-drag editor-group system with dockview-core.
 * WorkspaceLayout class is retained as a minimal metadata sidecar.
 *
 * Exposes on window:
 *   window._workspaceLayout   - the active WorkspaceLayout instance (metadata sidecar)
 *   window._dockview           - the DockviewComponent instance
 *   window._tabMeta            - { [panelId]: { label, dirty, typeIcon, typeColor } }
 *   window.getActiveEditorArea()
 *   window.splitRight(groupId)
 *   window.setActiveGroup(groupId)
 *   window.initWorkspaceLayout()
 *   window.switchTabInGroup(tabId, groupId)
 *   window.closeTabInGroup(tabId, groupId)
 *   window.renderGroupTabBar(group)
 *   window.loadTabInGroup(groupId, tabId)
 */

(function () {
  'use strict';

  var DV_LAYOUT_KEY = 'sempkm_workspace_layout_dv';

  // Resolve DockviewComponent from CDN global (namespaced or direct)
  var DockviewComponent = (typeof DockviewCore !== 'undefined')
    ? DockviewCore.DockviewComponent
    : window.DockviewComponent;

  // Reference to the layout instance (set by initWorkspaceLayout)
  var layout = null;

  // Tab metadata sidecar: { [panelId]: { label, dirty, typeIcon, typeColor } }
  var _tabMeta = {};

  // -----------------------------------------------------------------------
  // WorkspaceLayout class (minimal metadata sidecar)
  // -----------------------------------------------------------------------

  function WorkspaceLayout() {
    this._dv = null;         // reference to DockviewComponent
    this.activeGroupId = null; // track for backward-compat reads
  }

  // -----------------------------------------------------------------------
  // createComponent factory
  // -----------------------------------------------------------------------

  function createComponentFn(options) {
    if (options.name === 'object-editor') {
      return {
        init: function (params) {
          var iri = params.params.iri;
          htmx.ajax('GET', '/browser/object/' + encodeURIComponent(iri), {
            target: params.containerElement, swap: 'innerHTML'
          });
          // Visibility handler: re-measure CodeMirror when panel re-shown
          params.api.onDidVisibilityChange(function (event) {
            if (!event.isVisible) return;
            if (window._editorInstances && window._editorInstances[iri]) {
              var cm = window._editorInstances[iri];
              if (cm.requestMeasure) cm.requestMeasure();
              else if (cm.refresh) cm.refresh();
            }
          });
        }
      };
    }
    if (options.name === 'view-panel') {
      return {
        init: function (params) {
          var vt = params.params.viewType;
          var vid = params.params.viewId;
          var url = '/browser/views/' + vt + '/' + encodeURIComponent(vid);
          htmx.ajax('GET', url, { target: params.containerElement, swap: 'innerHTML' });
          params.api.onDidVisibilityChange(function (event) {
            if (!event.isVisible) return;
            if (window._cytoscapeInstances && window._cytoscapeInstances[vid]) {
              var cy = window._cytoscapeInstances[vid];
              cy.resize(); cy.fit();
            }
          });
        }
      };
    }
    if (options.name === 'special-panel') {
      return {
        init: function (params) {
          var st = params.params.specialType;
          htmx.ajax('GET', '/browser/' + st, { target: params.containerElement, swap: 'innerHTML' });
        }
      };
    }
    return { init: function () {} };
  }

  // -----------------------------------------------------------------------
  // Default layout builder
  // -----------------------------------------------------------------------

  function buildDefaultLayout(dv) {
    // Empty workspace -- dockview shows empty group UI by default.
    // No panels needed; workspace.js will add panels as user navigates.
  }

  // -----------------------------------------------------------------------
  // Initialization
  // -----------------------------------------------------------------------

  function initWorkspaceLayout() {
    var container = document.getElementById('editor-groups-container');
    if (!container) return;

    // Clear old sessionStorage format (migration)
    sessionStorage.removeItem('sempkm_workspace_layout');

    // Create dockview
    var dv = new DockviewComponent(container, {
      createComponent: createComponentFn
    });

    // Wire layout change: save to sessionStorage + re-process htmx on reparented panels
    dv.onDidLayoutChange(function () {
      try {
        sessionStorage.setItem(DV_LAYOUT_KEY, JSON.stringify(dv.toJSON()));
      } catch (e) {}
      document.querySelectorAll('.dv-content-container').forEach(function (el) {
        htmx.process(el);
      });
    });

    // Wire active panel change: dispatch sempkm:tab-activated
    dv.onDidActivePanelChange(function (panel) {
      if (!panel) return;
      var params = panel.params || {};
      var isObjectTab = !params.isView && !params.isSpecial;
      var groupId = panel.group ? panel.group.id : null;
      document.dispatchEvent(new CustomEvent('sempkm:tab-activated', {
        detail: { tabId: panel.id, groupId: groupId, isObjectTab: isObjectTab }
      }));
      if (isObjectTab && typeof loadRightPaneSection === 'function') {
        loadRightPaneSection(panel.id, 'relations');
        loadRightPaneSection(panel.id, 'lint');
      }
      if (layout) layout.activeGroupId = groupId;
    });

    // Wire panel remove: dispatch sempkm:tabs-empty when no object panels remain
    dv.onDidRemovePanel(function () {
      var hasObjectPanel = dv.panels.some(function (p) {
        return p.params && !p.params.isView && !p.params.isSpecial;
      });
      if (!hasObjectPanel) {
        document.dispatchEvent(new CustomEvent('sempkm:tabs-empty'));
      }
    });

    // Restore saved layout or build default
    var saved = null;
    try {
      var raw = sessionStorage.getItem(DV_LAYOUT_KEY);
      if (raw) saved = JSON.parse(raw);
    } catch (e) {}

    if (saved) {
      try {
        dv.fromJSON(saved);
      } catch (err) {
        console.warn('SemPKM: saved dockview layout incompatible, rebuilding.', err);
        sessionStorage.removeItem(DV_LAYOUT_KEY);
        // Do NOT call dv.clear() -- causes second "Invalid grid element" error
        buildDefaultLayout(dv);
      }
    } else {
      buildDefaultLayout(dv);
    }

    // Export
    window._dockview = dv;
    layout = new WorkspaceLayout();
    layout._dv = dv;
    window._workspaceLayout = layout;
    window._tabMeta = _tabMeta;
  }

  // -----------------------------------------------------------------------
  // Public API functions
  // -----------------------------------------------------------------------

  /**
   * Returns the content container of the active dockview panel.
   * Replaces all hard-coded document.getElementById('editor-area') calls.
   */
  function getActiveEditorArea() {
    var dv = window._dockview;
    if (dv && dv.activePanel && dv.activePanel.view) {
      return dv.activePanel.view.contentContainer;
    }
    return null;
  }

  /**
   * Split the editor to the right, duplicating the active panel's content.
   */
  function splitRight(groupId) {
    var dv = window._dockview;
    if (!dv) return;
    var activePanel = dv.activePanel;
    if (!activePanel) return;
    var newId = activePanel.id + '-split-' + Date.now();
    _tabMeta[newId] = Object.assign({}, _tabMeta[activePanel.id] || {}, { dirty: false });
    dv.addPanel({
      id: newId,
      component: activePanel.view.contentComponent,
      params: Object.assign({}, activePanel.params),
      title: activePanel.title,
      position: { referencePanel: activePanel.id, direction: 'right' }
    });
  }

  /**
   * Focus an editor group by id.
   * With dockview, groups are implicit -- backward-compat stub.
   */
  function setActiveGroup(groupId) {
    if (layout) layout.activeGroupId = groupId;
  }

  /**
   * Switch to a tab (panel) within a group.
   */
  function switchTabInGroup(tabId, groupId) {
    var dv = window._dockview;
    if (!dv) return;
    var panel = dv.getGroupPanel(tabId);
    if (panel) panel.api.setActive();
  }

  /**
   * Close a tab (panel).
   */
  function closeTabInGroup(tabId, groupId) {
    var dv = window._dockview;
    if (!dv) return;
    var panel = dv.getGroupPanel(tabId);
    if (panel) panel.api.close();
    delete _tabMeta[tabId];
  }

  /**
   * No-op stub -- dockview renders tab bars natively.
   * Tab metadata updates happen via window._tabMeta[panelId].
   */
  function renderGroupTabBar(group) {
    // no-op stub
  }

  /**
   * Load a tab in a group -- delegate to switchTabInGroup for backward compat.
   */
  function loadTabInGroup(groupId, tabId) {
    switchTabInGroup(tabId, groupId);
  }

  /**
   * Close all other tabs in a group, keeping only keepTabId.
   */
  function closeOtherTabsInGroup(keepTabId, groupId) {
    var dv = window._dockview;
    if (!dv) return;
    var toClose = dv.panels.filter(function (p) { return p.id !== keepTabId; });
    toClose.forEach(function (p) {
      p.api.close();
      delete _tabMeta[p.id];
    });
  }

  // -----------------------------------------------------------------------
  // Tab context menu
  // -----------------------------------------------------------------------

  function showTabContextMenu(e, tabId, groupId) {
    e.preventDefault();
    e.stopPropagation();

    // Remove any existing context menu
    var existing = document.getElementById('tab-context-menu');
    if (existing) existing.remove();

    var menu = document.createElement('div');
    menu.id = 'tab-context-menu';
    menu.className = 'context-menu';

    var items = [
      { label: 'Close', action: function () { closeTabInGroup(tabId, groupId); } },
      { label: 'Close Others', action: function () { closeOtherTabsInGroup(tabId, groupId); } },
      { label: '---' },
      { label: 'Split Right', action: function () { splitRight(groupId); } }
    ];

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

    document.body.appendChild(menu);
    var menuRect = menu.getBoundingClientRect();
    var x = Math.min(e.clientX, window.innerWidth - menuRect.width - 8);
    var y = Math.min(e.clientY, window.innerHeight - menuRect.height - 8);
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';

    function dismissClick(e2) {
      if (!menu.contains(e2.target)) {
        menu.remove();
        document.removeEventListener('click', dismissClick);
        document.removeEventListener('keydown', dismissKey);
      }
    }

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

  window._workspaceLayout = null;  // set by initWorkspaceLayout()
  window._dockview = null;          // set by initWorkspaceLayout()
  window._tabMeta = {};             // set by initWorkspaceLayout()
  window.getActiveEditorArea = getActiveEditorArea;
  window.splitRight = splitRight;
  window.setActiveGroup = setActiveGroup;
  window.initWorkspaceLayout = initWorkspaceLayout;
  window.switchTabInGroup = switchTabInGroup;
  window.closeTabInGroup = closeTabInGroup;
  window.renderGroupTabBar = renderGroupTabBar;
  window.loadTabInGroup = loadTabInGroup;

})();
