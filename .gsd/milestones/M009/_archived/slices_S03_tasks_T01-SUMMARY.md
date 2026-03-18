---
id: T01
parent: S03
milestone: M009
provides:
  - Admin router with 7 endpoints for app platform management
  - List and detail Jinja2 templates with htmx partial rendering
  - 26 unit tests covering all endpoints, role enforcement, and htmx partials
key_files:
  - backend/app/apps/admin_router.py
  - backend/app/templates/admin/apps/list.html
  - backend/app/templates/admin/apps/detail.html
  - backend/tests/test_app_admin.py
key_decisions:
  - Used get_current_user dependency override in tests (not require_role) since require_role returns a new closure each call — can't be used as a dependency_overrides key
  - Router uses no prefix — routes use full /admin/apps paths since it will be included directly in main.py
patterns_established:
  - App admin test pattern using _create_test_app() with Jinja2Blocks from real template directory + mock AppManager + get_current_user override
observability_surfaces:
  - /admin/apps shows live status badges (running/stopped/error/installing) for all apps
  - /admin/apps/{app_id} shows PID, uptime, restart count, error messages, and log output
  - HTTP 404 for unknown app_id; install errors rendered inline
  - Logger at app.apps.admin_router logs lifecycle actions with user attribution
duration: 25m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Admin router, templates, and unit tests

**Created admin router with 7 endpoints, list/detail templates, and 26 passing unit tests for app platform management.**

## What Happened

Built `app_admin_router` with GET list, GET detail, POST install, POST start/stop/restart/uninstall endpoints. All use `require_role("owner")` and htmx partial rendering via `block_name="content"`. List page shows app cards with status badges (running/stopped/error/installing), version pills, uptime, PID, and quick-action buttons. Detail page shows status stats bar, permissions table from manifest, log viewer from ring buffer, action buttons conditional on status, and placeholder sections for task history (S05) and renderer assignments (S06).

Tests override `get_current_user` (not `require_role` directly) to bypass cookie/session auth while still exercising the role check. This avoids the closure-identity mismatch problem where `require_role("owner")` creates a new function each call.

## Verification

- `cd backend && python -m pytest tests/test_app_admin.py -v` — 26 passed, 0 failed
- `python -c "from app.apps.admin_router import app_admin_router; print('OK')"` — import succeeds

### Slice-level verification (T01 is task 1 of 3):
- ✅ `pytest tests/test_app_admin.py -v` — all endpoints tested
- ⬜ `grep -c "location /app-static/" frontend/nginx.conf` — T02 scope
- ⬜ `grep -c "location /app/" frontend/nginx.conf` — T02 scope
- ⬜ `grep -c "./apps:/app/apps" docker-compose.yml` — T02 scope
- ⬜ `grep -c "Applications" backend/app/templates/components/_sidebar.html` — T03 scope
- ⬜ `grep -c "Applications" backend/app/templates/admin/index.html` — T03 scope
- ⬜ `grep -c "app_admin_router" backend/app/main.py` — T03 scope
- ✅ Detail page returns 404 for unknown app_id (tested in test_detail_404_for_unknown_app)

## Diagnostics

- Check app admin endpoint behavior: `GET /admin/apps` (list) and `GET /admin/apps/{id}` (detail)
- Log output filtered by `app.apps.admin_router` shows lifecycle actions with user attribution
- Detail page error_message field surfaces AppManager crash/restart errors from DB
- 404 response for unknown app_id includes JSON detail message

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/admin_router.py` — new admin router with 7 endpoints (list, detail, install, start, stop, restart, uninstall)
- `backend/app/templates/admin/apps/list.html` — app list page with status badges, install form, action buttons
- `backend/app/templates/admin/apps/detail.html` — app detail page with permissions, logs, actions, S05/S06 placeholders
- `backend/tests/test_app_admin.py` — 26 unit tests covering all endpoints, htmx partials, error handling, role enforcement
- `.gsd/milestones/M009/slices/S03/S03-PLAN.md` — added failure-path verification check
- `.gsd/milestones/M009/slices/S03/tasks/T01-PLAN.md` — added Observability Impact section
