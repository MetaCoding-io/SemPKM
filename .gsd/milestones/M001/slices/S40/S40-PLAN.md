# S40: E2e Test Coverage V24

**Goal:** Create Playwright E2E tests for the two major v2.
**Demo:** Create Playwright E2E tests for the two major v2.

## Must-Haves


## Tasks

- [x] **T01: 40-e2e-test-coverage-v24 01** `est:40min`
  - Create Playwright E2E tests for the two major v2.4 features: OWL 2 RL inference (Phase 35-36) and the global lint dashboard (Phase 37-38).

Purpose: These are the highest-value test targets covering core v2.4 functionality — bidirectional inference links and the lint dashboard UI with filtering/sorting.
Output: Two new test spec files in `e2e/tests/09-inference/` and `e2e/tests/10-lint-dashboard/`
- [x] **T02: 40-e2e-test-coverage-v24 02** `est:18min`
  - Create Playwright E2E tests for edit form helptext (Phase 39 HELP-01) and bug fix verifications (BUG-04 through BUG-09).

Purpose: Complete TEST-05 coverage with helptext feature tests and regression tests for all v2.4 bug fixes.
Output: Two new test spec files in `e2e/tests/11-helptext/` and `e2e/tests/12-bug-fixes/`

## Files Likely Touched

- `e2e/tests/09-inference/inference.spec.ts`
- `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts`
- `e2e/tests/11-helptext/helptext.spec.ts`
- `e2e/tests/12-bug-fixes/bug-fixes.spec.ts`
