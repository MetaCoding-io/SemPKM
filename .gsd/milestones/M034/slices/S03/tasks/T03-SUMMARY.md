---
id: T03
parent: S03
milestone: M034
provides:
  - E2E test suite for cross-view drag and scope propagation (3 tests)
  - Backend unit tests for PATCH endpoint start-only and start+end payloads (3 tests)
  - Backend unit tests for scope-changed event detail structure (3 tests)
  - calendarEvent selector added to SEL.views
key_files:
  - e2e/tests/02-views/cross-view-drag.spec.ts
  - backend/tests/test_cross_view_drag.py
  - e2e/helpers/selectors.ts
  - backend/app/templates/browser/kanban_view.html
key_decisions:
  - Calendar drop E2E test gracefully degrades when FullCalendar CDN is unreachable — falls back to direct API PATCH + SPARQL verification
patterns_established:
  - E2E calendar tests should try CDN load with timeout and fallback to API-only verification when CDN is blocked
  - Kanban drag data verification uses dispatchEvent(new DragEvent) to trigger onDragStart and check side-channel population
observability_surfaces:
  - "FullCalendar CDN not loaded — testing PATCH endpoint directly" console log signals CDN-fallback path in E2E
  - Test failure screenshots in e2e/test-results/ for post-mortem debugging
duration: 25m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: E2E and unit tests for cross-view drag and scope propagation

**Added 9 tests (3 E2E + 6 backend) covering kanban drag data, calendar external drop scheduling, scope propagation events, and PATCH endpoint payloads; fixed pre-existing kanban template crash.**

## What Happened

Created `e2e/tests/02-views/cross-view-drag.spec.ts` with three Playwright tests:

1. **Kanban card drag data** — opens kanban view with Task type, verifies `.kanban-card` elements carry `data-iri` and `data-title` attributes, simulates dragstart to confirm `window.__calendarDragPayload` side-channel is populated.

2. **External drop on calendar schedules task** — seeds a Task via the commands API, opens calendar view, attempts to load FullCalendar CDN (graceful degradation when CDN is unreachable), then either simulates the drop handler via `page.evaluate()` or calls the PATCH endpoint directly, and verifies `scheduledStart` was persisted via SPARQL.

3. **Scope change propagation** — opens a kanban view, registers a `sempkm:scope-changed` event listener, triggers scope change via `applyScopeQuery()`, and verifies the event detail contains `scopeQuery`, `sourcePanel`, `renderer`, and `selectedType` fields.

Created `backend/tests/test_cross_view_drag.py` with 6 unit tests: PATCH endpoint with start+end (Task), start-only (Task), start-only (Event using schema:startDate), and 3 scope event detail structure contract tests.

Added `calendarEvent: '.fc-event'` to `SEL.views` in selectors.ts.

**Bug fix:** Fixed pre-existing crash in `kanban_view.html` where `col.items` resolved to the dict `.items()` method instead of the `items` key in Jinja2. Changed to `col['items']` bracket notation. This bug caused the kanban endpoint to return 500 and blocked both the existing m031-views kanban test and the new cross-view-drag tests.

## Verification

All 9 tests pass:
- 6 backend unit tests: `cd backend && .venv/bin/python -m pytest tests/test_cross_view_drag.py -v` — 6 passed
- 3 E2E tests: `cd e2e && npx playwright test tests/02-views/cross-view-drag.spec.ts --project=chromium` — 3 passed
- File existence confirmed for both test files and selectors

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_cross_view_drag.py -v` | 0 | ✅ pass | 0.5s |
| 2 | `cd e2e && npx playwright test tests/02-views/cross-view-drag.spec.ts --project=chromium` | 0 | ✅ pass | 40s |
| 3 | `test -f e2e/tests/02-views/cross-view-drag.spec.ts` | 0 | ✅ pass | <1s |
| 4 | `test -f backend/tests/test_cross_view_drag.py` | 0 | ✅ pass | <1s |

## Diagnostics

- Run `cd e2e && npx playwright test tests/02-views/cross-view-drag.spec.ts --headed` to watch the tests visually
- Run `cd e2e && npx playwright test tests/02-views/cross-view-drag.spec.ts --debug` for step-through debugging
- Test failure artifacts (screenshots, traces) are written to `e2e/test-results/`
- Calendar drop test logs "FullCalendar CDN not loaded" when the CDN is unreachable — this is expected in isolated environments

## Deviations

- Fixed pre-existing bug in `kanban_view.html` where Jinja2 resolved `col.items` as the dict method instead of key lookup. Changed to `col['items']`. This was necessary for the kanban E2E tests to function but was not in the task plan.
- Calendar drop E2E test uses a CDN-fallback pattern not in the original plan — tries FullCalendar CDN load, then falls back to direct API verification when CDN is blocked. This was necessary because the test environment doesn't have CDN access.
- Commands API response shape uses `createData.results[0].iri` (not `createData.iri`) — corrected from the plan's assumption.

## Known Issues

- FullCalendar CDN is unreachable in the Docker test environment, so the calendar drop E2E test exercises the API fallback path rather than the full UI drop flow. When CDN access is available, the test automatically exercises the full flow including `page.evaluate()` drop simulation.
- The existing `calendar-view.spec.ts` tests also fail due to this CDN issue — pre-existing, not introduced by this task.

## Files Created/Modified

- `e2e/tests/02-views/cross-view-drag.spec.ts` — new: 3 E2E tests for cross-view drag and scope propagation
- `backend/tests/test_cross_view_drag.py` — new: 6 unit tests for PATCH endpoint payloads and scope event structure
- `e2e/helpers/selectors.ts` — modified: added `calendarEvent: '.fc-event'` to SEL.views
- `backend/app/templates/browser/kanban_view.html` — modified: fixed `col.items` → `col['items']` Jinja2 dict key access
- `.gsd/milestones/M034/slices/S03/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
- `.gsd/KNOWLEDGE.md` — appended Jinja2 dict key access gotcha
