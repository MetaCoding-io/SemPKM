# S06: Push Notifications with Context Filtering

**Goal:** Backend dispatches push notifications via FCM, suppresses during quiet periods and calendar busy, with device token registration and user preferences — all testable without a real Firebase project.
**Demo:** Run the test suite: service tests prove suppression logic (calendar_busy, quiet hours, disabled types, no-op mode), router tests prove CRUD and auth enforcement, and the Settings UI has a Notifications panel. Mobile app requests notification permission and registers its FCM token with the backend.

## Must-Haves

- `DeviceToken` and `NotificationPreferences` SQLAlchemy models with Alembic migration 021
- `NotificationService` with `register_token()`, `unregister_token()`, `send_notification()`, `send_to_user()`, `should_suppress()` — graceful no-op when Firebase not configured
- API router: `POST /api/notifications/register`, `GET/PUT /api/notifications/preferences`, `POST /api/notifications/test`
- Context-aware suppression: calendar_busy, quiet hours (midnight-spanning), disabled notification types
- Stale token cleanup on `messaging.UnregisteredError`
- "Notifications" panel in Settings UI with quiet hours, suppress-when-busy toggle, notification types
- `firebase-admin` added to `pyproject.toml` dependencies
- `firebase_credentials_path` setting in `config.py`
- Mobile app: `expo-notifications` integration with permission request, native FCM token retrieval, backend registration
- Unit tests for NotificationService suppression logic and token CRUD
- Router tests for all notification endpoints with auth enforcement

## Proof Level

- This slice proves: integration (backend notification infrastructure + mobile token registration)
- Real runtime required: no (FCM mocked in tests; real dispatch needs Firebase credentials)
- Human/UAT required: yes (receiving a real push notification on a device requires manual test via `/api/notifications/test`)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py tests/test_notification_router.py -v` — all tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py -v -k "suppress"` — suppression tests specifically pass
- `grep -q "firebase-admin" backend/pyproject.toml` — dependency added
- `grep -q "firebase_credentials_path" backend/app/config.py` — config setting exists
- `grep -q "Notifications" backend/app/templates/browser/settings_page.html` — settings sidebar button exists
- `grep -q "expo-notifications" mobile/package.json` — mobile dependency added

## Observability / Diagnostics

- Runtime signals: `notification.sent` (user_id, type, token_prefix), `notification.suppressed` (user_id, reason), `notification.token_expired` (user_id, token_prefix), `notification.skipped` (reason=firebase_not_configured)
- Inspection surfaces: `GET /api/notifications/preferences` (user prefs), `POST /api/notifications/test` (diagnostic send), `device_tokens` + `notification_preferences` SQLite tables
- Failure visibility: `messaging.UnregisteredError` → token auto-deleted + logged; firebase_app=None → no-op with warning log; `should_suppress()` returns reason string for logging
- Redaction constraints: FCM tokens logged as prefix only (first 20 chars + "...")

## Integration Closure

- Upstream surfaces consumed: `ContextService.get_current()` from S01 for suppression decisions, `ContextBroadcast` publish pattern from S01 for notification events, `RulesEngine` from S02 (calendar_busy context field), `PersonaService` on `app.state`, Settings page sidebar pattern from S02
- New wiring introduced: `app.state.notification_service` in main.py lifespan, `get_notification_service()` dependency, notification router mounted in main.py, "Notifications" sidebar category in settings_page.html, `expo-notifications` plugin in mobile app.json
- What remains before milestone is truly usable end-to-end: S07 integration test proving full loop (geofence → context → rule → persona switch → notification filtering → workspace update)

## Tasks

- [ ] **T01: DeviceToken + NotificationPreferences models, migration 021, and NotificationService** `est:45m`
  - Why: Foundation layer — all other notification work depends on the data model and service logic
  - Files: `backend/app/context/notification_models.py`, `backend/app/context/notification_service.py`, `backend/migrations/versions/021_device_tokens.py`, `backend/app/config.py`, `backend/pyproject.toml`, `backend/tests/test_notification_service.py`
  - Do: Create `DeviceToken` model (user_id FK CASCADE, token unique, platform, device_name, timestamps) and `NotificationPreferences` model (user_id FK CASCADE unique, enabled, quiet_hours_start/end as "HH:MM" strings, suppress_when_busy bool, enabled_types JSON string). Create Alembic migration 021 chaining from 020. Add `firebase_credentials_path: str = ""` to Settings in config.py. Add `firebase-admin~=6.7` to pyproject.toml dependencies. Build `NotificationService` with: `register_token()` (upsert by token value), `unregister_token()`, `get_tokens_for_user()`, `get_preferences()`/`update_preferences()`, `should_suppress(user_id)` checking calendar_busy (via ContextService), quiet hours (midnight-spanning: `now >= start OR now < end`), and enabled flag. `send_notification(token, title, body, data)` wraps `messaging.send()` in `asyncio.to_thread()`, catches `UnregisteredError` to auto-delete stale tokens. `send_to_user(user_id, title, body, data)` fans out to all user tokens with suppression check. No-op mode when `firebase_app is None`. Write 15+ unit tests covering: suppression for calendar_busy, quiet hours (including midnight span), disabled notifications, disabled type, no-token user, token CRUD (register/unregister/list), stale token cleanup, no-op mode, preferences CRUD.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py -v` — all pass
  - Done when: Service tests pass, migration file exists and chains from 020, firebase-admin in pyproject.toml, config has firebase_credentials_path

- [ ] **T02: Notification API router, main.py wiring, and Settings UI panel** `est:40m`
  - Why: Exposes notification infrastructure via HTTP endpoints and gives users a UI to manage preferences
  - Files: `backend/app/context/notification_router.py`, `backend/app/main.py`, `backend/app/dependencies.py`, `backend/app/browser/settings.py`, `backend/app/templates/browser/settings_page.html`, `backend/app/templates/browser/_notification_preferences.html`, `frontend/static/css/settings.css`, `backend/tests/test_notification_router.py`
  - Do: Create notification router with 4 endpoints: `POST /api/notifications/register` (register device token, 201), `GET /api/notifications/preferences` (return user prefs), `PUT /api/notifications/preferences` (update prefs), `POST /api/notifications/test` (send test notification to all user devices). Wire `NotificationService` into `app.state.notification_service` in main.py lifespan (initialize with firebase credentials from config — if path empty or file missing, pass `firebase_app=None`). Add `get_notification_service()` to dependencies.py. Mount notification router in main.py. Add "Notifications" sidebar button with bell icon in settings_page.html. Create `_notification_preferences.html` template partial with: enable/disable master toggle, quiet hours start/end time inputs, suppress-when-busy checkbox, notification type checkboxes (overdue_tasks, validation_warnings, context_changes). Add browser route `GET /browser/settings/notification-preferences` in settings.py. Write 12+ router tests covering: register token (201), duplicate token (upsert), get/update preferences, test notification, auth enforcement on all endpoints, invalid payload handling.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_notification_router.py -v` — all pass; `grep -q "notification_service" backend/app/main.py`
  - Done when: Router tests pass, NotificationService on app.state, settings UI has Notifications panel with quiet hours and suppress-when-busy controls

