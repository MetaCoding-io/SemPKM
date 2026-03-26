/**
 * apiFetch — Centralized apiFetch() wrapper for SemPKM.
 *
 * Wraps the native fetch API with consistent error handling:
 * - Network errors → toast + rethrow
 * - Non-2xx responses → toast + throw structured error (status, body)
 * - AbortError → silently suppressed (no toast, no rethrow)
 * - 401 → redirect to /login.html (unless already on an auth page)
 * - { silent: true } option → suppress all toasts
 *
 * Returns the raw Response on success (caller parses as needed).
 * Exposed globally as window.apiFetch.
 */
(function () {
  'use strict';

  window.SemPKM = window.SemPKM || {};

  var AUTH_PAGES = ['/login.html', '/setup.html', '/invite.html'];

  function _isAuthPage() {
    return AUTH_PAGES.indexOf(window.location.pathname) !== -1;
  }

  /**
   * Show a user-facing toast message.
   * Tries window.showToast (workspace.js) first, then _showGlobalToast
   * (base.html inline), then falls back to console.warn.
   */
  function _toast(message, type) {
    if (typeof window.SemPKM.showToast === 'function') {
      window.SemPKM.showToast(message, type === 'error' ? 5000 : 4000);
    } else if (typeof _showGlobalToast === 'function') {
      _showGlobalToast(message, type || 'warning');
    } else {
      console.warn('[apiFetch] toast (no UI available):', message);
    }
  }

  /**
   * @param {string|Request} resource - URL or Request object
   * @param {RequestInit & { silent?: boolean }} [options] - Standard fetch options + { silent }
   * @returns {Promise<Response>} Raw Response on success
   */
  async function apiFetch(resource, options) {
    var opts = Object.assign({}, options);
    var silent = Boolean(opts.silent);
    delete opts.silent; // don't forward non-standard key to native fetch

    var response;
    try {
      response = await fetch(resource, opts); // raw-fetch — the actual native call
    } catch (err) {
      // AbortError: caller cancelled via AbortController — swallow silently
      if (err.name === 'AbortError') {
        return; // return undefined; caller should handle this
      }
      // Network failure (DNS, offline, CORS block, etc.)
      console.error('[apiFetch] Network error:', err.message, '| url:', resource);
      if (!silent) {
        _toast('Network error — please check your connection.', 'error');
      }
      throw err;
    }

    // 401 — redirect to login (unless already on an auth page)
    if (response.status === 401 && !_isAuthPage()) {
      window.location.href = '/login.html';
      return response; // return in case redirect is slow
    }

    // Non-2xx — extract body, toast, throw structured error
    if (!response.ok) {
      var bodyText = '';
      try {
        bodyText = await response.text();
      } catch (_) {
        bodyText = '(could not read response body)';
      }

      var friendlyMsg = 'Request failed';
      if (response.status === 403) {
        friendlyMsg = 'Access denied — you don\u2019t have permission for this action.';
      } else if (response.status >= 500) {
        friendlyMsg = 'Server error (' + response.status + ') — please try again later.';
      } else {
        friendlyMsg = 'Request failed (' + response.status + ').';
      }

      console.error('[apiFetch] HTTP ' + response.status + ' |', String(resource), '|', bodyText.slice(0, 300));

      if (!silent) {
        _toast(friendlyMsg, response.status >= 500 ? 'error' : 'warning');
      }

      var err = new Error(friendlyMsg);
      err.status = response.status;
      err.body = bodyText;
      err.response = response;
      throw err;
    }

    return response;
  }

  window.SemPKM.apiFetch = apiFetch;
  // Backward-compat shim — 19 files still reference bare apiFetch
  window.apiFetch = apiFetch;

  /**
   * Debug logging gated by localStorage flag.
   * Enable:  localStorage.setItem('sempkm_debug', '1')
   * Disable: localStorage.removeItem('sempkm_debug')
   *
   * @param {string} tag - Component tag (e.g. 'copilot', 'calendar')
   * @param {...*} args - Values forwarded to console.log
   */
  window.SemPKM.debug = function debug(tag, ...args) {
    try {
      if (localStorage.getItem('sempkm_debug')) {
        console.log('[' + tag + ']', ...args);
      }
    } catch (_) {
      // localStorage unavailable (private browsing, iframe sandbox) — silently skip
    }
  };

})();
