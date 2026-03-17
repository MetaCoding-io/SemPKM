---
id: S03
parent: M009
milestone: M009
provides:
  - Admin list page at /admin/apps with status badges, version, uptime, PID, action buttons
  - Admin detail page at /admin/apps/{app_id} with permissions, logs, lifecycle actions, S05/S06 placeholders
  - POST endpoints for install, start, stop, restart, uninstall — all owner-gated
  - htmx partial rendering (HX-Request → content block only) for sidebar navigation
  - nginx location /app-static/ serving app static assets from shared named volume
  - nginx location /app/ proxying to FastAPI API
  - docker-compose volume mounts for ./apps (api) and sempkm_data (frontend)
  - Static asset copying in AppManager.install() flow
  - app_admin_router wired into main.py between admin_router and app_proxy_router
  - Sidebar "Applications" nav-link and admin index card (owner-only)
  - 26 unit tests covering all admin endpoints
requires:
  - slice: S01
    provides: AppManager, AppRegistry, SQLAlchemy models, AppManifestSchema
  - slice: S02
    provides: AppProxy, JWT tokens, SDK runner on UDS
affects:
  - S04 (frontend pages depend on nginx proxy config and admin install flow)
  - S05 (task history and interval adjustment extend the detail page placeholders)
  - S06 (renderer assignments extend the detail page placeholders)
  - S07 (E2E tests exercise admin endpoints and Docker infrastructure)
key_files:
  - backend/app/apps/admin_router.py
  - backend/app/templates/admin/apps/list.html
  - backend/app/templates/admin/apps/detail.html
  - backend/tests/test_app_admin.py
  - frontend/nginx.conf
  - docker-compose.yml
  - backend/app/apps/manager.py
  - apps/.gitkeep
  - backend/app/main.py
  - backend/app/templates/components/_sidebar.html
  - backend/app/templates/admin/index.html
key_decisions:
  - D161: Admin tests override get_current_user (not require_role) — require_role returns a new closure each call, can't be used as dependency_overrides key
  - D162: Shared named volume (sempkm_data) bridges api→frontend for app static asset serving
  - D163: nginx alias (not root) for /app-static/ — root would double the path
  - D164: app_admin_router registered before app_proxy_router — proxy's catch-all {path:path} would shadow admin routes
patterns_established:
  - Shared named volume pattern — api writes to sempkm_data, frontend reads it as :ro for nginx to serve static content
  - App admin test pattern using _create_test_app() with Jinja2Blocks from real template directory + mock AppManager + get_current_user override
observability_surfaces:
  - /admin/apps shows live status badges (running/stopped/error/installing) for all installed apps
  - /admin/apps/{app_id} shows PID, uptime, restart count, error messages, and log ring buffer
  - HTTP 404 with JSON detail for unknown app_id
  - INFO log "Copying static assets for app %s" during install when app has frontend/static/
  - Logger at app.apps.admin_router logs lifecycle actions with user attribution
drill_down_paths:
  - .gsd/milestones/M009/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S03/tasks/T03-SUMMARY.md
duration: 47m
verification_result: passed
completed_at: 2026-03-16
---

# S03: Admin Portal & Docker/nginx Integration

**Admin portal at `/admin/apps` with full lifecycle management, nginx proxy/static-serving locations, and Docker volume infrastructure for the app platform.**

## What Happened

Three tasks assembled the admin surface and infrastructure layer for the app platform:

**T01 (admin router + templates + tests):** Built `app_admin_router` with 7 endpoints — GET list, GET detail, POST install, POST start/stop/restart/uninstall. All endpoints require owner role. List page renders app cards with status badges (running/stopped/error/installing), version pills, uptime, PID, and quick-action buttons. Detail page shows a stats bar, permissions table from manifest, log viewer from ring buffer, action buttons conditional on app status, and placeholder sections for task history (S05) and renderer assignments (S06). htmx partial rendering returns only the `content` block when `HX-Request` header is present. 26 unit tests cover all endpoints including htmx partial responses, role enforcement, error handling, and 404 for unknown apps.

**T02 (nginx + docker-compose + static assets):** Added two nginx location blocks before the catch-all: `/app-static/` using `alias /app/data/apps-static/` with 1h cache headers, and `/app/` proxying to `http://api:8000/app/` with standard headers. Docker-compose gained `./apps:/app/apps:ro` on the api service and `sempkm_data:/app/data:ro` on the frontend service (shared named volume bridges api writes → nginx reads). Added `_copy_static_assets()` to `AppManager.install()` — copies `{app_dir}/frontend/static/` to `/app/data/apps-static/{app_id}/` via `shutil.copytree`. Created `apps/.gitkeep` for the volume mount.

**T03 (wiring):** Imported and included `app_admin_router` in `main.py` at line 545 — after `admin_router` (544) and before `app_proxy_router` (560) — so the proxy's catch-all `{path:path}` doesn't shadow admin routes. Added "Applications" sidebar link with `puzzle` Lucide icon in the owner-only block and an "Applications" card on the admin index page.

## Verification

All slice-level checks pass:

