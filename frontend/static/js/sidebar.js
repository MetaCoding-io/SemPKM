/**
 * SemPKM Sidebar - collapse/expand toggle, grouped section headers, localStorage persistence.
 */

(function() {
  var SIDEBAR_KEY = 'sempkm_sidebar_collapsed';
  var SECTION_KEY = 'sempkm_sidebar_sections';

  /** Toggle sidebar collapse state */
  window.toggleSidebar = function() {
    var layout = document.querySelector('.dashboard-layout, .workspace-layout');
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
    var layout = document.querySelector('.dashboard-layout, .workspace-layout');
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

  /** Generate initials from user name */
  function _getInitials(name) {
    if (!name) return '?';
    var parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return parts[0][0].toUpperCase();
  }

  /** Deterministic color from name */
  function _getAvatarColor(name) {
    var colors = ['#4A90D9', '#E67E22', '#27AE60', '#8E44AD', '#E74C3C', '#16A085', '#F39C12', '#2C3E50'];
    if (!name) return colors[0];
    var hash = 0;
    for (var i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    return colors[Math.abs(hash) % colors.length];
  }

  /** Initialize user avatars */
  function _initUserAvatars() {
    var avatarEl = document.getElementById('user-avatar');
    var avatarPopoverEl = document.getElementById('user-avatar-popover');
    if (!avatarEl) return;

    // Read name from the adjacent .user-name element
    var nameEl = avatarEl.parentElement && avatarEl.parentElement.querySelector('.user-name');
    var name = nameEl ? nameEl.textContent.trim() : 'User';

    var initials = _getInitials(name);
    var color = _getAvatarColor(name);

    // Set both avatars (sidebar + popover header)
    [avatarEl, avatarPopoverEl].forEach(function(el) {
      if (!el) return;
      el.textContent = initials;
      el.style.backgroundColor = color;
    });
  }

  /** Re-initialize Lucide icons when popover is shown */
  function _initPopoverIcons() {
    var popover = document.getElementById('user-popover');
    if (!popover) return;
    popover.addEventListener('toggle', function(e) {
      if (e.newState === 'open' && typeof lucide !== 'undefined') {
        lucide.createIcons({ root: popover });
      }
    });
  }

  // Expose avatar helpers for potential reuse
  window.getAvatarColor = _getAvatarColor;
  window.getInitials = _getInitials;

  /** Initialize on DOM ready */
  function init() {
    _restoreSidebarState();
    _restoreSectionStates();
    _initLucideIcons();
    _initUserAvatars();
    _initPopoverIcons();

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
