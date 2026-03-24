# S06 UAT: Push Notifications with Context Filtering

## Preconditions

- Docker stack running with backend API accessible
- Firebase credentials NOT configured (tests no-op mode)
- At least one user account exists
- S01 context API working (POST /api/context/update, GET /api/context/current)
- S02 rules engine working (context rules evaluate on update)

---

## Test 1: Device Token Registration

**Steps:**
1. Authenticate as a user, obtain session cookie or API token
2. `POST /api/notifications/register` with body `{"token": "test-fcm-token-abc123", "platform": "android", "device_name": "Pixel 8"}`
3. Verify response: HTTP 201 with `{"token": "test-fcm-token-abc123", "platform": "android", "device_name": "Pixel 8"}`
4. Repeat the same POST — verify it upserts (201, same token returned, no duplicate error)
5. `POST /api/notifications/register` with body `{"token": "test-token-2", "platform": "invalid"}` — expect HTTP 422 (invalid platform)
6. `POST /api/notifications/register` with body `{"token": "test-token-2"}` — expect HTTP 422 (missing platform)

**Expected:** Token registration works with upsert semantics. Invalid/missing platform rejected.

---

## Test 2: Notification Preferences CRUD

**Steps:**
1. `GET /api/notifications/preferences` — verify defaults: `{"enabled": true, "quiet_hours_start": null, "quiet_hours_end": null, "suppress_when_busy": true, "enabled_types": ["overdue_tasks", "validation_warnings", "context_changes"]}`
2. `PUT /api/notifications/preferences` with `{"quiet_hours_start": "22:00", "quiet_hours_end": "07:00"}` — verify 200 with updated values
3. `GET /api/notifications/preferences` — verify quiet hours persisted
4. `PUT /api/notifications/preferences` with `{"enabled": false}` — verify partial update preserves other fields
5. `PUT /api/notifications/preferences` with `{"quiet_hours_start": "invalid"}` — expect 422 (bad HH:MM format)
6. `PUT /api/notifications/preferences` with empty body `{}` — expect 422

**Expected:** Default preferences sensible. Partial updates work. Validation rejects bad formats.

---

## Test 3: Suppression — Quiet Hours (Normal Range)

**Steps:**
1. Set preferences: `quiet_hours_start: "09:00"`, `quiet_hours_end: "17:00"`, `enabled: true`
2. At 12:00 (within range): call `should_suppress()` or `POST /api/notifications/test` — expect suppressed with reason "quiet_hours"
3. At 20:00 (outside range): expect not suppressed

**Expected:** Notifications suppressed during configured quiet hours.

---

## Test 4: Suppression — Midnight-Spanning Quiet Hours

**Steps:**
1. Set preferences: `quiet_hours_start: "22:00"`, `quiet_hours_end: "06:00"`
2. At 23:00 — expect suppressed (after start, before midnight)
3. At 03:00 — expect suppressed (after midnight, before end)
4. At 08:00 — expect allowed (after end)
5. At 21:00 — expect allowed (before start)

**Expected:** Midnight-spanning quiet hours correctly wrap around midnight boundary.

---

## Test 5: Suppression — Calendar Busy

**Steps:**
1. Set preferences: `suppress_when_busy: true`
2. `POST /api/context/update` with `{"calendar_busy": true}`
3. `POST /api/notifications/test` — expect suppressed with reason "calendar_busy"
4. `POST /api/context/update` with `{"calendar_busy": false}`
5. `POST /api/notifications/test` — expect not suppressed (but sent_count=0 if no tokens)

**Expected:** Calendar busy flag suppresses notifications when suppress_when_busy enabled.

---

## Test 6: Suppression — Disabled Notification Types

**Steps:**
1. Set preferences: `enabled_types: ["overdue_tasks"]` (remove validation_warnings and context_changes)
2. Trigger a context_changes notification — expect suppressed with reason "type_disabled"
3. Trigger an overdue_tasks notification — expect not suppressed

**Expected:** Only enabled types pass the suppression filter.

---

## Test 7: Suppression — Master Disable

**Steps:**
1. Set preferences: `enabled: false`
2. `POST /api/notifications/test` — expect suppressed with reason "disabled"
3. Set preferences: `enabled: true`
4. `POST /api/notifications/test` — expect not suppressed

