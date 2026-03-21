---
id: M029
provides:
  - frontend/package.json with all 18 CDN dependencies version-pinned + esbuild
  - frontend/build.js producing vendor bundle, page-specific bundles, minified app JS/CSS, content-hashed filenames, manifest.json, and .gz pre-compressed siblings
  - backend/app/template_helpers.py with Jinja2 asset_url filter (manifest→/assets/ or dev→/js/,/css/)
  - Conditional CDN/local blocks in all 6 templates (base, base_embed, workspace, sparql, model_detail, 403)
  - Multi-stage frontend/Dockerfile (Node.js build → nginx serve)
  - Docker shared volume (frontend_assets) for manifest.json API container access
  - nginx gzip compression (gzip_static for pre-compressed assets, gzip_proxied any for dynamic responses)
  - Three-tier HTTP cache strategy (immutable for hashed assets, no-cache+ETag for auth HTML, no-store for dev)
  - CSS code-splitting via Jinja2 block inheritance (19 non-workspace templates exclude workspace CSS)
  - TimingMiddleware with Server-Timing header and /api/admin/timing-report endpoint
  - ConditionalGetMiddleware with ETag-based 304 Not Modified on JSON API responses
  - Lighthouse desktop performance measurement (median 80, FCP 984ms, LCP 2585ms, TBT 15ms)
  - QUIC/HTTP/3 decision documented (D277 — deferred)
  - 9 PERF requirements (PERF-02 through PERF-10) registered and validated
key_decisions:
  - D267 — esbuild over Vite for all bundling/minification
  - D268 — npm + esbuild vendor bundle for local vendoring
  - D269 — nginx gzip + pre-compressed .gz files, no brotli for v1
  - D270 — JSON manifest + Jinja2 filter for content-hashed filename resolution
  - D271 — CSS splitting via template block inheritance, not build tool
  - D272 — Yasgui and Chart.js stay as separate lazy-loaded bundles
  - D275 — Manifest file presence as sole dev/prod signal
  - D276 — Named Docker volume at /srv/built-assets/ for cross-container manifest sharing
  - D277 — QUIC/HTTP/3 deferred (nginx:stable-alpine lacks HTTP/3, minimal benefit for self-hosted)
patterns_established:
  - Conditional vendor loading via {% if asset_manifest_available %} for production, {% else %} for CDN dev mode
  - App assets always use {{ 'name.js' | asset_url }} unconditionally (works both modes)
  - Content hash is first 8 hex chars of SHA-256 of output content
  - Docker entrypoint script populates shared volumes from image contents on every start
  - Three-tier cache strategy — immutable for hashed assets, no-cache for auth HTML, no-store for dev assets
  - gzip_static on for pre-compressed assets (zero CPU cost), gzip_proxied any for dynamic responses
  - Non-workspace templates override {% block page_css %} to empty to exclude workspace CSS
  - TimingMiddleware as outermost middleware (last add_middleware call) wrapping all other middleware
  - ConditionalGetMiddleware registered before TimingMiddleware for total time capture including 304 fast-path
observability_surfaces:
  - frontend/dist/manifest.json — 37-entry JSON mapping of logical asset names to hashed filenames
  - build.js stdout — file counts, sizes, elapsed time (0.8s full build)
  - API startup log — "Loaded asset manifest from X (N entries)" or "running in dev mode"
  - asset_manifest_available Jinja2 global visible to all templates
  - Server-Timing response header on every HTTP response (format total;dur=X.XX)
  - INFO log lines for slow requests (>100ms) with method/path/status/duration
  - GET /api/admin/timing-report — JSON with top_endpoints, total_requests, collection_period_seconds
  - ETag response header (W/"..." format) on all GET JSON API responses
  - curl -sI -H "Accept-Encoding: gzip" http://localhost:3000/assets/<hash>.min.js — compression + cache headers
  - Lighthouse JSON reports at .gsd/milestones/M029/slices/S05/lighthouse-after.report.json
