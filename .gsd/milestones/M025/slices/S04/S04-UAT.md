# S04: Cloud deployment config + E2E + docs — UAT

**Milestone:** M025
**Written:** 2026-03-20

## UAT Type

- UAT mode: mixed (artifact-driven for docs/config files, live-runtime for E2E and deployment)
- Why this mode is sufficient: Deployment configs and docs can be verified by inspection; the E2E test requires a live demo stack to exercise the full anonymous→tour→dashboard→CTA flow

## Preconditions

1. Demo Docker stack running: `docker compose -f docker-compose.demo.yml up -d --build` from the repo root
2. Seed data loaded: `docker compose -f docker-compose.demo.yml exec api python /app/scripts/seed-demo-data.py`
3. Stack healthy: `curl -sf http://localhost:3902/api/health` returns 200
4. Playwright installed: `cd e2e && npm install`

## Smoke Test

Open `http://localhost:3902/browser/` in an incognito/private browser window. You should see the workspace immediately — no login page, no setup wizard. The explorer sidebar should show objects.

## Test Cases

### 1. Caddyfile validity and content

1. Open `Caddyfile` at the repository root
2. Verify it contains `demo.sempkm.app` as the domain placeholder
3. Verify it contains `reverse_proxy localhost:3902`
4. Verify it contains `X-Robots-Tag "noindex, nofollow"` header
5. **Expected:** All three directives present; Caddy would accept this config with `caddy validate --config Caddyfile` (requires Caddy installed)

### 2. Reset script syntax and structure

1. Run `bash -n scripts/reset-demo.sh` — must exit 0
2. Run `grep -q "set -euo pipefail" scripts/reset-demo.sh` — must exit 0
3. Read the script — verify 5 phases are labeled `[1/5]` through `[5/5]`
4. Verify the health wait loop has a timeout (should be ~120s)
5. Verify the script calls `seed-demo-data.py` and uses `--verify-only` for the final check
6. **Expected:** Valid bash, strict error handling, 5 clearly labeled phases, timeout prevents infinite loop

### 3. Deploy script DNS/SSL documentation

1. Run `grep -c "caddy\|Caddy\|SSL\|HTTPS" scripts/deploy-demo.sh` — should be ≥3
2. Read the script — verify DNS/SSL setup section with Caddy install instructions
3. Verify cron section referencing `reset-demo.sh` with a sample crontab line
4. Verify health check monitoring section mentioning `/api/health`
5. **Expected:** Deploy script documents all three operational concerns (SSL, cron reset, monitoring)

### 4. E2E test — anonymous access with sample data (DEMO-03)

1. Run `cd e2e && npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo --grep "anonymous"` against live demo stack
2. **Expected:** Test navigates to `/browser/`, receives HTTP 200 (no redirect), workspace container is visible, explorer sidebar has at least one item proving seed data loaded

### 5. E2E test — tour completion (DEMO-04)

1. Run `cd e2e && npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo --grep "tour"` against live demo stack
2. **Expected:** Test triggers `window.startDemoTour()`, clicks through Next/Done buttons, and `localStorage.getItem('sempkm_demo_tour_done')` returns `'true'`

### 6. E2E test — CTA banner visibility (DEMO-06)

1. Run `cd e2e && npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo --grep "CTA"` against live demo stack
2. **Expected:** `#demo-cta-banner` is visible, contains "SemPKM" text, and has a "Get Started" link pointing to the GitHub repository

### 7. E2E test — dashboard rendering (DEMO-05)

1. Run `cd e2e && npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo --grep "dashboard"` against live demo stack
2. **Expected:** Opens the demo dashboard (UUID `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee`) via `openDashboardTab()`, dashboard container or iframe appears with content

### 8. E2E test — no JS errors

1. Run the full test suite: `cd e2e && npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo`
2. **Expected:** All 5 tests pass. The final test confirms zero unhandled JS exceptions (excluding ResizeObserver noise) across the entire flow.

### 9. Chapter 38 content and navigation chain

1. Open `docs/guide/38-hosted-demo.md` — verify it covers: DEMO_MODE, docker-compose.demo.yml, seed script, Caddy SSL, periodic reset, CTA customization, health monitoring, troubleshooting
2. Verify footer: `**Previous:** Chapter 37` and `**Next:** Appendix A`
3. Open `docs/guide/37-monday-sync.md` — verify footer now points to Chapter 38 (not Appendix A)
4. **Expected:** Navigation chain Ch 37 → Ch 38 → Appendix A is complete in both directions

### 10. Three-file navigation sync

