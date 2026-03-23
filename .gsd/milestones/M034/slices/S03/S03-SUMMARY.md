---
id: S03
parent: M034
milestone: M034
provides:
  - External drag from kanban to calendar scheduling tasks at drop time
  - sempkm:scope-changed custom event for cross-view scope synchronization
  - Calendar, kanban, and workspace scope-changed listeners with self-trigger prevention
  - Calendar external drop handler using __calendarDragPayload side-channel
  - E2E tests for cross-view drag and scope propagation
  - Backend unit tests for PATCH endpoint payloads and scope event structure
requires:
  - slice: S01
    provides: Editable calendar with FullCalendar drop target configured
affects: []
key_files:
  - frontend/static/js/calendar.js
  - frontend/static/js/kanban.js
  - frontend/static/js/workspace.js
  - backend/app/templates/browser/calendar_view.html
  - backend/app/templates/browser/kanban_view.html
  - frontend/static/css/views.css
  - e2e/tests/02-views/cross-view-drag.spec.ts
  - backend/tests/test_cross_view_drag.py
key_decisions:
  - Used dedicated __calendarDragPayload side-channel separate from __canvasDragPayload but kanban sets both
  - sempkm:scope-changed dispatched BEFORE htmx re-swap so sibling views react in parallel
  - Calendar scope sync strips existing scope_query param and appends new one rather than URL rebuild
  - E2E calendar drop test gracefully degrades when FullCalendar CDN is unreachable
patterns_established:
  - Calendar external drop follows same side-channel pattern as canvas.js
  - Kanban dragstart sets both __calendarDragPayload and __canvasDragPayload for dual drop targets
  - E2E calendar tests should try CDN load with timeout and fallback to API-only verification
observability_surfaces:
  - scope-syncing CSS animation provides visual feedback on scope propagation
  - Console logs with [calendar] prefix for external drop events
  - E2E tests in cross-view-drag.spec.ts
  - Backend unit tests in test_cross_view_drag.py
drill_down_paths:
  - .gsd/milestones/M034/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M034/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M034/slices/S03/tasks/T03-SUMMARY.md
duration: 3h
verification_result: passed
completed_at: 2026-03-22
---

# S03: Cross-View Drag & Composable Planning

**Shipped kanban-to-calendar drag scheduling, scope-changed event propagation between sibling views, and cross-view E2E tests**

## What Happened

T01 extracted calendar.js as a standalone module with initCalendar() and droppable external drop handler, enriched kanban drag data with IRI/label/duration payload, and added window._sempkmCalendar reference for external control. T02 wired the sempkm:scope-changed custom event — dispatched from workspace.js applyScopeQuery before htmx re-swap — with listeners in calendar.js and kanban.js that re-fetch data with the updated scope query, using dv-panel ID comparison to prevent self-triggering loops. T03 added E2E tests for cross-view drag and scope propagation, plus backend unit tests for PATCH endpoint payloads.

## Verification

- E2E tests pass for cross-view drag and scope propagation
- Backend unit tests pass for PATCH endpoint and scope event structure
- Kanban-to-calendar drag schedules task at drop time
- Scope change in one view propagates to sibling views

## Requirements Advanced

- PLAN-03 — External drag to calendar from kanban implemented
- PLAN-08 — Composable planning with shared scope context and cross-view events

## Requirements Validated

- PLAN-03 — Kanban-to-calendar drag proven by E2E test with SPARQL verification of persisted scheduledStart
- PLAN-08 — Scope propagation proven by E2E test and backend unit tests

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

- E2E calendar drop test degrades to API-only verification when CDN is unreachable
- Scope sync is one-directional from the view that changed — no bidirectional negotiation

## Follow-ups

None.

## Files Created/Modified

- `frontend/static/js/calendar.js` — extracted module with initCalendar() and external drop handler
- `frontend/static/js/kanban.js` — drag data enrichment with dual side-channel payloads
- `frontend/static/js/workspace.js` — sempkm:scope-changed event dispatch
- `backend/app/templates/browser/calendar_view.html` — updated to use calendar.js module
- `backend/app/templates/browser/kanban_view.html` — drag data attributes on cards
- `frontend/static/css/views.css` — external drag ghost styling, scope-syncing animation
- `e2e/tests/02-views/cross-view-drag.spec.ts` — 3 E2E tests
- `backend/tests/test_cross_view_drag.py` — 6 backend unit tests
- `e2e/helpers/selectors.ts` — calendarEvent selector

## Forward Intelligence

### What the next slice should know
- Calendar external drop handler is in calendar.js, not inline in the template
- Scope-changed event fires before the source view's own htmx re-swap

### What's fragile
- Side-channel pattern (window.__calendarDragPayload) relies on synchronous dragstart → drop lifecycle
- CDN-dependent E2E tests need timeout + fallback pattern

### Authoritative diagnostics
- Browser console logs with [calendar] prefix show external drop events with IRI and computed dates
- scope-syncing CSS animation on view toolbars confirms event reception

### What assumptions changed
- Cross-dockview-panel drag turned out to work without special handling — HTML5 drag events cross panel boundaries naturally since dockview panels are regular DOM elements
