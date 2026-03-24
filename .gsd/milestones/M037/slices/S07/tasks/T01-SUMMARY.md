---
id: T01
parent: S07
milestone: M037
provides:
  - Integration test proving full context→rules→persona→notification loop with real services
key_files:
  - backend/tests/test_context_integration.py
key_decisions:
  - Rate limiter disabled in integration test app (limiter.enabled = False) since tests exercise integration logic, not rate limiting, and the 12/min cap breaks multi-test sessions
patterns_established:
  - Integration tests wire real services via app.state (matching main.py lifespan names) with dependency overrides for both Depends()-injected and request.app.state-accessed services
  - seed_persona/seed_rule/seed_preferences/seed_device_token helpers use session_factory directly for test data setup
observability_surfaces:
  - TestDiagnosticSignals class verifies error-handling paths: rule evaluation failures and notification dispatch failures are caught and logged without breaking context update
duration: 25m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Backend integration test proving cross-service context loop

**Created 12-test integration suite wiring real ContextService, RulesEngine, PersonaService, NotificationService, and ContextBroadcast against in-memory SQLite — proving the full context update → rule evaluation → persona switch → notification dispatch/suppression chain.**

## What Happened

Built `backend/tests/test_context_integration.py` with 12 tests organized into 4 classes:

- **TestFullLoop (4 tests):** Full context-to-persona-switch, no-rule-match, priority ordering, redundant switch skipped.
- **TestNotificationIntegration (4 tests):** Dispatch on zone change, suppression via calendar_busy, suppression via quiet hours, suppression when master toggle disabled.
- **TestContextStaleness (2 tests):** Staleness with zero TTL, freshness with default TTL.
- **TestDiagnosticSignals (2 tests):** Rule evaluation error logged not raised, notification dispatch error logged not raised.

All services are real implementations backed by a shared in-memory SQLite database — only Firebase dispatch is mocked (firebase_app=None → no-op mode). The test app fixture wires services onto app.state matching the main.py lifespan attribute names, with dependency overrides for both `Depends()`-injected and `request.app.state`-accessed services.

The initial run had 11/12 passing — the last diagnostic test hit the rate limiter (12 requests/min shared across all tests). Fixed by setting `limiter.enabled = False` in the test app fixture.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py -v` — 12 tests pass (exceeds 8+ requirement)
- `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py tests/test_rules_engine.py tests/test_rules_router.py tests/test_zone_service.py tests/test_zone_router.py tests/test_notification_service.py tests/test_notification_router.py -v` — all 172 existing tests pass (plan said 176; actual count is 172)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py -v` | 0 | ✅ pass | 0.92s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py tests/test_rules_engine.py tests/test_rules_router.py tests/test_zone_service.py tests/test_zone_router.py tests/test_notification_service.py tests/test_notification_router.py -v` | 0 | ✅ pass | 2.51s |

## Diagnostics

- Run `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py -v` to verify all integration paths.
- Tests are grouped by concern — `TestFullLoop` for core persona switching, `TestNotificationIntegration` for dispatch/suppression, `TestContextStaleness` for TTL, `TestDiagnosticSignals` for error isolation. A failure in any group pinpoints which layer is broken.
- The `TestDiagnosticSignals` tests inject broken services to prove the try/except blocks in `update_context()` work correctly.

## Deviations

- Plan said 8+ tests; delivered 12 (added staleness-not-stale, master-disabled suppression, and two error-handling diagnostic tests).
- Plan estimated 176 existing tests; actual count is 172. No regression — all pass.
- Added `limiter.enabled = False` to the test app fixture (not in plan) to prevent rate limiting interference across test methods.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_context_integration.py` — New integration test file with 12 tests covering the full context→rules→persona→notification loop
- `.gsd/milestones/M037/slices/S07/S07-PLAN.md` — Added diagnostic verification step to Verification section
- `.gsd/milestones/M037/slices/S07/tasks/T01-PLAN.md` — Added Observability Impact section
