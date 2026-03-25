---
estimated_steps: 24
estimated_files: 3
skills_used: []
---

# T02: Fix calendar, canvas, and federation event/timer leaks

Three files have event/timer leaks that need fixing. Each file uses the `registerCleanup()` infrastructure (now with `runCleanup()` exported from T01) to clean up when panels are destroyed.

## calendar.js (frontend/static/js/calendar.js)

**Problem:** `_initCalendar()` adds two anonymous document-level event listeners (`sempkm:command-executed`, `sempkm:scope-changed`) every time a calendar panel is opened. The FullCalendar instance is stored on `window._sempkmCalendar` but never `.destroy()`'d.

**Fix:**
1. Refactor the two anonymous document event handlers into named functions stored in module-scope variables (e.g., `_commandHandler`, `_scopeHandler`). Before adding them, remove any previous handler: `document.removeEventListener('sempkm:command-executed', _commandHandler)` then add the new one.
2. Register cleanup via `window.registerCleanup(containerId, cleanupFn)` where cleanupFn:
   - Calls `cal.destroy()` on the FullCalendar instance
   - Removes both document listeners using the named function references
   - Nulls `window._sempkmCalendar`
3. At the start of `_initCalendar()`, if `window._sempkmCalendar` exists, destroy it first (handles reinit without panel close).

## canvas.js (frontend/static/js/canvas.js)

**Problem:** `bindEvents()` (line ~228) adds 7 listeners to window/document (pointermove, pointerup, dragover, dragleave, drop, dragend, keydown) without ever removing them. The `htmx:afterSwap` handler at line ~1781 resets `state.mounted = false` and calls `mountCanvas()` → `bindEvents()`, stacking duplicate listeners.

**Fix:**
1. Add an `unbindEvents()` function that removes all 7 listeners using the same named handler references already defined in the IIFE (`onPointerMove`, `onPointerUp`, `onDragOver`, `onDragLeave`, `onDrop`, `onDragEnd`, `onKeyDown` — verify exact names by reading the file).
2. Call `unbindEvents()` at the start of `bindEvents()` to prevent stacking.
3. Call `unbindEvents()` + cleanup in a `registerCleanup` call. The canvas root element is `document.getElementById('spatial-canvas-root')` — register cleanup on that ID.
4. In the `htmx:afterSwap` handler (line ~1781), call `unbindEvents()` before setting `state.mounted = false`.

**Important:** The viewport/layer element-scoped listeners (wheel, pointerdown, click) GC with the DOM elements and don't need explicit removal.

## federation.js (frontend/static/js/federation.js)

**Problem:** `setInterval(updateInboxBadge, 60000)` (line ~61) runs forever with no cleanup.

**Fix:**
1. Store the interval handle: `var _badgeInterval = setInterval(updateInboxBadge, 60000);`
2. Add a `beforeunload` listener: `window.addEventListener('beforeunload', function() { clearInterval(_badgeInterval); });`

This is a workspace-lifetime interval (not per-panel), so `registerCleanup` isn't needed — `beforeunload` is the right hook.

## Inputs

- `frontend/static/js/calendar.js`
- `frontend/static/js/canvas.js`
- `frontend/static/js/federation.js`
- `frontend/static/js/cleanup.js`

## Expected Output

- `frontend/static/js/calendar.js`
- `frontend/static/js/canvas.js`
- `frontend/static/js/federation.js`

## Verification

1. **calendar.js listener cleanup:**
   - `rg 'removeEventListener' frontend/static/js/calendar.js` — at least 2 matches (command-executed + scope-changed)
   - `rg 'registerCleanup' frontend/static/js/calendar.js` — at least 1 match
   - `rg '\\.destroy\\(\\)' frontend/static/js/calendar.js` — at least 1 match (FullCalendar destroy)
   
2. **canvas.js unbind pattern:**
   - `rg 'unbindEvents' frontend/static/js/canvas.js` — at least 2 matches (definition + call)
   - `rg 'registerCleanup' frontend/static/js/canvas.js` — at least 1 match
   - `rg 'removeEventListener' frontend/static/js/canvas.js` — at least 5 matches (7 listeners minus element-scoped ones)

3. **federation.js interval cleanup:**
   - `rg 'clearInterval' frontend/static/js/federation.js` — at least 1 match
   - `rg 'beforeunload' frontend/static/js/federation.js` — at least 1 match

4. **No syntax errors:**
   - `node --check frontend/static/js/calendar.js` — exits 0
   - `node --check frontend/static/js/canvas.js` — exits 0
   - `node --check frontend/static/js/federation.js` — exits 0
