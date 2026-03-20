# S01: Build Pipeline & Local Vendoring

**Goal:** Workspace loads with all JS/CSS served from locally-bundled, minified, content-hashed files. htmx CRUD, Cytoscape graph, and dockview panels all work. Dev mode still uses raw files via volume mounts. Multi-stage Dockerfile builds optimized assets.
**Demo:** `docker compose build frontend` produces optimized assets. Navigate to workspace — all vendor JS/CSS loads from `/assets/` paths (no CDN requests). Create an object, edit it, save — htmx works. Open graph view — Cytoscape renders. Open a second panel — dockview works. SPARQL console opens with Yasgui. Admin model detail shows Chart.js sparkline.

## Must-Haves

- `frontend/package.json` with all 18 CDN dependencies as version-pinned npm packages + esbuild as devDependency
- `frontend/build.js` esbuild script producing: vendor bundle (IIFE), per-page vendor bundles (dockview, yasgui, chartjs), minified app JS/CSS, content-hashed filenames, and `manifest.json`
- `backend/app/template_helpers.py` with Jinja2 `asset_url` filter — resolves via manifest in production, returns original path in dev
- `base.html` and `base_embed.html` use conditional blocks: manifest available → local vendor bundle, no manifest → existing CDN URLs (dev mode preserved)
- `workspace.html` loads dockview from local workspace-vendor bundle (production) or CDN (dev)
- `admin/sparql.html` loads Yasgui from local bundle (production) or CDN (dev)
- `admin/model_detail.html` loads Chart.js from local bundle (production) or CDN (dev)
- `theme.js` highlight.js theme switcher works with both local (data attributes) and CDN (fallback) paths
- Multi-stage `frontend/Dockerfile`: Node.js stage runs `npm ci && node build.js`, nginx stage copies dist/ to `/usr/share/nginx/html/assets/`
- nginx.conf has `/assets/` location block serving built assets
- docker-compose.yml dev workflow unaffected: volume mounts serve raw files, override built assets
- Zero CDN `<script>`/`<link>` tags in production rendering path (all behind `{% if not asset_manifest_available %}` guards)

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Docker stack must load workspace with local assets, htmx CRUD must work)
- Human/UAT required: no (curl + Docker compose + grep verification sufficient)

## Verification

- `cd frontend && npm ci && node build.js` — produces `dist/` directory with `manifest.json` containing mappings for all vendor bundles, app JS/CSS, and hljs theme CSS files
- `python -m pytest backend/tests/test_template_helpers.py -v` — unit tests for asset_url filter in both dev mode (no manifest) and production mode (with manifest)
- `grep -rn 'unpkg\|jsdelivr\|cdnjs' backend/app/templates/ | grep -v '{% if not\|{# dev\|else\|endif\|{%- if not'` — zero unguarded CDN references (all CDN URLs must be inside dev-mode conditional blocks)
- `docker compose build frontend` — completes without error
- `docker compose up -d && sleep 5` then `curl -sI http://localhost:3000/assets/ | head -5` — nginx serves assets directory
- `curl -s http://localhost:3000/browser/ | grep -c '/assets/'` — at least 3 production asset references in rendered HTML (vendor.js, vendor.css, workspace.js at minimum)
- Docker workspace page: create object, edit title, save → htmx request succeeds (no JS errors)
- Docker workspace page: open graph view → Cytoscape renders (no missing cytoscape global)
- Docker workspace page: dockview panels render → no console errors about missing DockviewComponent

## Observability / Diagnostics

- Runtime signals: `asset_url` filter logs a warning at startup if manifest.json is expected but missing (production mode detection via environment or file presence)
- Inspection surfaces: `manifest.json` in Docker container at `/usr/share/nginx/html/assets/manifest.json` — inspect with `docker compose exec frontend cat /usr/share/nginx/html/assets/manifest.json`
- Failure visibility: If manifest is missing/malformed, asset_url returns original paths (graceful degradation to dev mode behavior), logged as warning
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: none (S01 is the first slice)
- New wiring introduced: `template_helpers.py` registered as Jinja2 filter in `main.py`, `frontend/Dockerfile` multi-stage build, nginx `/assets/` location block
- What remains before the milestone is truly usable end-to-end: S02 (compression + cache headers), S03 (CSS code-splitting), S04 (backend profiling), S05 (Lighthouse verification + QUIC decision)

## Tasks

