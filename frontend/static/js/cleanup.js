/**
 * SemPKM Cleanup Registry
 *
 * Centralized registry mapping DOM element IDs to teardown functions.
 * htmx:beforeCleanupElement fires before htmx removes/replaces DOM
 * elements, giving us a chance to call .destroy() on library instances.
 *
 * Usage:
 *   window.registerCleanup('element-id', function() { instance.destroy(); });
 */
(function() {
  'use strict';

  // Registry: elementId -> [cleanupFn, cleanupFn, ...]
  window.SemPKM._sempkmCleanup = {};

  function registerCleanup(elementId, cleanupFn) {
    if (!window.SemPKM._sempkmCleanup[elementId]) {
      window.SemPKM._sempkmCleanup[elementId] = [];
    }
    window.SemPKM._sempkmCleanup[elementId].push(cleanupFn);
  }

  function runCleanup(elementId) {
    var fns = window.SemPKM._sempkmCleanup[elementId];
    if (fns) {
      fns.forEach(function(fn) {
        try { fn(); } catch (e) {
          console.warn('Cleanup error for', elementId, ':', e);
        }
      });
      delete window.SemPKM._sempkmCleanup[elementId];
    }
  }

  // htmx fires beforeCleanupElement on the root element being replaced.
  // We must also check descendants since nested elements may have registered cleanup.
  document.addEventListener('htmx:beforeCleanupElement', function(evt) {
    var el = evt.detail.elt;
    if (!el) return;

    // Clean up the root element itself
    if (el.id) {
      runCleanup(el.id);
    }

    // Clean up all descendants with registered IDs
    if (el.querySelectorAll) {
      var descendants = el.querySelectorAll('[id]');
      descendants.forEach(function(child) {
        runCleanup(child.id);
      });
    }
  });

  window.SemPKM.registerCleanup = registerCleanup;
  window.SemPKM.runCleanup = runCleanup;

  // ── backward-compat shims (remove in T03) ──
  window._sempkmCleanup = window.SemPKM._sempkmCleanup;
  window.registerCleanup = window.SemPKM.registerCleanup;
  window.runCleanup = window.SemPKM.runCleanup;
})();
