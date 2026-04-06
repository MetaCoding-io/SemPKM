/**
 * explorer-config.js — Composable explorer configuration module.
 *
 * Manages the filter/group/sort config builder panel in OBJECTS explorer
 * sections. Supports multiple independent OBJECTS sections, each with
 * its own config state (filter, group, sort, active config ID).
 *
 * DOM access is section-scoped via sectionRoot.querySelector() — no
 * global IDs are used for config elements within a section.
 *
 * Exports to window.SemPKM:
 *   - initExplorerConfig()              — init primary section
 *   - applyExplorerConfig()             — apply primary section config
 *   - resetExplorerConfig()             — reset primary section
 *   - refreshExplorerTree()             — re-apply primary section config
 *   - refreshExplorerTreeForSection(el) — re-apply a specific section's config
 *   - toggleExplorerConfig()            — toggle primary section panel
 *   - loadConfigList()                  — load config list for primary section
 *   - saveCurrentConfig(btnEl)          — save config (section-scoped)
 *   - deleteSelectedConfig(btnEl)       — delete config (section-scoped)
 *   - onConfigSelectorChange(selectEl)  — handle dropdown change (section-scoped)
 *   - duplicateExplorerSection()        — duplicate the OBJECTS section
 *
 *   Internal helpers exposed for onclick wiring:
 *   - _applyFromPanel(btnEl)
 *   - _resetFromPanel(btnEl)
 *   - _openPanelFromSummary(summaryEl)
 *   - _resetFromSummary(btnEl)
 */
