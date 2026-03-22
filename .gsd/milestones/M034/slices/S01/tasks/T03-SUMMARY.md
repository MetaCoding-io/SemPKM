---
id: T03
parent: S01
milestone: M034
provides:
  - FullCalendar editable mode with drag-to-reschedule (eventDrop) and resize-to-change-duration (eventResize) handlers
  - Click-to-create Task via select handler calling showCreateFormForType
  - Optimistic UI with info.revert() rollback on PATCH failure
  - CSS color-coding classes (.fc-event-task green, .fc-event-event purple) via eventClassNames callback
  - window.showCreateFormForType export for cross-IIFE access from calendar template
key_files:
  - backend/app/templates/browser/calendar_view.html
  - frontend/static/css/views.css
  - frontend/static/js/workspace.js
key_decisions:
  - Extracted patchCalendarEvent() helper shared by eventDrop and eventResize to avoid code duplication — both handlers need identical IRI extraction, payload construction, fetch/revert/toast logic
  - Used eventClassNames callback for CSS class assignment rather than relying solely on backend inline colors — provides hover/active states and is a consistent fallback
  - Stored selected date range in window._calendarSelectedDates for future form pre-fill enhancement without blocking the current slice
patterns_established:
  - Calendar interaction pattern: console.log with [calendar] prefix + action label + IRI + date values for all drag/resize/select events, enabling grep-based debugging
  - Shared patchCalendarEvent(info, actionLabel) pattern for any future calendar mutation handlers
observability_surfaces:
  - "[calendar] drop:" / "[calendar] resize:" / "[calendar] select range:" console logs on interaction
  - "[calendar] ... persisted, event_iri:" on successful PATCH
  - "[calendar] ... patch failed:" console.error on failure with error details
  - Toast feedback: "Task rescheduled" / "Duration updated" on success, "Failed to save — reverted" on failure
  - sempkm:command-executed custom event dispatched after successful PATCH
duration: 12m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: Make FullCalendar editable with drag/resize/select handlers and task/event color coding

**Enable interactive calendar with drag-to-reschedule, resize-to-change-duration, click-to-create-Task, and CSS color coding for Task (green) vs Event (purple)**

## What Happened

Transformed the read-only calendar into an interactive planning surface:

1. **Editable/selectable modes**: Added `editable: true`, `selectable: true`, `eventStartEditable: true`, `eventDurationEditable: true` to FullCalendar initialization.

2. **Drag handler (`eventDrop`)**: Calls shared `patchCalendarEvent(info, 'drop')` which extracts the IRI from `extendedProps`, builds `{iri, start, end}` payload, POSTs to `/browser/views/calendar/patch`, shows toast on success, dispatches `sempkm:command-executed`, and calls `info.revert()` on failure.

3. **Resize handler (`eventResize`)**: Same pattern via `patchCalendarEvent(info, 'resize')` — persists the new duration.

4. **Select handler**: On empty-slot click/drag, stashes selected dates to `window._calendarSelectedDates` and calls `window.showCreateFormForType('urn:sempkm:model:basic-pkm:Task', 'Task')` to open a new Task form.

5. **Color coding**: Added `eventClassNames` callback that assigns `.fc-event-task` or `.fc-event-event` based on `extendedProps.sourceType`. CSS rules in `views.css` provide green (#10b981) for tasks and purple (#8b5cf6) for events, with darker hover states and white text for contrast.

6. **Export fix**: Exported `showCreateFormForType` to `window` in workspace.js so the calendar template's IIFE can call it.

## Verification

- All 35 tests pass: `cd backend && .venv/bin/python -m pytest tests/test_calendar.py tests/test_calendar_editable.py -v`
- Failure-path tests pass: `validates_iri`, `requires_start_or_end`, `date_predicates` all green
- Shapes integrity check: 3 scheduling properties confirmed on TaskShape
- CSS classes verified: `.fc-event-task` and `.fc-event-event` present in views.css
- JS syntax check: `node -c frontend/static/js/workspace.js` — OK
- Jinja2 template syntax: `env.parse(calendar_view.html)` — OK

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_calendar.py tests/test_calendar_editable.py -v` | 0 | ✅ pass | 0.6s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v -k "validates_iri or requires_start_or_end or date_predicates"` | 0 | ✅ pass | 0.5s |
| 3 | Shapes integrity: 3 scheduling props on TaskShape | 0 | ✅ pass | <1s |
| 4 | `grep -c 'fc-event-task\|fc-event-event' frontend/static/css/views.css` → 4 rules | 0 | ✅ pass | <1s |
| 5 | `node -c frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 6 | Jinja2 template parse: calendar_view.html | 0 | ✅ pass | <1s |

## Diagnostics

- Browser console: search for `[calendar]` to see all drag/resize/select events with IRI and date details
- Network tab: POST to `/browser/views/calendar/patch` shows payload and response
- DOM inspection: `.fc-event-task` and `.fc-event-event` classes on calendar event elements in DevTools
- Toast messages: visible feedback for success and failure states
- `window._calendarSelectedDates` — inspect in console after clicking empty slot to verify date stash

## Deviations

- `showCreateFormForType` was not exported to `window` in the existing codebase (task plan assumed it was). Added the export in workspace.js at the global exports section.
- The slice-level failure-path verification `-k "invalid_iri or unsupported_type or no_dates"` doesn't match actual test names (they're `validates_iri`, `request_model`, `requires_start_or_end`, `date_predicates`). Ran with corrected filter — all 3 matching tests pass.

## Known Issues

- None

## Files Created/Modified

- `backend/app/templates/browser/calendar_view.html` — Added patchCalendarEvent helper, editable/selectable modes, eventDrop/eventResize/select handlers, eventClassNames callback for color coding
- `frontend/static/css/views.css` — Added .fc-event-task (green), .fc-event-event (purple) color classes with hover states, cursor styles for editable events, selection highlight
- `frontend/static/js/workspace.js` — Exported showCreateFormForType to window for cross-IIFE access from calendar template
- `.gsd/milestones/M034/slices/S01/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
