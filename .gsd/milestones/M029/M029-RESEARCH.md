# M029 — Frontend Performance & Build Pipeline — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

M029 addresses accumulated frontend performance debt across 28 milestones of feature work. The current state is: 18 CDN dependencies loaded on every page, zero compression, no caching (`no-store, no-cache` on all static assets), no minification, no build pipeline, no CSS code-splitting, and HTTP/1.1 only. The frontend Dockerfile is 4 lines (FROM nginx:stable-alpine, copy files, expose 80).

The recommended approach is a phased build pipeline using **esbuild** (not Vite) for bundling/minification, **npm** for local vendoring of CDN dependencies, **nginx gzip_static + gzip on** for compression, **content-hashed filenames with a JSON manifest** read by a Jinja2 template filter for cache busting, and **route-based CSS splitting** via separate `<link>` tags in template blocks. QUIC/HTTP/3 should be researched but likely deferred — nginx:stable-alpine doesn't include HTTP/3 support, and the self-hosted single-user context means multiplexing benefits are minimal.

The highest-risk item is the **content-hashed filename → Jinja2 template integration** because every template that references `/js/workspace.js` or `/css/workspace.css` must switch to manifest-based lookups. The second risk is **htmx compatibility** — htmx uses `hx-on::` attributes and inline `<script>` blocks that must survive minification without breaking. Both should be proven in S01 before scaling to all assets.

## Recommendation

**Build tool: esbuild** — For a vanilla JS + htmx project with no ES module imports, esbuild's speed (~10ms builds) and simplicity far outweigh Vite's HMR and plugin ecosystem. Vite targets React/Vue SPAs; SemPKM is server-rendered with htmx. esbuild handles concatenation, minification, and content-hashing natively. Install via npm in a multi-stage Docker build.

**Vendoring: npm + esbuild bundle** — Create a `frontend/package.json` with all 18 CDN dependencies as npm packages. esbuild bundles them into a single `vendor.min.js` (and `vendor.min.css` where applicable). This eliminates CDN dependency completely and enables tree-shaking of unused exports.

**Compression: nginx gzip + pre-compressed .gz files** — Build step generates `.gz` files alongside originals. nginx `gzip_static on` serves pre-compressed files when available, `gzip on` as fallback for dynamic responses. Brotli is out of scope for v1 — nginx:stable-alpine doesn't include the brotli module without a custom build.

**Caching: content-hashed filenames + immutable headers** — esbuild's `--entry-names=[name]-[hash]` produces `workspace-a1b2c3d4.min.js`. A build script writes `manifest.json` mapping original names to hashed names. A Jinja2 template filter `{{ 'workspace.js' | asset_url }}` resolves via the manifest. Hashed assets get `Cache-Control: public, max-age=31536000, immutable`. HTML responses get `Cache-Control: no-cache` with ETag.

**CSS splitting: template block inheritance** — `base.html` loads only shared CSS (theme.css). `workspace.html` extends with workspace CSS stack. Admin templates load only admin CSS. This is a template-level change, not a build tool concern.

**Backend profiling: FastAPI middleware** — Simple timing middleware that logs request path + duration. Top-5 slowest report as a one-time analysis, not a permanent dashboard.

## Implementation Landscape

### Key Files

- `frontend/Dockerfile` — Currently 4 lines. Must become multi-stage: (1) Node.js stage installs deps + runs esbuild, (2) nginx stage copies built assets. Dev mode bypasses build via volume mounts.
- `frontend/nginx.conf` — Must add `gzip on`, `gzip_static on`, `gzip_types`, and split cache headers: `immutable` for `/assets/` (hashed), `no-cache` for HTML. Currently has `no-store, no-cache` on all `/css/` and `/js/`.
- `backend/app/templates/base.html` — Has 18 CDN `<script>`/`<link>` tags. Must replace with local vendor bundle references using manifest-resolved URLs.
- `backend/app/templates/base_embed.html` — Has 5 CDN scripts for embed iframes. Same treatment as base.html.
- `docker-compose.yml` — Frontend service volume mounts (`./frontend/static:/usr/share/nginx/html:ro`) must be preserved for dev mode. Production builds serve from the Docker image's built assets.
- `backend/app/vfs/resources.py` — Has existing Cache-Control header pattern (reference for backend caching).
- `frontend/static/js/workspace.js` — 4076 lines unminified, largest JS file. Primary minification target.
- `frontend/static/css/workspace.css` — ~160KB unminified, largest CSS file. Primary minification + splitting target.

