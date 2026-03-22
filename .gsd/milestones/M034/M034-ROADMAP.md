# M034: Task Planning, Time-Blocking & Calendar UX

**Vision:** Transform the read-only calendar into an interactive daily planning hub — time-block tasks, drag from kanban to schedule, view projects as Gantt timelines, set up recurring tasks, and run structured PPV reviews.

## Success Criteria

- Tasks have scheduledStart/scheduledEnd/estimatedDuration properties; setting them places the task on the calendar as a colored block
- Users drag tasks onto calendar time slots (or from kanban) to schedule them; resize to change duration; click empty slots to create tasks
- A timeline/Gantt view shows tasks as horizontal bars with dependency arrows, filterable by project or saved query
- Recurring tasks with RRULE strings show virtual instances on the calendar without creating real objects
- Task templates exist as named reusable patterns with default properties and subtask structures
- PPV weekly/monthly/quarterly/yearly review workflows run via the existing WorkflowSpec stepper
- Calendar + kanban side by side share scope context — status change on kanban triggers calendar re-fetch

## Key Risks / Unknowns

- **FullCalendar interaction within htmx swap lifecycle** — The calendar template is loaded via htmx into dockview panels. FullCalendar's `editable`/`droppable`/`selectable` options need the interaction plugin, which IS included in the standard CDN bundle (research confirmed). Re-initialization on htmx re-swap via the existing `tryInit` polling pattern should work but needs proof.
- **Custom timeline renderer** — Most code-heavy new view. Frappe Gantt (MIT, zero deps, ~50KB SVG) is the leading candidate per research. Must integrate as a generic view renderer following the established ViewSpecService pattern.
- **Cross-dockview-panel drag** — Dragging a task from a kanban or explorer panel to a calendar panel crosses dockview panel boundaries. `stopPropagation()` is proven in kanban/canvas, but the drop target is FullCalendar's `externalDrop` handler, not a custom drop zone. Needs coordination.
- **RRULE expansion without python-dateutil** — Backend needs `python-dateutil` (not currently a dependency) for `rrule.rrulestr()` to expand recurrence rules into virtual calendar events.

## Proof Strategy

- Editable calendar → retire in S01 by shipping drag-to-reschedule, resize, click-to-create on real Task data with `scheduledStart`/`scheduledEnd` persisted via `object.patch`
- Timeline/Gantt → retire in S02 by rendering real task data with dependency arrows using Frappe Gantt, integrated as a generic view renderer
- Cross-panel drag → retire in S03 by shipping kanban-to-calendar drag with visible scheduling result
- RRULE expansion → retire in S04 by showing virtual recurring instances on the calendar from a single task's recurrenceRule

## Verification Classes

- Contract verification: pytest unit tests for RRULE expansion, date field detection, template CRUD, review workflow steps; Playwright E2E for calendar drag, timeline rendering, cross-view drag
- Integration verification: Docker Compose stack with calendar + kanban side by side, drag task from kanban to calendar, verify SPARQL-persisted scheduledStart/scheduledEnd; timeline filtered by saved query showing dependency arrows
- Operational verification: scheduled data persists across container restart; RRULE expansion generates correct dates without phantom objects; review workflows create properly-linked PPV objects
- UAT / human verification: calendar interaction feel (drag smoothness, resize handles), timeline readability, planning workflow usability

## Milestone Definition of Done

This milestone is complete only when all are true:

- All slices pass their verification criteria
- bpkm:Task schema has scheduledStart/scheduledEnd/estimatedDuration; basic-pkm upgraded to v2.2.0
- Calendar view accepts drag, resize, and click-to-create interactions that persist via object.patch
- External drag from kanban or explorer to calendar schedules a task at the drop time
- Timeline/Gantt view renders task bars with dependency arrows, supports drag-to-reschedule and zoom
- Recurring tasks with RRULE show virtual calendar instances; recurrence editor UI exists
- Task templates are creatable, listable, and usable from command palette
- PPV review workflows run via stepper, creating linked Review objects
- Calendar and kanban views share scope context and react to each other's changes

## Requirement Coverage

New requirements introduced by M034:

| ID | Requirement | Primary | Supporting |
|---|---|---|---|
| PLAN-01 | Task time-blocking (scheduledStart/scheduledEnd/estimatedDuration on Task) | S01 | — |
| PLAN-02 | Editable calendar (drag-to-reschedule, resize duration, click-to-create) | S01 | — |
| PLAN-03 | External drag to calendar (kanban/explorer → calendar drop scheduling) | S03 | S01 |
| PLAN-04 | Timeline/Gantt view with dependency arrows and zoom levels | S02 | — |
| PLAN-05 | Recurring tasks (RRULE storage, virtual calendar expansion, editor UI) | S04 | S01 |
| PLAN-06 | Task templates (named patterns, subtask structures, command palette) | S05 | — |
| PLAN-07 | PPV review workflows (weekly/monthly/quarterly/yearly via stepper) | S05 | — |
| PLAN-08 | Composable planning (calendar + kanban side by side, shared scope, cross-view events) | S03 | S01, S02 |
| PLAN-09 | Calendar shows tasks and events together with color coding | S01 | S03 |
| PLAN-10 | Timeline project-scoped filtering via saved queries | S02 | — |

