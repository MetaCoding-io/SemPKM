---
estimated_steps: 8
estimated_files: 5
---

# T04: Multi-stage Dockerfile, nginx config, and Docker integration test

**Slice:** S01 — Build Pipeline & Local Vendoring
**Milestone:** M029

## Description

Wire the build pipeline into the Docker infrastructure so `docker compose build frontend` automatically produces optimized assets. This is the integration test for the entire slice — it proves that the build runs in Docker, nginx serves the built assets, templates render with manifest-resolved URLs, and htmx/Cytoscape/dockview all work with the locally-vendored bundles.

The key challenge is the **manifest sharing problem**: the build output (manifest.json) lives in the frontend container's filesystem, but the Jinja2 filter runs in the API container. The manifest must be accessible to the API container at startup. The cleanest solution is a shared Docker volume.

## Steps

1. **Rewrite `frontend/Dockerfile`** as a multi-stage build:

   ```dockerfile
   # ── Stage 1: Build optimized assets ──
   FROM node:20-alpine AS builder
   WORKDIR /build
   
   # Install dependencies (layer cached if package*.json unchanged)
   COPY package.json package-lock.json ./
   RUN npm ci --no-audit --no-fund
   
   # Copy source files and run build
   COPY build.js ./
   COPY static/ ./static/
   RUN node build.js
   
   # ── Stage 2: Serve with nginx ──
   FROM nginx:stable-alpine
   
   # Copy raw static files (served at /js/ and /css/ when volume-mounted in dev)
   COPY static/ /usr/share/nginx/html/
   
   # Copy built assets (served at /assets/ in production)
   COPY --from=builder /build/dist/ /usr/share/nginx/html/assets/
   
   # Copy nginx configuration
   COPY nginx.conf /etc/nginx/conf.d/default.conf
   
   EXPOSE 80
   CMD ["nginx", "-g", "daemon off;"]
   ```

   Note: Both raw files AND built assets are in the image. In dev mode, docker-compose.yml volume mounts `./frontend/static:/usr/share/nginx/html` which overlays the raw files but does NOT touch `/usr/share/nginx/html/assets/` (the volume mount is at /html, not /html/assets). However, the /assets/ directory exists in the image so production requests work even without volume mounts.

   Wait — the volume mount `./frontend/static:/usr/share/nginx/html:ro` mounts AT `/usr/share/nginx/html`, which REPLACES the entire directory including `/usr/share/nginx/html/assets/`. This means in dev mode, `/assets/` won't exist (the mount hides it). That's actually correct behavior: in dev mode, the manifest doesn't exist either (API container doesn't have it), so templates use CDN URLs and never request `/assets/`. The dev and production paths are fully disjoint.

2. **Add `/assets/` location block to `frontend/nginx.conf`**:

   Add this block before the `/css/` location:
   ```nginx
   # Built assets (production) — hashed filenames, cache headers added in S02
   location /assets/ {
       root /usr/share/nginx/html;
       try_files $uri =404;
   }
   ```

   This is minimal for S01 — no cache headers yet (S02 adds `Cache-Control: public, max-age=31536000, immutable`).

