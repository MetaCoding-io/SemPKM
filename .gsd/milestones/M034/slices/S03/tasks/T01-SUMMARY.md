---
id: T01
parent: S03
milestone: M034
provides:
  - calendar.js extracted module with initCalendar() and droppable external drop handler
  - kanban drag data enrichment with text/iri, text/label, and __calendarDragPayload side-channel
  - window._sempkmCalendar reference for external calendar control
  - sempkm:command-executed listener for automatic calendar refresh
key_files:
  - frontend/static/js/calendar.js
  - frontend/static/js/kanban.js
  - backend/app/templates/browser/calendar_view.html
  - backend/app/templates/browser/kanban_view.html
  - frontend/static/css/views.css
key_decisions:
  - Used dedicated __calendarDragPayload side-channel (separate from __canvasDragPayload) but kanban sets both so either drop target works
patterns_established:
  - Calendar external drop follows same side-channel pattern as canvas.js — read window.__calendarDragPayload first, fallback to element data attributes
  - Kanban dragstart sets both __calendarDragPayload and __canvasDragPayload so cards can be dropped on either calendar or canvas
observability_surfaces:
  - "[calendar] external drop:" console log with IRI + start/end on every external drop
  - "[calendar] external drop failed:" console.error on PATCH failure
  - window._sempkmCalendar in dev console for instance inspection
  - Toast "Task scheduled" on success, "Failed to schedule" on error
duration: 20m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Extract calendar.js, add external drop handler, enrich kanban drag data

**Extracted calendar inline script to standalone module, added FullCalendar droppable external drop handler with side-channel pattern, enriched kanban drag data with IRI/label MIME types.**

## What Happened

Extracted the ~100-line inline IIFE from `calendar_view.html` into `frontend/static/js/calendar.js`. The module exports `window.initCalendar(containerId, dataUrl)` which lazy-loads the FullCalendar CDN and creates the calendar instance, stored as `window._sempkmCalendar` for external access.

Added `droppable: true` to the FullCalendar config with a `drop` callback that reads from `window.__calendarDragPayload` side-channel (same pattern as canvas.js), computes scheduledStart from the drop date and defaults to a 1-hour duration, then POSTs to the existing `/browser/views/calendar/patch` endpoint. On success it calls `calendar.addEvent()` for immediate visual feedback and dispatches `sempkm:command-executed`. On failure it shows an error toast and logs to console.

Added `sempkm:command-executed` listener that calls `calendar.refetchEvents()` so external mutations (kanban status change, object edits) refresh the calendar automatically.

Enriched kanban `onDragStart` to set `text/iri` and `text/label` MIME types plus both `window.__calendarDragPayload` and `window.__canvasDragPayload` side-channels. Added `data-title="{{ item.label }}"` to the kanban card template.

Added `.calendar-drop-active` CSS class with accent border and subtle box-shadow for visual feedback during external drag-over.

## Verification

All 10 task-level checks passed: file existence, droppable enabled, side-channel read/write, instance export, auto-refresh wiring, kanban IRI MIME type, kanban side-channel, data-title attribute, external script reference, no inline FullCalendar init.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f frontend/static/js/calendar.js` | 0 | ✅ pass | <1s |
| 2 | `grep -q "droppable.*true" frontend/static/js/calendar.js` | 0 | ✅ pass | <1s |
| 3 | `grep -q "__calendarDragPayload" frontend/static/js/calendar.js` | 0 | ✅ pass | <1s |
| 4 | `grep -q "window._sempkmCalendar" frontend/static/js/calendar.js` | 0 | ✅ pass | <1s |
| 5 | `grep -q "refetchEvents" frontend/static/js/calendar.js` | 0 | ✅ pass | <1s |
| 6 | `grep -q "text/iri" frontend/static/js/kanban.js` | 0 | ✅ pass | <1s |
| 7 | `grep -q "__calendarDragPayload" frontend/static/js/kanban.js` | 0 | ✅ pass | <1s |
| 8 | `grep -q "data-title" backend/app/templates/browser/kanban_view.html` | 0 | ✅ pass | <1s |
| 9 | `grep -q "calendar.js" backend/app/templates/browser/calendar_view.html` | 0 | ✅ pass | <1s |
| 10 | `! grep -q "new FullCalendar.Calendar" backend/app/templates/browser/calendar_view.html` | 0 | ✅ pass | <1s |

## Diagnostics

- `window._sempkmCalendar` — dev console reference to the FullCalendar instance
- `[calendar] external drop:` console log on every external drop with IRI, start, end
- `[calendar] external drop failed:` console.error with error details on PATCH failure
- Toast notifications: "Task scheduled" on success, "Failed to schedule — {error}" on failure
- `document.addEventListener('sempkm:command-executed', e => console.log('refresh'))` to verify auto-refresh wiring

## Deviations

- Kanban `onDragStart` also sets `window.__canvasDragPayload` (not in task plan) so kanban cards can be dropped on the canvas view too — this was a zero-cost improvement since the canvas already reads that side-channel.
- Used `handleExternalDrop(info, calendar)` as a separate function rather than inlining in the FullCalendar `drop` callback, for readability and testability.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/calendar.js` — new file, extracted calendar module with initCalendar(), droppable handler, and command-executed listener
- `frontend/static/js/kanban.js` — enriched onDragStart with text/iri, text/label, and side-channel payloads
- `backend/app/templates/browser/calendar_view.html` — replaced inline script with external calendar.js + init call
- `backend/app/templates/browser/kanban_view.html` — added data-title="{{ item.label }}" to kanban card div
- `frontend/static/css/views.css` — added .calendar-drop-active class for external drop visual feedback
