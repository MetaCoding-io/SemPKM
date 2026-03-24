---
id: T03
parent: S06
milestone: M037
provides:
  - Notification dispatch hook in update_context() triggered by location zone changes and calendar busy→free transitions
  - Integration tests for full suppress→skip and allow→send paths through send_to_user()
  - Dedicated midnight-spanning quiet hours tests at 4 time points (23:00, 03:00, 08:00, 21:00)
  - 3 additional dispatch-related router tests for test-send suppression scenarios
key_files:
  - backend/app/context/router.py
  - backend/tests/test_notification_service.py
  - backend/tests/test_notification_router.py
key_decisions:
  - Pre-update state captured only when calendar_busy is in the update fields (avoids unnecessary DB read on every context update)
  - Notification dispatch uses getattr() with None fallback rather than hard dependency on notification_service existing on app.state — graceful no-op if service not initialized
patterns_established:
  - Context state transition detection pattern: capture old_ctx before update, compare post-update fields against old state for transition triggers
  - try/except guard block for notification dispatch mirrors the existing rule evaluation guard — notification errors never break context update responses
observability_surfaces:
  - notification.dispatch_triggered (user_id, type, location_zone or calendar_busy=free)
  - context.notification_dispatch_failed (user_id, exc_info) — error log for dispatch failures
duration: 12m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Context-aware notification dispatch hook and integration tests

**Wire notification dispatch into context update flow for location zone changes and calendar busy→free transitions, with 8 new integration tests and 4 dedicated midnight-spanning quiet hours tests**

## What Happened

Added a notification dispatch block in `update_context()` in `backend/app/context/router.py`, placed after the existing auto-persona rule evaluation block. The dispatch detects two notable state changes: (1) location_zone appearing in the update fields with a non-null value triggers a "Location Update" notification, and (2) calendar_busy transitioning from True to False triggers a "Focus Block Ended" notification. Both dispatch via `notification_service.send_to_user()` which internally handles suppression — the router trusts the service to filter.

Pre-update state is captured only when `calendar_busy` is in the update fields, avoiding an unnecessary DB read on every context update. The dispatch block uses `getattr(request.app.state, "notification_service", None)` for graceful no-op when the service isn't initialized.

Added 8 new integration tests to `test_notification_service.py`: 4 in `TestIntegrationSuppressAndSend` (calendar_busy suppression, allowed send, no-tokens no-op, firebase no-op) and 4 in `TestMidnightSpanningQuietHours` (23:00 suppressed, 03:00 suppressed, 08:00 allowed, 21:00 allowed). Added 3 new dispatch-related router tests for the test-send endpoint: zero-sent with no tokens, suppression info with calendar_busy, and quiet-hours suppression.

## Verification

All task-level and slice-level checks pass:

- `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py tests/test_notification_router.py -v` — 55/55 pass
- `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py -v -k "suppress"` — 17/17 pass
- `grep -q "notification_service" backend/app/context/router.py` — found
- `grep -q "notification.dispatch_triggered" backend/app/context/router.py` — found
- `grep -q "firebase-admin" backend/pyproject.toml` — found
- `grep -q "firebase_credentials_path" backend/app/config.py` — found
- `grep -q "Notifications" backend/app/templates/browser/settings_page.html` — found

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py tests/test_notification_router.py -v` | 0 | ✅ pass | 0.99s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py -v -k "suppress"` | 0 | ✅ pass | 0.45s |
| 3 | `grep -q "notification_service" backend/app/context/router.py` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "notification.dispatch_triggered" backend/app/context/router.py` | 0 | ✅ pass | <0.1s |
| 5 | `grep -q "firebase-admin" backend/pyproject.toml` | 0 | ✅ pass | <0.1s |
| 6 | `grep -q "firebase_credentials_path" backend/app/config.py` | 0 | ✅ pass | <0.1s |
| 7 | `grep -q "Notifications" backend/app/templates/browser/settings_page.html` | 0 | ✅ pass | <0.1s |

## Diagnostics

- Check structured logs for `notification.dispatch_triggered` to verify dispatch fires on context updates containing location_zone or calendar_busy transitions
- Check `notification.suppressed` logs to verify downstream suppression logic (calendar_busy, quiet_hours, disabled, type_disabled) is filtering dispatched notifications
- Check `context.notification_dispatch_failed` for errors in the dispatch block — these are logged with exc_info for debugging but never break the context update response
- The try/except guard ensures the notification dispatch is completely isolated from the context update flow

## Deviations

None — implementation followed the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `backend/app/context/router.py` — added: pre-update state capture for calendar_busy transition detection, notification dispatch block after rule evaluation with try/except guard and structured logging
- `backend/tests/test_notification_service.py` — added: TestIntegrationSuppressAndSend (4 tests) and TestMidnightSpanningQuietHours (4 tests) — total now 35 service tests
- `backend/tests/test_notification_router.py` — added: 3 dispatch-related router tests for test-send suppression scenarios — total now 20 router tests
- `.gsd/milestones/M037/slices/S06/tasks/T03-PLAN.md` — added: Observability Impact section (pre-flight fix)
