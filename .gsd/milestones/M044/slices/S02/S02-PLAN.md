# S02: Event Listener & Timer Leak Fixes

**Goal:** Opening and closing dockview panels (graph, calendar, canvas, SPARQL console) no longer leaks event listeners or library instances; federation badge polling clears on page unload.
**Demo:** After this: opening and closing dockview panels (graph, kanban, SPARQL console) no longer leaks event listeners; federation panel can be reopened without duplicate polling intervals

## Must-Haves

- `runCleanup()` exported from cleanup.js and callable from dockview dispose()
- All 3 content renderers (object-editor, view-panel, special-panel) have dispose() methods that fire cleanup
- calendar.js: FullCalendar instance destroyed + document listeners removed on panel close
- canvas.js: window/document listeners removed before rebind and on panel close
- federation.js: badge polling interval cleared on beforeunload
- Dead `_cytoscapeInstances` code removed from workspace-layout.js
- `rg 'addEventListener' frontend/static/js/calendar.js frontend/static/js/canvas.js` — every window/document listener has a matching removal path (via removeEventListener or registerCleanup)

## Proof Level

- This slice proves: Contract — static analysis confirms balanced add/remove for all window/document listeners; runtime verification via browser DevTools getEventListeners() is recommended but not automated.

## Integration Closure

- Upstream: cleanup.js registerCleanup() API (already used by graph.js, editor.js)
- New wiring: workspace-layout.js dispose() → runCleanup() on panel element tree
- Downstream: S07 E2E regression suite will exercise panel open/close cycles

## Verification

- console.warn on cleanup errors (already exists in cleanup.js). No new runtime signals needed — leaks are silent by nature and verified via static analysis.

## Tasks

- [x] **T01: Wire dockview panel dispose() to cleanup registry** `est:45m`
  Export runCleanup() from cleanup.js so it's callable outside the IIFE. Add dispose() methods to all three dockview content renderers (object-editor, view-panel, special-panel) in workspace-layout.js that fire cleanup on the panel's element tree. Remove dead _cytoscapeInstances code.
  - Files: `frontend/static/js/cleanup.js`, `frontend/static/js/workspace-layout.js`
  - Verify: rg 'dispose' frontend/static/js/workspace-layout.js shows dispose functions on all 3 content renderers; rg 'runCleanup' frontend/static/js/cleanup.js shows window.runCleanup export; rg '_cytoscapeInstances' frontend/static/js/ returns zero results

- [ ] **T02: Fix calendar, canvas, and federation event/timer leaks** `est:1h`
  calendar.js: refactor anonymous document event handlers to named functions stored in closure; destroy FullCalendar instance and remove handlers on cleanup; register via registerCleanup(). canvas.js: add unbindEvents() that removes all window/document listeners; call it before bindEvents() on remount and register via registerCleanup(). federation.js: store setInterval handle; add beforeunload listener to clearInterval.
  - Files: `frontend/static/js/calendar.js`, `frontend/static/js/canvas.js`, `frontend/static/js/federation.js`
  - Verify: For calendar.js: rg 'removeEventListener' frontend/static/js/calendar.js returns >= 2 matches; rg 'registerCleanup' frontend/static/js/calendar.js returns >= 1 match; rg '\.destroy()' frontend/static/js/calendar.js returns >= 1 match. For canvas.js: rg 'unbindEvents' frontend/static/js/canvas.js returns >= 2 matches; rg 'registerCleanup' frontend/static/js/canvas.js returns >= 1 match. For federation.js: rg 'clearInterval' frontend/static/js/federation.js returns >= 1 match; rg 'beforeunload' frontend/static/js/federation.js returns >= 1 match.

## Files Likely Touched

- frontend/static/js/cleanup.js
- frontend/static/js/workspace-layout.js
- frontend/static/js/calendar.js
- frontend/static/js/canvas.js
- frontend/static/js/federation.js
