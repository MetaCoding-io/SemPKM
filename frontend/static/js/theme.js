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

    // Switch CodeMirror editors via Compartment reconfigure
    if (typeof window.switchEditorThemes === 'function') {
      window.switchEditorThemes(resolved === 'dark');
    }

    // Switch Cytoscape graph styles
    if (typeof window.switchGraphTheme === 'function') {
      window.switchGraphTheme(resolved === 'dark');
    }

    // Dispatch event for any other listeners
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

  // Settings system integration: react to sempkm:setting-changed for core.theme
  document.addEventListener('sempkm:setting-changed', function (e) {
    if (e.detail && e.detail.key === 'core.theme') {
      var newTheme = e.detail.value;
      if (typeof window.setTheme === 'function') {
        window.setTheme(newTheme);
      }
      // Write-through: keep localStorage in sync so anti-FOUC fast-path is accurate
      try { localStorage.setItem('sempkm_theme', newTheme); } catch (_) {}
    }
  });

  // On DOMContentLoaded, sync theme from server settings if different from localStorage fast-path
  document.addEventListener('DOMContentLoaded', function () {
    // Small delay to let settings.js auto-fetch complete
    setTimeout(function () {
      var serverTheme = window.SemPKMSettings ? window.SemPKMSettings.get('core.theme') : null;
      if (serverTheme) {
        var localTheme;
        try { localTheme = localStorage.getItem('sempkm_theme'); } catch (_) { localTheme = null; }
        if (serverTheme !== localTheme && typeof window.setTheme === 'function') {
          window.setTheme(serverTheme);
          try { localStorage.setItem('sempkm_theme', serverTheme); } catch (_) {}
        }
      }
    }, 300);
  });
})();
