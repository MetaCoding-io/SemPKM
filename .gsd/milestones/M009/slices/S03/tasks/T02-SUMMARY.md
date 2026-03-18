---
id: T02
parent: S03
milestone: M009
provides:
  - nginx location blocks for /app-static/ (static asset serving) and /app/ (proxy to FastAPI)
  - docker-compose volume mounts for apps directory and shared data volume on frontend
  - Static asset copying in AppManager.install() flow
  - apps/.gitkeep placeholder for volume mount
key_files:
  - frontend/nginx.conf
  - docker-compose.yml
  - backend/app/apps/manager.py
  - apps/.gitkeep
key_decisions:
  - Static assets copied to data_dir/../apps-static/{app_id} so they resolve to /app/data/apps-static/ in Docker
  - SDK source mounted as ./backend/sdk:/app/backend/sdk:ro for hot-reload during dev
patterns_established:
  - nginx alias directive (not root) for path-remapped static serving with trailing slashes on both location and alias
observability_surfaces:
  - nginx access logs distinguish /app-static/ and /app/ requests from catch-all proxy
  - AppManager._copy_static_assets() logs at INFO "Copying static assets for app {app_id}" when frontend/static/ exists
  - shutil.copytree failure propagates through install() with source/dest paths in traceback
duration: 10m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: nginx config, docker-compose, and static asset copying

**Added nginx locations for app-static and app proxy, docker-compose volume mounts for apps and shared data, and static asset copying in AppManager.install()**

## What Happened

Five changes made as planned:

1. **nginx.conf**: Added two location blocks before the catch-all `location /` — `/app-static/` with `alias /app/data/apps-static/;` plus cache headers, and `/app/` proxying to `http://api:8000/app/` with standard headers.

2. **docker-compose.yml api service**: Added `./apps:/app/apps:ro` and `./backend/sdk:/app/backend/sdk:ro` volume mounts after the ontologies mount.

3. **docker-compose.yml frontend service**: Added `sempkm_data:/app/data:ro` so nginx can read the apps-static directory written by the api service.

4. **manager.py**: Added `_copy_static_assets()` method that checks for `{app_dir}/frontend/static/` and copies to `{data_dir}/../apps-static/{app_id}/` using `shutil.copytree(dirs_exist_ok=True)`. Called from `install()` after SDK install and before DB persist.

5. **apps/.gitkeep**: Created empty placeholder so the `./apps` directory exists for the Docker volume mount.

## Verification

All six task-level verification checks pass. All 33 admin router tests from T01 continue to pass. Slice-level checks SV2-SV4 and SV8 pass; SV5-SV7 (sidebar, admin index, main.py wiring) are T03 work.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c "location /app-static/" frontend/nginx.conf` | 0 (returns 1) | ✅ pass | <1s |
| 2 | `grep -c "alias /app/data/apps-static/" frontend/nginx.conf` | 0 (returns 1) | ✅ pass | <1s |
| 3 | `grep "apps:/app/apps" docker-compose.yml` | 0 | ✅ pass | <1s |
| 4 | `grep "sempkm_data:/app/data" docker-compose.yml` | 0 (2 matches: api + frontend) | ✅ pass | <1s |
| 5 | `grep "_copy_static_assets" backend/app/apps/manager.py` | 0 (2 matches: call + def) | ✅ pass | <1s |
| 6 | `test -f apps/.gitkeep` | 0 | ✅ pass | <1s |
| 7 | `uv run python -m pytest tests/test_app_admin.py -v` | 0 (33 passed) | ✅ pass | 1.4s |
| 8 | `grep -n "location " frontend/nginx.conf \| tail -5` | 0 (app-static@201, app/@208, catch-all@219) | ✅ pass | <1s |

## Diagnostics

- **nginx location ordering**: `grep -n "location " frontend/nginx.conf` — /app-static/ and /app/ must appear before catch-all `/`
- **Static asset copy at runtime**: Look for INFO log `"Copying static assets for app {app_id}"` in api container logs during install
- **Verify assets served**: `curl -I http://localhost:3000/app-static/{app_id}/somefile` — should return with `Cache-Control: public, immutable` and `Expires` header
- **Volume mounts**: `docker compose config | grep -A5 volumes` on api and frontend services

## Deviations

None — all five steps executed as planned.

## Known Issues

- Pre-existing Pyright warning on `app.apps.tokens` import (from T01, module not yet created) — not introduced by this task.

## Files Created/Modified

- `frontend/nginx.conf` — Added /app-static/ alias location and /app/ proxy location before catch-all
- `docker-compose.yml` — Added ./apps and ./backend/sdk mounts on api; sempkm_data:/app/data:ro on frontend
- `backend/app/apps/manager.py` — Added _copy_static_assets() method and call in install()
- `apps/.gitkeep` — Empty placeholder for Docker volume mount
