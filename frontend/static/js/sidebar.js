/**
 * SemPKM Sidebar - collapse/expand toggle, grouped section headers, localStorage persistence.
 */

(function() {
  var SIDEBAR_KEY = 'sempkm_sidebar_collapsed';
  var SECTION_KEY = 'sempkm_sidebar_sections';

  /** Toggle sidebar collapse state */
  window.toggleSidebar = function() {
    var layout = document.querySelector('.dashboard-layout');
    if (!layout) return;
    var isCollapsed = layout.classList.toggle('sidebar-collapsed');
    localStorage.setItem(SIDEBAR_KEY, isCollapsed ? 'true' : 'false');

    // After transition, dispatch resize so Split.js recalculates
    // (Research Pitfall 3: Split.js may need recalc after container width change)
    setTimeout(function() {
      window.dispatchEvent(new Event('resize'));
    }, 250); // Match CSS transition duration
  };

  /** Toggle a sidebar group's collapsed state */
  window.toggleSidebarGroup = function(headerEl) {
    var group = headerEl.closest('.sidebar-group');
    if (!group) return;
    group.classList.toggle('collapsed');
    _saveSectionStates();
  };

  /** Save section collapse states to localStorage */
  function _saveSectionStates() {
    var states = {};
    document.querySelectorAll('.sidebar-group').forEach(function(g) {
      var key = g.getAttribute('data-group');
      if (key) states[key] = g.classList.contains('collapsed');
    });
    localStorage.setItem(SECTION_KEY, JSON.stringify(states));
  }

  /** Restore section collapse states from localStorage */
  function _restoreSectionStates() {
    var raw = localStorage.getItem(SECTION_KEY);
    if (!raw) return;
    try {
      var states = JSON.parse(raw);
      Object.keys(states).forEach(function(key) {
        var group = document.querySelector('.sidebar-group[data-group="' + key + '"]');
        if (group && states[key]) group.classList.add('collapsed');
      });
    } catch (e) { /* ignore parse errors */ }
  }

  /** Restore sidebar collapse state from localStorage */
  function _restoreSidebarState() {
    var layout = document.querySelector('.dashboard-layout');
    if (!layout) return;
    if (localStorage.getItem(SIDEBAR_KEY) === 'true') {
      layout.classList.add('sidebar-collapsed');
    }
  }

  /** Initialize Lucide icons */
  function _initLucideIcons() {
    if (typeof lucide !== 'undefined' && lucide.createIcons) {
      lucide.createIcons();
    }
  }

  /** Initialize on DOM ready */
  function init() {
    _restoreSidebarState();
    _restoreSectionStates();
    _initLucideIcons();

    // Also init Lucide icons after htmx swaps (for future phases using icons in dynamic content)
    document.addEventListener('htmx:afterSwap', function(e) {
      if (e.detail && e.detail.target && typeof lucide !== 'undefined') {
        lucide.createIcons({ root: e.detail.target });
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
