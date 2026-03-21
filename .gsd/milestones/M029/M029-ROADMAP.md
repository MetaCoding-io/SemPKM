# M029: Frontend Performance & Build Pipeline

**Vision:** Transform the frontend from 18 CDN-dependent, uncompressed, uncached raw source files into a locally-vendored, minified, compressed, properly-cached build pipeline — measurably improving page load performance (Lighthouse ≥ 85) while preserving the dev workflow (volume-mount hot-reload) and htmx compatibility.

## Success Criteria

- Lighthouse Performance score ≥ 85 on workspace page (up from estimated ~40-60), with before/after delta documented including FCP, LCP, TTI, TBT, CLS
- All 18 CDN dependencies replaced with locally served files — app functions with network disconnected after initial page load
- nginx serves gzip-compressed responses (`curl -H "Accept-Encoding: gzip" -sI` shows `Content-Encoding: gzip` for CSS/JS/HTML)
- Repeat page loads use cached assets (hashed filenames with `Cache-Control: public, max-age=31536000, immutable`)
- Admin pages do NOT load workspace.css — CSS is split by route
- Build pipeline runs automatically as part of `docker compose build` — no manual step
- All existing E2E tests pass against the optimized build
- Backend timing middleware identifies top 5 slowest endpoints with timing data
- Backend responses include appropriate cache headers (ETag, Cache-Control) on API responses
- QUIC/HTTP/3 decision documented with rationale
- Dev workflow unchanged: volume mounts serve raw files, no build watcher needed

## Key Risks / Unknowns

- **Content-hashed filenames ↔ Jinja2 template integration** — Every template referencing `/js/workspace.js` or `/css/workspace.css` must switch to manifest-based lookups. If the Jinja2 filter doesn't work correctly, all pages break. This is the highest-risk item because it touches every page render.
- **htmx + minified vendor bundle compatibility** — htmx registers globals and uses `hx-on::` attributes. If esbuild's minification renames or tree-shakes htmx internals, workspace interactions break. The `--keep-names` flag mitigates but must be proven.
- **dockview-core ESM packaging** — dockview-core may be distributed as ESM-only on npm. Wrapping it for IIFE consumption may require an esbuild shim.
- **Yasgui bundling complexity** — @zazuko/yasgui bundles CodeMirror + YASQE + YASR. Its npm package may have peer dependencies requiring separate handling. May need to stay as a lazy-loaded separate bundle.

## Proof Strategy

- **Manifest ↔ Jinja2 integration** → retire in S01 by proving: workspace loads with locally-bundled vendor JS via manifest-resolved URLs, htmx CRUD works, Cytoscape renders, dockview panels work
- **htmx minification compat** → retire in S01 by proving: create object, edit, save cycle works against minified vendor bundle with `--keep-names`
- **dockview/Yasgui packaging** → retire in S01 by proving: dockview panels render, Yasgui SPARQL console opens, both from locally-bundled JS

## Verification Classes

- Contract verification: Lighthouse JSON reports (before/after), `curl` header checks for compression/caching, asset size measurements, E2E Playwright tests
- Integration verification: Full application works with optimized assets — htmx, Cytoscape, dockview, Yasgui all functional
- Operational verification: Docker multi-stage build produces optimized assets automatically, dev volume-mount workflow unaffected
- UAT / human verification: Visual spot-check that workspace, admin, and auth pages render correctly with no missing icons, broken layouts, or invisible elements

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 5 slices are complete with verification passing
- Lighthouse before/after measurements documented with specific metric deltas
- All CDN `<script>`/`<link>` tags in base.html and base_embed.html replaced with local vendor bundle references
- nginx serves compressed, cached responses with correct headers per route type
- CSS code-splitting verified: admin pages load only admin CSS, workspace pages load workspace CSS
- Multi-stage Dockerfile produces optimized assets on `docker compose build`
- Dev workflow verified: volume mounts bypass build, edit-refresh cycle works without build step
- All existing E2E tests pass against the optimized build
- Backend timing report produced identifying top 5 slowest endpoints
- QUIC/HTTP/3 decision documented in DECISIONS.md
- Final Lighthouse score ≥ 85 confirmed

