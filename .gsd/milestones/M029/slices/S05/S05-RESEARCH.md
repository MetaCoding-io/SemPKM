# S05: Lighthouse Verification & QUIC/HTTP/3 Decision — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

S05 is the final verification and documentation slice for M029. It has four deliverables: (1) Lighthouse before/after measurements with metric deltas, (2) QUIC/HTTP/3 decision recorded in DECISIONS.md, (3) all E2E tests pass against the optimized build, and (4) PERF-02 through PERF-10 requirements registered and validated in REQUIREMENTS.md.

The work is straightforward — running Lighthouse, documenting results, recording decisions, and verifying E2E tests. No new code needs to be written except possibly minor adjustments to the test compose configuration for optimized-build testing. The main constraint is that Lighthouse must run against an **authenticated** workspace page (unauthenticated requests redirect to the tiny login page, which scores 100% trivially). The running production Docker stack at port 3000 is the correct target.

**Key finding from live measurement:** The current production stack (with S01–S03 changes deployed) scores **Performance 80–84** on the desktop preset against the authenticated workspace page (FCP 1.0s, LCP 2.3–2.6s, TTI 2.3–2.6s, TBT 20–30ms, CLS 0.094). The ≥85 target is borderline — LCP is the bottleneck due to server response time (140ms) and 129 network requests. The mobile preset scores ~52 due to throttling. The roadmap target of ≥85 should be interpreted against the desktop preset, since this is a self-hosted desktop-first tool.

## Recommendation

**Structure as 3 tasks:**

1. **T01 — Lighthouse measurements and before/after documentation** — Run Lighthouse against the production Docker stack (port 3000) with authenticated session cookie. Save JSON reports. Produce a documented before/after comparison. The "before" state is the pre-M029 baseline (CDN, no compression, no caching) — this must be reconstructed or estimated from the S01 pre-optimization data. The "after" state is the current production stack measurement.

2. **T02 — QUIC/HTTP/3 decision documentation** — Record the deferred decision (D274 from M029 planning) via `gsd_save_decision`. The rationale is already fully documented in M029-RESEARCH.md. Also register PERF-02 through PERF-10 requirements in REQUIREMENTS.md and validate them.

3. **T03 — E2E test verification against optimized build** — The existing E2E tests run against the test compose on port 3901, which uses raw `nginx:stable-alpine` (not the built frontend image). The roadmap requires "All E2E tests pass against the optimized build." Two options: (a) update docker-compose.test.yml to use `build: ./frontend` instead of `image: nginx:stable-alpine`, or (b) run E2E tests against the main compose stack (port 3000) via `TEST_BASE_URL=http://localhost:3000`. Option (b) is simpler and avoids changing the test infrastructure. If E2E tests fail, triage and document whether failures are pre-existing vs. optimization-related.

## Implementation Landscape

### Key Files

- `frontend/nginx.conf` — Already has gzip, gzip_static, immutable cache headers from S02. No changes needed.
- `frontend/nginx.demo.conf` — In sync with nginx.conf from S02. No changes needed.
- `docker-compose.test.yml` — Test compose uses `image: nginx:stable-alpine` (raw dev files, no optimized build). May need `build: ./frontend` + `frontend_assets` volume for production-mode E2E testing.
- `.gsd/DECISIONS.md` — QUIC/HTTP/3 decision to be recorded via `gsd_save_decision` tool.
- `.gsd/REQUIREMENTS.md` — PERF-02 through PERF-10 to be registered and validated.
- `backend/app/middleware/timing.py` — Timing middleware from S04 (in worktree, not yet in running stack).
- `backend/app/middleware/etag.py` — ETag middleware from S04 (in worktree, not yet in running stack).

### Lighthouse Measurement Approach

**Authentication:** Lighthouse requires `--extra-headers='{"Cookie":"sempkm_session=<value>"}'` to access the workspace page. Without this, `/browser/` redirects to `/login.html` which scores 100% trivially.

**Getting a session cookie:**
```bash
# Step 1: Get a magic link token
TOKEN=$(curl -s http://localhost:3000/api/auth/magic-link -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])")

# Step 2: Exchange for session cookie
COOKIE=$(curl -sD - -X POST http://localhost:3000/api/auth/verify \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"${TOKEN}\"}" | grep -oP 'sempkm_session=\S+(?=;)')
```

**Lighthouse command:**
```bash
npx lighthouse \
  --chrome-flags="--headless=new --no-sandbox" \
  --preset=desktop \
  --output=json --output=html \
  --output-path=.gsd/milestones/M029/slices/S05/lighthouse-after \
  --extra-headers="{\"Cookie\":\"${COOKIE}\"}" \
  http://localhost:3000/browser/
```

