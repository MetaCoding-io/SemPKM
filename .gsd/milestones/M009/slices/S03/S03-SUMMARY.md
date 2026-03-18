---
id: S03
parent: M009
milestone: M009
provides:
  - Admin portal at /admin/apps with app list (status/version/uptime/PID) and detail page (permissions/logs/actions)
  - 7 admin endpoints: list, detail, install, start, stop, restart, uninstall — all owner-only
  - htmx partial rendering for sidebar navigation (HX-Request check returns content block)
  - nginx location /app-static/ serving app assets from shared data volume with cache headers
  - nginx location /app/ proxying to FastAPI API with standard headers
  - docker-compose volume mounts: ./apps:/app/apps:ro on api, sempkm_data:/app/data:ro on frontend, ./backend/sdk mount
  - AppManager._copy_static_assets() copying app frontend/static/ to shared volume on install
  - "Applications" sidebar nav link (owner-only, puzzle icon) and admin index card
  - apps/.gitkeep placeholder for volume mount
requires:
  - slice: S01
    provides: AppManager (get_status, get_logs, install, start, stop, restart, uninstall), AppRegistry (list_apps, get_manifest), AppManifestSchema, SQLAlchemy models
  - slice: S02
    provides: AppProxy (status verification), JWT tokens (app communication), SDK package structure
affects:
  - S04 (needs nginx proxy config + admin install flow to make app pages reachable)
  - S05 (extends detail page with task history section)
  - S06 (extends detail page with renderer assignments section)
  - S07 (E2E tests exercise admin install/status/uninstall flow)
key_files:
  - backend/app/apps/admin_router.py
  - backend/app/templates/admin/apps/list.html
  - backend/app/templates/admin/apps/detail.html
  - backend/tests/test_app_admin.py
  - frontend/nginx.conf
  - docker-compose.yml
  - backend/app/apps/manager.py
  - backend/app/main.py
  - backend/app/templates/components/_sidebar.html
  - backend/app/templates/admin/index.html
  - apps/.gitkeep
