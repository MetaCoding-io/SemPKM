/**
 * SemPKM Theme Toggle
 *
 * Manages tri-state theme switching (Light / System / Dark),
 * localStorage persistence, third-party library integration,
 * and the no-transition class removal after initial paint.
 */
(function () {
  'use strict';

  var THEME_KEY = 'sempkm_theme';

  function getStoredPreference() {
    return localStorage.getItem(THEME_KEY) || 'system';
  }

  function resolveTheme(preference) {
    if (preference === 'dark') return 'dark';
    if (preference === 'light') return 'light';
    // System: check OS preference once at load
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(resolved) {
    document.documentElement.setAttribute('data-theme', resolved);

    // Toggle ninja-keys dark class
    var ninja = document.querySelector('ninja-keys');
    if (ninja) {
      if (resolved === 'dark') {
        ninja.classList.add('dark');
      } else {
        ninja.classList.remove('dark');
      }
    }

    // Switch highlight.js theme
    var hljsLink = document.getElementById('hljs-theme');
    if (hljsLink) {
      var base = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/';
      hljsLink.href = base + (resolved === 'dark' ? 'github-dark.min.css' : 'github.min.css');
    }

    // Update toggle UI active state
    var pref = getStoredPreference();
    document.querySelectorAll('.theme-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.themeValue === pref);
    });

    // Remove no-transition class after first paint
    requestAnimationFrame(function () {
      document.documentElement.classList.remove('no-transition');
    });

    // Dispatch event for any other listeners (CodeMirror, Cytoscape, etc.)
    document.dispatchEvent(new CustomEvent('sempkm:theme-changed', {
      detail: { theme: resolved, preference: pref }
    }));
  }

  window.setTheme = function (preference) {
    localStorage.setItem(THEME_KEY, preference);
    applyTheme(resolveTheme(preference));
  };

  // On load: wire up third-party libs and active states.
  // The anti-FOUC inline script in <head> already set data-theme visually.
  var pref = getStoredPreference();
  applyTheme(resolveTheme(pref));

  // Re-apply active states when user popover opens (Lucide icons reinitialize)
  document.addEventListener('toggle', function (e) {
    if (e.target && e.target.id === 'user-popover') {
      var currentPref = getStoredPreference();
      document.querySelectorAll('.theme-btn').forEach(function (btn) {
        btn.classList.toggle('active', btn.dataset.themeValue === currentPref);
      });
      // Re-create Lucide icons inside popover
      if (typeof lucide !== 'undefined' && typeof lucide.createIcons === 'function') {
        lucide.createIcons();
      }
    }
  }, true);
})();
