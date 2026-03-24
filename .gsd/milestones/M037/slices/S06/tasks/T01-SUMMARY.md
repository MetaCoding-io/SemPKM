---
id: T01
parent: S06
milestone: M037
provides:
  - DeviceToken and NotificationPreferences SQLAlchemy models
  - Alembic migration 021 creating device_tokens and notification_preferences tables
  - NotificationService with token CRUD, preference management, context-aware suppression, and FCM dispatch
  - firebase-admin dependency and firebase_credentials_path config setting
  - 27 unit tests covering all CRUD, suppression, and dispatch scenarios
key_files:
  - backend/app/context/notification_models.py
  - backend/app/context/notification_service.py
  - backend/migrations/versions/021_device_tokens.py
  - backend/tests/test_notification_service.py
key_decisions:
  - Lazy import for firebase_admin.messaging inside send_notification() to avoid import failure when firebase-admin is not installed or configured
  - _now parameter on should_suppress() for deterministic time testing without freezegun
  - enabled_types stored as JSON string in DB, deserialized on read — keeps schema simple without a join table
patterns_established:
  - Test files importing app.auth.models.User (noqa F401) to register the users table in Base.metadata for FK resolution in in-memory SQLite
  - Mock firebase_admin via sys.modules dict patching with explicit UnregisteredError subclass — avoids MagicMock "not a BaseException" TypeError
observability_surfaces:
  - notification.sent (token_prefix, msg_id)
  - notification.suppressed (user_id, reason)
  - notification.token_expired (token_prefix)
  - notification.skipped (reason=firebase_not_configured)
  - should_suppress() returns (bool, reason_string) for structured logging
duration: 25m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: DeviceToken + NotificationPreferences models, migration 021, and NotificationService

**Add notification data models, migration 021, and NotificationService with context-aware suppression, no-op FCM mode, and 27 unit tests**

## What Happened

Created the full notification data layer and service: two SQLAlchemy models (DeviceToken with unique token constraint and CASCADE FK, NotificationPreferences with unique user_id constraint), Alembic migration 021 chaining from 020, and NotificationService with token CRUD (register/unregister/list), preference management (get/update with upsert), context-aware suppression (disabled check, type filtering, calendar_busy via ContextService, midnight-spanning quiet hours), and FCM dispatch with no-op mode when firebase_app is None. Added firebase-admin~=6.7 to pyproject.toml and firebase_credentials_path to config.py Settings. Wrote 27 unit tests covering all paths including both sides of midnight-spanning quiet hours, stale token auto-deletion on UnregisteredError, and no-op mode.

## Verification

All task-level and relevant slice-level verification checks pass:

- `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py -v` — 27/27 pass
- `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py -v -k "suppress"` — 11/11 pass
- `grep -q "firebase-admin" backend/pyproject.toml` — found
- `grep -q "firebase_credentials_path" backend/app/config.py` — found
- `test -f backend/migrations/versions/021_device_tokens.py` — exists
- `grep -q "down_revision.*020" backend/migrations/versions/021_device_tokens.py` — chains correctly

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py -v` | 0 | ✅ pass | 0.54s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py -v -k "suppress"` | 0 | ✅ pass | 0.35s |
| 3 | `grep -q "firebase-admin" backend/pyproject.toml` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "firebase_credentials_path" backend/app/config.py` | 0 | ✅ pass | <0.1s |
| 5 | `test -f backend/migrations/versions/021_device_tokens.py` | 0 | ✅ pass | <0.1s |
| 6 | `grep -q "down_revision.*020" backend/migrations/versions/021_device_tokens.py` | 0 | ✅ pass | <0.1s |

## Diagnostics

- Query `device_tokens` and `notification_preferences` SQLite tables directly to inspect registered devices and user preferences
- Check structured logs for `notification.suppressed` (includes user_id and reason string), `notification.token_expired` (token prefix), `notification.skipped` (firebase not configured)
- `should_suppress()` returns a `(bool, reason_string)` tuple — reason is one of: "disabled", "type_disabled", "calendar_busy", "quiet_hours", or None
- FCM tokens logged as prefix only (first 20 chars + "...") per redaction constraint

## Deviations

- Added `_now` parameter to `should_suppress()` for deterministic time testing — not in the original plan but necessary to test quiet hours without freezegun or real clock dependency
- Test file requires `from app.auth.models import User` (noqa F401) to register the `users` table in SQLAlchemy metadata — existing context service tests have the same latent FK resolution issue

## Known Issues

- Existing `test_context_service.py` has the same FK resolution failure (NoReferencedTableError for users.id) — it needs the same `User` model import fix. Not addressed here since it's outside this task's scope.

## Files Created/Modified

- `backend/app/context/notification_models.py` — new: DeviceToken and NotificationPreferences SQLAlchemy models
- `backend/app/context/notification_service.py` — new: NotificationService with CRUD, suppression, dispatch
- `backend/migrations/versions/021_device_tokens.py` — new: migration creating device_tokens and notification_preferences tables
- `backend/app/config.py` — added firebase_credentials_path setting
- `backend/pyproject.toml` — added firebase-admin~=6.7 dependency
- `backend/tests/test_notification_service.py` — new: 27 unit tests
- `.gsd/milestones/M037/slices/S06/S06-PLAN.md` — added diagnostic verification step per pre-flight fix
