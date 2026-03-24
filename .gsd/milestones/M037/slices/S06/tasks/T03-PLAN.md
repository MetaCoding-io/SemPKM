---
estimated_steps: 3
estimated_files: 4
skills_used:
  - best-practices
  - test
---

# T03: Context-aware notification dispatch hook and integration tests

**Slice:** S06 — Push Notifications with Context Filtering
**Milestone:** M037

## Description

Wire the notification service into the context update flow so that notable context state changes (e.g., location zone change, focus block ending) trigger push notification dispatch. The service's `should_suppress()` handles filtering — the router just calls `send_to_user()` and trusts the service. Add integration-style tests that exercise the full suppress→skip and allow→send code paths.

## Steps

1. **Hook notification dispatch into `update_context()` in `backend/app/context/router.py`**:
   - After the existing auto-persona rule evaluation block (the try/except that evaluates rules and switches persona), add a second try/except block for notification dispatch.
   - Get the notification service from `request.app.state.notification_service`.
   - Dispatch notifications for notable state changes:
     - If `location_zone` is in the update fields and differs from null → send "Location: {zone}" notification with type `context_changes`
     - If `calendar_busy` transitions from True to False → send "Focus block ended" notification with type `context_changes`
   - Call `notification_service.send_to_user(user.id, title, body, data={'type': notification_type}, notification_type=notification_type)`.
   - Wrap in try/except — notification errors must never break the context update response (same pattern as rule evaluation).
   - Add structured log: `notification.dispatch_triggered user_id={} type={} location_zone={}`

2. **Add integration tests to `backend/tests/test_notification_service.py`**:
   - Test that `send_to_user()` skips when `should_suppress()` returns True (calendar_busy)
   - Test that `send_to_user()` proceeds when `should_suppress()` returns False
   - Test midnight-spanning quiet hours edge case explicitly: test at 23:00 (within 22:00-07:00 = suppressed), at 03:00 (within = suppressed), at 08:00 (outside = allowed), at 21:00 (outside = allowed)
   - Test that `send_to_user()` with no registered tokens is a no-op (doesn't error)
   - Test that `send_notification()` in no-op mode (firebase_app=None) returns None without error
   - Mock `firebase_admin.messaging.send` at the module level to avoid needing real Firebase credentials

3. **Add dispatch-related router tests to `backend/tests/test_notification_router.py`**:
   - Test that `POST /api/notifications/test` returns `{sent_count: 0}` when no tokens registered
   - Test that `POST /api/notifications/test` returns suppression info when suppressed
   - Verify the test endpoint respects suppression (register a token, set quiet hours covering now, call test, verify suppressed=True in response)

## Must-Haves

- [ ] Notification dispatch hooked into `update_context()` with try/except guard
- [ ] Location zone change triggers notification
- [ ] Calendar busy→free transition triggers notification
- [ ] Notification errors never break context update response
- [ ] Midnight-spanning quiet hours tested with 4 time points (23:00, 03:00, 08:00, 21:00)
- [ ] Integration tests for full suppress→skip and allow→send paths
- [ ] All existing + new tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py tests/test_notification_router.py -v` — all tests pass
- `grep -q "notification_service" backend/app/context/router.py` — dispatch hook wired
- `grep -q "notification.dispatch_triggered" backend/app/context/router.py` — structured log present

## Inputs

- `backend/app/context/router.py` — context update endpoint to hook into (existing auto-persona block pattern)
- `backend/app/context/notification_service.py` — NotificationService from T01
- `backend/tests/test_notification_service.py` — existing tests from T01 to extend
- `backend/tests/test_notification_router.py` — existing tests from T02 to extend

## Expected Output

- `backend/app/context/router.py` — modified: notification dispatch hook after rule evaluation
- `backend/tests/test_notification_service.py` — modified: additional integration tests
- `backend/tests/test_notification_router.py` — modified: dispatch-related router tests
- `backend/app/context/notification_service.py` — potentially adjusted if integration reveals issues
