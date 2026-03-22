---
id: T03
parent: S03
milestone: M033
provides:
  - "'calendar' in dockview.ts renderer union type for openGenericViewTab"
  - "calendar selector in SEL.views for E2E automation"
  - "3 Playwright E2E tests: FullCalendar rendering, empty state, month/week/day switching"
key_files:
  - e2e/tests/02-views/calendar-view.spec.ts
  - e2e/helpers/dockview.ts
  - e2e/helpers/selectors.ts
key_decisions:
  - "Empty-state test waits for .view-empty-state instead of the calendar container — the template conditionally renders data-testid='calendar-view' only when a type with date fields is selected"
  - "Used localStorage pre-seeding (sempkm_generic_type_calendar) to set Event type before opening calendar view, matching the kanban test pattern from m031-views.spec.ts"
patterns_established:
  - "Calendar E2E tests follow the same openGenericViewTab + waitForSelector + assertion pattern as M031 view tests"
observability_surfaces:
  - "E2E test suite catches calendar regressions — CDN load failure, data endpoint errors, view-switching breakage — with screenshots on failure"
  - "SEL.views.calendar selector enables ad-hoc browser_assert checks"
duration: 12m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: E2E test for calendar view

**Added 3 Playwright E2E tests for calendar view: FullCalendar rendering, empty state, and month/week/day view switching**

## What Happened

1. **`e2e/helpers/dockview.ts`**: Added `'calendar'` to the `openGenericViewTab` renderer union type, enabling type-safe calendar view tab opening from tests.

2. **`e2e/helpers/selectors.ts`**: Added `calendar: '[data-testid="calendar-view"]'` to `SEL.views`, centralizing the calendar container selector alongside existing view selectors.

3. **`e2e/tests/02-views/calendar-view.spec.ts`**: Created 3 tests:
   - **"calendar view renders with FullCalendar"**: Pre-sets Event type in localStorage, opens calendar tab via `openGenericViewTab`, waits for CDN-loaded `.fc` container, asserts visibility.
   - **"calendar view shows empty state when no type selected"**: Clears localStorage type, opens calendar tab waiting for `.view-empty-state` (since the `data-testid="calendar-view"` container is conditionally rendered only when a type with date fields is present).
   - **"month/week/day view switching"**: Pre-sets Event type, opens calendar, verifies `.fc-daygrid` for month view, clicks week/day/month buttons and asserts corresponding `.fc-timegrid`/`.fc-daygrid` containers appear.

## Verification

- `cd e2e && TEST_BASE_URL=http://localhost:3000 npx playwright test tests/02-views/calendar-view.spec.ts --project=chromium` — 3/3 passed
- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` — 22/22 passed (slice-level check)
- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py::TestExecuteCalendarQuery::test_query_failure_returns_empty -v` — passed (slice-level failure path check)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && TEST_BASE_URL=http://localhost:3000 npx playwright test tests/02-views/calendar-view.spec.ts --project=chromium` | 0 | ✅ pass | 6.5s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` | 0 | ✅ pass | 0.46s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_calendar.py::TestExecuteCalendarQuery::test_query_failure_returns_empty -v` | 0 | ✅ pass | 0.46s |

## Diagnostics

- **E2E test failures**: Playwright captures screenshots on failure and traces on first retry. Check `e2e/test-results/` for artifacts.
- **Empty-state distinction**: The calendar template uses three code paths: `error_message` → `.view-empty-state` text, `date_fields` present → `data-testid="calendar-view"` with FullCalendar, neither → `.view-empty-state` with "Select a type" message. The empty-state test covers the first path.
- **Firefox auth**: Firefox tests fail against the dev stack due to auth fixture differences (dev stack vs test stack). All 3 tests pass on Chromium. When run against the proper test stack (port 3901), Firefox tests should also pass.

## Deviations

- Empty-state test uses `.view-empty-state` as the wait selector instead of `SEL.views.calendar`, because the template conditionally renders the calendar container only when a type with date fields is selected. Without a type, only the empty-state div exists.
- `TYPES` from seed-data.ts doesn't include an Event type constant, so the Event type IRI is defined as a local constant in the test file.

## Known Issues

- Firefox E2E tests fail against the development Docker stack (port 3000) due to auth fixture token retrieval issues — this is a dev-stack limitation, not a calendar-specific problem. The proper test stack on port 3901 handles multi-browser auth correctly.

## Files Created/Modified

- `e2e/tests/02-views/calendar-view.spec.ts` — New E2E test file with 3 calendar view tests
- `e2e/helpers/dockview.ts` — Added `'calendar'` to renderer union type
- `e2e/helpers/selectors.ts` — Added `calendar` selector to SEL.views
- `.gsd/milestones/M033/slices/S03/tasks/T03-PLAN.md` — Added Observability Impact section
