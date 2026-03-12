# T03: 19-bug-fixes-and-e2e-test-hardening 03

**Slice:** S19 — **Milestone:** M001

## Description

Add E2E test coverage for critical Phase 10-18 features (split panes, event log, tutorial launch) and document the known infrastructure constraint on setup wizard tests. Verify the full suite stays at >= 118/123 with no regressions.

Purpose: Phase 19 bug fixes could introduce regressions. This plan adds targeted tests for the Phase 10-18 features that now have bug fixes applied (split panes, docs/tutorials), and verifies the suite is healthy before v2.0 ships.
Output: Three new spec files covering split panes, event log, and tutorial launch. A code comment in setup wizard spec explaining the known infrastructure issue. Full Playwright run confirming >= 118/123.

## Must-Haves

- [ ] "E2E chromium suite runs with >= 118/123 tests passing — no regressions from Phase 10-18 or Phase 19 fixes"
- [ ] "Split panes E2E test exists and verifies Ctrl+\\ creates a split and tabs are independent"
- [ ] "Event log E2E test exists and verifies the event log panel opens and displays event rows"
- [ ] "Tutorial launch E2E test exists and verifies the Docs tab opens and a tutorial button is visible"
- [ ] "Setup wizard tests (00-setup/01-setup-wizard.spec.ts) have a code comment explaining the known infrastructure constraint — tests are not skipped or tagged"

## Files

- `e2e/tests/03-navigation/split-panes.spec.ts`
- `e2e/tests/06-settings/event-log.spec.ts`
- `e2e/tests/06-settings/tutorials.spec.ts`
- `e2e/tests/00-setup/01-setup-wizard.spec.ts`
