---
estimated_steps: 5
estimated_files: 8
skills_used:
  - best-practices
  - test
---

# T02: Notification API router, main.py wiring, and Settings UI panel

**Slice:** S06 — Push Notifications with Context Filtering
**Milestone:** M037

## Description

Expose the NotificationService via HTTP API endpoints and wire it into the FastAPI application lifecycle. Add a "Notifications" panel to the Settings UI allowing users to configure quiet hours, suppress-when-busy, and notification type preferences. All endpoints require authentication. Router tests verify CRUD, auth enforcement, and the test-notification diagnostic endpoint.

## Steps

1. **Create `backend/app/context/notification_router.py`** with 4 endpoints:
   - `POST /api/notifications/register` — accepts `{token, platform, device_name?}`, calls `service.register_token()`, returns 201 with token info. Validate platform is "ios" or "android".
   - `GET /api/notifications/preferences` — returns user's notification preferences (or defaults if no row).
   - `PUT /api/notifications/preferences` — accepts `{enabled?, quiet_hours_start?, quiet_hours_end?, suppress_when_busy?, enabled_types?}`, calls `service.update_preferences()`, returns updated prefs.
   - `POST /api/notifications/test` — sends a test notification to all user's registered devices. Calls `service.send_to_user(user_id, "SemPKM Test", "Push notifications are working!", notification_type="test")`. Returns `{sent_count, suppressed, reason?}`.
   - All endpoints use `Depends(get_current_user_or_api)` for dual-auth (session + API key).
   - Router prefix: `/api/notifications`, tags: `["notifications"]`.

2. **Wire into `backend/app/main.py`**:
   - Import `notification_router` and mount via `app.include_router(notification_router)`.
   - In the lifespan function, initialize `NotificationService`:
     ```python
     from app.context.notification_service import NotificationService
     firebase_app = None
     creds_path = settings.firebase_credentials_path
     if creds_path and os.path.isfile(creds_path):
         import firebase_admin
         from firebase_admin import credentials
         cred = credentials.Certificate(creds_path)
         firebase_app = firebase_admin.initialize_app(cred)
     app.state.notification_service = NotificationService(
         async_session_factory, app.state.context_service, firebase_app
     )
     ```
   - Add `get_notification_service()` to `backend/app/dependencies.py` following the `get_context_service()` pattern.

3. **Add Settings UI "Notifications" panel**:
   - In `backend/app/templates/browser/settings_page.html`: add a sidebar button after the Context Rules button with bell icon (`<i data-lucide="bell">`) and text "Notifications", `data-category="notifications"`, `onclick="showSettingsCategory('notifications')"`. Add a corresponding `<div class="settings-category-panel" id="category-notifications">` with `hx-get="/browser/settings/notification-preferences"` and `hx-trigger="intersect once"`.
   - Create `backend/app/templates/browser/_notification_preferences.html` partial:
     - Master enable/disable toggle
     - Quiet hours: two `<input type="time">` fields for start/end
     - "Suppress when busy" checkbox (suppress notifications during calendar focus blocks)
     - Notification type checkboxes: overdue_tasks, validation_warnings, context_changes
     - "Send Test Notification" button calling `POST /api/notifications/test` via fetch()
     - Status message area showing result of test send
   - Add browser route `GET /browser/settings/notification-preferences` in `backend/app/browser/settings.py` following the `context_rules_panel` pattern. Fetch preferences via the service and render the template.
   - Add notification preference styles to `frontend/static/css/settings.css` — follow the context-rules card pattern.

4. **Create `backend/tests/test_notification_router.py`** with 12+ tests:
   - Register token: success (201), missing platform (422), invalid platform (422)
   - Get preferences: default (no row), after update
   - Update preferences: partial update, full update, invalid quiet hours format
   - Test notification: no tokens (sends 0), with suppression active
   - Auth enforcement: all 4 endpoints return 401/403 without auth
   - Duplicate token registration (upsert behavior)
   - Use httpx AsyncClient with `ASGITransport(app=app)` pattern matching `test_context_router.py`.

5. **Verify wiring**: Confirm `notification_service` is accessible via `request.app.state.notification_service` and the router is mounted by checking imports and include_router call.

## Must-Haves

- [ ] 4 API endpoints with dual-auth (session + API key)
- [ ] NotificationService initialized in main.py lifespan (no-op if no Firebase credentials)
- [ ] `get_notification_service()` dependency function
- [ ] Settings UI "Notifications" sidebar button + panel with quiet hours and suppress-when-busy
- [ ] `_notification_preferences.html` template with master toggle, quiet hours, suppress-when-busy, type checkboxes, test button
- [ ] Browser route for settings partial
- [ ] 12+ router tests all passing

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_notification_router.py -v` — all tests pass
- `grep -q "notification_service" backend/app/main.py` — wired in lifespan
- `grep -q "get_notification_service" backend/app/dependencies.py` — dependency exists
- `grep -q "Notifications" backend/app/templates/browser/settings_page.html` — sidebar button exists
- `test -f backend/app/templates/browser/_notification_preferences.html` — template exists

## Inputs

- `backend/app/context/notification_service.py` — NotificationService from T01
- `backend/app/context/notification_models.py` — models from T01
- `backend/app/main.py` — lifespan and router mounting
- `backend/app/dependencies.py` — dependency function pattern
- `backend/app/browser/settings.py` — settings route pattern (context_rules_panel)
- `backend/app/templates/browser/settings_page.html` — sidebar button pattern
- `backend/app/templates/browser/_context_rules.html` — template partial pattern
- `frontend/static/css/settings.css` — existing settings styles
- `backend/tests/test_context_router.py` — router test pattern
- `backend/tests/test_rules_router.py` — router test pattern

## Expected Output

- `backend/app/context/notification_router.py` — 4-endpoint API router
- `backend/app/main.py` — modified: NotificationService initialization + router mount
- `backend/app/dependencies.py` — modified: get_notification_service()
- `backend/app/browser/settings.py` — modified: notification_preferences_panel route
- `backend/app/templates/browser/settings_page.html` — modified: Notifications sidebar button + panel div
- `backend/app/templates/browser/_notification_preferences.html` — new template partial
- `frontend/static/css/settings.css` — modified: notification preference styles
- `backend/tests/test_notification_router.py` — 12+ router tests

## Observability Impact

- **New HTTP endpoints:** `POST /api/notifications/register` (201 on success), `GET /api/notifications/preferences`, `PUT /api/notifications/preferences`, `POST /api/notifications/test` — all return structured JSON with diagnostic info (sent_count, suppressed, reason).
- **Test endpoint diagnostics:** `POST /api/notifications/test` returns `{sent_count, suppressed, reason}` — a built-in diagnostic surface for verifying push notification delivery and suppression without external tools.
- **Service unavailable signal:** If `notification_service` is not on `app.state`, endpoints return HTTP 503 with `"Notification service not available"` — explicit failure mode instead of AttributeError.
- **Firebase init logging:** Lifespan logs `"Firebase Admin initialized from <path>"` on success, or `"notification.skipped reason=firebase_not_configured"` when no credentials — visible in container logs.
- **Inspection via API:** `GET /api/notifications/preferences` exposes the current suppression config for any authenticated user, enabling runtime debugging of why notifications are or aren't being delivered.
