# S07 UAT — End-to-End Integration & Acceptance

## Preconditions

- Backend venv exists at `backend/.venv/` with all dependencies
- M037 S01–S06 code present (context service, rules engine, zones, notifications, mobile app scaffold)
- No Docker stack required — integration tests use in-memory SQLite

---

## Test Case 1: Full Context → Persona Switch Loop

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestFullLoop::test_full_loop_context_to_persona_switch -v`
2. Verify the test:
   - Creates a persona ("Work") and a rule matching `location_zone=office`
   - POSTs `{"location_zone": "office"}` to `/api/context/update`
   - Asserts response contains `location_zone: "office"` and `is_stale: false`
   - Verifies the active persona switched to "Work"

**Expected:** Test PASSED. The full chain fires: context persisted → rule evaluated → persona switched.

---

## Test Case 2: No Rule Match — Context Updates Without Persona Change

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestFullLoop::test_no_rule_match -v`
2. Verify context update succeeds with 200 but no persona switch occurs when no rule matches

**Expected:** Test PASSED. Context stored correctly, no side effects.

---

## Test Case 3: Rule Priority Ordering

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestFullLoop::test_rule_priority_ordering -v`
2. Verify that when two rules match the same context, the higher-priority rule's persona wins

**Expected:** Test PASSED. Priority 10 rule wins over priority 1 rule.

---

## Test Case 4: Redundant Switch Skipped

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestFullLoop::test_redundant_switch_skipped -v`
2. Verify that posting the same context twice doesn't trigger a second persona switch

**Expected:** Test PASSED. PersonaService.activate() not called redundantly.

---

## Test Case 5: Notification Dispatched on Zone Change

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestNotificationIntegration::test_notification_dispatched_on_zone_change -v`
2. Verify that a context update with a zone change triggers notification dispatch (in no-op mode)

**Expected:** Test PASSED. Notification service receives send request.

---

## Test Case 6: Notification Suppression — Calendar Busy

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestNotificationIntegration::test_notification_suppressed_calendar_busy -v`
2. Verify notifications are suppressed when `calendar_busy=true` in context

**Expected:** Test PASSED. Notification not dispatched.

---

## Test Case 7: Notification Suppression — Quiet Hours

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestNotificationIntegration::test_notification_suppressed_quiet_hours -v`
2. Verify notifications are suppressed during configured quiet hours

**Expected:** Test PASSED. Notification not dispatched.

---

## Test Case 8: Notification Suppression — Master Toggle Disabled

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestNotificationIntegration::test_notification_suppressed_master_disabled -v`
2. Verify notifications are suppressed when user has disabled the master notifications toggle

**Expected:** Test PASSED. Notification not dispatched.

---

## Test Case 9: Context Staleness via TTL

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestContextStaleness::test_context_staleness_via_ttl -v`
2. Verify that context with TTL=0 is immediately reported as stale (`is_stale: true`)

**Expected:** Test PASSED. GET `/api/context/current` returns `is_stale: true`.

---

## Test Case 10: Context Freshness with Default TTL

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestContextStaleness::test_context_not_stale_with_default_ttl -v`
2. Verify that freshly-posted context with default TTL (15 min) is reported as fresh

**Expected:** Test PASSED. GET returns `is_stale: false`.

---

## Test Case 11: Diagnostic — Rule Evaluation Failure Isolated

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestDiagnosticSignals::test_rule_evaluation_failure_logged_not_raised -v`
2. Verify that a broken rules engine doesn't break the context update endpoint — error is caught and logged

**Expected:** Test PASSED. Context update returns 200 despite rule evaluation failure.

---

## Test Case 12: Diagnostic — Notification Dispatch Failure Isolated

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_integration.py::TestDiagnosticSignals::test_notification_failure_logged_not_raised -v`
2. Verify that a broken notification service doesn't break the context update endpoint

**Expected:** Test PASSED. Context update returns 200 despite notification dispatch failure.

---

## Test Case 13: User Guide Chapter 48 Exists and Is Substantive

**Steps:**
1. `wc -l docs/guide/48-mobile-app-context.md`
2. Verify file has 200+ lines of substantive content covering installation, onboarding, zones, dashboard, rules, notifications, workspace indicator, and troubleshooting

**Expected:** 386 lines. Content covers all 8 sections listed above.

---

## Test Case 14: All Three Guide Indexes Reference Chapter 48

**Steps:**
1. `grep '48-mobile-app-context' docs/guide/README.md`
2. `grep '48-mobile-app-context' docs/guide/index.html`
3. `grep '48-mobile-app-context' backend/app/templates/guide.html`

**Expected:** All three grep commands return matches. No missing index entry.

---

## Test Case 15: Regression — All 172 Existing Tests Pass

**Steps:**
1. `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py tests/test_rules_engine.py tests/test_rules_router.py tests/test_zone_service.py tests/test_zone_router.py tests/test_notification_service.py tests/test_notification_router.py -v`

**Expected:** 172 tests PASSED. Zero failures, zero errors.

---

## Edge Cases

- **Rate limiter interference:** The integration test disables the rate limiter (`limiter.enabled = False`). If this is removed, tests hitting > 12 requests/minute will get 429 responses.
- **Firebase mock:** Integration tests use `firebase_app=None` no-op mode. Real FCM dispatch is not exercised here — that's S06's scope.
- **SQLite in-memory:** Tests share a single in-memory SQLite database via `session_factory`. If tests are parallelized, they will conflict on shared state.
