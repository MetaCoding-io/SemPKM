---
id: S03
parent: M033
milestone: M033
provides:
  - Calendar view renderer with FullCalendar 6.x integration
  - _detect_date_fields() dual heuristic (sh:datatype + well-known path IRI)
  - SPARQL calendar query builder with optional end date and scope filter
  - /browser/views/generic/calendar/data JSON endpoint
  - calendar_view.html template with CDN lazy-loading
  - Dark mode FullCalendar CSS overrides
  - Calendar sidebar entry and workspace.js label
  - 22 unit tests and 3 E2E tests
requires: []
affects: []
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/app/templates/browser/calendar_view.html
  - frontend/static/css/views.css
  - backend/tests/test_calendar.py
  - e2e/tests/02-views/calendar-view.spec.ts
key_decisions: []
patterns_established:
  - "Dual date detection heuristic: sh:datatype xsd:date/dateTime check + well-known path IRI matching"
  - "CDN lazy-loading pattern for heavy JS libraries (FullCalendar 6.1.17)"
  - "view-flex-column wrapper for full-height view panels"
observability_surfaces:
  - "logger.warning on SPARQL query failure in execute_calendar_query (returns empty events, no crash)"
  - "Empty states: no-type-selected and no-date-fields-detected with instructive messages"
drill_down_paths:
  - .gsd/milestones/M033/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M033/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M033/slices/S03/tasks/T03-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-22
---

# S03: Calendar View

**Built calendar view with FullCalendar 6.x, SHACL-based date field detection, and month/week/day switching — 22 unit tests and 3 E2E tests passing**

## What Happened

T01 built the backend: `_detect_date_fields()` on ViewSpecService using dual heuristic (sh:datatype check + well-known path IRI matching), `_build_calendar_select()` SPARQL builder, `execute_calendar_query()` returning FullCalendar-compatible events, "calendar" registered in `_VALID_RENDERERS`, router branch with empty states, and JSON data endpoint. 22 unit tests covering detection (Event, Project, Note types), query building, and event mapping.

T02 built the frontend: `calendar_view.html` with CDN lazy-loading of FullCalendar 6.1.17, type filter pills, view toolbar, `eventClick` handler opening object tabs. Dark mode CSS overrides. Calendar sidebar entry with drag-drop support. Workspace.js label registration.

T03 added 3 Playwright E2E tests: FullCalendar rendering, empty state, and month/week/day view switching.

## Verification

22 unit tests and 3 E2E tests pass. Calendar renders with proper styling in light/dark modes, empty states display correctly, event clicks open object tabs, month/week/day switching works.

## Deviations

None.

## Known Limitations

- Date detection relies on SHACL shapes — types without shape definitions won't show date fields.
- No recurring event support (one event per date property value).

## Follow-ups

None.

## Files Created/Modified

- `backend/app/views/service.py` — _detect_date_fields, _build_calendar_select, execute_calendar_query
- `backend/app/views/router.py` — Calendar renderer branch, data endpoint, _VALID_RENDERERS update
- `backend/app/templates/browser/calendar_view.html` — FullCalendar template with CDN lazy-loading
- `frontend/static/css/views.css` — Calendar container CSS, dark mode FullCalendar overrides
- `backend/app/templates/browser/views_explorer.html` — Calendar sidebar entry
- `frontend/static/js/workspace.js` — Calendar label in openGenericViewTab
- `backend/tests/test_calendar.py` — 22 unit tests
- `e2e/tests/02-views/calendar-view.spec.ts` — 3 E2E tests

## Forward Intelligence

### What the next slice should know
- The date detection heuristic is reusable — it scans SHACL PropertyShapes by both datatype and path IRI.

### What's fragile
- FullCalendar CDN version (6.1.17) is pinned in the template — CDN outage would break the view.

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` for unit tests.
- Empty state messages in the template are instructive — they tell users what date properties are needed.

### What assumptions changed
- None.
