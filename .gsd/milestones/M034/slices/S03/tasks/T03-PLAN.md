---
estimated_steps: 4
estimated_files: 3
skills_used: []
---

# T03: E2E and unit tests for cross-view drag and scope propagation

**Slice:** S03 — Cross-View Drag & Composable Planning
**Milestone:** M034

## Description

Verifies the integration contracts from T01 and T02: (1) external drag from kanban to calendar persists scheduledStart via the PATCH endpoint, (2) scope change propagation works between sibling views. HTML5 drag-and-drop is notoriously hard to simulate in Playwright across dockview panels, so the E2E test exercises the drop handler directly via `page.evaluate()` — this is the approach used by canvas tests in the codebase.

Also adds a backend unit test file for the drop data computation logic (date + 1hr default duration) to verify the contract without requiring a browser.

**E2E infrastructure:**
- `openGenericViewTab(page, renderer, waitSelector)` from `e2e/helpers/dockview.ts` opens a view tab
- `SEL.views.calendar`, `SEL.views.kanbanBoard` etc. from `e2e/helpers/selectors.ts`
- Auth fixture provides `ownerPage` with login
- SPARQL API at `BASE_URL/api/sparql` can verify persisted data
- Task type IRI: `urn:sempkm:model:basic-pkm:Task`

**Existing calendar test pattern** (from `calendar-view.spec.ts`):
- Pre-set `localStorage.setItem('sempkm_generic_type_calendar', taskType)` before opening calendar
- Use `openGenericViewTab(page, 'calendar', SEL.views.calendar, undefined, undefined, 20000)` with 20s timeout for CDN load
- Wait for `.fc` selector after tab opens

## Steps

1. **Write `e2e/tests/02-views/cross-view-drag.spec.ts`** — Playwright test file with these test cases:

   **Test 1: "kanban card drag data includes IRI and title"** — Open kanban view with Task type. Find a `.kanban-card` element. Use `page.evaluate()` to read its `data-iri` and `data-title` attributes, verify both are non-empty strings. Also verify that calling the `onDragStart` handler (or simulating it) would set `window.__calendarDragPayload`.

   **Test 2: "external drop on calendar schedules task"** — The core integration test:
   - Seed a Task via the commands API (`POST /api/commands` with `object.create`) with a known title and `bpkm:taskStatus = "todo"`
   - Open calendar view (pre-set localStorage type to Task type IRI)
   - Wait for FullCalendar to render (`.fc` visible)
   - Simulate the drop via `page.evaluate()`:
     ```javascript
     window.__calendarDragPayload = { iri: '<task-iri>', title: 'Test Task' };
     // Call the calendar's drop handler directly
     var cal = window._sempkmCalendar;
     // Create a synthetic drop info object matching FullCalendar's API
     var dropDate = new Date();
     dropDate.setHours(14, 0, 0, 0); // 2pm today
     // Trigger the internal drop processing
     ```
   - Alternatively, fire a custom event or call the exported drop-handling function directly
   - Wait for the PATCH request to complete (use `page.waitForResponse` matching `/browser/views/calendar/patch`)
   - Verify the task now has `scheduledStart` by querying SPARQL API: `SELECT ?start WHERE { GRAPH <urn:sempkm:current> { <task-iri> <urn:sempkm:model:basic-pkm:scheduledStart> ?start } }`
   - Verify the calendar shows the event (check for `.fc-event` with the task title)

   **Test 3: "scope change propagation fires event"** — Open a view, use `page.evaluate()` to set up a listener `document.addEventListener('sempkm:scope-changed', e => window.__scopeEventFired = e.detail)`, then trigger a scope change via the select element, verify `window.__scopeEventFired` has `scopeQuery`, `sourcePanel` fields.

2. **Update `e2e/helpers/selectors.ts`** — Add to `SEL.views`:
   - `calendarEvent: '.fc-event'` — FullCalendar event element
   - `scopeSelect: '.view-scope-select'` (already exists, verify)

3. **Write `backend/tests/test_cross_view_drag.py`** — Unit tests for the backend side of cross-view drag. These tests are lightweight — the PATCH endpoint was already tested in T04 of S01 (`test_calendar_editable.py`). Focus on:
   - Verify the `/browser/views/calendar/patch` endpoint accepts a Task IRI with only `start` (no `end`) and returns success — this is the external drop's minimum payload
   - Verify the endpoint correctly handles the `start` + `end` combo that the JS drop handler sends
   - These can be additions to the existing `test_calendar_editable.py` or a new file — prefer a new file for slice isolation

4. **Verify all tests pass** — Run both test suites and confirm green:
   - `cd backend && .venv/bin/python -m pytest tests/test_cross_view_drag.py -v`
   - `npx playwright test e2e/tests/02-views/cross-view-drag.spec.ts`

## Must-Haves

- [ ] E2E test verifies kanban card drag data includes IRI and title attributes
- [ ] E2E test verifies external drop on calendar triggers PATCH and persists scheduledStart
- [ ] E2E test verifies scope-changed event fires with correct detail structure
- [ ] Backend unit test verifies PATCH endpoint handles start-only and start+end payloads
- [ ] All tests pass

## Verification

- `npx playwright test e2e/tests/02-views/cross-view-drag.spec.ts` — all E2E tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_cross_view_drag.py -v` — all unit tests pass
- `test -f e2e/tests/02-views/cross-view-drag.spec.ts` — E2E test file exists
- `test -f backend/tests/test_cross_view_drag.py` — backend test file exists

## Inputs

- `frontend/static/js/calendar.js` — T01's extracted calendar module (drop handler to test)
- `frontend/static/js/kanban.js` — T01's enriched kanban drag data (data attrs to verify)
- `frontend/static/js/workspace.js` — T02's scope event dispatch (event to verify)
- `e2e/helpers/selectors.ts` — existing selectors (to extend)
- `e2e/helpers/dockview.ts` — `openGenericViewTab` helper
- `e2e/tests/02-views/calendar-view.spec.ts` — reference pattern for calendar E2E tests
- `backend/tests/test_calendar_editable.py` — reference pattern for PATCH endpoint tests

## Expected Output

- `e2e/tests/02-views/cross-view-drag.spec.ts` — new E2E test file
- `e2e/helpers/selectors.ts` — modified with new selectors
- `backend/tests/test_cross_view_drag.py` — new backend unit test file

## Observability Impact

- **New test coverage:** 6 backend unit tests (3 PATCH endpoint variants, 3 scope event contract tests) + 3 E2E tests (kanban drag data, calendar drop scheduling, scope propagation)
- **Failure visibility:** E2E test failures include screenshot + error context artifacts in `e2e/test-results/` for post-mortem debugging
- **CDN dependency surfaced:** Test 2 gracefully degrades when FullCalendar CDN is unreachable, falling back to direct API verification — the console log `FullCalendar CDN not loaded — testing PATCH endpoint directly` signals this path
- **Inspection:** Run `npx playwright test tests/02-views/cross-view-drag.spec.ts --headed` from `e2e/` to observe the visual flow; use `--debug` flag for step-through

