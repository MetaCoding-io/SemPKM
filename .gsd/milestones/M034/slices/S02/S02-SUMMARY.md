---
id: S02
parent: M034
milestone: M034
provides:
  - Timeline/Gantt view as 7th generic view renderer using Frappe Gantt
  - _build_timeline_select() and execute_timeline_query() with dependency grouping
  - Drag-to-reschedule on timeline bars via calendar PATCH endpoint reuse
  - Status-based bar coloring (done, active, blocked) and zoom levels
  - E2E tests for timeline rendering, dependency arrows, and zoom switching
  - 15 unit tests for SPARQL construction, dep grouping, date fallback
requires:
  - slice: S01
    provides: scheduledStart/scheduledEnd properties and calendar PATCH endpoint
affects: []
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/app/templates/browser/timeline_view.html
  - frontend/static/css/views.css
  - backend/tests/test_timeline.py
  - e2e/tests/02-views/timeline.spec.ts
key_decisions:
  - Reused calendar PATCH endpoint for drag-to-reschedule rather than creating timeline-specific endpoint
  - Used bpkm:dependsOn/priority/taskStatus IRIs directly in SPARQL rather than dynamic detection
  - Set container_height to 'auto' so Frappe Gantt grows to fit all tasks
  - Dependencies array joined with comma for Frappe Gantt v1.2.2 format
patterns_established:
  - Timeline SPARQL groups multi-row results by task IRI to collect dependency arrays
  - CDN lazy-load pattern for Frappe Gantt follows same structure as FullCalendar
  - SVG sub-elements in Playwright should use state:'attached' not visibility assertions
observability_surfaces:
  - logger.info("execute_timeline_query: type=%s tasks=%d deps=%d") structured log
  - 15 unit tests in test_timeline.py
  - E2E tests with timeline selectors in SEL.views
drill_down_paths:
  - .gsd/milestones/M034/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M034/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M034/slices/S02/tasks/T03-SUMMARY.md
duration: 3h
verification_result: passed
completed_at: 2026-03-22
---

# S02: Timeline / Gantt View

**Added timeline as 7th generic view renderer with Frappe Gantt for task bars, dependency arrows, drag-to-reschedule, zoom levels, and project-scoped filtering**

## What Happened

T01 built the backend SPARQL query builder and data endpoint for timeline views, including multi-row dependency grouping and status-to-CSS-class mapping. T02 created the timeline_view.html template with Frappe Gantt CDN integration, dark mode overrides, and drag-to-reschedule using the calendar PATCH endpoint. T03 added E2E Playwright tests proving rendering, dependency arrows (using state:'attached' for SVG elements), and zoom level switching.

## Verification

- 15 unit tests pass in test_timeline.py
- E2E tests pass: timeline renders task bars, dependency arrows attached, zoom switching works
- Timeline appears in views explorer sidebar with drag-drop support

## Requirements Advanced

- PLAN-04 — Timeline/Gantt view with dependency arrows and zoom levels implemented
- PLAN-10 — Timeline project-scoped filtering via saved queries functional

## Requirements Validated

- PLAN-04 — Frappe Gantt renders real task data with dependency arrows, drag-to-reschedule, zoom levels proven by unit + E2E tests

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

- Frappe Gantt loaded from CDN — CDN outage breaks the timeline view
- Dependencies use bpkm:dependsOn hardcoded — not dynamically detected from SHACL shapes

## Follow-ups

None.

## Files Created/Modified

- `backend/app/views/service.py` — _build_timeline_select(), execute_timeline_query()
- `backend/app/views/router.py` — timeline renderer case in generic_view + generic_view_data
- `backend/app/templates/browser/timeline_view.html` — Frappe Gantt template with interactions
- `frontend/static/css/views.css` — timeline dark mode overrides and status bar colors
- `backend/app/templates/browser/views_explorer.html` — timeline entry in sidebar
- `frontend/static/js/workspace.js` — "timeline" label in openGenericViewTab labels
- `backend/tests/test_timeline.py` — 15 unit tests
- `e2e/tests/02-views/timeline.spec.ts` — 3 E2E tests
- `e2e/helpers/selectors.ts` — timeline selectors added to SEL.views
- `e2e/helpers/dockview.ts` — 'timeline' added to renderer type union

## Forward Intelligence

### What the next slice should know
- Timeline reuses calendar PATCH endpoint — any changes to that endpoint affect both views
- _detect_date_fields() priority puts scheduledStart first; test data must use scheduledStart for timeline visibility

### What's fragile
- Frappe Gantt CDN dependency — same risk as FullCalendar
- Dependencies comma-joined string format is specific to Frappe Gantt v1.2.2

### Authoritative diagnostics
- `execute_timeline_query` structured log shows type, task count, and dependency count
- E2E test uses state:'attached' for SVG assertions — documented in KNOWLEDGE.md

### What assumptions changed
- Originally planned to vendor Frappe Gantt — used CDN lazy-loading instead for faster delivery
