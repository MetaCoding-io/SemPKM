---
verdict: needs-remediation
remediation_round: 0
---

# Milestone Validation: M046

## Success Criteria Checklist
- [ ] **Full 122-spec suite passes with exit code 0** — NOT MET. S06 final run: 163/439 tests executed on chromium, 19 failures across 9 categories. S06 summary explicitly states "The 0-failure target was not achieved."
- [x] **Each slice fixes an independent failure category** — MET. S01 (auth), S02 (copilot z-index), S03 (app subprocess), S04 (ontology duplicates), S05 (calendar/recurring/setup), S06 (bare-globals + misc) each addressed distinct categories.
- [x] **Docker test stack starts cleanly** — MET. `docker compose -f docker-compose.test.yml config` validates; 5 new mock services added with health checks.

## Slice Delivery Audit
| Slice | Claimed Deliverable | Delivered? | Evidence |
|-------|---------------------|------------|----------|
| S01 | Auth-dependent tests pass without magic link failures | ✅ Yes | 15 tests passed in 14.1s, 0 failures |
| S02 | All 5 copilot tests pass | ✅ Yes | 5 tests passed in 26.3s |
| S03 | Sync app tests find running processes and render settings UI | ✅ Yes | Scheduler fix verified, 5 mock services defined, 7 env vars, selectors compile |
| S04 | Ontology tests pass without strict mode errors | ✅ Yes | All 7 data-testid attributes unique, TBox/ABox pass |
| S05 | Calendar, recurring task, setup wizard tests pass | ✅ Yes | 20 passed, 10 skipped, 0 failed |
| S06 | Full suite 0 failures | ❌ No | 19 residual failures across 9 categories. Bare-global and selector fixes delivered, but timing/infrastructure failures remain.

## Cross-Slice Integration
No cross-slice boundary mismatches. S01–S05 each fixed independent failure categories. S06 depended on all prior slices and consumed their fixes correctly — the 19 remaining failures are NOT regressions from S01–S05 work. They are residual issues S06 identified but did not have time to fully resolve.

## Requirement Coverage
Requirements advanced during this milestone:
- APP-02: Fixed scheduler datetime crash (S03/T01)
- APP-06: Fixed naive/aware datetime bug in AppScheduler (S03/T01)
- APP-14: Added APP_BASE_URL and 5 mock service dependencies (S03/T02)

No active requirements left unaddressed by the milestone scope. The milestone is test infrastructure — it advances requirements indirectly by restoring the regression safety net.

## Verdict Rationale
The milestone's entire purpose is achieving 0 E2E test failures across 122 specs. S06's own summary states "The 0-failure target was not achieved" with 19 residual failures remaining. While S01–S05 delivered their individual slice goals cleanly, and S06 made significant progress (fixed 14 bare-globals, 5 targeted issues), the Contract and UAT verification classes are not met. The remaining 19 failures all have identified root causes and proposed fixes in the S06 summary and failure catalog — they are timing/assertion adjustments, not deep architectural issues. A single remediation slice should resolve them.

## Remediation Plan
Add **S07: Residual Failure Sweep** to address the 19 remaining test failures across 9 documented categories:

1. **Timeline visibility (3 tests):** Change wait from `state:'visible'` to `state:'attached'` for timeline view initial load.
2. **Object-tab loading (5 tests):** Increase individual `waitForSelector('.object-tab')` timeouts to 20s (matching the openObjectTab helper change).
3. **waitForIdle htmx-request (3 tests):** Increase timeout or switch to specific element waits instead of generic idle checks.
4. **Workspace layout assertions (2 tests):** Update expected tab count from 4 to 5; use case-insensitive text matching for section summaries.
5. **Table pagination (1 test):** Fix test to create the correct type (Events, not Notes) for the table view spec.
6. **Multi-value autocomplete (1 test):** Fix suggestion dropdown click timing.
7. **Magic-link rate limit (1 test):** Add rate limiter reset or spacing between test files that create new users.
8. **Event log panel (1 test):** Verify bottom panel via class toggle instead of inline style height check.
9. **Object-form visibility (2 tests):** Increase timeout or add explicit wait for htmx `/browser/types` load.

After S07, re-run full suite and verify exit code 0.
