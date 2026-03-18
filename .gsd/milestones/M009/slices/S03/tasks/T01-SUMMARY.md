---
id: T01
parent: S03
milestone: M009
provides:
  - Admin router with 7 endpoints for app list, detail, install, start, stop, restart, uninstall
  - Jinja2 list template with status badges, version pills, uptime, PID, action buttons
  - Jinja2 detail template with permissions, logs, actions, and S05/S06 placeholders
  - 33 unit tests covering all endpoints, htmx partials, role enforcement, error paths
key_files:
  - backend/app/apps/admin_router.py
  - backend/app/templates/admin/apps/list.html
  - backend/app/templates/admin/apps/detail.html
  - backend/tests/test_app_admin.py
key_decisions:
  - Router uses standalone APIRouter (no prefix) with full /admin/apps paths, since it will be included directly in main.py rather than nested under the existing admin router
  - Lifecycle actions (start/stop/restart) redirect to detail page via 303; install/uninstall redirect to list page
  - Flash messages passed via query params (success/error) matching existing admin redirect patterns
patterns_established:
  - App admin router pattern: _templates_response helper, _is_htmx_request check, require_role("owner") on all endpoints
  - Test pattern: real SQLite DB for auth, mocked app_manager on app.state, httpx AsyncClient with ASGITransport
observability_surfaces:
  - logger.info for all lifecycle actions with app_id and user email
  - /admin/apps list shows live status (running/stopped/error/installing) per app
  - /admin/apps/{app_id} detail shows PID, uptime, restart count, error_message from DB, log output from ring buffer
  - HTTP 404 returned for unknown app_id on detail page
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Admin router, templates, and unit tests

**Created admin router with 7 endpoints, list/detail Jinja2 templates, and 33 unit tests for the /admin/apps app management portal.**

## What Happened

Built the complete admin router at `backend/app/apps/admin_router.py` with all 7 endpoints: GET list, GET detail, POST install, POST start/stop/restart/uninstall. All endpoints use `require_role("owner")` and support htmx partial rendering via the `HX-Request` header check.

The list template (`admin/apps/list.html`) extends `base.html` and shows app cards with status badges (color-coded running/stopped/error/installing), version pills, uptime, PID, and quick action buttons. Includes an install form and empty state messaging.

The detail template (`admin/apps/detail.html`) shows a full app dashboard: header with name/version/status, stats bar (PID/uptime/restarts), permissions table from manifest, log viewer from ring buffer, lifecycle action buttons, and placeholder sections for task history (S05) and renderer assignments (S06).

Wrote 33 unit tests in `backend/tests/test_app_admin.py` covering: list rendering (7 tests), detail rendering (9 tests), install with success/error paths (3 tests), lifecycle actions calling correct manager methods (6 tests), role enforcement for all 7 endpoints + unauthenticated access (8 tests). Tests use real SQLite for auth and mocked AppManager on app.state.

## Verification

- `uv run python -c "from app.apps.admin_router import app_admin_router; print('OK')"` — import succeeds, 7 routes registered
- `uv run python -m pytest tests/test_app_admin.py -v` — all 33 tests pass in 1.37s

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `uv run python -c "from app.apps.admin_router import app_admin_router; ..."` | 0 | ✅ pass | 3s |
| 2 | `uv run python -m pytest tests/test_app_admin.py -v` | 0 | ✅ pass | 4.3s |
| 3 | `grep -c "location /app-static/" frontend/nginx.conf` | 1 | ⏳ T02 scope | — |
| 4 | `grep -c "location /app/" frontend/nginx.conf` | 1 | ⏳ T02 scope | — |
| 5 | `grep -c "./apps:/app/apps" docker-compose.yml` | 1 | ⏳ T02 scope | — |
| 6 | `grep -c "Applications" backend/app/templates/components/_sidebar.html` | 1 | ⏳ T03 scope | — |
| 7 | `grep -c "Applications" backend/app/templates/admin/index.html` | 1 | ⏳ T03 scope | — |
| 8 | `grep -c "app_admin_router" backend/app/main.py` | 1 | ⏳ T03 scope | — |

## Diagnostics

- **Admin router logs**: Filter by `app.apps.admin_router` — emits INFO for install/start/stop/restart/uninstall with app_id and user email
- **Template rendering**: Check `GET /admin/apps` response for status badges; `GET /admin/apps/{app_id}` for permissions/logs/error_message
- **404 behavior**: `GET /admin/apps/nonexistent` returns HTTP 404 with JSON detail when app not found in DB

## Deviations

None. All plan steps executed as specified.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/admin_router.py` — new admin router with 7 endpoints (list, detail, install, start, stop, restart, uninstall)
- `backend/app/templates/admin/apps/list.html` — app list page template with status badges, install form, action buttons
- `backend/app/templates/admin/apps/detail.html` — app detail page template with status, permissions, logs, actions, placeholders
- `backend/tests/test_app_admin.py` — 33 unit tests covering all endpoints, htmx partials, role enforcement, error paths
