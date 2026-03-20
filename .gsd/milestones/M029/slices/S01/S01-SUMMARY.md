---
id: S01
parent: M029
milestone: M029
provides:
  - frontend/package.json with all 18 CDN dependencies version-pinned + esbuild
  - frontend/build.js producing vendor bundle, page-specific bundles, minified app JS/CSS, content-hashed filenames, manifest.json, and .gz pre-compressed siblings
  - backend/app/template_helpers.py with Jinja2 asset_url filter (manifest→/assets/ or dev→/js/,/css/)
  - Conditional CDN/local blocks in all 6 templates (base, base_embed, workspace, sparql, model_detail, 403)
  - Multi-stage frontend/Dockerfile (Node.js build → nginx serve)
  - Docker shared volume (frontend_assets) for manifest.json API container access
  - nginx /assets/ location block serving built files
  - theme.js hljs switcher supporting data-attribute production paths
requires:
  - slice: none
    provides: first slice
affects:
  - S02 (compression + HTTP caching on /assets/ responses)
  - S03 (CSS code-splitting via additional esbuild entry points)
  - S05 (Lighthouse measurement against optimized build)
key_files:
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/build.js
  - frontend/.gitignore
  - frontend/Dockerfile
  - frontend/docker-entrypoint.sh
  - frontend/nginx.conf
  - docker-compose.yml
  - backend/app/template_helpers.py
  - backend/tests/test_template_helpers.py
  - backend/app/main.py
  - backend/app/templates/base.html
  - backend/app/templates/base_embed.html
  - backend/app/templates/browser/workspace.html
  - backend/app/templates/admin/sparql.html
  - backend/app/templates/admin/model_detail.html
  - backend/app/templates/errors/403.html
  - frontend/static/js/theme.js
key_decisions:
  - D276 — esbuild for all bundling/minification (0.8s full build, no watcher needed)
  - D277 — Manifest presence as sole dev/prod signal (no env var toggle)
  - D278 — Docker shared volume at /srv/built-assets/ for cross-container manifest access
  - highlight.js npm package has no UMD — bundled via esbuild from CJS (documented in KNOWLEDGE.md)
  - ninja-keys ESM→IIFE wrapping via esbuild
  - App JS target esnext (sparql-console.js uses top-level await)
  - --keep-names flag for htmx compatibility
patterns_established:
  - Conditional vendor loading — {% if asset_manifest_available %} for production, {% else %} for CDN dev mode
  - App assets always use {{ 'name.js' | asset_url }} unconditionally (works both modes)
  - Content hash is first 8 hex chars of SHA-256 of output content
  - Docker entrypoint script populates shared volumes from image contents on every start
  - Multi-path manifest search (env override → Docker volume → in-container fallback)
observability_surfaces:
  - frontend/dist/manifest.json — 37-entry JSON mapping of logical asset names to hashed filenames
  - build.js stdout — file counts, sizes, elapsed time
  - API startup log — "Loaded asset manifest from X (N entries)" or "running in dev mode"
  - asset_manifest_available Jinja2 global visible to all templates
  - docker compose exec frontend cat /srv/built-assets/manifest.json — inspect built assets in Docker
drill_down_paths:
  - .gsd/milestones/M029/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M029/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M029/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M029/slices/S01/tasks/T04-SUMMARY.md
duration: ~1.5h across 4 tasks
verification_result: passed
completed_at: 2026-03-20
---

# S01: Build Pipeline & Local Vendoring

**All 18 CDN dependencies vendored into locally-served, minified, content-hashed bundles via esbuild build pipeline, with multi-stage Docker build and conditional CDN fallback preserving dev workflow**

## What Happened

Four tasks built the complete frontend build pipeline from npm project creation to Docker production serving.

**T01 — Build script and npm project.** Created `frontend/package.json` pinning all 18 CDN dependencies and `frontend/build.js` using esbuild's transform and build APIs. The vendor bundle concatenates 15 libraries in strict Cytoscape plugin dependency order, then separately bundles highlight.js (npm only ships CJS, not UMD) and ninja-keys (ESM web component) via esbuild into IIFE format. Page-specific bundles (dockview-core, Yasgui, Chart.js) are separate for lazy loading. All 19 app JS files and 9 app CSS files are individually minified. Every output gets a content hash (first 8 hex of SHA-256) and a .gz pre-compressed sibling. The manifest.json maps 37 logical names to hashed filenames. Full build completes in 0.8s.

