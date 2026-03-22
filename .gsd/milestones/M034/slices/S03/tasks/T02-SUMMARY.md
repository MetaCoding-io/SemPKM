---
id: T02
parent: S03
milestone: M034
provides:
  - sempkm:scope-changed custom event dispatched from applyScopeQuery in workspace.js
  - Calendar scope-changed listener that re-fetches data with updated scope_query
  - Kanban scope-changed listener that triggers htmx re-swap with updated scope_query
  - Self-triggering prevention via dv-panel ID comparison
  - scope-syncing CSS animation for visual feedback on scope sync
key_files:
  - frontend/static/js/workspace.js
  - frontend/static/js/calendar.js
  - frontend/static/js/kanban.js
  - backend/app/templates/browser/view_toolbar.html
  - backend/app/templates/browser/kanban_view.html
  - frontend/static/css/views.css
key_decisions:
  - Event dispatched BEFORE htmx re-swap so sibling views react in parallel with the source view's own update
  - Calendar scope sync strips existing scope_query param from dataUrl and appends the new one, rather than rebuilding from scratch
  - Kanban board gets data-type-iri attribute so scope listener can pass the type to the re-fetch URL
patterns_established:
  - sempkm:scope-changed event with detail { scopeQuery, renderer, selectedType, sourcePanel } is the standard for cross-view scope propagation
  - Self-skip pattern uses el.closest('.dv-panel').id comparison — same approach for any future view that needs scope sync
  - scope-syncing CSS class with outline animation provides brief visual confirmation of sync receipt
observability_surfaces:
  - "[scope] propagated:" console log on every scope change dispatch
  - "[calendar] scope sync:" and "[kanban] scope sync:" console logs on listener activation
  - "[calendar] scope sync complete:" with event count on successful re-fetch
  - "[calendar] scope sync failed:" console.error on fetch failure
  - document.addEventListener('sempkm:scope-changed', e => console.log(e.detail)) for dev debugging
duration: 12m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Scope change propagation between views via sempkm:scope-changed event

**Wired sempkm:scope-changed custom event from scope select to calendar and kanban listeners with panel-identity self-skip, enabling cross-view scope synchronization.**

## What Happened

Modified `applyScopeQuery()` in workspace.js to accept a 4th `sourceEl` parameter, compute the source panel ID from `sourceEl.closest('.dv-panel').id`, and dispatch a `sempkm:scope-changed` CustomEvent on `document` before performing its own htmx re-swap. The event detail includes `scopeQuery`, `renderer`, `selectedType`, and `sourcePanel`.

Updated `view_toolbar.html` to pass `this` as the 4th argument to `applyScopeQuery` so the source element is available for panel ID derivation.

Added a scope-changed listener inside calendar.js's `_initCalendar` function (where `cal`, `el`, and `dataUrl` are in closure scope). The listener computes its own panel ID, skips if it matches `sourcePanel`, strips any existing `scope_query` param from the data URL, appends the new one, fetches fresh event data, and replaces all calendar events via `removeAllEvents()` + `addEvent()` loop.

Added a scope-changed listener in kanban.js (after the IIFE export, at module scope). The listener finds `.kanban-board`, computes its panel ID, skips self-triggers, reads `data-type-iri` from the board element, and issues an htmx re-swap to the kanban view URL with the updated scope_query param. Also added `data-type-iri` to the kanban board template so the type is discoverable.

Added a `.scope-syncing` CSS keyframe animation (accent outline that fades out in 300ms) in views.css. Both calendar and kanban listeners apply this class briefly on sync for visual feedback.

## Verification

All 5 task-level grep checks pass: `sempkm:scope-changed` present in workspace.js, calendar.js, and kanban.js; `sourcePanel` present in workspace.js and calendar.js.

Slice-level test files (test_cross_view_drag.py, cross-view-drag.spec.ts) are T03's responsibility — not yet created, as expected.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "sempkm:scope-changed" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 2 | `grep -q "sempkm:scope-changed" frontend/static/js/calendar.js` | 0 | ✅ pass | <1s |
| 3 | `grep -q "sempkm:scope-changed" frontend/static/js/kanban.js` | 0 | ✅ pass | <1s |
| 4 | `grep -q "sourcePanel" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 5 | `grep -q "sourcePanel" frontend/static/js/calendar.js` | 0 | ✅ pass | <1s |
| 6 | `grep -q "applyScopeQuery(this.value.*this)" backend/app/templates/browser/view_toolbar.html` | 0 | ✅ pass | <1s |
| 7 | `grep -q "data-type-iri" backend/app/templates/browser/kanban_view.html` | 0 | ✅ pass | <1s |
| 8 | `grep -q "scope-syncing" frontend/static/css/views.css` | 0 | ✅ pass | <1s |

## Diagnostics

- `[scope] propagated:` console log with scopeQuery, renderer, sourcePanel on every scope change dispatch
- `[calendar] scope sync:` console log when calendar receives and processes a scope-changed event
- `[calendar] scope sync complete: N events` confirms successful data replacement
- `[calendar] scope sync failed:` console.error surfaces fetch errors
- `[kanban] scope sync:` console log when kanban receives and processes a scope-changed event
- `document.addEventListener('sempkm:scope-changed', e => console.log(e.detail))` — attach in dev console to observe all scope propagation events
- `.scope-syncing` CSS class on view containers provides brief visual confirmation (300ms accent outline flash)

## Deviations

- Added `data-type-iri="{{ type_iri | default('') }}"` to the kanban board element in `kanban_view.html` — not in the task plan but necessary for the kanban scope listener to pass the correct type to the re-fetch URL.
- Calendar scope sync re-fetches by stripping/replacing the `scope_query` URL parameter on the original `dataUrl` rather than constructing a URL from scratch. This preserves any other parameters (like `merged=true`) the original data URL carried.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js` — modified: `applyScopeQuery` now accepts `sourceEl`, dispatches `sempkm:scope-changed` event with panel identity
- `frontend/static/js/calendar.js` — modified: added scope-changed listener with re-fetch, self-skip, and visual feedback
- `frontend/static/js/kanban.js` — modified: added scope-changed listener with htmx re-swap, self-skip, and visual feedback
- `backend/app/templates/browser/view_toolbar.html` — modified: passes `this` as 4th arg to `applyScopeQuery`
- `backend/app/templates/browser/kanban_view.html` — modified: added `data-type-iri` attribute to `.kanban-board` element
- `frontend/static/css/views.css` — modified: added `.scope-syncing` keyframe animation and class
- `.gsd/milestones/M034/slices/S03/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
