---
estimated_steps: 41
estimated_files: 4
skills_used: []
---

# T02: Run E2E tests and verify calendar + setup wizard pass

## Description

Run the four affected E2E test files against the Docker test stack to prove the namespace fixes and skip logic work. This is the slice's acceptance gate.

The Docker test stack should already be running (prior slices in M046 used it). If not, start it with `docker compose -f docker-compose.test.yml up -d`.

## Steps

1. Ensure the Docker test stack is running:
   - `docker compose -f docker-compose.test.yml ps` — all containers should be Up
   - If not running: `docker compose -f docker-compose.test.yml up -d` and wait for healthy

2. Run calendar view tests:
   - `cd /home/james/Code/SemPKM && npx playwright test e2e/tests/02-views/calendar-view.spec.ts --reporter=list`
   - All tests must pass (expect 3 passes)

3. Run recurring tasks tests:
   - `cd /home/james/Code/SemPKM && npx playwright test e2e/tests/02-views/recurring-tasks.spec.ts --reporter=list`
   - Both tests must pass

4. Run cross-view drag tests:
   - `cd /home/james/Code/SemPKM && npx playwright test e2e/tests/02-views/cross-view-drag.spec.ts --reporter=list`
   - The 'external drop on calendar' test (test 2) must pass — it depends on the calendar booting

5. Run setup wizard tests:
   - `cd /home/james/Code/SemPKM && npx playwright test e2e/tests/00-setup/01-setup-wizard.spec.ts --reporter=list`
   - On a non-fresh stack: 5 skipped, 2 passed, 0 failed
   - On a fresh stack: 7 passed, 0 failed

6. If any test fails, diagnose the failure output, fix the root cause in the source files from T01, and re-run until all pass.

## Must-Haves

- [ ] `calendar-view.spec.ts` — 0 failures
- [ ] `recurring-tasks.spec.ts` — 0 failures
- [ ] `cross-view-drag.spec.ts` — 0 failures (or only failures unrelated to calendar)
- [ ] `01-setup-wizard.spec.ts` — 0 failures (5 skipped on non-fresh stack)

## Verification

- All four `npx playwright test` commands exit with code 0
- No test reports 'failed' status in the output

## Inputs

- `backend/app/templates/browser/calendar_view.html` — fixed in T01
- `frontend/static/js/calendar.js` — fixed in T01
- `e2e/tests/00-setup/01-setup-wizard.spec.ts` — fixed in T01
- `e2e/tests/02-views/calendar-view.spec.ts` — existing test file to run
- `e2e/tests/02-views/recurring-tasks.spec.ts` — existing test file to run
- `e2e/tests/02-views/cross-view-drag.spec.ts` — existing test file to run

## Expected Output

- `e2e/tests/02-views/calendar-view.spec.ts` — verified passing
- `e2e/tests/02-views/recurring-tasks.spec.ts` — verified passing
- `e2e/tests/02-views/cross-view-drag.spec.ts` — verified passing
- `e2e/tests/00-setup/01-setup-wizard.spec.ts` — verified passing/skipping

## Inputs

- `backend/app/templates/browser/calendar_view.html`
- `frontend/static/js/calendar.js`
- `e2e/tests/00-setup/01-setup-wizard.spec.ts`
- `e2e/tests/02-views/calendar-view.spec.ts`
- `e2e/tests/02-views/recurring-tasks.spec.ts`
- `e2e/tests/02-views/cross-view-drag.spec.ts`

## Expected Output

- `e2e/tests/02-views/calendar-view.spec.ts`
- `e2e/tests/02-views/recurring-tasks.spec.ts`
- `e2e/tests/02-views/cross-view-drag.spec.ts`
- `e2e/tests/00-setup/01-setup-wizard.spec.ts`

## Verification

npx playwright test e2e/tests/02-views/calendar-view.spec.ts e2e/tests/02-views/recurring-tasks.spec.ts e2e/tests/02-views/cross-view-drag.spec.ts e2e/tests/00-setup/01-setup-wizard.spec.ts --reporter=list exits with code 0
