# M029: Frontend Performance & Build Pipeline

**Gathered:** 2026-03-17
**Status:** Queued — pending auto-mode execution

## Project Description

Establish a measurable frontend performance baseline using Lighthouse, WebPageTest, and asset size tracking, then systematically improve scores through a build pipeline (esbuild or Vite), local JS vendoring to eliminate CDN dependency, gzip/brotli compression, proper HTTP caching with content-hashed filenames, CSS code-splitting by route, and asset minification. Backend gets response profiling and HTTP cache header improvements (ETags, conditional GETs). QUIC/HTTP/3 is researched and implemented if the cost is low relative to the self-hosted Docker deployment model.

## Why This Milestone

The frontend has accumulated significant performance debt across 9 milestones of feature work:

- **18 CDN script/CSS loads** on every page (htmx, Cytoscape + 4 layout plugins, marked, highlight.js, DOMPurify, Lucide, Split.js, Driver.js, dockview-core) — each is a DNS lookup + TLS handshake + download from a third-party host. CDN outages or slowness directly impact the self-hosted app.
- **Zero compression** — nginx serves all responses without gzip or brotli. A 160KB workspace.css is sent uncompressed.
- **No caching** — CSS and JS use `no-store, no-cache` headers. Every page load re-downloads every asset.
- **No minification** — raw source files served directly. workspace.js is 4076 lines of unminified JS. workspace.css is 160KB of unminified CSS with comments.
- **No build pipeline** — no bundler, no package.json on the frontend side. No tree-shaking, no dead code elimination, no content-hashed filenames for cache busting.
- **All CSS loaded on every page** — workspace.css, views.css, vfs-browser.css, forms.css, and settings.css are all loaded on admin pages that don't need them.
- **No HTTP/2** — nginx proxies over HTTP/1.1, meaning no multiplexing, no header compression, no server push.

