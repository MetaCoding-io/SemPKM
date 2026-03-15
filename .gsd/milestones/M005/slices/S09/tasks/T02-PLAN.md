---
estimated_steps: 8
estimated_files: 3
---

# T02: Playwright E2E tests for operations log and model refresh

**Slice:** S09 — E2E Tests & Docs
**Milestone:** M005

## Description

Create Playwright E2E tests covering the operations log admin page (LOG-01) and model refresh button (MIG-01). Two spec files in `e2e/tests/25-ops-log/`: `ops-log.spec.ts` tests page rendering and filter, `model-refresh.spec.ts` tests the refresh button click workflow and ops log entry creation. Tests must account for the known basic-pkm JSON parsing error — the refresh test should assert that a response appears (success OR error message) rather than requiring success.

## Steps

1. Add `opsLog` selector group to `e2e/helpers/selectors.ts` — `table: '[data-testid="ops-log-table"]'`, `row: '.ops-log-row'`, `typeBadge: '.ops-log-type-badge'`, `filter: '#ops-log-filter'`, `status: '.ops-log-status'`
2. Create `e2e/tests/25-ops-log/ops-log.spec.ts` with imports from auth fixtures, selectors, and wait helpers
3. Write test 1 — "ops log page shows activities table": navigate to `/admin/ops-log`, wait for `[data-testid="ops-log-table"]`, assert the heading "Operations Log" is visible, assert the table has at least 1 row (basic-pkm install should have created ops log entries during test stack setup), assert each row has a type badge and status element
4. Write test 2 — "activity type filter narrows results": on the ops log page, select a specific activity type from `#ops-log-filter` dropdown (e.g. `model.install`), wait for htmx swap to complete, assert that all visible `.ops-log-type-badge` elements show the selected type, then reset filter to "All activities" and verify rows reappear
5. Create `e2e/tests/25-ops-log/model-refresh.spec.ts` with imports
6. Write test 1 — "refresh button triggers model refresh and ops log entry": register `ownerPage.on('dialog', dialog => dialog.accept())` BEFORE any clicks, navigate to `/admin/models`, assert a "Refresh" button exists in the basic-pkm model row, click it, wait for htmx response, assert either a success message or an error message appears (not a 500/crash). Then navigate to `/admin/ops-log`, wait for table, check for a `model.refresh` type badge in the most recent entries.
7. Handle edge cases: if test stack has no ops log entries, the ops-log.spec tests should detect the "No operations logged yet" empty state and assert gracefully rather than failing
8. Ensure all tests use `ownerPage` fixture only (ops log is owner-only), and follow D069 rate-limit consolidation pattern

## Must-Haves

- [ ] Two tests pass in `ops-log.spec.ts`
- [ ] One test passes in `model-refresh.spec.ts`
- [ ] Model refresh test handles both success and known JSON parsing error gracefully
- [ ] Dialog handler registered before refresh button click (per `admin-model-lifecycle.spec.ts` pattern)
- [ ] All `opsLog` selectors added to SEL

## Verification

- `cd e2e && npx playwright test tests/25-ops-log/ --reporter=list` — 3 tests pass
- No regressions in existing admin test specs

## Inputs

- `e2e/tests/05-admin/admin-model-lifecycle.spec.ts` — dialog handler pattern for `hx-confirm`
- `e2e/tests/05-admin/admin-model-detail.spec.ts` — admin page navigation pattern
- `e2e/helpers/selectors.ts` — existing SEL object to extend
- `backend/app/templates/admin/ops_log.html` — `data-testid="ops-log-table"`, `#ops-log-filter`, `.ops-log-type-badge`, `.ops-log-row`, `.ops-log-status`
- `backend/app/templates/admin/models.html` — refresh button with `hx-confirm` and `hx-post`
- S02 summary: ops log entries created by model install/inference/validation
- S05 summary: model refresh has known basic-pkm JSON parsing error; button exists on list and detail pages

## Observability Impact

- **New signal:** `npx playwright test tests/25-ops-log/ --reporter=list` — reports pass/fail for ops log and model refresh tests
- **Failure artifacts:** On test failure, Playwright trace files in `e2e/test-results/` contain DOM snapshots, network logs, and screenshots
- **Inspection:** `npx playwright test --list` shows registered test names for the 25-ops-log suite
- **Rate-limit caveat:** Tests consume 2 magic-link tokens; running <60s after other tests may hit the 5/min rate limit — wait and re-run

## Expected Output

- `e2e/tests/25-ops-log/ops-log.spec.ts` — new spec file with 2 passing tests
- `e2e/tests/25-ops-log/model-refresh.spec.ts` — new spec file with 1 passing test
- `e2e/helpers/selectors.ts` — extended with `opsLog` selector group
