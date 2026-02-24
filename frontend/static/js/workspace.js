/**
 * SemPKM IDE Workspace
 *
 * Manages the three-column resizable layout (Split.js), tab state
 * (sessionStorage), keyboard shortcuts, and command palette (ninja-keys).
 */

(function () {
  'use strict';

  // --- Constants ---
  var TAB_KEY = 'sempkm_open_tabs';
  var PANE_KEY = 'sempkm_pane_sizes';
  var ACTIVE_TAB_KEY = 'sempkm_active_tab';

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

  // --- Tab Management ---

  function getTabs() {
    try {
      return JSON.parse(sessionStorage.getItem(TAB_KEY) || '[]');
    } catch (e) {
      return [];
    }
  }

  function saveTabs(tabs) {
    try {
      sessionStorage.setItem(TAB_KEY, JSON.stringify(tabs));
    } catch (e) {
      // sessionStorage might be blocked
    }
  }

  function getActiveTabIri() {
    return sessionStorage.getItem(ACTIVE_TAB_KEY) || null;
  }

  function setActiveTabIri(iri) {
    if (iri) {
      sessionStorage.setItem(ACTIVE_TAB_KEY, iri);
    } else {
      sessionStorage.removeItem(ACTIVE_TAB_KEY);
    }
  }

  function openTab(objectIri, label, mode) {
    var tabs = getTabs();
    var existing = tabs.find(function (t) { return t.iri === objectIri; });

    if (!existing) {
      tabs.push({ iri: objectIri, label: label, dirty: false });
      saveTabs(tabs);
    }

    setActiveTabIri(objectIri);
    renderTabBar();
    loadObjectContent(objectIri, mode);

    // Add to command palette dynamically
    addObjectToCommandPalette(objectIri, label);
  }

  // --- View Tab Support ---

  function openViewTab(viewId, viewLabel, viewType) {
    var tabKey = 'view:' + viewId;
    var tabs = getTabs();
    var existing = tabs.find(function (t) { return t.iri === tabKey; });

    if (existing) {
      // Tab already open -- switch to it
      setActiveTabIri(tabKey);
      renderTabBar();
      loadViewContent(viewId, viewType);
      return;
    }

    tabs.push({ iri: tabKey, label: viewLabel, dirty: false, isView: true, viewType: viewType, viewId: viewId });
    saveTabs(tabs);

    setActiveTabIri(tabKey);
    renderTabBar();
    loadViewContent(viewId, viewType);
  }

  function loadViewContent(viewId, viewType) {
    var editorArea = document.getElementById('editor-area');
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
        target: '#editor-area',
        swap: 'innerHTML'
      }).catch(function () {
        editorArea.innerHTML = '<div class="editor-empty"><p>Failed to load view.</p></div>';
      });
    }
  }

  function closeTab(objectIri) {
    var tabs = getTabs();
    var index = tabs.findIndex(function (t) { return t.iri === objectIri; });

    if (index === -1) return;

    tabs.splice(index, 1);
    saveTabs(tabs);

    var activeIri = getActiveTabIri();
    if (activeIri === objectIri) {
      // Switch to the nearest remaining tab or show empty state
      if (tabs.length > 0) {
        var nextIndex = Math.min(index, tabs.length - 1);
        var nextTab = tabs[nextIndex];
        setActiveTabIri(nextTab.iri);
        _loadTabContent(nextTab);
      } else {
        setActiveTabIri(null);
        showEditorEmpty();
      }
    }

    renderTabBar();
  }

  function switchTab(objectIri) {
    setActiveTabIri(objectIri);
    renderTabBar();
    var tabs = getTabs();
    var tab = tabs.find(function (t) { return t.iri === objectIri; });
    if (tab) {
      _loadTabContent(tab);
    } else {
      loadObjectContent(objectIri);
    }
  }

  function _loadTabContent(tab) {
    if (tab.isView && tab.viewId && tab.viewType) {
      loadViewContent(tab.viewId, tab.viewType);
    } else if (tab.iri && tab.iri.indexOf('view:') === 0) {
      // Fallback for view tabs without viewId/viewType (e.g., restored from session)
      var viewId = tab.iri.substring(5);
      var viewType = tab.viewType || 'table';
      loadViewContent(viewId, viewType);
    } else {
      // Normal tab switch: no mode parameter (opens in read mode by default)
      loadObjectContent(tab.iri);
    }
  }

  function markDirty(objectIri) {
    var tabs = getTabs();
    var tab = tabs.find(function (t) { return t.iri === objectIri; });
    if (tab) {
      tab.dirty = true;
      saveTabs(tabs);
      renderTabBar();
    }
  }

  function markClean(objectIri) {
    var tabs = getTabs();
    var tab = tabs.find(function (t) { return t.iri === objectIri; });
    if (tab) {
      tab.dirty = false;
      saveTabs(tabs);
      renderTabBar();
    }
  }

  function renderTabBar() {
    var tabBar = document.getElementById('tab-bar');
    if (!tabBar) return;

    var tabs = getTabs();
    var activeIri = getActiveTabIri();

    if (tabs.length === 0) {
      tabBar.innerHTML = '<div class="tab-empty-state">No objects open</div>';
      return;
    }

    var html = '';
    tabs.forEach(function (tab) {
      var isActive = tab.iri === activeIri;
      var isView = tab.isView || (tab.iri && tab.iri.indexOf('view:') === 0);
      html += '<div class="workspace-tab' + (isActive ? ' active' : '') + (isView ? ' view-tab' : '') + '"' +
        ' data-iri="' + escapeHtml(tab.iri) + '"' +
        ' onclick="switchTab(\'' + escapeJs(tab.iri) + '\')">';
      if (isView) {
        var vt = tab.viewType || '';
        var icon = '&#9654;';
        if (vt === 'table') icon = '&#9638;';
        else if (vt === 'card') icon = '&#9641;';
        else if (vt === 'graph') icon = '&#9672;';
        html += '<span class="tab-view-icon" title="View: ' + escapeHtml(vt) + '">' + icon + '</span>';
      }
      html += '<span class="tab-label">' + escapeHtml(tab.label) + '</span>';
      if (tab.dirty) {
        html += '<span class="tab-dirty" title="Unsaved changes"></span>';
      }
      html += '<button class="tab-close" onclick="event.stopPropagation(); closeTab(\'' +
        escapeJs(tab.iri) + '\')" title="Close tab">&times;</button>';
      html += '</div>';
    });

    tabBar.innerHTML = html;
  }

  function loadObjectContent(objectIri, mode) {
    var editorArea = document.getElementById('editor-area');
    if (!editorArea) return;

    // If IRI starts with 'view:', load as view tab
    if (objectIri && objectIri.indexOf('view:') === 0) {
      var tabs = getTabs();
      var tab = tabs.find(function (t) { return t.iri === objectIri; });
      if (tab && tab.viewId && tab.viewType) {
        loadViewContent(tab.viewId, tab.viewType);
        return;
      }
      // Fallback: try to parse view type from stored data
      var viewId = objectIri.substring(5);
      loadViewContent(viewId, (tab && tab.viewType) || 'table');
      return;
    }

    // Build URL with optional mode parameter
    var url = '/browser/object/' + encodeURIComponent(objectIri);
    if (mode === 'edit') {
      url += '?mode=edit';
    }

    // Use htmx to load object content into center pane
    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', url, {
        target: '#editor-area',
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
    var editorArea = document.getElementById('editor-area');
    if (editorArea) {
      editorArea.innerHTML = '<div class="editor-empty">' +
        '<p>Select an object from the Explorer to open it here.</p>' +
        '<p class="hint">Or press <kbd>Ctrl</kbd>+<kbd>K</kbd> to open the command palette.</p>' +
        '</div>';
    }
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
      var gutter = pane.previousElementSibling;
      if (gutter && gutter.classList.contains('gutter')) gutter.style.display = '';
      _rebuildSplit(paneStates[paneId]);
      delete paneStates[paneId];
    } else {
      // Collapse the pane: save sizes, hide it and its gutter, rebuild Split.js
      paneStates[paneId] = splitInstance.getSizes().slice();
      pane.style.display = 'none';
      var gutter = pane.previousElementSibling;
      if (gutter && gutter.classList.contains('gutter')) gutter.style.display = 'none';
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
      var tabs = getTabs();
      var tab = tabs.find(function (t) { return t.iri === objectIri; });
      if (tab && tab.dirty) {
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
            mdSources.forEach(function(src) {
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

      // Ctrl+\ / Cmd+\: Toggle sidebar
      if (mod && e.key === '\\') {
        e.preventDefault();
        toggleSidebar();
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
        var objectTab = document.querySelector('.object-tab');
        if (objectTab) {
          var iri = objectTab.dataset.objectIri;
          var safeId = encodeURIComponent(iri).replace(/%/g, '_');
          toggleObjectMode(safeId, iri);
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
    });
  }

  function saveCurrentObject() {
    var activeIri = getActiveTabIri();
    if (!activeIri) return;

    // Save form properties via htmx form submission
    var activeTab = document.querySelector('.object-tab');
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
        var content = fallback.value || '';
        var fbPredicate = fallback.dataset.bodyPredicate || '';
        var fbUrl = '/browser/objects/' + encodeURIComponent(fallback.dataset.objectIri) + '/body';
        if (fbPredicate) fbUrl += '?predicate=' + encodeURIComponent(fbPredicate);
        fetch(fbUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'text/plain' },
          body: content
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
          id: 'toggle-sidebar',
          title: 'Toggle Sidebar',
          section: 'View',
          hotkey: 'ctrl+\\',
          handler: function () { toggleSidebar(); }
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
            var activeTab = document.querySelector('.object-tab');
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
      ];

      // Dynamically load available views into command palette
      _loadViewCommandPaletteEntries(ninja);
    }).catch(function () {
      console.warn('ninja-keys custom element not available');
    });
  }

  function openViewMenu() {
    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', '/browser/views/menu', {
        target: '#editor-area',
        swap: 'innerHTML'
      }).catch(function () {
        var editorArea = document.getElementById('editor-area');
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
    // Load the type picker dialog into the editor area via htmx
    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', '/browser/types', {
        target: '#editor-area',
        swap: 'innerHTML'
      }).catch(function () {
        var editorArea = document.getElementById('editor-area');
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
    var lintDetails = document.querySelector('#lint-content')?.closest('details.right-section');
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

  // --- Right Pane Tabs (legacy — sections now always visible) ---
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

  function escapeJs(str) {
    return str.replace(/'/g, "\\'").replace(/\\/g, '\\\\');
  }

  // --- Restore tab state on page load ---

  function restoreTabState() {
    var tabs = getTabs();
    if (tabs.length > 0) {
      renderTabBar();
      var activeIri = getActiveTabIri();
      if (activeIri) {
        var activeTab = tabs.find(function (t) { return t.iri === activeIri; });
        if (activeTab) {
          _loadTabContent(activeTab);
        } else {
          loadObjectContent(activeIri);
        }
      }
    }
  }

  // --- Initialization ---

  function init() {
    initSplit();
    initKeyboardShortcuts();
    initCommandPalette();
    initTreeToggle();
    initRightPaneTabs();
    initClientSideValidation();
    restoreTabState();
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
      // Open a tab for the newly created object
      var tabs = getTabs();
      // Remove any "New Object" placeholder tab
      tabs = tabs.filter(function (t) { return t.iri !== '__new__'; });
      saveTabs(tabs);
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

})();
