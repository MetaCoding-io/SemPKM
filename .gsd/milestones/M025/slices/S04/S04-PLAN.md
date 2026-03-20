# S04: Cloud deployment config + E2E + docs

**Goal:** Wire S01-S03 outputs into a deployable demo configuration with Caddy SSL termination, periodic reset, E2E proof of the full demo flow, and user guide documentation.
**Demo:** docker-compose.demo.yml with Caddy reverse proxy deploys the full demo stack; E2E Playwright test proves anonymous access → tour completion → CTA banner → dashboard rendering; Chapter 38 user guide documents deployment and configuration.

## Must-Haves

- `Caddyfile` with automatic HTTPS reverse proxy to Docker's nginx on port 3902
- `scripts/reset-demo.sh` that tears down, rebuilds, and re-seeds the demo stack
- `deploy-demo.sh` updated with DNS/SSL setup instructions and cron section
- `e2e/tests/50-demo/demo-full-flow.spec.ts` E2E test exercising full demo flow (anonymous → tour → dashboard → CTA)
- `docs/guide/38-hosted-demo.md` Chapter 38 documenting demo deployment
- All three navigation files updated: `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`
- `DEMO_MODE` added to `docs/guide/appendix-a-environment-variables.md`
- Glossary entries for "Demo Mode" and "Hosted Demo" in `appendix-d-glossary.md`
- Navigation chain: Ch 37 → Ch 38 → Appendix A

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (E2E test runs against live Docker demo stack)
- Human/UAT required: no

## Verification

- `bash -n scripts/reset-demo.sh` — valid bash syntax
- `bash -n scripts/deploy-demo.sh` — valid after updates
- `cat Caddyfile` — valid Caddy config with domain placeholder, reverse_proxy, tls
- `npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo` — all tests pass against live demo stack
- `grep "38" docs/guide/README.md` — chapter entry present
- `grep "38" docs/guide/index.html` — sidebar entry present
- `grep "38" backend/app/templates/guide.html` — button entry present
- `grep "DEMO_MODE" docs/guide/appendix-a-environment-variables.md` — env var documented
- `grep -i "demo mode" docs/guide/appendix-d-glossary.md` — glossary entry present
- Navigation chain: Ch 37 bottom links to Ch 38, Ch 38 bottom links to Appendix A
- `grep -q "set -euo pipefail" scripts/reset-demo.sh` — reset script has strict error handling for failure visibility

## Observability / Diagnostics

- **Health check endpoint:** `curl -sf http://localhost:3902/api/health` — returns JSON health status; used by reset script, deploy script, and uptime monitoring
- **Reset script logging:** `reset-demo.sh` outputs timestamped step messages to stdout; cron redirects to `/var/log/sempkm-demo-reset.log` for post-mortem inspection
- **Caddy access logs:** Caddy logs to systemd journal by default (`journalctl -u caddy`); shows HTTPS certificate status, request routing, and proxy errors
- **Docker container health:** `docker compose -f docker-compose.demo.yml ps` shows container status and health check results
- **Failure visibility:** Reset script uses `set -euo pipefail` — any step failure stops execution with a non-zero exit code; cron logs capture the failure point
- **Seed verification:** `--verify-only` flag on seed script confirms demo data integrity without mutation

## Integration Closure

- Upstream surfaces consumed: `docker-compose.demo.yml` (S01), `scripts/seed-demo-data.py` (S02), `scripts/deploy-demo.sh` (S02), `frontend/static/js/tutorials.js` `startDemoTour()` (S03), `frontend/static/css/workspace.css` `.demo-cta-banner` (S03), `backend/app/config.py` `demo_mode` (S01)
- New wiring introduced in this slice: Caddyfile reverse proxy, reset-demo.sh cron integration, E2E test composition
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Caddy reverse proxy config, reset script, and deploy script update** `est:25m`
  - Why: Provides SSL termination config and periodic reset mechanism — covers DEMO-07 (Docker Compose with SSL), DEMO-08 (periodic reset), and DEMO-09 (uptime monitoring via health check)
  - Files: `Caddyfile`, `scripts/reset-demo.sh`, `scripts/deploy-demo.sh`
  - Do: Create Caddyfile with domain placeholder (`demo.sempkm.app`) and `reverse_proxy localhost:3902`. Create `scripts/reset-demo.sh` that runs down -v → up -d --build → health wait → re-seed. Update `deploy-demo.sh` with DNS/SSL setup instruction comments and a cron section showing the reset mechanism (e.g., `0 */6 * * * /path/to/reset-demo.sh`).
  - Verify: `bash -n scripts/reset-demo.sh && bash -n scripts/deploy-demo.sh` — both valid bash. `cat Caddyfile` — has domain, reverse_proxy, tls directives.
  - Done when: All three files exist with valid syntax and the deploy script includes cron documentation