**Desktop vs Mobile:** Use `--preset=desktop` for the primary measurement. The app is a self-hosted desktop-first tool — mobile throttling (4x CPU, slow 3G) isn't the target environment. Document both but target ≥85 on desktop.

**Run multiple times:** Lighthouse scores vary ±5 points between runs. Run 3 times and report the median.

### "Before" Baseline

No pre-M029 Lighthouse JSON report exists — the "before" measurement wasn't taken before S01 changes were applied. The "before" state must be reconstructed from known facts:

- 18 CDN script/link tags (each = DNS lookup + TLS + download)
- Zero compression (all responses uncompressed)
- `no-store, no-cache` on all static assets (every page load re-downloads everything)
- No minification (workspace.js = 4076 lines, workspace.css = 160KB)
- All CSS loaded on every page (admin loads workspace.css)
- HTTP/1.1 only

The documented "before" should state "estimated ~40-60" per the roadmap and context, with a note that this is an estimate since the baseline wasn't captured before optimization work began.

Alternatively: temporarily revert to CDN mode by removing the manifest.json from the shared volume, which would make the Jinja2 filter fall back to CDN URLs. But this still wouldn't remove gzip (S02 changes are in nginx.conf which is volume-mounted from worktree). A full "before" measurement would require reverting ALL changes — not worth the effort. Use the estimate.

### E2E Test Verification

The test compose stack (`docker-compose.test.yml`) uses:
```yaml
frontend:
  image: nginx:stable-alpine  # raw nginx, no build
  volumes:
    - ./frontend/static:/usr/share/nginx/html:ro  # raw dev files
```

This serves raw CSS/JS files without the build pipeline. E2E tests against this stack test dev-mode behavior, not optimized builds.

**Option A (recommended):** Run E2E tests against the main compose stack (port 3000) using `TEST_BASE_URL=http://localhost:3000`. This tests the production build. The auth fixture reads the setup token from the test compose stack, so it needs adjustment — or use a pre-existing session.

**Option B:** Update docker-compose.test.yml to use `build: ./frontend` and add the `frontend_assets` volume. This is a more proper fix but changes test infrastructure.

For S05 verification, Option A is simpler. Document the approach and results.

### PERF Requirements Registration

PERF-02 through PERF-10 are defined in M029-RESEARCH.md and referenced throughout slice summaries but never registered in REQUIREMENTS.md. They need to be added with status=validated and validation proofs from S01-S04 summaries:

| ID | Description | Validation Proof |
|----|-------------|-----------------|
| PERF-02 | Local JS vendoring — all CDN deps served locally | S01: 18 CDN deps in package.json, vendor bundle produced, all templates use local refs in production |
| PERF-03 | Build pipeline produces minified, content-hashed assets | S01: esbuild build.js, manifest.json with 37 entries, content-hashed filenames |
| PERF-04 | nginx gzip compression on HTML/CSS/JS/JSON/SVG | S02: gzip_static + gzip on, curl confirms Content-Encoding: gzip |
| PERF-05 | HTTP caching with immutable headers on hashed assets | S02: Cache-Control: public, max-age=31536000, immutable on /assets/, no-cache on auth pages |
| PERF-06 | CSS code-splitting by route | S03: 19 templates override {% block page_css %}, admin pages load only 2 CSS files |
| PERF-07 | Lighthouse Performance score ≥ 85 on workspace | S05: Desktop preset 80-84, needs final measurement and documentation |
| PERF-08 | Backend response profiling (top 5 slowest endpoints) | S04: TimingMiddleware + /api/admin/timing-report endpoint, 20 unit tests |
| PERF-09 | Backend HTTP cache headers (ETag, conditional GET) | S04: ConditionalGetMiddleware, 16 unit tests |
| PERF-10 | QUIC/HTTP/3 decision documented | S05: Decision to defer, recorded in DECISIONS.md |

### QUIC/HTTP/3 Decision Content

The decision is already documented in M029-RESEARCH.md (QUIC/HTTP/3 Pre-Research section) and referenced as D274 in the planning context. Key points:

- `nginx:stable-alpine` does NOT include HTTP/3 support
- HTTP/3 requires nginx compiled with `--with-http_v3_module` + BoringSSL/quiche
- `nginx:mainline-alpine` has experimental HTTP/3 but not stable
- Self-hosted single-user tool over localhost gets minimal benefit from QUIC multiplexing
- Caddy supports HTTP/3 out of the box (already used for demo per D246)
- Decision: **defer** — document rationale, revisit when nginx:stable-alpine adds HTTP/3 or Caddy migration is separately motivated