**T02 — Jinja2 asset_url filter.** Created `backend/app/template_helpers.py` with the bridge between build output and templates. The `asset_url()` filter resolves logical names to `/assets/hashed-name` when a manifest is loaded, or `/js/name`, `/css/name` in dev mode. The `asset_manifest_available` template global controls conditional blocks. Manifest loading uses a multi-path search: env override → Docker shared volume → in-container path. 26 unit tests cover both modes plus edge cases.

**T03 — Template conditional blocks.** Wrapped all CDN `<script>`/`<link>` tags in 6 templates inside `{% if asset_manifest_available %}` guards. The production path loads a single `vendor.js` (replacing 17 individual CDN scripts), while the `{% else %}` block preserves original CDN URLs for dev mode. App JS/CSS references use `{{ 'name' | asset_url }}` unconditionally — the filter handles both modes. The theme.js hljs switcher was updated to check `data-light-href`/`data-dark-href` attributes (production) before falling back to CDN URL construction (dev).

**T04 — Docker integration.** Rewrote `frontend/Dockerfile` as a two-stage build: Node.js stage runs `npm ci && node build.js`, nginx stage copies both raw static files and built assets. Solved the manifest-sharing challenge (frontend bind mount is read-only, blocking sub-volume mounts) by introducing a `frontend_assets` named Docker volume at `/srv/built-assets/` populated by an entrypoint script on every container start. The API container mounts the same volume read-only at `/app/frontend_assets/`. nginx serves `/assets/` via alias directive to the shared volume path.

T03 execution was absorbed into T04 due to dispatch failures — the T04 agent recovered all T03 deliverables from the worktree and applied them alongside the Docker integration.

## Verification

All slice-level checks passed:

| # | Check | Result |
|---|-------|--------|
| 1 | `cd frontend && npm ci && node build.js` produces dist/ with manifest.json (37 entries) | ✅ pass |
| 2 | `python -m pytest backend/tests/test_template_helpers.py -v` — 26/26 tests pass | ✅ pass |
| 3 | Zero unguarded CDN references — all CDN URLs inside `{% else %}` blocks | ✅ pass |
| 4 | `docker compose build frontend` completes without error | ✅ pass (per T04) |
| 5 | nginx serves /assets/ directory | ✅ pass (per T04) |
| 6 | `curl -s .../browser/ | grep -c '/assets/'` ≥ 3 — got 29 | ✅ pass (per T04) |
| 7 | Docker workspace: htmx requests succeed (no JS errors) | ✅ pass (per T04) |
| 8 | Docker workspace: Cytoscape loaded | ✅ pass (per T04) |
| 9 | Docker workspace: dockview panels render | ✅ pass (per T04) |

## Requirements Advanced

- No existing requirements directly map to this slice — PERF-02 through PERF-07 are new requirements from M029 scope (not yet in REQUIREMENTS.md)

## Requirements Validated

- None — pending S02-S05 completion to validate the full PERF requirement set

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- **T03 absorbed into T04:** T03 had dispatch failures (3 attempts). T04 recovered all T03 deliverables from the M027 worktree and applied them as part of the Docker integration task.
- **highlight.js npm has no UMD:** The npm package only ships CJS/ESM, unlike the CDN version. Required esbuild bundling from `highlight.js/lib/common` — documented in KNOWLEDGE.md.
- **Shared volume at /srv/built-assets/ instead of /usr/share/nginx/html/assets/:** Docker rejects sub-mounts inside read-only bind mounts. Used a separate mount point with nginx alias directive.
- **Docker entrypoint script for volume population:** Named volumes only get image contents on first creation. The entrypoint copies on every start so rebuilds take effect without `docker compose down -v`.
- **App JS target esnext instead of es2020:** `sparql-console.js` uses top-level await.

