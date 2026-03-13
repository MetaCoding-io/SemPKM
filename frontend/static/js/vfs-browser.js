/**
 * SemPKM VFS File Browser
 *
 * Renders a file-tree from /api/vfs/tree and opens files in tabbed
 * CodeMirror editors on the right pane.  Supports read-only view with
 * an Edit toggle and Save (Ctrl+S) via PUT /api/vfs/file.
 *
 * The tree is a three-level hierarchy:
 *   model → type (folder) → file (.md)
 *
 * File tabs support multiple open files, dirty tracking, and close.
 * Markdown files support side-by-side raw/rendered preview (toggle via button).
 */

(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────────────────

  var openFiles = {};      // { path: { content, iri, label, editor, dirty, editable, previewOn } }
  var activeFilePath = null;
  var treeData = null;

  // CodeMirror module cache (loaded dynamically)
  var _cmModules = null;

  // Debounce timers for live preview sync
  var _previewTimers = {};

  // ── DOM refs ───────────────────────────────────────────────────────

  function $id(id) { return document.getElementById(id); }

  // ── Init ───────────────────────────────────────────────────────────

  function init() {
    // Render Lucide icons in the header (needed when loaded inside dockview
    // panels where the main-page Lucide scan has already completed)
    var container = $id('vfs-container');
    if (container && typeof lucide !== 'undefined') {
      lucide.createIcons({ root: container });
    }

    loadTree();
    initResize();

    var refreshBtn = $id('vfs-refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', function () { loadTree(); });
    }
  }

  // ── CodeMirror dynamic import ──────────────────────────────────────

  function loadCodeMirror() {
    if (_cmModules) return Promise.resolve(_cmModules);
    return Promise.all([
      import('https://esm.sh/@codemirror/view@6'),
      import('https://esm.sh/@codemirror/state@6'),
      import('https://esm.sh/codemirror@6.0.1'),
      import('https://esm.sh/@codemirror/lang-markdown@6')
    ]).then(function (mods) {
      _cmModules = {
        EditorView: mods[0].EditorView,
        keymap: mods[0].keymap,
        EditorState: mods[1].EditorState,
        Compartment: mods[1].Compartment,
        basicSetup: mods[2].basicSetup,
        markdown: mods[3].markdown
      };
      return _cmModules;
    });
  }

  // ── Tree loading ───────────────────────────────────────────────────

  function loadTree() {
    var body = $id('vfs-tree-body');
    if (!body) return;
    body.innerHTML =
      '<div class="vfs-tree-loading">' +
      '<div class="vfs-loading-spinner"></div>' +
      '<span>Loading files...</span></div>';

    // Fetch both model tree and user mounts in parallel
    Promise.all([
      fetch('/api/vfs/tree').then(function (r) { return r.json(); }),
      fetch('/api/vfs/mounts', { credentials: 'include' })
        .then(function (r) { return r.ok ? r.json() : []; })
        .catch(function () { return []; })
    ])
      .then(function (results) {
        treeData = results[0];
        var mounts = results[1];
        renderTree(treeData, mounts);
      })
      .catch(function (err) {
        body.innerHTML = '<div class="vfs-tree-loading" style="color:var(--color-danger,#e74c3c)">Failed to load file tree</div>';
        console.error('VFS tree load error:', err);
      });
  }

  // ── Tree rendering ─────────────────────────────────────────────────

  function renderTree(models, mounts) {
    var body = $id('vfs-tree-body');
    if (!body) return;
    body.innerHTML = '';

    var hasContent = (models && models.length > 0) || (mounts && mounts.length > 0);
    if (!hasContent) {
      body.innerHTML = '<div class="vfs-tree-loading">No files found</div>';
      return;
    }

    // ── Model trees (installed mental models) ──
    if (models && models.length > 0) {
      models.forEach(function (model) {
        var modelNode = createNode({
          label: model.label,
          icon: 'database',
          iconClass: 'vfs-tree-icon--folder',
          expandable: true,
          level: 0,
          expanded: true,
          badge: model.children ? model.children.length + ' types' : ''
        });
        body.appendChild(modelNode);

        var modelChildren = modelNode.querySelector('.vfs-tree-children');

        (model.children || []).forEach(function (typeEntry) {
          var typeNode = createNode({
            label: typeEntry.label,
            icon: 'folder',
            iconClass: 'vfs-tree-icon--folder',
            expandable: true,
            level: 1,
            expanded: false,
            badge: typeEntry.children ? typeEntry.children.length : ''
          });
          modelChildren.appendChild(typeNode);

          var typeChildren = typeNode.querySelector('.vfs-tree-children');

          (typeEntry.children || []).forEach(function (file) {
            var fileNode = createNode({
              label: file.label,
              icon: 'file-text',
              iconClass: 'vfs-tree-icon--file',
              expandable: false,
              level: 2,
              filePath: file.id,
              fileIri: file.iri
            });
            typeChildren.appendChild(fileNode);
          });
        });
      });
    }

    // ── User mount trees ──
    if (mounts && mounts.length > 0) {
      var mountSeparator = document.createElement('div');
      mountSeparator.className = 'vfs-tree-separator';
      mountSeparator.innerHTML = '<span class="vfs-tree-separator-label">CUSTOM MOUNTS</span>';
      body.appendChild(mountSeparator);

      mounts.forEach(function (mount) {
        var strategyLabel = mount.strategy.replace(/-/g, ' ').replace('by ', 'by-');
        var mountNode = createNode({
          label: mount.name,
          icon: _mountStrategyIcon(mount.strategy),
          iconClass: 'vfs-tree-icon--mount',
          expandable: true,
          level: 0,
          expanded: false,
          badge: strategyLabel,
          lazyLoad: true,
          mountId: mount.id,
          mountStrategy: mount.strategy
        });
        body.appendChild(mountNode);
      });
    }

    if (typeof lucide !== 'undefined') lucide.createIcons({ root: body });
  }

  /**
   * Return a Lucide icon name based on the mount strategy.
   */
  function _mountStrategyIcon(strategy) {
    switch (strategy) {
      case 'by-type': return 'shapes';
      case 'by-date': return 'calendar';
      case 'by-tag': return 'tag';
      case 'by-property': return 'list-tree';
      case 'flat': return 'files';
      default: return 'hard-drive';
    }
  }

  function createNode(opts) {
    var node = document.createElement('div');
    node.className = 'vfs-tree-node' + (opts.expanded ? ' expanded' : '');

    var row = document.createElement('div');
    row.className = 'vfs-tree-row';

    // Indentation
    var indent = document.createElement('span');
    indent.className = 'vfs-tree-indent';
    indent.style.width = (opts.level * 16 + 4) + 'px';
    row.appendChild(indent);

    if (opts.expandable) {
      // Chevron
      var chevron = document.createElement('span');
      chevron.className = 'vfs-tree-chevron';
      chevron.innerHTML = '<i data-lucide="chevron-right"></i>';
      row.appendChild(chevron);
    } else {
      // Spacer instead of chevron
      var spacer = document.createElement('span');
      spacer.style.width = '18px';
      spacer.style.flexShrink = '0';
      row.appendChild(spacer);
    }

    // Icon
    var icon = document.createElement('span');
    icon.className = 'vfs-tree-icon ' + (opts.iconClass || '');
    icon.innerHTML = '<i data-lucide="' + opts.icon + '"></i>';
    row.appendChild(icon);

    // Label
    var label = document.createElement('span');
    label.className = 'vfs-tree-label';
    label.textContent = opts.label;
    label.title = opts.label;
    row.appendChild(label);

    // Badge
    if (opts.badge) {
      var badge = document.createElement('span');
      badge.className = 'vfs-tree-badge';
      badge.textContent = opts.badge;
      row.appendChild(badge);
    }

    node.appendChild(row);

    if (opts.expandable) {
      var children = document.createElement('div');
      children.className = 'vfs-tree-children';
      node.appendChild(children);

      row.addEventListener('click', function () {
        node.classList.toggle('expanded');
        // Lazy-load mount folder contents on first expand
        if (opts.lazyLoad && !node._loaded) {
          node._loaded = true;
          _loadMountChildren(children, opts.mountId, opts.mountStrategy);
        }
      });
    } else if (opts.filePath) {
      row.addEventListener('click', function () {
        openFile(opts.filePath, opts.label);
        // Highlight active
        document.querySelectorAll('.vfs-tree-row.active').forEach(function (r) {
          r.classList.remove('active');
        });
        row.classList.add('active');
      });
    }

    return node;
  }

  // ── Mount lazy loading ─────────────────────────────────────────────

  /**
   * Load the top-level folder contents for a VFS mount via the explorer
   * API and render them as child nodes in the VFS browser tree.
   *
   * For flat mounts, loads objects directly.
   * For strategy mounts, loads folder nodes that can expand further.
   */
  function _loadMountChildren(container, mountId, strategy) {
    container.innerHTML =
      '<div class="vfs-tree-loading" style="padding:4px 0 4px 24px;font-size:12px">' +
      '<div class="vfs-loading-spinner" style="width:12px;height:12px"></div>' +
      '<span>Loading...</span></div>';

    fetch('/browser/explorer/tree?mode=mount:' + encodeURIComponent(mountId), { credentials: 'include' })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        // The explorer endpoint returns HTML tree nodes. We need to parse
        // the returned objects/folders and re-render as VFS tree nodes.
        var tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;

        container.innerHTML = '';

        // Look for tree-leaf elements (objects) — flat or leaf-level responses
        var leaves = tempDiv.querySelectorAll('.tree-leaf');
        var folders = tempDiv.querySelectorAll('.tree-node');

        if (folders.length > 0) {
          _renderMountFolders(container, folders, mountId);
        } else if (leaves.length > 0) {
          _renderMountLeaves(container, leaves, 1);
        } else {
          container.innerHTML =
            '<div class="vfs-tree-loading" style="padding:4px 0 4px 24px;font-size:12px;opacity:0.6">No files in this mount</div>';
        }

        if (typeof lucide !== 'undefined') lucide.createIcons({ root: container });
      })
      .catch(function (err) {
        container.innerHTML =
          '<div class="vfs-tree-loading" style="padding:4px 0 4px 24px;font-size:12px;color:var(--color-danger)">Failed to load</div>';
        console.error('Mount tree load error:', err);
      });
  }

  /**
   * Render folder nodes from explorer HTML response as VFS tree nodes.
   */
  function _renderMountFolders(container, folderEls, mountId) {
    folderEls.forEach(function (el) {
      var labelEl = el.querySelector('.tree-label');
      var label = labelEl ? labelEl.textContent.trim() : 'Folder';
      var countEl = el.querySelector('.tree-count');
      var count = countEl ? countEl.textContent.trim() : '';

      var folderNode = createNode({
        label: label,
        icon: 'folder',
        iconClass: 'vfs-tree-icon--folder',
        expandable: true,
        level: 1,
        expanded: false,
        badge: count
      });

      // Set up lazy expansion for folder children
      var childContainer = folderNode.querySelector('.vfs-tree-children');
      var folderRow = folderNode.querySelector('.vfs-tree-row');
      var loaded = false;

      // Extract the hx-get URL from the original element for child loading
      var hxGet = el.getAttribute('hx-get') || '';

      folderRow.addEventListener('click', function () {
        if (loaded) return;
        loaded = true;
        _loadMountFolderChildren(childContainer, hxGet);
      });

      container.appendChild(folderNode);
    });
  }

  /**
   * Load sub-folder or object children from an explorer children endpoint.
   */
  function _loadMountFolderChildren(container, url) {
    if (!url) {
      container.innerHTML =
        '<div class="vfs-tree-loading" style="padding:4px 0 4px 24px;font-size:12px;opacity:0.6">No items</div>';
      return;
    }

    container.innerHTML =
      '<div class="vfs-tree-loading" style="padding:4px 0 4px 24px;font-size:12px">' +
      '<div class="vfs-loading-spinner" style="width:12px;height:12px"></div>' +
      '<span>Loading...</span></div>';

    fetch(url, { credentials: 'include' })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        var tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;

        container.innerHTML = '';

        var subFolders = tempDiv.querySelectorAll('.tree-node');
        var leaves = tempDiv.querySelectorAll('.tree-leaf');

        if (subFolders.length > 0) {
          // Nested folders (e.g. by-date year → month)
          subFolders.forEach(function (el) {
            var labelEl = el.querySelector('.tree-label');
            var label = labelEl ? labelEl.textContent.trim() : 'Folder';
            var hxGet = el.getAttribute('hx-get') || '';

            var subNode = createNode({
              label: label,
              icon: 'folder',
              iconClass: 'vfs-tree-icon--folder',
              expandable: true,
              level: 2,
              expanded: false
            });

            var subChildren = subNode.querySelector('.vfs-tree-children');
            var subRow = subNode.querySelector('.vfs-tree-row');
            var subLoaded = false;

            subRow.addEventListener('click', function () {
              if (subLoaded) return;
              subLoaded = true;
              _loadMountFolderChildren(subChildren, hxGet);
            });

            container.appendChild(subNode);
          });
        }

        if (leaves.length > 0) {
          _renderMountLeaves(container, leaves, subFolders.length > 0 ? 3 : 2);
        }

        if (subFolders.length === 0 && leaves.length === 0) {
          container.innerHTML =
            '<div class="vfs-tree-loading" style="padding:4px 0 4px 24px;font-size:12px;opacity:0.6">Empty folder</div>';
        }

        if (typeof lucide !== 'undefined') lucide.createIcons({ root: container });
      })
      .catch(function (err) {
        container.innerHTML =
          '<div class="vfs-tree-loading" style="padding:4px 0 4px 24px;font-size:12px;color:var(--color-danger)">Failed to load</div>';
        console.error('Mount folder children error:', err);
      });
  }

  /**
   * Render leaf (object) nodes from explorer HTML tree-leaf elements.
   */
  function _renderMountLeaves(container, leafEls, level) {
    leafEls.forEach(function (el) {
      var labelEl = el.querySelector('.tree-label') || el.querySelector('.tree-leaf-label');
      var label = labelEl ? labelEl.textContent.trim() : 'Object';
      var iri = el.getAttribute('data-iri') || el.getAttribute('onclick') || '';

      // Extract IRI from onclick handler if needed (handleTreeLeafClick('iri','label'))
      var iriMatch = iri.match(/handleTreeLeafClick\s*\(\s*'([^']+)'/);
      if (iriMatch) iri = iriMatch[1];
      else if (!iri.startsWith('http') && !iri.startsWith('urn:')) iri = '';

      var fileNode = createNode({
        label: label,
        icon: 'file-text',
        iconClass: 'vfs-tree-icon--file',
        expandable: false,
        level: level
      });

      if (iri) {
        var row = fileNode.querySelector('.vfs-tree-row');
        row.addEventListener('click', function () {
          // Open the object in the workspace via openTab (if available)
          if (typeof window.openTab === 'function') {
            window.openTab(iri, label);
          } else {
            window.location.href = '/browser/object/' + encodeURIComponent(iri);
          }
        });
        row.style.cursor = 'pointer';
      }

      container.appendChild(fileNode);
    });
  }

  /**
   * Open the Settings tab scrolled to the Custom Mounts section.
   * Used by the "+" button in the VFS browser header.
   *
   * In the workspace (dockview active), opens a Settings panel tab.
   * On the standalone VFS page, navigates to /browser/settings.
   */
  function openMountSettings() {
    // Check if dockview workspace is actually active (not just function exists)
    if (window._dockview && typeof window.openSettingsTab === 'function') {
      window.openSettingsTab();
      // Wait for settings to render, then switch to VFS category and scroll to mounts
      _waitForSettingsAndShowMounts();
    } else {
      // Standalone VFS page or no dockview — navigate directly
      window.location.href = '/browser/settings#vfs-mount-section';
    }
  }

  /**
   * Poll for the settings VFS category button and click it, then scroll
   * to the Custom Mounts section. Settings content loads via htmx so we
   * need to wait for both the category nav and the mount section to appear.
   */
  function _waitForSettingsAndShowMounts(attempts) {
    if (!attempts) attempts = 0;
    if (attempts > 20) return; // give up after ~2s

    var vfsBtn = document.querySelector('.settings-category-btn[data-category="virtual-filesystem"]');
    if (!vfsBtn) {
      setTimeout(function () { _waitForSettingsAndShowMounts(attempts + 1); }, 100);
      return;
    }

    // Click the VFS category tab
    vfsBtn.click();

    // Wait for the mount section to render (htmx loads VFS content)
    setTimeout(function () {
      var mountSection = document.getElementById('vfs-mount-section');
      if (mountSection) {
        mountSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        mountSection.classList.add('vfs-mount-highlight');
        setTimeout(function () { mountSection.classList.remove('vfs-mount-highlight'); }, 2000);
      }
    }, 300);
  }

  // Expose for the + button onclick
  window.openMountSettings = openMountSettings;

  // ── File opening ───────────────────────────────────────────────────

  function openFile(path, label) {
    // Already open? Just switch to it
    if (openFiles[path]) {
      switchToFile(path);
      return;
    }

    // Show editor area
    var emptyEl = $id('vfs-editor-empty');
    var tabsEl = $id('vfs-editor-tabs');
    if (emptyEl) emptyEl.style.display = 'none';
    if (tabsEl) tabsEl.style.display = 'flex';

    var isMarkdown = /\.md$/i.test(path);

    // Create tab (with preview toggle button for markdown files)
    addTab(path, label, isMarkdown);

    // Create editor panel with side-by-side layout for markdown
    var contentEl = $id('vfs-editor-content');
    var panel = document.createElement('div');
    panel.className = 'vfs-editor-panel';
    panel.id = 'vfs-panel-' + _pathId(path);

    var pid = _pathId(path);

    panel.innerHTML =
      '<div class="vfs-editor-toolbar">' +
      '  <span class="vfs-editor-path">' + _escapeHtml(path) + '</span>' +
      '  <span class="vfs-editor-status" id="vfs-status-' + pid + '"></span>' +
      '  <button class="btn-sm vfs-toolbar-btn" id="vfs-edit-btn-' + pid + '" title="Click to edit">' +
      '    <i data-lucide="lock"></i></button>' +
      '  <button class="btn-sm btn-primary vfs-toolbar-btn" id="vfs-save-btn-' + pid + '" title="Save (Ctrl+S)" style="display:none;">' +
      '    <i data-lucide="save"></i></button>' +
      '</div>' +
      '<div class="vfs-split-container" id="vfs-split-' + pid + '">' +
      '  <div class="vfs-split-left">' +
      '    <div class="vfs-cm-container" id="vfs-cm-' + pid + '">' +
      '      <div class="vfs-editor-loading"><div class="vfs-loading-spinner"></div> Loading...</div>' +
      '    </div>' +
      '  </div>' +
      (isMarkdown ?
        '  <div class="vfs-split-handle" id="vfs-handle-' + pid + '" style="display:none"></div>' +
        '  <div class="vfs-split-right" id="vfs-split-right-' + pid + '" style="display:none">' +
        '    <div class="vfs-preview-container" id="vfs-preview-' + pid + '">' +
        '      <div class="markdown-body"></div>' +
        '    </div>' +
        '  </div>'
        : '') +
      '</div>';
    contentEl.appendChild(panel);
    if (typeof lucide !== 'undefined') lucide.createIcons({ root: panel });

    // Track file
    openFiles[path] = { content: '', iri: null, label: label, editor: null, dirty: false, editable: false, previewOn: false };

    switchToFile(path);

    // Fetch content and init editor
    fetch('/api/vfs/file?path=' + encodeURIComponent(path))
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        openFiles[path].content = data.content;
        openFiles[path].iri = data.iri;
        initFileEditor(path, data.content, false);
      })
      .catch(function (err) {
        var cmEl = $id('vfs-cm-' + _pathId(path));
        if (cmEl) cmEl.innerHTML = '<div class="vfs-editor-loading" style="color:var(--color-danger,#e74c3c)">Failed to load file</div>';
        showVfsToast('Failed to load file: ' + err.message, 'error');
        console.error('VFS file load error:', err);
      });
  }

  // ── Editor init ────────────────────────────────────────────────────

  function initFileEditor(path, content, editable) {
    loadCodeMirror().then(function (cm) {
      var pid = _pathId(path);
      var containerId = 'vfs-cm-' + pid;
      var container = $id(containerId);
      if (!container) return;
      container.innerHTML = '';

      var file = openFiles[path];
      if (!file) return;

      var isMarkdown = /\.md$/i.test(path);
      var readOnlyCompartment = new cm.Compartment();

      // Unified theme using CSS variables -- resolves dynamically for light/dark
      var unifiedTheme = cm.EditorView.theme({
        '&': {
          backgroundColor: 'var(--color-surface)',
          color: 'var(--color-text)',
          fontSize: '0.85rem'
        },
        '.cm-cursor, .cm-dropCursor': {
          borderLeftColor: 'var(--color-accent)'
        },
        '.cm-gutters': {
          backgroundColor: 'var(--color-surface-raised)',
          color: 'var(--color-text-faint)',
          borderRight: '1px solid var(--color-border)'
        },
        '.cm-activeLineGutter': {
          backgroundColor: 'var(--color-surface-hover)'
        },
        '.cm-activeLine': {
          backgroundColor: 'var(--color-surface-hover)'
        },
        '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {
          backgroundColor: 'var(--color-accent-subtle)'
        }
      });

      var view = new cm.EditorView({
        state: cm.EditorState.create({
          doc: content || '',
          extensions: [
            cm.basicSetup,
            cm.markdown(),
            unifiedTheme,
            readOnlyCompartment.of(cm.EditorState.readOnly.of(!editable)),
            cm.keymap.of([{
              key: 'Mod-s',
              run: function () {
                saveFile(path);
                return true;
              }
            }]),
            cm.EditorView.updateListener.of(function (update) {
              if (update.docChanged && file.editable) {
                file.dirty = true;
                updateTabDirty(path, true);
                // Debounced live preview sync for markdown files
                if (isMarkdown && file.previewOn) {
                  _schedulePreviewUpdate(path);
                }
              }
            })
          ]
        }),
        parent: container
      });

      file.editor = view;
      file._readOnlyCompartment = readOnlyCompartment;
      file._savedContent = content;

      // Render initial preview if this is markdown
      if (isMarkdown) {
        _renderMarkdownPreview(path);
      }

      // Init split-pane resize handle for markdown
      if (isMarkdown) {
        _initSplitResize(pid);
      }

      // Wire edit toggle button (lock/unlock icons)
      var editBtn = $id('vfs-edit-btn-' + pid);
      var saveBtn = $id('vfs-save-btn-' + pid);
      if (editBtn) {
        editBtn.addEventListener('click', function () {
          if (file.editable) {
            // Switch back to read-only
            file.editable = false;
            editBtn.innerHTML = '<i data-lucide="lock"></i>';
            editBtn.title = 'Click to edit';
            if (saveBtn) saveBtn.style.display = 'none';
            view.dispatch({
              effects: readOnlyCompartment.reconfigure(cm.EditorState.readOnly.of(true))
            });
          } else {
            // Switch to edit mode
            file.editable = true;
            editBtn.innerHTML = '<i data-lucide="lock-open"></i>';
            editBtn.title = 'Click to lock';
            if (saveBtn) saveBtn.style.display = '';
            view.dispatch({
              effects: readOnlyCompartment.reconfigure(cm.EditorState.readOnly.of(false))
            });
          }
          if (typeof lucide !== 'undefined') lucide.createIcons({ root: editBtn });
        });
      }
      if (saveBtn) {
        saveBtn.addEventListener('click', function () { saveFile(path); });
      }
    });
  }

  // ── Preview toggle ────────────────────────────────────────────────

  function togglePreview(path) {
    var file = openFiles[path];
    if (!file) return;
    var pid = _pathId(path);
    var handle = $id('vfs-handle-' + pid);
    var right = $id('vfs-split-right-' + pid);
    var splitLeft = $id('vfs-split-' + pid);
    var leftPane = splitLeft ? splitLeft.querySelector('.vfs-split-left') : null;
    var toggleBtn = $id('vfs-preview-toggle-' + pid);

    file.previewOn = !file.previewOn;

    if (file.previewOn) {
      // Show preview pane
      if (handle) handle.style.display = '';
      if (right) right.style.display = '';
      if (leftPane) leftPane.style.flex = '0 0 50%';
      if (toggleBtn) toggleBtn.classList.add('active');
      _renderMarkdownPreview(path);
    } else {
      // Hide preview pane
      if (handle) handle.style.display = 'none';
      if (right) right.style.display = 'none';
      if (leftPane) leftPane.style.flex = '1';
      if (toggleBtn) toggleBtn.classList.remove('active');
    }
  }

  // ── Debounced preview update ──────────────────────────────────────

  function _schedulePreviewUpdate(path) {
    if (_previewTimers[path]) clearTimeout(_previewTimers[path]);
    _previewTimers[path] = setTimeout(function () {
      _renderMarkdownPreview(path);
      delete _previewTimers[path];
    }, 300);
  }

  // ── Split pane resize ─────────────────────────────────────────────

  function _initSplitResize(pid) {
    var handle = $id('vfs-handle-' + pid);
    var splitContainer = $id('vfs-split-' + pid);
    if (!handle || !splitContainer) return;

    var leftPane = splitContainer.querySelector('.vfs-split-left');
    var rightPane = splitContainer.querySelector('.vfs-split-right');
    if (!leftPane || !rightPane) return;

    var dragging = false;

    handle.addEventListener('mousedown', function (e) {
      e.preventDefault();
      dragging = true;
      handle.classList.add('dragging');
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });

    function onMove(e) {
      if (!dragging) return;
      var rect = splitContainer.getBoundingClientRect();
      var totalWidth = rect.width;
      var offsetX = e.clientX - rect.left;
      var leftPct = (offsetX / totalWidth) * 100;
      // Enforce minimum 20% each side
      leftPct = Math.max(20, Math.min(leftPct, 80));
      leftPane.style.flex = '0 0 ' + leftPct + '%';
      rightPane.style.flex = '0 0 ' + (100 - leftPct) + '%';
    }

    function onUp() {
      dragging = false;
      handle.classList.remove('dragging');
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    }
  }

  // ── File save ──────────────────────────────────────────────────────

  function saveFile(path) {
    var file = openFiles[path];
    if (!file || !file.editor || !file.editable) return;

    var content = file.editor.state.doc.toString();
    var pid = _pathId(path);
    var statusEl = $id('vfs-status-' + pid);
    var saveBtn = $id('vfs-save-btn-' + pid);

    // Show saving state
    if (statusEl) {
      statusEl.innerHTML = '<div class="vfs-loading-spinner vfs-loading-spinner--sm"></div> Saving...';
      statusEl.className = 'vfs-editor-status saving';
    }
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.style.opacity = '0.6';
    }

    fetch('/api/vfs/file?path=' + encodeURIComponent(path), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: content })
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function () {
        file.dirty = false;
        file._savedContent = content;
        updateTabDirty(path, false);
        // Show saved flash
        _showSavedFlash(pid);
        showVfsToast('File saved', 'success');
        if (statusEl) {
          statusEl.textContent = '';
          statusEl.className = 'vfs-editor-status';
        }
      })
      .catch(function (err) {
        if (statusEl) {
          statusEl.textContent = 'Save failed';
          statusEl.className = 'vfs-editor-status error';
        }
        showVfsToast('Save failed: ' + err.message, 'error');
        console.error('VFS save error:', err);
      })
      .finally(function () {
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.style.opacity = '';
        }
      });
  }

  // ── Saved flash indicator ─────────────────────────────────────────

  function _showSavedFlash(pid) {
    var toolbar = $id('vfs-status-' + pid);
    if (!toolbar) return;
    var parentEl = toolbar.parentElement;
    if (!parentEl) return;

    // Remove any existing flash
    var existing = parentEl.querySelector('.vfs-saved-flash');
    if (existing) existing.remove();

    var flash = document.createElement('span');
    flash.className = 'vfs-saved-flash';
    flash.textContent = 'Saved';
    parentEl.insertBefore(flash, toolbar.nextSibling);

    // Remove after animation
    setTimeout(function () { flash.remove(); }, 1800);
  }

  // ── Toast notifications ───────────────────────────────────────────

  function showVfsToast(message, type) {
    var container = $id('vfs-editor-pane') || $id('vfs-container');
    if (!container) return;

    var toast = document.createElement('div');
    toast.className = 'vfs-toast vfs-toast--' + (type || 'info');
    toast.textContent = message;
    container.appendChild(toast);

    // Trigger reflow then show
    toast.offsetHeight; // force reflow
    toast.classList.add('vfs-toast--visible');

    setTimeout(function () {
      toast.classList.remove('vfs-toast--visible');
      setTimeout(function () { toast.remove(); }, 300);
    }, 3000);
  }

  // ── Tab management ─────────────────────────────────────────────────

  function addTab(path, label, isMarkdown) {
    var bar = $id('vfs-tab-bar');
    if (!bar) return;

    var pid = _pathId(path);
    var tab = document.createElement('div');
    tab.className = 'vfs-tab';
    tab.id = 'vfs-tab-' + pid;
    tab.setAttribute('data-path', path);

    var tabLabel = document.createElement('span');
    tabLabel.className = 'vfs-tab-label';
    tabLabel.textContent = label;
    tabLabel.title = path;
    tab.appendChild(tabLabel);

    // Preview toggle button (markdown files only)
    if (isMarkdown) {
      var previewBtn = document.createElement('button');
      previewBtn.className = 'vfs-tab-preview-btn';
      previewBtn.id = 'vfs-preview-toggle-' + pid;
      previewBtn.title = 'Toggle preview';
      previewBtn.innerHTML = '<i data-lucide="book-open"></i>';
      previewBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        togglePreview(path);
      });
      tab.appendChild(previewBtn);
    }

    var closeBtn = document.createElement('button');
    closeBtn.className = 'vfs-tab-close';
    closeBtn.innerHTML = '<i data-lucide="x"></i>';
    closeBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      closeFile(path);
    });
    tab.appendChild(closeBtn);

    tab.addEventListener('click', function () {
      switchToFile(path);
    });

    bar.appendChild(tab);
    if (typeof lucide !== 'undefined') lucide.createIcons({ root: tab });
  }

  function switchToFile(path) {
    activeFilePath = path;

    // Update tab active state
    document.querySelectorAll('.vfs-tab').forEach(function (t) {
      t.classList.toggle('active', t.getAttribute('data-path') === path);
    });

    // Show correct panel
    document.querySelectorAll('.vfs-editor-panel').forEach(function (p) {
      p.classList.toggle('active', p.id === 'vfs-panel-' + _pathId(path));
    });

    // Update tree highlight
    // (tree rows don't store path, so we skip this for simplicity)
  }

  function closeFile(path) {
    var file = openFiles[path];
    if (file && file.editor) {
      file.editor.destroy();
    }
    // Clean up preview debounce timer
    if (_previewTimers[path]) {
      clearTimeout(_previewTimers[path]);
      delete _previewTimers[path];
    }
    delete openFiles[path];

    // Remove tab
    var tab = $id('vfs-tab-' + _pathId(path));
    if (tab) tab.remove();

    // Remove panel
    var panel = $id('vfs-panel-' + _pathId(path));
    if (panel) panel.remove();

    // Switch to another open file or show empty state
    var remaining = Object.keys(openFiles);
    if (remaining.length > 0) {
      switchToFile(remaining[remaining.length - 1]);
    } else {
      activeFilePath = null;
      var emptyEl = $id('vfs-editor-empty');
      var tabsEl = $id('vfs-editor-tabs');
      if (emptyEl) emptyEl.style.display = '';
      if (tabsEl) tabsEl.style.display = 'none';
    }
  }

  function updateTabDirty(path, dirty) {
    var tab = $id('vfs-tab-' + _pathId(path));
    if (tab) {
      tab.classList.toggle('dirty', dirty);
    }
  }

  // ── Resize handle ──────────────────────────────────────────────────

  function initResize() {
    var handle = $id('vfs-resize-handle');
    var treePane = $id('vfs-tree-pane');
    if (!handle || !treePane) return;

    var startX, startWidth;

    function onMouseDown(e) {
      e.preventDefault();
      startX = e.clientX;
      startWidth = treePane.offsetWidth;
      handle.classList.add('dragging');
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    }

    function onMouseMove(e) {
      var newWidth = startWidth + (e.clientX - startX);
      newWidth = Math.max(180, Math.min(newWidth, window.innerWidth * 0.5));
      treePane.style.width = newWidth + 'px';
    }

    function onMouseUp() {
      handle.classList.remove('dragging');
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    }

    handle.addEventListener('mousedown', onMouseDown);
  }

  // ── Helpers ────────────────────────────────────────────────────────

  /** Convert path to a safe DOM id fragment */
  function _pathId(path) {
    return path.replace(/[^a-zA-Z0-9]/g, '-');
  }

  function _escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  /** Render markdown preview for a file path using the global marked instance */
  function _renderMarkdownPreview(path) {
    var file = openFiles[path];
    if (!file) return;
    var previewEl = $id('vfs-preview-' + _pathId(path));
    if (!previewEl) return;
    var mdBody = previewEl.querySelector('.markdown-body');
    if (!mdBody) return;

    var content = file.editor ? file.editor.state.doc.toString() : (file.content || '');

    // Strip YAML frontmatter (---\n...\n---) before rendering markdown
    content = content.replace(/^---\n[\s\S]*?\n---\n?/, '');

    if (typeof globalThis.marked !== 'undefined') {
      var rawHtml = globalThis.marked.parse(content);
      if (typeof DOMPurify !== 'undefined') {
        rawHtml = DOMPurify.sanitize(rawHtml);
      }
      mdBody.innerHTML = rawHtml;
    } else {
      mdBody.textContent = content;
    }
  }

  // ── Boot ───────────────────────────────────────────────────────────

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Also re-init when loaded via htmx
  document.addEventListener('htmx:afterSwap', function (e) {
    if (e.detail && e.detail.target && e.detail.target.querySelector &&
        e.detail.target.querySelector('.vfs-container')) {
      init();
    }
  });

})();