Existing requirements referenced:
- CAL-01..CAL-03 (M033): Calendar view exists, read-only — M034 extends to interactive
- D301 (M033 scope decision): "Add inline reschedule if users request it" — M034 delivers this

Orphan risks: None — all prior Active requirements (APP-01..14, RSS-01..08, GCAL-01..09) are maintenance concerns from earlier milestones, not blocked by or dependent on M034.

## Slices

- [x] **S01: Editable Calendar & Task Time-Blocking** `risk:high` `depends:[]`
  > After this: User opens Calendar view, sees Tasks (with scheduledStart) as colored blocks alongside Events. Dragging a task reschedules it. Resizing changes duration. Clicking an empty time slot creates a new task at that time. Tasks have scheduledStart/scheduledEnd/estimatedDuration in the schema. Calendar data endpoint returns both Events and scheduled Tasks.
  - **Demo:** Open calendar, drag a task from 2pm to 4pm — task block moves, reload confirms persistence. Click empty 10am slot — new task form opens with pre-filled start time. Resize a task block to 2 hours — duration updates.
  - **Proof:** E2E test: schedule task via drag → verify SPARQL shows scheduledStart/scheduledEnd. Unit test: calendar query returns both Events and Tasks.
  - **Verification:** `contract` `integration`

- [x] **S02: Timeline / Gantt View** `risk:high` `depends:[]`
  > After this: User opens a Timeline view from the views menu. Frappe Gantt renders tasks as horizontal bars with dependency arrows. Drag-to-reschedule and resize work. Zoom levels (day/week/month/quarter) available. Project-scoped filtering via saved queries.
  - **Demo:** Open Timeline view filtered to a project. See task bars with arrows showing bpkm:dependsOn. Drag a bar to reschedule. Switch zoom from week to month.
  - **Proof:** E2E test: timeline renders with correct task bars and dependency arrows. Unit test: timeline data endpoint returns bars with dependency edges.
  - **Verification:** `contract` `integration`

- [x] **S03: Cross-View Drag & Composable Planning** `risk:medium` `depends:[S01]`
  > After this: User opens calendar and kanban side by side in dockview. Drags a task from the kanban "todo" column onto the calendar at Wednesday 2pm. Task gets scheduledStart, appears on calendar, and status updates in kanban if configured. Scope context shared between views — selecting a project filter in one updates the other.
  - **Demo:** Open kanban + calendar side by side. Drag task card from kanban to calendar 2pm slot — card gets scheduled, calendar shows it as a block. Change scope in calendar — kanban filters to same query.
  - **Proof:** E2E test: drag from kanban panel to calendar panel → verify scheduledStart persisted and task visible on calendar. Verify scope change propagation.
  - **Verification:** `contract` `integration`

- [ ] **S04: Recurring Tasks & RRULE Expansion** `risk:medium` `depends:[S01]`
  > After this: User creates a task with a recurrence rule (e.g., FREQ=WEEKLY;BYDAY=FR). Calendar shows virtual instances for the next N occurrences without creating real objects. A recurrence editor UI provides presets (daily, weekly, monthly, custom). Exception dates (EXDATE) are tracked.
  - **Demo:** Create task "Weekly Review" with FREQ=WEEKLY;BYDAY=FR. Calendar shows next 4 Fridays as task blocks. Click one — opens the real task. Edit recurrence to skip next Friday — EXDATE applied, that instance disappears.
  - **Proof:** Unit test: RRULE expansion generates correct dates, respects EXDATE. E2E test: recurring task shows virtual instances on calendar.
  - **Verification:** `contract` `integration`

- [ ] **S05: Task Templates & Review Workflows** `risk:low` `depends:[S01]`
  > After this: User creates a task template with a title pattern, default properties, and subtask structure. "Create from Template" appears in the command palette. PPV review workflows (weekly/monthly/quarterly/yearly) are available as pre-seeded WorkflowSpecs that guide users through review steps and create linked Review objects.
  - **Demo:** Open command palette → "Create from Template" → select "Sprint Planning" → new task created with defaults. Run "Weekly Review" workflow → stepper guides through completed tasks, next week goals → creates ppv:WeeklyReview object linked to the month.
  - **Proof:** E2E test: create task from template, verify properties match. E2E test: run weekly review workflow, verify ppv:WeeklyReview object created with correct links.
  - **Verification:** `contract` `integration`

## Boundary Map

### S01 (Editable Calendar & Task Time-Blocking)

