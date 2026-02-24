/**
 * SemPKM IDE Workspace
 *
 * Manages the three-column resizable layout (Split.js), keyboard shortcuts,
 * and command palette (ninja-keys).
 *
 * Tab state is now delegated to WorkspaceLayout (workspace-layout.js).
 * All openTab/closeTab/switchTab functions delegate to window._workspaceLayout.
 */

(function () {
  'use strict';

  // --- Constants ---
  var PANE_KEY = 'sempkm_pane_sizes';
  var PANEL_KEY = 'sempkm_bottom_panel';

  // --- Bottom Panel State ---
  var panelState = { open: false, height: 30, activeTab: 'sparql', maximized: false };

  // --- Split.js Initialization ---
  var splitInstance = null;
  var savedPaneSizes = null;
  var defaultSizes = [20, 50, 30];

  function initSplit() {
    if (typeof Split === 'undefined') {
      console.warn('Split.js not loaded yet, retrying...');
      setTimeout(initSplit, 100);
      return;
    }

    // Restore saved pane sizes
    try {
      var saved = localStorage.getItem(PANE_KEY);
      if (saved) {
        savedPaneSizes = JSON.parse(saved);
      }
    } catch (e) {
      savedPaneSizes = null;
    }

    splitInstance = Split(['#nav-pane', '#editor-pane', '#right-pane'], {
      sizes: savedPaneSizes || defaultSizes,
      minSize: [180, 300, 200],
      gutterSize: 5,
      cursor: 'col-resize',
      onDragEnd: function (sizes) {
        try {
          localStorage.setItem(PANE_KEY, JSON.stringify(sizes));
        } catch (e) {
          // localStorage might be full or blocked
        }
      }
    });
  }

  // --- Tab Management (delegates to WorkspaceLayout) ---

  function openTab(objectIri, label, mode) {
    var layout = window._workspaceLayout;
    if (layout) {
      // Check if already open in active group
      var activeGroup = layout.getGroup(layout.activeGroupId);
      if (activeGroup) {
        var existing = activeGroup.tabs.find(function (t) { return (t.id || t.iri) === objectIri; });
        if (existing) {
          // Switch to it
          switchTabInGroup(objectIri, layout.activeGroupId);
          return;
        }
      }

      layout.addTabToGroup(
        { id: objectIri, iri: objectIri, label: label || objectIri, dirty: false, isView: false },
        layout.activeGroupId
      );
      // Load the content
      if (mode === 'edit') {
        var editorArea = window.getActiveEditorArea();
        if (editorArea && typeof htmx !== 'undefined') {
          htmx.ajax('GET', '/browser/object/' + encodeURIComponent(objectIri) + '?mode=edit', {
            target: editorArea,
            swap: 'innerHTML'
          });
        }
      } else {
        window.loadTabInGroup(layout.activeGroupId, objectIri);
      }
    } else {
      // Fallback: direct load without tab management (layout not initialized)
      loadObjectContent(objectIri, mode);
    }

    // Add to command palette dynamically
    addObjectToCommandPalette(objectIri, label);
  }

  // --- View Tab Support ---

  function openViewTab(viewId, viewLabel, viewType) {
    var tabKey = 'view:' + viewId;
    var layout = window._workspaceLayout;

    if (layout) {
      var activeGroup = layout.getGroup(layout.activeGroupId);
      if (activeGroup) {
        var existing = activeGroup.tabs.find(function (t) { return (t.id || t.iri) === tabKey; });
        if (existing) {
          switchTabInGroup(tabKey, layout.activeGroupId);
          return;
        }
      }

      layout.addTabToGroup(
        { id: tabKey, iri: tabKey, label: viewLabel, dirty: false, isView: true, viewType: viewType, viewId: viewId },
        layout.activeGroupId
      );
      window.loadTabInGroup(layout.activeGroupId, tabKey);
    } else {
      // Fallback
      loadViewContent(viewId, viewType);
    }
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
    var layout = window._workspaceLayout;
    if (layout) {
      layout.removeTabFromGroup(objectIri, layout.activeGroupId);
    }
  }

  function switchTab(objectIri) {
    var layout = window._workspaceLayout;
    if (layout) {
      switchTabInGroup(objectIri, layout.activeGroupId);
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
    var layout = window._workspaceLayout;
    if (!layout) return;

    // Mark dirty across all groups
    var found = false;
    layout.groups.forEach(function (group) {
      var tab = group.tabs.find(function (t) { return (t.id || t.iri) === objectIri; });
      if (tab) {
        tab.dirty = true;
        found = true;
        window.renderGroupTabBar(group);
      }
    });
    if (found) layout.save();
  }

  function markClean(objectIri) {
    var layout = window._workspaceLayout;
    if (!layout) return;

    var found = false;
    layout.groups.forEach(function (group) {
      var tab = group.tabs.find(function (t) { return (t.id || t.iri) === objectIri; });
      if (tab) {
        tab.dirty = false;
        found = true;
        window.renderGroupTabBar(group);
      }
    });
    if (found) layout.save();
  }

  function getActiveTabIri() {
    var layout = window._workspaceLayout;
    if (!layout) return null;
    var group = layout.getGroup(layout.activeGroupId);
    return group ? group.activeTabId : null;
  }

  function loadObjectContent(objectIri, mode) {
    var editorArea = window.getActiveEditorArea ? window.getActiveEditorArea() : document.getElementById('editor-area-group-1');
    if (!editorArea) return;

    // If IRI starts with 'view:', load as view tab
    if (objectIri && objectIri.indexOf('view:') === 0) {
      var layout = window._workspaceLayout;
      var tab = null;
      if (layout) {
        layout.groups.forEach(function (g) {
          var found = g.tabs.find(function (t) { return (t.id || t.iri) === objectIri; });
          if (found) tab = found;
        });
      }
      var viewId = objectIri.substring(5);
      loadViewContent(viewId, (tab && tab.viewType) || 'table');
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
      panel.style.display = 'none';
      if (handle) handle.classList.remove('panel-open');
      editorCol.classList.remove('panel-maximized');
    } else if (panelState.maximized) {
      panel.style.display = '';
      panel.style.height = '';
      if (handle) handle.classList.add('panel-open');
      editorCol.classList.add('panel-maximized');
    } else {
      panel.style.display = '';
      if (handle) handle.classList.add('panel-open');
      editorCol.classList.remove('panel-maximized');
      // Set height in pixels (not %) to avoid pitfall with flex layout
      var parentH = panel.parentElement ? panel.parentElement.getBoundingClientRect().height : 0;
      if (parentH > 0) {
        panel.style.height = (parentH * panelState.height / 100) + 'px';
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

  var paneStates = {};

  function togglePane(paneId) {
    if (!splitInstance) return;

    var pane = document.getElementById(paneId);
    if (!pane) return;

    var panes = ['nav-pane', 'editor-pane', 'right-pane'];
    var paneIndex = panes.indexOf(paneId);
    if (paneIndex === -1) return;

    if (paneStates[paneId]) {
      // Restore the pane: show it and its gutter, rebuild Split.js
      pane.style.display = '';
      var gutterPrev = pane.previousElementSibling;
      if (gutterPrev && gutterPrev.classList.contains('gutter')) gutterPrev.style.display = '';
      _rebuildSplit(paneStates[paneId]);
      delete paneStates[paneId];
    } else {
      // Collapse the pane: save sizes, hide it and its gutter, rebuild Split.js
      paneStates[paneId] = splitInstance.getSizes().slice();
      pane.style.display = 'none';
      var gutterPrev2 = pane.previousElementSibling;
      if (gutterPrev2 && gutterPrev2.classList.contains('gutter')) gutterPrev2.style.display = 'none';
      // Rebuild with only visible panes
      var visibleIds = [];
      var visibleSizes = [];
      panes.forEach(function (id) {
        var el = document.getElementById(id);
        if (el && el.style.display !== 'none') {
          visibleIds.push('#' + id);
          visibleSizes.push(id === 'editor-pane' ? 80 : 20);
        }
      });
      _rebuildSplit(null, visibleIds, visibleSizes);
    }
  }

  function _rebuildSplit(restoreSizes, visibleIds, visibleSizes) {
    if (splitInstance) {
      splitInstance.destroy();
    }
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

    var sizes = restoreSizes || visibleSizes || null;
    // If restoring, filter to only visible panes
    if (restoreSizes) {
      sizes = [];
      panes.forEach(function (id, i) {
        var el = document.getElementById(id);
        if (el && el.style.display !== 'none') {
          sizes.push(restoreSizes[i]);
        }
      });
    }

    splitInstance = Split(ids, {
      sizes: sizes || ids.map(function () { return 100 / ids.length; }),
      minSize: minSizes,
      gutterSize: 5,
      cursor: 'col-resize',
      onDragEnd: function (s) {
        try { localStorage.setItem(PANE_KEY, JSON.stringify(s)); } catch (e) {}
      }
    });
  }

  // --- Object Mode Toggle (Read/Edit) ---

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
      var layout = window._workspaceLayout;
      var isDirty = false;
      if (layout) {
        layout.groups.forEach(function (g) {
          var tab = g.tabs.find(function (t) { return (t.id || t.iri) === objectIri; });
          if (tab && tab.dirty) isDirty = true;
        });
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
      if (toggleBtn) toggleBtn.textContent = 'Done';
      if (saveBtn) saveBtn.style.display = '';
      // Swap faces at midpoint (300ms into 600ms animation)
      setTimeout(function () {
        if (readFace) readFace.classList.add('face-hidden');
        if (editFace) editFace.classList.add('face-visible');
      }, 300);
    }
  }

  // --- Keyboard Shortcuts ---

  function initKeyboardShortcuts() {
    document.addEventListener('keydown', function (e) {
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
        var layout = window._workspaceLayout;
        if (layout) {
          window.splitRight(layout.activeGroupId);
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

      // Ctrl+1/2/3/4: Focus editor group by index
      if (mod && ['1', '2', '3', '4'].indexOf(e.key) !== -1) {
        e.preventDefault();
        var idx = parseInt(e.key) - 1;
        var layout2 = window._workspaceLayout;
        if (layout2 && layout2.groups[idx]) {
          window.setActiveGroup(layout2.groups[idx].id);
        }
      }
    });
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
            var layout = window._workspaceLayout;
            if (layout) window.splitRight(layout.activeGroupId);
          }
        },
        {
          id: 'close-group',
          title: 'Close Group',
          section: 'View',
          handler: function () {
            var layout = window._workspaceLayout;
            if (layout && layout.groups.length > 1) {
              layout.removeGroup(layout.activeGroupId);
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
        }
      ];

      // Dynamically load available views into command palette
      _loadViewCommandPaletteEntries(ninja);
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

  function showTypePicker() {
    var editorArea = window.getActiveEditorArea ? window.getActiveEditorArea() : document.getElementById('editor-area-group-1');
    if (typeof htmx !== 'undefined') {
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

  // --- Initialization ---

  function init() {
    initSplit();
    initKeyboardShortcuts();
    initTreeToggle();
    initRightPaneTabs();
    initClientSideValidation();
    initBottomPanel();

    // Initialize workspace layout (migrates old tab state, builds multi-group DOM)
    if (typeof window.initWorkspaceLayout === 'function') {
      window.initWorkspaceLayout();
    }

    // Initialize command palette after workspace layout is ready
    initCommandPalette();
  }

  // Wait for DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Also reinitialize after htmx swaps (e.g., navigating back to /browser/)
  document.addEventListener('htmx:afterSwap', function (e) {
    if (e.detail.target && e.detail.target.id === 'app-content') {
      var ws = document.getElementById('workspace');
      if (ws) {
        init();
      }
    }

    // When tree children are loaded, add objects to command palette
    var target = e.detail.target;
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

  // When an object is created via the create form, open it in a tab
  document.addEventListener('objectCreated', function (e) {
    var detail = e.detail;
    if (detail && detail.iri) {
      var label = detail.label || detail.iri;
      // Newly created objects open directly in edit mode
      openTab(detail.iri, label, 'edit');
    }
  });

  // When an object is saved via the edit form, mark the tab clean
  document.addEventListener('objectSaved', function (e) {
    var detail = e.detail;
    if (detail && detail.iri) {
      markClean(detail.iri);
    }
  });

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
  window.toggleObjectMode = toggleObjectMode;
  window.saveCurrentObject = saveCurrentObject;
  window.toggleBottomPanel = toggleBottomPanel;
  window.maximizeBottomPanel = maximizeBottomPanel;

})();