These aren't hypothetical problems — they compound into measurably slow page loads, especially on first visit or over slower connections. For a self-hosted tool, CDN dependencies also create an unnecessary external failure mode.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Experience measurably faster page loads (target: Lighthouse Performance score ≥ 85, up from current estimated ~40-60)
- Load the workspace with all assets served locally — no CDN dependencies, works fully offline/air-gapped
- See instant page loads on repeat visits due to proper HTTP caching with long-lived immutable assets
- Benefit from compressed responses (gzip/brotli) — ~70-80% reduction in transfer size
- Experience faster initial render due to route-appropriate CSS (admin pages don't load workspace CSS)
- Benefit from HTTP/2 multiplexing if QUIC/HTTP/3 or HTTP/2 is implemented

### Entry point / environment

- Entry point: `http://localhost:3000` (all routes — workspace, admin, auth pages)
- Environment: Docker Compose (api + triplestore + frontend/nginx)
- Live dependencies involved: None (the point is removing external dependencies)

## Completion Class

- Contract complete means: Lighthouse CI runs in CI-compatible fashion producing scores, build pipeline produces minified/hashed assets, all CDN scripts vendored locally, nginx serves compressed responses with proper cache headers, CSS split by route
- Integration complete means: full application works identically with optimized assets — all E2E tests pass, no visual regressions, htmx still works with minified JS, Cytoscape/dockview still render correctly
- Operational complete means: Docker build produces optimized assets automatically, no manual build step, dev workflow still supports hot-reload via volume mounts

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Lighthouse Performance score ≥ 85 on workspace page (measured before and after with delta documented)
- All 18 CDN dependencies replaced with locally served files — app works with network disconnected after initial page load
- nginx serves gzip or brotli compressed responses (verify via `curl -H "Accept-Encoding: gzip" -sI`)
- Repeat page loads use cached assets (HTTP 304 or cache-hit, not full re-download)
- Admin pages load only admin-relevant CSS/JS — workspace.css not loaded on `/admin/` routes
- Build pipeline runs as part of `docker compose build` — no manual step
- All existing E2E tests pass against the optimized build
- Backend slow endpoint report identifies top 5 slowest routes with timing data
- Backend responses include appropriate cache headers (ETag, Cache-Control, Last-Modified where applicable)
- QUIC/HTTP/3 decision documented with rationale — implemented if feasible, deferred with clear reasoning if not

## Risks and Unknowns

- **htmx compatibility with minified/bundled JS** — htmx uses inline event handlers (`hx-on::`), template-embedded JS snippets, and `htmx.trigger()` calls from external scripts. Bundling must not break these patterns. Risk: medium — htmx doesn't use module imports, so bundling is mainly about minification, not tree-shaking.
- **Cytoscape plugin loading order** — Cytoscape + layout-base + cose-base + fcose + dagre + dagre-layout must load in dependency order. Bundling must preserve this. Risk: low — a single concatenated vendor bundle handles this.
- **Content-hashed filenames with Jinja2 templates** — Templates reference `/js/workspace.js` by name. With content hashes (`workspace.a1b2c3.js`), templates need a manifest lookup. Risk: medium — need a build-time manifest + Jinja2 helper or filter.
- **Dev workflow friction** — Adding a build step could slow down the edit-refresh cycle for frontend development. Volume mounts currently serve raw files. Risk: medium — mitigate by keeping raw-file dev mode alongside production build.
- **QUIC/HTTP/3 in Docker** — Requires TLS (QUIC mandates encryption) and nginx compiled with HTTP/3 support (quiche or boringssl). The `nginx:stable-alpine` image may not include HTTP/3. Risk: medium — may require a custom nginx build or switching to Caddy.
- **Vendor JS total size** — Downloading all 18 CDN packages locally increases the Docker image size. Current CDN packages are ~1-2MB total. Acceptable, but worth measuring.

## Existing Codebase / Prior Art

- `frontend/nginx.conf` — Current nginx config with `no-store, no-cache` on all static assets, HTTP/1.1 proxy, no compression
- `frontend/Dockerfile` — 4 lines: `FROM nginx:stable-alpine`, copy static files, that's it
- `frontend/static/css/` — 10 CSS files totaling ~320KB unminified
- `frontend/static/js/` — 19 JS files totaling ~12K lines unminified
- `backend/app/templates/base.html` — 18 CDN `<script>`/`<link>` tags loaded on every page
- `backend/app/templates/base_embed.html` — 5 CDN scripts for embed iframes
- `docker-compose.yml` — Frontend service with volume mounts for CSS/JS hot-reload
- `backend/app/vfs/resources.py` — Has Cache-Control headers (reference for backend caching pattern)

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- No existing requirements — this introduces new capability (PERF-02 through PERF-10 to be created during planning)

## Scope

### In Scope

**Audit & Measurement:**
- Lighthouse CI setup (automated scoring for Performance, Accessibility, Best Practices, SEO)
- WebPageTest waterfall analysis for key pages (workspace, admin, auth)
- Asset size tracking (bundlesize or size-limit) with documented baseline and targets
- Before/after comparison documented with specific metrics (FCP, LCP, TTI, TBT, CLS)

**Build Pipeline:**
- Frontend build tool (esbuild or Vite) for bundling, minification, and content-hashing
- Vendor bundle for all third-party libraries (currently CDN-loaded)
- Application bundle(s) for SemPKM's own JS
- CSS minification with route-based code splitting
- Source maps for production debugging
- Build integrated into Docker build process (multi-stage Dockerfile)
- Dev mode preserving current volume-mount hot-reload workflow

**Local JS Vendoring:**
- All 18 CDN dependencies downloaded and served locally
- Version-pinned (matching current CDN versions)
- No runtime dependency on unpkg, jsdelivr, or cdnjs
- Works fully offline after initial page load

**Compression:**
- nginx gzip (and brotli if available in alpine image) for HTML, CSS, JS, JSON, SVG
- Pre-compressed static assets (`.gz`/`.br` files generated at build time) for optimal serving
- Compression level tuning (balance CPU vs size)

**HTTP Caching:**
- Content-hashed filenames for CSS and JS (`workspace.a1b2c3.min.css`)
- Long-lived `Cache-Control: public, max-age=31536000, immutable` for hashed assets
- Short-lived caching for HTML responses (`Cache-Control: no-cache` with ETag)
- Jinja2 template integration for hashed filenames (manifest file or template filter)

**CSS Code Splitting:**
- Admin pages load only admin CSS (style.css, theme.css)
- Workspace pages load workspace CSS stack (workspace.css, forms.css, views.css, etc.)
- Auth pages load minimal CSS (theme.css, auth-specific styles)
- Shared CSS (theme.css, base reset) loaded everywhere

**Backend Performance:**
- Response profiling: identify top 5 slowest endpoints with timing middleware
- HTTP cache headers on appropriate responses (ETags for SPARQL results, object pages)
- Conditional GET support (If-None-Match / If-Modified-Since → 304 Not Modified)
- Review SPARQL query patterns for obvious inefficiencies

**QUIC / HTTP/3:**
- Research: nginx HTTP/3 support status, Docker constraints, TLS requirements
- Research: benefit for self-hosted single-user tool (multiplexing, 0-RTT, head-of-line blocking)
- Implement if: nginx:alpine supports it or Caddy switch is low-cost; TLS termination is straightforward
- Document decision with rationale either way

### Out of Scope / Non-Goals

- Service worker / PWA offline support (separate milestone)
- Image optimization (no significant images in current UI)
- CDN deployment (this is self-hosted)
- SSR or pre-rendering (htmx server-renders already)
- React/Vue migration (htmx stays)
- WebSocket for real-time updates (htmx SSE is sufficient)
- Frontend framework changes of any kind
- Lazy loading of JS modules (can be follow-up after build pipeline exists)

## Technical Constraints

- Frontend: htmx + vanilla JS — no module system, scripts are IIFEs and global functions
- Build output must be static files servable by nginx (no Node.js runtime in production)
- Docker build must be reproducible (pinned tool versions)
- Dev workflow must not require running a build watcher for CSS/JS changes (volume mounts bypass build)
- Jinja2 templates rendered server-side — build tool must produce a manifest the Python backend can read
- htmx's `hx-on::` attributes and inline `<script>` blocks in templates must continue to work after minification

## Integration Points

- **nginx** — gzip/brotli config, HTTP/2 or HTTP/3, cache headers, static file serving with hashed filenames
- **Dockerfile (frontend)** — multi-stage build: install build tools → build assets → copy to nginx image
- **docker-compose.yml** — volume mounts for dev mode vs built assets for production
- **Jinja2 templates** — hashed filename resolution (manifest lookup), CSS `<link>` tags split by route
- **base.html / base_embed.html** — CDN script tags replaced with local vendor bundle references
- **FastAPI backend** — timing middleware, ETag generation, conditional GET handling
- **E2E tests** — must pass against both dev (raw files) and production (optimized) builds
- **Lighthouse CI** — runs against the Docker stack, produces JSON reports

## Open Questions

- **Build tool choice** — esbuild (fastest, simplest, Go-based) vs Vite (more features, HMR, plugin ecosystem). For a vanilla JS + htmx project with no module imports, esbuild's simplicity may be sufficient. Vite adds complexity that's more valuable for React/Vue projects. Decide during S01 research.
- **Manifest format for hashed filenames** — JSON manifest file read by a Jinja2 extension? Or a simpler approach like writing hashed filenames into a Python dict at build time? The Django `staticfiles` approach (manifest.json) is proven but requires a Jinja2 filter. Decide during implementation.
- **Pre-compressed vs on-the-fly** — Should gzip/brotli compression happen at build time (`.gz` files served by `gzip_static on`) or at request time (`gzip on`)? Pre-compressed is faster to serve but increases build artifact size. Both is ideal (pre-compressed with on-the-fly fallback). Confirm during nginx config work.
- **HTTP/2 without TLS** — HTTP/2 technically works without TLS (`h2c`) but browser support is limited and nginx's `h2c` support has caveats. For local dev (no TLS), HTTP/1.1 with gzip may be the pragmatic choice, with HTTP/2 documented for production TLS deployments. Decide during QUIC/HTTP/3 research.