- [x] **T01: Create frontend npm project and esbuild build script** `est:2h`
  - Why: Foundation for all vendoring — defines npm deps, builds vendor bundles, app bundles, manifest.json. Without this, nothing else can reference local assets.
  - Files: `frontend/package.json`, `frontend/build.js`, `frontend/.gitignore`
  - Do: Create package.json with all 18 CDN deps version-pinned + esbuild devDependency. Create build.js that uses esbuild to: (1) bundle vendor deps into vendor.min.js (IIFE format, correct dependency order for Cytoscape stack), (2) copy/minify vendor CSS (driver.css → vendor.min.css, hljs github + github-dark themes as separate files), (3) bundle dockview-core into workspace-vendor.min.js + workspace-vendor.min.css, (4) bundle Yasgui into yasgui.min.js + yasgui.min.css, (5) bundle Chart.js into chartjs.min.js, (6) minify each app JS/CSS file individually, (7) content-hash all output filenames, (8) write manifest.json mapping logical names to hashed filenames, (9) generate .gz pre-compressed siblings. ninja-keys must be bundled as IIFE (it self-registers a web component via side effects). Cytoscape plugins must concatenate in dependency order: cytoscape → layout-base → cose-base → fcose → dagre → dagre-layout. Use `--keep-names` for htmx compatibility. Add `dist/` and `node_modules/` to frontend/.gitignore.
  - Verify: `cd frontend && npm ci && node build.js` completes without error. `ls dist/` shows vendor-*.min.js, vendor-*.min.css, workspace-vendor-*.min.js, hljs-github-*.css, yasgui-*.min.js, chartjs-*.min.js, all app files, manifest.json, and .gz siblings. `cat dist/manifest.json | python3 -m json.tool` shows valid JSON with entries for all expected assets.
  - Done when: `node build.js` produces a complete dist/ directory with manifest.json containing ≥25 entries (18 source JS files + 10 source CSS files + vendor bundles + page-specific bundles)

- [x] **T02: Create Jinja2 asset_url filter with dev/prod mode and unit tests** `est:1h`
  - Why: The bridge between build output and templates. Without this filter, templates can't resolve content-hashed filenames. Unit tests prove both modes work before touching any templates.
  - Files: `backend/app/template_helpers.py`, `backend/app/main.py`, `backend/tests/test_template_helpers.py`
  - Do: Create template_helpers.py with: (1) `_load_manifest()` function that reads manifest.json from a configurable path (default: `/usr/share/nginx/html/assets/manifest.json`), returns dict or None if file doesn't exist. (2) Module-level `_manifest` loaded once at import time. (3) `asset_url(name)` filter function: if manifest exists and name is in manifest, returns `/assets/{manifest[name]}`; otherwise returns `/js/{name}` for .js files, `/css/{name}` for .css files. (4) `asset_manifest_available` boolean for template globals. Wire into main.py: register `asset_url` as Jinja2 filter, register `asset_manifest_available` as template global. Write unit tests covering: filter with manifest (returns /assets/ path), filter without manifest (returns /js/ or /css/ path), filter with missing key in manifest (falls back gracefully), manifest loading from file, manifest loading when file missing.
  - Verify: `cd backend && python -m pytest tests/test_template_helpers.py -v` — all tests pass
  - Done when: Unit tests pass for both production (manifest present) and dev (manifest absent) modes. Filter registered in main.py and accessible in Jinja2 templates.

- [x] **T03: Replace CDN references in all templates with conditional local/CDN blocks** `est:2h`
  - Why: The highest-risk change — every CDN `<script>`/`<link>` must be replaced with manifest-resolved local paths in production, while preserving CDN fallback for dev mode. A single missed reference means a broken page.
  - Files: `backend/app/templates/base.html`, `backend/app/templates/base_embed.html`, `backend/app/templates/browser/workspace.html`, `backend/app/templates/admin/sparql.html`, `backend/app/templates/admin/model_detail.html`, `frontend/static/js/theme.js`
  - Do: (1) **base.html** — wrap all 15 CDN `<script>`/`<link>` tags in `{% if not asset_manifest_available %}...{% else %}` block. Production block loads: `vendor.js` (single script replacing 14 CDN scripts), `vendor.css` (driver.css), hljs theme link with `data-light-href` and `data-dark-href` attributes from `asset_url`. Dev block keeps existing CDN tags unchanged. For app JS/CSS files (workspace.js, canvas.js, etc.), use `{{ 'workspace.js' | asset_url }}` unconditionally (works in both modes — dev returns /js/workspace.js, prod returns /assets/workspace-hash.min.js). Same for app CSS. (2) **base_embed.html** — same pattern: production loads embed-vendor.js (htmx + marked + dompurify + lucide subset) or vendor.js, dev keeps CDN URLs. App assets use asset_url unconditionally. (3) **workspace.html** — dockview CSS + JS: conditional block for production (workspace-vendor.js/css) vs CDN. (4) **admin/sparql.html** — Yasgui: conditional for production (yasgui.js/css) vs CDN. (5) **admin/model_detail.html** — Chart.js: conditional for production (chartjs.js) vs CDN. (6) **theme.js** — update hljs theme switcher to check for data-light-href/data-dark-href attributes first (production path), fall back to CDN URL construction (dev path).
  - Verify: `grep -rn 'unpkg\|jsdelivr\|cdnjs' backend/app/templates/ | grep -v 'if not asset_manifest\|else\|endif\|dev mode\|{#'` returns zero lines (all CDN URLs are inside dev-mode guards). `grep -c 'asset_url' backend/app/templates/base.html` returns ≥15 (all app assets use the filter).
  - Done when: Every CDN URL in every template is inside a `{% if not asset_manifest_available %}` guard. Every app JS/CSS file reference uses `{{ name | asset_url }}`. theme.js handles both local and CDN hljs paths.