3. **Share manifest.json with the API container** via a named Docker volume.

   In `docker-compose.yml`, add a named volume for the asset manifest:
   ```yaml
   volumes:
     asset_manifest:  # Shared manifest.json between frontend and API

   services:
     frontend:
       volumes:
         # In dev mode, this volume mount overrides the Docker image's /html/
         # so /assets/ is not accessible — which is correct (dev uses CDN URLs)
         - ./frontend/static:/usr/share/nginx/html:ro
         - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
         # Copy manifest to shared volume on container start
         # (will be empty in dev mode since volume mount hides /assets/)

     api:
       volumes:
         - asset_manifest:/app/asset_manifest:ro
   ```

   Actually, the volume approach is tricky because the manifest only exists in the Docker image (not volume-mounted in dev). A simpler approach: **have the build script also copy manifest.json into the backend directory**, or better yet, use a **Docker build-time copy** with a shared build context.

   Simplest correct approach: In the multi-stage Dockerfile, the frontend image has the manifest at `/usr/share/nginx/html/assets/manifest.json`. We need the API container to read this file. Options:

   **Option A (recommended): Mount manifest from frontend build output into API container.**
   Add to docker-compose.yml for production (non-dev) use: Since the dev compose file uses volume mounts that hide the built assets, we need a separate strategy for production. But actually, in dev mode, the API container shouldn't have the manifest (so it uses dev mode paths). In production, we need the manifest.

   **Cleaner approach: Build the manifest in the API container too.**
   The API Dockerfile can also run the build to get manifest.json. But that's wasteful — two build stages.

   **Cleanest approach: Use an init container or Docker entrypoint.**
   
   Actually, the simplest working approach:
   - In production (no volume mounts), use `docker compose` with a production override that mounts the manifest from a named volume.
   - In dev (volume mounts), manifest doesn't exist, filter falls back to dev paths. Perfect.
   
   **Final approach: Use a Docker named volume populated by the frontend container.**
   
   In docker-compose.yml:
   ```yaml
   volumes:
     asset_manifest:
   
   services:
     frontend:
       volumes:
         - asset_manifest:/usr/share/nginx/html/assets/_manifest
       # Use a custom entrypoint that copies manifest to the shared volume
   ```

   No — this is getting overcomplicated. The **simplest correct approach** for a self-hosted single-user app:

   **Copy manifest.json into a path the API container can read.** The API container already mounts `./backend/app:/app/app`. During `docker compose build`, the build runs in the frontend container. We can't directly share between them via mounts during build.

   **Actual simplest approach:** After `docker compose build`, before `docker compose up`, run `docker compose run --rm frontend cat /usr/share/nginx/html/assets/manifest.json > backend/asset_manifest.json`. But that's manual.

   **Actually simplest:** Make template_helpers.py check multiple paths. Add a `docker-compose.yml` volume that mounts the frontend's assets directory into the API container as read-only:
   
   ```yaml
   services:
     api:
       volumes:
         - frontend_assets:/app/frontend_assets:ro
     frontend:
       volumes:
         - frontend_assets:/usr/share/nginx/html/assets
   
   volumes:
     frontend_assets:
   ```
   
   In dev mode, the frontend container's `/usr/share/nginx/html` is volume-mounted from `./frontend/static`, which doesn't have an `assets/` dir, so the `frontend_assets` volume will be empty → API container sees empty dir → no manifest → dev mode. In production (without the static volume mount), the Docker image's built assets populate the volume → API container reads manifest → production mode.

   **But wait** — in the default docker-compose.yml (used for dev), the `./frontend/static:/usr/share/nginx/html:ro` mount replaces the entire /html directory. The `frontend_assets` volume at `/usr/share/nginx/html/assets` would be a sub-mount that Docker keeps separate from the parent bind mount. This actually works in Docker: a named volume at a sub-path takes precedence over the parent bind mount.

   However, in dev mode, the Docker image was built with assets in /html/assets/, so the named volume would get populated from the image's built assets on first run (Docker's volume initialization behavior). This means even in dev mode, the API container would see the manifest from the last build. That's actually not terrible — but it's confusing.

   **Simplest correct approach for real:** Since dev and test compose files use volume mounts that serve raw files, and the `asset_url` filter gracefully degrades, just configure template_helpers.py to also look for the manifest at a path that's easy to share:
   
   Update template_helpers.py to check paths in order:
   1. `ASSET_MANIFEST_PATH` env var (explicit override)
   2. `/app/frontend_assets/manifest.json` (Docker shared volume)
   3. `/usr/share/nginx/html/assets/manifest.json` (same-container, won't exist for API)

   Add to docker-compose.yml:
   ```yaml
   services:
     frontend:
       volumes:
         - frontend_assets:/usr/share/nginx/html/assets
     api:
       volumes:
         - frontend_assets:/app/frontend_assets:ro
   volumes:
     frontend_assets:
   ```

   In docker-compose.yml (dev), keep existing volume mounts. The `frontend_assets` named volume won't interfere because Docker manages it separately from the bind mount.
   
   For production use (docker compose build + up without bind mounts), the frontend image populates the named volume with built assets, and the API container reads the manifest.

4. **Update `backend/app/template_helpers.py`** manifest path search:
   
   Update `_MANIFEST_PATH` to check `/app/frontend_assets/manifest.json` first (shared Docker volume), then fall back to the env var or a sensible default. The env var override remains for testing.

5. **Update `docker-compose.test.yml`** — no changes needed for test stack. The test stack uses volume mounts (dev mode), so no manifest exists and templates use CDN URLs. This is correct for testing — tests verify app behavior, not the build pipeline.

6. **Build and verify the Docker stack:**
   ```bash
   # Build the frontend (runs Node.js stage + nginx stage)
   docker compose build frontend
   
   # Verify manifest exists in image
   docker compose run --rm frontend cat /usr/share/nginx/html/assets/manifest.json | head -5
   
   # Start the stack
   docker compose up -d
   
   # Wait for health
   sleep 10
   
   # Verify assets are served
   curl -sI http://localhost:3000/assets/manifest.json | head -3
   
   # Verify workspace page loads with local asset references
   curl -s http://localhost:3000/browser/ | grep -o '/assets/[^"]*' | head -10
   ```

7. **Verify htmx CRUD still works:** Navigate to the workspace, create an object, edit the title, save. Verify no JS console errors.

8. **Verify Cytoscape/dockview work:** Open graph view (Cytoscape), verify rendering. Open multiple panels (dockview), verify they render.

## Must-Haves

- [ ] `docker compose build frontend` completes without error
- [ ] Multi-stage Dockerfile: Node.js stage builds, nginx stage serves
- [ ] nginx.conf has `/assets/` location block
- [ ] manifest.json accessible to API container via shared Docker volume
- [ ] Dev mode (with volume mounts) still uses CDN URLs — unaffected by build pipeline
- [ ] Production mode (without volume mounts) uses local vendored assets
- [ ] Workspace loads without JS errors in production mode
- [ ] htmx requests work in production mode

## Verification

- `docker compose build frontend` — exit code 0
- `docker compose run --rm frontend ls /usr/share/nginx/html/assets/manifest.json` — file exists
- `docker compose run --rm frontend ls /usr/share/nginx/html/assets/ | wc -l` — shows ≥50 files
- `docker compose up -d && sleep 10 && curl -s http://localhost:3000/assets/manifest.json | python3 -m json.tool | head -5` — valid JSON
- `curl -s http://localhost:3000/browser/ | grep -c '/assets/'` — returns ≥3 (vendor.js, vendor.css, workspace.js at minimum)
- `curl -s http://localhost:3000/browser/ | grep -c 'unpkg\|jsdelivr\|cdnjs'` — returns 0 (no CDN refs in production)

## Observability Impact

- Signals added: If manifest loading fails at API startup, a WARNING-level log message is emitted
- How a future agent inspects this: `docker compose exec frontend cat /usr/share/nginx/html/assets/manifest.json` to check built assets; `docker compose exec api python -c "from app.template_helpers import is_asset_manifest_available; print(is_asset_manifest_available())"` to check manifest loading
- Failure state exposed: If manifest is missing/corrupt, `asset_manifest_available` is False → templates fall back to CDN URLs → page still works but loads from CDN instead of local files

## Inputs

- T01 output: `frontend/package.json`, `frontend/build.js` — complete build tooling
- T02 output: `backend/app/template_helpers.py` — asset_url filter with manifest loading
- T03 output: all templates using `asset_url` filter and conditional blocks
- Current `frontend/Dockerfile` — 6-line single-stage
- Current `frontend/nginx.conf` — no /assets/ block
- Current `docker-compose.yml` — frontend volume mounts

## Expected Output

- `frontend/Dockerfile` — multi-stage build (Node.js → nginx)
- `frontend/nginx.conf` — /assets/ location block added
- `docker-compose.yml` — `frontend_assets` shared volume for manifest
- `backend/app/template_helpers.py` — manifest path updated to check shared volume path
- Working Docker stack with locally-vendored assets in production mode