key_decisions:
  - D175: app_admin_router placed immediately before app_proxy_router in main.py to prevent catch-all {path:path} from consuming /admin/apps/* URLs
  - D176: nginx alias directive (not root) for /app-static/ with trailing slashes on both location and alias, serving from shared sempkm_data volume
  - Admin router uses standalone APIRouter with full /admin/apps paths (included directly in main.py, not nested under existing admin router)
  - Lifecycle actions redirect via 303: start/stop/restart → detail page, install/uninstall → list page
  - Flash messages via query params (success/error) matching existing admin redirect patterns
patterns_established:
  - App admin router pattern: _templates_response helper, _is_htmx_request check, require_role("owner") on all endpoints
  - Test pattern: real SQLite DB for auth, mocked app_manager on app.state, httpx AsyncClient with ASGITransport
  - nginx alias with trailing slashes pattern for path-remapped static serving
  - Sidebar nav link pattern: href + hx-get + hx-target + hx-swap + hx-push-url + lucide icon
observability_surfaces:
  - Admin router logs INFO for install/start/stop/restart/uninstall with app_id and user email
  - /admin/apps list shows live status (running/stopped/error/installing) per app
  - /admin/apps/{app_id} detail shows PID, uptime, restart count, error_message, log output
  - HTTP 404 with JSON detail for unknown app_id
  - nginx access logs distinguish /app-static/ and /app/ from catch-all
  - AppManager._copy_static_assets() logs INFO when copying
drill_down_paths:
  - .gsd/milestones/M009/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S03/tasks/T03-SUMMARY.md
duration: 45m
verification_result: passed
completed_at: 2026-03-18
---

# S03: Admin Portal & Docker/nginx Integration

**Admin portal at /admin/apps with full app lifecycle management, nginx locations for app proxy and static assets, docker-compose volume mounts, and 33 unit tests — completing the admin and infrastructure layer for the app platform.**

## What Happened

Three tasks delivered the admin surface and Docker/nginx infrastructure for the app platform:

**T01 (Admin router + templates + tests):** Created `admin_router.py` with 7 endpoints: GET list, GET detail, POST install, POST start/stop/restart/uninstall. All use `require_role("owner")` and support htmx partial rendering. The list template shows app cards with color-coded status badges (running/stopped/error/installing), version pills, uptime, PID, and quick action buttons including an install form. The detail template provides a full app dashboard: header with name/version/status, stats bar (PID/uptime/restarts), permissions table from manifest, log viewer from ring buffer, lifecycle action buttons, and placeholder sections for task history (S05) and renderer assignments (S06). 33 unit tests cover all endpoints, htmx partials, role enforcement, and error paths using real SQLite for auth and mocked AppManager on app.state.

**T02 (nginx + docker-compose + static assets):** Added two nginx locations before the catch-all: `/app-static/` with `alias /app/data/apps-static/;` plus `Cache-Control: public, immutable` headers, and `/app/` proxying to `http://api:8000/app/` with standard headers. Updated docker-compose.yml: `./apps:/app/apps:ro` and `./backend/sdk:/app/backend/sdk:ro` on the api service, `sempkm_data:/app/data:ro` on the frontend service so nginx reads app-static files from the shared volume. Added `_copy_static_assets()` to AppManager that copies `{app_dir}/frontend/static/` to the shared data volume during install. Created `apps/.gitkeep`.

**T03 (Wiring + sidebar + index card):** Imported and included `app_admin_router` in main.py immediately before `app_proxy_router` (critical ordering — the proxy's catch-all `{path:path}` would swallow admin URLs otherwise). Added "Applications" nav-link with puzzle icon in the owner-only sidebar admin group. Added "Applications" card to the admin index page. Fixed a pre-existing stray syntax error in main.py.

## Verification

All slice-level verification checks pass:

| # | Check | Result |
|---|-------|--------|
| SV1 | `pytest tests/test_app_admin.py -v` — 33 tests | ✅ pass (1.37s) |
| SV2 | `grep -c "location /app-static/" frontend/nginx.conf` → 1 | ✅ pass |
| SV3 | `grep -c "location /app/" frontend/nginx.conf` → 1 | ✅ pass |
| SV4 | `grep -c "./apps:/app/apps" docker-compose.yml` → 1 | ✅ pass |
| SV5 | `grep -c "Applications" _sidebar.html` → 2 | ✅ pass |
| SV6 | `grep -c "Applications" admin/index.html` → 2 | ✅ pass |
| SV7 | `grep -c "app_admin_router" main.py` → 2 | ✅ pass |
| SV8 | `grep -c "_copy_static_assets" manager.py` → 2 | ✅ pass |
| SV9 | `test -f apps/.gitkeep` | ✅ pass |
| SV10 | `python3 -c "import ast; ast.parse(open('app/main.py').read())"` | ✅ pass |
| SV11 | Router ordering: app_admin_router (line 570) before app_proxy_router (line 571) | ✅ pass |
| SV12 | nginx location ordering: /app-static/ (201), /app/ (208), catch-all / (219) | ✅ pass |

## Requirements Advanced

- APP-10 — Admin list page with status/version/uptime/PID and detail page with permissions/logs/actions now delivered. Task history (S05) and renderer assignments (S06) remain as placeholder sections.

## Requirements Validated

- APP-14 — Docker and nginx integration fully delivered: docker-compose mounts ./apps volume, nginx serves /app-static/{appId}/ via alias to shared data volume, nginx proxies /app/{appId}/ to API, static asset copy during install. All verified via grep checks.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Fixed pre-existing stray `asgi_dav_app)` line at end of main.py that caused SyntaxError on import — not introduced by S03 tasks.

## Known Limitations

- Admin detail page task history and renderer assignments sections are placeholders — populated in S05 and S06 respectively
- Memory usage stat not yet available on list page (requires runtime process introspection, deferred to S07)
- Static asset serving not yet exercised end-to-end through Docker stack (deferred to S07)
- Admin list shows data from mocked AppManager in tests — real Docker integration verified in S07

## Follow-ups

- S05 must extend detail template with real task history data from app_task_runs table
- S06 must extend detail template with renderer assignment data from app_renderer_prefs table
- S07 E2E tests should exercise the full admin flow: navigate to /admin/apps → install app → verify status → start/stop → uninstall

## Files Created/Modified

- `backend/app/apps/admin_router.py` — new admin router with 7 endpoints (list, detail, install, start, stop, restart, uninstall)
- `backend/app/templates/admin/apps/list.html` — app list page template with status badges, install form, action buttons
- `backend/app/templates/admin/apps/detail.html` — app detail page with status, permissions, logs, actions, placeholders
- `backend/tests/test_app_admin.py` — 33 unit tests covering all endpoints, htmx partials, role enforcement, error paths
- `frontend/nginx.conf` — added /app-static/ alias location and /app/ proxy location before catch-all
- `docker-compose.yml` — added ./apps and ./backend/sdk mounts on api; sempkm_data:/app/data:ro on frontend
- `backend/app/apps/manager.py` — added _copy_static_assets() method and call in install()
- `apps/.gitkeep` — empty placeholder for Docker volume mount
- `backend/app/main.py` — added import and include_router for app_admin_router; fixed stray syntax error
- `backend/app/templates/components/_sidebar.html` — added "Applications" nav-link in owner-only admin group
- `backend/app/templates/admin/index.html` — added "Applications" card in dashboard-cards grid

## Forward Intelligence

### What the next slice should know
- Admin router is at `backend/app/apps/admin_router.py` — it's a standalone APIRouter (not nested under admin_router). When adding new admin-facing app endpoints, extend this router.
- The admin detail page template has two clearly marked placeholder blocks: `<!-- Task History section - S05 will populate -->` and `<!-- Renderer Assignments section - S06 will populate -->`. These are divs with IDs ready for htmx injection.
- nginx location `/app/` proxies to `http://api:8000/app/` — app fragments served via SDK are already reachable from the browser once the app subprocess is running.
- `_copy_static_assets()` copies to `{data_dir}/../apps-static/{app_id}/` — that resolves to `/app/data/apps-static/` in Docker, matching nginx's alias target.

### What's fragile
- **Router ordering in main.py** — `app_admin_router` MUST be included before `app_proxy_router`. If any future refactor reorders router includes, admin pages will be swallowed by the proxy catch-all and return 404/502.
- **nginx alias trailing slashes** — Both the `location /app-static/` and `alias /app/data/apps-static/;` must end with `/`. Missing either trailing slash causes nginx to return 404 or serve wrong files. This is a well-known nginx gotcha.

### Authoritative diagnostics
- `backend/tests/test_app_admin.py` — 33 tests are the contract for admin endpoint behavior. If admin pages break, run these first.
- `grep -n "include_router" backend/app/main.py` — verify app_admin_router appears before app_proxy_router in the output.
- `grep -n "location " frontend/nginx.conf` — verify /app-static/ and /app/ appear before catch-all `/`.

### What assumptions changed
- Originally assumed admin router would be nested under existing admin_router — actual implementation uses standalone APIRouter with full paths, which is simpler and avoids prefix conflicts.