## Requirement Coverage

- Covers: PERF-02 (local vendoring), PERF-03 (build pipeline), PERF-04 (gzip compression), PERF-05 (HTTP caching), PERF-06 (CSS code-splitting), PERF-07 (Lighthouse ≥ 85), PERF-08 (backend profiling), PERF-09 (backend cache headers), PERF-10 (QUIC/HTTP/3 decision)
- Partially covers: none
- Leaves for later: Service worker/PWA offline support, image optimization, lazy loading of JS modules
- Orphan risks: none — all 9 new PERF requirements mapped to slices

## Slices

- [x] **S01: Build Pipeline & Local Vendoring** `risk:high` `depends:[]`
  > After this: Workspace loads with all JS/CSS served from locally-bundled, minified, content-hashed files. htmx CRUD, Cytoscape graph, and dockview panels all work. Dev mode still uses raw files via volume mounts. Multi-stage Dockerfile builds optimized assets.

- [x] **S02: Compression & HTTP Caching** `risk:medium` `depends:[S01]`
  > After this: nginx serves gzip-compressed responses with correct cache headers — immutable for hashed assets, no-cache with ETag for HTML. `curl` header checks confirm compression and caching. Repeat page loads are instant from browser cache.

- [x] **S03: CSS Code-Splitting & Route Optimization** `risk:low` `depends:[S01]`
  > After this: Admin pages load only admin-relevant CSS (~30KB) instead of the full workspace stack (~320KB). Auth pages load minimal CSS. Network waterfall on admin pages shows no workspace.css request.

- [x] **S04: Backend Performance & HTTP Cache Headers** `risk:low` `depends:[]`
  > After this: Timing middleware logs request durations, top-5 slowest endpoint report produced. API responses include ETag headers, conditional GET returns 304 Not Modified for unchanged resources.

- [x] **S05: Lighthouse Verification & QUIC/HTTP/3 Decision** `risk:low` `depends:[S01,S02,S03,S04]`
  > After this: Lighthouse before/after measurements documented with FCP, LCP, TTI, TBT, CLS deltas. QUIC/HTTP/3 decision documented in DECISIONS.md. All E2E tests pass against the optimized build. User guide updated if applicable.

## Boundary Map

### S01 → S02

Produces:
- `frontend/package.json` with all 18 CDN dependencies + esbuild as devDependency
- `frontend/build.js` — esbuild build script producing vendor bundle, app bundles, minified CSS, and `manifest.json`
- `frontend/Dockerfile` — multi-stage build (Node.js stage → nginx stage)
- `backend/app/template_helpers.py` — Jinja2 `asset_url` filter reading manifest.json
- Content-hashed output files in `frontend/dist/` (e.g., `vendor-a1b2c3d4.min.js`, `workspace-e5f6g7h8.min.css`)
- Updated `base.html` and `base_embed.html` using `{{ 'vendor.js' | asset_url }}` instead of CDN URLs

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- Build pipeline infrastructure (esbuild, manifest, Jinja2 filter) that S03 extends for CSS route splitting
- Pattern for per-route CSS bundles via esbuild entry points

Consumes:
- nothing (first slice)

### S01 → S05

Produces:
- Optimized assets that S05 measures with Lighthouse
- Working Docker build that S05 runs E2E tests against

### S02 → S05

Produces:
- nginx gzip config + cache headers that S05 verifies via Lighthouse and curl checks

### S03 → S05

Produces:
- Route-split CSS that S05 verifies in admin page network waterfall

### S04 (independent)

Produces:
- `backend/app/middleware/timing.py` — request timing middleware
- ETag generation on appropriate backend responses
- Conditional GET (If-None-Match → 304) support
- Top-5 slowest endpoint report

Consumes:
- nothing (independent of frontend pipeline)

### S04 → S05

Produces:
- Backend cache headers that S05 can verify contribute to Lighthouse score
