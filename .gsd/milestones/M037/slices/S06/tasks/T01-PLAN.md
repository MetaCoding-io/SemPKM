---
estimated_steps: 5
estimated_files: 6
skills_used:
  - best-practices
  - test
---

# T01: DeviceToken + NotificationPreferences models, migration 021, and NotificationService

**Slice:** S06 — Push Notifications with Context Filtering
**Milestone:** M037

## Description

Build the data model and service layer for push notifications. This creates the `DeviceToken` and `NotificationPreferences` SQLAlchemy models, the Alembic migration to create both tables, adds `firebase-admin` to dependencies, adds `firebase_credentials_path` to config, and implements `NotificationService` with token CRUD, preference management, context-aware suppression logic, and FCM dispatch (with no-op mode when Firebase isn't configured). Comprehensive unit tests validate all suppression scenarios.

## Steps

1. **Add `firebase-admin~=6.7` to `backend/pyproject.toml`** in the `dependencies` list and add `firebase_credentials_path: str = ""` to the `Settings` class in `backend/app/config.py`.

2. **Create `backend/app/context/notification_models.py`** with two SQLAlchemy models:
   - `DeviceToken`: UUID PK, `user_id` FK to `users.id` (CASCADE, indexed), `token` String(500) unique, `platform` String(10) — "ios"/"android", `device_name` String(200) nullable, `created_at`/`updated_at` DateTime with `server_default=func.now()`.
   - `NotificationPreferences`: UUID PK, `user_id` FK to `users.id` (CASCADE, unique+indexed), `enabled` Boolean default True, `quiet_hours_start` String(5) nullable (format "HH:MM"), `quiet_hours_end` String(5) nullable, `suppress_when_busy` Boolean default True, `enabled_types` String(500) nullable (JSON array as string, e.g. `'["overdue_tasks","validation_warnings"]'`).

3. **Create `backend/migrations/versions/021_device_tokens.py`** with `revision = "021"`, `down_revision = "020"`. Creates `device_tokens` and `notification_preferences` tables. Follow the exact pattern of `020_context_zones.py`.

4. **Create `backend/app/context/notification_service.py`** with `NotificationService` class:
   - Constructor: `__init__(self, session_factory, context_service=None, firebase_app=None)`. Store all three. If `firebase_app` is None, the service operates in no-op mode.
   - Token CRUD: `register_token(user_id, token, platform, device_name=None)` — upsert by token value (if token exists, update user_id/platform/device_name/updated_at; if not, insert). `unregister_token(token)` — delete by token. `get_tokens_for_user(user_id)` — return list.
   - Preferences: `get_preferences(user_id)` — return row or default dict. `update_preferences(user_id, **fields)` — upsert.
   - Suppression: `should_suppress(user_id, notification_type=None)` — async method. Checks in order: (a) preferences.enabled is False → suppress with reason "disabled", (b) notification_type not in preferences.enabled_types → suppress "type_disabled", (c) preferences.suppress_when_busy and context_service.get_current() has calendar_busy=True → suppress "calendar_busy", (d) quiet hours: parse start/end times, compare against current UTC time. Handle midnight span: if start > end (e.g. 22:00→07:00), suppress when `now >= start OR now < end`; else suppress when `start <= now < end`. Returns `(should_suppress: bool, reason: str | None)`.
   - Dispatch: `send_notification(token, title, body, data=None)` — if firebase_app is None, log warning and return None. Otherwise, construct `messaging.Message` and call `messaging.send()` via `asyncio.to_thread()`. Catch `messaging.UnregisteredError` → delete the stale token and log. Log token as prefix only (first 20 chars). `send_to_user(user_id, title, body, data=None, notification_type=None)` — call `should_suppress()` first. If suppressed, log reason and return. Otherwise, get all tokens for user and call `send_notification()` for each.

5. **Create `backend/tests/test_notification_service.py`** with 15+ unit tests:
   - Token CRUD: register new token, register duplicate token updates, unregister token, get tokens for user (multiple devices), get tokens for user with no tokens
   - Preferences: get default preferences (no row), update preferences, update partial preferences
   - Suppression: suppress when disabled, suppress when type disabled, suppress when calendar_busy, suppress during quiet hours (normal range e.g. 22:00-23:00), suppress during quiet hours (midnight span e.g. 22:00-07:00 — test both sides), allow when outside quiet hours, allow when all conditions pass
   - Dispatch: no-op mode (firebase_app=None), stale token cleanup on UnregisteredError
   - Use the same test session pattern as `tests/test_context_service.py` and `tests/test_rules_engine.py` — async pytest with in-memory SQLite.

## Must-Haves

- [ ] `DeviceToken` model with unique token constraint and CASCADE FK
- [ ] `NotificationPreferences` model with unique user_id constraint
- [ ] Migration 021 chains from 020, creates both tables
- [ ] `firebase-admin~=6.7` in pyproject.toml dependencies
- [ ] `firebase_credentials_path` in Settings class
- [ ] `should_suppress()` handles midnight-spanning quiet hours correctly
- [ ] No-op mode when firebase_app is None (log warning, skip send)
- [ ] Stale token auto-deletion on `messaging.UnregisteredError`
- [ ] FCM tokens logged as prefix only (first 20 chars + "...")
- [ ] 15+ unit tests all passing

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py -v` — all tests pass
- `grep -q "firebase-admin" backend/pyproject.toml` — dependency listed
- `grep -q "firebase_credentials_path" backend/app/config.py` — config field exists
- `test -f backend/migrations/versions/021_device_tokens.py` — migration exists
- `grep -q "down_revision.*020" backend/migrations/versions/021_device_tokens.py` — chains correctly

## Observability Impact

- Signals added: `notification.sent` (user_id, type, token_prefix), `notification.suppressed` (user_id, reason), `notification.token_expired` (token_prefix), `notification.skipped` (reason=firebase_not_configured)
- How a future agent inspects: query `device_tokens` and `notification_preferences` tables; check structured logs for suppression reasons
- Failure state exposed: `should_suppress()` returns reason string; `UnregisteredError` logged with token prefix

## Inputs

- `backend/app/context/models.py` — existing UserContext model pattern to follow
- `backend/app/context/service.py` — ContextService for `get_current()` in suppression checks
- `backend/migrations/versions/020_context_zones.py` — previous migration to chain from
- `backend/app/config.py` — Settings class to extend
- `backend/pyproject.toml` — dependencies list to extend
- `backend/tests/test_context_service.py` — test pattern to follow
- `backend/app/db/base.py` — Base class for models

## Expected Output

- `backend/app/context/notification_models.py` — DeviceToken + NotificationPreferences models
- `backend/app/context/notification_service.py` — NotificationService with CRUD, suppression, dispatch
- `backend/migrations/versions/021_device_tokens.py` — migration creating both tables
- `backend/app/config.py` — modified with firebase_credentials_path
- `backend/pyproject.toml` — modified with firebase-admin dependency
- `backend/tests/test_notification_service.py` — 15+ unit tests
