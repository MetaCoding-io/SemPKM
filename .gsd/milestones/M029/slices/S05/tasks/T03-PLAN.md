---
estimated_steps: 5
estimated_files: 2
---

# T03: E2E test verification against optimized build and slice summary

**Slice:** S05 — Lighthouse Verification & QUIC/HTTP/3 Decision
**Milestone:** M029

## Description

Run existing E2E tests to verify the optimized build doesn't break functionality, then write the S05-SUMMARY.md that closes both this slice and the M029 milestone.

**E2E testing approach:** The main Docker stack (port 3000) serves the optimized build but uses the main-tree auth setup, not the test-compose auth fixture. The test compose stack (port 3901) uses raw `nginx:stable-alpine` without the build pipeline. Two approaches:

- **Option A (preferred):** Run E2E tests against port 3000 using `TEST_BASE_URL=http://localhost:3000`. The auth fixture may need adjustment since it reads the setup token from the test compose containers. Try it first — if auth works, this is the best verification. If it fails due to auth fixture incompatibility, fall back to Option B.
- **Option B (fallback):** Run E2E tests against the test compose stack (port 3901) to verify tests still pass. Then document that the optimized build was manually verified via Lighthouse + curl in T01, and E2E tests pass against dev-mode serving. Note this as a limitation.

Any test failures must be triaged: is the failure pre-existing (existed before M029) or caused by optimization changes? The build pipeline only changes asset paths and compression — it shouldn't affect functionality.

## Steps

1. **Check if test compose stack is running**, and if E2E test infrastructure is available:
   ```bash
   cd /home/james/Code/SemPKM  # E2E tests run from main tree
   docker compose -f docker-compose.test.yml ps 2>/dev/null
   ls e2e/package.json
   ```

2. **Try running E2E tests against port 3000** (optimized build):
   ```bash
   cd /home/james/Code/SemPKM/e2e
   TEST_BASE_URL=http://localhost:3000 npx playwright test --project=chromium --reporter=list 2>&1 | tail -30
   ```
   If auth fixture fails, note the error and fall back to Option B (test compose stack on port 3901).

3. **If Option B needed**, start the test compose stack and run E2E tests normally:
   ```bash
   cd /home/james/Code/SemPKM
   docker compose -f docker-compose.test.yml up -d
   # Wait for healthy
   sleep 15
   cd e2e && npx playwright test --project=chromium --reporter=list 2>&1 | tail -50
   ```

4. **Triage any failures:**
   - Check if the failure existed before M029 (look at test history, error type)
   - Optimization-related failures would show: missing assets, broken paths, JS errors from minification
   - Pre-existing failures would show: unrelated functionality errors, known flaky tests

5. **Write S05-SUMMARY.md** with all required sections:
   - What happened: T01 Lighthouse measurements, T02 decisions/requirements, T03 E2E results
   - Before/after delta table (pull data from `.gsd/milestones/M029/slices/S05/lighthouse-results.md`)
   - Verification table with all checks
   - Requirements validated: PERF-02 through PERF-10 (reference T02)
   - E2E test results with pass/fail count and triage of any failures
   - Forward intelligence: milestone is complete, what comes next
   - Files created/modified across all three tasks

## Must-Haves

- [ ] E2E tests run (against either port 3000 or port 3901) with results documented
- [ ] Any test failures triaged as pre-existing vs optimization-related
- [ ] S05-SUMMARY.md exists with complete what-happened, verification, requirements-validated, and forward-intelligence sections
- [ ] Before/after Lighthouse delta table included in summary

## Verification

- E2E test command exits with results (pass count documented)
- `test -f .gsd/milestones/M029/slices/S05/S05-SUMMARY.md && echo "Summary exists"`
- `grep 'PERF-07' .gsd/milestones/M029/slices/S05/S05-SUMMARY.md` — Lighthouse score referenced in summary
- `grep 'Requirements Validated' .gsd/milestones/M029/slices/S05/S05-SUMMARY.md` — requirements section present

## Inputs

- `.gsd/milestones/M029/slices/S05/lighthouse-results.md` — T01's measurement results (for delta table in summary)
- `.gsd/milestones/M029/slices/S05/lighthouse-after.report.json` — T01's Lighthouse JSON report
- T02 completion — QUIC/HTTP/3 decision and PERF requirements registered
- S01 through S04 summaries — for verification evidence compilation
- Running Docker stack at port 3000 with optimized build
- E2E test infrastructure at `/home/james/Code/SemPKM/e2e/`

## Observability Impact

- **E2E test results:** Documented in S05-SUMMARY.md — pass/fail counts with triage of any failures. Future agents can grep for "E2E" in the summary to find results.
- **S05-SUMMARY.md:** Primary inspection artifact for the entire slice. Contains verification evidence table, before/after Lighthouse deltas, requirements validated, and forward intelligence. Inspect with `grep -A2 'Verification Evidence' .gsd/milestones/M029/slices/S05/S05-SUMMARY.md`.
- **Failure state:** If E2E tests fail due to optimization changes, the summary will document specific failure types (missing assets, broken paths, JS minification errors) vs pre-existing failures. Check `grep 'optimization-related' S05-SUMMARY.md`.

## Expected Output

- `.gsd/milestones/M029/slices/S05/S05-SUMMARY.md` — Complete slice summary closing S05 and M029
- E2E test results documented (in summary or separate results file)
