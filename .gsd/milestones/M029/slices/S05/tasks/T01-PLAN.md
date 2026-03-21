---
estimated_steps: 7
estimated_files: 3
---

# T01: Run Lighthouse measurements and document before/after deltas

**Slice:** S05 — Lighthouse Verification & QUIC/HTTP/3 Decision
**Milestone:** M029

## Description

Run Lighthouse against the authenticated workspace page on the running Docker stack (port 3000) to measure the current post-optimization Performance score. Run 3 times with the desktop preset to get a reliable median. Also run curl-based spot checks for compression, caching, and CSS code-splitting. Document everything in a results file with a before/after delta table.

The "before" baseline is an estimate (~40-60) since no Lighthouse JSON report was captured before S01 changes. The estimate is based on known pre-M029 conditions: 18 CDN script/link tags (each requiring DNS+TLS+download), zero compression, `no-store, no-cache` on all assets, no minification (workspace.js ~4076 lines, workspace.css ~160KB), all CSS loaded on every page, HTTP/1.1 only.

**Authentication is critical:** Without a valid session cookie in `--extra-headers`, Lighthouse measures the login page (which scores ~100% trivially) instead of the workspace. Always verify `finalDisplayedUrl` in the JSON report matches `/browser/`, not `/login.html`.

**Desktop preset:** Use `--preset=desktop`. This app is a self-hosted desktop-first tool. Mobile throttling (4x CPU, simulated slow 3G) isn't the target environment. The roadmap target of ≥85 is against the desktop preset.

## Steps

1. **Install Lighthouse** — `npx lighthouse --version` to verify it's available, or install via `npm install -g lighthouse` if needed. Lighthouse must be run from a location with Chrome/Chromium accessible.

2. **Get auth session cookie** from the running Docker stack at port 3000:
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

3. **Run Lighthouse 3 times** with the desktop preset and save results:
   ```bash
   for i in 1 2 3; do
     npx lighthouse \
       --chrome-flags="--headless=new --no-sandbox" \
       --preset=desktop \
       --output=json \
       --output-path=stdout \
       --extra-headers="{\"Cookie\":\"${COOKIE}\"}" \
       http://localhost:3000/browser/ 2>/dev/null | \
       python3 -c "
   import json,sys
   d = json.load(sys.stdin)
   c = d['categories']['performance']
   a = d['audits']
   print(f'Run {int(sys.argv[1])}: score={c[\"score\"]:.2f}', end=' ')
   for m in ['first-contentful-paint','largest-contentful-paint','interactive','total-blocking-time','cumulative-layout-shift']:
       print(f'{m}={a[m][\"numericValue\"]:.0f}', end=' ')
   print()
   " $i
   done
   ```

4. **Save the best/median run** as JSON and HTML reports:
   ```bash
   npx lighthouse \
     --chrome-flags="--headless=new --no-sandbox" \
     --preset=desktop \
     --output=json --output=html \
     --output-path=.gsd/milestones/M029/slices/S05/lighthouse-after \
     --extra-headers="{\"Cookie\":\"${COOKIE}\"}" \
     http://localhost:3000/browser/
   ```

5. **Verify finalDisplayedUrl** in the JSON report is `/browser/`, not `/login.html`:
   ```bash
   python3 -c "import json; d=json.load(open('.gsd/milestones/M029/slices/S05/lighthouse-after.report.json')); print('URL:', d['finalDisplayedUrl'])"
   ```

6. **Run curl spot checks** to complement Lighthouse:
   ```bash
   # Compression on hashed assets
   curl -sI -H "Accept-Encoding: gzip" http://localhost:3000/assets/ 2>/dev/null  # list is fine, pick one asset from manifest
   # Get a real asset name from manifest
   ASSET=$(curl -s http://localhost:3000/browser/ | grep -oP '/assets/[a-z]+-[a-f0-9]+\.min\.(js|css)' | head -1)
   curl -sI -H "Accept-Encoding: gzip" "http://localhost:3000${ASSET}" | grep -iE "content-encoding|cache-control"
   
   # CSS code-splitting: admin page has no workspace CSS
   curl -s http://localhost:3000/admin/models -H "Cookie: ${COOKIE}" | grep -c 'workspace'
   
   # ETag on API responses (S04 middleware — only if middleware is in running stack)
   curl -sI http://localhost:3000/api/health | grep -iE 'server-timing|etag'
   ```

