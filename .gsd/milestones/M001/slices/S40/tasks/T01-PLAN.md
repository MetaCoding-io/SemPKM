# T01: 40-e2e-test-coverage-v24 01

**Slice:** S40 — **Milestone:** M001

## Description

Create Playwright E2E tests for the two major v2.4 features: OWL 2 RL inference (Phase 35-36) and the global lint dashboard (Phase 37-38).

Purpose: These are the highest-value test targets covering core v2.4 functionality — bidirectional inference links and the lint dashboard UI with filtering/sorting.
Output: Two new test spec files in `e2e/tests/09-inference/` and `e2e/tests/10-lint-dashboard/`

## Must-Haves

- [ ] "Inference E2E test creates an edge, triggers inference, and verifies the inverse triple appears"
- [ ] "Inference E2E test verifies bottom panel shows inferred triples with badge and filter controls"
- [ ] "Lint dashboard E2E test verifies the dashboard loads with validation results"
- [ ] "Lint dashboard E2E test verifies severity filtering narrows visible results"
- [ ] "Lint dashboard E2E test verifies sorting changes result order"

## Files

- `e2e/tests/09-inference/inference.spec.ts`
- `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts`
