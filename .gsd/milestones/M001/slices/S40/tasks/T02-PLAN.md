# T02: 40-e2e-test-coverage-v24 02

**Slice:** S40 — **Milestone:** M001

## Description

Create Playwright E2E tests for edit form helptext (Phase 39 HELP-01) and bug fix verifications (BUG-04 through BUG-09).

Purpose: Complete TEST-05 coverage with helptext feature tests and regression tests for all v2.4 bug fixes.
Output: Two new test spec files in `e2e/tests/11-helptext/` and `e2e/tests/12-bug-fixes/`

## Must-Haves

- [ ] "Helptext E2E test verifies the helptext toggle exists on edit forms and expands/collapses content"
- [ ] "Bug fix E2E test verifies type-specific accent colors differ between object types (BUG-04)"
- [ ] "Bug fix E2E test verifies card view borders render (BUG-05)"
- [ ] "Bug fix E2E test verifies Ctrl+K opens command palette (BUG-06)"
- [ ] "Bug fix E2E test verifies inactive tabs do not show accent bleed (BUG-07)"
- [ ] "Bug fix E2E test verifies panel chevron icons are visible (BUG-08)"
- [ ] "Bug fix E2E test verifies concept search works (BUG-09)"

## Files

- `e2e/tests/11-helptext/helptext.spec.ts`
- `e2e/tests/12-bug-fixes/bug-fixes.spec.ts`