- [x] **T02: E2E Playwright test for full demo flow** `est:40m`
  - Why: Proves DEMO-03 (browser visibility), DEMO-04 (tour completes), DEMO-05 (dashboard renders), DEMO-06 (CTA banner visible) end-to-end against the live Docker demo stack. This is the milestone's primary verification artifact.
  - Files: `e2e/tests/50-demo/demo-full-flow.spec.ts`
  - Do: Create a serial Playwright test in the existing `demo` project that: (1) navigates to `/browser/`, verifies workspace loads; (2) triggers tour via `page.evaluate('window.startDemoTour()')`, waits for localStorage `sempkm_demo_tour_done` to be set via `page.waitForFunction`; (3) verifies CTA banner element is visible; (4) opens the demo dashboard via `page.evaluate` calling `openDashboardTab('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', 'Demo Dashboard')`, verifies the dashboard tab content renders. Follow the S04-RESEARCH pitfalls: don't step through tour steps individually, verify the outcome via localStorage; wait for localStorage before checking CTA; use generous timeouts for tour completion (~60s).
  - Verify: `npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo` — all tests pass
  - Done when: E2E test passes against the live demo Docker stack proving anonymous access, tour completion, CTA visibility, and dashboard rendering

- [x] **T03: User guide Chapter 38 and documentation updates** `est:30m`
  - Why: Covers the documentation requirement — documents DEMO_MODE, docker-compose.demo.yml, seed script, Caddy SSL, periodic reset, and CTA customization. Updates all three navigation files per KNOWLEDGE.md rule.
  - Files: `docs/guide/38-hosted-demo.md`, `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`, `docs/guide/appendix-a-environment-variables.md`, `docs/guide/appendix-d-glossary.md`, `docs/guide/37-monday-sync.md`
  - Do: Write Chapter 38 covering: overview, DEMO_MODE env var, docker-compose.demo.yml usage, seed script, Caddy SSL termination, periodic reset via cron, CTA banner customization, health check monitoring. Update navigation chain: change Ch 37's "Next" from Appendix A to Ch 38, add Ch 38 with "Next" pointing to Appendix A. Add Ch 38 entry to README.md TOC, index.html sidebar, and guide.html in-app page. Add `DEMO_MODE` row to appendix-a table. Add "Demo Mode" and "Hosted Demo" entries to appendix-d glossary.
  - Verify: All three nav files have Ch 38 entries. `grep "DEMO_MODE" appendix-a-environment-variables.md` finds the entry. `grep -i "demo mode" appendix-d-glossary.md` finds the entry. Ch 37 → Ch 38 → Appendix A navigation chain verified.
  - Done when: Chapter 38 exists, all navigation files updated, appendix and glossary entries added, navigation chain Ch 37 → Ch 38 → Appendix A complete

## Files Likely Touched

- `Caddyfile` (new)
- `scripts/reset-demo.sh` (new)
- `scripts/deploy-demo.sh` (modified)
- `e2e/tests/50-demo/demo-full-flow.spec.ts` (new)
- `docs/guide/38-hosted-demo.md` (new)
- `docs/guide/README.md` (modified)
- `docs/guide/index.html` (modified)
- `backend/app/templates/guide.html` (modified)
- `docs/guide/appendix-a-environment-variables.md` (modified)
- `docs/guide/appendix-d-glossary.md` (modified)
- `docs/guide/37-monday-sync.md` (modified — navigation chain)