7. **Write results markdown** at `.gsd/milestones/M029/slices/S05/lighthouse-results.md` with:
   - Table of 3 run scores
   - Median/best scores for Performance, FCP, LCP, TTI, TBT, CLS
   - Before/after delta table (before = estimate ~40-60, after = measured)
   - Note that "before" is an estimate since no pre-M029 baseline was captured
   - Spot check results for compression, caching, CSS splitting
   - Note about S04 middleware (timing + ETag) — exists in worktree only, validated by 36 unit tests, not in running stack

## Must-Haves

- [ ] Lighthouse run against authenticated workspace page (not login page) — `finalDisplayedUrl` confirms `/browser/`
- [ ] Desktop preset used (not default mobile throttling)
- [ ] At least 3 runs to account for ±5 point variance
- [ ] JSON report saved at `.gsd/milestones/M029/slices/S05/lighthouse-after.report.json`
- [ ] Before/after delta table with FCP, LCP, TTI, TBT, CLS documented
- [ ] Spot checks for compression and caching documented

## Verification

- `test -f .gsd/milestones/M029/slices/S05/lighthouse-after.report.json && echo "JSON report exists"`
- `python3 -c "import json; d=json.load(open('.gsd/milestones/M029/slices/S05/lighthouse-after.report.json')); assert '/browser' in d['finalDisplayedUrl'], 'Wrong page!'; print('Score:', d['categories']['performance']['score'])"`
- `test -f .gsd/milestones/M029/slices/S05/lighthouse-results.md && echo "Results doc exists"`

## Observability Impact

- **New artifact: Lighthouse JSON report** — `lighthouse-after.report.json` provides machine-readable performance data. Future agents can parse `categories.performance.score` and all audit metrics to compare against targets.
- **New artifact: Lighthouse HTML report** — `lighthouse-after.report.html` provides visual audit breakdown for human inspection.
- **New artifact: Results markdown** — `lighthouse-results.md` documents before/after deltas, spot check results, and provides the evidence table that PERF-07 requires.
- **Auth verification signal** — `finalDisplayedUrl` in the JSON report confirms whether the authenticated workspace was measured. If this shows `/login.html`, all scores are invalid.
- **Spot check headers** — curl output for `Content-Encoding`, `Cache-Control`, `Server-Timing`, `ETag` provides direct infrastructure verification independent of Lighthouse scoring.
- **Failure inspection** — if Lighthouse scores are unexpectedly low, check: (1) `finalDisplayedUrl` for auth failure, (2) `audits.diagnostics` in JSON for specific bottlenecks, (3) `audits.network-requests` for asset loading issues.

## Inputs

- Running Docker stack at `http://localhost:3000` with S01 (optimized assets), S02 (gzip + caching), and S03 (CSS splitting) applied
- S01 summary: 37 manifest entries, vendor bundle replaces 17 CDN scripts, content-hashed filenames
- S02 summary: gzip_static on, immutable cache headers on /assets/, no-cache on auth pages
- S03 summary: 19 templates override page_css block, admin pages load 0 workspace CSS files
- S04 summary: TimingMiddleware + ConditionalGetMiddleware exist in worktree only (20 + 16 unit tests), NOT in running Docker stack

## Expected Output

- `.gsd/milestones/M029/slices/S05/lighthouse-after.report.json` — Full Lighthouse JSON report
- `.gsd/milestones/M029/slices/S05/lighthouse-after.report.html` — Lighthouse HTML report for visual inspection
- `.gsd/milestones/M029/slices/S05/lighthouse-results.md` — Before/after delta table, 3-run scores, spot check results
