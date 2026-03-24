# S06 Research: Push Notifications with Context Filtering

## Summary

S06 introduces push notification infrastructure — entirely new to SemPKM. The backend gains a `NotificationService` wrapping `firebase-admin` Python SDK for FCM dispatch, a `device_tokens` SQLite table for per-user device registration, per-user notification preferences, and context-aware suppression logic (quiet hours, calendar_busy). The mobile app gains `expo-notifications` for token retrieval and notification display. All backend work follows the established service/router/model/migration pattern used by S01–S05.

**Complexity assessment: Targeted.** The technology is new (`firebase-admin`, `expo-notifications`) but the integration patterns are mature in this codebase. The core risk is Firebase credential management and the context-aware filtering logic, not the service wiring.

## Recommendation

1. **T01: DeviceToken model + migration 021 + NotificationService** — SQLAlchemy model, Alembic migration, service with `register_token()`, `send_notification()`, `send_to_user()`, context-aware `should_suppress()` logic. Include `firebase-admin` in `pyproject.toml` dependencies.
2. **T02: Notification API router + preferences** — `POST /api/notifications/register` (token registration), `GET/PUT /api/notifications/preferences` (quiet hours, enabled types), `POST /api/notifications/test` (send test notification). Wire to main.py lifespan + dependencies.
3. **T03: Context-aware filtering integration** — Hook notification dispatch into the context update flow. When notable events occur (overdue tasks, validation warnings), evaluate `should_suppress()` against current context before dispatching. Add notification preferences to Settings UI.
4. **T04: Mobile app expo-notifications integration** — Add `expo-notifications` dependency, implement token registration service, notification permission request flow, notification handler, and settings screen notification toggle.
5. **T05: Tests** — Unit tests for NotificationService (suppress logic, token CRUD, send mock), router tests, mobile-side can't be auto-tested but manual verification steps documented.

## Implementation Landscape

### Backend: New Files

| File | Purpose |
|------|---------|
| `backend/app/context/notification_models.py` | `DeviceToken` SQLAlchemy model — user_id FK, token string, platform (ios/android), device_name, created/updated_at |
| `backend/app/context/notification_service.py` | `NotificationService` — `register_token()`, `unregister_token()`, `send_notification()`, `send_to_user()`, `should_suppress()` |
| `backend/app/context/notification_router.py` | API router: `/api/notifications/register`, `/api/notifications/preferences`, `/api/notifications/test` |
| `backend/app/context/notification_preferences.py` | `NotificationPreferences` model or JSON column — quiet_hours_start/end, enabled_types list, suppress_when_busy bool |
| `backend/migrations/versions/021_device_tokens.py` | Creates `device_tokens` and `notification_preferences` tables |

### Backend: Modified Files

| File | Change |
|------|--------|
| `backend/app/main.py` | Register `NotificationService` on `app.state`, include notification router |
| `backend/app/dependencies.py` | Add `get_notification_service()` dependency function |
| `backend/app/config.py` | Add `firebase_credentials_path: str = ""` setting |
| `backend/pyproject.toml` | Add `firebase-admin` dependency |
| `backend/app/templates/browser/settings_page.html` | Add "Notifications" sidebar button + panel |
| `backend/app/browser/settings.py` | Add `notification_preferences_panel` route |
| `frontend/static/css/settings.css` | Notification preference styles |

### Mobile: New/Modified Files

| File | Change |
|------|--------|
| `mobile/package.json` | Add `expo-notifications`, `expo-device` (if not present) |
| `mobile/app.json` | Add `expo-notifications` plugin config |
| `mobile/src/services/notifications.ts` | New: permission request, token retrieval, registration with backend, notification listeners |
| `mobile/src/api/client.ts` | Add `registerPushToken()`, `getNotificationPreferences()`, `updateNotificationPreferences()` methods |
| `mobile/src/app/(app)/(tabs)/settings.tsx` | Add notification toggle, permission status display |

## Key Technical Findings

### firebase-admin Initialization

The SDK needs a Firebase service account JSON credential file. Two initialization paths:

```python
# Path 1: Service account file (recommended for self-hosted)
import firebase_admin
from firebase_admin import credentials, messaging

cred = credentials.Certificate('/app/config/firebase-service-account.json')
firebase_admin.initialize_app(cred)

# Path 2: Environment variable pointing to file
# GOOGLE_APPLICATION_CREDENTIALS=/app/config/firebase-service-account.json
firebase_admin.initialize_app()  # auto-discovers from env var
```

**Decision needed:** Use `Settings.firebase_credentials_path` pointing to a JSON file mounted via Docker volume (`./config:/app/config:ro`). If empty/missing, NotificationService operates in no-op mode (logs warning, silently skips sends). This prevents the service from crashing when Firebase isn't configured.

### FCM Message Dispatch

```python
from firebase_admin import messaging

message = messaging.Message(
    notification=messaging.Notification(
        title='Overdue Task',
        body='Task "Review PR #42" is past due'
    ),
    data={'type': 'overdue_task', 'object_iri': 'urn:sempkm:...'},
    token='DEVICE_FCM_TOKEN'
)
response = messaging.send(message)  # Returns message ID string
```

Key constraint: `messaging.send()` is synchronous. Should be called via `asyncio.to_thread()` in the async service to avoid blocking the event loop.

### expo-notifications Token Retrieval (Mobile)

Per D338, the mobile app uses `getDevicePushTokenAsync()` for native FCM/APNs tokens (not Expo push tokens):

