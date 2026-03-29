# S05: Calendar, Recurring Tasks & Setup Wizard Fixes — UAT

**Milestone:** M046
**Written:** 2026-03-29T03:31:38.790Z

## UAT: Calendar, Recurring Tasks & Setup Wizard Fixes

### Preconditions
- Docker test stack running (`docker compose -f docker-compose.test.yml up -d`)
- Stack is NOT freshly created (setup already completed)

### Test 1: Calendar View Renders
1. Run: `cd e2e && npx playwright test tests/02-views/calendar-view.spec.ts --project=chromium --reporter=list`
2. **Expected:** 3 passed, 0 failed
3. Verify: FullCalendar `.fc` container renders, merged mode works without type filter, month/week/day switching works

### Test 2: Recurring Tasks on Calendar
1. Run: `cd e2e && npx playwright test tests/02-views/recurring-tasks.spec.ts --project=chromium --reporter=list`
2. **Expected:** 2 passed, 0 failed
3. Verify: RRULE FREQ=WEEKLY;COUNT=4 produces ≥2 visible events with `.fc-event-recurring` class, clicking virtual event opens master task tab

### Test 3: Cross-View Drag
1. Run: `cd e2e && npx playwright test tests/02-views/cross-view-drag.spec.ts --project=chromium --reporter=list`
2. **Expected:** 3 passed, 0 failed
3. Verify: Kanban card has drag data, external drop on calendar schedules task, scope change fires event

### Test 4: Setup Wizard (Non-Fresh Stack)
1. Run: `cd e2e && npx playwright test tests/00-setup/01-setup-wizard.spec.ts --project=chromium --reporter=list`
2. **Expected:** 5 skipped, 2 passed, 0 failed
3. Verify: Tests 1-5 skip with "Setup already completed" message, tests 6-7 pass

### Test 5: All Four Suites Combined
1. Run from project root: `npx playwright test e2e/tests/02-views/calendar-view.spec.ts e2e/tests/02-views/recurring-tasks.spec.ts e2e/tests/02-views/cross-view-drag.spec.ts e2e/tests/00-setup/01-setup-wizard.spec.ts --reporter=list`
2. **Expected:** 20 passed, 10 skipped, 0 failed (both chromium + firefox)

### Edge Cases
- **Fresh stack:** Setup wizard tests 1-5 should pass (not skip) on `docker compose down -v && docker compose up -d`
- **No bare globals:** `rg 'typeof initCalendar[^.]|typeof openTab[^.]|typeof showToast[^.]' frontend/static/js/calendar.js backend/app/templates/browser/calendar_view.html` returns 0 results
