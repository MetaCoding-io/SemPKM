/**
 * SemPKM IDE Workspace
 *
 * Manages the three-column resizable layout (Split.js), keyboard shortcuts,
 * and command palette (ninja-keys).
 *
 * Tab state is now delegated to dockview (workspace-layout.js).
 * All openTab/closeTab/switchTab functions delegate to window._dockview.
 */

(function () {
  'use strict';

  // --- Constants ---
  var PANE_KEY = 'sempkm_pane_sizes';
  var PANEL_KEY = 'sempkm_bottom_panel';
  var PANEL_POSITIONS_KEY = 'sempkm_panel_positions';
  var FUZZY_KEY = 'sempkm_fts_fuzzy';

  // --- Toast Notifications ---

  function showToast(message, duration) {
    duration = duration || 3000;
    var toast = document.createElement('div');
    toast.className = 'sempkm-toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    requestAnimationFrame(function () { toast.classList.add('sempkm-toast--visible'); });
    setTimeout(function () {
      toast.classList.remove('sempkm-toast--visible');
      setTimeout(function () { toast.remove(); }, 300);
    }, duration);
  }

  // --- Bottom Panel State ---
  var panelState = { open: false, height: 30, activeTab: 'event-log', maximized: false };

  // --- Split.js Initialization ---
  var splitInstance = null;
  var lastFullSizes = null;   // canonical 3-pane sizes [nav%, editor%, right%]
  var hiddenPanes = {};       // { 'nav-pane': true, 'right-pane': true }
  var defaultSizes = [20, 50, 30];

  function initSplit() {
    if (typeof Split === 'undefined') {
      console.warn('Split.js not loaded yet, retrying...');
      setTimeout(initSplit, 100);
      return;
    }

    // Restore saved pane sizes (only accept valid 3-element arrays)
    try {
      var saved = localStorage.getItem(PANE_KEY);
      if (saved) {
        var parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length === 3) {
          lastFullSizes = parsed;
        }
      }
    } catch (e) {
      lastFullSizes = null;
    }

    splitInstance = Split(['#nav-pane', '#editor-pane', '#right-pane'], {
      sizes: lastFullSizes || defaultSizes,
      minSize: [180, 300, 200],
      gutterSize: 5,
      cursor: 'col-resize',
      onDragEnd: function (sizes) {
        if (Object.keys(hiddenPanes).length === 0) {
          lastFullSizes = sizes.slice();
        }
        try { localStorage.setItem(PANE_KEY, JSON.stringify(sizes)); } catch (e) {}
      }
    });
  }

  // --- Tab Management (delegates to dockview) ---

  function openTab(objectIri, label, mode) {
    var dv = window._dockview;
    if (!dv) {
      loadObjectContent(objectIri, mode);
      return;
    }

    // Check if already open — focus it
    var existing = dv.panels.find(function(p) { return p.id === objectIri; });
    if (existing) {
      existing.api.setActive();
      return;
    }

    // Register tab metadata before addPanel (so createComponent can read it if needed)
    if (!window._tabMeta) window._tabMeta = {};
    window._tabMeta[objectIri] = { label: label || objectIri, dirty: false };

    dv.api.addPanel({
      id: objectIri,
      component: 'object-editor',
      params: { iri: objectIri, isView: false, isSpecial: false, mode: mode },
      title: label || objectIri
    });

    // sempkm:tab-activated is dispatched by workspace-layout.js onDidActivePanelChange — no double-dispatch here

    addObjectToCommandPalette(objectIri, label);
  }

  // --- View Tab Support ---

  function openViewTab(viewId, viewLabel, viewType) {
    var tabKey = 'view:' + viewId;
    var dv = window._dockview;
    if (!dv) {
      loadViewContent(viewId, viewType);
      return;
    }

    var existing = dv.panels.find(function(p) { return p.id === tabKey; });
    if (existing) {
      existing.api.setActive();
      return;
    }

    if (!window._tabMeta) window._tabMeta = {};
    window._tabMeta[tabKey] = { label: viewLabel, dirty: false };

    dv.api.addPanel({
      id: tabKey,
      component: 'view-panel',
      params: { viewId: viewId, viewType: viewType, isView: true, isSpecial: false },
      title: viewLabel
    });
  }

  function loadViewContent(viewId, viewType) {
    var editorArea = window.getActiveEditorArea ? window.getActiveEditorArea() : document.getElementById('editor-area-group-1');
    if (!editorArea) return;

    var url;
    if (viewType === 'table') {
      url = '/browser/views/table/' + encodeURIComponent(viewId);
    } else if (viewType === 'card') {
      url = '/browser/views/card/' + encodeURIComponent(viewId);
    } else if (viewType === 'graph') {
      url = '/browser/views/graph/' + encodeURIComponent(viewId);
    } else if (viewType === 'canvas') {
      url = '/browser/canvas';
    } else {
      url = '/browser/views/table/' + encodeURIComponent(viewId);
    }

    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', url, {
        target: editorArea,
        swap: 'innerHTML'
      }).catch(function () {
        editorArea.innerHTML = '<div class="editor-empty"><p>Failed to load view.</p></div>';
      });
    }
  }

  function closeTab(objectIri) {
    var dv = window._dockview;
    if (!dv) return;
    var panel = dv.panels.find(function(p) { return p.id === objectIri; });
    if (panel) {
      panel.api.close();
      if (window._tabMeta) delete window._tabMeta[objectIri];
    }
  }

  function switchTab(objectIri) {
    var dv = window._dockview;
    if (!dv) return;
    var panel = dv.panels.find(function(p) { return p.id === objectIri; });
    if (panel) {
      panel.api.setActive();
    }
  }

  // Internal: switch tab in a specific group (also exposed as window.switchTabInGroup
  // by workspace-layout.js, but we define a local alias for internal use)
  function switchTabInGroup(tabId, groupId) {
    if (window.switchTabInGroup) {
      window.switchTabInGroup(tabId, groupId);
    }
  }

  function markDirty(objectIri) {
    if (!window._tabMeta) return;
    if (window._tabMeta[objectIri]) {
      window._tabMeta[objectIri].dirty = true;
    }
  }

  function markClean(objectIri) {
    if (!window._tabMeta) return;
    if (window._tabMeta[objectIri]) {
      window._tabMeta[objectIri].dirty = false;
    }
  }

  function getActiveTabIri() {
    var dv = window._dockview;
    if (!dv || !dv.activePanel) return null;
    return dv.activePanel.id;
  }

  function loadObjectContent(objectIri, mode) {
    var editorArea = window.getActiveEditorArea ? window.getActiveEditorArea() : document.getElementById('editor-area-group-1');
    if (!editorArea) return;

    // If IRI starts with 'view:', load as view tab
    if (objectIri && objectIri.indexOf('view:') === 0) {
      var dv = window._dockview;
      var viewType = 'table';
      if (dv) {
        var panel = dv.panels.find(function(p) { return p.id === objectIri; });
        if (panel && panel.params && panel.params.viewType) {
          viewType = panel.params.viewType;
        }
      }
      var viewId = objectIri.substring(5);
      loadViewContent(viewId, viewType);
      return;
    }

    // Build URL with optional mode parameter
    var url = '/browser/object/' + encodeURIComponent(objectIri);
    if (mode === 'edit') {
      url += '?mode=edit';
    }

    // Use htmx to load object content into active editor area
    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', url, {
        target: editorArea,
        swap: 'innerHTML'
      }).catch(function () {
        editorArea.innerHTML = '<div class="editor-empty"><p>Failed to load object.</p></div>';
      });

      // Load both right pane sections
      loadRightPaneSection(objectIri, 'relations');
      loadRightPaneSection(objectIri, 'lint');
    } else {
      editorArea.innerHTML = '<div class="editor-empty"><p>Loading ' + escapeHtml(objectIri) + '...</p></div>';
    }
  }

  function loadRightPaneSection(objectIri, section) {
    var targetId = section + '-content';
    var url;

    if (section === 'lint') {
      url = '/browser/lint/' + encodeURIComponent(objectIri);
    } else {
      url = '/browser/relations/' + encodeURIComponent(objectIri);
    }

    fetch(url, { headers: { 'HX-Request': 'true' } })
      .then(function (resp) { return resp.text(); })
      .then(function (html) {
        var el = document.getElementById(targetId);
        if (el) el.innerHTML = html;
      })
      .catch(function () {
        var el = document.getElementById(targetId);
        if (el) el.innerHTML = '<div class="right-empty">Failed to load content</div>';
      });
  }

  function showEditorEmpty() {
    var editorArea = window.getActiveEditorArea ? window.getActiveEditorArea() : document.getElementById('editor-area-group-1');
    if (editorArea) {
      editorArea.innerHTML = '<div class="editor-empty">' +
        '<p>Select an object from the Explorer to open it here.</p>' +
        '<p class="hint">Or press <kbd>Ctrl</kbd>+<kbd>K</kbd> to open the command palette.</p>' +
        '</div>';
    }
  }

  // --- Bottom Panel ---

  function restorePanelState() {
    try {
      var saved = localStorage.getItem(PANEL_KEY);
      if (saved) {
        Object.assign(panelState, JSON.parse(saved));
      }
    } catch (e) {
      // localStorage unavailable or corrupt -- use defaults
    }
  }

  function savePanelState() {
    try {
      localStorage.setItem(PANEL_KEY, JSON.stringify(panelState));
    } catch (e) {
      // localStorage unavailable
    }
  }

  function _applyPanelState() {
    var panel = document.getElementById('bottom-panel');
    var handle = document.getElementById('panel-resize-handle');
    var editorCol = document.querySelector('.editor-column');

    if (!panel || !editorCol) return;

    if (!panelState.open) {
      panel.style.height = '0';
      if (handle) handle.classList.remove('panel-open');
      editorCol.classList.remove('panel-maximized');
    } else if (panelState.maximized) {
      panel.style.height = '';
      if (handle) handle.classList.add('panel-open');
      editorCol.classList.add('panel-maximized');
    } else {
      if (handle) handle.classList.add('panel-open');
      editorCol.classList.remove('panel-maximized');
      // Set height in pixels (not %) to avoid pitfall with flex layout
      var parentH = panel.parentElement ? panel.parentElement.getBoundingClientRect().height : 0;
      if (parentH > 0) {
        panel.style.height = (parentH * panelState.height / 100) + 'px';
      } else {
        panel.style.height = '30vh';
      }
    }

    // Set active panel tab and pane
    var tabs = document.querySelectorAll('.panel-tab');
    tabs.forEach(function (tab) { tab.classList.remove('active'); });
    var activeTab = document.querySelector('.panel-tab[data-panel="' + panelState.activeTab + '"]');
    if (activeTab) activeTab.classList.add('active');

    var panes = document.querySelectorAll('.panel-pane');
    panes.forEach(function (pane) { pane.classList.remove('active'); });
    var activePaneId = 'panel-' + panelState.activeTab;
    var activePane = document.getElementById(activePaneId);
    if (activePane) activePane.classList.add('active');

    // Re-init Lucide icons if panel is open
    if (panelState.open && typeof lucide !== 'undefined') {
      lucide.createIcons({ attrs: { class: ['lucide'] } });
    }

    // Auto-load event log when panel opens with event-log as active tab
    // (e.g. restoring state on page load, or toggling panel open via Ctrl+J)
    if (panelState.open && panelState.activeTab === 'event-log') {
      var pane = document.getElementById('panel-event-log');
      if (pane && pane.querySelector('.panel-placeholder')) {
        htmx.ajax('GET', '/browser/events', {
          target: '#panel-event-log',
          swap: 'innerHTML'
        });
      }
    }
  }

  function toggleBottomPanel() {
    panelState.open = !panelState.open;
    panelState.maximized = false;
    _applyPanelState();
    savePanelState();
  }

  function maximizeBottomPanel() {
    if (!panelState.open) panelState.open = true;
    panelState.maximized = !panelState.maximized;
    _applyPanelState();
    savePanelState();
  }

  function initBottomPanelResize() {
    var handle = document.getElementById('panel-resize-handle');
    var panel = document.getElementById('bottom-panel');
    if (!handle || !panel) return;

    var startY, startHeight;

    function onMouseMove(e) {
      var delta = startY - e.clientY;
      var workspaceH = panel.parentElement ? panel.parentElement.getBoundingClientRect().height : 0;
      var newHeight = Math.max(80, Math.min(startHeight + delta, workspaceH * 0.8));
      panel.style.height = newHeight + 'px';
      if (workspaceH > 0) {
        panelState.height = (newHeight / workspaceH * 100);
      }
    }

    function onMouseUp() {
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
      savePanelState();
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    }

    handle.addEventListener('mousedown', function (e) {
      e.preventDefault();
      startY = e.clientY;
      startHeight = panel.getBoundingClientRect().height;
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'row-resize';
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    });
  }

  function initPanelTabs() {
    document.querySelectorAll('.panel-tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        panelState.activeTab = btn.dataset.panel;
        savePanelState();
        _applyPanelState();

        // Lazy-load event log on first activation (replace placeholder with real content)
        if (btn.dataset.panel === 'event-log') {
          var pane = document.getElementById('panel-event-log');
          if (pane && pane.querySelector('.panel-placeholder')) {
            htmx.ajax('GET', '/browser/events', {
              target: '#panel-event-log',
              swap: 'innerHTML'
            });
          }
        }

      });
    });
  }

  function initBottomPanel() {
    var maximizeBtn = document.getElementById('panel-maximize-btn');
    if (maximizeBtn) {
      maximizeBtn.addEventListener('click', maximizeBottomPanel);
    }
    var closeBtn = document.getElementById('panel-close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', toggleBottomPanel);
    }
    initPanelTabs();
    initBottomPanelResize();
    restorePanelState();
    _applyPanelState();
  }

  // --- Pane Toggle ---

  function togglePane(paneId) {
    if (!splitInstance) return;
    var pane = document.getElementById(paneId);
    if (!pane) return;
    var panes = ['nav-pane', 'editor-pane', 'right-pane'];
    if (panes.indexOf(paneId) === -1) return;

    if (hiddenPanes[paneId]) {
      // Show: remove from hiddenPanes, un-hide DOM element and its gutter
      delete hiddenPanes[paneId];
      pane.style.display = '';
      var gutter = pane.previousElementSibling;
      if (gutter && gutter.classList.contains('gutter')) gutter.style.display = '';
    } else {
      // Hide: capture lastFullSizes on first hide, add to hiddenPanes, hide DOM
      if (Object.keys(hiddenPanes).length === 0) {
        lastFullSizes = splitInstance.getSizes().slice();
      }
      hiddenPanes[paneId] = true;
      pane.style.display = 'none';
      var gutter2 = pane.previousElementSibling;
      if (gutter2 && gutter2.classList.contains('gutter')) gutter2.style.display = 'none';
    }

    _rebuildFromCanonical();
  }

  function _rebuildFromCanonical() {
    var panes = ['nav-pane', 'editor-pane', 'right-pane'];
    var base = lastFullSizes || defaultSizes;
    var visibleIds = [];
    var visibleSizes = [];
    panes.forEach(function (id, i) {
      var el = document.getElementById(id);
      if (el && el.style.display !== 'none') {
        visibleIds.push('#' + id);
        visibleSizes.push(base[i]);
      }
    });
    var total = visibleSizes.reduce(function (a, b) { return a + b; }, 0);
    if (total > 0 && Math.abs(total - 100) > 0.5) {
      visibleSizes = visibleSizes.map(function (s) { return (s / total) * 100; });
    }
    _rebuildSplit(null, visibleIds, visibleSizes);
  }

  function _rebuildSplit(restoreSizes, visibleIds, visibleSizes) {
    if (splitInstance) splitInstance.destroy();

    var panes = ['nav-pane', 'editor-pane', 'right-pane'];
    var ids = visibleIds || panes.filter(function (id) {
      var el = document.getElementById(id);
      return el && el.style.display !== 'none';
    }).map(function (id) { return '#' + id; });

    var minSizes = ids.map(function (id) {
      if (id === '#editor-pane') return 300;
      if (id === '#nav-pane') return 180;
      return 200;
    });

    var sizes = visibleSizes || ids.map(function () { return 100 / ids.length; });

    splitInstance = Split(ids, {
      sizes: sizes,
      minSize: minSizes,
      gutterSize: 5,
      cursor: 'col-resize',
      onDragEnd: function (s) {
        if (Object.keys(hiddenPanes).length === 0) {
          lastFullSizes = s.slice();
        }
        try { localStorage.setItem(PANE_KEY, JSON.stringify(s)); } catch (e) {}
      }
    });
  }

  // --- Object Mode Toggle (Read/Edit) ---
  // Edit button first-touch investigation (phase 19-02):
  //   safe_id encoding: object_tab.html computes it as
  //   {{ object_iri | urlencode | replace('%', '_') }} — the button onclick
  //   passes '{{ safe_id }}' directly (same variable). The window key is set as
  //   window['_initEditMode_' + safeId] in the IIFE that runs during htmx swap.
  //   Both use the same safe_id value so no mismatch exists.
  //   The _initEditMode_ function is defined before any click is possible (script
  //   runs during htmx afterSwap, user cannot click before that completes).
  //   The `if (typeof initFn === 'function') initFn()` guard at line 594 is correct.
  //   First-touch is therefore expected to work. If a regression occurs, verify
  //   that workspace.js loads before object_tab.html content is inserted into DOM.

  function toggleObjectMode(safeId, objectIri) {
    var flipInner = document.getElementById('flip-inner-' + safeId);
    var toggleBtn = document.getElementById('mode-toggle-' + safeId);
    var saveBtn = document.getElementById('save-btn-' + safeId);
    if (!flipInner) return;

    var readFace = flipInner.querySelector('.object-face-read');
    var editFace = flipInner.querySelector('.object-face-edit');
    var isFlipped = flipInner.classList.contains('flipped');

    if (isFlipped) {
      // Switching from edit to read: check for unsaved changes
      var isDirty = false;
      if (window._tabMeta && window._tabMeta[objectIri]) {
        isDirty = window._tabMeta[objectIri].dirty;
      }

      if (isDirty) {
        if (!window.confirm('Discard unsaved changes?')) return;
        markClean(objectIri);
      }
      flipInner.classList.remove('flipped');
      if (toggleBtn) toggleBtn.textContent = 'Edit';
      if (saveBtn) saveBtn.style.display = 'none';
      // Refresh read face with fresh data from server
      if (readFace) {
        fetch('/browser/object/' + encodeURIComponent(objectIri) + '?mode=read', {
          headers: { 'HX-Request': 'true' }
        }).then(function (resp) { return resp.text(); }).then(function (html) {
          // Extract the read face content from the full response
          var tmp = document.createElement('div');
          tmp.innerHTML = html;
          var freshRead = tmp.querySelector('.object-face-read');
          if (freshRead) {
            readFace.innerHTML = freshRead.innerHTML;
            // Re-trigger markdown rendering for any md-source/md-rendered pairs
            var mdSources = readFace.querySelectorAll('script[type="text/plain"][id^="md-source-"]');
            mdSources.forEach(function (src) {
              var renderedId = src.id.replace('md-source-', 'md-rendered-');
              var tgt = document.getElementById(renderedId);
              if (src && tgt && typeof window.renderMarkdownBody === 'function') {
                window.renderMarkdownBody(src.id, renderedId);
              } else if (src && tgt) {
                tgt.textContent = src.textContent;
              }
            });
            // Re-apply properties collapse state after read face refresh
            if (typeof window.initPropertiesState === 'function') {
              var badge = readFace.closest('.object-tab');
              var badgeBtn = badge ? badge.querySelector('.properties-toggle-badge') : null;
              var hasBody = badgeBtn ? badgeBtn.dataset.hasBody === 'true' : true;
              window.initPropertiesState(safeId, objectIri, hasBody);
            }
          }
        }).catch(function () { /* keep stale content on error */ });
      }
      // Swap faces at midpoint (300ms into 600ms animation)
      setTimeout(function () {
        if (readFace) readFace.classList.remove('face-hidden');
        if (editFace) editFace.classList.remove('face-visible');
      }, 300);
    } else {
      // Switching from read to edit: initialize edit mode if needed
      var initFn = window['_initEditMode_' + safeId];
      if (typeof initFn === 'function') initFn();
      flipInner.classList.add('flipped');
      if (toggleBtn) toggleBtn.textContent = 'Cancel';
      if (saveBtn) saveBtn.style.display = '';
      // Swap faces at midpoint (300ms into 600ms animation)
      setTimeout(function () {
        if (readFace) readFace.classList.add('face-hidden');
        if (editFace) editFace.classList.add('face-visible');
      }, 300);
    }
  }

  // --- Autocomplete dropdown position (phase 19-02 investigation) ---
  // Autocomplete suggestion dropdowns use position:fixed (workspace.css line 1099)
  // with z-index:9999 and are positioned via getBoundingClientRect() in the
  // htmx:afterSwap handler in object_form.html (lines 238-253). The scroll/resize
  // reposition handler in object_form.html (lines 255-275) keeps dropdowns anchored.
  // No fix needed: position:fixed already escapes overflow:hidden containers.

  // --- Settings Tab ---

  function openSettingsTab() {
    var tabKey = 'special:settings';
    var dv = window._dockview;
    if (!dv) return;

    var existing = dv.panels.find(function(p) { return p.id === tabKey; });
    if (existing) { existing.api.setActive(); return; }

    if (!window._tabMeta) window._tabMeta = {};
    window._tabMeta[tabKey] = { label: 'Settings', dirty: false };

    dv.api.addPanel({
      id: tabKey,
      component: 'special-panel',
      params: { specialType: 'settings', isView: false, isSpecial: true },
      title: 'Settings'
    });
  }
  window.openSettingsTab = openSettingsTab;

  // --- Docs Tab ---
  // Docs tab investigation (phase 19-02):
  //   _sidebar.html calls openDocsTab() via onclick. This function is exposed as
  //   window.openDocsTab below. workspace.js loads synchronously before any user
  //   interaction is possible. loadTabInGroup resolves 'special:docs' to /browser/docs
  //   at workspace-layout.js line 726 (special:docs branch). No bug found — the
  //   implementation follows the same pattern as openSettingsTab() (Phase 18-01).

  function openDocsTab() {
    var tabKey = 'special:docs';
    var dv = window._dockview;
    if (!dv) return;

    var existing = dv.panels.find(function(p) { return p.id === tabKey; });
    if (existing) { existing.api.setActive(); return; }

    if (!window._tabMeta) window._tabMeta = {};
    window._tabMeta[tabKey] = { label: 'Docs & Tutorials', dirty: false };

    dv.api.addPanel({
      id: tabKey,
      component: 'special-panel',
      params: { specialType: 'docs', isView: false, isSpecial: true },
      title: 'Docs & Tutorials'
    });
  }
  window.openDocsTab = openDocsTab;


  function openCanvasTab() {
    var tabKey = 'special:canvas';
    var dv = window._dockview;
    if (!dv) return;

    var existing = dv.panels.find(function(p) { return p.id === tabKey; });
    if (existing) { existing.api.setActive(); return; }

    if (!window._tabMeta) window._tabMeta = {};
    window._tabMeta[tabKey] = { label: 'Spatial Canvas', dirty: false };

    dv.api.addPanel({
      id: tabKey,
      component: 'special-panel',
      params: { specialType: 'canvas', isView: false, isSpecial: true },
      title: 'Spatial Canvas'
    });
  }
  window.openCanvasTab = openCanvasTab;

  // --- Keyboard Shortcuts ---

  var _keydownHandler = null;

  function initKeyboardShortcuts() {
    if (_keydownHandler) {
      document.removeEventListener('keydown', _keydownHandler);
    }
    _keydownHandler = function (e) {
      var isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      var mod = isMac ? e.metaKey : e.ctrlKey;

      // Ctrl+S / Cmd+S: Save current object
      if (mod && e.key === 's') {
        e.preventDefault();
        saveCurrentObject();
      }

      // Ctrl+W / Cmd+W: Close current tab
      if (mod && e.key === 'w') {
        e.preventDefault();
        var activeIri = getActiveTabIri();
        if (activeIri) {
          closeTab(activeIri);
        }
      }

      // Ctrl+\ / Cmd+\: Split Right (reassigned from sidebar toggle per Phase 14 CONTEXT.md)
      // Sidebar toggle remains on Ctrl+B (Phase 12)
      if (mod && e.key === '\\') {
        e.preventDefault();
        if (typeof window.splitRight === 'function') {
          window.splitRight();
        }
      }

      // Ctrl+[ / Cmd+[: Toggle explorer pane
      if (mod && e.key === '[') {
        e.preventDefault();
        togglePane('nav-pane');
      }

      // Ctrl+] / Cmd+]: Toggle right panel
      if (mod && e.key === ']') {
        e.preventDefault();
        togglePane('right-pane');
      }

      // Ctrl+E / Cmd+E: Toggle read/edit mode
      if (mod && e.key === 'e') {
        e.preventDefault();
        var editorArea = window.getActiveEditorArea ? window.getActiveEditorArea() : null;
        if (editorArea) {
          var objectTab = editorArea.querySelector('.object-tab');
          if (objectTab) {
            var iri = objectTab.dataset.objectIri;
            var safeId = encodeURIComponent(iri).replace(/%/g, '_');
            toggleObjectMode(safeId, iri);
          }
        }
      }

      // Ctrl+K / Cmd+K: Open command palette
      if (mod && e.key === 'k') {
        e.preventDefault();
        var ninja = document.querySelector('ninja-keys');
        if (ninja) {
          ninja.open();
        }
      }

      // Ctrl+J / Cmd+J: Toggle bottom panel
      if (mod && e.key === 'j') {
        e.preventDefault();
        toggleBottomPanel();
      }

      // Ctrl+, / Cmd+,: Open Settings tab
      if (mod && e.key === ',') {
        e.preventDefault();
        openSettingsTab();
        return;
      }

      // Ctrl+1/2/3/4: Focus editor group by index
      if (mod && ['1', '2', '3', '4'].indexOf(e.key) !== -1) {
        e.preventDefault();
        var idx = parseInt(e.key) - 1;
        var dv2 = window._dockview;
        if (dv2 && dv2.groups && dv2.groups[idx]) {
          dv2.groups[idx].focus();
        }
      }
    };
    document.addEventListener('keydown', _keydownHandler);
  }

  function saveCurrentObject() {
    var activeIri = getActiveTabIri();
    if (!activeIri) return;

    var editorArea = window.getActiveEditorArea ? window.getActiveEditorArea() : document.getElementById('editor-area-group-1');
    var activeTab = editorArea ? editorArea.querySelector('.object-tab') : null;

    // Save form properties via htmx form submission
    if (activeTab) {
      var form = activeTab.querySelector('#object-form');
      if (form && typeof htmx !== 'undefined') {
        htmx.trigger(form, 'submit');
      }
    }

    // Save body via editor.js (CodeMirror)
    if (typeof window.getEditor === 'function') {
      var editor = window.getEditor(activeIri);
      if (editor) {
        var content = editor.state.doc.toString();
        var bodyContainer = activeTab ? activeTab.querySelector('.codemirror-container') : null;
        var bodyPredicate = bodyContainer && bodyContainer.dataset.bodyPredicate ? bodyContainer.dataset.bodyPredicate : '';
        var bodyUrl = '/browser/objects/' + encodeURIComponent(activeIri) + '/body';
        if (bodyPredicate) bodyUrl += '?predicate=' + encodeURIComponent(bodyPredicate);
        fetch(bodyUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'text/plain' },
          body: content
        }).then(function (resp) {
          if (resp.ok) {
            editor._sempkmSavedContent = content;
            markClean(activeIri);
            refreshLintAfterSave(activeIri);
          }
        }).catch(function (err) {
          console.error('Body save error:', err);
        });
        return;
      }
    }

    // Fallback: plain textarea editor
    if (activeTab) {
      var fallback = activeTab.querySelector('.body-fallback');
      if (fallback && fallback.dataset && fallback.dataset.objectIri) {
        var fbContent = fallback.value || '';
        var fbPredicate = fallback.dataset.bodyPredicate || '';
        var fbUrl = '/browser/objects/' + encodeURIComponent(fallback.dataset.objectIri) + '/body';
        if (fbPredicate) fbUrl += '?predicate=' + encodeURIComponent(fbPredicate);
        fetch(fbUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'text/plain' },
          body: fbContent
        }).then(function (resp) {
          if (resp.ok) {
            markClean(fallback.dataset.objectIri);
            refreshLintAfterSave(fallback.dataset.objectIri);
          }
        }).catch(function (err) {
          console.error('Body save error:', err);
        });
      }
    }

    // Also submit the form if it exists (properties save)
    var form = document.getElementById('object-form');
    if (form && typeof htmx !== 'undefined') {
      htmx.trigger(form, 'submit');
    }
  }

  function refreshLintAfterSave(objectIri) {
    // Refresh the lint panel after a short delay (validation queue processes async)
    setTimeout(function () {
      loadRightPaneSection(objectIri, 'lint');
    }, 2000);
  }

  // --- Command Palette ---

  function initCommandPalette() {
    customElements.whenDefined('ninja-keys').then(function () {
      var ninja = document.querySelector('ninja-keys');
      if (!ninja) return;

      // Patch open/close to reflect state as an HTML attribute so tests
      // and external code can detect open state via getAttribute('opened').
      var _origOpen = ninja.open.bind(ninja);
      var _origClose = ninja.close.bind(ninja);
      ninja.open = function (options) { _origOpen(options); ninja.setAttribute('opened', ''); };
      ninja.close = function () { _origClose(); ninja.removeAttribute('opened'); };

      ninja.data = [
        {
          id: 'new-object',
          title: 'New Object',
          section: 'Objects',
          hotkey: 'ctrl+n',
          handler: function () { showTypePicker(); }
        },
        {
          id: 'run-validation',
          title: 'Run Validation',
          section: 'Tools',
          hotkey: 'ctrl+shift+v',
          handler: function () { triggerValidation(); }
        },
        {
          id: 'split-right',
          title: 'Split Right',
          section: 'View',
          hotkey: 'ctrl+\\',
          handler: function () {
            if (typeof window.splitRight === 'function') window.splitRight();
          }
        },
        {
          id: 'close-group',
          title: 'Close Group',
          section: 'View',
          handler: function () {
            var dv = window._dockview;
            if (dv && dv.activeGroup) {
              dv.activeGroup.api.close();
            }
          }
        },
        {
          id: 'toggle-panel',
          title: 'Toggle Panel',
          section: 'View',
          hotkey: 'ctrl+j',
          handler: function () { toggleBottomPanel(); }
        },
        {
          id: 'maximize-panel',
          title: 'Maximize Panel',
          section: 'View',
          handler: function () { maximizeBottomPanel(); }
        },
        {
          id: 'toggle-explorer',
          title: 'Toggle Explorer Panel',
          section: 'View',
          hotkey: 'ctrl+[',
          handler: function () { togglePane('nav-pane'); }
        },
        {
          id: 'toggle-right',
          title: 'Toggle Details Panel',
          section: 'View',
          hotkey: 'ctrl+]',
          handler: function () { togglePane('right-pane'); }
        },
        {
          id: 'open-view-menu',
          title: 'Open View Menu',
          section: 'Views',
          handler: function () { openViewMenu(); }
        },
        {
          id: 'theme-light',
          title: 'Theme: Light',
          section: 'Appearance',
          handler: function () { setTheme('light'); }
        },
        {
          id: 'theme-dark',
          title: 'Theme: Dark',
          section: 'Appearance',
          handler: function () { setTheme('dark'); }
        },
        {
          id: 'theme-system',
          title: 'Theme: System Default',
          section: 'Appearance',
          handler: function () { setTheme('system'); }
        },
        {
          id: 'toggle-edit-mode',
          title: 'Toggle Edit Mode',
          section: 'Objects',
          hotkey: 'ctrl+e',
          handler: function () {
            var editorArea = window.getActiveEditorArea ? window.getActiveEditorArea() : null;
            if (editorArea) {
              var activeTab = editorArea.querySelector('.object-tab');
              if (activeTab) {
                var objectIri = activeTab.dataset.objectIri;
                var flipContainer = activeTab.querySelector('.object-flip-container');
                if (flipContainer) {
                  var safeId = flipContainer.id.replace('flip-', '');
                  toggleObjectMode(safeId, objectIri);
                }
              }
            }
          }
        },
        // --- Layout Management ---
        {
          id: 'layout-save-as',
          title: 'Layout: Save As...',
          section: 'Layout',
          children: ['layout-save-confirm']
        },
        {
          id: 'layout-save-confirm',
          title: 'Type a layout name above, then select this item to save',
          parent: 'layout-save-as',
          handler: function () {
            var ninjaEl = document.querySelector('ninja-keys');
            var name = '';
            if (ninjaEl) {
              // Try shadowRoot input (the search field ninja-keys uses)
              try {
                var input = ninjaEl.shadowRoot.querySelector('input[type="text"]');
                if (input) name = input.value;
              } catch (e) {}
              // Fallback: ninja-keys may expose _search or .search property
              if (!name && ninjaEl._search) name = ninjaEl._search;
            }
            name = name ? name.trim() : '';
            if (!name) {
              showToast('Please type a layout name in the search field first', 3000);
              return;
            }
            window.SemPKMLayouts.save(name);
            showToast('Layout "' + name + '" saved');
            _refreshLayoutPaletteItems(ninjaEl);
          }
        },
        {
          id: 'layout-restore',
          title: 'Layout: Restore...',
          section: 'Layout',
          children: []   // populated by _refreshLayoutPaletteItems
        },
        {
          id: 'layout-delete',
          title: 'Layout: Delete...',
          section: 'Layout',
          children: []   // populated by _refreshLayoutPaletteItems
        }
      ];

      // Dynamically load available views into command palette
      _loadViewCommandPaletteEntries(ninja);
      _addCanvasPaletteEntry(ninja);

      // Initialize FTS search integration for Ctrl+K palette
      _initFtsSearch(ninja);

      // Populate layout restore/delete children from saved layouts
      _refreshLayoutPaletteItems(ninja);
    }).catch(function () {
      console.warn('ninja-keys custom element not available');
    });
  }

  function openViewMenu() {
    var editorArea = window.getActiveEditorArea ? window.getActiveEditorArea() : document.getElementById('editor-area-group-1');
    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', '/browser/views/menu', {
        target: editorArea,
        swap: 'innerHTML'
      }).catch(function () {
        if (editorArea) {
          editorArea.innerHTML = '<div class="editor-empty"><p>Failed to load view menu.</p></div>';
        }
      });
    }
  }


  function _addCanvasPaletteEntry(ninja) {
    if (!ninja || !ninja.data) return;
    var exists = ninja.data.find(function (d) { return d.id === 'nav-spatial-canvas'; });
    if (exists) return;

    ninja.data = ninja.data.concat([{
      id: 'nav-spatial-canvas',
      title: 'Open: Spatial Canvas',
      section: 'Views',
      handler: function () { openCanvasTab(); }
    }]);
  }

  function _loadViewCommandPaletteEntries(ninja) {
    fetch('/browser/views/available')
      .then(function (resp) { return resp.json(); })
      .then(function (views) {
        if (!views || views.length === 0) return;

        var newData = ninja.data.slice();
        views.forEach(function (v) {
          var id = 'view-' + v.spec_iri;
          var exists = newData.find(function (d) { return d.id === id; });
          if (exists) return;

          var icon = '';
          if (v.renderer_type === 'table') icon = 'Table: ';
          else if (v.renderer_type === 'card') icon = 'Cards: ';
          else if (v.renderer_type === 'graph') icon = 'Graph: ';

          newData.push({
            id: id,
            title: 'Browse: ' + icon + v.label,
            section: 'Views',
            handler: function () { openViewTab(v.spec_iri, v.label, v.renderer_type); }
          });
        });
        ninja.data = newData;
      })
      .catch(function () {
        // Silently fail -- views might not be available yet
      });
  }

  /**
   * Map a type IRI to an inline SVG icon string for ninja-keys display.
   * Matches on the local name portion of the type IRI.
   * Falls back to a generic document icon.
   */
  function _typeToIcon(typeIri) {
    if (!typeIri) return '';
    var icons = {
      'Note': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
      'Project': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
      'Person': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
      'Concept': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'
    };
    // Match on the local name of the type IRI
    for (var name in icons) {
      if (typeIri.indexOf(name) !== -1) return icons[name];
    }
    // Default: document icon
    return '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';
  }

  /**
   * Initialize full-text search integration for the ninja-keys command palette.
   * Listens for the 'change' event (fired when search input changes),
   * debounces 300ms, fetches from /api/search, and injects results
   * into the 'Search' section of the palette.
   */
  function _initFtsSearch(ninja) {
    var _ftsDebounce = null;
    var _ftsAbort = null;
    var _fuzzyEnabled = localStorage.getItem(FUZZY_KEY) === 'true';

    function _updateFuzzyTitle() {
      var idx = ninja.data.findIndex(function(d) { return d.id === 'search-fuzzy-toggle'; });
      if (idx === -1) return;
      var newData = ninja.data.slice();
      newData[idx] = Object.assign({}, newData[idx], {
        title: _fuzzyEnabled
          ? 'Search: Fuzzy Mode ON \u2014 click to disable'
          : 'Search: Fuzzy Mode OFF \u2014 click to enable'
      });
      ninja.data = newData;
    }

    // Add fuzzy toggle command. ID does NOT start with 'fts-' so it is never
    // removed by the change listener's startsWith('fts-') filter.
    ninja.data = ninja.data.concat([{
      id: 'search-fuzzy-toggle',
      title: _fuzzyEnabled
        ? 'Search: Fuzzy Mode ON \u2014 click to disable'
        : 'Search: Fuzzy Mode OFF \u2014 click to enable',
      section: 'Search',
      handler: function() {
        _fuzzyEnabled = !_fuzzyEnabled;
        try {
          localStorage.setItem(FUZZY_KEY, String(_fuzzyEnabled));
        } catch (e) {}
        _updateFuzzyTitle();
      }
    }]);

    ninja.addEventListener('change', function(e) {
      var query = (e.detail && e.detail.search) ? e.detail.search : '';
      if (!query || query.length < 2) {
        // Remove FTS result entries only (startsWith 'fts-') — toggle is 'search-fuzzy-toggle'
        ninja.data = ninja.data.filter(function(d) { return !d.id.startsWith('fts-'); });
        return;
      }

      // Debounce 300ms
      clearTimeout(_ftsDebounce);
      if (_ftsAbort) { _ftsAbort.abort(); }

      _ftsDebounce = setTimeout(function() {
        var controller = new AbortController();
        _ftsAbort = controller;

        var url = '/api/search?q=' + encodeURIComponent(query) + '&limit=10'
                + (_fuzzyEnabled ? '&fuzzy=true' : '');

        fetch(url, {
          signal: controller.signal,
          credentials: 'same-origin'
        })
          .then(function(resp) { return resp.ok ? resp.json() : null; })
          .then(function(data) {
            if (!data || !data.results) return;

            // Remove previous FTS result entries, keep non-FTS entries (including toggle)
            var baseData = ninja.data.filter(function(d) { return !d.id.startsWith('fts-'); });

            var ftsItems = data.results.map(function(r) {
              var icon = _typeToIcon(r.type);
              var snippet = r.snippet ? ' \u2014 ' + r.snippet.replace(/<\/?[^>]+>/g, '').substring(0, 60) : '';
              return {
                id: 'fts-' + r.iri,   // Keep 'fts-' prefix — E2E test checks startsWith('fts-')
                title: r.label + snippet,
                section: 'Search',
                icon: icon,
                handler: function() { openTab(r.iri, r.label); }
              };
            });

            ninja.data = baseData.concat(ftsItems);
          })
          .catch(function() {
            // Abort or network error — silently ignore
          });
      }, 300);
    });
  }

  // --- Named Layout Palette Items ---

  function _refreshLayoutPaletteItems(ninja) {
    var baseData = ninja.data.filter(function (d) {
      return !d.id.startsWith('layout-restore-') && !d.id.startsWith('layout-delete-');
    });
    var layouts = window.SemPKMLayouts ? window.SemPKMLayouts.list() : [];
    layouts.forEach(function (l) {
      baseData.push({
        id: 'layout-restore-' + l.name,
        title: l.name,
        parent: 'layout-restore',
        handler: function () {
          var result = window.SemPKMLayouts.restore(l.name);
          if (result.success) {
            showToast('Layout "' + l.name + '" restored');
          } else if (result.skipped.length > 0) {
            showToast('Layout restored with ' + result.skipped.length + ' skipped item(s)', 5000);
          }
        }
      });
      baseData.push({
        id: 'layout-delete-' + l.name,
        title: l.name,
        parent: 'layout-delete',
        handler: function () {
          window.SemPKMLayouts.remove(l.name);
          showToast('Layout "' + l.name + '" deleted');
          _refreshLayoutPaletteItems(ninja);
        }
      });
    });
    ninja.data = baseData;
  }

  function showTypePicker() {
    var editorArea = window.getActiveEditorArea ? window.getActiveEditorArea() : null;

    // If no active panel (empty workspace), create one so the type picker loads
    // into a .group-editor-area (required by hx-target="closest .group-editor-area")
    if (!editorArea && window._dockview) {
      var panelId = '__new-object-' + Date.now();
      if (!window._tabMeta) window._tabMeta = {};
      window._tabMeta[panelId] = { label: 'New Object', dirty: false };
      window._dockview.api.addPanel({
        id: panelId,
        component: 'empty',
        params: { isView: false, isSpecial: false },
        title: 'New Object'
      });
      editorArea = window.getActiveEditorArea ? window.getActiveEditorArea() : null;
    }

    if (!editorArea) editorArea = document.getElementById('editor-area-group-1');

    if (typeof htmx !== 'undefined' && editorArea) {
      htmx.ajax('GET', '/browser/types', {
        target: editorArea,
        swap: 'innerHTML'
      }).catch(function () {
        if (editorArea) {
          editorArea.innerHTML = '<div class="editor-empty"><p>Failed to load type picker.</p></div>';
        }
      });
    }
  }

  function triggerValidation() {
    var activeIri = getActiveTabIri();
    if (!activeIri) return;

    // First save the current object to trigger validation via the queue
    saveCurrentObject();

    // Open lint section if collapsed, and refresh after delay
    var lintDetails = document.querySelector('#lint-content') && document.querySelector('#lint-content').closest('details.right-section');
    if (lintDetails) lintDetails.open = true;

    setTimeout(function () {
      loadRightPaneSection(activeIri, 'lint');
    }, 1500);
  }

  function addObjectToCommandPalette(objectIri, label) {
    var ninja = document.querySelector('ninja-keys');
    if (!ninja || !ninja.data) return;

    var id = 'open-' + objectIri;
    var exists = ninja.data.find(function (d) { return d.id === id; });
    if (exists) return;

    var newData = ninja.data.slice();
    newData.push({
      id: id,
      title: 'Open: ' + label,
      section: 'Objects',
      handler: function () { openTab(objectIri, label); }
    });
    ninja.data = newData;
  }

  // --- Tree Toggle ---

  function initTreeToggle() {
    document.addEventListener('click', function (e) {
      var node = e.target.closest('.tree-node');
      if (node) {
        node.classList.toggle('expanded');
      }
    });
  }

  // --- Nav Tree Tooltip (phase 19-02) ---
  // Shows a graph-popover-style tooltip (type + label) on hover for nav tree leaf items.
  // Uses event delegation so it works for dynamically loaded tree content (htmx swaps).
  // Data attributes data-tooltip-label and data-tooltip-type are set by tree_children.html.

  function initNavTreeTooltips() {
    var tooltip = document.createElement('div');
    tooltip.className = 'nav-tree-tooltip';
    tooltip.innerHTML = '<div class="tooltip-type"></div><div class="tooltip-label"></div>';
    tooltip.style.display = 'none';
    document.body.appendChild(tooltip);

    document.addEventListener('mouseover', function (e) {
      var leaf = e.target.closest('[data-tooltip-label]');
      if (!leaf) {
        tooltip.style.display = 'none';
        return;
      }
      var typeText = leaf.dataset.tooltipType || '';
      var labelText = leaf.dataset.tooltipLabel || '';
      tooltip.querySelector('.tooltip-type').textContent = typeText;
      tooltip.querySelector('.tooltip-label').textContent = labelText;

      var rect = leaf.getBoundingClientRect();
      tooltip.style.display = 'block';
      tooltip.style.top = rect.top + 'px';
      tooltip.style.left = (rect.right + 8) + 'px';

      // Prevent overflow past right edge of viewport
      var tRect = tooltip.getBoundingClientRect();
      if (tRect.right > window.innerWidth - 8) {
        tooltip.style.left = (rect.left - tRect.width - 8) + 'px';
      }
    });

    document.addEventListener('mouseout', function (e) {
      var leaf = e.target.closest('[data-tooltip-label]');
      if (leaf) tooltip.style.display = 'none';
    });
  }

  // --- Right Pane Tabs (legacy -- sections now always visible) ---
  function initRightPaneTabs() {
    // No-op: Relations and Lint are now separate collapsible sections, both loaded on object open
  }

  // --- Jump to Field (from lint panel click) ---

  function jumpToField(propertyPath) {
    if (!propertyPath) return;

    // Try to find the field by encoded path ID
    var fieldId = 'field-' + encodeURIComponent(propertyPath);
    var element = document.getElementById(fieldId);

    // Also try with the raw path as ID
    if (!element) {
      element = document.getElementById('field-' + propertyPath);
    }

    // Try matching by partial path (last segment after # or /)
    if (!element) {
      var segments = propertyPath.split(/[#\/]/);
      var lastSegment = segments[segments.length - 1];
      if (lastSegment) {
        var allFields = document.querySelectorAll('.form-field');
        allFields.forEach(function (f) {
          if (f.id && f.id.indexOf(lastSegment) !== -1) {
            element = f;
          }
        });
      }
    }

    if (element) {
      // Scroll the field into view
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });

      // Add highlight effect (flash yellow background for 2 seconds)
      element.classList.add('field-highlight');
      setTimeout(function () {
        element.classList.remove('field-highlight');
      }, 2000);

      // Focus the input within the field if possible
      var input = element.querySelector('input, select, textarea');
      if (input) {
        input.focus();
      }

      // Show validation message inline below the field
      var validationDiv = element.querySelector('.field-validation');
      if (validationDiv) {
        validationDiv.classList.add('error');
        if (!validationDiv.textContent.trim()) {
          validationDiv.textContent = 'Constraint violation on this field';
        }
      }
    }
  }

  // --- Client-side Required Field Validation ---

  function initClientSideValidation() {
    // Check required fields on blur for instant feedback
    document.addEventListener('focusout', function (e) {
      var input = e.target;
      if (!input || !input.closest) return;

      var field = input.closest('.form-field');
      if (!field) return;

      // Check if this is a required field
      var requiredMarker = field.querySelector('.required-marker');
      if (!requiredMarker) return;

      var validationDiv = field.querySelector('.field-validation');
      if (!validationDiv) return;

      // Check if the input is empty
      var value = input.value ? input.value.trim() : '';
      if (!value) {
        validationDiv.textContent = 'This field is required';
        validationDiv.className = 'field-validation error';
        input.style.borderColor = '#c62828';
      } else {
        validationDiv.textContent = '';
        validationDiv.className = 'field-validation';
        input.style.borderColor = '';
      }
    });
  }

  // --- Utilities ---

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // -----------------------------------------------------------------------
  // Phase 28: Sidebar Panel Drag-and-Drop (POLSH-02)
  // -----------------------------------------------------------------------

  function initPanelDragDrop() {
    var draggedPanelName = null;

    // dragstart: must originate from a draggable="true" element inside a [data-panel-name] panel
    document.addEventListener('dragstart', function(e) {
      var handle = e.target.closest('[draggable="true"]');
      if (!handle) return;
      var panel = handle.closest('[data-panel-name]');
      if (!panel) return;
      draggedPanelName = panel.dataset.panelName;
      e.dataTransfer.setData('text/panel-name', draggedPanelName);
      e.dataTransfer.effectAllowed = 'move';
      panel.classList.add('panel-dragging');
    });

    document.addEventListener('dragend', function() {
      draggedPanelName = null;
      document.querySelectorAll('.panel-dragging').forEach(function(el) {
        el.classList.remove('panel-dragging');
      });
      clearDropIndicators();
    });

    // document-level dragover: find nearest [data-panel-name] and show insert indicator
    document.addEventListener('dragover', function(e) {
      if (!e.dataTransfer.types || e.dataTransfer.types.indexOf('text/panel-name') === -1) return;
      var target = e.target.closest('[data-panel-name]');
      if (!target) return;
      if (target.dataset.panelName === draggedPanelName) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';

      clearDropIndicators();
      var rect = target.getBoundingClientRect();
      var mid = rect.top + rect.height / 2;
      if (e.clientY < mid) {
        target.classList.add('panel-drop-before');
      } else {
        target.classList.add('panel-drop-after');
      }
    });

    // document-level drop: move panel to insert position
    document.addEventListener('drop', function(e) {
      var panelName = e.dataTransfer.getData('text/panel-name');
      if (!panelName) return;
      var target = e.target.closest('[data-panel-name]');
      if (!target || target.dataset.panelName === panelName) {
        clearDropIndicators();
        return;
      }
      e.preventDefault();
      var insertPos = target.classList.contains('panel-drop-before') ? 'before' : 'after';
      clearDropIndicators();
      movePanel(panelName, target.dataset.panelName, insertPos);
    });
  }

  function clearDropIndicators() {
    document.querySelectorAll('.panel-drop-before, .panel-drop-after').forEach(function(el) {
      el.classList.remove('panel-drop-before', 'panel-drop-after');
    });
  }

  /**
   * Move a panel relative to a target panel (insert-before/after),
   * or force it into a zone by passing forceZone with no targetName.
   *
   * @param {string} draggedName  - data-panel-name of panel to move
   * @param {string|null} targetName  - data-panel-name of reference panel, or null
   * @param {string|null} insertPos   - 'before' | 'after', or null when using forceZone
   * @param {string} [forceZone]  - 'left' | 'right' — zone to append into (used by restore)
   */
  function movePanel(draggedName, targetName, insertPos, forceZone) {
    var panel = document.querySelector('[data-panel-name="' + draggedName + '"]');
    if (!panel) return;

    var rightContent = document.getElementById('right-content');
    var navTree = document.getElementById('nav-tree');
    if (!rightContent || !navTree) return;

    var targetZone, refNode;

    if (targetName) {
      var targetPanel = document.querySelector('[data-panel-name="' + targetName + '"]');
      if (!targetPanel) return;
      targetZone = rightContent.contains(targetPanel) ? 'right' : 'left';
      refNode = insertPos === 'before' ? targetPanel : targetPanel.nextSibling;
    } else {
      // forceZone only — append to end of the container
      targetZone = forceZone || 'right';
      refNode = null;
    }

    var container = targetZone === 'right' ? rightContent : navTree;

    // Update zone indicator classes on the panel element
    panel.classList.remove('panel-in-left', 'panel-in-right');
    panel.classList.add(targetZone === 'left' ? 'panel-in-left' : 'panel-in-right');

    // DOM move
    container.insertBefore(panel, refNode || null);

    // Re-init Lucide icons in the moved panel so SVGs render
    if (typeof lucide !== 'undefined') {
      lucide.createIcons({ attrs: { class: ['lucide'] } });
    }

    savePanelPositions();
  }

  function savePanelPositions() {
    var positions = {};
    ['#right-content', '#nav-tree'].forEach(function(sel) {
      var container = document.querySelector(sel);
      var zone = sel === '#right-content' ? 'right' : 'left';
      if (!container) return;
      container.querySelectorAll(':scope > [data-panel-name]').forEach(function(p, i) {
        positions[p.dataset.panelName] = { zone: zone, order: i };
      });
    });
    try {
      localStorage.setItem(PANEL_POSITIONS_KEY, JSON.stringify(positions));
    } catch (e) {
      // localStorage blocked — continue without persisting
    }
  }

  function restorePanelPositions() {
    var raw = null;
    try {
      raw = localStorage.getItem(PANEL_POSITIONS_KEY);
    } catch (e) {
      return;
    }
    if (!raw) return;
    try {
      var saved = JSON.parse(raw);

      // Migrate old string format: { relations: 'right', lint: 'left' }
      var values = Object.keys(saved).map(function(k) { return saved[k]; });
      var needsMigration = values.some(function(v) { return typeof v === 'string'; });
      if (needsMigration) {
        var migrated = {};
        var leftOrder = 0, rightOrder = 0;
        Object.keys(saved).forEach(function(name) {
          var zone = saved[name];
          migrated[name] = { zone: zone, order: zone === 'left' ? leftOrder++ : rightOrder++ };
        });
        saved = migrated;
      }

      // Sort panels by saved order within each zone, then append in order
      var leftPanels = [], rightPanels = [];
      Object.keys(saved).forEach(function(name) {
        var entry = saved[name];
        if (entry.zone === 'left') {
          leftPanels.push({ name: name, order: entry.order });
        } else {
          rightPanels.push({ name: name, order: entry.order });
        }
      });
      leftPanels.sort(function(a, b) { return a.order - b.order; });
      rightPanels.sort(function(a, b) { return a.order - b.order; });

      var rightContent = document.getElementById('right-content');
      var navTree = document.getElementById('nav-tree');
      if (!rightContent || !navTree) return;

      rightPanels.forEach(function(entry) {
        var p = document.querySelector('[data-panel-name="' + entry.name + '"]');
        if (!p) return;
        p.classList.remove('panel-in-left', 'panel-in-right');
        p.classList.add('panel-in-right');
        rightContent.appendChild(p);
      });
      leftPanels.forEach(function(entry) {
        var p = document.querySelector('[data-panel-name="' + entry.name + '"]');
        if (!p) return;
        p.classList.remove('panel-in-left', 'panel-in-right');
        p.classList.add('panel-in-left');
        navTree.appendChild(p);
      });

      if (typeof lucide !== 'undefined') {
        lucide.createIcons({ attrs: { class: ['lucide'] } });
      }
    } catch (e) {
      // Ignore parse errors — positions revert to default
    }
  }

  // --- Initialization ---

  function init() {
    initSplit();
    initKeyboardShortcuts();
    initTreeToggle();
    initNavTreeTooltips();
    initRightPaneTabs();
    initClientSideValidation();
    initBottomPanel();
    initPanelDragDrop();
    restorePanelPositions();

    // Initialize workspace layout (dockview)
    if (typeof window.initWorkspaceLayout === 'function') {
      window.initWorkspaceLayout();
      // Restore accent bar based on the currently active dockview panel.
      // Accent = focused tab is an object tab; settings/views = off.
      // Must run immediately after initWorkspaceLayout so _dockview is set.
      (function restoreAccentBar() {
        var dv = window._dockview;
        if (!dv || !dv.activePanel) return;
        var panelId = dv.activePanel.id;
        var isObjectTab = panelId && !panelId.startsWith('view:') && !panelId.startsWith('special:');
        setContextualPanelActive(isObjectTab);
      }());
    }

    // Initialize command palette after workspace layout is ready
    initCommandPalette();

    // Fetch and cache icon map for client-side use (graph shapes, tab icons)
    fetch('/browser/icons', { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        window._sempkmIcons = data;  // { tree: {...}, tab: {...}, graph: {...} }
      })
      .catch(function () {
        window._sempkmIcons = { tree: {}, tab: {}, graph: {} };
      });
  }

  // Auto-start tour from ?tour= query param (e.g. linked from /guide page)
  function maybeStartTour() {
    var tour = new URLSearchParams(window.location.search).get('tour');
    if (!tour) return;
    // Remove the param from the URL without reloading
    var url = new URL(window.location.href);
    url.searchParams.delete('tour');
    history.replaceState(null, '', url.pathname + (url.search || ''));
    // Brief delay to let the workspace fully render before the tour overlay
    setTimeout(function () {
      if (tour === 'welcome' && typeof window.startWelcomeTour === 'function') {
        window.startWelcomeTour();
      } else if (tour === 'create-object' && typeof window.startCreateObjectTour === 'function') {
        window.startCreateObjectTour();
      }
    }, 600);
  }

  // Wait for DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(); maybeStartTour(); });
  } else {
    init();
    maybeStartTour();
  }

  // Also reinitialize after htmx swaps (e.g., navigating back to /browser/)
  document.addEventListener('htmx:afterSwap', function (e) {
    if (e.detail.target && e.detail.target.id === 'app-content') {
      var ws = document.getElementById('workspace');
      if (ws) {
        init();
      }
    }

    // Reinitialize Lucide icons in the swapped target (tree children, etc.)
    var target = e.detail.target;
    if (target && typeof lucide !== 'undefined') {
      lucide.createIcons({ root: target });
    }

    // When tree children are loaded, add objects to command palette
    if (target && target.classList && target.classList.contains('tree-children')) {
      var leaves = target.querySelectorAll('.tree-leaf');
      leaves.forEach(function (leaf) {
        var onclick = leaf.getAttribute('onclick');
        if (onclick) {
          // Extract IRI and label from onclick="openTab('iri', 'label')"
          var match = onclick.match(/openTab\('([^']*)',\s*'([^']*)'\)/);
          if (match) {
            addObjectToCommandPalette(match[1], match[2]);
          }
        }
      });
    }
  });

  // --- HX-Trigger event listeners for create/edit flows ---

  // When an object is created via the create form, open it in a tab.
  // Brief delay so the success message is visible before the tab loads.
  document.addEventListener('objectCreated', function (e) {
    var detail = e.detail;
    if (detail && detail.iri) {
      var label = detail.label || detail.iri;
      setTimeout(function () {
        openTab(detail.iri, label, 'edit');
      }, 1500);
    }
  });

  // When an object is saved via the edit form, mark the tab clean and update labels
  document.addEventListener('objectSaved', function (e) {
    var detail = e.detail;
    if (!detail || !detail.iri) return;
    markClean(detail.iri);

    if (!detail.label) return;
    var newLabel = detail.label;
    var iri = detail.iri;

    // Update toolbar title in the object tab
    var tabEl = document.querySelector('.object-tab[data-object-iri="' + iri + '"]');
    if (tabEl) {
      var titleEl = tabEl.querySelector('.object-toolbar-title');
      if (titleEl) titleEl.textContent = newLabel;
    }

    // Update tab label in the _tabMeta sidecar and dockview panel title
    if (window._tabMeta && window._tabMeta[iri]) {
      window._tabMeta[iri].label = newLabel;
    }
    var dv = window._dockview;
    if (dv) {
      var panel = dv.panels.find(function(p) { return p.id === iri; });
      if (panel) {
        panel.api.setTitle(newLabel);
      }
    }
  });

  // --- Event Log: Undo ---

  /**
   * Confirm and submit an undo request for a reversible event.
   * Creates a new compensating event via POST /browser/events/{iri}/undo,
   * then reloads the event log panel to show the new compensating event.
   *
   * @param {string} eventIri - The IRI of the event to undo.
   * @param {HTMLElement} btn - The Undo button element (disabled during request).
   */
  window.sempkmUndoEvent = function(eventIri, btn) {
    if (!window.confirm('Undo this event? This will create a new compensating event.\n\nNote: Any changes made to the same fields after this event will also be reverted.')) {
      return;
    }
    btn.disabled = true;
    btn.textContent = 'Undoing\u2026';
    fetch('/browser/events/' + encodeURIComponent(eventIri) + '/undo', {
      method: 'POST'
    }).then(function(res) {
      if (res.ok) {
        htmx.ajax('GET', '/browser/events', {
          target: '#panel-event-log',
          swap: 'innerHTML'
        });
      } else {
        res.json().then(function(d) {
          alert('Undo failed: ' + (d.error || 'Unknown error'));
          btn.disabled = false;
          btn.textContent = 'Undo';
        });
      }
    }).catch(function() {
      alert('Undo failed: network error');
      btn.disabled = false;
      btn.textContent = 'Undo';
    });
  };

  // --- Carousel View Switching ---

  function switchCarouselView(tabEl, specIri, rendererType, typeIri) {
    // Update active tab styling
    var bar = tabEl.closest('.carousel-tab-bar');
    bar.querySelectorAll('.carousel-tab').forEach(function(t) {
      t.classList.remove('active');
    });
    tabEl.classList.add('active');

    // Persist selection per type IRI
    try {
      var data = JSON.parse(localStorage.getItem('sempkm_carousel_view') || '{}');
      data[typeIri] = specIri;
      localStorage.setItem('sempkm_carousel_view', JSON.stringify(data));
    } catch (e) { /* localStorage unavailable */ }

    // Preserve current filter if present (use class selector, not ID, to avoid duplicate ID issues)
    var panel = bar.closest('.group-editor-area');
    var filterInput = panel ? panel.querySelector('.view-filter-input') : null;
    var filter = filterInput ? filterInput.value : '';

    // Build URL
    var url = '/browser/views/' + rendererType + '/' + encodeURIComponent(specIri);
    if (filter) {
      url += '?filter=' + encodeURIComponent(filter);
    }

    // Find the view body container (two-container pattern: bar stays, body swaps)
    var viewBody = bar.parentElement.querySelector('.carousel-view-body');
    if (!viewBody) {
      // Fallback: if no .carousel-view-body found, target the panel container
      viewBody = panel;
    }

    if (viewBody && typeof htmx !== 'undefined') {
      // Show loading indicator
      var indicator = document.createElement('div');
      indicator.className = 'view-loading-indicator';
      indicator.innerHTML = '<div class="view-loading-spinner"></div>';
      viewBody.style.position = 'relative';
      viewBody.appendChild(indicator);

      // Load view content -- outerHTML swap with select extracts only .carousel-view-body
      // from the response, discarding the response's carousel bar
      htmx.ajax('GET', url, { target: viewBody, swap: 'outerHTML', select: '.carousel-view-body' });
    }
  }

  function restoreCarouselView(currentSpecIri, typeIri) {
    try {
      var data = JSON.parse(localStorage.getItem('sempkm_carousel_view') || '{}');
      var savedSpecIri = data[typeIri];
      if (!savedSpecIri || savedSpecIri === currentSpecIri) return;

      // Check if the saved spec exists in the current carousel bar
      var bar = document.querySelector('.carousel-tab-bar[data-type-iri="' + typeIri + '"]');
      if (!bar) return;
      var savedTab = bar.querySelector('[data-spec-iri="' + savedSpecIri + '"]');
      if (!savedTab) {
        // Saved view no longer exists in manifest -- clear and use current (first) silently
        delete data[typeIri];
        localStorage.setItem('sempkm_carousel_view', JSON.stringify(data));
        return;
      }

      // Switch to the saved view
      var rendererType = savedTab.getAttribute('data-renderer-type');
      switchCarouselView(savedTab, savedSpecIri, rendererType, typeIri);
    } catch (e) { /* localStorage unavailable */ }
  }

  // --- Export functions globally for htmx onclick handlers ---
  window.openTab = openTab;
  window.closeTab = closeTab;
  window.switchTab = switchTab;
  window.markDirty = markDirty;
  window.markClean = markClean;
  window.togglePane = togglePane;
  window.showTypePicker = showTypePicker;
  window.jumpToField = jumpToField;
  window.triggerValidation = triggerValidation;
  window.loadRightPaneSection = loadRightPaneSection;
  window.openViewTab = openViewTab;
  window.openViewMenu = openViewMenu;
  window.switchCarouselView = switchCarouselView;
  window.restoreCarouselView = restoreCarouselView;
  window.toggleObjectMode = toggleObjectMode;
  window.saveCurrentObject = saveCurrentObject;
  window.toggleBottomPanel = toggleBottomPanel;
  window.maximizeBottomPanel = maximizeBottomPanel;
  window.movePanel = movePanel;
  window.showToast = showToast;
  // Backward-compat shim — callers can still pass (name, 'left'/'right')
  window.swapPanel = function(panelName, zone) { movePanel(panelName, null, null, zone); };

  // -----------------------------------------------------------------------
  // Phase 28: Object-contextual panel indicator (POLSH-03)
  // -----------------------------------------------------------------------

  /**
   * Toggle the contextual-panel-active class on all [data-panel-name] panels.
   * Called when an object tab is activated (isActive=true) or when all tabs
   * are closed (isActive=false).
   */
  function setContextualPanelActive(isActive) {
    document.querySelectorAll('[data-panel-name]').forEach(function(panel) {
      if (isActive) {
        panel.classList.add('contextual-panel-active');
      } else {
        panel.classList.remove('contextual-panel-active');
      }
    });
    // Phase 28 gap-closure: clear panel content when no object is active
    // so stale data from a previously open object does not persist
    if (!isActive) {
      var relEl = document.getElementById('relations-content');
      var lintEl = document.getElementById('lint-content');
      if (relEl) relEl.innerHTML = '<div class="right-empty">No object selected</div>';
      if (lintEl) lintEl.innerHTML = '<div class="right-empty">No object selected</div>';
    }
  }

  // Listen for tab lifecycle events dispatched by workspace-layout.js
  document.addEventListener('sempkm:tab-activated', function(e) {
    // Accent bar tracks the FOCUSED tab: on for object tabs, off for settings/views.
    // Panels are contextual — they only make sense when an object is focused.
    setContextualPanelActive(!!(e.detail && e.detail.isObjectTab));
  });

  document.addEventListener('sempkm:tabs-empty', function() {
    setContextualPanelActive(false);
  });

  window.setContextualPanelActive = setContextualPanelActive;

})();

