# S04: E2E Tests + User Guide

**Goal:** Prove the Linear sync app works end-to-end against a mocked Linear API in the Docker test stack, and document the full workflow in user guide Chapter 34.
**Demo:** `npx playwright test e2e/tests/31-linear-sync/linear-sync.spec.ts` passes — installing the app, connecting via API key, selecting a team, triggering sync, and verifying tasks appear. `docs/guide/34-linear-sync.md` exists with complete setup/usage documentation linked from the TOC and glossary.

## Must-Haves

- Mock Linear API server returning canned GraphQL responses for viewer, teams, issues, and workflow states
- `LINEAR_GRAPHQL_URL` and `LINEAR_TOKEN_URL` configurable via environment variables in app code
- Docker compose test stack includes `mock-linear` service
- `mock-linear` added to manifest network domains so HttpClient domain check passes
- Playwright E2E test covering install → connect → configure → sync → verify tasks → admin detail → cleanup
- User guide Chapter 34 with installation, API key setup, team selection, sync behavior, push sync, admin monitoring, and troubleshooting
- README TOC updated, navigation chain Ch 33 → Ch 34 → Appendix A, glossary entries added

## Proof Level

- This slice proves: integration + final-assembly
- Real runtime required: yes (Docker test stack with mock Linear API)
- Human/UAT required: no

## Verification

- `cd /home/james/Code/SemPKM && npx playwright test e2e/tests/31-linear-sync/linear-sync.spec.ts` — all tests pass against Docker test stack
- `python3 e2e/mock-linear-api/server.py --selftest` — mock server starts and serves canned responses (or syntax check via `python3 -c "import ast; ast.parse(open('e2e/mock-linear-api/server.py').read())"`)
- `grep "34-linear-sync" docs/guide/README.md` returns a hit
- `grep "Chapter 34" docs/guide/33-context-overlay.md` returns a hit in the navigation footer
- `grep "Linear Sync" docs/guide/appendix-d-glossary.md` returns glossary entries
- All 4 modified Python files pass `python3 -c "import ast; ast.parse(open(f).read())"` syntax check
- `docker compose -f docker-compose.test.yml logs mock-linear 2>&1 | grep -E "Matched query type"` — mock server logs show query type matches (diagnostic surface for test failures)

## Observability / Diagnostics

- Runtime signals: Mock server logs each incoming GraphQL query type to stdout for debugging test failures
- Inspection surfaces: `docker compose -f docker-compose.test.yml logs mock-linear` shows all mock API calls during test run
- Failure visibility: E2E test uses named phases with descriptive assertions — failure messages indicate which phase broke (install, connect, sync, verify)
- Redaction constraints: Mock API key is a test-only value, no real secrets

## Integration Closure

- Upstream surfaces consumed: All S01–S03 app code (`app.py`, `linear_client.py`, `auth.py`, `sync_engine.py`, `field_mapper.py`, `person_matcher.py`), manifest.yaml, frontend templates (`connect.html`, `connect_status.html`)
- New wiring introduced: `mock-linear` Docker service, `LINEAR_API_URL` env var override in linear_client.py and auth.py, `mock-linear` in manifest network list
- What remains before the milestone is truly usable end-to-end: nothing — this is the terminal slice

## Tasks

- [x] **T01: E2E test with mock Linear API server** `est:2h`
  - Why: Proves the full install → configure → poll → verify flow works at integration level against the Docker test stack. This is the primary proof artifact for the milestone.
  - Files: `e2e/mock-linear-api/server.py`, `e2e/tests/31-linear-sync/linear-sync.spec.ts`, `docker-compose.test.yml`, `apps/linear-sync/services/linear_client.py`, `apps/linear-sync/services/auth.py`, `apps/linear-sync/manifest.yaml`, `e2e/helpers/selectors.ts`
  - Do: (1) Make `LINEAR_GRAPHQL_URL` and `LINEAR_TOKEN_URL` configurable via env vars with existing values as defaults. (2) Add `mock-linear` to manifest network domains. (3) Create mock server returning canned GraphQL responses for viewer, organization, teams, issues, workflow states, and issueUpdate mutation — use substring matching on query body. (4) Add `mock-linear` service to docker-compose.test.yml with `LINEAR_API_URL` env var on api container. (5) Write Playwright spec following the app-platform test pattern with serial phases: cleanup, install basic-pkm, install linear-sync, connect API key, select team, configure sync, Sync Now, verify tasks via SPARQL, check admin detail, cleanup.
  - Verify: `npx playwright test e2e/tests/31-linear-sync/linear-sync.spec.ts` passes
  - Done when: All E2E test phases pass against Docker test stack with mock Linear API

- [ ] **T02: User guide Chapter 34 — Linear Sync** `est:1h`
  - Why: Documents the full Linear sync workflow for end users. Terminal documentation artifact for the milestone.
  - Files: `docs/guide/34-linear-sync.md`, `docs/guide/README.md`, `docs/guide/33-context-overlay.md`, `docs/guide/appendix-d-glossary.md`
  - Do: (1) Write Chapter 34 covering: what Linear Sync does, prerequisites (basic-pkm model), installation, API key configuration, team selection, sync direction and interval, manual sync, understanding sync stats, field mapping table, push sync and bidirectional mode, admin monitoring, troubleshooting. (2) Add Ch 34 to README TOC. (3) Update Ch 33 nav footer to point to Ch 34. (4) Add Ch 34 nav footer pointing to Appendix A. (5) Add glossary entries for Linear Sync, Pull Sync, Push Sync, Bidirectional Sync.
  - Verify: `grep "34-linear-sync" docs/guide/README.md` returns a hit; navigation chain is Ch 33 → Ch 34 → Appendix A; glossary entries exist
  - Done when: Chapter 34 exists with complete content, all navigation links correct, glossary entries present

## Files Likely Touched

- `e2e/mock-linear-api/server.py`
- `e2e/tests/31-linear-sync/linear-sync.spec.ts`
- `e2e/helpers/selectors.ts`
- `docker-compose.test.yml`
- `apps/linear-sync/services/linear_client.py`
- `apps/linear-sync/services/auth.py`
- `apps/linear-sync/manifest.yaml`
- `docs/guide/34-linear-sync.md`
- `docs/guide/README.md`
- `docs/guide/33-context-overlay.md`
- `docs/guide/appendix-d-glossary.md`
