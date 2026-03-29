---
estimated_steps: 17
estimated_files: 2
skills_used: []
---

# T01: Run full E2E suite and catalog all failures with error messages

Run the complete 122-spec E2E suite against the Docker test stack and catalog every failure with its file path, test name, and error message. Group failures by likely root cause category. The partial research run (tests 1–118, chromium only) found 14 failures. This task completes the catalog by running all 122 files across both chromium and firefox.

Steps:
1. Ensure Docker test stack is healthy: `docker compose -f docker-compose.test.yml ps` and check all services are Up/healthy.
2. Run the full suite from project root: `cd e2e && npx playwright test --reporter=list 2>&1 | tee /tmp/e2e-full-run.log`
   - If the full run times out (>900s), run per-directory: `npx playwright test tests/00-setup/ tests/01-objects/ tests/02-views/` etc.
3. Extract all failures: grep for 'FAILED\|Error\|Timeout\|expect(' in the output.
4. Write a structured failure catalog to `.gsd/milestones/M046/slices/S06/failure-catalog.md` with columns: File, Test Name, Error Summary, Root Cause Category.
5. Categorize failures into groups: A=bare-global refs (M044 migration), B=template testid mismatch, C=timing/flaky, D=assertion logic, E=missing feature/selector, F=other.

Known failures from S06 research to expect:
- Timeline view (3 tests) — bare globals in timeline_view.html
- RBox ontology viewer — data-testid naming mismatch
- Class creation — bare globals in onclick handlers
- Type picker / keyboard shortcuts — timing
- Object create/edit — timing/flaky
- Table pagination — assertion
- Markdown rendering — CDN timing
- Magic-link member role — invite flow

## Inputs

- `e2e/tests/`
- `e2e/fixtures/auth.ts`
- `.gsd/milestones/M046/slices/S06/S06-RESEARCH.md`

## Expected Output

- `.gsd/milestones/M046/slices/S06/failure-catalog.md`

## Verification

test -f .gsd/milestones/M046/slices/S06/failure-catalog.md && grep -c '|' .gsd/milestones/M046/slices/S06/failure-catalog.md