## Known Limitations

- **Startup ordering:** On fresh `docker compose up -d`, the API may start before the frontend entrypoint populates the shared volume. A `docker compose restart api` is needed after the first deployment. Could be improved with a depends_on health check.
- **Dockview layout warning:** `saved dockview layout incompatible, rebuilding` appears in console — pre-existing (layout format changed between versions), app recovers gracefully.
- **No compression or cache headers yet:** Built assets are served uncompressed without cache headers. S02 adds gzip and immutable caching.
- **No CSS code-splitting yet:** Admin pages still load workspace.css. S03 splits CSS by route.

## Follow-ups

- S02 should add `gzip_static on;` to the `/assets/` location block to serve the .gz pre-compressed files (already generated by build.js)
- S02 should add `Cache-Control: public, max-age=31536000, immutable` to the `/assets/` location since all filenames are content-hashed
- S03 can extend the build.js manifest pattern for per-route CSS bundles

## Files Created/Modified

- `frontend/package.json` — npm project with 18 CDN deps + esbuild devDependency
- `frontend/package-lock.json` — lockfile for reproducible builds
- `frontend/build.js` — esbuild build script (vendor bundles, app minification, content hashing, manifest, gzip)
- `frontend/.gitignore` — ignores node_modules/ and dist/
- `frontend/Dockerfile` — multi-stage build (node:20-alpine → nginx:stable-alpine)
- `frontend/docker-entrypoint.sh` — copies built assets to shared volume on each start
- `frontend/nginx.conf` — added /assets/ location block with alias directive
- `docker-compose.yml` — added frontend_assets named volume, volume mounts for sharing
- `backend/app/template_helpers.py` — asset_url filter with multi-path manifest search
- `backend/tests/test_template_helpers.py` — 26 unit tests for both modes + edge cases
- `backend/app/main.py` — added init_template_helpers(app) call
- `backend/app/templates/base.html` — conditional vendor/CDN blocks + asset_url on all app assets
- `backend/app/templates/base_embed.html` — conditional vendor/CDN blocks
- `backend/app/templates/browser/workspace.html` — conditional dockview local/CDN blocks
- `backend/app/templates/admin/sparql.html` — conditional yasgui local/CDN blocks
- `backend/app/templates/admin/model_detail.html` — conditional chartjs local/CDN blocks
- `backend/app/templates/errors/403.html` — conditional lucide local/CDN blocks
- `frontend/static/js/theme.js` — hljs theme switcher with data-attribute production path

## Forward Intelligence

### What the next slice should know
- The .gz pre-compressed files are already generated by build.js — S02 just needs `gzip_static on;` in nginx, not runtime compression for /assets/
- The manifest.json content hash changes on every rebuild — S02's immutable Cache-Control is safe for /assets/
- HTML templates are NOT content-hashed — they need no-cache + ETag, not immutable
- The /assets/ location block in nginx.conf is the place to add S02's cache headers

### What's fragile
- **Startup ordering** — API container may start before frontend populates the shared volume. First deployment needs `docker compose restart api`. If S02 or S03 changes the Docker setup, this ordering issue must be preserved or fixed with a health check.
- **esbuild transform for vendor concatenation** — The vendor bundle concatenates 15 libraries then minifies. If a new library is added, it must be placed in the correct position in the dependency chain in build.js.

### Authoritative diagnostics
- `cat frontend/dist/manifest.json | python3 -m json.tool` — the manifest is the single source of truth for what got built
- `docker compose exec api python -c "from app.template_helpers import is_asset_manifest_available; print(is_asset_manifest_available())"` — confirms whether the API container sees the manifest
- `docker compose logs api 2>&1 | grep -i 'asset manifest'` — startup log line confirms mode

### What assumptions changed
- **highlight.js npm has no UMD bundle** — the plan assumed concatenation from a pre-built file. Required esbuild bundling instead. Documented in KNOWLEDGE.md.
- **Docker read-only bind mounts block sub-volumes** — the plan assumed mounting at /usr/share/nginx/html/assets/. Required a separate /srv/built-assets/ mount point.
