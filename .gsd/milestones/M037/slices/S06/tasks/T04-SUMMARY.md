---
id: T04
parent: S06
milestone: M037
provides:
  - Push notification service (permissions, native token retrieval, backend registration)
  - Notification API client methods (register, preferences CRUD, test send)
  - Settings screen Push Notifications section with permission status, toggle, and test send
  - Notification infrastructure wired into app layout (handler, Android channel, post-auth registration)
key_files:
  - mobile/src/services/notifications.ts
  - mobile/src/api/client.ts
  - mobile/src/app/(app)/(tabs)/settings.tsx
  - mobile/src/app/(app)/_layout.tsx
  - mobile/package.json
  - mobile/app.json
key_decisions:
  - Used SDK 55 version scheme (~55.0.10) for expo-notifications instead of plan's ~0.29.x which matched an older SDK
  - Used shouldShowBanner/shouldShowList instead of deprecated shouldShowAlert in NotificationBehavior (SDK 55 API change)
  - Omitted notification icon path from expo-notifications plugin config since the asset doesn't exist — prevents build error
  - expo-device already installed at SDK 55 — no addition needed
patterns_established:
  - Notification handler uses shouldShowBanner + shouldShowList (SDK 55) not shouldShowAlert
  - Fire-and-forget pattern for push registration — async call with .catch() in useEffect, never blocks app startup
  - Token prefix logging (first 20 chars + "...") for FCM/APNs token redaction
observability_surfaces:
  - "Settings screen shows live permission status (granted/denied/undetermined) and enable toggle"
  - "Console diagnostics: notifications.permission_status, notifications.token_registered, notifications.registration_error, notifications.not_physical_device"
  - "POST /api/notifications/test accessible via Settings screen Send Test button with Alert showing result"
duration: 15m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T04: Mobile app expo-notifications integration

**Add expo-notifications with native FCM/APNs token registration, notification preferences API client, Settings UI section, and post-auth registration wiring**

## What Happened

Added `expo-notifications` (~55.0.10) to package.json and the plugins array in app.json. `expo-device` was already present at SDK 55.

Created `notifications.ts` service with three exports: `registerForPushNotifications()` (permission check → native token retrieval via `getDevicePushTokenAsync` → backend registration), `setupNotificationHandler()` (foreground display + tap listener), and `setupAndroidChannel()` (default channel with MAX importance). The service skips silently on simulators and catches all errors to prevent push failures from breaking app startup.

Added four notification methods to `SemPKMClient`: `registerPushToken()`, `getNotificationPreferences()`, `updateNotificationPreferences()`, and `sendTestNotification()`, plus three TypeScript interfaces (`NotificationPreferences`, `RegisterTokenPayload`, `TestNotificationResponse`).

Rewrote the settings screen to include a Push Notifications section between Connection and About. Shows permission status badge (color-coded), Request Permission button (when not granted), Enable Notifications toggle (calls server preferences API), and Send Test Notification button with Alert result display. Handles simulator detection with a graceful message.

Wired `setupNotificationHandler()` and `setupAndroidChannel()` into a mount-time useEffect in the app layout. Added a session-dependent useEffect that creates a `SemPKMClient` and calls `registerForPushNotifications()` fire-and-forget after authentication.

## Verification

- `cd mobile && npx tsc --noEmit` — zero errors, TypeScript compiles clean
- All 6 task-level grep/test checks pass
- All 7 slice-level verification checks pass (55 backend tests, dependency checks, config checks)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd mobile && npx tsc --noEmit` | 0 | ✅ pass | ~3s |
| 2 | `grep -q "expo-notifications" mobile/package.json` | 0 | ✅ pass | <1s |
| 3 | `grep -q "expo-notifications" mobile/app.json` | 0 | ✅ pass | <1s |
| 4 | `test -f mobile/src/services/notifications.ts` | 0 | ✅ pass | <1s |
| 5 | `grep -q "registerPushToken" mobile/src/api/client.ts` | 0 | ✅ pass | <1s |
| 6 | `grep -q "getDevicePushTokenAsync" mobile/src/services/notifications.ts` | 0 | ✅ pass | <1s |
| 7 | `cd backend && pytest tests/test_notification_service.py tests/test_notification_router.py -v` | 0 | ✅ pass (55 tests) | ~1s |
| 8 | `cd backend && pytest tests/test_notification_service.py -v -k "suppress"` | 0 | ✅ pass (17 tests) | <1s |
| 9 | `grep -q "firebase-admin" backend/pyproject.toml` | 0 | ✅ pass | <1s |
| 10 | `grep -q "firebase_credentials_path" backend/app/config.py` | 0 | ✅ pass | <1s |
| 11 | `grep -q "Notifications" backend/app/templates/browser/settings_page.html` | 0 | ✅ pass | <1s |
| 12 | `grep -q "expo-notifications" mobile/package.json` | 0 | ✅ pass | <1s |

## Diagnostics

- **Settings screen:** Navigate to Settings tab → Push Notifications section shows permission status badge, enable toggle, and test send button
- **Console logs:** Filter by `notifications.` prefix to see permission_status, token_registered, handler_setup, channel_created, registration_error, not_physical_device
- **Token redaction:** FCM/APNs tokens logged as first 20 chars + "..." — never displayed in UI
- **Simulator behavior:** Settings screen shows "Push notifications are not available on simulators" message; `registerForPushNotifications()` returns early with console log

## Deviations

- **SDK version:** Plan specified `~0.29.x` for expo-notifications and `~7.0.x` for expo-device. Actual SDK 55 uses `~55.0.x` for all Expo packages. Used `~55.0.10` to match the existing pattern.
- **NotificationBehavior API:** Plan used `shouldShowAlert` which is deprecated in SDK 55. Used `shouldShowBanner: true, shouldShowList: true` instead (the current API).
- **Notification icon:** Plan specified `"icon": "./assets/images/notification-icon.png"` in plugin config. Asset doesn't exist — omitted to prevent build error. Color-only config is sufficient.
- **expo-device:** Plan said "if not already in package.json, add it." It was already present — no changes needed.

## Known Issues

- No notification icon asset exists at `./assets/images/notification-icon.png` — Android will use the app's default icon. A custom notification icon can be added later.
- Deep linking from notification taps is logged but not implemented (deferred to S07 per plan).

## Files Created/Modified

- `mobile/package.json` — added expo-notifications ~55.0.10 dependency
- `mobile/app.json` — added expo-notifications plugin with color config
- `mobile/src/services/notifications.ts` — new: permission request, native token retrieval, foreground handler, Android channel
- `mobile/src/api/client.ts` — added NotificationPreferences/RegisterTokenPayload/TestNotificationResponse interfaces and 4 client methods
- `mobile/src/app/(app)/(tabs)/settings.tsx` — added Push Notifications section with permission status, toggle, test send
- `mobile/src/app/(app)/_layout.tsx` — wired notification handler setup and post-auth token registration
- `.gsd/milestones/M037/slices/S06/tasks/T04-PLAN.md` — added Observability Impact section
