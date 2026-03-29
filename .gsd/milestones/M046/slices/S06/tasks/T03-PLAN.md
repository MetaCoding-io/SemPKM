---
estimated_steps: 13
estimated_files: 1
skills_used: []
---

# T03: Full suite green-light verification — 0 failures across all 122 specs

Run the complete E2E suite and verify 0 failures. Fix any remaining failures discovered during this run.

Steps:
1. Run full suite: `cd e2e && npx playwright test --reporter=list 2>&1 | tee /tmp/e2e-greenlight.log`
   - If timeout is an issue, run in batches by directory.
2. If any tests fail:
   a. Read the error output carefully.
   b. Apply targeted fixes (template edits, test timeout increases, selector adjustments).
   c. Re-run the failing tests to confirm the fix.
   d. Re-run the full suite again to check for regressions.
3. Repeat until 0 failures.
4. Record the final pass count and any skipped tests in the verification output.

Expected: 122 spec files, majority passing, some skipped (setup wizard fresh-stack tests, demo mode tests, etc.), 0 failures.

Note: Tests that skip due to prerequisites (e.g., fresh Docker stack, demo mode, rate limiting) are acceptable — they're gated by `test.skip()` conditions. Only actual failures (assertion errors, timeouts, crashes) count.

## Inputs

- `backend/app/templates/browser/timeline_view.html`
- `backend/app/templates/browser/ontology/create_class_form.html`
- `e2e/tests/22-ontology/ontology-viewer.spec.ts`
- `e2e/tests/`

## Expected Output

- `e2e/tests/`

## Verification

cd e2e && npx playwright test --reporter=list 2>&1 | grep -E 'failed|passed|skipped' | tail -3