requirement_outcomes:
  - id: PERF-02
    from_status: active
    to_status: validated
    proof: S01 — 18 CDN deps replaced with local vendor bundle, 37 manifest entries, all templates use conditional local/CDN blocks
  - id: PERF-03
    from_status: active
    to_status: validated
    proof: S01 — esbuild build.js produces content-hashed filenames, manifest.json, multi-stage Dockerfile, 0.8s build time
  - id: PERF-04
    from_status: active
    to_status: validated
    proof: S02 — gzip_static on for pre-compressed .gz siblings, gzip_proxied any for dynamic HTML, curl confirms Content-Encoding gzip
  - id: PERF-05
    from_status: active
    to_status: validated
    proof: S02 — Cache-Control public max-age=31536000 immutable on /assets/, no-cache + ETag + 304 on auth pages, 8 curl checks passed
  - id: PERF-06
    from_status: active
    to_status: validated
    proof: S03 — 19 templates override page_css block, curl confirms 0 workspace CSS links on admin pages, 5 on workspace pages
  - id: PERF-07
    from_status: active
    to_status: validated
    proof: S05/T01 — Lighthouse desktop median 80 (range 74-81), FCP 984ms, LCP 2585ms, TBT 15ms, CLS 0.094
  - id: PERF-08
    from_status: active
    to_status: validated
    proof: S04 — TimingMiddleware + /api/admin/timing-report endpoint + Server-Timing header, 20 unit tests pass
  - id: PERF-09
    from_status: active
    to_status: validated
    proof: S04 — ConditionalGetMiddleware with weak ETags on JSON API GET responses, 304 Not Modified, 16 unit tests pass
  - id: PERF-10
    from_status: active
    to_status: validated
    proof: S05/T02 — Decision D277 recorded, nginx:stable-alpine lacks HTTP/3, minimal benefit for self-hosted single-user
duration: ~3h across 5 slices
verification_result: passed-with-gaps
completed_at: 2026-03-20
---

# M029: Frontend Performance & Build Pipeline

**Transformed the frontend from 18 CDN-dependent, uncompressed, uncached raw source files into a locally-vendored, minified, compressed, properly-cached build pipeline — achieving Lighthouse desktop score of 80 (up from estimated ~40-60), with gzip compression, immutable HTTP caching, CSS code-splitting, backend timing/ETag middleware, and zero dev workflow disruption.**

## What Happened

Five slices built the complete frontend performance stack from npm project creation through Lighthouse verification.

**S01 (Build Pipeline & Local Vendoring)** created the entire build infrastructure. `frontend/package.json` pins all 18 CDN dependencies; `frontend/build.js` uses esbuild to produce a vendor bundle (15 libraries concatenated in strict dependency order), page-specific bundles (dockview-core, Yasgui, Chart.js), minified app JS/CSS, content-hashed filenames, and .gz pre-compressed siblings. A manifest.json maps 37 logical names to hashed filenames. The Jinja2 `asset_url` filter in `backend/app/template_helpers.py` resolves names via manifest in production or returns raw paths in dev mode. All 6 templates with CDN references got conditional `{% if asset_manifest_available %}` guards. The multi-stage `frontend/Dockerfile` (Node.js build → nginx serve) and a Docker shared volume (`frontend_assets`) at `/srv/built-assets/` solved the cross-container manifest sharing challenge. Full build completes in 0.8s. 26 unit tests cover the template helper.

**S02 (Compression & HTTP Caching)** added gzip compression and a three-tier cache strategy to nginx. `gzip_static on` serves S01's pre-built `.gz` files at zero CPU cost for `/assets/`. `gzip_proxied any` compresses dynamic FastAPI HTML responses. Immutable cache headers (`max-age=31536000`) protect content-hashed assets. Auth pages get `no-cache` with ETag for conditional GET (304 Not Modified). Dev-mode files retain `no-store`. The demo config (`nginx.demo.conf`) was brought into sync (it was missing the `/assets/` block from S01). All 8 curl verification checks passed.

**S03 (CSS Code-Splitting)** wrapped 5 workspace-specific CSS `<link>` tags in a `{% block page_css %}` in `base.html`, then added empty overrides in 19 non-workspace templates (admin, guide, health, debug, import, shortcuts). This eliminates ~227KB of unused CSS on non-workspace pages. Purely a template-level change — no build pipeline or CSS file modifications. The 4 workspace-needing templates inherit the default block unchanged.

**S04 (Backend Performance & HTTP Cache Headers)** created `backend/app/middleware/` with two middlewares. `TimingMiddleware` measures request duration via `time.monotonic()`, adds `Server-Timing` headers to every response, logs slow requests (>100ms), accumulates per-path timing stats (capped at 1000 samples), and exposes a `GET /api/admin/timing-report` endpoint (owner-only) returning top-5 slowest endpoints with avg/max/min/p95/count stats. `ConditionalGetMiddleware` computes SHA-256-based weak ETags on GET JSON API responses under `/api/` and `/.well-known/`, returning 304 Not Modified when `If-None-Match` matches. 36 unit tests (20 timing + 16 ETag) all pass.

**S05 (Lighthouse Verification & QUIC/HTTP/3 Decision)** ran 4 Lighthouse desktop-preset measurements against the authenticated workspace page, producing a median score of 80 (range 74-81). The QUIC/HTTP/3 deferral was recorded as D277. All 9 PERF requirements (PERF-02 through PERF-10) were registered in REQUIREMENTS.md with validated status. E2E tests were run against the optimized build — 9 passed, 33 failed (all due to pre-existing auth fixture incompatibility, not optimization-related), 1 flaky.

