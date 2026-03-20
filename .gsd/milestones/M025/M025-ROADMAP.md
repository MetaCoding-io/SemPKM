# M025: Hosted Demo Instance

**Vision:** A pre-populated, publicly accessible SemPKM instance that lets prospective users explore the product without installing Docker — click a link, take a 3-minute guided tour, see the value, then decide to self-host.

## Success Criteria

- Anonymous visitor lands at a public URL and sees the workspace immediately — no login, no setup wizard
- All write operations (POST/PUT/DELETE/PATCH on mutation endpoints) return 403 JSON error at the nginx layer
- 30-50 interconnected sample objects across 4 Mental Models (basic-pkm, CRM, zettelkasten, research) are visible in the explorer, graph, and table views
- A demo-optimized Driver.js tour completes in under 3 minutes, walking visitors through graph, forms, validation, canvas, and dashboard
- A pre-built demo dashboard renders with real data and demonstrates cross-view context filtering
- "Try SemPKM" CTA banner is visible after tour completion with install link
- Validation warnings appear on seed data (overdue task, stale contact, unprocessed fleeting note)
- The instance deploys via docker-compose.demo.yml with SSL termination and handles concurrent visitors
- Periodic reset mechanism restores clean state (cron or container restart)

## Key Risks / Unknowns

- **Anonymous access bypass** — The auth system has no anonymous mode; `get_current_user` always requires a valid session. A `DEMO_MODE` env var must bypass this cleanly without breaking existing auth for non-demo instances. This is the foundation — if anonymous visitors can't reach the workspace, nothing else matters.
- **Tour reliability on first load** — Existing Driver.js tours assume an authenticated user with workspace loaded. Demo tour must handle auto-navigation, element timing (htmx lazy loads), and no pre-existing session state. Tour step selectors depend on sample data being loaded.
- **Write-blocking completeness** — Missing even one POST route allows data corruption across visitors. Default-deny approach (block all non-GET/HEAD/OPTIONS) is safer than endpoint-by-endpoint allowlisting, but must still pass health checks and the auto-login path.

## Proof Strategy

- **Anonymous access** → retire in S01 by proving a fresh browser hits `/browser/` and sees the workspace without login, AND POST to `/api/commands` returns 403
- **Tour reliability** → retire in S03 by proving the tour starts on a fresh anonymous session, completes all steps without errors, and the dashboard renders with data
- **Write-blocking** → retire in S01 by proving every mutation method on every endpoint family returns 403 while all read routes return 200

## Verification Classes

- Contract verification: unit tests for DEMO_MODE auth bypass, E2E Playwright tests for read-only enforcement and demo tour flow
- Integration verification: Docker Compose demo stack with all 4 models installed, sample data loaded, tour completing against real data
- Operational verification: docker-compose.demo.yml deploys, SSL terminates, periodic reset cron restores clean state
- UAT / human verification: visitor experience — tour pacing, visual appeal of sample data, CTA visibility

## Milestone Definition of Done

This milestone is complete only when all are true:

- [ ] All 4 slice deliverables are complete and verified
- [ ] Anonymous visitor lands in workspace without login on demo compose stack
- [ ] All write endpoints return 403 on demo compose stack
- [ ] 30-50 sample objects visible across 4 models with cross-model edges
- [ ] Demo tour starts and completes without errors on fresh anonymous session
- [ ] Pre-built dashboard renders with real data and context filtering works
- [ ] CTA banner visible after tour completion
- [ ] Validation warnings fire on seed data (overdue task, stale contact, unprocessed note)
- [ ] docker-compose.demo.yml deploys with SSL config
- [ ] Reset mechanism documented and tested
- [ ] E2E Playwright test verifies full demo flow
- [ ] User guide page documents deployment and configuration
- [ ] Success criteria re-checked against live demo stack
- [ ] Zero conflict markers in committed code

## Requirement Coverage

- Covers: DEMO-01, DEMO-02, DEMO-03, DEMO-04, DEMO-05, DEMO-06, DEMO-07, DEMO-08, DEMO-09, DEMO-10
- Partially covers: none
- Leaves for later: none
- Orphan risks: none — all 10 candidate requirements from research are mapped

## Slices

- [x] **S01: Read-only enforcement + DEMO_MODE anonymous access** `risk:high` `depends:[]`
  > After this: anonymous visitor hits the demo compose stack, lands in the workspace without login, can browse all read routes, and every write endpoint returns 403 JSON — proven by E2E Playwright test against running Docker stack

- [x] **S02: Sample data generation script** `risk:medium` `depends:[S01]`
  > After this: running the seed script against a demo stack creates 30-50 interconnected objects across 4 Mental Models with bodies, edges, tags, and validation-triggering data — proven by SPARQL queries and explorer visibility

- [x] **S03: Demo tour + dashboard + CTA banner** `risk:medium` `depends:[S02]`
  > After this: anonymous visitor sees the tour auto-start (or clicks a button), completes 7 steps in under 3 minutes covering graph/forms/validation/canvas/dashboard, sees a CTA banner, and the pre-built dashboard filters correctly — proven by E2E Playwright test

- [x] **S04: Cloud deployment config + E2E + docs** `risk:low` `depends:[S01,S02,S03]`
  > After this: docker-compose.demo.yml with Caddy SSL termination deploys the full demo stack, periodic reset cron restores clean state, E2E test verifies the complete demo flow, and user guide documents deployment — proven by deployment script and E2E test

## Boundary Map

### S01 → S02

Produces:
- `DEMO_MODE=true` env var in `backend/app/auth/dependencies.py` that makes `get_current_user` return a synthetic read-only guest user without session/cookie check
- Read-only nginx config snippet blocking all non-GET/HEAD/OPTIONS methods (except health check) with 403 JSON response
- `docker-compose.demo.yml` extending base compose with DEMO_MODE env and read-only nginx override
- E2E test proving anonymous access works and writes are blocked

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `scripts/seed-demo-data.py` Python script that installs 4 models and creates 30-50 interconnected objects via Command API (or bulk endpoint)
- Cross-model edges (CRM Contact who is a basic-pkm Person, Research Paper cited in Zettelkasten LiteratureNote, etc.)
- Validation-triggering data (overdue task, stale contact, unprocessed fleeting note)
- Idempotent — checks if demo data exists before creating

Consumes:
- DEMO_MODE anonymous access (S01) — seed script needs a working demo stack to POST commands against
- docker-compose.demo.yml (S01) — seed script runs against the demo compose stack

### S03 → S04

Produces:
- `window.startDemoTour()` in `frontend/static/js/tutorials.js` — 7-step demo-optimized Driver.js tour
- Pre-built demo dashboard (created by seed script extension or startup hook)
- CTA banner in workspace template (visible in demo mode)
- `demo_mode` template variable in workspace rendering

Consumes:
- 30-50 sample objects (S02) — tour steps reference specific objects and views
- DEMO_MODE flag (S01) — CTA banner conditional on demo mode

### S04 (final)

Produces:
- Complete `docker-compose.demo.yml` with Caddy reverse proxy for SSL
- Deployment script with DNS and SSL setup instructions
- Periodic reset cron configuration
- E2E Playwright test exercising full demo flow (anonymous → tour → dashboard → CTA)
- User guide page (`docs/guide/38-hosted-demo.md`) documenting demo deployment
- Basic uptime monitoring via health check endpoint

Consumes:
- All S01-S03 outputs assembled into deployable configuration