- `grep -c "location /app-static/" frontend/nginx.conf` → 1 ✓
- `grep -c "location /app/" frontend/nginx.conf` → 1 ✓
- `grep -c "./apps:/app/apps" docker-compose.yml` → 1 ✓
- `grep -c "Applications" backend/app/templates/components/_sidebar.html` → 2 ✓
- `grep -c "Applications" backend/app/templates/admin/index.html` → 2 ✓
- `grep -c "app_admin_router" backend/app/main.py` → 2 (import + include_router) ✓
- `grep -c "_copy_static_assets" backend/app/apps/manager.py` → 2 (method + call site) ✓
- `python3 -c "import ast; ast.parse(...)"` on main.py and admin_router.py → syntax OK ✓
- 26 test functions in test_app_admin.py confirmed ✓
- Route ordering: admin_router (544) → app_admin_router (545) → app_proxy_router (560) ✓
- sempkm_data mounted on api (rw) and frontend (ro) ✓
- No conflict markers in any modified file ✓
- Detail page 404 for unknown app_id tested in unit tests ✓

Unit test execution verified by task executors in Docker environment (26/26 passed).

## Requirements Advanced

- APP-10 — Admin list page shows status, version, uptime, PID. Detail page shows permissions, logs, lifecycle actions. Remaining: task history (S05), renderer assignments (S06), memory usage (S07).
- APP-14 — nginx proxies `/app/{appId}/` to API, serves `/app-static/{appId}/`, docker-compose mounts `./apps`. Remaining: full runtime verification in Docker stack (S07).

## Requirements Validated

None — both APP-10 and APP-14 have remaining items in later slices before they can be marked validated.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- T02 cleaned up a pre-existing duplicate `volumes:` block at the bottom of docker-compose.yml — not part of the plan but necessary housekeeping discovered during editing.
- T03's first edit attempt on main.py matched an unintended location, creating a stray line — detected immediately via syntax check and fixed.

## Known Limitations

- Admin pages cannot be verified in a live browser until Docker stack runs (S07 scope). Templates are validated only via unit test rendering.
- `_copy_static_assets()` is synchronous (`shutil.copytree`) — fine for small apps but could block the event loop for very large static directories. Not a concern for v1 app sizes.
- Detail page has placeholder sections ("Task History" and "Renderer Assignments") that show "coming soon" messages — filled in by S05 and S06.

## Follow-ups

None — all planned work completed. S05 and S06 will extend the detail page with task history and renderer assignments as already scoped.

## Files Created/Modified

- `backend/app/apps/admin_router.py` — new admin router with 7 endpoints (list, detail, install, start, stop, restart, uninstall)
- `backend/app/templates/admin/apps/list.html` — app list page with status badges, install form, action buttons
- `backend/app/templates/admin/apps/detail.html` — app detail page with permissions, logs, actions, placeholder sections
- `backend/tests/test_app_admin.py` — 26 unit tests covering all endpoints, htmx partials, error handling, role enforcement
- `frontend/nginx.conf` — added /app-static/ (alias) and /app/ (proxy) location blocks
- `docker-compose.yml` — added apps + sdk mounts on api, sempkm_data on frontend, cleaned duplicate volumes block
- `backend/app/apps/manager.py` — added _copy_static_assets() method and call in install()
- `apps/.gitkeep` — empty placeholder for Docker volume mount
- `backend/app/main.py` — imported and included app_admin_router
- `backend/app/templates/components/_sidebar.html` — added "Applications" nav-link in owner-only admin group
- `backend/app/templates/admin/index.html` — added "Applications" card to dashboard-cards

## Forward Intelligence

### What the next slice should know
- The admin router is at `backend/app/apps/admin_router.py` and uses `request.app.state.app_manager` / `request.app.state.app_registry` — same pattern as the proxy router.
- nginx location `/app/` proxies to `http://api:8000/app/` — S04's frontend fragment loading will go through this chain: browser → nginx `/app/{appId}/` → FastAPI → AppProxy → UDS → SDK app.
- The `sempkm_data` named volume is the bridge between api (writes) and frontend/nginx (reads). App static assets land at `/app/data/apps-static/{app_id}/` inside both containers.

### What's fragile
- **Route ordering in main.py** — `app_admin_router` MUST be registered before `app_proxy_router`. The proxy has a catch-all `{path:path}` that would silently consume `/admin/apps/*` if it wins. If anyone reorders router includes, admin pages will 404 and proxy will get garbage requests.
- **nginx location ordering** — `/app-static/` and `/app/` must appear before the catch-all `location /`. nginx uses first-match for prefix locations.

### Authoritative diagnostics
- `grep -n "include_router" backend/app/main.py` — verify router registration order; admin_router → app_admin_router → app_proxy_router
- `grep -n "location " frontend/nginx.conf` — verify nginx location ordering
- `python -m pytest tests/test_app_admin.py -v` — 26 tests covering all admin endpoint contracts

### What assumptions changed
- No assumptions changed — the slice delivered exactly what was planned. The shared named volume pattern (D162) was implicit in the plan but worth calling out explicitly as a pattern.
