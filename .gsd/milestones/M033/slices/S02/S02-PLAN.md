# S02: Calendar View Renderer

**Goal:** Users can open a Calendar View from the VIEWS explorer and see temporal objects (Events, Projects, Tasks) on a FullCalendar month grid with type filtering, click-to-open, and month/week/day switching.
**Demo:** User opens "Calendar" from VIEWS explorer, sees bpkm:Event objects on a FullCalendar month grid. Clicking an event opens the object tab. Type filter pills narrow displayed events. Switching to week/day view works.

## Must-Haves

- Calendar registered in `RENDERER_REGISTRY` and `_VALID_RENDERERS`
- Date property auto-detection from SHACL shapes (xsd:date, xsd:dateTime, plus well-known path names)
- Calendar data JSON endpoint returning FullCalendar-compatible event objects
- FullCalendar 6.x vendored via build.js with CDN fallback
- `calendar_view.html` template with FullCalendar init, type filter pills, view toolbar
- `calendar.js` init function with event click → openTab(), month/week/day switching
- Dark mode support via `--fc-*` CSS custom property overrides
- Explorer sidebar entry for Calendar View
- `openGenericViewTab('calendar')` label registered in workspace.js
- Saved view support (automatic from toolbar inclusion)

## Proof Level

- This slice proves: operational
- Real runtime required: yes (SPARQL queries against triplestore with seed data)
- Human/UAT required: no (unit tests + manual browser verification)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` — all tests pass
- Calendar view renders in browser at `/browser/views/generic/calendar` with seed Event data
- FullCalendar JS loads from vendored bundle (check `manifest.json` has `fullcalendar.js` entry)
- Click event on calendar → object tab opens
- Type filter pills switch displayed objects
- Month/week/day view buttons work
- Dark mode renders correctly (no white flashes)
- Failure path: `/browser/views/generic/calendar/data?type=urn:nonexistent:Type` returns empty JSON array `[]` (not 500)

## Observability / Diagnostics

- Runtime signals: `generic_view: renderer=calendar` and `execute_calendar_query` log lines at INFO level
- Inspection surfaces: `/browser/views/generic/calendar/data?type=<iri>` JSON endpoint returns event array
- Failure visibility: Empty calendar with "No events found" message when no date properties detected; error logged when SPARQL fails

## Integration Closure

- Upstream surfaces consumed: `RENDERER_REGISTRY` (registry.py), `_VALID_RENDERERS` (router.py), `ViewSpecService` (service.py), `ShapesService.get_form_for_type()`, `scope_to_current_graph()`, `openGenericViewTab()` (workspace.js), `view_toolbar.html` + `type_filter_pills.html` includes, `build.js` vendor pipeline
- New wiring introduced in this slice: `"calendar"` entry in registry, `elif renderer == "calendar"` branch in generic_view(), `/browser/views/generic/calendar/data` endpoint, explorer sidebar tree-leaf, FullCalendar vendor bundle in build pipeline
- What remains before the milestone is truly usable end-to-end: nothing for calendar — S02 is self-contained

## Tasks

- [x] **T01: Backend — register calendar renderer, date detection, data endpoint** `est:2h`
  - Why: Core backend wiring — registers the calendar renderer, adds date property auto-detection from SHACL shapes, builds the calendar SPARQL query, and adds the JSON data endpoint. Without this, the frontend has nothing to render.
  - Files: `backend/app/views/registry.py`, `backend/app/views/router.py`, `backend/app/views/service.py`
  - Do: (1) Add `"calendar"` to `RENDERER_REGISTRY` with template `browser/calendar_view.html`. (2) Add `"calendar"` to `_VALID_RENDERERS`. (3) Add `_detect_date_fields(type_iri)` to `ViewSpecService` — scans SHACL shapes for `xsd:date`/`xsd:dateTime` datatype properties, plus well-known path matching (`schema:startDate` > `bpkm:dueDate` > `dcterms:created` for start; `schema:endDate` > `bpkm:completedDate` for end). (4) Add `_build_calendar_select()` static method — builds SELECT query for `?s ?label ?startDate ?endDate ?type`. (5) Add `execute_calendar_query()` — runs query, transforms bindings to FullCalendar JSON format `{id, title, start, end, extendedProps: {iri, type}}`. (6) Add `elif renderer == "calendar"` branch in `generic_view()` — detects date fields, renders template with metadata. (7) Extend the `/browser/views/generic/{renderer}/data` endpoint to handle `renderer == "calendar"` — returns JSON array of calendar events.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` passes
  - Done when: Calendar data endpoint returns valid FullCalendar JSON for types with date properties; date detection finds `schema:startDate`/`schema:endDate` on Event shape

