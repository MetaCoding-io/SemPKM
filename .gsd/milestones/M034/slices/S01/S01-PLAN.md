# S01: Editable Calendar & Task Time-Blocking

**Goal:** Tasks have scheduledStart/scheduledEnd/estimatedDuration properties. The calendar view shows both Events and scheduled Tasks with color coding. Users can drag tasks to reschedule, resize to change duration, and click empty slots to create new tasks — all persisted via object.patch/object.create.
**Demo:** Open Calendar view with type "Task" selected, see scheduled tasks as colored blocks alongside events. Drag a task from 2pm to 4pm — block moves, reload confirms persistence. Click empty 10am slot — new task form opens with pre-filled start time. Resize a task block to 2 hours — duration updates.

## Must-Haves

- bpkm:TaskShape has `bpkm:scheduledStart` (xsd:dateTime), `bpkm:scheduledEnd` (xsd:dateTime), `bpkm:estimatedDuration` (xsd:string, ISO 8601 duration) properties
- Ontology declares all 3 new DatatypeProperty entries with domain bpkm:Task
- basic-pkm manifest version bumped to 2.2.0
- Calendar data endpoint returns Tasks with scheduledStart alongside Events with schema:startDate, merged into a single FullCalendar event list with `sourceType` annotation
- New PATCH-style endpoint (or extended data endpoint) accepts calendar drag/resize results and persists via `object.patch`
- FullCalendar initialized with `editable: true`, `selectable: true`; `eventDrop`, `eventResize`, `select` handlers wired
- CSS color coding distinguishes Tasks from Events on the calendar
- `_detect_date_fields()` returns `scheduledStart`/`scheduledEnd` for Task type (scheduledStart is higher priority than dueDate for start field detection)

## Proof Level

- This slice proves: contract, integration
- Real runtime required: yes (FullCalendar CDN, triplestore queries)
- Human/UAT required: yes (drag/resize feel)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py tests/test_calendar_editable.py -v` — all pass
- `python3 -c "import json; d=json.load(open('models/basic-pkm/shapes/basic-pkm.jsonld')); props=[p for ps in d['@graph'] if ps.get('rdfs:label')=='Task Shape' for p in ps.get('sh:property',[]) if 'scheduled' in str(p.get('sh:path',{}).get('@id','')) or 'estimated' in str(p.get('sh:path',{}).get('@id',''))]; assert len(props)==3"` — exits 0 (shapes integrity check)
- `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v -k "invalid_iri or unsupported_type or no_dates"` — failure-path tests pass (400 status for invalid IRI, unsupported type, missing dates)
- Manual: open calendar in Docker stack, confirm drag/resize/select work and persist

## Observability / Diagnostics

- Runtime signals: `[calendar]` prefixed console.log for drag/resize/select outcomes; backend `execute_calendar_query` logs event count per type
- Inspection surfaces: browser dev tools Network tab shows PATCH request with new dates; `/browser/views/generic/calendar/data?type=...` returns merged event list
- Failure visibility: fetch errors surface as toast via `showToast()` + console.error; backend logs warning on query/patch failure
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `backend/app/commands/handlers/object_patch.py` (existing), `backend/app/commands/router.py` (existing command dispatch), `backend/app/views/service.py` (existing calendar query), FullCalendar 6.1.17 CDN (existing)
- New wiring introduced: calendar PATCH endpoint in views router, merged multi-type calendar query in service, editable calendar handlers in template
- What remains before the milestone is truly usable end-to-end: S03 (cross-panel drag from kanban), S04 (recurring task expansion on calendar)

## Tasks

- [x] **T01: Add scheduledStart/scheduledEnd/estimatedDuration to Task schema and ontology** `est:30m`
  - Why: All calendar time-blocking depends on Tasks having scheduling properties. This is the foundational data model change.
  - Files: `models/basic-pkm/shapes/basic-pkm.jsonld`, `models/basic-pkm/ontology/basic-pkm.jsonld`, `models/basic-pkm/manifest.yaml`
  - Do: Add 3 properties to TaskShape in the Dates group (scheduledStart order 5.1, scheduledEnd order 5.2, estimatedDuration order 5.3 — between existing dueDate at 6 and completedDate at 7). Add matching OWL DatatypeProperty declarations in ontology. Bump manifest version to 2.2.0. Ensure `_detect_date_fields()` will prefer scheduledStart over dueDate for start field (scheduledStart contains "startdate" which is highest priority in `_START_DATE_PRIORITY`).
  - Verify: `python3 -c "import json; d=json.load(open('models/basic-pkm/shapes/basic-pkm.jsonld')); props=[p for ps in d['@graph'] if ps.get('rdfs:label')=='Task Shape' for p in ps.get('sh:property',[]) if 'scheduled' in str(p.get('sh:path',{}).get('@id','')) or 'estimated' in str(p.get('sh:path',{}).get('@id',''))]; assert len(props)==3, f'Expected 3, got {len(props)}'"` passes
  - Done when: shapes file has 3 new properties on TaskShape, ontology has 3 new DatatypeProperty entries, manifest says 2.2.0

- [x] **T02: Extend backend calendar data endpoint with merged Task+Event query and PATCH handler** `est:1h30m`
  - Why: The calendar currently queries one type at a time. To show Tasks and Events together, the backend needs a merged query mode. Drag/resize interactions need a server endpoint to persist the new dates.
  - Files: `backend/app/views/service.py`, `backend/app/views/router.py`
  - Do: (1) Add `execute_merged_calendar_query()` to ViewSpecService that queries both Event and Task types, merges results, and annotates each event with `sourceType: "task"|"event"`. Use `_detect_date_fields()` for each type. (2) Extend `generic_view_data()` to accept `merged=true` query param — when set, runs the merged query regardless of single type filter. (3) Add a POST endpoint `/browser/views/calendar/patch` that accepts `{iri, scheduledStart?, scheduledEnd?, estimatedDuration?}` and issues an `object.patch` command via the existing command dispatch. (4) Update `calendar_view.html` context to pass the merged data URL when type filter is blank or "all".
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v` — merged query and patch handler tests pass
  - Done when: `/browser/views/generic/calendar/data?merged=true` returns events from both Event and Task types with `sourceType` field; POST to `/browser/views/calendar/patch` with valid IRI+dates returns 200 and persists