### New Files to Create

- `frontend/package.json` — npm dependencies for all 18 CDN packages + esbuild as devDependency
- `frontend/build.js` — esbuild build script (vendor bundle + app bundles + CSS minification + manifest generation)
- `frontend/manifest.json` — Build output mapping original filenames to content-hashed filenames
- `backend/app/template_helpers.py` (or similar) — Jinja2 filter/global for manifest-based asset URL resolution
- `backend/app/middleware/timing.py` — Request timing middleware for profiling

### CDN Dependencies to Vendor (from base.html)

Based on the context document, these 18 CDN loads need vendoring:
1. htmx (core library)
2. Cytoscape.js (graph rendering)
3. cytoscape-layout-base (layout plugin)
4. cytoscape-cose-base (layout plugin)
5. cytoscape-fcose (layout plugin)
6. cytoscape-dagre (layout plugin)
7. dagre (layout dependency)
8. marked (Markdown rendering)
9. highlight.js (syntax highlighting)
10. DOMPurify (HTML sanitization)
11. Lucide (icon library)
12. Split.js (resizable panes — may still be used in some views)
13. Driver.js (guided tours)
14. dockview-core (panel layout)
15. ninja-keys (command palette)
16. CodeMirror (SPARQL editor — loaded via Yasgui)
17. @zazuko/yasgui (SPARQL console)
18. Chart.js (admin charts — model detail page only)

**Critical loading order:** Cytoscape + layout-base + cose-base + fcose + dagre + dagre-layout must load in dependency order. A single concatenated vendor bundle handles this naturally (concatenate in correct order).

### Build Order (Slice Sequencing)

**S01 — Audit & Build Pipeline Foundation (PROVE FIRST)**
- Lighthouse baseline measurement (before)
- Create `frontend/package.json` with all CDN deps
- Create esbuild build script producing vendor bundle + app bundles + CSS minification
- Content-hashed filenames with manifest.json
- Jinja2 manifest filter integration
- Multi-stage Dockerfile
- Prove: workspace loads correctly with locally-bundled vendor JS, htmx still works, Cytoscape renders, dockview panels work
- **This is the highest-risk slice** — if manifest integration or htmx compat breaks, everything downstream is blocked

**S02 — Compression & Caching**
- nginx gzip/gzip_static configuration
- Pre-compressed .gz file generation in build step
- Content-hashed asset caching (immutable headers)
- HTML response caching (ETag + no-cache)
- Verify: `curl -H "Accept-Encoding: gzip" -sI` shows compressed responses
- Verify: repeat loads show HTTP 304 or cache hits

**S03 — CSS Code-Splitting & Route Optimization**
- Split CSS loading by route in template blocks
- Admin pages: only style.css + theme.css
- Workspace pages: workspace CSS stack
- Auth pages: minimal CSS
- Source maps for production debugging
- Verify: admin page network tab shows no workspace.css

**S04 — Backend Performance & HTTP Cache Headers**
- Request timing middleware
- Identify top 5 slowest endpoints
- ETag generation for appropriate responses (SPARQL results, object pages)
- Conditional GET support (If-None-Match → 304)
- Review SPARQL query patterns for inefficiencies

**S05 — QUIC/HTTP/3 Research + Lighthouse Verification**
- Research nginx HTTP/3 support in Docker context
- Document decision with rationale
- Final Lighthouse measurement (after)
- Before/after delta documentation with FCP, LCP, TTI, TBT, CLS
- E2E test verification against optimized build
- User guide updates if applicable (mostly internal, likely no user-facing docs needed)

### Verification Approach

