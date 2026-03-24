---
id: S06
milestone: M037
title: "Push Notifications with Context Filtering"
status: done
started: 2026-03-23
completed: 2026-03-23
tasks_completed: 4
tasks_total: 4
test_count: 55
verification: passed
---

# S06: Push Notifications with Context Filtering

## What This Slice Delivers

Full push notification infrastructure: backend dispatches notifications via Firebase Cloud Messaging (FCM) to registered mobile devices, with context-aware suppression (quiet hours, calendar busy, disabled types). Users manage notification preferences through the Settings UI. The mobile app requests permission, retrieves its native FCM/APNs token, registers it with the backend, and handles incoming notifications.

This is the **notification plumbing** — it doesn't send notifications autonomously in response to data events (that's a future concern). It proves the suppress→send pipeline works and gives users the controls to configure when notifications are acceptable.

## Key Components Built

### Backend (4 new files, 5 modified)

- **`notification_models.py`** — `DeviceToken` (user_id FK CASCADE, unique token, platform, device_name, timestamps) and `NotificationPreferences` (unique user_id, enabled, quiet hours as HH:MM strings, suppress_when_busy, enabled_types as JSON string)
- **`notification_service.py`** — Token CRUD, preference management, `should_suppress(user_id, notification_type)` returning `(bool, reason)`, `send_notification()` wrapping `messaging.send()` via `asyncio.to_thread()` with stale token auto-cleanup on `UnregisteredError`, `send_to_user()` fan-out with suppression. No-op when `firebase_app is None`.
- **`notification_router.py`** — 4 endpoints: `POST /api/notifications/register` (201), `GET/PUT /api/notifications/preferences`, `POST /api/notifications/test` (diagnostic with suppression reporting)
- **Migration 021** — creates `device_tokens` and `notification_preferences` tables, chains from 020
- **Context router hook** — dispatch block in `update_context()` fires notifications on location_zone changes and calendar_busy→free transitions. Uses try/except guard so notification failures never break context updates.
- **main.py** — `NotificationService` initialized in lifespan with Firebase credentials (no-op when path empty)
- **Settings UI** — "Notifications" panel with quiet hours, suppress-when-busy toggle, notification type checkboxes, test-send button

### Mobile (3 new/modified files)

- **`notifications.ts`** — `registerForPushNotifications()` (permission → native token → backend registration), `setupNotificationHandler()` (foreground display + tap listener), `setupAndroidChannel()` (MAX importance)
- **`client.ts`** — 4 notification methods + 3 TypeScript interfaces
- **Settings screen** — Push Notifications section with permission status badge, enable toggle, test-send button
- **App layout** — handler setup on mount, post-auth token registration (fire-and-forget)

## Suppression Logic

`should_suppress()` checks in order: (1) master enabled flag, (2) notification type in enabled_types, (3) calendar_busy via ContextService, (4) quiet hours with midnight-spanning support. Returns `(True, "reason_string")` or `(False, None)`.

Midnight-spanning quiet hours (e.g., 22:00→06:00): `now >= start OR now < end` — tested at 4 time points (23:00 suppressed, 03:00 suppressed, 08:00 allowed, 21:00 allowed).

## Test Coverage

55 tests total (35 service + 20 router), all passing in ~1.2s:
- Token CRUD: register, unregister, list, duplicate upsert
- Preferences: get defaults, update partial/full, persist types as JSON
- Suppression: 17 tests covering disabled, type_disabled, calendar_busy, quiet hours (normal + midnight-spanning), all-conditions-pass
- Dispatch: send_to_user fan-out, suppressed skip, stale token cleanup, no-op mode
- Integration: full suppress→skip and allow→send paths
- Router: CRUD endpoints, auth enforcement on all 4, validation (missing/invalid platform, bad quiet hours format), test-send with suppression reporting

TypeScript compiles clean with zero errors.

## Patterns Established

