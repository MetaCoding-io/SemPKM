---
id: S02
parent: M044
milestone: M044
provides:
  - Cleaned-up event listener patterns with registerCleanup() examples for dockview panels
  - dispose() on all 3 dockview content renderers fires cleanup registry
requires:
  []
affects:
  - S07
key_files:
  - frontend/static/js/cleanup.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/js/calendar.js
  - frontend/static/js/canvas.js
  - frontend/static/js/federation.js
key_decisions:
  - Removed entire onDidVisibilityChange handler from view-panel renderer since it only contained dead _cytoscapeInstances code — no live resize/fit logic to preserve
  - canvas.js element-scoped listeners (wheel, pointerdown, click on viewport/layer) left to GC with their DOM elements — only window/document-level listeners need explicit removal
  - federation.js badge interval uses beforeunload instead of registerCleanup since it is workspace-lifetime, not per-panel
patterns_established:
  - Dockview dispose() → window.runCleanup() wiring pattern for all content renderers
  - Named handler variables for document-level listeners to enable balanced add/remove
  - unbindEvents() before bindEvents() pattern to prevent listener stacking on panel remount
  - beforeunload for workspace-lifetime intervals vs registerCleanup for per-panel cleanup
observability_surfaces:
  - console.warn on cleanup errors (pre-existing in cleanup.js — no new signals added)
drill_down_paths:
  - .gsd/milestones/M044/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M044/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-25T17:13:31.762Z
blocker_discovered: false
---

# S02: Event Listener & Timer Leak Fixes

**All dockview panel types now dispose cleanly via runCleanup(); calendar, canvas, and federation event/timer leaks fixed; dead _cytoscapeInstances code removed.**

## What Happened

This slice fixed event listener and timer leaks across five frontend JS files, ensuring dockview panel open/close cycles no longer accumulate stale handlers.

**T01 — Dockview dispose wiring:** Exported `runCleanup()` from cleanup.js to `window.runCleanup` so it's callable from dockview content renderers. Added `dispose()` methods to all three content renderers in workspace-layout.js (object-editor, view-panel, special-panel). Each dispose walks the panel's element tree and fires cleanup callbacks registered via `registerCleanup()`. Removed the dead `_cytoscapeInstances` reference from the view-panel renderer — it was never populated anywhere in the codebase (graph views already use the cleanup registry).

**T02 — Calendar, canvas, federation fixes:** In calendar.js, refactored two anonymous document-level listeners (`sempkm:command-executed`, `sempkm:scope-changed`) to module-scoped named handler variables that are removed before re-adding. Added FullCalendar `.destroy()` on cleanup. Registered a `registerCleanup()` callback covering all teardown. In canvas.js, added `unbindEvents()` that removes all 7 window/document listeners (pointermove, pointerup, dragover, dragleave, drop, dragend, keydown). Called at the start of `bindEvents()` to prevent stacking, plus registered via `registerCleanup()` for panel disposal. In federation.js, stored the badge polling `setInterval` handle and added a `beforeunload` listener to clear it on page unload.

All changes are static-analysis verified — every window/document `addEventListener` has a matching `removeEventListener` path. All five files pass `node --check` syntax validation.

## Verification

Slice-level must-have checks all pass:

1. `window.runCleanup` exported from cleanup.js — confirmed via rg
2. `dispose: function` present on all 3 content renderers (plus tab dispose = 4 total) in workspace-layout.js
3. `_cytoscapeInstances` returns zero results across all frontend JS — dead code fully removed
4. calendar.js: 5 removeEventListener calls (balanced with 5 addEventListener), 2 registerCleanup calls, 2 .destroy() calls
5. canvas.js: 4 unbindEvents references (definition + 3 call sites), 2 registerCleanup calls, 8 removeEventListener calls matching all 8 window/document addEventListener calls
6. federation.js: 1 clearInterval call, 1 beforeunload listener
7. All 5 modified files pass node --check syntax validation

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

Static analysis confirms balanced add/remove for all window/document listeners. Runtime verification via browser DevTools getEventListeners() was not automated — recommended as manual UAT step.

## Follow-ups

S07 E2E regression suite will exercise panel open/close cycles to confirm no functional regressions from the cleanup wiring.

## Files Created/Modified

- `frontend/static/js/cleanup.js` — Exported runCleanup() to window.runCleanup so dockview dispose() can invoke it
- `frontend/static/js/workspace-layout.js` — Added dispose() methods to all 3 content renderers (object-editor, view-panel, special-panel) that fire runCleanup on panel element tree; removed dead _cytoscapeInstances code from view-panel onDidVisibilityChange
- `frontend/static/js/calendar.js` — Refactored anonymous document listeners to named handler variables; added FullCalendar .destroy() on cleanup; registered registerCleanup callback
- `frontend/static/js/canvas.js` — Added unbindEvents() removing all 7 window/document listeners; called before bindEvents() to prevent stacking; registered registerCleanup callback
- `frontend/static/js/federation.js` — Stored setInterval handle in _badgeInterval; added beforeunload listener to clearInterval on page unload
