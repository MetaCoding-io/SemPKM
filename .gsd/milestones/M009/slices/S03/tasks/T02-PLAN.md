---
estimated_steps: 5
estimated_files: 4
---

# T02: nginx config, docker-compose, and static asset copying

**Slice:** S03 — Admin Portal & Docker/nginx Integration
**Milestone:** M009

## Description

Configure nginx to serve app static assets and proxy app requests. Update docker-compose.yml to mount the apps directory and share the data volume with the frontend service. Add static asset copying to the AppManager install flow.

## Steps

1. **Add nginx locations to `frontend/nginx.conf`** — insert BEFORE the catch-all `location /` block (order matters):
   ```nginx
   # App static assets served by nginx from shared data volume
   location /app-static/ {
       alias /app/data/apps-static/;
       expires 1h;
       add_header Cache-Control "public, immutable";
   }

   # App proxy — forward to FastAPI which proxies to app subprocess
   location /app/ {
       proxy_pass http://api:8000/app/;
       proxy_set_header Host $http_host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_set_header Cookie $http_cookie;
       proxy_pass_header Set-Cookie;
   }
   ```
   **Critical:** Use `alias` not `root` for `/app-static/` — `root` would double the path. The trailing slash on the alias value is required.

2. **Update `docker-compose.yml` api service volumes** — add `./apps:/app/apps:ro` volume mount. Also add the SDK source mount `./backend/sdk:/app/backend/sdk:ro` so SDK changes are picked up without rebuild. Both after the existing `./backend/ontologies:/app/ontologies:ro` line.

3. **Update `docker-compose.yml` frontend service volumes** — add `sempkm_data:/app/data:ro` so nginx can read the `/app/data/apps-static/` directory. This is a read-only mount of the named volume that the api service writes to.

4. **Add `_copy_static_assets()` method to `backend/app/apps/manager.py`** — called from `install()` after deps are installed, before DB persist:
   - Check if `{app_dir}/frontend/static/` directory exists
   - If yes, copy its contents to `{self._data_dir}/../apps-static/{app_id}/` (which resolves to `/app/data/apps-static/{app_id}/` in Docker)
   - Use `shutil.copytree` with `dirs_exist_ok=True` for idempotent copies
   - Log at INFO level when copying static assets
   - On reinstall, the `dirs_exist_ok=True` overwrites stale assets

5. **Create `apps/.gitkeep`** — empty file so the `./apps` directory exists in the repo and the Docker volume mount doesn't fail.

## Must-Haves

- [ ] nginx serves `/app-static/{appId}/` files from `/app/data/apps-static/`
- [ ] nginx proxies `/app/{appId}/` to FastAPI backend
- [ ] Both nginx locations appear BEFORE the catch-all `location /`
- [ ] docker-compose mounts `./apps:/app/apps:ro` on api service
- [ ] docker-compose mounts `sempkm_data:/app/data:ro` on frontend service
- [ ] `AppManager.install()` copies static assets when present
- [ ] `apps/.gitkeep` exists

## Verification

- `grep -c "location /app-static/" frontend/nginx.conf` returns 1
- `grep -c "alias /app/data/apps-static/" frontend/nginx.conf` returns 1
- `grep "apps:/app/apps" docker-compose.yml` matches
- `grep "sempkm_data:/app/data" docker-compose.yml` shows both api and frontend mounts
- `grep "_copy_static_assets" backend/app/apps/manager.py` matches
- `test -f apps/.gitkeep` succeeds

## Observability Impact

- **nginx access logs:** Requests to `/app-static/` and `/app/` now appear in the nginx access log with their own location context — distinguishable from the catch-all proxy.
- **Static asset copy logging:** `AppManager._copy_static_assets()` logs at INFO level when copying static assets for an app (`"Copying static assets for app %s"`). If no frontend/static/ directory exists, no log line is emitted (absence = no static assets).
- **Failure visibility:** If `shutil.copytree` fails, the exception propagates up through `install()` — the app install fails with a traceback that includes the source and destination paths.
- **Future inspection:** `ls /app/data/apps-static/{app_id}/` inside the container confirms which assets were copied. The nginx `expires 1h` header is observable via `curl -I /app-static/{app_id}/somefile`.

## Inputs

- `frontend/nginx.conf` — current nginx config; new locations must go before catch-all `location /` block (starts around line 145)
- `docker-compose.yml` — api service volumes at lines 22-28, frontend service volumes at lines 60-62, named volumes at lines 72-75
- `backend/app/apps/manager.py` — `install()` method (lines 99-181); `_data_dir` is `/app/data/apps` so parent is `/app/data/`; add `_copy_static_assets()` call after SDK install and before DB persist (around line 157)

## Expected Output

- `frontend/nginx.conf` — two new location blocks for app-static and app proxy
- `docker-compose.yml` — apps volume mount on api, data volume mount on frontend, sdk mount on api
- `backend/app/apps/manager.py` — `_copy_static_assets()` method + call in install()
- `apps/.gitkeep` — empty placeholder file