- [x] **T02: Frontend — vendor FullCalendar, template, JS, CSS, explorer entry** `est:2h`
  - Why: All frontend work — vendors the FullCalendar library, creates the template that renders the calendar, writes the JS init function, adds CSS (including dark mode), and wires the explorer sidebar entry.
  - Files: `frontend/package.json`, `frontend/build.js`, `backend/app/templates/browser/calendar_view.html`, `frontend/static/js/calendar.js`, `frontend/static/css/views.css`, `backend/app/templates/browser/views_explorer.html`, `frontend/static/js/workspace.js`
  - Do: (1) Add `"fullcalendar": "^6.1.20"` to `frontend/package.json` dependencies. (2) Add FullCalendar build section in `build.js` after chart.js — read `fullcalendar/index.global.min.js`, content-hash, write to dist, add `fullcalendar.js` manifest entry. No CSS needed (v6 self-injects). (3) Create `calendar_view.html` — `.view-flex-column` wrapper, include `type_filter_pills.html` + `view_toolbar.html`, FullCalendar container div, inline script with `tryInit()` polling pattern (same as graph_view.html). Load FullCalendar via `{{ 'fullcalendar.js' | asset_url }}` with CDN fallback. (4) Create `calendar.js` — `initCalendar(containerId, dataUrl, options)` function: creates `new FullCalendar.Calendar()` with dayGridMonth/timeGridWeek/timeGridDay header buttons, `eventClick` → `openTab(iri, title)`, auto-refetch on type filter change. (5) Append calendar CSS to `views.css` — `.calendar-container` styles, dark mode overrides for `--fc-*` custom properties. (6) Add Calendar View tree-leaf to `views_explorer.html` with `onclick="openGenericViewTab('calendar')"` and canvas drag support. (7) Add `calendar: 'Calendar View'` to the `labels` dict in `openGenericViewTab()` in `workspace.js`.
  - Verify: `cd frontend && npm ci && node build.js` succeeds; `grep fullcalendar dist/manifest.json` shows entry; calendar view renders at `/browser/views/generic/calendar`
  - Done when: Calendar renders FullCalendar grid with events from data endpoint; clicking event opens object tab; type pills filter; month/week/day buttons switch view; dark mode uses correct colors

- [x] **T03: Unit tests for date detection and calendar query builder** `est:1h`
  - Why: Ensures date property detection and SPARQL query building work correctly across all shape configurations. Follows the test_kanban.py pattern.
  - Files: `backend/tests/test_calendar.py`
  - Do: Create `test_calendar.py` following `test_kanban.py` structure: (1) Test `_detect_date_fields()` — Event shape with schema:startDate/endDate, Task shape with bpkm:dueDate, type with only dcterms:created, type with no date properties, type with xsd:dateTime datatype. (2) Test `_build_calendar_select()` — verify query structure with type, with scope filter, without end date. (3) Test `execute_calendar_query()` — mock SPARQL bindings, verify FullCalendar JSON output format, empty results, deduplication.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` — all tests pass
  - Done when: ≥10 unit tests covering date detection priority, query building, and result transformation

## Files Likely Touched

- `backend/app/views/registry.py`
- `backend/app/views/router.py`
- `backend/app/views/service.py`
- `backend/app/templates/browser/calendar_view.html`
- `backend/app/templates/browser/views_explorer.html`
- `frontend/static/js/calendar.js`
- `frontend/static/js/workspace.js`
- `frontend/static/css/views.css`
- `frontend/package.json`
- `frontend/build.js`
- `backend/tests/test_calendar.py`