- [ ] **T03: Context-aware notification dispatch hook and integration tests** `est:30m`
  - Why: Connects the notification system to the context update flow — the core value prop of "context filtering"
  - Files: `backend/app/context/router.py`, `backend/app/context/notification_service.py`, `backend/tests/test_notification_service.py`, `backend/tests/test_notification_router.py`
  - Do: Add a notification dispatch hook in `update_context()` in `context/router.py` — after the existing rule evaluation block, if the context update contains notable state changes (calendar_busy transitioning to False = "focus block ended", or location_zone change), dispatch a notification via `notification_service.send_to_user()`. The `send_to_user()` method already calls `should_suppress()` internally, so the router just fires and trusts the service to filter. Add structured logging: `notification.dispatch_triggered` with context fields. Add integration-style tests that verify the full suppress→skip and allow→send paths by mocking firebase_admin at the messaging.send level while using real service + router together. Verify midnight-spanning quiet hours edge case has a dedicated test.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py tests/test_notification_router.py -v` — all pass
  - Done when: Context update can trigger notification dispatch, suppression works end-to-end in tests, midnight-spanning quiet hours tested

- [ ] **T04: Mobile app expo-notifications integration** `est:35m`
  - Why: Completes the mobile side — the app needs to request permission, get the native FCM token, register it with the backend, and handle incoming notifications
  - Files: `mobile/package.json`, `mobile/app.json`, `mobile/src/services/notifications.ts`, `mobile/src/api/client.ts`, `mobile/src/app/(app)/(tabs)/settings.tsx`, `mobile/src/app/(app)/_layout.tsx`
  - Do: Add `expo-notifications` and `expo-device` to mobile/package.json. Add `expo-notifications` plugin to app.json (with Android notification channel config). Create `mobile/src/services/notifications.ts` with: `registerForPushNotifications(client)` — checks `Device.isDevice`, requests permission, gets native token via `getDevicePushTokenAsync()`, calls `client.registerPushToken()`. `setupNotificationHandler()` — registers foreground notification handler (display even when app is open) and response handler (tap to navigate). Add `registerPushToken(token, platform)`, `getNotificationPreferences()`, `updateNotificationPreferences(prefs)` methods to `SemPKMClient` in client.ts. Add corresponding TypeScript interfaces. Update settings.tsx with a "Push Notifications" section showing permission status and a toggle. Call `registerForPushNotifications()` from the app layout after successful authentication. Add Android notification channel setup in the layout's useEffect.
  - Verify: `cd mobile && npx tsc --noEmit` — TypeScript compiles without errors; `grep -q "expo-notifications" mobile/package.json && grep -q "expo-notifications" mobile/app.json && test -f mobile/src/services/notifications.ts`
  - Done when: TypeScript compiles cleanly, notification service file exists with permission request + token registration + handlers, client.ts has notification API methods, settings screen has notification toggle

## Files Likely Touched

- `backend/app/context/notification_models.py` (new)
- `backend/app/context/notification_service.py` (new)
- `backend/app/context/notification_router.py` (new)
- `backend/migrations/versions/021_device_tokens.py` (new)
- `backend/app/config.py`
- `backend/pyproject.toml`
- `backend/app/main.py`
- `backend/app/dependencies.py`
- `backend/app/context/router.py`
- `backend/app/browser/settings.py`
- `backend/app/templates/browser/settings_page.html`
- `backend/app/templates/browser/_notification_preferences.html` (new)
- `frontend/static/css/settings.css`
- `backend/tests/test_notification_service.py` (new)
- `backend/tests/test_notification_router.py` (new)
- `mobile/package.json`
- `mobile/app.json`
- `mobile/src/services/notifications.ts` (new)
- `mobile/src/api/client.ts`
- `mobile/src/app/(app)/(tabs)/settings.tsx`
- `mobile/src/app/(app)/_layout.tsx`
