---
id: T02
parent: S06
milestone: M037
provides:
  - Notification API router with 4 endpoints (register, preferences CRUD, test-send)
  - NotificationService wired into main.py lifespan with Firebase initialization
  - get_notification_service() dependency in dependencies.py
  - "Notifications" panel in Settings UI with quiet hours, suppress-when-busy, and type checkboxes
  - Browser route for notification preferences partial
  - 17 router tests covering CRUD, validation, auth enforcement, and diagnostic test-send
key_files:
  - backend/app/context/notification_router.py
  - backend/app/main.py
  - backend/app/dependencies.py
  - backend/app/browser/settings.py
  - backend/app/templates/browser/settings_page.html
  - backend/app/templates/browser/_notification_preferences.html
  - frontend/static/css/settings.css
  - backend/tests/test_notification_router.py
key_decisions:
  - Router uses inline _get_notification_service() helper from request.app.state rather than Depends(get_notification_service) — simpler for test setup and avoids adding the dependency to the override chain
  - Test-send endpoint pre-checks suppression separately from send_to_user() so it can report suppression reason to the user in the response
patterns_established:
  - Notification preference partial uses the same htmx lazy-load pattern as context rules (hx-get + hx-trigger="intersect once")
  - Router tests use FastAPI dependency override for auth with a separate noauth_client fixture for 401 enforcement tests
observability_surfaces:
  - POST /api/notifications/test returns {sent_count, suppressed, reason} — diagnostic surface for push notification verification
  - GET /api/notifications/preferences — runtime inspection of user suppression config
  - HTTP 503 when notification_service not on app.state — explicit failure mode
  - Firebase init logged at startup (success or firebase_not_configured)
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Notification API router, main.py wiring, and Settings UI panel

**Add notification API router with 4 authenticated endpoints, wire NotificationService into app lifespan, create Settings UI panel with quiet hours and suppress-when-busy controls, and 17 router tests**

## What Happened

Created `notification_router.py` with 4 endpoints: POST /register (201 with token info, platform validation), GET/PUT /preferences (with HH:MM format validation for quiet hours), and POST /test (diagnostic send with suppression reporting). All endpoints enforce authentication via `get_current_user_or_api`.

Wired NotificationService into main.py lifespan — initializes Firebase Admin from `firebase_credentials_path` config setting (no-op when path empty or missing). Added `get_notification_service()` to dependencies.py. Mounted the notification router alongside existing context routers.

Added "Notifications" sidebar button with bell icon in settings_page.html and a corresponding panel div with htmx lazy-loading. Created `_notification_preferences.html` template partial with: master enable/disable toggle, quiet hours time inputs, suppress-when-busy toggle, notification type checkboxes (overdue_tasks, validation_warnings, context_changes), and a "Send Test Notification" button with inline result display. All controls save via fetch() to the PUT /preferences endpoint.

Added notification preference CSS styles to settings.css following the existing context-rules card pattern.

Wrote 17 router tests covering: register success (201), missing platform (422), invalid platform (422), duplicate token upsert, default preferences, updated preferences, partial update, full update, empty body (422), invalid quiet hours format (422), test-send with no tokens, test-send with suppression, test-send with tokens, and auth enforcement on all 4 endpoints.

## Verification

All task-level and relevant slice-level checks pass:

- `cd backend && .venv/bin/python -m pytest tests/test_notification_router.py -v` — 17/17 pass
- `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py tests/test_notification_router.py -v` — 44/44 pass
- `grep -q "notification_service" backend/app/main.py` — found
- `grep -q "get_notification_service" backend/app/dependencies.py` — found
- `grep -q "Notifications" backend/app/templates/browser/settings_page.html` — found
- `test -f backend/app/templates/browser/_notification_preferences.html` — exists
- `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py -v -k "suppress"` — 11/11 pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_notification_router.py -v` | 0 | ✅ pass | 0.48s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py tests/test_notification_router.py -v` | 0 | ✅ pass | 0.83s |
| 3 | `grep -q "notification_service" backend/app/main.py` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "get_notification_service" backend/app/dependencies.py` | 0 | ✅ pass | <0.1s |
| 5 | `grep -q "Notifications" backend/app/templates/browser/settings_page.html` | 0 | ✅ pass | <0.1s |
| 6 | `test -f backend/app/templates/browser/_notification_preferences.html` | 0 | ✅ pass | <0.1s |
| 7 | `cd backend && .venv/bin/python -m pytest tests/test_notification_service.py -v -k "suppress"` | 0 | ✅ pass | 0.36s |

## Diagnostics

- `POST /api/notifications/test` returns `{sent_count, suppressed, reason}` — built-in diagnostic for verifying push delivery and suppression logic
- `GET /api/notifications/preferences` — inspect current suppression config for any authenticated user
- Firebase initialization success/failure logged at startup: `"Firebase Admin initialized from <path>"` or `"notification.skipped reason=firebase_not_configured"`
- If `notification_service` is not on `app.state`, all endpoints return HTTP 503 with explicit error message

## Deviations

- Added `import os` in main.py lifespan for `os.path.isfile()` check on Firebase credentials — not explicitly in plan but necessary for file existence check
- Used 422 (UNPROCESSABLE_ENTITY) for empty preferences update body — matches FastAPI convention for invalid request bodies

## Known Issues

- The DeprecationWarning about `HTTP_422_UNPROCESSABLE_ENTITY` in one test comes from FastAPI/Starlette internals (they've renamed it to `HTTP_422_UNPROCESSABLE_CONTENT`). Non-blocking; will resolve when FastAPI updates.

## Files Created/Modified

- `backend/app/context/notification_router.py` — new: 4-endpoint API router with Pydantic validation
- `backend/app/main.py` — added: notification_router import, NotificationService init in lifespan, router mount
- `backend/app/dependencies.py` — added: get_notification_service() dependency function
- `backend/app/browser/settings.py` — added: notification_preferences_panel route
- `backend/app/templates/browser/settings_page.html` — added: Notifications sidebar button + panel div
- `backend/app/templates/browser/_notification_preferences.html` — new: notification preferences template partial
- `frontend/static/css/settings.css` — added: notification preference styles
- `backend/tests/test_notification_router.py` — new: 17 router tests
- `.gsd/milestones/M037/slices/S06/tasks/T02-PLAN.md` — added: Observability Impact section (pre-flight fix)
