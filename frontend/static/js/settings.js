(function () {
  'use strict';

  var _cache = null;  // resolved settings dict from server

  function fetchSettings() {
    return fetch('/browser/settings/data', { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        _cache = data;
        return data;
      });
  }

  function get(key) {
    return _cache ? _cache[key] : null;
  }

  function set(key, value) {
    if (_cache) _cache[key] = value;
    document.dispatchEvent(new CustomEvent('sempkm:setting-changed', {
      detail: { key: key, value: value }
    }));
    return fetch('/browser/settings/' + encodeURIComponent(key), {
      method: 'PUT',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: value })
    });
  }

  function reset(key) {
    return fetch('/browser/settings/' + encodeURIComponent(key), {
      method: 'DELETE',
      credentials: 'include'
    }).then(function (r) { return r.json(); })
      .then(function (data) {
        if (_cache) _cache[key] = data.default_value;
        document.dispatchEvent(new CustomEvent('sempkm:setting-changed', {
          detail: { key: key, value: data.default_value }
        }));
        return data;
      });
  }

  window.SemPKMSettings = { get: get, set: set, reset: reset, fetch: fetchSettings };

  // Auto-fetch on DOM ready so cache is warm
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fetchSettings);
  } else {
    fetchSettings();
  }
})();
