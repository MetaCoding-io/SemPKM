---
id: M034
provides:
  - bpkm:scheduledStart/scheduledEnd/estimatedDuration on TaskShape (basic-pkm v2.2.0)
  - Editable FullCalendar with drag-to-reschedule, resize-to-change-duration, click-to-create
  - Merged calendar query returning both Events and Tasks with color coding
  - Calendar PATCH endpoint for persisting schedule changes via command dispatch pipeline
  - Timeline/Gantt view (8th generic renderer) using Frappe Gantt with dependency arrows and zoom
  - External drag from kanban to calendar scheduling tasks at drop time
  - sempkm:scope-changed cross-view event propagation between sibling dockview panels
  - RRULE expansion generating virtual calendar instances without creating real objects
  - Recurrence editor UI with presets and custom RRULE builder
  - TaskTemplateService with RDF CRUD and batch instantiation via @slot: references
  - 4 PPV review workflow seeds (Weekly/Monthly/Quarterly/Yearly) with per-name idempotency
  - Command palette entries for templates and review workflow launchers
key_decisions:
  - D303: Enable editable/selectable/droppable on existing FullCalendar CDN bundle
  - D304: Frappe Gantt (MIT, zero deps, ~50KB SVG) for timeline/Gantt renderer
  - D305: scheduledStart/scheduledEnd (xsd:dateTime) + estimatedDuration (xsd:string ISO 8601) complement dueDate/doDate
  - D306: python-dateutil for backend RRULE expansion at query time
  - D307: text/x-sempkm-iri dataTransfer protocol for cross-panel drag
  - D308: PLAN-01..PLAN-10 requirement IDs for planning domain
  - D309: Frappe Gantt loaded from CDN (not vendored) following established pattern
patterns_established:
  - Fractional sh:order values (6.1–6.5) to insert properties between existing integer-ordered ones
  - Calendar PATCH endpoint reusable by any view that reschedules tasks
  - CDN lazy-load IIFE pattern for Frappe Gantt matching FullCalendar/Leaflet/Chart.js
  - __calendarDragPayload side-channel for kanban-to-calendar drag data transfer
  - sempkm:scope-changed custom event with dv-panel ID self-trigger prevention
  - Virtual event synthetic IDs: {iri}__recurrence__{isodate}
  - Naive datetime throughout RRULE expansion (dateutil rruleset requires consistent naive/aware)
  - RDF-backed service with dedicated named graph for template CRUD
  - Internal batch command dispatch with slot_map for template instantiation
observability_surfaces:
  - Calendar PATCH endpoint returns event_iri for audit trail
  - Console logs with [calendar] prefix for drag/resize/select/drop actions
  - execute_timeline_query structured log with type, task count, dependency count
  - scope-syncing CSS animation on view toolbars confirms scope propagation
  - TaskTemplateService structured logs for all CRUD operations
  - 99 unit tests across 6 test files + 8 E2E tests across 3 spec files
requirement_outcomes:
  - id: PLAN-01
    from_status: active
    to_status: validated
    proof: 23 unit tests in test_calendar_editable.py prove scheduledStart/scheduledEnd/estimatedDuration on TaskShape. Schema confirmed in basic-pkm v2.2.0 shapes file.
  - id: PLAN-02
    from_status: active
    to_status: validated
    proof: S01 delivers drag-to-reschedule (eventDrop), resize (eventResize), and click-to-create (select handler). 23 unit tests + calendar PATCH endpoint verified.
  - id: PLAN-03
    from_status: active
    to_status: validated
    proof: S03 E2E test proves kanban-to-calendar drag with SPARQL verification of persisted scheduledStart. Backend unit tests confirm PATCH payload structure.
  - id: PLAN-04
    from_status: active
    to_status: validated
    proof: S02 delivers Frappe Gantt timeline with dependency arrows, drag-to-reschedule, zoom levels. 15 unit tests + 3 E2E tests (rendering, arrows via state:attached, zoom switching).
  - id: PLAN-05
    from_status: active
    to_status: validated
    proof: S04 delivers RRULE expansion with 24 unit tests (weekly/daily/monthly/EXDATE/COUNT/UNTIL/malformed/max cap) + 2 E2E tests (virtual instances rendered, click routes to master). Recurrence editor UI with presets and custom builder.
  - id: PLAN-06
    from_status: active
    to_status: validated
    proof: S05 delivers TaskTemplateService with full CRUD, batch instantiation via @slot:, command palette "Create from Template" with dynamic API children. 21 unit tests.
  - id: PLAN-07
    from_status: active
    to_status: validated
    proof: S05 seeds 4 PPV review workflows (Weekly/Monthly/Quarterly/Yearly) with per-name idempotency. 10 seed tests verify correct step configurations. 4 palette launcher commands verified by grep.
  - id: PLAN-08
    from_status: active
    to_status: validated
    proof: S03 delivers calendar+kanban side-by-side with scope-changed propagation and cross-view drag. E2E tests prove scope change propagation and drag scheduling.
  - id: PLAN-09
    from_status: active
    to_status: validated
    proof: S01 merged calendar query returns both Events (schema:startDate) and Tasks (bpkm:scheduledStart) with distinct color coding via CSS classes. Unit tests verify merged query output.
  - id: PLAN-10
    from_status: active
    to_status: validated
    proof: S02 timeline accepts scope_query parameter for saved query filtering. _build_timeline_select() composes with scope WHERE injection. Unit tests verify scope binding.
