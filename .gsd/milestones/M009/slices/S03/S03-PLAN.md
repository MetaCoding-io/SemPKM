# S03: Admin Portal & Docker/nginx Integration

**Goal:** Admin portal at `/admin/apps` shows installed app list with status/version/uptime and detail page with permissions, data stats, logs, and lifecycle actions. nginx proxies `/app/{appId}/` and serves `/app-static/{appId}/`. docker-compose mounts `./apps`.

**Demo:** Navigate to `/admin/apps` — see list of installed apps with status badges. Click an app — see detail page with permissions, log output, and start/stop/restart/uninstall buttons. Static assets served by nginx at `/app-static/{appId}/`.

## Must-Haves

- Admin list page at `/admin/apps` showing all installed apps with status, version, uptime, PID
- Admin detail page at `/admin/apps/{app_id}` showing permissions, data stats, logs, lifecycle actions
- `POST /admin/apps/install` endpoint calling `AppManager.install()`
- `POST /admin/apps/{app_id}/start|stop|restart|uninstall` action endpoints
- All admin endpoints require owner role
- htmx partial rendering for sidebar navigation (return `content` block when `HX-Request`)
- nginx `location /app-static/` serving app static assets from shared volume
- nginx `location /app/{appId}/` proxying to FastAPI API
- `docker-compose.yml` mounts `./apps:/app/apps:ro` and shares `sempkm_data` volume with frontend
- Static asset copy step in `AppManager.install()` flow
- Sidebar nav entry "Applications" in Admin group (owner-only)
- Admin index card for "Applications"
- Unit tests for all admin router endpoints

## Proof Level

- This slice proves: integration (admin surfaces + Docker config)
- Real runtime required: no (unit tests mock AppManager/AppRegistry; Docker config verified in S07)
- Human/UAT required: no (S07 scope)

## Verification

- `cd backend && python -m pytest tests/test_app_admin.py -v` — all endpoints tested with mocked services
- `grep -c "location /app-static/" frontend/nginx.conf` — returns 1
- `grep -c "location /app/" frontend/nginx.conf` — returns 1
- `grep -c "./apps:/app/apps" docker-compose.yml` — returns 1
- `grep -c "Applications" backend/app/templates/components/_sidebar.html` — returns 1
- `grep -c "Applications" backend/app/templates/admin/index.html` — returns 1
- `grep -c "app_admin_router" backend/app/main.py` — returns 1
- Detail page returns 404 with JSON detail for unknown app_id: `curl /admin/apps/nonexistent` → HTTP 404
- Static asset copy logs inspectable: `grep "_copy_static_assets" backend/app/apps/manager.py` confirms method exists; runtime log line `"Copying static assets"` emitted at INFO level when an app has frontend/static/

## Observability / Diagnostics

- Runtime signals: Admin endpoints log nothing new — they surface existing `AppManager.get_status()` and `get_logs()` data
- Inspection surfaces: `/admin/apps` list shows live status; `/admin/apps/{app_id}` shows logs and error messages
- Failure visibility: App error_message from DB shown on detail page; HTTP 404 for unknown app_id
- Redaction constraints: none (no secrets in admin views)

## Integration Closure

- Upstream surfaces consumed: `AppManager` (get_status, get_logs, install, start, stop, restart, uninstall), `AppRegistry` (list_apps, get_manifest), `AppManifestSchema` (permissions, frontend fields), `AppProxy` (from app.state for future verification)
- New wiring introduced: `app_admin_router` included in `main.py`, sidebar nav link, admin index card, nginx locations, docker-compose volume mount
- What remains before milestone is usable end-to-end: S04 (frontend pages), S05 (scheduler/permissions + task history on detail page), S06 (renderer assignments on detail page), S07 (E2E proof)

## Tasks