Produces:
- `models/basic-pkm/shapes/basic-pkm.jsonld` — 3 new properties on TaskShape: `bpkm:scheduledStart` (xsd:dateTime), `bpkm:scheduledEnd` (xsd:dateTime), `bpkm:estimatedDuration` (xsd:string, ISO 8601 duration)
- `models/basic-pkm/ontology/basic-pkm.jsonld` — 3 new OWL DatatypeProperty declarations
- `models/basic-pkm/manifest.yaml` — version bump to 2.2.0
- `backend/app/views/service.py` — `execute_calendar_query()` extended to include Tasks with scheduledStart alongside Events with schema:startDate
- `backend/app/views/router.py` — calendar data endpoint extended for task+event merge; new PATCH handler for calendar event drag/resize
- `backend/app/templates/browser/calendar_view.html` — FullCalendar initialized with `editable: true`, `selectable: true`, `eventDrop`/`eventResize`/`select` handlers that call object.patch or create endpoints
- `frontend/static/css/views.css` — calendar event color coding (tasks vs events, priority-based)

Consumes:
- `backend/app/commands/router.py` — existing `object.patch` for scheduledStart/scheduledEnd updates
- `backend/app/views/service.py` — existing `_detect_date_fields()`, `_build_calendar_select()`
- `frontend/static/js/kanban.js` — drag pattern reference (stopPropagation)

### S02 (Timeline / Gantt View)

Produces:
- `frontend/static/vendor/frappe-gantt.min.js` — vendored Frappe Gantt library (~50KB)
- `frontend/static/vendor/frappe-gantt.min.css` — Frappe Gantt styles
- `backend/app/templates/browser/timeline_view.html` — Jinja2 template with Frappe Gantt init, data fetch, drag/resize handlers
- `backend/app/views/service.py` — `_build_timeline_select()`, `execute_timeline_query()` returning task bars with dependency edges
- `backend/app/views/router.py` — timeline renderer case in generic_view, timeline data in generic_view_data
- `frontend/static/css/views.css` — timeline view CSS overrides for dark mode, container sizing

Consumes:
- S01's scheduledStart/scheduledEnd for bar positioning (falls back to dueDate for tasks without schedule)
- `bpkm:dependsOn` edges for dependency arrows
- Existing `_detect_date_fields()` pattern
- `_VALID_RENDERERS` set in router (add "timeline")

### S03 (Cross-View Drag & Composable Planning)

Produces:
- `frontend/static/js/calendar.js` — extracted from inline template script; FullCalendar `drop` handler for external events; `sempkm:calendar-reschedule` custom event
- `frontend/static/js/kanban.js` — extended `dragstart` to set `text/x-sempkm-iri` + title + estimatedDuration on dataTransfer; kanban cards get `data-iri` + `data-title` + `data-duration` attributes
- `frontend/static/js/workspace.js` — `sempkm:scope-changed` custom event listener wiring between dockview panels
- `frontend/static/css/views.css` — external drag ghost styling

Consumes:
- S01's editable calendar (drop target configured)
- S01's calendar data endpoint (re-fetches on scope change)
- Existing kanban drag handlers (extend, not replace)
- dockview panel API for cross-panel event routing

### S04 (Recurring Tasks & RRULE Expansion)

Produces:
- `backend/pyproject.toml` — `python-dateutil~=2.9.0` added to dependencies
- `backend/app/views/service.py` — `_expand_rrule()` method generating virtual events from recurrenceRule; `execute_calendar_query()` extended to call expansion
- `models/basic-pkm/shapes/basic-pkm.jsonld` — `bpkm:recurrenceRule` (xsd:string) and `bpkm:exceptionDates` (xsd:string) added to TaskShape
- `backend/app/templates/browser/recurrence_editor.html` — modal/popover UI with presets (daily, weekdays, weekly, biweekly, monthly, custom) and EXDATE picker
- `frontend/static/js/recurrence-editor.js` — RRULE string builder from UI selections
- `frontend/static/css/views.css` — recurrence editor styling, recurring event indicators

Consumes:
- S01's calendar rendering (virtual events merge into event list)
- Existing `bpkm:recurrenceRule` on EventShape (same pattern, now also on TaskShape)
- `object.patch` command for saving recurrence rules

### S05 (Task Templates & Review Workflows)

Produces:
- `backend/app/templates_service.py` — TaskTemplate CRUD (RDF storage in `urn:sempkm:task-templates` graph)
- `backend/app/templates_router.py` — REST endpoints for template CRUD + instantiation
- `backend/app/templates/browser/template_picker.html` — command palette integration for "Create from Template"
- `models/ppv/workflows/` — 4 seed WorkflowSpec definitions (weekly, monthly, quarterly, yearly review)
- `backend/app/workflow/router.py` — extended to handle review-specific step types (task summary, goal setting)
- `frontend/static/js/workspace.js` — command palette entries for templates and review workflows

Consumes:
- Existing WorkflowSpec stepper runner (view, dashboard, form step types)
- PPV model review shapes (WeeklyReviewShape, MonthlyReviewShape, etc.)
- Existing command palette ninja-keys registration pattern
- `object.create` command for template instantiation