- [x] **T03: Make FullCalendar editable with drag/resize/select handlers and task/event color coding** `est:1h30m`
  - Why: The calendar template currently creates a read-only FullCalendar. This task adds all interactive behavior and visual differentiation.
  - Files: `backend/app/templates/browser/calendar_view.html`, `frontend/static/css/views.css`
  - Do: (1) Add `editable: true`, `selectable: true` to Calendar config. (2) Add `eventDrop` handler that POSTs new start/end to `/browser/views/calendar/patch`, shows toast on success/failure. (3) Add `eventResize` handler (same pattern). (4) Add `select` handler that opens the object creation form with pre-filled scheduledStart/scheduledEnd via `openCreateForm()` or similar workspace API. (5) Add `eventClassNames` callback that returns CSS class based on `event.extendedProps.sourceType` (task vs event). (6) In views.css, add `.fc-event-task` and `.fc-event-event` color classes using the existing bpkm icon colors (task: #10b981 green, event: #8b5cf6 purple). (7) Update the `calendar_data_url` construction to include `merged=true` when appropriate. (8) Add event duration display via `displayEventTime: true`.
  - Verify: Load calendar page in browser at `http://localhost:3901/browser/views/generic?renderer=calendar`, confirm FullCalendar renders with editable=true (events show resize handles, empty slots are clickable)
  - Done when: Calendar renders with drag handles on events, resize cursors at event edges, click-to-select on empty slots; task events colored green, event events colored purple

- [x] **T04: Unit tests for merged calendar query, PATCH endpoint, and date field detection with scheduling properties** `est:45m`
  - Why: Verifies the new backend behavior contractually — merged query returns both types, PATCH persists dates, and scheduledStart is preferred over dueDate for Task date detection.
  - Files: `backend/tests/test_calendar_editable.py`
  - Do: (1) Test `_detect_date_fields()` with Task type that has both scheduledStart and dueDate — scheduledStart must win as start field, scheduledEnd must be detected as end field. (2) Test `execute_merged_calendar_query()` with mock bindings from both Event and Task — verify merged list with sourceType annotations. (3) Test the PATCH endpoint handler — mock command dispatch, verify correct object.patch payload. (4) Test edge cases: Task with no scheduledStart falls back to dueDate; merged query with no Tasks returns only Events; PATCH with invalid IRI returns 400.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v` — all tests pass, 0 failures
  - Done when: All tests in test_calendar_editable.py pass; covers merged query, PATCH handler, and updated date field detection

## Files Likely Touched

- `models/basic-pkm/shapes/basic-pkm.jsonld`
- `models/basic-pkm/ontology/basic-pkm.jsonld`
- `models/basic-pkm/manifest.yaml`
- `backend/app/views/service.py`
- `backend/app/views/router.py`
- `backend/app/templates/browser/calendar_view.html`
- `frontend/static/css/views.css`
- `backend/tests/test_calendar_editable.py`
