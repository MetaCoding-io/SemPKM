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

  function openTab(objectIri, label) {
    var tabs = getTabs();
    var existing = tabs.find(function (t) { return t.iri === objectIri; });

    if (!existing) {
      tabs.push({ iri: objectIri, label: label, dirty: false });
      saveTabs(tabs);
    }

    setActiveTabIri(objectIri);
    renderTabBar();
    loadObjectContent(objectIri);

    // Add to command palette dynamically
    addObjectToCommandPalette(objectIri, label);
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
        setActiveTabIri(tabs[nextIndex].iri);
        loadObjectContent(tabs[nextIndex].iri);
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
    loadObjectContent(objectIri);
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
      html += '<div class="workspace-tab' + (isActive ? ' active' : '') + '"' +
        ' data-iri="' + escapeHtml(tab.iri) + '"' +
        ' onclick="switchTab(\'' + escapeJs(tab.iri) + '\')">';
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

  function loadObjectContent(objectIri) {
    var editorArea = document.getElementById('editor-area');
    if (!editorArea) return;

    // Use htmx to load object content
    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', '/browser/object/' + encodeURIComponent(objectIri), {
        target: '#editor-area',
        swap: 'innerHTML'
      }).catch(function () {
        editorArea.innerHTML = '<div class="editor-empty"><p>Object content will be available after Plan 05/06 implementation.</p></div>';
      });
    } else {
      editorArea.innerHTML = '<div class="editor-empty"><p>Loading ' + escapeHtml(objectIri) + '...</p></div>';
    }
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

    var currentSizes = splitInstance.getSizes();

    if (paneStates[paneId]) {
      // Restore the pane
      splitInstance.setSizes(paneStates[paneId]);
      delete paneStates[paneId];
    } else {
      // Collapse the pane: save current sizes, set pane to 0
      paneStates[paneId] = currentSizes.slice();
      var newSizes = currentSizes.slice();
      var redistributed = newSizes[paneIndex];
      newSizes[paneIndex] = 0;
      // Distribute space to other panes proportionally
      var remaining = panes.filter(function (_, i) { return i !== paneIndex && newSizes[i] > 0; });
      if (remaining.length > 0) {
        var share = redistributed / remaining.length;
        panes.forEach(function (_, i) {
          if (i !== paneIndex && newSizes[i] > 0) {
            newSizes[i] += share;
          }
        });
      }
      splitInstance.setSizes(newSizes);
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
    });
  }

  function saveCurrentObject() {
    var activeIri = getActiveTabIri();
    if (!activeIri) return;
    console.log('Save triggered for:', activeIri);
    // Save implementation will be wired in Plan 05/06
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
          id: 'toggle-nav',
          title: 'Toggle Navigation Panel',
          section: 'View',
          hotkey: 'ctrl+b',
          handler: function () { togglePane('nav-pane'); }
        },
        {
          id: 'toggle-right',
          title: 'Toggle Properties Panel',
          section: 'View',
          handler: function () { togglePane('right-pane'); }
        }
      ];
    }).catch(function () {
      console.warn('ninja-keys custom element not available');
    });
  }

  function showTypePicker() {
    // Placeholder: will be implemented in Plan 05 (SHACL forms)
    console.log('Type picker will be available after Plan 05 implementation.');
    alert('New Object: type picker coming soon (Plan 05).');
  }

  function triggerValidation() {
    // Placeholder: will be wired in Plan 06
    console.log('Validation will be available after Plan 06 implementation.');
    alert('Run Validation: coming soon (Plan 06).');
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

  // --- Right Pane Tabs ---

  function initRightPaneTabs() {
    document.addEventListener('click', function (e) {
      var tab = e.target.closest('.rp-tab');
      if (!tab) return;

      // Remove active from all sibling tabs
      var tabs = tab.parentElement.querySelectorAll('.rp-tab');
      tabs.forEach(function (t) { t.classList.remove('active'); });
      tab.classList.add('active');

      // Future: show/hide tab content based on data-tab attribute
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
        loadObjectContent(activeIri);
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
  });

  // --- Export functions globally for htmx onclick handlers ---
  window.openTab = openTab;
  window.closeTab = closeTab;
  window.switchTab = switchTab;
  window.markDirty = markDirty;
  window.markClean = markClean;
  window.togglePane = togglePane;

})();