1. **Lighthouse CI:** Run `npx lighthouse` against Docker stack before and after, capture JSON reports. Target: Performance ≥ 85 (up from estimated ~40-60).
2. **Offline verification:** After vendoring, disconnect network and verify workspace loads from cache.
3. **Compression check:** `curl -H "Accept-Encoding: gzip" -sI http://localhost:3000/css/workspace.css | grep Content-Encoding` should show `gzip`.
4. **Cache check:** Second request to hashed asset should return 304 or be served from browser cache (no full download).
5. **CSS splitting:** Admin page network waterfall should NOT contain workspace.css.
6. **E2E tests:** All existing Playwright tests must pass against the optimized build.
7. **htmx sanity:** Workspace CRUD (create object, edit, save) works with minified JS.
8. **Asset size tracking:** Document before/after sizes for vendor bundle, app bundles, CSS.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| JS bundling/minification | esbuild | 100x faster than webpack, zero-config for concatenation, built-in content hashing |
| CSS minification | esbuild (CSS loader) or lightningcss | esbuild handles CSS natively; lightningcss for advanced transforms |
| Pre-compression | `gzip` CLI in build script | Simpler than a Node.js compression plugin; Alpine has gzip built-in |
| Manifest generation | Custom ~30-line Node.js script | esbuild's metafile output contains input→output mappings; transform to manifest.json |
| Lighthouse CI | `lighthouse` npm package | Standard tool, produces JSON reports, CI-compatible |

## Constraints

