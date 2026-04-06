/**
 * explorer-config.js — Composable explorer configuration module.
 *
 * Manages the filter/group/sort config builder panel in the OBJECTS explorer
 * section. Fetches available options from /browser/explorer/config-options,
 * populates dropdowns, and triggers config-tree renders via htmx.
 *
 * Exports to window.SemPKM:
 *   - initExplorerConfig()   — fetch options and populate dropdowns
 *   - applyExplorerConfig()  — apply current config, render tree
 *   - resetExplorerConfig()  — clear config, restore default tree
 *   - refreshExplorerTree()  — re-apply current config (after CRUD)
 */
(function () {
  'use strict';

  window.SemPKM = window.SemPKM || {};

  // --- Module state ---
  var _optionsLoaded = false;
  var _optionsData = null; // cached response from config-options
  var _configActive = false; // whether a non-default config is applied

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

    // Hide the old mode-select dropdown when config is active
    var modeSelect = _el('explorer-mode-select');
    if (modeSelect) modeSelect.style.display = _configActive ? 'none' : '';

    htmx.ajax('GET', url, { target: body, swap: 'innerHTML' }).then(function () {
      if (typeof lucide !== 'undefined') lucide.createIcons();
    });
  }

  /**
   * Build summary text from current config values.
   */
  function _updateSummary(typeFilter, groupBy, sortBy, sortOrder) {
    var summary = _summary();
    var summaryText = _summaryText();
    if (!summary || !summaryText) return;

    if (!_configActive) {
      summary.classList.remove('visible');
      return;
    }

    var parts = [];

    // Type label
    var typeSel = _typeSelect();
    if (typeFilter && typeSel) {
      var selectedOpt = typeSel.options[typeSel.selectedIndex];
      parts.push(selectedOpt ? selectedOpt.textContent : 'Filtered');
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

    // Hide summary
    var summary = _summary();
    if (summary) summary.classList.remove('visible');

    // Close panel
    var panel = _panel();
    if (panel) panel.classList.remove('open');

    // Restore mode-select visibility
    var modeSelect = _el('explorer-mode-select');
    if (modeSelect) modeSelect.style.display = '';

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

    if (panel.classList.contains('open')) {
      panel.classList.remove('open');
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

})();
