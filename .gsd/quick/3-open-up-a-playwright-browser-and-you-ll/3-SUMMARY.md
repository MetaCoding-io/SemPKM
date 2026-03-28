# Quick Task: open up a playwright browser and you'll see you cannot click on anything. check js console

**Date:** 2026-03-28
**Branch:** gsd/quick/3-open-up-a-playwright-browser-and-you-ll

## What Changed
- **Root cause:** The M044/S03 namespace migration moved all workspace functions from `window.fnName` to `window.SemPKM.fnName`. Phase 3 removed the backward-compat shims, but ~50 HTML templates still use bare function names in inline `onclick` handlers. Every click threw `ReferenceError: X is not defined`.
- **Fix:** Added `sempkm-shims.js` — iterates all functions on `window.SemPKM` and copies them to `window[name]` (skipping names already defined). Loaded as the last `<script>` in `base.html`.
- **Dead code cleanup:** Removed `_vfs_types.html` and `_vfs_objects.html` — orphaned partials not referenced by any route, template include, or JS file.

## Files Modified
- `frontend/static/js/sempkm-shims.js` — new file, backward-compat shim generator
- `backend/app/templates/base.html` — added `<script>` tag for shims after all other JS
- `backend/app/templates/browser/_vfs_types.html` — deleted (dead code)
- `backend/app/templates/browser/_vfs_objects.html` — deleted (dead code)

## Verification
- Confirmed 50 functions were missing from global scope before fix
- After fix: all tested functions restored to global scope
- Clicked tree nodes, opened objects, toggled sidebar — all work without console errors
- Scanned all `_*.html` partials in browser templates — only these two were orphaned