```typescript
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';

async function registerForPushNotifications(client: SemPKMClient) {
  if (!Device.isDevice) return; // Simulator can't get push tokens

  const { status } = await Notifications.requestPermissionsAsync();
  if (status !== 'granted') return;

  // Native FCM/APNs token — NOT Expo push token
  const { data: token } = await Notifications.getDevicePushTokenAsync();
  await client.registerPushToken(token, Platform.OS);
}
```

Android requires a notification channel before requesting permissions (done in the `registerForPushNotificationsAsync` pattern from expo docs).

### Context-Aware Suppression Logic

The `should_suppress()` method checks:

1. **calendar_busy** — If `context.calendar_busy is True`, suppress (per roadmap "focus block" requirement)
2. **Quiet hours** — If current time is within user's configured quiet_hours_start/end window, suppress
3. **Notification type disabled** — If the notification type is not in user's `enabled_types` list, suppress
4. **No device token** — If user has no registered tokens, skip (not really suppression, just no target)

The current context is already available via `ContextService.get_current(user_id)` from S01. The rules engine (S02) provides `calendar_busy` in the context data.

### DeviceToken Model

```python
class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(500), unique=True)  # FCM tokens ~150-250 chars
    platform: Mapped[str] = mapped_column(String(10))  # "ios" or "android"
    device_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Unique constraint on `token` prevents duplicate registrations. User may have multiple devices (phone + tablet). `ON DELETE CASCADE` on user_id FK cleans up tokens when account is deleted (addresses CTX-18 from roadmap).

### NotificationPreferences Model

Two options: (a) separate table, or (b) JSON column on `user_context`. Separate table is cleaner — notification preferences are distinct from ephemeral context:

```python
class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default=sa.true())
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "22:00"
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)    # "07:00"
    suppress_when_busy: Mapped[bool] = mapped_column(Boolean(), default=True, server_default=sa.true())
    enabled_types: Mapped[str | None] = mapped_column(String(500), nullable=True)  # JSON array as string
```

### Firebase Not Configured: Graceful No-Op

The service must handle the case where Firebase credentials are not configured (common for dev instances, test environments). Pattern:

```python
class NotificationService:
    def __init__(self, session_factory, firebase_app=None):
        self._session_factory = session_factory
        self._firebase_app = firebase_app  # None = no-op mode

    async def send_notification(self, ...):
        if self._firebase_app is None:
            logger.warning("notification.skipped reason=firebase_not_configured")
            return None
        # ... actual FCM dispatch
```

### Settings UI: Notification Preferences Panel

Follow the Context Rules panel pattern from S02:
- Sidebar button with bell icon in `settings_page.html`
- `_notification_preferences.html` template partial
- `GET /browser/settings/notification-preferences` browser route
- htmx lazy-load with `hx-get` + `hx-trigger="intersect once"`

### Test Strategy

- **NotificationService unit tests:** Mock `firebase_admin.messaging.send()` — verify `should_suppress()` logic for calendar_busy, quiet hours, disabled types, and no-token scenarios. Verify token CRUD (register, unregister, list). Verify no-op mode when Firebase not configured.
- **Router tests:** Token registration (POST), preferences CRUD (GET/PUT), test notification (POST), auth enforcement on all endpoints.
- **No E2E for push notifications:** FCM requires real Firebase project + real device. Test endpoint (`POST /api/notifications/test`) serves as the manual verification hook.

## Constraints

1. **`firebase-admin` is synchronous** — `messaging.send()` blocks. Wrap in `asyncio.to_thread()`.
2. **Service account JSON file must be mounted** — Docker volume `./config:/app/config:ro` already exists. Add `FIREBASE_CREDENTIALS_PATH` env var.
3. **FCM tokens expire/rotate** — Tokens can become invalid. `messaging.send()` raises `messaging.UnregisteredError` for dead tokens. The service should catch this and delete the stale token.
4. **expo-notifications requires development build** — Won't work in Expo Go. Already addressed by D337 (development builds for native modules).
5. **Android 13+ requires runtime notification permission** — `Notifications.requestPermissionsAsync()` handles this, but the UX needs clear explanation of why notifications are needed.
6. **Quiet hours span midnight** — If start=22:00, end=07:00, the check must handle the day boundary: `now >= start OR now < end`, not `start <= now <= end`.

## Existing Patterns to Follow

| Pattern | Source | Applies To |
|---------|--------|------------|
| Service + router + model in context package | `context/service.py`, `context/router.py`, `context/models.py` | NotificationService, router, DeviceToken model |
| app.state registration in lifespan | `main.py` lines 358-369 | `app.state.notification_service` |
| Dependency function | `dependencies.py` lines 190-205 | `get_notification_service()` |
| Alembic migration chaining | `020_context_zones.py` → 021 | `021_device_tokens.py` |
| Settings sidebar panel | `settings_page.html` Context Rules button | Notifications button + panel |
| Browser route for settings partial | `settings.py` `context_rules_panel()` | `notification_preferences_panel()` |
| SemPKMClient method addition | `mobile/src/api/client.ts` zone methods | `registerPushToken()`, preferences methods |
| Permission request flow | `mobile/src/services/permissions.ts` | Notification permission request follows same structure |

## Sources

- firebase-admin Python SDK docs (Context7): initialization, messaging.send(), credentials.Certificate()
- expo-notifications docs (Context7): getDevicePushTokenAsync(), requestPermissionsAsync(), notification channels, handler setup
- D337: Expo managed workflow with development builds
- D338: Direct FCM via firebase-admin, getDevicePushTokenAsync for native tokens
- S01 Summary: ContextService on app.state, ContextBroadcast, SSE pattern, dual-auth
- S02 Summary: RulesEngine on app.state, integration hook pattern in update_context(), settings panel pattern