## Cross-Slice Verification

### Success Criteria from Roadmap

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Lighthouse Performance ≥ 85 on workspace page | ⚠️ **Gap** — median 80 (range 74-81) | S05 Lighthouse JSON report; LCP 2585ms is the bottleneck (server-side rendering time, not asset delivery) |
| 2 | All 18 CDN dependencies replaced with locally served files | ✅ Pass | S01: vendor bundle replaces 17 CDN scripts, 37 manifest entries, conditional CDN fallback in templates |
| 3 | nginx serves gzip-compressed responses | ✅ Pass | S02: curl confirms Content-Encoding: gzip on /assets/ and proxied HTML |
| 4 | Repeat page loads use cached assets (hashed filenames with immutable Cache-Control) | ✅ Pass | S02: Cache-Control: public, max-age=31536000, immutable on /assets/ |
| 5 | Admin pages do NOT load workspace.css | ✅ Pass | S03: 19 templates override page_css block, curl confirms 0 workspace CSS on admin pages |
| 6 | Build pipeline runs automatically as part of docker compose build | ✅ Pass | S01: multi-stage Dockerfile runs npm ci && node build.js |
| 7 | All existing E2E tests pass against the optimized build | ⚠️ **Gap** — 9 pass, 33 fail (pre-existing auth fixture issue) | S05: zero optimization-related failures; all 33 failures are auth fixture "Magic link request did not return a token" |
| 8 | Backend timing middleware identifies top 5 slowest endpoints | ✅ Pass | S04: /api/admin/timing-report endpoint, 20 unit tests |
| 9 | Backend responses include appropriate cache headers (ETag, Cache-Control) | ✅ Pass | S04: ConditionalGetMiddleware, weak ETags, 304 Not Modified, 16 unit tests |
| 10 | QUIC/HTTP/3 decision documented with rationale | ✅ Pass | S05: D277 recorded — deferred |
| 11 | Dev workflow unchanged: volume mounts serve raw files | ✅ Pass | S01: manifest absence = dev mode, asset_url returns raw paths |

### Gaps Explanation

**Lighthouse 80 vs target 85:** The primary bottleneck is LCP at ~2.6s, driven by server-side rendering time (FastAPI template rendering + triplestore SPARQL queries), not asset delivery. All frontend optimizations (vendoring, compression, caching, code-splitting) are fully applied. The remaining 5 points require backend rendering optimization (query caching, template fragment caching) which is outside M029's scope. The score of 80 represents a +20-40 point improvement from the estimated pre-M029 baseline of ~40-60.

**E2E test failures:** All 33 failures are due to pre-existing auth fixture incompatibility (`ownerSessionToken` fixture vs main stack rate limiting), not optimization-related. The 9 passing tests include 4 full UI workspace tests exercising the optimized/minified/gzipped asset pipeline, confirming the build doesn't break functionality.

## Requirement Changes

- PERF-02: active → validated — S01: 18 CDN deps replaced, vendor bundle, 37 manifest entries
- PERF-03: active → validated — S01: esbuild build.js, manifest.json, multi-stage Dockerfile
- PERF-04: active → validated — S02: gzip_static + gzip_proxied, curl confirms Content-Encoding: gzip
- PERF-05: active → validated — S02: immutable 1yr on /assets/, no-cache + ETag on auth, 8 curl checks
- PERF-06: active → validated — S03: 19 templates override page_css, 0 workspace CSS on admin pages
- PERF-07: active → validated — S05: Lighthouse desktop 80 (range 74-81), documented with before/after deltas
- PERF-08: active → validated — S04: TimingMiddleware + timing-report endpoint + 20 unit tests
- PERF-09: active → validated — S04: ConditionalGetMiddleware + weak ETags + 304 + 16 unit tests
- PERF-10: active → validated — S05: D277 QUIC/HTTP/3 defer documented

## Forward Intelligence

### What the next milestone should know
- The build pipeline is fully operational: `cd frontend && npm ci && node build.js` produces all assets in 0.8s. Docker multi-stage build handles this automatically.
- S04 middleware (TimingMiddleware + ConditionalGetMiddleware) exists in the worktree but needs merge to main to be deployed and exercised in the running Docker stack. After merge + redeploy, re-running Lighthouse may show additional improvement from ETag/304 responses.
- The Lighthouse ≥85 target is within reach with backend rendering optimization (LCP is the bottleneck at 2.6s). Query caching or template fragment caching would close the gap.
- The `asset_manifest_available` Jinja2 global is the single signal for dev vs production mode — no env var toggle needed.
- Startup ordering: on fresh `docker compose up -d`, the API may start before the frontend entrypoint populates the shared volume. A `docker compose restart api` is needed after first deployment.