1. Run `grep "38.*Hosted Demo" docs/guide/README.md` — TOC entry present
2. Run `grep "38-hosted-demo" docs/guide/index.html` — sidebar entry present
3. Run `grep "38-hosted-demo" backend/app/templates/guide.html` — button entry present
4. **Expected:** All three navigation files have Ch 38 entries

### 11. DEMO_MODE in Appendix A

1. Run `grep "DEMO_MODE" docs/guide/appendix-a-environment-variables.md`
2. **Expected:** Row in the environment variable table describing DEMO_MODE with default `false`

### 12. Glossary entries

1. Run `grep -i "demo mode" docs/guide/appendix-d-glossary.md` — entry exists
2. Run `grep -i "hosted demo" docs/guide/appendix-d-glossary.md` — entry exists
3. Both entries should reference Chapter 38
4. **Expected:** Both glossary entries present in alphabetical order with cross-references

## Edge Cases

### Reset script failure mid-execution

1. Start the demo stack, then manually stop the API container (`docker compose -f docker-compose.demo.yml stop api`)
2. Run `scripts/reset-demo.sh`
3. **Expected:** Script runs `down -v` (cleans up), `up -d --build` (restarts all), then health wait succeeds because `up` recreates the container. If health check fails within 120s, script exits non-zero with an explicit timeout error message.

### Tour on already-toured session

1. Complete the demo tour once (localStorage `sempkm_demo_tour_done` = `'true'`)
2. Refresh the page
3. **Expected:** Tour does not auto-start again. CTA banner remains visible because it reads `sempkm_demo_tour_done` from localStorage.

### Reset restores clean state

1. Open the demo instance, trigger the tour, verify CTA banner is shown
2. Run `scripts/reset-demo.sh` (this destroys and rebuilds the entire stack)
3. Open the demo instance in a fresh incognito window
4. **Expected:** Tour is available again (localStorage is per-browser, not server-side). Seed data is fresh — all 74+ objects visible in explorer.

## Failure Signals

- `bash -n scripts/reset-demo.sh` exits non-zero → invalid bash syntax
- `curl -sf http://localhost:3902/api/health` returns non-200 → demo stack is unhealthy
- E2E tests fail with "Timeout" on workspace load → DEMO_MODE auth bypass not working
- E2E tests fail with "element not visible" for CTA banner → tour didn't complete or CTA CSS is broken
- `grep "38" docs/guide/README.md` returns empty → TOC entry missing
- Navigation chain broken → Ch 37 footer still points to Appendix A instead of Ch 38

## Requirements Proved By This UAT

- DEMO-07 — Docker Compose with SSL termination via Caddyfile (test cases 1, 3)
- DEMO-08 — Periodic reset mechanism via reset-demo.sh and cron (test cases 2, 3, edge case 1)
- DEMO-09 — Uptime monitoring via health check endpoint (test case 3)
- DEMO-10 — User guide documents deployment and configuration (test cases 9, 10, 11, 12)
- DEMO-03 — Sample data visible in browser (test case 4, validated via E2E)
- DEMO-04 — Tour completes without errors (test case 5, validated via E2E)
- DEMO-05 — Dashboard renders with data (test case 7, validated via E2E)
- DEMO-06 — CTA banner visible after tour (test case 6, validated via E2E)

## Not Proven By This UAT

- **Live SSL certificate issuance** — Caddyfile is verified by inspection, but actual Let's Encrypt certificate issuance requires a public DNS-resolvable domain
- **Cron execution** — reset-demo.sh is verified syntactically, but actual cron scheduling requires a deployed server with crontab configured
- **Multi-visitor concurrency** — the E2E test proves a single visitor flow; concurrent visitor isolation depends on the read-only nginx enforcement (validated in S01)
- **Uptime monitoring integration** — health endpoint documented but no specific monitoring service (e.g., UptimeRobot) configured

## Notes for Tester

- The E2E tests require the demo Docker stack running on `localhost:3902`. Start it with `docker compose -f docker-compose.demo.yml up -d --build` then seed with `docker compose -f docker-compose.demo.yml exec api python /app/scripts/seed-demo-data.py`.
- All serial tests share a single browser page context — they must run in order. Use `npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo` (not `--workers=4`).
- The tour click-through takes several seconds per step. The test uses generous timeouts (60s for tour completion).
- The Caddyfile uses `demo.sempkm.app` as a placeholder — change it to your actual domain before deploying.
- The `X-Robots-Tag: noindex, nofollow` header prevents search engine indexing of the demo instance.
