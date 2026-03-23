---
id: S01
parent: M034
milestone: M034
provides:
  - bpkm:scheduledStart, bpkm:scheduledEnd, bpkm:estimatedDuration properties on TaskShape (basic-pkm v2.2.0)
  - Merged calendar query returning both Events and Tasks with color coding
  - Calendar PATCH endpoint for drag-to-reschedule and resize-to-change-duration
  - FullCalendar editable mode with eventDrop, eventResize, and select handlers
  - 23 unit tests for date detection, merged calendar query, and PATCH endpoint
requires: []
affects:
  - S03
  - S04
key_files:
  - models/basic-pkm/shapes/basic-pkm.jsonld
  - models/basic-pkm/ontology/basic-pkm.jsonld
  - models/basic-pkm/manifest.yaml
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/app/templates/browser/calendar_view.html
  - frontend/static/css/views.css
  - backend/tests/test_calendar_editable.py
key_decisions:
  - xsd:dateTime for scheduledStart/scheduledEnd (not xsd:date) to support intra-day time-blocking
  - xsd:string for estimatedDuration to hold ISO 8601 duration literals since xsd:duration is poorly supported in rdflib
  - Calendar PATCH uses full command dispatch pipeline (dispatch → EventStore.commit → validation queue) for event log consistency
  - Type lookup query in PATCH endpoint determines correct predicates per object type rather than requiring client to specify
patterns_established:
  - Fractional sh:order values (6.1, 6.2, 6.3) to insert properties between existing integer-ordered ones
  - Calendar interaction pattern with console.log [calendar] prefix for grep-based debugging
  - Handler-level testing pattern for FastAPI endpoints with heavy Depends() injection
observability_surfaces:
  - Calendar PATCH endpoint returns created event_iri for audit trail
  - Console logs with [calendar] prefix for drag/resize/select actions
  - 23 unit tests in test_calendar_editable.py
drill_down_paths:
  - .gsd/milestones/M034/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M034/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M034/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M034/slices/S01/tasks/T04-SUMMARY.md
duration: 4h
verification_result: passed
completed_at: 2026-03-22
---

# S01: Editable Calendar & Task Time-Blocking

**Added scheduledStart/scheduledEnd/estimatedDuration to TaskShape, merged calendar query for Tasks+Events with color coding, and FullCalendar editable mode with drag-to-reschedule, resize, and click-to-create**

## What Happened

T01 extended basic-pkm model to v2.2.0 with three new scheduling properties on TaskShape. T02 built the merged calendar query (Events + Tasks) and the PATCH endpoint for persisting drag/resize operations. T03 wired FullCalendar's editable mode with eventDrop, eventResize, and select handlers that call the PATCH endpoint with optimistic UI and rollback on failure. T04 added 23 unit tests covering date detection, merged calendar query, and PATCH endpoint failure paths.

## Verification

- 23 unit tests pass in test_calendar_editable.py
- Calendar shows both Events and Tasks with distinct colors
- Drag-to-reschedule persists via object.patch through command dispatch pipeline
- Resize changes estimatedDuration
- Click-to-create opens task form with pre-filled start time

## Requirements Advanced

- PLAN-01 — Task time-blocking properties added to schema and functional
- PLAN-02 — Editable calendar with drag, resize, and click-to-create implemented
- PLAN-09 — Calendar shows tasks and events together with color coding

## Requirements Validated

- PLAN-01 — scheduledStart/scheduledEnd/estimatedDuration on TaskShape proven by unit tests and runtime behavior

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

- Calendar form pre-fill with selected date range is deferred (stored in window._calendarSelectedDates for future use)
- Color coding uses a static type→color map — not yet user-configurable

## Follow-ups

None.

## Files Created/Modified

- `models/basic-pkm/shapes/basic-pkm.jsonld` — 3 new scheduling property shapes
- `models/basic-pkm/ontology/basic-pkm.jsonld` — 3 new OWL DatatypeProperty declarations
- `models/basic-pkm/manifest.yaml` — version bump to 2.2.0
- `backend/app/views/service.py` — execute_merged_calendar_query(), _detect_date_fields() updates
- `backend/app/views/router.py` — calendar PATCH endpoint, merged mode parameter
- `backend/app/templates/browser/calendar_view.html` — editable FullCalendar with interaction handlers
- `frontend/static/css/views.css` — calendar event color classes
- `frontend/static/js/workspace.js` — window.showCreateFormForType export
- `backend/tests/test_calendar_editable.py` — 23 unit tests

## Forward Intelligence

### What the next slice should know
- Calendar PATCH endpoint at /browser/views/calendar/patch is reusable for any view that reschedules tasks (S02 timeline uses it)
- _detect_date_fields() now prioritizes scheduledStart above all other date fields

### What's fragile
- FullCalendar CDN dependency — CDN outage breaks the calendar entirely
- Optimistic UI with info.revert() assumes PATCH is idempotent

### Authoritative diagnostics
- Console logs with `[calendar]` prefix show all user interactions with IRI and date values
- PATCH endpoint returns event_iri for tracing through event log

### What assumptions changed
- Originally planned to use xsd:duration for estimatedDuration — changed to xsd:string with ISO 8601 because rdflib's xsd:duration support is incomplete
