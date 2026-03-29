---
estimated_steps: 16
estimated_files: 12
skills_used: []
---

# T03: Full suite verification — confirm 0 failures across all 122 specs

Run the complete Playwright test suite against the Docker test stack and confirm 0 failures. If any residual failures appear, diagnose and fix them on the spot.

## Steps

1. Ensure Docker test stack is running: `docker compose -f docker-compose.test.yml ps` — if not running, start it with `docker compose -f docker-compose.test.yml up -d` and wait for health checks

2. Run the full suite: `cd e2e && npx playwright test --project=chromium --retries=1 --reporter=line` with a generous timeout (the suite may take 30-60 minutes with retries=1 and workers=1)

3. If all 122 specs pass (0 failures after retries), the slice is done

4. If any failures remain:
   - Identify the specific test and failure message
   - Classify as: assertion mismatch, timeout, test logic bug, or genuine app bug
   - Apply a targeted fix following the same patterns from T01/T02
   - Re-run the failing spec file to confirm the fix
   - Re-run the full suite to confirm no regressions

5. Known non-failure: `rate-limiting.spec.ts` self-skips when `RATE_LIMIT_ENABLED=false` (which is the test stack default). A skip is not a failure.

## Must-Haves

- [ ] Full `npx playwright test --project=chromium --retries=1` completes with 0 failures
- [ ] All 122 spec files executed (none skipped unexpectedly)
- [ ] Any residual fixes applied and verified

## Inputs

- ``e2e/tests/03-navigation/workspace-layout.spec.ts` — T01 output`
- ``e2e/tests/03-navigation/keyboard-shortcuts.spec.ts` — T01 output`
- ``e2e/tests/02-views/table-pagination.spec.ts` — T01 output`
- ``e2e/helpers/dockview.ts` — T01 output`
- ``e2e/tests/02-views/timeline.spec.ts` — T01 output`
- ``e2e/tests/27-event-log-polish/event-log-polish.spec.ts` — T01 output`
- ``e2e/tests/01-objects/edit-object-ui.spec.ts` — T01 output`
- ``e2e/tests/01-objects/create-object.spec.ts` — T01 output`
- ``e2e/tests/01-objects/object-view-redesign.spec.ts` — T02 output`
- ``e2e/tests/12-bug-fixes/bug-fixes.spec.ts` — T02 output`
- ``e2e/tests/05-admin/admin-model-detail.spec.ts` — T02 output`
- ``e2e/tests/01-objects/create-edge.spec.ts` — T02 output`

## Expected Output

- ``e2e/tests/03-navigation/workspace-layout.spec.ts` — passes`
- ``e2e/tests/01-objects/object-view-redesign.spec.ts` — passes`
- ``e2e/tests/12-bug-fixes/bug-fixes.spec.ts` — passes`
- ``e2e/tests/05-admin/admin-model-detail.spec.ts` — passes`

## Verification

cd e2e && npx playwright test --project=chromium --retries=1 --reporter=line 2>&1 | tail -5 | grep -q '0 failed'
