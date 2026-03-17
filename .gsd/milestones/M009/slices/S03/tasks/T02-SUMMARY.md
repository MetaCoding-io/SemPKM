---
id: T02
parent: S03
milestone: M009
provides:
  - nginx location blocks for /app-static/ (alias to shared volume) and /app/ (proxy to FastAPI)
  - docker-compose volume mounts for ./apps on api service and sempkm_data on frontend service
  - SDK source mount for hot-reload during development
  - Static asset copying in AppManager.install() flow
  - apps/.gitkeep placeholder for Docker volume mount
key_files:
  - frontend/nginx.conf
  - docker-compose.yml
  - backend/app/apps/manager.py
  - apps/.gitkeep
key_decisions:
  - Used alias (not root) for nginx /app-static/ to avoid path doubling
  - _copy_static_assets is synchronous (shutil.copytree) since it runs during install() which is already async-locked — no need for async file ops
  - apps-static directory sits at /app/data/apps-static/ (sibling of /app/data/apps/) so both api and frontend can access via the sempkm_data named volume
patterns_established:
  - Shared named volume pattern — api writes to sempkm_data, frontend reads it as :ro for nginx to serve static content
observability_surfaces:
  - INFO log "Copying static assets for app %s" emitted during install when app has frontend/static/
  - nginx access logs distinguish /app-static/ and /app/ requests from catch-all proxy
  - Failure in copytree propagates as exception through install() with source/dest paths in traceback
duration: 12m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: nginx config, docker-compose, and static asset copying

**Added nginx locations for app static/proxy, docker-compose volume mounts, and static asset copying in AppManager.install().**

## What Happened

Five changes across four files:

1. **nginx.conf** — Added two location blocks before the catch-all `location /`: `/app-static/` using `alias /app/data/apps-static/` with 1h cache headers, and `/app/` proxying to `http://api:8000/app/` with standard proxy headers and cookie forwarding.

2. **docker-compose.yml** — Added `./apps:/app/apps:ro` and `./backend/sdk:/app/backend/sdk:ro` mounts to the api service. Added `sempkm_data:/app/data:ro` mount to the frontend service so nginx can read app-static files from the shared named volume. Also cleaned up a duplicate `data:` volumes section that had crept into the file.

3. **manager.py** — Added `_copy_static_assets()` method that checks for `{app_dir}/frontend/static/`, and if present, copies it to `/app/data/apps-static/{app_id}/` using `shutil.copytree` with `dirs_exist_ok=True`. Called from `install()` after SDK install and before DB persist.

4. **apps/.gitkeep** — Empty placeholder so the `./apps` directory exists for the Docker volume mount.

## Verification

All task-level checks pass:
- `grep -c "location /app-static/" frontend/nginx.conf` → 1 ✓
- `grep -c "alias /app/data/apps-static/" frontend/nginx.conf` → 1 ✓
- `grep "apps:/app/apps" docker-compose.yml` → matches `./apps:/app/apps:ro` ✓
- `grep "sempkm_data:/app/data" docker-compose.yml` → shows both api (rw) and frontend (ro) mounts ✓
- `grep "_copy_static_assets" backend/app/apps/manager.py` → method + call site ✓
- `test -f apps/.gitkeep` → exists ✓
- nginx location order verified: /app-static/ at line 150, /app/ at line 157, catch-all / at line 168 ✓

Slice-level checks (T02-relevant):
- `pytest tests/test_app_admin.py -v` → 26/26 passed ✓
- `grep -c "location /app-static/"` → 1 ✓
- `grep -c "location /app/"` → 1 ✓
- `grep -c "./apps:/app/apps"` → 1 ✓

Slice checks deferred to T03: sidebar nav, admin index card, main.py wiring (0 matches expected).

## Diagnostics

- **nginx locations:** `grep -n "location " frontend/nginx.conf | tail -5` shows ordering
- **Static asset copy:** Runtime log line `"Copying static assets for app %s"` at INFO level; absence means app had no frontend/static/
- **Volume mounts:** `docker compose config` validates the compose file syntax (requires Docker)
- **Installed assets:** `ls /app/data/apps-static/{app_id}/` inside container confirms copy

## Deviations

- Cleaned up a duplicate `data:` / `sempkm_data:` / `lucene_index:` block at the bottom of docker-compose.yml that was not mentioned in the plan — it was pre-existing corruption.

## Known Issues

None.

## Files Created/Modified

- `frontend/nginx.conf` — Added /app-static/ and /app/ location blocks before catch-all
- `docker-compose.yml` — Added apps + sdk mounts on api, data volume on frontend, cleaned duplicate volumes block
- `backend/app/apps/manager.py` — Added _copy_static_assets() method and call in install()
- `apps/.gitkeep` — Empty placeholder for Docker volume mount