(function () {
  'use strict';

  window.SemPKM = window.SemPKM || {};

  // --- Per-section state ---
  // Map keyed by sectionRoot DOM element → { configActive, optionsData,
  //   optionsLoaded, configList, hierarchyActive, sectionIndex }
  var _sectionState = new Map();
  var _nextSectionIndex = 1; // 0 is the primary section

  // Shared options data — fetched once, reused by all sections
  var _sharedOptionsData = null;
  var _sharedOptionsLoaded = false;
  var _sharedConfigList = []; // cached API list of configs + presets

  var _HIERARCHY_VALUE = '__hierarchy__';

  // --- Section state helpers ---

  function _getState(section) {
    if (!section) return null;
    if (!_sectionState.has(section)) {
      var idx = section.id === 'section-objects' ? 0 : _nextSectionIndex++;
      _sectionState.set(section, {
        configActive: false,
        hierarchyActive: false,
        sectionIndex: idx,
      });
    }
    return _sectionState.get(section);
  }

  function _lsKey(section) {
    var state = _getState(section);
    var idx = state ? state.sectionIndex : 0;
    return idx === 0
      ? 'sempkm_explorer_active_config'
      : 'sempkm_explorer_active_config_' + idx;
  }

  // --- DOM helpers (section-scoped) ---

  function _primarySection() {
    return document.getElementById('section-objects');
  }

  function _q(section, cls) {
    return section ? section.querySelector('.' + cls) : null;
  }

  function _typeSelect(s)    { return _q(s, 'explorer-config-type'); }
  function _groupSelect(s)   { return _q(s, 'explorer-config-group'); }
  function _sortSelect(s)    { return _q(s, 'explorer-config-sort'); }
  function _sortOrderBtn(s)  { return _q(s, 'explorer-config-sort-order'); }
  function _panel(s)         { return _q(s, 'explorer-config-panel'); }
  function _summary(s)       { return _q(s, 'explorer-config-summary'); }
  function _summaryText(s)   { return _q(s, 'explorer-config-summary-text'); }
  function _treeBody(s)      { return _q(s, 'explorer-tree-body'); }
  function _configDropdown(s){ return _q(s, 'explorer-config-dropdown'); }
  function _configNameInput(s){ return _q(s, 'explorer-config-name'); }
  function _deleteBtn(s)     { return _q(s, 'explorer-config-delete-btn'); }
  function _selectorRow(s)   { return _q(s, 'explorer-config-selector'); }

  /**
   * Walk up from any element inside a section to find the section root.
   */
  function _findSection(el) {
    if (!el) return _primarySection();
    var node = el;
    while (node && !node.classList.contains('explorer-section')) {
      node = node.parentElement;
    }
    return node || _primarySection();
  }

  // --- Config list (saved configs + presets) ---

  /**
   * Fetch saved configs + presets from API once, then populate all sections.
   */
  async function loadConfigList(section) {
    section = section || _primarySection();

    try {
      var resp = await window.SemPKM.apiFetch('/browser/api/explorer/configs', { silent: true });
      if (!resp) return;
      _sharedConfigList = await resp.json();
    } catch (err) {
      console.error('[explorer-config] Failed to load config list:', err);
      _sharedConfigList = [];
    }

    _populateConfigDropdown(section);

    // Restore last active config from localStorage
    var lastId = localStorage.getItem(_lsKey(section));
    if (lastId) {
      var dd = _configDropdown(section);
      if (dd) {
        var found = Array.from(dd.options).some(function (o) { return o.value === lastId; });
        if (found) {
          dd.value = lastId;
          _updateDeleteButton(section);
          _applyConfigById(section, lastId, true);
        } else {
          localStorage.removeItem(_lsKey(section));
        }
      }
    }
  }

  /**
   * Populate the config selector dropdown for a specific section.
   */
  function _populateConfigDropdown(section) {
    var dd = _configDropdown(section);
    if (!dd) return;

    var currentVal = dd.value;
    dd.innerHTML = '';

    // Default option
    var defaultOpt = document.createElement('option');
    defaultOpt.value = '';
    defaultOpt.textContent = '— Select Config —';
    dd.appendChild(defaultOpt);

    // Presets group
    var presets = _sharedConfigList.filter(function (c) { return c.is_preset; });
    var presetGroup = document.createElement('optgroup');
    presetGroup.label = 'Presets';

    presets.forEach(function (p) {
      var opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.name;
      opt.dataset.preset = 'true';
      presetGroup.appendChild(opt);
    });

    // Hierarchy pseudo-preset
    var hierOpt = document.createElement('option');
    hierOpt.value = _HIERARCHY_VALUE;
    hierOpt.textContent = 'Hierarchy';
    hierOpt.dataset.preset = 'true';
    presetGroup.appendChild(hierOpt);

    dd.appendChild(presetGroup);

    // User configs group
    var userConfigs = _sharedConfigList.filter(function (c) { return !c.is_preset; });
    if (userConfigs.length > 0) {
      var userGroup = document.createElement('optgroup');
      userGroup.label = 'Saved Configs';

      userConfigs.forEach(function (c) {
        var opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.name;
        userGroup.appendChild(opt);
      });

      dd.appendChild(userGroup);
    }

    // Restore selection
    if (currentVal) {
      var exists = Array.from(dd.options).some(function (o) { return o.value === currentVal; });
      if (exists) dd.value = currentVal;
    }

    _updateDeleteButton(section);
  }

  /**
   * Enable/disable delete button based on selection.
   */
  function _updateDeleteButton(section) {
    var dd = _configDropdown(section);
    var btn = _deleteBtn(section);
    if (!dd || !btn) return;

    var val = dd.value;
    if (!val || val === _HIERARCHY_VALUE) {
      btn.disabled = true;
      return;
    }

    var selectedOpt = dd.options[dd.selectedIndex];
    btn.disabled = !!(selectedOpt && selectedOpt.dataset.preset === 'true');
  }

  /**
   * Handle config selector dropdown change.
   * @param {HTMLSelectElement} selectEl — the dropdown that changed
   */
  function onConfigSelectorChange(selectEl) {
    var section = _findSection(selectEl);
    var value = selectEl.value;

    _updateDeleteButton(section);

    if (!value) {
      resetExplorerConfigForSection(section);
      localStorage.removeItem(_lsKey(section));
      return;
    }

    localStorage.setItem(_lsKey(section), value);
    _applyConfigById(section, value, false);
  }

  /**
   * Apply a config by its ID for a specific section.
   */
  function _applyConfigById(section, configId, silent) {
    if (configId === _HIERARCHY_VALUE) {
      _applyHierarchy(section);
      return;
    }

    var cfg = _sharedConfigList.find(function (c) { return c.id === configId; });
    if (!cfg) return;

    var configData = cfg.config || {};

    var typeSel = _typeSelect(section);
    var groupSel = _groupSelect(section);
    var sortSel = _sortSelect(section);
    var sortOrderBtn = _sortOrderBtn(section);

    if (typeSel) typeSel.value = configData.type_filter || '';
    if (groupSel) groupSel.value = configData.group_by || '';
    if (sortSel) sortSel.value = configData.sort_by || 'label';
    if (sortOrderBtn) {
      var order = configData.sort_order || 'asc';
      sortOrderBtn.dataset.order = order;
      sortOrderBtn.innerHTML = order === 'asc' ? '&#9650;' : '&#9660;';
    }

    var state = _getState(section);
    state.hierarchyActive = false;
    var panel = _panel(section);
    if (panel) panel.style.display = '';

    applyExplorerConfigForSection(section);
    _updateSummaryWithName(section, cfg.name);
  }

  /**
   * Apply Hierarchy pseudo-preset for a specific section.
   */
  function _applyHierarchy(section) {
    var state = _getState(section);
    state.hierarchyActive = true;
    state.configActive = true;

    var panel = _panel(section);
    if (panel) panel.style.display = 'none';

    var body = _treeBody(section);
    if (!body) return;

    htmx.ajax('GET', '/browser/explorer/tree?mode=hierarchy', { target: body, swap: 'innerHTML' }).then(function () {
      if (typeof lucide !== 'undefined') lucide.createIcons();
    });

    _updateSummaryWithName(section, 'Hierarchy');
  }

  /**
   * Update summary bar with a config name.
   */
  function _updateSummaryWithName(section, name) {
    var summary = _summary(section);
    var summaryText = _summaryText(section);
    if (!summary || !summaryText) return;

    summaryText.textContent = name;
    var panel = _panel(section);
    if (!panel || !panel.classList.contains('open')) {
      summary.classList.add('visible');
    }
  }

  /**
   * Save current dropdown state as a named config (section-scoped).
   */
  async function saveCurrentConfig(btnEl) {
    var section = _findSection(btnEl);
    var nameInput = _configNameInput(section);
    if (!nameInput) return;

    var name = nameInput.value.trim();
    if (!name) {
      nameInput.focus();
      nameInput.classList.add('input-error');
      setTimeout(function () { nameInput.classList.remove('input-error'); }, 1500);
      return;
    }

    var configData = _readCurrentConfig(section);

    try {
      var resp = await window.SemPKM.apiFetch('/browser/api/explorer/configs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, config: configData }),
        silent: true,
      });
      if (!resp || !resp.ok) {
        console.error('[explorer-config] Save failed');
        return;
      }

      var result = await resp.json();
      nameInput.value = '';

      // Reload config list for this section and select the new config
      await loadConfigList(section);
      var dd = _configDropdown(section);
      if (dd && result.id) {
        dd.value = result.id;
        localStorage.setItem(_lsKey(section), result.id);
        _updateDeleteButton(section);
      }
    } catch (err) {
      console.error('[explorer-config] Save error:', err);
    }
  }

  /**
   * Delete the currently selected user config (section-scoped).
   */
  async function deleteSelectedConfig(btnEl) {
    var section = _findSection(btnEl);
    var dd = _configDropdown(section);
    if (!dd) return;

    var configId = dd.value;
    if (!configId || configId === _HIERARCHY_VALUE) return;

    var selectedOpt = dd.options[dd.selectedIndex];
    if (selectedOpt && selectedOpt.dataset.preset === 'true') return;

    try {
      var resp = await window.SemPKM.apiFetch('/browser/api/explorer/configs/' + encodeURIComponent(configId), {
        method: 'DELETE',
        silent: true,
      });
      if (!resp || !resp.ok) {
        console.error('[explorer-config] Delete failed');
        return;
      }

      localStorage.removeItem(_lsKey(section));

      await loadConfigList(section);
      resetExplorerConfigForSection(section);
    } catch (err) {
      console.error('[explorer-config] Delete error:', err);
    }
  }

  /**
   * Read current filter/group/sort dropdown values from a section.
   */
  function _readCurrentConfig(section) {
    return {
      type_filter: (_typeSelect(section) || {}).value || '',
      group_by: (_groupSelect(section) || {}).value || '',
      sort_by: (_sortSelect(section) || {}).value || 'label',
      sort_order: (_sortOrderBtn(section) ? _sortOrderBtn(section).dataset.order : 'asc'),
    };
  }

  // --- Fetch and populate options ---

  /**
   * Initialize the config builder for a section: fetch options, populate dropdowns.
   */
  async function initExplorerConfigForSection(section) {
    if (_sharedOptionsLoaded && _sharedOptionsData) {
      _populateTypeDropdown(section);
      _bindTypeChangeHandler(section);
      return;
    }

    try {
      var resp = await window.SemPKM.apiFetch('/browser/explorer/config-options', { silent: true });
      if (!resp) return;
      _sharedOptionsData = await resp.json();
      _sharedOptionsLoaded = true;
      _populateTypeDropdown(section);
      _bindTypeChangeHandler(section);
    } catch (err) {
      console.error('[explorer-config] Failed to load config options:', err);
    }
  }

  /** Backward-compat wrapper for primary section. */
  async function initExplorerConfig() {
    return initExplorerConfigForSection(_primarySection());
  }

  function _populateTypeDropdown(section) {
    var sel = _typeSelect(section);
    if (!sel || !_sharedOptionsData) return;

    sel.innerHTML = '<option value="">All Types</option>';

    var types = _sharedOptionsData.types || [];
    types.forEach(function (t) {
      var opt = document.createElement('option');
      opt.value = t.iri;
      opt.textContent = t.label;
      sel.appendChild(opt);
    });
  }

  function _bindTypeChangeHandler(section) {
    var sel = _typeSelect(section);
    if (!sel || sel._configBound) return;
    sel._configBound = true;

    sel.addEventListener('change', function () {
      _updatePropertyDropdowns(section, sel.value);
    });
  }

  function _updatePropertyDropdowns(section, typeIri) {
    if (!_sharedOptionsData) return;

    var groupSel = _groupSelect(section);
    var sortSel = _sortSelect(section);

    if (groupSel) {
      var currentGroup = groupSel.value;
      groupSel.innerHTML = '';

      var builtinGroup = document.createElement('option');
      builtinGroup.value = '';
      builtinGroup.textContent = 'None';
      groupSel.appendChild(builtinGroup);

      (_sharedOptionsData.group_by_builtins || []).forEach(function (b) {
        var opt = document.createElement('option');
        opt.value = b.value;
        opt.textContent = b.label;
        groupSel.appendChild(opt);
      });

      if (typeIri && _sharedOptionsData.groupable_properties && _sharedOptionsData.groupable_properties[typeIri]) {
        var sep = document.createElement('option');
        sep.disabled = true;
        sep.textContent = '── Properties ──';
        groupSel.appendChild(sep);

        _sharedOptionsData.groupable_properties[typeIri].forEach(function (p) {
          var opt = document.createElement('option');
          opt.value = 'prop:' + p.iri;
          opt.textContent = p.label + (p.preferred_group ? ' ★' : '');
          groupSel.appendChild(opt);
        });
      }

      if (currentGroup) {
        var found = Array.from(groupSel.options).some(function (o) { return o.value === currentGroup; });
        if (found) groupSel.value = currentGroup;
      }
    }

    if (sortSel) {
      var currentSort = sortSel.value;
      sortSel.innerHTML = '';

      (_sharedOptionsData.sort_by_builtins || []).forEach(function (b) {
        var opt = document.createElement('option');
        opt.value = b.value;
        opt.textContent = b.label;
        sortSel.appendChild(opt);
      });

      if (typeIri && _sharedOptionsData.sortable_properties && _sharedOptionsData.sortable_properties[typeIri]) {
        var sep = document.createElement('option');
        sep.disabled = true;
        sep.textContent = '── Properties ──';
        sortSel.appendChild(sep);

        _sharedOptionsData.sortable_properties[typeIri].forEach(function (p) {
          var opt = document.createElement('option');
          opt.value = 'prop:' + p.iri;
          opt.textContent = p.label;
          sortSel.appendChild(opt);
        });
      }

      if (currentSort) {
        var found = Array.from(sortSel.options).some(function (o) { return o.value === currentSort; });
        if (found) sortSel.value = currentSort;
      }
    }
  }

  // --- Apply / Reset / Refresh (section-scoped) ---

  /**
   * Apply config for a specific section — reads dropdowns and fetches config-tree.
   */
  function applyExplorerConfigForSection(section) {
    var state = _getState(section);

    if (state.hierarchyActive) {
      _applyHierarchy(section);
      return;
    }

    var body = _treeBody(section);
    if (!body) return;

    var typeFilter = (_typeSelect(section) || {}).value || '';
    var groupBy = (_groupSelect(section) || {}).value || '';
    var sortBy = (_sortSelect(section) || {}).value || 'label';
    var sortOrderBtn = _sortOrderBtn(section);
    var sortOrder = sortOrderBtn ? (sortOrderBtn.dataset.order || 'asc') : 'asc';

    var params = [];
    if (typeFilter) params.push('type_filter=' + encodeURIComponent(typeFilter));
    if (groupBy) params.push('group_by=' + encodeURIComponent(groupBy));
    params.push('sort_by=' + encodeURIComponent(sortBy));
    params.push('sort_order=' + encodeURIComponent(sortOrder));

    var url = '/browser/explorer/config-tree?' + params.join('&');

    state.configActive = !!(typeFilter || groupBy || sortBy !== 'label' || sortOrder !== 'asc');

    var panel = _panel(section);
    if (panel) panel.classList.remove('open');

    _updateSummary(section, typeFilter, groupBy, sortBy, sortOrder);

    htmx.ajax('GET', url, { target: body, swap: 'innerHTML' }).then(function () {
      if (typeof lucide !== 'undefined') lucide.createIcons();
    });
  }

  /** Backward-compat wrapper: apply on primary section. */
  function applyExplorerConfig() {
    applyExplorerConfigForSection(_primarySection());
  }

  function _updateSummary(section, typeFilter, groupBy, sortBy, sortOrder) {
    var summary = _summary(section);
    var summaryText = _summaryText(section);
    if (!summary || !summaryText) return;
    var state = _getState(section);

    var dd = _configDropdown(section);
    if (dd && dd.value) {
      var selectedOpt = dd.options[dd.selectedIndex];
      if (selectedOpt && selectedOpt.textContent) {
        _updateSummaryWithName(section, selectedOpt.textContent);
        return;
      }
    }

    if (!state.configActive) {
      summary.classList.remove('visible');
      return;
    }

    var parts = [];

    var typeSel = _typeSelect(section);
    if (typeFilter && typeSel) {
      var opt = typeSel.options[typeSel.selectedIndex];
      parts.push(opt ? opt.textContent : 'Filtered');
    }

    var groupSel = _groupSelect(section);
    if (groupBy && groupSel) {
      var groupOpt = groupSel.options[groupSel.selectedIndex];
      parts.push('→ ' + (groupOpt ? groupOpt.textContent : groupBy));
    }

    var sortSel = _sortSelect(section);
    if (sortSel) {
      var sortOpt = sortSel.options[sortSel.selectedIndex];
      var arrow = sortOrder === 'asc' ? '↑' : '↓';
      parts.push('→ ' + (sortOpt ? sortOpt.textContent : sortBy) + ' ' + arrow);
    }

    summaryText.textContent = parts.join(' ');
    summary.classList.add('visible');
  }

  /**
   * Reset config controls for a specific section.
   */
  function resetExplorerConfigForSection(section) {
    var typeSel = _typeSelect(section);
    var groupSel = _groupSelect(section);
    var sortSel = _sortSelect(section);
    var sortOrderBtn = _sortOrderBtn(section);

    if (typeSel) typeSel.value = '';
    if (groupSel) {
      _updatePropertyDropdowns(section, '');
      groupSel.value = '';
    }
    if (sortSel) {
      _updatePropertyDropdowns(section, '');
      sortSel.value = 'label';
    }
    if (sortOrderBtn) {
      sortOrderBtn.dataset.order = 'asc';
      sortOrderBtn.innerHTML = '&#9650;';
    }

    var state = _getState(section);
    state.configActive = false;
    state.hierarchyActive = false;

    var dd = _configDropdown(section);
    if (dd) dd.value = '';
    _updateDeleteButton(section);
    localStorage.removeItem(_lsKey(section));

    var panel = _panel(section);
    if (panel) panel.style.display = '';

    var summary = _summary(section);
    if (summary) summary.classList.remove('visible');

    if (panel) panel.classList.remove('open');

    // Reload default tree
    var body = _treeBody(section);
    if (body) {
      // Primary section uses the standard refreshNavTree
      if (section === _primarySection() && typeof window.SemPKM.refreshNavTree === 'function') {
        window.SemPKM.refreshNavTree();
      } else {
        // Duplicate sections reload the default nav_tree
        htmx.ajax('GET', '/browser/explorer/tree', { target: body, swap: 'innerHTML' }).then(function () {
          if (typeof lucide !== 'undefined') lucide.createIcons();
        });
      }
    }
  }

  /** Backward-compat wrapper: reset primary section. */
  function resetExplorerConfig() {
    resetExplorerConfigForSection(_primarySection());
  }

  /**
   * Re-apply config for a section (used after CRUD operations).
   */
  function refreshExplorerTreeForSection(section) {
    var state = _getState(section);
    if (state && state.configActive) {
      applyExplorerConfigForSection(section);
    } else {
      var body = _treeBody(section);
      if (body) {
        if (section === _primarySection() && typeof window.SemPKM.refreshNavTree === 'function') {
          window.SemPKM.refreshNavTree();
        } else {
          htmx.ajax('GET', '/browser/explorer/tree', { target: body, swap: 'innerHTML' }).then(function () {
            if (typeof lucide !== 'undefined') lucide.createIcons();
          });
        }
      }
    }
  }

  /** Backward-compat: refreshExplorerTree operates on primary section. */
  function refreshExplorerTree() {
    refreshExplorerTreeForSection(_primarySection());
  }

  /**
   * Toggle config panel for primary section.
   */
  function toggleExplorerConfig() {
    _toggleExplorerConfigForSection(_primarySection());
  }

  function _toggleExplorerConfigForSection(section) {
    var panel = _panel(section);
    if (!panel) return;

    var state = _getState(section);

    if (state.hierarchyActive) {
      var selector = _selectorRow(section);
      if (selector) selector.classList.toggle('collapsed');
      return;
    }

    if (panel.classList.contains('open')) {
      panel.classList.remove('open');
      if (state.configActive) {
        var summary = _summary(section);
        if (summary) summary.classList.add('visible');
      }
    } else {
      panel.classList.add('open');
      var summary = _summary(section);
      if (summary) summary.classList.remove('visible');
      initExplorerConfigForSection(section);
    }
  }

  // --- onclick helpers (wired from HTML template) ---

  function _applyFromPanel(btnEl) {
    applyExplorerConfigForSection(_findSection(btnEl));
  }

  function _resetFromPanel(btnEl) {
    resetExplorerConfigForSection(_findSection(btnEl));
  }

  function _openPanelFromSummary(summaryEl) {
    var section = _findSection(summaryEl);
    initExplorerConfigForSection(section);
    var panel = _panel(section);
    if (panel) panel.classList.add('open');
    summaryEl.classList.remove('visible');
  }

  function _resetFromSummary(btnEl) {
    resetExplorerConfigForSection(_findSection(btnEl));
  }

  // --- Duplicate OBJECTS section ---

  /**
   * Create a duplicate of the primary OBJECTS explorer section.
   * The clone gets its own config state, tree, and selector.
   */
  function duplicateExplorerSection() {
    var primary = _primarySection();
    if (!primary) return;

    var idx = _nextSectionIndex; // will be assigned in _getState

    // Clone the section
    var clone = primary.cloneNode(true);

    // Remove the primary ID — assign a unique one
    clone.id = 'section-objects-' + idx;
    clone.setAttribute('data-panel-name', 'objects-' + idx);

    // Start expanded
    clone.classList.add('expanded');

    // Update the title to show it's a duplicate
    var title = clone.querySelector('.explorer-section-title');
    if (title) title.textContent = 'OBJECTS (' + idx + ')';

    // Replace the duplicate button with a close button in the header
    var headerActions = clone.querySelector('.explorer-header-actions');
    if (headerActions) {
      // Remove selection badge and bulk-delete from clone
      var badge = headerActions.querySelector('.selection-badge');
      if (badge) badge.remove();
      var bulkDelBtn = headerActions.querySelector('#bulk-delete-btn');
      if (bulkDelBtn) bulkDelBtn.remove();

      // Remove the explorer-config-btn id to avoid duplicates
      var configBtn = headerActions.querySelector('#explorer-config-btn');
      if (configBtn) configBtn.removeAttribute('id');

      // Replace the duplicate button with a close button
      var dupBtn = headerActions.querySelector('[title="Duplicate OBJECTS section"]');
      if (dupBtn) {
        var closeBtn = document.createElement('button');
        closeBtn.className = 'panel-btn explorer-action-btn explorer-section-close-btn';
        closeBtn.title = 'Close this section';
        closeBtn.innerHTML = '<i data-lucide="x"></i>';
        closeBtn.onclick = function (e) {
          e.stopPropagation();
          _removeExplorerSection(clone);
        };
        dupBtn.parentNode.replaceChild(closeBtn, dupBtn);
      }
    }

    // Rewire the settings button in the clone header
    var settingsBtn = clone.querySelector('[title="Configure explorer"]');
    if (settingsBtn) {
      settingsBtn.onclick = function (e) {
        e.stopPropagation();
        _toggleExplorerConfigForSection(clone);
      };
    }

    // Rewire the refresh button
    var refreshBtn = clone.querySelector('[title="Refresh"]');
    if (refreshBtn) {
      refreshBtn.onclick = function (e) {
        e.stopPropagation();
        refreshExplorerTreeForSection(clone);
      };
    }

    // Clear any ID-based references inside the clone body
    var treeBody = clone.querySelector('.explorer-tree-body');
    if (treeBody) {
      treeBody.removeAttribute('id');
      treeBody.innerHTML = '<p style="padding:8px; font-size:0.72rem; color:var(--color-text-muted);">Select a config to load objects.</p>';
    }

    // Reset panel state in clone
    var panel = clone.querySelector('.explorer-config-panel');
    if (panel) {
      panel.classList.remove('open');
      panel.style.display = '';
    }

    var summary = clone.querySelector('.explorer-config-summary');
    if (summary) summary.classList.remove('visible');

    // Insert after the primary section
    primary.parentNode.insertBefore(clone, primary.nextSibling);

    // Initialize the clone's state
    _getState(clone);

    // Populate its config dropdown
    _populateConfigDropdown(clone);

    // Init type dropdown from cached options
    if (_sharedOptionsLoaded && _sharedOptionsData) {
      _populateTypeDropdown(clone);
      _bindTypeChangeHandler(clone);
    }

    // Re-init Lucide icons in the clone
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  /**
   * Remove a duplicated explorer section (not the primary).
   */
  function _removeExplorerSection(section) {
    if (section === _primarySection()) return; // never remove primary

    // Clean up state
    var state = _getState(section);
    if (state) {
      localStorage.removeItem(_lsKey(section));
    }
    _sectionState.delete(section);

    // Remove from DOM
    section.remove();
  }

  // --- Exports ---
  window.SemPKM.initExplorerConfig = initExplorerConfig;
  window.SemPKM.applyExplorerConfig = applyExplorerConfig;
  window.SemPKM.resetExplorerConfig = resetExplorerConfig;
  window.SemPKM.refreshExplorerTree = refreshExplorerTree;
  window.SemPKM.refreshExplorerTreeForSection = refreshExplorerTreeForSection;
  window.SemPKM.toggleExplorerConfig = toggleExplorerConfig;
  window.SemPKM.loadConfigList = loadConfigList;
  window.SemPKM.saveCurrentConfig = saveCurrentConfig;
  window.SemPKM.deleteSelectedConfig = deleteSelectedConfig;
  window.SemPKM.onConfigSelectorChange = onConfigSelectorChange;
  window.SemPKM.duplicateExplorerSection = duplicateExplorerSection;

  // Internal helpers exposed for onclick wiring from template
  window.SemPKM._applyFromPanel = _applyFromPanel;
  window.SemPKM._resetFromPanel = _resetFromPanel;
  window.SemPKM._openPanelFromSummary = _openPanelFromSummary;
  window.SemPKM._resetFromSummary = _resetFromSummary;

})();
