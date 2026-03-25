---
id: T02
parent: S02
milestone: M044
key_files:
  - frontend/static/js/calendar.js
  - frontend/static/js/canvas.js
  - frontend/static/js/federation.js
key_decisions:
  - canvas.js: Element-scoped listeners (wheel, pointerdown, click on viewport/layer) are left to GC with their DOM elements — only window/document-level listeners need explicit removal
  - federation.js: Used beforeunload instead of registerCleanup since the badge interval is workspace-lifetime, not per-panel
duration: ""
verification_result: passed
completed_at: 2026-03-25T17:10:07.289Z
blocker_discovered: false
---

# T02: Fix calendar, canvas, and federation event/timer leaks with named handlers, unbindEvents, registerCleanup, and beforeunload

**Fix calendar, canvas, and federation event/timer leaks with named handlers, unbindEvents, registerCleanup, and beforeunload**

## What Happened

Fixed event listener and timer leaks in three files:

**calendar.js:** The two anonymous document-level listeners (`sempkm:command-executed` and `sempkm:scope-changed`) were added every time a calendar panel opened, stacking duplicates. Refactored both into module-scoped named variables (`_commandHandler`, `_scopeHandler`) that are removed before re-adding. Added cleanup at the start of `_initCalendar()` to destroy any existing FullCalendar instance and remove stale listeners. Registered a cleanup function via `window.registerCleanup(containerId, fn)` that destroys the FullCalendar instance, removes both document listeners, and nulls the global reference.

**canvas.js:** The `bindEvents()` function added 7 window/document listeners (pointermove, pointerup, dragover, dragleave, drop, dragend, keydown) without ever removing them. The `htmx:afterSwap` handler called `mountCanvas()` → `bindEvents()` on reswap, stacking duplicates. Added `unbindEvents()` that removes all 7 using the same named handler references already defined in the IIFE. Called `unbindEvents()` at the start of `bindEvents()` to prevent stacking, at the end of `mountCanvas()` via `registerCleanup('spatial-canvas-root', fn)` for panel disposal, and in the `htmx:afterSwap` handler before resetting `state.mounted`.

**federation.js:** The `setInterval(updateInboxBadge, 60000)` ran forever with no cleanup. Stored the interval handle in `_badgeInterval` and added a `beforeunload` listener to clear it on page unload. This is a workspace-lifetime interval (not per-panel), so `registerCleanup` isn't needed — `beforeunload` is the correct hook.

## Verification

All 11 verification checks pass:

1. calendar.js removeEventListener: 5 matches (≥2 required) ✅
2. calendar.js registerCleanup: 2 matches (≥1 required) ✅
3. calendar.js .destroy(): 2 matches (≥1 required) ✅
4. canvas.js unbindEvents: 4 matches (≥2 required) ✅
5. canvas.js registerCleanup: 2 matches (≥1 required) ✅
6. canvas.js removeEventListener: 8 matches (≥5 required) ✅
7. federation.js clearInterval: 1 match (≥1 required) ✅
8. federation.js beforeunload: 1 match (≥1 required) ✅
9. node --check calendar.js: exit 0 ✅
10. node --check canvas.js: exit 0 ✅
11. node --check federation.js: exit 0 ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg -c 'removeEventListener' frontend/static/js/calendar.js` | 0 | ✅ pass | 50ms |
| 2 | `rg -c 'registerCleanup' frontend/static/js/calendar.js` | 0 | ✅ pass | 50ms |
| 3 | `rg -c '\.destroy\(\)' frontend/static/js/calendar.js` | 0 | ✅ pass | 50ms |
| 4 | `rg -c 'unbindEvents' frontend/static/js/canvas.js` | 0 | ✅ pass | 50ms |
| 5 | `rg -c 'registerCleanup' frontend/static/js/canvas.js` | 0 | ✅ pass | 50ms |
| 6 | `rg -c 'removeEventListener' frontend/static/js/canvas.js` | 0 | ✅ pass | 50ms |
| 7 | `rg -c 'clearInterval' frontend/static/js/federation.js` | 0 | ✅ pass | 50ms |
| 8 | `rg -c 'beforeunload' frontend/static/js/federation.js` | 0 | ✅ pass | 50ms |
| 9 | `node --check frontend/static/js/calendar.js` | 0 | ✅ pass | 4400ms |
| 10 | `node --check frontend/static/js/canvas.js` | 0 | ✅ pass | 4400ms |
| 11 | `node --check frontend/static/js/federation.js` | 0 | ✅ pass | 4400ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/calendar.js`
- `frontend/static/js/canvas.js`
- `frontend/static/js/federation.js`