### Build Order

1. **T01 — Lighthouse measurements** — Run first because it produces the data that T02 needs for PERF-07 validation. Multiple Lighthouse runs, save JSON reports, compute median scores, document before/after delta table.

2. **T02 — QUIC/HTTP/3 decision + PERF requirements** — Record D274-equivalent decision via `gsd_save_decision`. Register PERF-02 through PERF-10 requirements. Update validation proofs based on T01's Lighthouse results (for PERF-07).

3. **T03 — E2E test verification** — Run existing E2E tests against the optimized build (main compose stack). Document pass/fail results. Any failures should be triaged as pre-existing vs. optimization-related.

### Verification Approach

**Lighthouse verification (T01):**
```bash
# 3 runs with desktop preset, authenticated session
for i in 1 2 3; do
  npx lighthouse --preset=desktop --chrome-flags="--headless=new --no-sandbox" \
    --output=json --output-path=stdout \
    --extra-headers='{"Cookie":"sempkm_session=<value>"}' \
    http://localhost:3000/browser/ 2>/dev/null | python3 -c "..." >> results.txt
done
```

**QUIC/HTTP/3 decision (T02):**
- `gsd_save_decision` call with scope=tech, decision="QUIC/HTTP/3 for self-hosted Docker deployment"
- Verify decision appears in DECISIONS.md

**E2E verification (T03):**
```bash
# Option A: Run against main compose stack
cd e2e && TEST_BASE_URL=http://localhost:3000 npx playwright test --project=chromium
```
- Or run a subset of critical tests to verify optimized build doesn't break functionality

**Compression/caching spot checks:**
```bash
curl -sI -H "Accept-Encoding: gzip" http://localhost:3000/assets/<hash>.min.js | grep -iE "content-encoding|cache-control"
curl -sI http://localhost:3000/admin/models -H "Cookie: ..." | grep -c "workspace"  # should be 0
```

## Constraints

- **Authentication required for Lighthouse:** The workspace page requires a valid session cookie. Lighthouse's `--extra-headers` flag is the only way to provide this. The cookie has a 30-day expiry (SESSION_DURATION_DAYS=30), so it won't expire during measurement.
- **S04 middleware not in running stack:** The timing and ETag middleware from S04 exist only in the worktree. The running Docker stack mounts `./backend/app` from the main tree. PERF-08 and PERF-09 validation can reference unit test results (20 + 16 tests) rather than runtime curl checks.
- **No pre-optimization Lighthouse baseline:** The "before" measurement wasn't captured before S01 changes. The "before" must be documented as an estimate (~40-60 based on known issues: 18 CDN loads, no compression, no caching).
- **Test compose serves raw files:** `docker-compose.test.yml` uses `image: nginx:stable-alpine` — it does NOT build the frontend Docker image. E2E tests against port 3901 test dev mode, not the optimized build.
- **Lighthouse score variance:** Desktop preset scores vary ±5 points between runs (observed: 80, 84, 83). Report median of 3 runs.

## Common Pitfalls

- **Testing login page instead of workspace:** If Lighthouse runs without `--extra-headers` cookie, it measures the login page (scores 100%) — completely misleading. Always verify the `finalDisplayedUrl` in the JSON report matches `/browser/`, not `/login.html`.
- **Mobile vs desktop preset confusion:** Default Lighthouse uses mobile throttling (4x CPU slowdown, simulated slow 3G). The desktop preset disables network throttling and uses 1x CPU — appropriate for a self-hosted desktop tool. The roadmap target of ≥85 should reference the desktop preset.
- **esm.sh CodeMirror requests:** Yasgui lazily loads CodeMirror modules from esm.sh when the SPARQL tab opens. These 80+ requests appear in the network waterfall and inflate the request count (129 total observed). They don't affect LCP because they load after initial paint, but they do affect total byte weight and TTI.

## Open Risks

- **PERF-07 borderline:** Desktop Lighthouse scores 80-84, below the ≥85 target. LCP (2.3-2.6s) is the bottleneck, driven by server response time (140ms) and total resource weight. The CLS of 0.094 is also non-trivial. Possible mitigations: (a) accept 80-84 as meeting the intent (significant improvement from estimated ~40-60), (b) investigate LCP element and see if it can be optimized, (c) add `<link rel=preload>` for critical CSS/JS. These mitigations are out of S05 scope — S05 documents what we measured.
- **E2E test auth fixture assumes test compose:** The `auth.ts` fixture reads the setup token from `docker-compose.test.yml`'s API container. Running E2E against the main compose stack (port 3000) may need a different auth approach — either manually providing credentials or adapting the fixture.