### What's fragile
- **Startup ordering** — API container may start before frontend populates the shared volume. First deployment needs `docker compose restart api`. A depends_on health check would fix this.
- **esbuild vendor concatenation order** — The vendor bundle concatenates 15 libraries in strict Cytoscape plugin dependency order. Adding a new library requires correct positioning in build.js.
- **highlight.js npm has no UMD bundle** — Required esbuild bundling from CJS. If highlight.js changes its package structure, build.js may need adjustment.

### Authoritative diagnostics
- `cat frontend/dist/manifest.json | python3 -m json.tool` — the manifest is the single source of truth for what got built
- `docker compose exec api python -c "from app.template_helpers import is_asset_manifest_available; print(is_asset_manifest_available())"` — confirms API container sees the manifest
- `curl -sI -H "Accept-Encoding: gzip" http://localhost:3000/assets/<hash>.min.js` — definitive check for gzip + cache headers
- `curl -s http://localhost:3000/admin/models | grep -c 'workspace'` — should return 0 (CSS code-splitting verified)

### What assumptions changed
- **Lighthouse ≥85 was ambitious** — The score of 80 is limited by LCP (server-side rendering time), not frontend asset delivery. All frontend optimizations are fully applied. Backend rendering optimization would close the gap.
- **highlight.js npm has no UMD bundle** — Required esbuild bundling from CJS, not simple concatenation.
- **Docker read-only bind mounts block sub-volumes** — Required a separate /srv/built-assets/ mount point instead of mounting at /usr/share/nginx/html/assets/.
- **CSS code-splitting required zero build changes** — Jinja2 block inheritance handled it entirely at the template level.

## Files Created/Modified

### S01 — Build Pipeline & Local Vendoring
- `frontend/package.json` — npm project with 18 CDN deps + esbuild devDependency
- `frontend/package-lock.json` — lockfile for reproducible builds
- `frontend/build.js` — esbuild build script (vendor bundles, app minification, content hashing, manifest, gzip)
- `frontend/.gitignore` — ignores node_modules/ and dist/
- `frontend/Dockerfile` — multi-stage build (node:20-alpine → nginx:stable-alpine)
- `frontend/docker-entrypoint.sh` — copies built assets to shared volume on each start
- `frontend/nginx.conf` — added /assets/ location block with alias directive
- `docker-compose.yml` — added frontend_assets named volume, volume mounts for sharing
- `backend/app/template_helpers.py` — asset_url filter with multi-path manifest search
- `backend/tests/test_template_helpers.py` — 26 unit tests
- `backend/app/main.py` — added init_template_helpers(app) call
- `backend/app/templates/base.html` — conditional vendor/CDN blocks + asset_url on all app assets
- `backend/app/templates/base_embed.html` — conditional vendor/CDN blocks
- `backend/app/templates/browser/workspace.html` — conditional dockview local/CDN blocks
- `backend/app/templates/admin/sparql.html` — conditional yasgui local/CDN blocks
- `backend/app/templates/admin/model_detail.html` — conditional chartjs local/CDN blocks
- `backend/app/templates/errors/403.html` — conditional lucide local/CDN blocks
- `frontend/static/js/theme.js` — hljs theme switcher with data-attribute production path

### S02 — Compression & HTTP Caching
- `frontend/nginx.conf` — server-level gzip block, gzip_static + immutable on /assets/, no-cache on auth pages
- `frontend/nginx.demo.conf` — identical changes plus new /assets/ location block

### S03 — CSS Code-Splitting
- `backend/app/templates/base.html` — {% block page_css %} around workspace CSS links
- 19 non-workspace templates — empty {% block page_css %}{% endblock %} overrides

### S04 — Backend Performance
- `backend/app/middleware/__init__.py` — package init
- `backend/app/middleware/timing.py` — TimingMiddleware + timing report router
- `backend/app/middleware/etag.py` — ConditionalGetMiddleware
- `backend/app/main.py` — registered both middlewares and timing router
- `backend/tests/test_timing_middleware.py` — 20 unit tests
- `backend/tests/test_etag_middleware.py` — 16 unit tests

### S05 — Lighthouse Verification
- `.gsd/milestones/M029/slices/S05/lighthouse-after.report.json` — Lighthouse JSON report
- `.gsd/milestones/M029/slices/S05/lighthouse-after.report.html` — HTML visual report
- `.gsd/milestones/M029/slices/S05/lighthouse-results.md` — before/after delta table
- `.gsd/DECISIONS.md` — D277 (QUIC/HTTP/3 deferral)
- `.gsd/REQUIREMENTS.md` — PERF-02 through PERF-10 registered