duration: 18h
verification_result: passed-with-gaps
completed_at: 2026-03-22
---

# M034: Task Planning, Time-Blocking & Calendar UX

**Transformed the read-only calendar into an interactive daily planning hub with time-blocking, cross-view drag scheduling, timeline/Gantt view, recurring tasks, templates, and review workflows — 99 unit tests + 8 E2E tests across 5 slices**

## What Happened

S01 extended basic-pkm to v2.2.0 with three scheduling properties (scheduledStart, scheduledEnd, estimatedDuration) and wired FullCalendar's editable mode — drag reschedules tasks, resize changes duration, clicking empty slots creates tasks. The calendar PATCH endpoint flows through the full command dispatch pipeline for event log consistency. The merged calendar query returns both Events and Tasks with color-coded rendering.

S02 added the timeline/Gantt view as the 8th generic renderer, using Frappe Gantt from CDN. Tasks render as horizontal bars with dependency arrows from bpkm:dependsOn edges. Drag-to-reschedule reuses S01's calendar PATCH endpoint. Zoom levels (day/week/month/quarter) switch via Frappe Gantt's native controls. Project-scoped filtering works via saved query scope injection.

S03 connected the views — kanban cards gained drag data with IRI/title/duration payload, and the calendar accepts external drops via FullCalendar's droppable handler. A new sempkm:scope-changed custom event propagates scope changes between sibling dockview panels, with self-trigger prevention via panel ID comparison.

S04 added recurring task support. Tasks with RFC 5545 RRULE strings produce virtual calendar instances via python-dateutil expansion, capped at 52 per task within a ±6 month window. A recurrence editor UI provides presets (daily/weekdays/weekly/biweekly/monthly/custom) and EXDATE management. Virtual events render with dashed borders and ↻ prefix; clicking routes to the master task.

S05 built the task template system (RDF CRUD in a dedicated named graph, REST API, batch instantiation via @slot: references through the command dispatch pipeline) and seeded 4 PPV review workflows (Weekly/Monthly/Quarterly/Yearly) with per-name idempotency. Both are accessible from the command palette.

## Cross-Slice Verification

| Success Criterion | Status | Evidence |
|---|---|---|
| Tasks have scheduledStart/scheduledEnd/estimatedDuration; basic-pkm v2.2.0 | ✅ | manifest.yaml shows version 2.2.0; shapes file has 6 scheduling property references |
| Calendar accepts drag, resize, click-to-create; persists via object.patch | ✅ | S01: 23 unit tests, FullCalendar editable mode with eventDrop/eventResize/select handlers |
| External drag from kanban to calendar schedules task at drop time | ✅ | S03: E2E test with SPARQL verification of persisted scheduledStart |
| Timeline/Gantt renders task bars with dependency arrows; drag-to-reschedule and zoom | ✅ | S02: 15 unit tests + 3 E2E tests (bars rendered, arrows attached, zoom switching) |
| Recurring tasks with RRULE show virtual instances without creating real objects | ✅ | S04: 24 unit tests + 2 E2E tests; virtual events have synthetic IDs and isVirtual flag |
| Task templates creatable, listable, usable from command palette | ✅ | S05: 21 unit tests; command palette entries verified by grep |
| PPV review workflows run via stepper, creating linked Review objects | ✅ | S05: 4 seed workflows with correct step configs; 10 seed tests pass |
| Calendar + kanban share scope context and react to each other's changes | ✅ | S03: scope-changed event propagation E2E tested; dv-panel ID self-trigger prevention |
| All slices pass verification | ✅ | All 5 slices have verification_result: passed |
| User guide docs for new features | ❌ | No docs/guide chapters created for M034 features (calendar editing, timeline, templates, recurring tasks, review workflows) |

## Requirement Changes

- PLAN-01: active → validated — scheduledStart/scheduledEnd/estimatedDuration on TaskShape proven by 23 unit tests and schema inspection
- PLAN-02: active → validated — drag-to-reschedule, resize, click-to-create all functional with calendar PATCH persistence
- PLAN-03: active → validated — kanban-to-calendar drag with SPARQL-verified scheduledStart persistence
- PLAN-04: active → validated — Frappe Gantt renders task bars with dependency arrows, zoom levels, drag-to-reschedule
- PLAN-05: active → validated — RRULE expansion generates correct dates, respects EXDATE, 24+2 tests
- PLAN-06: active → validated — template CRUD + command palette integration, 21 unit tests
- PLAN-07: active → validated — 4 review workflows seeded with correct step configurations, 10 seed tests
- PLAN-08: active → validated — cross-view drag and scope propagation proven by E2E tests
- PLAN-09: active → validated — merged calendar query returns Events + Tasks with color coding
- PLAN-10: active → validated — timeline accepts scope_query for project-scoped filtering

