/**
 * Backward-compatibility shims for inline onclick handlers in templates.
 *
 * The M044/S03 migration moved all workspace functions from global scope to
 * window.SemPKM.*.  HTML templates still reference bare function names
 * (e.g. onclick="handleTreeLeafClick(...)").  This script bridges the gap by
 * copying every function from SemPKM back to window — only if the name isn't
 * already occupied (avoids clobbering auth.js globals, native APIs, etc.).
 *
 * This file loads immediately after workspace.js in base.html.
 */
(function () {
  var ns = window.SemPKM;
  if (!ns) return;
  var keys = Object.keys(ns);
  for (var i = 0; i < keys.length; i++) {
    var k = keys[i];
    if (typeof ns[k] === 'function' && typeof window[k] === 'undefined') {
      window[k] = ns[k];
    }
  }
})();