- [ ] **T01: Admin router, templates, and unit tests** `est:1h30m`
  - Why: Core deliverable — all admin HTML routes, two Jinja2 templates, and contract tests proving endpoint behavior
  - Files: `backend/app/apps/admin_router.py`, `backend/app/templates/admin/apps/list.html`, `backend/app/templates/admin/apps/detail.html`, `backend/tests/test_app_admin.py`
  - Do: Create admin router with list/detail/install/start/stop/restart/uninstall endpoints. All use `require_role("owner")`. htmx partial rendering (check `HX-Request` header, return `block_name="content"` for sidebar nav). Create list template extending `base.html` with app cards showing status badge, version, uptime, PID, action buttons. Create detail template with back-link, status section, permissions table (from manifest), log viewer (from ring buffer), action buttons, placeholder sections for task history (S05) and renderer assignments (S06). Write unit tests mocking `AppManager` and `AppRegistry` on `request.app.state`.
  - Verify: `cd backend && python -m pytest tests/test_app_admin.py -v` passes
  - Done when: All admin endpoints return correct template contexts, all action endpoints call correct manager methods, role enforcement tested

- [ ] **T02: nginx config, docker-compose, and static asset copying** `est:30m`
  - Why: Infrastructure config for serving app static assets via nginx and making `./apps` directory available in containers
  - Files: `frontend/nginx.conf`, `docker-compose.yml`, `backend/app/apps/manager.py`, `apps/.gitkeep`
  - Do: Add nginx `location /app-static/` with `alias /app/data/apps-static/;` (trailing slash critical) and cache headers. Add nginx `location /app/` proxying to `http://api:8000/app/` with standard headers (before the catch-all `location /`). Add `./apps:/app/apps:ro` volume mount to `api` service in docker-compose.yml. Add `sempkm_data:/app/data:ro` volume mount to `frontend` service so nginx can read app-static files. Add `_copy_static_assets()` method to `AppManager.install()` that copies `{app_dir}/frontend/static/` to `/app/data/apps-static/{app_id}/` if it exists. Create `apps/.gitkeep` so the volume mount works.
  - Verify: `grep -c "location /app-static/" frontend/nginx.conf` returns 1; `grep "apps:/app/apps" docker-compose.yml` matches; `grep "sempkm_data" docker-compose.yml` shows frontend service mounts it
  - Done when: nginx config has both new locations, docker-compose mounts apps dir and shares data volume, manager copies static assets on install

- [ ] **T03: main.py wiring, sidebar nav, and admin index card** `est:15m`
  - Why: Connects the admin router to the app, adds navigation entry points in the admin UI
  - Files: `backend/app/main.py`, `backend/app/templates/components/_sidebar.html`, `backend/app/templates/admin/index.html`
  - Do: Import and include `app_admin_router` in `main.py` — place it after `admin_router` (line 543) and before `app_proxy_router` (line 558). Add "Applications" nav-link in sidebar Admin group (after "Operations Log", before the `{% else %}` block) with `lucide:puzzle` icon, `hx-get="/admin/apps"`, owner-only visibility. Add "Applications" card to admin index page (after Operations Log card) with description and link.
  - Verify: `grep "app_admin_router" backend/app/main.py` matches; `grep "Applications" backend/app/templates/components/_sidebar.html` matches; `grep "Applications" backend/app/templates/admin/index.html` matches
  - Done when: Router included, sidebar shows Applications link, admin index shows Applications card

## Files Likely Touched

- `backend/app/apps/admin_router.py` (new)
- `backend/app/templates/admin/apps/list.html` (new)
- `backend/app/templates/admin/apps/detail.html` (new)
- `backend/tests/test_app_admin.py` (new)
- `frontend/nginx.conf` (modified)
- `docker-compose.yml` (modified)
- `backend/app/apps/manager.py` (modified)
- `apps/.gitkeep` (new)
- `backend/app/main.py` (modified)
- `backend/app/templates/components/_sidebar.html` (modified)
- `backend/app/templates/admin/index.html` (modified)