## Gaps

**User guide documentation not created.** M034 delivered 10 user-visible features (editable calendar, timeline view, cross-view drag, recurring tasks, recurrence editor, task templates, review workflows, scope propagation, task scheduling properties, composable planning) without corresponding docs/guide chapters. This is a known standing requirement gap. The next milestone or a dedicated docs pass should cover:
- Calendar editing interactions (drag, resize, click-to-create)
- Timeline/Gantt view usage and dependency visualization
- Recurring tasks and the recurrence editor
- Task templates and "Create from Template" workflow
- PPV review workflows
- Composable planning (calendar + kanban side by side)

## Forward Intelligence

### What the next milestone should know
- Calendar PATCH endpoint at `/browser/views/calendar/patch` is reusable for any view that reschedules tasks — both calendar and timeline use it
- `_detect_date_fields()` prioritizes scheduledStart above all other date fields — test data must use scheduledStart for timeline/calendar visibility
- TaskTemplateService is on `app.state.template_service` — instantiation uses dispatch() + EventStore.commit() pipeline
- SEED_WORKFLOWS constant in `backend/app/dashboard/seed.py` is importable for downstream references
- Virtual events use `{iri}__recurrence__{isodate}` synthetic IDs — any code processing calendar event IDs must check for `__recurrence__`

### What's fragile
- FullCalendar and Frappe Gantt both loaded from CDN — CDN outage breaks both views entirely
- Frappe Gantt dependencies comma-joined string format is specific to v1.2.2
- Side-channel pattern (window.__calendarDragPayload) relies on synchronous dragstart → drop lifecycle
- Template instantiation assumes command schemas haven't changed — if ObjectCreateParams gains required fields, instantiate() breaks
- Review workflow launchers find workflows by name string match — name changes in seed data require palette code update

### Authoritative diagnostics
- Console logs with `[calendar]` prefix show all calendar interactions with IRI and date values
- `execute_timeline_query` structured log shows type, task count, and dependency count
- TaskTemplateService logs at INFO for all CRUD operations with template IRI
- 99 unit tests + 8 E2E tests provide comprehensive regression detection

### What assumptions changed
- Originally planned to vendor Frappe Gantt (D304) — used CDN lazy-loading instead (D309) to match the established codebase pattern
- Originally planned xsd:duration for estimatedDuration — changed to xsd:string with ISO 8601 because rdflib's xsd:duration support is incomplete
- Originally planned separate templates_service.py at top level — placed in task_templates/ package for better organization

## Files Created/Modified

- `models/basic-pkm/shapes/basic-pkm.jsonld` — 5 new scheduling/recurrence property shapes on TaskShape
- `models/basic-pkm/ontology/basic-pkm.jsonld` — 5 new OWL DatatypeProperty declarations
- `models/basic-pkm/manifest.yaml` — version bump to 2.2.0
- `backend/pyproject.toml` — python-dateutil~=2.9.0 added
- `backend/app/views/service.py` — execute_merged_calendar_query(), _build_timeline_select(), execute_timeline_query(), _expand_rrule()
- `backend/app/views/router.py` — calendar PATCH endpoint, timeline renderer, merged mode parameter
- `backend/app/templates/browser/calendar_view.html` — editable FullCalendar with interaction handlers
- `backend/app/templates/browser/timeline_view.html` — Frappe Gantt template with interactions
- `frontend/static/js/calendar.js` — extracted module with initCalendar(), external drop handler, scope sync
- `frontend/static/js/kanban.js` — drag data enrichment with dual side-channel payloads
- `frontend/static/js/recurrence-editor.js` — RRULE preset/custom editor + EXDATE picker
- `frontend/static/js/workspace.js` — scope-changed dispatch, showCreateFormForType export, template/workflow palette entries
- `frontend/static/css/views.css` — calendar colors, timeline dark mode, recurrence editor, scope-syncing animation
- `backend/app/task_templates/service.py` — TaskTemplateService with SPARQL CRUD
- `backend/app/task_templates/router.py` — REST API and htmx template routes
- `backend/app/dashboard/seed.py` — 4 PPV review workflow seed definitions
- `backend/tests/test_calendar_editable.py` — 23 unit tests
- `backend/tests/test_timeline.py` — 15 unit tests
- `backend/tests/test_rrule_expansion.py` — 24 unit tests
- `backend/tests/test_task_templates.py` — 21 unit tests
- `backend/tests/test_seed_data.py` — 10 unit tests
- `backend/tests/test_cross_view_drag.py` — 6 unit tests
- `e2e/tests/02-views/timeline.spec.ts` — 3 E2E tests
- `e2e/tests/02-views/recurring-tasks.spec.ts` — 2 E2E tests
- `e2e/tests/02-views/cross-view-drag.spec.ts` — 3 E2E tests
