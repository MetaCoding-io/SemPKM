/**
 * SemPKM Named Layouts Manager
 *
 * Manages named workspace layouts in localStorage.
 * Exposes API on window.SemPKMLayouts for save/restore/delete/list.
 *
 * localStorage keys:
 *   sempkm_layouts         - { "Name": { layout: <dockview JSON>, savedAt: <ISO> } }
 *   sempkm_layout_current  - raw JSON.stringify(dv.toJSON()) for auto-save
 */

(function () {
  'use strict';

  var LAYOUTS_KEY = 'sempkm_layouts';
  var CURRENT_KEY = 'sempkm_layout_current';

  // -----------------------------------------------------------------------
  // Internal helpers
  // -----------------------------------------------------------------------

  function _readLayouts() {
    try {
      return JSON.parse(localStorage.getItem(LAYOUTS_KEY)) || {};
    } catch (e) {
      return {};
    }
  }

  function _writeLayouts(obj) {
    localStorage.setItem(LAYOUTS_KEY, JSON.stringify(obj));
  }

  function _escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // -----------------------------------------------------------------------
  // Public API
  // -----------------------------------------------------------------------

  /**
   * Save the current dockview layout under a name.
   * Silently overwrites if name already exists.
   * @param {string} name - Layout name
   * @returns {boolean} true on success
   */
  function save(name) {
    var dv = window._dockview;
    if (!dv) return false;
    try {
      var layouts = _readLayouts();
      layouts[name] = {
        layout: dv.toJSON(),
        savedAt: new Date().toISOString()
      };
      _writeLayouts(layouts);
      return true;
    } catch (e) {
      console.warn('SemPKMLayouts.save failed:', e);
      return false;
    }
  }

  /**
   * Restore a named layout into dockview.
   * @param {string} name - Layout name to restore
   * @returns {{ success: boolean, skipped: string[] }}
   */
  function restore(name) {
    var dv = window._dockview;
    if (!dv) return { success: false, skipped: [] };

    var layouts = _readLayouts();
    var entry = layouts[name];
    if (!entry || !entry.layout) return { success: false, skipped: [] };

    var savedPanelIds = [];
    try {
      var panels = entry.layout.panels;
      if (panels) {
        savedPanelIds = Object.keys(panels);
      }
    } catch (e) {}

    try {
      dv.fromJSON(entry.layout);
      return { success: true, skipped: [] };
    } catch (err) {
      console.warn('SemPKMLayouts.restore failed:', err);
      // Build skipped list by comparing saved panels vs current
      var currentIds = {};
      try {
        dv.panels.forEach(function (p) { currentIds[p.id] = true; });
      } catch (e) {}
      var skipped = savedPanelIds.filter(function (id) { return !currentIds[id]; });
      return { success: false, skipped: skipped };
    }
  }

  /**
   * Delete a named layout.
   * @param {string} name - Layout name to remove
   * @returns {boolean} true if existed and was deleted
   */
  function remove(name) {
    var layouts = _readLayouts();
    if (!layouts.hasOwnProperty(name)) return false;
    delete layouts[name];
    _writeLayouts(layouts);
    return true;
  }

  /**
   * List all saved layouts, sorted by savedAt descending (most recent first).
   * @returns {Array<{ name: string, savedAt: string }>}
   */
  function list() {
    var layouts = _readLayouts();
    var result = [];
    for (var name in layouts) {
      if (layouts.hasOwnProperty(name)) {
        result.push({
          name: name,
          savedAt: layouts[name].savedAt || ''
        });
      }
    }
    result.sort(function (a, b) {
      return (b.savedAt || '').localeCompare(a.savedAt || '');
    });
    return result;
  }

  /**
   * Auto-save current dockview layout to localStorage.
   * Called by workspace-layout.js onDidLayoutChange.
   */
  function autoSave() {
    var dv = window._dockview;
    if (!dv) return;
    try {
      localStorage.setItem(CURRENT_KEY, JSON.stringify(dv.toJSON()));
    } catch (e) {}
  }

  /**
   * Read the auto-saved current layout from localStorage.
   * @returns {object|null} Parsed dockview layout JSON, or null
   */
  function restoreCurrent() {
    try {
      var raw = localStorage.getItem(CURRENT_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  // -----------------------------------------------------------------------
  // Window export
  // -----------------------------------------------------------------------

  window.SemPKMLayouts = {
    save: save,
    restore: restore,
    remove: remove,
    list: list,
    autoSave: autoSave,
    restoreCurrent: restoreCurrent,
    _escapeHtml: _escapeHtml
  };

})();