- [x] **T04: Multi-stage Dockerfile, nginx config, and Docker integration test** `est:2h`
  - Why: Wires the build pipeline into Docker so `docker compose build` produces optimized assets automatically. Verifies the complete integration: build → serve → render → interact.
  - Files: `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`, `docker-compose.test.yml`
  - Do: (1) **frontend/Dockerfile** — rewrite as multi-stage: Stage 1 (`node:20-alpine` as builder): `WORKDIR /build`, copy package.json + package-lock.json, `RUN npm ci`, copy build.js + static/, `RUN node build.js`. Stage 2 (`nginx:stable-alpine`): copy static/ to `/usr/share/nginx/html/` (raw files for /css/ and /js/ paths), copy dist/ to `/usr/share/nginx/html/assets/` (built assets), copy dist/manifest.json to `/usr/share/nginx/html/assets/manifest.json`, copy nginx.conf. (2) **nginx.conf** — add `/assets/` location block serving built files with `try_files $uri =404` (caching headers added in S02). (3) **docker-compose.yml** — no changes needed (volume mounts in dev override image contents; production uses `docker compose build` without volume mounts). (4) **docker-compose.test.yml** — same volume mount structure as dev, so test stack uses raw files. (5) **Backend manifest path** — update template_helpers.py manifest path to check `/usr/share/nginx/html/assets/manifest.json` (Docker production) and optionally a local dev path. Since the backend container doesn't have the frontend filesystem, the manifest must be shared. Options: (a) mount dist/manifest.json into the API container, or (b) have the build copy manifest.json to a shared volume, or (c) mount the frontend dist as a read-only volume in the API container. Simplest: add a volume mount in docker-compose.yml production profile that shares manifest.json. For the default dev profile (volume mounts), manifest.json won't exist and the filter falls back to dev mode — which is exactly right. (6) Build and test: `docker compose build frontend`, `docker compose up -d`, verify workspace loads with `/assets/` URLs, verify htmx CRUD, verify Cytoscape, verify dockview.
  - Verify: `docker compose build frontend` completes. `docker compose exec frontend ls /usr/share/nginx/html/assets/manifest.json` shows the file. `docker compose exec frontend ls /usr/share/nginx/html/assets/ | wc -l` shows ≥50 files. `curl -s http://localhost:3000/assets/manifest.json | python3 -m json.tool | head -5` returns valid JSON. Workspace page loads without JS console errors.
  - Done when: `docker compose build && docker compose up -d` produces a working stack where all vendor JS/CSS loads from local /assets/ paths. htmx CRUD, Cytoscape graph, and dockview panels all function. No CDN requests visible in browser network tab (production mode).

## Files Likely Touched

- `frontend/package.json` (new)
- `frontend/package-lock.json` (new, generated)
- `frontend/build.js` (new)
- `frontend/.gitignore` (new or modified)
- `frontend/Dockerfile` (rewritten)
- `frontend/nginx.conf` (modified — /assets/ location)
- `backend/app/template_helpers.py` (new)
- `backend/app/main.py` (modified — register filter + global)
- `backend/app/templates/base.html` (modified — conditional CDN/local blocks)
- `backend/app/templates/base_embed.html` (modified — conditional CDN/local blocks)
- `backend/app/templates/browser/workspace.html` (modified — dockview local bundle)
- `backend/app/templates/admin/sparql.html` (modified — yasgui local bundle)
- `backend/app/templates/admin/model_detail.html` (modified — chart.js local bundle)
- `frontend/static/js/theme.js` (modified — hljs theme data-attribute support)
- `backend/tests/test_template_helpers.py` (new)
- `docker-compose.yml` (potentially modified — manifest volume mount for API container)
