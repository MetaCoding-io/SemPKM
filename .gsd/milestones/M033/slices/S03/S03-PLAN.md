# S03: Calendar View

**Goal:** Users can open a Calendar view that renders objects with date properties on a FullCalendar month/week/day grid, with event clicks opening object tabs.
**Demo:** Open Calendar View from explorer sidebar → select a type with date fields (Event, Project, Task) → see objects positioned on a FullCalendar grid → switch between month/week/day → click an event → object tab opens.

## Must-Haves

- `"calendar"` added to `_VALID_RENDERERS` in views/router.py
- `_detect_date_fields()` method on ViewSpecService that detects date properties via both `sh:datatype` and well-known path heuristics
- `/browser/views/generic/calendar/data` JSON endpoint returning FullCalendar-compatible event objects
- `calendar_view.html` template with lazy-loaded FullCalendar 6.x, type filter pills, view toolbar
- Dark mode FullCalendar CSS overrides in `views.css`
- Calendar entry in views explorer sidebar
- `calendar: 'Calendar View'` label in `openGenericViewTab()` workspace.js
- Empty states for no-type-selected and no-date-fields-detected
- Event click → `openTab(iri, label)` handler
- Unit tests for `_detect_date_fields` covering Event (no sh:datatype), Project (with sh:datatype), and Note (no dates)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` — all unit tests pass
- `npx playwright test e2e/tests/02-views/calendar-view.spec.ts` — E2E test passes
- Manual: open Calendar View → select Event type → month/week/day switching works → event click opens object tab

## Tasks

- [ ] **T01: Backend — date field detection, calendar query, router, and unit tests** `est:1h`
  - Why: The calendar view needs backend date-property detection from SHACL shapes, a SPARQL query builder for calendar events, the router branch in `generic_view()`, and a JSON data endpoint. Unit tests verify the date detection heuristic handles Event (no sh:datatype on dates), Project (with sh:datatype), and types with no date fields.
  - Files: `backend/app/views/service.py`, `backend/app/views/router.py`, `backend/tests/test_calendar.py`
  - Do: Add `_detect_date_fields()` to ViewSpecService using both `prop.datatype` checks and well-known path IRI matching. Add `_build_calendar_select()` and `execute_calendar_query()`. Add `"calendar"` to `_VALID_RENDERERS`. Add the `elif renderer == "calendar":` branch in `generic_view()`. Add `/generic/calendar/data` JSON endpoint. Write unit tests following `test_kanban.py` pattern.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` passes
  - Done when: All unit tests pass; the data endpoint returns FullCalendar-compatible JSON for a type with date fields and returns an error_message context for types without.

- [ ] **T02: Frontend — template, CSS, explorer entry, and workspace.js integration** `est:45m`
  - Why: The frontend needs the calendar_view.html template (lazy-loading FullCalendar 6 CDN), dark mode CSS overrides, the explorer sidebar entry, and the workspace.js label for `openGenericViewTab()`. This wires up everything the user interacts with.
  - Files: `backend/app/templates/browser/calendar_view.html`, `frontend/static/css/views.css`, `backend/app/templates/browser/views_explorer.html`, `frontend/static/js/workspace.js`
  - Do: Create `calendar_view.html` following kanban_view.html pattern (view-flex-column wrapper, type_filter_pills include, view_toolbar include, empty states, calendar container with data-testid, lazy-load FullCalendar script, eventClick handler calling openTab). Add `.calendar-container` CSS with `flex:1; min-height:0` and dark mode FullCalendar variable overrides. Add Calendar View entry in views_explorer.html. Add `calendar: 'Calendar View'` to workspace.js labels dict.
  - Verify: Start dev stack, open Calendar View from sidebar → FullCalendar renders → month/week/day switching works → click event opens object tab
  - Done when: Calendar view renders with proper styling in both light and dark modes; empty states display correctly; event clicks open object tabs.

- [ ] **T03: E2E test for calendar view** `est:30m`
  - Why: Automated verification that the full calendar view pipeline works: sidebar entry → FullCalendar rendering → view switching → event click → object tab opens.
  - Files: `e2e/tests/02-views/calendar-view.spec.ts`, `e2e/helpers/selectors.ts`, `e2e/helpers/dockview.ts`
  - Do: Add `'calendar'` to the `openGenericViewTab` renderer union type in dockview.ts. Add `calendar` selector to `SEL.views`. Write E2E spec covering: open calendar view → verify FullCalendar `.fc` container rendered → switch to week/day views → verify view changes → (if Event data exists) click event → verify object tab opens.
  - Verify: `npx playwright test e2e/tests/02-views/calendar-view.spec.ts` passes
  - Done when: E2E test passes covering calendar rendering, view switching, and event interaction.

## Files Likely Touched

- `backend/app/views/service.py`
- `backend/app/views/router.py`
- `backend/tests/test_calendar.py`
- `backend/app/templates/browser/calendar_view.html`
- `frontend/static/css/views.css`
- `backend/app/templates/browser/views_explorer.html`
- `frontend/static/js/workspace.js`
- `e2e/tests/02-views/calendar-view.spec.ts`
- `e2e/helpers/selectors.ts`
- `e2e/helpers/dockview.ts`
