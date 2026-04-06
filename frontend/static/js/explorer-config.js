/**
 * explorer-config.js — Composable explorer configuration module.
 *
 * Manages the filter/group/sort config builder panel in the OBJECTS explorer
 * section. Fetches available options from /browser/explorer/config-options,
 * populates dropdowns, and triggers config-tree renders via htmx.
 *
 * Also manages config persistence: save/load/delete named configs via
 * the /api/explorer/configs CRUD API, plus built-in presets and Hierarchy.
 *
 * Exports to window.SemPKM:
 *   - initExplorerConfig()      — fetch options and populate dropdowns
 *   - applyExplorerConfig()     — apply current config, render tree
 *   - resetExplorerConfig()     — clear config, restore default tree
 *   - refreshExplorerTree()     — re-apply current config (after CRUD)
 *   - toggleExplorerConfig()    — toggle config panel open/closed
 *   - loadConfigList()          — fetch saved configs + presets, populate selector
 *   - saveCurrentConfig()       — save current dropdown state as a named config
 *   - deleteSelectedConfig()    — delete the currently selected config
 *   - onConfigSelectorChange()  — handle config selector dropdown change
 */
(function () {
  'use strict';

  window.SemPKM = window.SemPKM || {};

  // --- Module state ---
  var _optionsLoaded = false;
  var _optionsData = null; // cached response from config-options
  var _configActive = false; // whether a non-default config is applied
  var _configList = []; // cached list of saved configs + presets from API
  var _hierarchyActive = false; // whether the Hierarchy pseudo-preset is active

  var _LS_KEY = 'sempkm_explorer_active_config';
  var _HIERARCHY_VALUE = '__hierarchy__'; // sentinel value for Hierarchy option

  // --- DOM helpers ---
  function _el(id) { return document.getElementById(id); }

  function _typeSelect() { return _el('explorer-config-type'); }
  function _groupSelect() { return _el('explorer-config-group'); }
  function _sortSelect() { return _el('explorer-config-sort'); }
  function _sortOrderBtn() { return _el('explorer-config-sort-order'); }
  function _panel() { return _el('explorer-config-panel'); }
  function _summary() { return _el('explorer-config-summary'); }
  function _summaryText() { return _el('explorer-config-summary-text'); }
  function _treeBody() { return _el('explorer-tree-body'); }
  function _configDropdown() { return _el('explorer-config-dropdown'); }
  function _configNameInput() { return _el('explorer-config-name'); }
  function _deleteBtn() { return _el('explorer-config-delete-btn'); }

  // --- Config list (saved configs + presets) ---

  /**
   * Fetch saved configs + presets from API, populate the selector dropdown.
   * Also restores last active config from localStorage.
   */
  async function loadConfigList() {
    try {
      var resp = await window.SemPKM.apiFetch('/browser/api/explorer/configs', { silent: true });
      if (!resp) return;
      _configList = await resp.json();
    } catch (err) {
      console.error('[explorer-config] Failed to load config list:', err);
      _configList = [];
    }

    _populateConfigDropdown();

    // Restore last active config
    var lastId = localStorage.getItem(_LS_KEY);
    if (lastId) {
      var dd = _configDropdown();
      if (dd) {
        // Check if the stored ID exists in current options
        var found = Array.from(dd.options).some(function (o) { return o.value === lastId; });
        if (found) {
          dd.value = lastId;
          _updateDeleteButton();
          // Apply the restored config silently
          _applyConfigById(lastId, true);
        } else {
          // Stored config no longer exists — clear
          localStorage.removeItem(_LS_KEY);
        }
      }
    }
  }

  /**
   * Populate the config selector dropdown with presets and user configs.
   */
  function _populateConfigDropdown() {
    var dd = _configDropdown();
    if (!dd) return;

    var currentVal = dd.value;
    dd.innerHTML = '';

    // Default option
    var defaultOpt = document.createElement('option');
    defaultOpt.value = '';
    defaultOpt.textContent = '— Select Config —';
    dd.appendChild(defaultOpt);

    // Presets group — includes API presets + Hierarchy special
    var presets = _configList.filter(function (c) { return c.is_preset; });
    if (presets.length > 0 || true) { // always show presets group for Hierarchy
      var presetGroup = document.createElement('optgroup');
      presetGroup.label = 'Presets';

      presets.forEach(function (p) {
        var opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        opt.dataset.preset = 'true';
        presetGroup.appendChild(opt);
      });

      // Hierarchy pseudo-preset (not an API config — uses legacy mode)
      var hierOpt = document.createElement('option');
      hierOpt.value = _HIERARCHY_VALUE;
      hierOpt.textContent = 'Hierarchy';
      hierOpt.dataset.preset = 'true';
      presetGroup.appendChild(hierOpt);

      dd.appendChild(presetGroup);
    }

    // User configs group
    var userConfigs = _configList.filter(function (c) { return !c.is_preset; });
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

    // Restore selection if still valid
    if (currentVal) {
      var exists = Array.from(dd.options).some(function (o) { return o.value === currentVal; });
      if (exists) dd.value = currentVal;
    }

    _updateDeleteButton();
  }

  /**
   * Enable/disable the delete button based on current selection.
   * Presets and Hierarchy cannot be deleted.
   */
  function _updateDeleteButton() {
    var dd = _configDropdown();
    var btn = _deleteBtn();
    if (!dd || !btn) return;

    var val = dd.value;
    if (!val || val === _HIERARCHY_VALUE) {
      btn.disabled = true;
      return;
    }

    // Check if selection is a preset
    var selectedOpt = dd.options[dd.selectedIndex];
    if (selectedOpt && selectedOpt.dataset.preset === 'true') {
      btn.disabled = true;
    } else {
      btn.disabled = false;
    }
  }

  /**
   * Handle config selector dropdown change.
   */
  function onConfigSelectorChange(value) {
    _updateDeleteButton();

    if (!value) {
      // Deselected — reset
      resetExplorerConfig();
      localStorage.removeItem(_LS_KEY);
      return;
    }

    // Persist selection
    localStorage.setItem(_LS_KEY, value);

    _applyConfigById(value, false);
  }

  /**
   * Apply a config by its ID (or the Hierarchy sentinel).
   * @param {string} configId
   * @param {boolean} silent — if true, skip panel close animation
   */
  function _applyConfigById(configId, silent) {
    if (configId === _HIERARCHY_VALUE) {
      _applyHierarchy();
      return;
    }

    // Find the config in the cached list
    var cfg = _configList.find(function (c) { return c.id === configId; });
    if (!cfg) return;

    var configData = cfg.config || {};

    // Set dropdown values from config
    var typeSel = _typeSelect();
    var groupSel = _groupSelect();
    var sortSel = _sortSelect();
    var sortOrderBtn = _sortOrderBtn();

    if (typeSel) typeSel.value = configData.type_filter || '';
    if (groupSel) groupSel.value = configData.group_by || '';
    if (sortSel) sortSel.value = configData.sort_by || 'label';
    if (sortOrderBtn) {
      var order = configData.sort_order || 'asc';
      sortOrderBtn.dataset.order = order;
      sortOrderBtn.innerHTML = order === 'asc' ? '&#9650;' : '&#9660;';
    }

    // Show builder panel if config is non-empty
    _hierarchyActive = false;
    var panel = _panel();
    if (panel) panel.style.display = '';

    // Apply the config (renders tree)
    applyExplorerConfig();

    // Update summary to show config name
    _updateSummaryWithName(cfg.name);
  }

  /**
   * Apply the Hierarchy pseudo-preset — uses legacy /browser/explorer/tree?mode=hierarchy.
   */
  function _applyHierarchy() {
    _hierarchyActive = true;
    _configActive = true;

    // Hide the config builder panel — filter/group/sort don't apply
    var panel = _panel();
    if (panel) panel.style.display = 'none';

    // Load hierarchy tree
    var body = _treeBody();
    if (!body) return;

    htmx.ajax('GET', '/browser/explorer/tree?mode=hierarchy', { target: body, swap: 'innerHTML' }).then(function () {
      if (typeof lucide !== 'undefined') lucide.createIcons();
    });

    _updateSummaryWithName('Hierarchy');
  }

  /**
   * Update summary bar with a config name.
   */
  function _updateSummaryWithName(name) {
    var summary = _summary();
    var summaryText = _summaryText();
    if (!summary || !summaryText) return;

    summaryText.textContent = name;
    // Only show summary if panel is closed
    var panel = _panel();
    if (!panel || !panel.classList.contains('open')) {
      summary.classList.add('visible');
    }
  }

  /**
   * Save the current dropdown state as a named config.
   */
  async function saveCurrentConfig() {
    var nameInput = _configNameInput();
    if (!nameInput) return;

    var name = nameInput.value.trim();
    if (!name) {
      nameInput.focus();
      nameInput.classList.add('input-error');
      setTimeout(function () { nameInput.classList.remove('input-error'); }, 1500);
      return;
    }

    var configData = _readCurrentConfig();

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

      // Reload config list and select the new config
      await loadConfigList();
      var dd = _configDropdown();
      if (dd && result.id) {
        dd.value = result.id;
        localStorage.setItem(_LS_KEY, result.id);
        _updateDeleteButton();
      }
    } catch (err) {
      console.error('[explorer-config] Save error:', err);
    }
  }

  /**
   * Delete the currently selected user config.
   */
  async function deleteSelectedConfig() {
    var dd = _configDropdown();
    if (!dd) return;

    var configId = dd.value;
    if (!configId || configId === _HIERARCHY_VALUE) return;

    // Don't delete presets
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

      localStorage.removeItem(_LS_KEY);

      // Reload config list, reset to default
      await loadConfigList();
      resetExplorerConfig();
    } catch (err) {
      console.error('[explorer-config] Delete error:', err);
    }
  }

  /**
   * Read current filter/group/sort dropdown values into a config object.
   */
  function _readCurrentConfig() {
    return {
      type_filter: (_typeSelect() || {}).value || '',
      group_by: (_groupSelect() || {}).value || '',
      sort_by: (_sortSelect() || {}).value || 'label',
      sort_order: (_sortOrderBtn() ? _sortOrderBtn().dataset.order : 'asc'),
    };
  }

  // --- Fetch and populate options ---

  /**
   * Initialize the config builder: fetch options, populate dropdowns.
   * Safe to call multiple times — only fetches once.
   */
  async function initExplorerConfig() {
    if (_optionsLoaded && _optionsData) {
      return;
    }

    try {
      var resp = await window.SemPKM.apiFetch('/browser/explorer/config-options', { silent: true });
      if (!resp) return;
      _optionsData = await resp.json();
      _optionsLoaded = true;
      _populateTypeDropdown();
      _bindTypeChangeHandler();
    } catch (err) {
      console.error('[explorer-config] Failed to load config options:', err);
    }
  }

  /**
   * Populate the type filter dropdown from API data.
   */
  function _populateTypeDropdown() {
    var sel = _typeSelect();
    if (!sel || !_optionsData) return;

    // Clear existing options except "All Types"
    sel.innerHTML = '<option value="">All Types</option>';

    var types = _optionsData.types || [];
    types.forEach(function (t) {
      var opt = document.createElement('option');
      opt.value = t.iri;
      opt.textContent = t.label;
      sel.appendChild(opt);
    });
  }

  /**
   * When type changes, update group-by and sort dropdowns with
   * type-specific properties from the cached options data.
   */
  function _bindTypeChangeHandler() {
    var sel = _typeSelect();
    if (!sel) return;

    sel.addEventListener('change', function () {
      _updatePropertyDropdowns(sel.value);
    });
  }

  /**
   * Repopulate group-by and sort dropdowns for a given type IRI.
   * Keeps built-in options and appends type-specific properties.
   */
  function _updatePropertyDropdowns(typeIri) {
    if (!_optionsData) return;

    var groupSel = _groupSelect();
    var sortSel = _sortSelect();

    // --- Group-by ---
    if (groupSel) {
      var currentGroup = groupSel.value;
      groupSel.innerHTML = '';

      // Built-in options
      var builtinGroup = document.createElement('option');
      builtinGroup.value = '';
      builtinGroup.textContent = 'None';
      groupSel.appendChild(builtinGroup);

      (_optionsData.group_by_builtins || []).forEach(function (b) {
        var opt = document.createElement('option');
        opt.value = b.value;
        opt.textContent = b.label;
        groupSel.appendChild(opt);
      });

      // Type-specific properties
      if (typeIri && _optionsData.groupable_properties && _optionsData.groupable_properties[typeIri]) {
        var sep = document.createElement('option');
        sep.disabled = true;
        sep.textContent = '── Properties ──';
        groupSel.appendChild(sep);

        _optionsData.groupable_properties[typeIri].forEach(function (p) {
          var opt = document.createElement('option');
          opt.value = 'prop:' + p.iri;
          opt.textContent = p.label + (p.preferred_group ? ' ★' : '');
          groupSel.appendChild(opt);
        });
      }

      // Restore previous selection if still valid
      if (currentGroup) {
        var found = Array.from(groupSel.options).some(function (o) { return o.value === currentGroup; });
        if (found) groupSel.value = currentGroup;
      }
    }

    // --- Sort-by ---
    if (sortSel) {
      var currentSort = sortSel.value;
      sortSel.innerHTML = '';

      // Built-in sort options
      (_optionsData.sort_by_builtins || []).forEach(function (b) {
        var opt = document.createElement('option');
        opt.value = b.value;
        opt.textContent = b.label;
        sortSel.appendChild(opt);
      });

      // Type-specific sortable properties
      if (typeIri && _optionsData.sortable_properties && _optionsData.sortable_properties[typeIri]) {
        var sep = document.createElement('option');
        sep.disabled = true;
        sep.textContent = '── Properties ──';
        sortSel.appendChild(sep);

        _optionsData.sortable_properties[typeIri].forEach(function (p) {
          var opt = document.createElement('option');
          opt.value = 'prop:' + p.iri;
          opt.textContent = p.label;
          sortSel.appendChild(opt);
        });
      }

      // Restore previous selection if still valid
      if (currentSort) {
        var found = Array.from(sortSel.options).some(function (o) { return o.value === currentSort; });
        if (found) sortSel.value = currentSort;
      }
    }
  }

  // --- Apply / Reset / Refresh ---

  /**
   * Read current dropdown values and fetch config-tree into explorer body.
   */
  function applyExplorerConfig() {
    // If hierarchy is active, delegate to that handler
    if (_hierarchyActive) {
      _applyHierarchy();
      return;
    }

    var body = _treeBody();
    if (!body) return;

    var typeFilter = (_typeSelect() || {}).value || '';
    var groupBy = (_groupSelect() || {}).value || '';
    var sortBy = (_sortSelect() || {}).value || 'label';
    var sortOrderBtn = _sortOrderBtn();
    var sortOrder = sortOrderBtn ? (sortOrderBtn.dataset.order || 'asc') : 'asc';

    var params = [];
    if (typeFilter) params.push('type_filter=' + encodeURIComponent(typeFilter));
    if (groupBy) params.push('group_by=' + encodeURIComponent(groupBy));
    params.push('sort_by=' + encodeURIComponent(sortBy));
    params.push('sort_order=' + encodeURIComponent(sortOrder));

    var url = '/browser/explorer/config-tree?' + params.join('&');

    // Track whether we have a non-default config
    _configActive = !!(typeFilter || groupBy || sortBy !== 'label' || sortOrder !== 'asc');

    // Collapse panel, show summary if config is active
    var panel = _panel();
    if (panel) panel.classList.remove('open');

    _updateSummary(typeFilter, groupBy, sortBy, sortOrder);

    htmx.ajax('GET', url, { target: body, swap: 'innerHTML' }).then(function () {
      if (typeof lucide !== 'undefined') lucide.createIcons();
    });
  }

  /**
   * Build summary text from current config values.
   * Overridden by config name when a saved config is active.
   */
  function _updateSummary(typeFilter, groupBy, sortBy, sortOrder) {
    var summary = _summary();
    var summaryText = _summaryText();
    if (!summary || !summaryText) return;

    // If a named config is selected, show its name instead
    var dd = _configDropdown();
    if (dd && dd.value) {
      var selectedOpt = dd.options[dd.selectedIndex];
      if (selectedOpt && selectedOpt.textContent) {
        _updateSummaryWithName(selectedOpt.textContent);
        return;
      }
    }

    if (!_configActive) {
      summary.classList.remove('visible');
      return;
    }

    var parts = [];

    // Type label
    var typeSel = _typeSelect();
    if (typeFilter && typeSel) {
      var opt = typeSel.options[typeSel.selectedIndex];
      parts.push(opt ? opt.textContent : 'Filtered');
    }

    // Group label
    var groupSel = _groupSelect();
    if (groupBy && groupSel) {
      var groupOpt = groupSel.options[groupSel.selectedIndex];
      parts.push('→ ' + (groupOpt ? groupOpt.textContent : groupBy));
    }

    // Sort label
    var sortSel = _sortSelect();
    if (sortSel) {
      var sortOpt = sortSel.options[sortSel.selectedIndex];
      var arrow = sortOrder === 'asc' ? '↑' : '↓';
      parts.push('→ ' + (sortOpt ? sortOpt.textContent : sortBy) + ' ' + arrow);
    }

    summaryText.textContent = parts.join(' ');
    summary.classList.add('visible');
  }

  /**
   * Reset all config controls to defaults and reload the default tree.
   */
  function resetExplorerConfig() {
    var typeSel = _typeSelect();
    var groupSel = _groupSelect();
    var sortSel = _sortSelect();
    var sortOrderBtn = _sortOrderBtn();

    if (typeSel) typeSel.value = '';
    if (groupSel) {
      // Reset to built-in options only (remove type-specific)
      _updatePropertyDropdowns('');
      groupSel.value = '';
    }
    if (sortSel) {
      _updatePropertyDropdowns('');
      sortSel.value = 'label';
    }
    if (sortOrderBtn) {
      sortOrderBtn.dataset.order = 'asc';
      sortOrderBtn.innerHTML = '&#9650;';
    }

    _configActive = false;
    _hierarchyActive = false;

    // Reset config selector
    var dd = _configDropdown();
    if (dd) dd.value = '';
    _updateDeleteButton();
    localStorage.removeItem(_LS_KEY);

    // Show builder panel again (may have been hidden by Hierarchy)
    var panel = _panel();
    if (panel) panel.style.display = '';

    // Hide summary
    var summary = _summary();
    if (summary) summary.classList.remove('visible');

    // Close panel
    if (panel) panel.classList.remove('open');

    // Reload default tree via standard refreshNavTree
    if (typeof window.SemPKM.refreshNavTree === 'function') {
      window.SemPKM.refreshNavTree();
    }
  }

  /**
   * Re-apply the current config (used after object CRUD operations).
   * If no config is active, delegates to refreshNavTree.
   */
  function refreshExplorerTree() {
    if (_configActive) {
      applyExplorerConfig();
    } else if (typeof window.SemPKM.refreshNavTree === 'function') {
      window.SemPKM.refreshNavTree();
    }
  }

  /**
   * Toggle the config panel open/closed.
   * Initializes options on first open.
   */
  function toggleExplorerConfig() {
    var panel = _panel();
    if (!panel) return;

    // Don't open builder panel when Hierarchy is active
    if (_hierarchyActive) {
      // Toggle selector visibility instead
      var selector = _el('explorer-config-selector');
      if (selector) {
        selector.classList.toggle('collapsed');
      }
      return;
    }

    if (panel.classList.contains('open')) {
      panel.classList.remove('open');
      // Show summary if config is active
      if (_configActive) {
        var summary = _summary();
        if (summary) summary.classList.add('visible');
      }
    } else {
      panel.classList.add('open');
      // Hide summary while panel is open
      var summary = _summary();
      if (summary) summary.classList.remove('visible');
      // Load options on first open
      initExplorerConfig();
    }
  }

  // --- Exports ---
  window.SemPKM.initExplorerConfig = initExplorerConfig;
  window.SemPKM.applyExplorerConfig = applyExplorerConfig;
  window.SemPKM.resetExplorerConfig = resetExplorerConfig;
  window.SemPKM.refreshExplorerTree = refreshExplorerTree;
  window.SemPKM.toggleExplorerConfig = toggleExplorerConfig;
  window.SemPKM.loadConfigList = loadConfigList;
  window.SemPKM.saveCurrentConfig = saveCurrentConfig;
  window.SemPKM.deleteSelectedConfig = deleteSelectedConfig;
  window.SemPKM.onConfigSelectorChange = onConfigSelectorChange;

})();
