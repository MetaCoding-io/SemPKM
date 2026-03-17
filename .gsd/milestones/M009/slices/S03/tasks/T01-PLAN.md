---
estimated_steps: 8
estimated_files: 4
---

# T01: Admin router, templates, and unit tests

**Slice:** S03 — Admin Portal & Docker/nginx Integration
**Milestone:** M009

## Description

Create the admin router for the app platform at `backend/app/apps/admin_router.py` with HTML endpoints for list, detail, install, and lifecycle actions. Create two Jinja2 templates (list + detail) following existing admin patterns. Write unit tests covering all endpoints with mocked AppManager and AppRegistry.

## Steps

1. **Create `backend/app/apps/admin_router.py`** with `app_admin_router = APIRouter()` (no prefix — routes use full `/admin/apps` paths since it's included directly in main.py, not nested under existing admin router):
   - `GET /admin/apps` — list page. Get `app_manager` from `request.app.state.app_manager`. Call `app_manager.registry.list_apps()` to get app IDs, then `app_manager.get_status(app_id)` for each. Also get `app_manager.registry.get_manifest(app_id)` for display name/description. Build context with apps list. Check `HX-Request` header — if present, return with `block_name="content"`. Require `require_role("owner")`.
   - `GET /admin/apps/{app_id}` — detail page. Get status, manifest, and logs. Build context with all three. Same htmx partial pattern. 404 if app not found (status dict returns `status: "not_found"`).
   - `POST /admin/apps/install` — accept `app_path` form field. Call `app_manager.install(Path(app_path))`. Redirect to list with success message. Catch `ValueError`/`RuntimeError` and redirect with error message.
   - `POST /admin/apps/{app_id}/start` — call `app_manager.start(app_id)`. Return htmx redirect or partial refresh.
   - `POST /admin/apps/{app_id}/stop` — call `app_manager.stop(app_id)`.
   - `POST /admin/apps/{app_id}/restart` — call `app_manager.restart(app_id)`.
   - `POST /admin/apps/{app_id}/uninstall` — call `app_manager.uninstall(app_id)`. Redirect to list.
   - All endpoints use `user: User = Depends(require_role("owner"))`.
   - Use a local `_templates_response()` helper (same pattern as existing admin router) for consistent block rendering.

2. **Create `backend/app/templates/admin/apps/list.html`** extending `base.html`:
   - Back-link to `/admin` (admin portal index)
   - Page title "Applications"
   - Install form section: text input for app path + "Install" button (POST to `/admin/apps/install`)
   - Grid of app cards. Each card shows:
     - App name (from manifest `name` field) + version pill
     - Status badge (running=green, stopped=gray, error=red, installing=yellow)
     - Uptime (formatted from `uptime_seconds`), PID
     - Description (from manifest)
     - Quick action buttons: Start (if stopped/error), Stop (if running), Restart (if running)
   - Empty state: "No apps installed" message
   - Use `{% block content %}` for htmx partial rendering

3. **Create `backend/app/templates/admin/apps/detail.html`** extending `base.html`:
   - Back-link to `/admin/apps`
   - Header: app name + version pill + status badge
   - Status section: PID, uptime, restart count, error message (if any)
   - Permissions section: table listing approved permissions from manifest (commands, iriPrefix, network domains)
   - Data stats section: placeholder with "Data statistics will be available in a future update" (computing IRI-prefix counts is S05+ scope)
   - Logs section: `<pre>` block showing log lines from ring buffer, with "No log output" fallback
   - Actions section: Start/Stop/Restart buttons (conditional on status) + Uninstall button (with `hx-confirm`)
   - Task history placeholder: "Tasks will appear here when scheduler is active" (S05 scope)
   - Renderer assignments placeholder: "Renderer assignments will appear here when configured" (S06 scope)
   - Use `{% block content %}` for htmx partial rendering

4. **Create `backend/tests/test_app_admin.py`** with unit tests:
   - Use `httpx.AsyncClient` with `ASGITransport` pointing to the FastAPI app (same pattern as other admin tests in codebase)
   - Mock `app.state.app_manager` with a `MagicMock`/`AsyncMock` providing `registry`, `get_status()`, `get_logs()`, `install()`, `start()`, `stop()`, `restart()`, `uninstall()`
   - Mock `app.state.app_manager.registry` with `list_apps()` returning `["test-app"]` and `get_manifest()` returning a mock manifest
   - Test list endpoint returns 200 with app data in template context
   - Test detail endpoint returns 200 with status + manifest + logs
   - Test detail endpoint returns 404 for unknown app
   - Test install endpoint calls `manager.install()` with correct Path
   - Test install endpoint handles ValueError (invalid manifest)
   - Test start/stop/restart/uninstall endpoints call correct manager methods
   - Test role enforcement: mock a non-owner user, verify 403/redirect on admin endpoints
   - Test htmx partial rendering: send `HX-Request: true` header, verify response

## Must-Haves

- [ ] All 7 endpoints implemented with `require_role("owner")`
- [ ] htmx partial rendering on list and detail pages
- [ ] List template shows status badges, version, uptime for each app
- [ ] Detail template shows permissions, logs, action buttons, and S05/S06 placeholders
- [ ] Unit tests cover all endpoints with mocked services
- [ ] 404 on detail page for unknown app

## Verification

- `cd backend && python -m pytest tests/test_app_admin.py -v` — all tests pass
- `python -c "from app.apps.admin_router import app_admin_router; print('OK')"` — import succeeds

## Inputs

- `backend/app/apps/manager.py` — `AppManager` API: `get_status()`, `get_logs()`, `install()`, `start()`, `stop()`, `restart()`, `uninstall()`, `.registry` property
- `backend/app/apps/registry.py` — `AppRegistry` API: `list_apps()`, `get_manifest()`
- `backend/app/apps/manifest.py` — `AppManifestSchema` with fields: `appId`, `name`, `description`, `version`, `permissions` (with `.commands`, `.iriPrefix`, `.network`), `frontend`, `tasks`
- `backend/app/admin/router.py` — reference implementation for admin page patterns (htmx partial rendering, `require_role`, `templates_response` helper)
- `backend/app/templates/admin/model_detail.html` — reference template for detail page layout (header, stats bar, back-link, tabs)
- `backend/app/templates/admin/index.html` — reference for admin card layout
- `backend/app/auth/dependencies.py` — `require_role("owner")` dependency

## Expected Output

- `backend/app/apps/admin_router.py` — complete admin router with 7 endpoints
- `backend/app/templates/admin/apps/list.html` — app list page template
- `backend/app/templates/admin/apps/detail.html` — app detail page template
- `backend/tests/test_app_admin.py` — unit tests for all endpoints

## Observability Impact

- **New signals:** Admin router logs `app installed/started/stopped/restarted/uninstalled (by user X)` at INFO level for all lifecycle actions via `logger.info()`.
- **Inspection surfaces:** `/admin/apps` shows live status (running/stopped/error/installing) for each app. `/admin/apps/{app_id}` shows PID, uptime, restart count, error messages from DB, and log output from ring buffer.
- **Failure visibility:** HTTP 404 returned for unknown `app_id` on detail page. Install errors (ValueError/RuntimeError) rendered inline on list page. App error_message from DB shown on detail page.
- **Future agent inspection:** Check `GET /admin/apps/{app_id}` response for status dict, or look at `logger` output filtered by `app.apps.admin_router`.
