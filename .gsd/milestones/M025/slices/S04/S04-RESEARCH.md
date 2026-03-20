# S04: Cloud deployment config + E2E + docs — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

S04 is the final assembly slice — no new features, just wiring existing outputs (S01 auth bypass, S02 seed data, S03 tour/dashboard/CTA) into a deployable configuration with verification and documentation. The work divides into three independent units: (1) Caddy reverse proxy config for SSL termination + periodic reset cron, (2) an E2E Playwright test exercising the full demo flow, and (3) a user guide chapter (Chapter 38) with supporting file updates.

All patterns are established: `docker-compose.demo.yml` exists, the `demo` Playwright project is configured, the user guide chapter pattern is repeated across 15+ chapters, and the three-file guide update rule is documented in KNOWLEDGE.md.

## Recommendation

Three parallel tasks, all low-risk:

1. **Caddy + deployment config** — Add a `Caddyfile` and update `deploy-demo.sh` with DNS/SSL instructions and a cron-based reset mechanism. This is pure configuration — no code changes.
2. **E2E Playwright test** — A single `demo-full-flow.spec.ts` test file exercising anonymous access → tour start → tour completion → CTA banner visibility → dashboard renders. Reuses the existing `demo` project in `playwright.config.ts`.
3. **User guide + docs updates** — Write `docs/guide/38-hosted-demo.md`, update all three navigation files (README.md, index.html, guide.html), add `DEMO_MODE` to appendix-a, add glossary entries.

## Implementation Landscape

### Key Files

- `Caddyfile` (new) — Caddy reverse proxy config for automatic HTTPS. ~10 lines: domain placeholder, `reverse_proxy localhost:3902`, TLS auto. Per D246, Caddy runs on the host and proxies to Docker's nginx.
- `scripts/deploy-demo.sh` (existing) — Currently handles start → health → seed → verify. Needs DNS/SSL setup instructions as comments, and a cron section showing the reset mechanism.
- `scripts/reset-demo.sh` (new) — Simple script: `docker compose -f docker-compose.demo.yml down -v && docker compose -f docker-compose.demo.yml up -d --build`, then wait for health, then re-seed. Called by cron.
- `e2e/tests/50-demo/demo-full-flow.spec.ts` (new) — E2E test: navigate to `/browser/`, verify workspace loads (reuses S01 pattern), trigger tour via `window.startDemoTour()`, verify localStorage `sempkm_demo_tour_done` is set, verify CTA banner element exists, navigate to dashboard tab and verify it renders. This extends the existing `demo-read-only.spec.ts` which already proves anonymous access.
- `docs/guide/38-hosted-demo.md` (new) — Chapter 38 documenting: DEMO_MODE env var, docker-compose.demo.yml, seed script usage, Caddy SSL, periodic reset, CTA customization.
- `docs/guide/README.md` — Add Chapter 38 entry after Chapter 37.
- `docs/guide/index.html` — Add sidebar `<li>` for Chapter 38 after Monday.com entry.
- `backend/app/templates/guide.html` — Add `<button>` for Chapter 38 after Monday.com entry.
- `docs/guide/appendix-a-environment-variables.md` — Add `DEMO_MODE` row to the main table.
- `docs/guide/appendix-d-glossary.md` — Add entries for "Demo Mode", "Hosted Demo".

### Build Order

1. **Caddy + reset script** — Pure config files, no dependencies on other tasks. Creates `Caddyfile`, `scripts/reset-demo.sh`, updates `deploy-demo.sh` comments.
2. **E2E test** — Independent of task 1. Creates `demo-full-flow.spec.ts` in the existing `50-demo/` directory. Must run against a live demo stack but doesn't depend on Caddy (tests use direct HTTP on port 3902).
3. **Docs** — Independent of tasks 1-2. Creates Chapter 38, updates 5 navigation/reference files.

All three tasks can execute in parallel — no data dependencies between them.

### Verification Approach

**Task 1 (Caddy + deploy):**
- `cat Caddyfile` — valid Caddy syntax (domain, reverse_proxy, tls)
- `bash -n scripts/reset-demo.sh` — valid bash syntax
- `bash -n scripts/deploy-demo.sh` — still valid after updates

**Task 2 (E2E test):**
- `npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo` against live demo stack
- Test must pass: anonymous access, tour trigger, localStorage flag set, CTA banner present

**Task 3 (Docs):**
- `38-hosted-demo.md` file exists with deployment instructions
- `grep "38" docs/guide/README.md` — entry present
- `grep "38" docs/guide/index.html` — sidebar entry present
- `grep "38" backend/app/templates/guide.html` — button entry present
- `grep "DEMO_MODE" docs/guide/appendix-a-environment-variables.md` — env var documented
- `grep -i "demo mode" docs/guide/appendix-d-glossary.md` — glossary entry present

### Requirements Mapping

This slice owns or validates:
- **DEMO-04** (Demo tour completes without errors) — E2E test proves tour trigger + localStorage completion flag
- **DEMO-05** (Pre-built demo dashboard renders) — E2E test proves dashboard tab opens with content
- **DEMO-06** (CTA banner visible after tour) — E2E test proves banner element visible after tour completes
- **DEMO-07** (Docker Compose demo config with SSL) — Caddyfile + updated deploy script
- **DEMO-08** (Periodic data reset) — reset-demo.sh + cron documentation in Chapter 38
- **DEMO-09** (Basic uptime monitoring) — Health check endpoint already exists; documented in Chapter 38

DEMO-03 browser-level visibility also gets validated here by the E2E test seeing sample data in the workspace.

## Constraints

- **Three guide files must stay in sync** — Per KNOWLEDGE.md rule: `docs/guide/README.md`, `docs/guide/index.html`, and `backend/app/templates/guide.html` must all list Chapter 38.
- **Caddyfile is a template, not production-ready** — The domain is a placeholder (`demo.sempkm.app`). Actual DNS/SSL depends on the VPS provider and domain registration, which are out of scope.
- **E2E test runs against port 3902** — The existing `demo` Playwright project targets `http://localhost:3902` with no auth. The test must use the `demo` project, not the default test project.
- **Tour steps depend on timing** — The demo tour uses 500ms delays between navigation and `moveNext()`. E2E test should verify the *outcome* (localStorage flag set) rather than trying to step through each tour step.
- **Navigation chain** — Chapter 37 currently points to Appendix A as "Next". Chapter 38 must be inserted between them: Ch 37 → Ch 38 → Appendix A.

## Common Pitfalls

- **E2E tour timeout** — Don't try to click through all 7 tour steps in the E2E test. The tour auto-navigates with hardcoded 500ms delays and DOM-dependent element targeting. Instead, trigger `window.startDemoTour()` via `page.evaluate()` and wait for the localStorage flag to be set (polling or `page.waitForFunction`). If the tour hangs on a step, the test should timeout gracefully.
- **CTA banner visibility timing** — The CTA banner is shown via a `sempkm:demo-tour-done` custom event *or* on page load if `sempkm_demo_tour_done` localStorage is set. After triggering the tour, the test should wait for localStorage before checking banner visibility. The banner might need a moment to animate in (CSS slide-up animation).
- **Dashboard tab opening** — The tour's step 6 calls `openDashboardTab('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', 'Demo Dashboard')`. The E2E test can open it the same way via `page.evaluate()` or verify it exists via API query.
