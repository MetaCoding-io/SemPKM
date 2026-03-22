# S03: Cross-View Drag & Composable Planning

**Goal:** External drag from kanban/explorer to calendar schedules a task; views share scope context so filtering one propagates to siblings in dockview.
**Demo:** Open kanban + calendar side by side. Drag task card from kanban to calendar 2pm slot — task appears as a calendar block with scheduledStart persisted. Change scope filter in calendar — kanban re-renders with matching scope.

## Must-Haves

- Kanban cards carry `data-title` and set `text/iri` + `text/label` MIME types on dragstart (aligning with explorer tree drag pattern)
- Calendar accepts external drops via FullCalendar `droppable: true` + `drop` callback with `window.__calendarDragPayload` side-channel
- Drop handler computes scheduledStart from FullCalendar drop target date, defaults to 1-hour duration, calls existing `/browser/views/calendar/patch` endpoint
- Calendar JS extracted from inline `<script>` in `calendar_view.html` to `frontend/static/js/calendar.js` with `window._sempkmCalendar` reference for external control
- Calendar listens for `sempkm:command-executed` and calls `refetchEvents()` to reflect external mutations
- New `sempkm:scope-changed` custom event dispatched by view toolbar scope select; calendar and kanban listen and re-fetch with updated scope
- Panel identity via closest `.dv-panel` ancestor prevents self-triggered scope loops
- E2E test verifying cross-view drag scheduling persists via SPARQL and scope propagation works

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Docker stack with FullCalendar CDN, kanban, dockview)
- Human/UAT required: yes (drag feel, visual feedback)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_cross_view_drag.py -v` — unit tests for scope event dispatch logic and calendar drop handler data flow
- `npx playwright test e2e/tests/02-views/cross-view-drag.spec.ts --headed` — E2E: kanban→calendar drag scheduling + scope propagation
- Manual: open two views side by side, drag a kanban card to calendar, confirm block appears at correct time; change scope select in one view, confirm sibling updates

## Observability / Diagnostics

- Runtime signals: `[calendar] external drop:` console log with IRI + computed start/end on every external drop; `[scope] propagated:` log on scope change dispatch
- Inspection surfaces: `window._sempkmCalendar` reference for dev console inspection; `document.addEventListener('sempkm:scope-changed', e => console.log(e.detail))` for debugging scope sync
- Failure visibility: calendar `drop` handler logs error + shows toast on PATCH failure; `patchCalendarEvent` already logs `[calendar] ... patch failed:` with error details from S01
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: S01's editable calendar (`calendar_view.html` inline script), S01's PATCH endpoint (`/browser/views/calendar/patch`), kanban drag handlers (`kanban.js`), explorer tree drag (`tree_children.html`), canvas side-channel pattern (`canvas.js`)
- New wiring introduced: `sempkm:scope-changed` custom event connecting view toolbar to all view renderers; `window.__calendarDragPayload` side-channel from kanban/tree drag sources to calendar drop target
- What remains before the milestone is truly usable end-to-end: S04 (recurring tasks), S05 (templates/workflows) — both independent of cross-view drag

## Tasks

- [x] **T01: Extract calendar.js, add external drop handler, enrich kanban drag data** `est:45m`
  - Why: The calendar is currently an inline IIFE with no external reference — can't call `refetchEvents()` from outside, can't add droppable support cleanly. Kanban cards lack title/label data in drag payloads. This task makes calendar externally controllable and wires up the full drop→patch→display pipeline.
  - Files: `frontend/static/js/calendar.js`, `frontend/static/js/kanban.js`, `backend/app/templates/browser/calendar_view.html`, `backend/app/templates/browser/kanban_view.html`, `frontend/static/css/views.css`
  - Do: (1) Extract calendar inline script to `calendar.js` as an IIFE exporting `window.initCalendar(el, dataUrl)` and storing the FullCalendar instance as `window._sempkmCalendar`. (2) Add `droppable: true` and `drop(info)` callback that reads IRI/title from `window.__calendarDragPayload` side-channel (same pattern as canvas.js), computes scheduledStart from `info.date`, defaults 1hr duration for scheduledEnd, calls existing `patchCalendarEvent` logic. (3) Add `sempkm:command-executed` listener that calls `calendar.refetchEvents()`. (4) In kanban.js `dragstart`: set `text/iri` + `text/label` MIME types, set `window.__calendarDragPayload = { iri, title }`. (5) In kanban_view.html: add `data-title="{{ item.label }}"` to `.kanban-card`. (6) In calendar_view.html: replace inline script with `<script src="/static/js/calendar.js">` + `initCalendar(...)` call. (7) CSS: external drop visual feedback (`.calendar-external-drop-active` class or FullCalendar's built-in `.fc-highlight`).
  - Verify: `grep -q "droppable.*true" frontend/static/js/calendar.js && grep -q "__calendarDragPayload" frontend/static/js/calendar.js && grep -q "text/iri" frontend/static/js/kanban.js && grep -q "data-title" backend/app/templates/browser/kanban_view.html`
  - Done when: Calendar accepts drops from kanban and explorer tree, creates a scheduled event via PATCH, shows it immediately via `addEvent()`, and the inline script in calendar_view.html is replaced by an external JS file.

- [x] **T02: Scope change propagation between views via sempkm:scope-changed event** `est:30m`
  - Why: Views currently operate in isolation — changing the scope select in one view doesn't affect siblings. This task wires a `sempkm:scope-changed` custom event so all open views can synchronize their data source to the same scope query.
  - Files: `frontend/static/js/workspace.js`, `frontend/static/js/calendar.js`, `frontend/static/js/kanban.js`, `backend/app/templates/browser/view_toolbar.html`
  - Do: (1) In view_toolbar.html: scope select `onchange` dispatches `new CustomEvent('sempkm:scope-changed', { detail: { scopeQuery: this.value, renderer, selectedType, sourcePanel } })` on `document` in addition to calling `applyScopeQuery()`. (2) sourcePanel computed as `this.closest('.dv-panel')?.id || ''`. (3) In calendar.js: register `sempkm:scope-changed` listener — if `sourcePanel` differs from own panel ID, re-fetch calendar data with new scope param by calling `calendar.removeAllEvents()` + fetch + `addEvent()` loop. (4) In kanban.js: register `sempkm:scope-changed` listener — if source differs, trigger htmx re-swap of the kanban board with updated scope_query param. (5) In workspace.js: update `applyScopeQuery` to also dispatch the event (centralizing dispatch point). Panel self-skip via comparing `sourcePanel` to own `.dv-panel` ancestor ID.
  - Verify: `grep -q "sempkm:scope-changed" frontend/static/js/workspace.js && grep -q "sempkm:scope-changed" frontend/static/js/calendar.js && grep -q "sempkm:scope-changed" frontend/static/js/kanban.js`
  - Done when: Changing scope select in calendar view triggers kanban re-fetch with same scope, and vice versa. Self-triggered scope changes are skipped via panel ID comparison.

- [ ] **T03: E2E test for cross-view drag and scope propagation** `est:35m`
  - Why: Verifies the integration contract — external drag scheduling persists correctly and scope sync works across panels. HTML5 DnD is hard to simulate in Playwright so the test exercises the drop handler directly via `page.evaluate()`.
  - Files: `e2e/tests/02-views/cross-view-drag.spec.ts`, `e2e/helpers/selectors.ts`, `backend/tests/test_cross_view_drag.py`
  - Do: (1) Add selectors to `SEL.views` if needed (e.g. `calendarDropZone`). (2) Write Playwright spec: seed a Task via API, open kanban + calendar side by side using `openGenericViewTab()`, verify kanban card visible, simulate drop by calling `window.__calendarDragPayload = { iri, title }` + invoke calendar drop handler via `page.evaluate()` with synthetic date, verify `scheduledStart` persisted via SPARQL API or the calendar PATCH response. (3) Test scope propagation: change scope select in one view, verify sibling view receives the event and updates (check that htmx request was made or DOM updated). (4) Write `backend/tests/test_cross_view_drag.py` with unit tests: scope event detail structure, calendar drop data computation (date + 1hr default), side-channel payload format.
  - Verify: `npx playwright test e2e/tests/02-views/cross-view-drag.spec.ts` passes; `cd backend && .venv/bin/python -m pytest tests/test_cross_view_drag.py -v` passes
  - Done when: E2E test proves external drag→calendar scheduling persists and scope change propagates between panels. Unit tests cover drop data computation logic.

## Files Likely Touched

- `frontend/static/js/calendar.js` (new — extracted from inline template script)
- `frontend/static/js/kanban.js` (modify — drag data enrichment + scope listener)
- `frontend/static/js/workspace.js` (modify — scope event dispatch)
- `backend/app/templates/browser/calendar_view.html` (modify — replace inline script with external JS)
- `backend/app/templates/browser/kanban_view.html` (modify — add data-title to cards)
- `backend/app/templates/browser/view_toolbar.html` (modify — scope change event dispatch)
- `frontend/static/css/views.css` (modify — drop zone visual feedback)
- `e2e/tests/02-views/cross-view-drag.spec.ts` (new)
- `e2e/helpers/selectors.ts` (modify — add new selectors)
- `backend/tests/test_cross_view_drag.py` (new)