- **Optional dependency lazy import:** `firebase_admin.messaging` imported inside `send_notification()` to avoid import failure when firebase-admin is not installed. Pattern for any optional heavy dependency.
- **Deterministic time testing via `_now` parameter:** `should_suppress(user_id, type, _now=datetime)` avoids freezegun dependency for time-sensitive tests.
- **Context state transition detection:** Capture `old_ctx` before update, compare post-update fields for transition triggers (calendar_busy True→False). Only reads old state when relevant fields are present in the update.
- **Fire-and-forget dispatch guard:** `getattr(request.app.state, "notification_service", None)` with try/except ensures notification dispatch never breaks the context update response path.
- **SDK 55 notification API:** `shouldShowBanner: true, shouldShowList: true` replaces deprecated `shouldShowAlert` in Expo SDK 55.

## What S07 Should Know

- NotificationService is on `app.state.notification_service` — access via `get_notification_service()` dependency or `getattr(request.app.state, "notification_service", None)`
- Firebase is no-op without credentials — all tests pass without a real Firebase project. Real dispatch needs `FIREBASE_CREDENTIALS_PATH` pointing to a service account JSON file.
- The context router dispatches notifications for location_zone changes and calendar_busy→free transitions. More trigger types can be added by extending the dispatch block in `update_context()`.
- Mobile token registration is fire-and-forget on auth — check device_tokens table to verify registration.
- `POST /api/notifications/test` is the diagnostic surface for verifying push delivery end-to-end. Returns `{sent_count, suppressed, reason}`.

## Verification Evidence

| # | Check | Result |
|---|-------|--------|
| 1 | 55 notification tests pass | ✅ |
| 2 | 17 suppress tests pass | ✅ |
| 3 | firebase-admin in pyproject.toml | ✅ |
| 4 | firebase_credentials_path in config.py | ✅ |
| 5 | Notifications in settings_page.html | ✅ |
| 6 | expo-notifications in mobile/package.json | ✅ |
| 7 | expo-notifications in mobile/app.json | ✅ |
| 8 | notifications.ts exists | ✅ |
| 9 | notification_service in main.py | ✅ |
| 10 | notification dispatch in context router | ✅ |
| 11 | TypeScript compiles clean | ✅ |
| 12 | Migration 021 exists and chains from 020 | ✅ |

## Deviations from Plan

- Expo SDK 55 uses `~55.0.x` versioning (plan specified `~0.29.x` from older SDK)
- `shouldShowBanner/shouldShowList` replaces deprecated `shouldShowAlert`
- Notification icon omitted from plugin config (asset doesn't exist — avoids build error)
- `expo-device` already present — no addition needed

## Files Created

- `backend/app/context/notification_models.py`
- `backend/app/context/notification_service.py`
- `backend/app/context/notification_router.py`
- `backend/migrations/versions/021_device_tokens.py`
- `backend/app/templates/browser/_notification_preferences.html`
- `backend/tests/test_notification_service.py`
- `backend/tests/test_notification_router.py`
- `mobile/src/services/notifications.ts`

## Files Modified

- `backend/app/config.py` — firebase_credentials_path setting
- `backend/pyproject.toml` — firebase-admin~=6.7
- `backend/app/main.py` — NotificationService init, router mount
- `backend/app/dependencies.py` — get_notification_service()
- `backend/app/context/router.py` — notification dispatch hook
- `backend/app/browser/settings.py` — notification preferences route
- `backend/app/templates/browser/settings_page.html` — Notifications sidebar button + panel
- `frontend/static/css/settings.css` — notification preference styles
- `mobile/package.json` — expo-notifications dependency
- `mobile/app.json` — expo-notifications plugin
- `mobile/src/api/client.ts` — 4 notification methods + interfaces
- `mobile/src/app/(app)/(tabs)/settings.tsx` — Push Notifications section
- `mobile/src/app/(app)/_layout.tsx` — handler setup + post-auth registration