- **htmx inline handlers:** `hx-on::` attributes and inline `<script>` blocks in Jinja2 templates must survive. esbuild minifies external JS files, not HTML attributes — these are safe. But template-embedded `<script>` blocks are NOT processed by esbuild. They remain unminified (acceptable — they're small).
- **No ES modules in production:** Frontend JS uses IIFEs and global functions. esbuild must be configured for `--format=iife` (not esm). No `import`/`export` statements exist.
- **Dev workflow must not require build watcher:** Volume mounts in docker-compose.yml serve raw files directly to nginx, bypassing the Docker build. Developers edit JS/CSS and refresh — no build step. The build pipeline only runs during `docker compose build`.
- **Jinja2 templates rendered server-side:** The Python backend must read manifest.json at startup and expose an `asset_url` filter. Hot-reload in dev mode should serve unmanifested paths (direct file references work because dev nginx serves raw files).
- **nginx:stable-alpine image:** No brotli module. No HTTP/3 module. Custom nginx builds add Dockerfile complexity and maintenance burden.
- **Chart.js loaded on admin model detail page only** (D065) — should stay page-specific, not in the global vendor bundle. Same for Yasgui (loaded lazily on SPARQL tab click).

## Common Pitfalls

- **Cytoscape plugin loading order** — Cytoscape layout plugins must register after cytoscape core. In a concatenated vendor bundle, file order = execution order. The build script must concatenate in dependency order: cytoscape → layout-base → cose-base → fcose → dagre → dagre-layout.
- **Content hash invalidation cascade** — If vendor.js hash changes, every HTML page needs the new URL. The Jinja2 manifest filter handles this, but the manifest must be loaded once at app startup and cached (not re-read per request). In dev mode (no manifest file), the filter should return the original path.
- **gzip_static requires exact .gz sibling** — `gzip_static on` looks for `file.js.gz` next to `file.js`. The build script must generate these in the same output directory. Missing .gz files fall back to on-the-fly compression.
- **ETag generation cost** — Computing ETags for large SPARQL result sets on every request defeats the purpose. Use weak ETags based on query hash + last-modified timestamp, not full content hashing.
- **Dev vs production asset path divergence** — Dev serves `/js/workspace.js` (raw). Production serves `/assets/workspace-a1b2c3d4.min.js` (hashed). The Jinja2 filter must handle both modes cleanly. Simplest: in dev, return `/js/{name}`; in production, look up in manifest.
- **Source maps leak source code** — Generate source maps but serve them only in development or behind auth. For a self-hosted app this is low risk, but worth documenting.

## Open Risks

- **htmx + minified vendor bundle compatibility** — htmx registers global functions and event handlers. If esbuild's minification renames or tree-shakes htmx internals, workspace interactions break. **Mitigation:** Use `--keep-names` flag and test htmx CRUD operations immediately after bundling.
- **dockview-core as ES module** — dockview-core may be distributed as ESM only on npm. Wrapping it for IIFE consumption may require an esbuild shim. Need to verify the npm package's `main`/`module` fields.
- **Yasgui CDN bundle complexity** — @zazuko/yasgui bundles CodeMirror + YASQE + YASR. Its npm package may have peer dependencies or require specific bundler configuration. May need to keep Yasgui as a separate lazy-loaded bundle rather than including in the main vendor bundle.
- **Docker build time increase** — Adding a Node.js stage to the frontend Dockerfile increases build time. Mitigate with npm ci (not npm install) and Docker layer caching for node_modules.
- **Lighthouse score depends on server response time** — If the FastAPI backend is slow (SPARQL queries, template rendering), Lighthouse Performance score reflects backend latency, not just frontend optimization. Backend profiling (S04) may be needed to reach the ≥85 target.

## QUIC/HTTP/3 Pre-Research

**nginx:stable-alpine HTTP/3 status:** As of early 2026, the official `nginx:stable-alpine` image does NOT include HTTP/3 (QUIC) support. HTTP/3 requires nginx compiled with `--with-http_v3_module` against a QUIC-capable TLS library (BoringSSL or quiche). This is available in `nginx:mainline-alpine` with experimental flags but not in stable.

**Alternative: Caddy** — The project already uses Caddy for the demo instance (M025, D246). Caddy supports HTTP/3 out of the box with automatic HTTPS. However, switching the main stack from nginx to Caddy is a significant change affecting all nginx.conf location blocks, SSE proxy configuration, and the demo nginx.demo.conf.

**Recommendation:** Document HTTP/3 as deferred. The benefit for a self-hosted single-user tool over localhost is minimal — HTTP/2 multiplexing is the main win, and HTTP/2 over h2c (cleartext) is poorly supported by browsers. For production deployments with TLS (behind Caddy or a reverse proxy), HTTP/2 is automatic. HTTP/3 can be revisited if/when nginx:stable-alpine adds native support or if a Caddy migration is separately motivated.

## Requirements Analysis

The context document notes "No existing requirements — this introduces new capability (PERF-02 through PERF-10 to be created during planning)." PERF-01 already exists (event detail N+1 fix from M002).

**Candidate requirements for roadmap planning:**

| ID | Description | Class | Notes |
|----|-------------|-------|-------|
| PERF-02 | Local JS vendoring — all CDN deps served locally | core-capability | Table stakes — the primary user value |
| PERF-03 | Build pipeline produces minified, content-hashed assets | core-capability | Enables caching and reduces transfer size |
| PERF-04 | nginx gzip compression on HTML/CSS/JS/JSON/SVG | core-capability | ~70-80% transfer size reduction |
| PERF-05 | HTTP caching with immutable headers on hashed assets | core-capability | Instant repeat page loads |
| PERF-06 | CSS code-splitting by route | core-capability | Admin pages don't load workspace CSS |
| PERF-07 | Lighthouse Performance score ≥ 85 on workspace | quality-attribute | Measurable outcome target |
| PERF-08 | Backend response profiling (top 5 slowest endpoints) | quality-attribute | One-time analysis, not permanent feature |
| PERF-09 | Backend HTTP cache headers (ETag, conditional GET) | core-capability | Reduces redundant data transfer |
| PERF-10 | QUIC/HTTP/3 decision documented | quality-attribute | Research deliverable, not necessarily implementation |

**Not a requirement but worth tracking:** Dev workflow must not regress — volume mounts continue to work for edit-refresh cycle without a build step.

## Existing Patterns to Reuse

- **D065 (Chart.js per-page loading):** Establishes the pattern for page-specific vendor scripts not in the global bundle. Yasgui should follow the same pattern.
- **D125 (base_embed.html):** Separate minimal template. Embed pages should get their own slim vendor bundle (htmx + theme only).
- **D246 (Caddy for demo):** Caddy precedent exists for TLS/HTTP/2. If HTTP/3 is pursued, extending the Caddy pattern is lower risk than custom nginx.
- **backend/app/vfs/resources.py Cache-Control pattern:** Reference for how cache headers are currently set in Python.
- **Multi-stage Dockerfile pattern:** Not yet used in this project but standard Docker practice. Stage 1 builds, Stage 2 copies artifacts.

## Sources

- esbuild documentation for content hashing, metafile, and CSS bundling
- nginx gzip_static module documentation
- nginx HTTP/3 experimental support status
- Lighthouse CI npm package for automated scoring
- Existing codebase: `frontend/Dockerfile` (4 lines), `frontend/nginx.conf` (18 CDN deps confirmed via context)