**Expected:** Master toggle gates all notifications.

---

## Test 8: Test Notification Endpoint (Diagnostic)

**Steps:**
1. Register a token for the user
2. `POST /api/notifications/test` — verify response includes `{"sent_count": 0, "suppressed": false}` (sent_count 0 because Firebase not configured — no-op mode)
3. With quiet hours active, `POST /api/notifications/test` — verify `{"suppressed": true, "reason": "quiet_hours"}`

**Expected:** Test endpoint reports suppression state and sent count. In no-op mode, no real push is attempted.

---

## Test 9: Auth Enforcement

**Steps:**
1. Without auth cookie/token, call each endpoint:
   - `POST /api/notifications/register` — expect 401
   - `GET /api/notifications/preferences` — expect 401 or 302 (HTML redirect)
   - `PUT /api/notifications/preferences` — expect 401
   - `POST /api/notifications/test` — expect 401

**Expected:** All notification endpoints require authentication.

---

## Test 10: Context Update Triggers Notification Dispatch

**Steps:**
1. Register a device token for the user
2. Ensure preferences: enabled, no quiet hours, suppress_when_busy=false
3. `POST /api/context/update` with `{"location_zone": "office"}` — check backend logs for `notification.dispatch_triggered` with type=location_zone
4. `POST /api/context/update` with `{"calendar_busy": true}` — no dispatch expected (busy→true is not a trigger)
5. `POST /api/context/update` with `{"calendar_busy": false}` — check logs for `notification.dispatch_triggered` with type=calendar_busy_cleared

**Expected:** Notification dispatch fires on location zone changes and calendar busy→free transitions. Does not fire on busy→true.

---

## Test 11: Settings UI — Notifications Panel

**Steps:**
1. Navigate to Settings page in the browser
2. Click "Notifications" in the sidebar — verify panel loads via htmx
3. Verify controls present: master enable/disable toggle, quiet hours start/end time inputs, suppress-when-busy checkbox, notification type checkboxes (overdue_tasks, validation_warnings, context_changes)
4. Toggle "Enable Notifications" off, reload page — verify state persisted
5. Set quiet hours 22:00-06:00, reload — verify times persisted
6. Click "Send Test Notification" — verify result message appears (e.g., "Suppressed: disabled" or "Sent: 0")

**Expected:** Settings UI renders, saves via API, and test-send works as diagnostic.

---

## Test 12: Mobile App — Notification Service (Simulator)

**Steps:**
1. Open mobile app in iOS simulator or Android emulator
2. Navigate to Settings tab
3. Verify "Push Notifications" section shows "Push notifications are not available on simulators" or equivalent message
4. Verify no crash occurs (notification code gracefully skips on non-physical devices)

**Expected:** Mobile app handles simulator environment gracefully.

---

## Test 13: Mobile App — Notification Service (Physical Device)

**Steps:**
1. Open mobile app on a physical device
2. On first launch after auth, observe permission prompt for notifications
3. Grant permission — verify token registration logged (`notifications.token_registered` console log with prefix)
4. Navigate to Settings tab — verify permission status shows "granted" badge
5. Toggle "Enable Notifications" — verify API call to PUT preferences
6. Tap "Send Test Notification" — verify Alert appears with result message
7. If Firebase configured: verify push notification appears on device

**Expected:** Full permission → token → registration → test flow works on real hardware.

---

## Test 14: Stale Token Auto-Cleanup

**Steps:**
1. Register a token for the user
2. Simulate `messaging.UnregisteredError` (requires Firebase configured or mock)
3. `send_notification()` catches error and deletes the stale token
4. Query device_tokens table — verify token is gone

**Expected:** Invalid tokens are automatically cleaned up, preventing repeated delivery failures.

---

## Edge Cases

- **No tokens registered:** `send_to_user()` returns empty list, no error
- **Firebase not configured:** All dispatch is no-op with `notification.skipped` log
- **Concurrent context updates:** Notification dispatch block is isolated by try/except — failures don't cascade
- **Empty enabled_types list:** All types suppressed with "type_disabled" reason
- **Quiet hours equal (start == end):** All times are within range — effectively always suppressed
