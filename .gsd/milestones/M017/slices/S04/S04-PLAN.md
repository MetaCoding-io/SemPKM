# S04: E2E Tests + User Guide

**Goal:** Mock GitHub REST API server running in Docker, Playwright E2E test covering full install → configure → sync → verify → push → cleanup lifecycle, and Chapter 35 user guide documenting GitHub sync with field mapping tables.
**Demo:** `npx playwright test e2e/tests/32-github-sync/github-sync.spec.ts` passes against Docker test stack. `docs/guide/35-github-sync.md` exists with field mapping tables. README TOC and glossary updated.

## Must-Haves

- Mock GitHub REST API server with canned responses for 6 endpoints (GET /user, GET /user/repos, GET /repos/{owner}/{repo}/issues, GET /repos/{owner}/{repo}/issues/{n}/timeline, PATCH /repos/{owner}/{repo}/issues/{n}, GET /health)
- `--selftest` flag validates all canned responses before Docker involvement
- `docker-compose.test.yml` includes `mock-github` service with `GITHUB_API_URL` env var wired to api container
- Playwright E2E test (~12 phases) covering install → connect → repo selection → sync config → sync now → SPARQL verification → PR edge verification → admin detail → cleanup
- E2E test verifies diagnostic surface: sync stats show pull result status and created count
- Chapter 35 user guide with field mapping tables (GitHub → bpkm:Task, status mapping, PR handling)
- README TOC includes Ch 35, glossary has GitHub Sync entry, navigation links updated

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (Docker test stack with mock GitHub API)
- Human/UAT required: no

## Verification

- `python e2e/mock-github-api/server.py --selftest` exits 0 with all endpoints validated
- `docker compose -f docker-compose.test.yml up -d --build` starts mock-github container as healthy
- `npx playwright test e2e/tests/32-github-sync/github-sync.spec.ts` passes against Docker test stack (port 3901)
- E2E test verifies sync stats section shows pull result with status and created count ≥ 2 — proving the diagnostic surface is operational and a future agent can inspect sync outcomes via the UI
- `docs/guide/35-github-sync.md` exists with ≥10 sections and field mapping tables
- `grep "35-github-sync" docs/guide/README.md` finds the TOC entry
- `grep -i "github sync" docs/guide/appendix-d-glossary.md` finds the glossary entry

## Observability / Diagnostics

- Runtime signals: Mock server logs each request method/path to stderr. E2E test captures sync stats from the settings page UI after Sync Now completes.
- Inspection surfaces: Sync stats panel in connect_status.html shows last_pull_result (status/created/updated/errors) and last_push_result (status/pushed/skipped/errors). E2E test asserts on these stat values.
- Failure visibility: If pull sync fails, the sync stats section shows status "error" with failed_issues list. If mock server doesn't start, Docker healthcheck fails and docker-compose up reports unhealthy. E2E test timeout at 240s provides phase-level failure localization.
- Redaction constraints: PAT value in mock test is a fake token (e.g., `ghp_testtoken123`) — no real credentials involved.

## Integration Closure

- Upstream surfaces consumed: `apps/github-sync/` (all services from S01-S03), `docker-compose.test.yml` (existing test stack), `e2e/helpers/selectors.ts` (selector registry), `e2e/fixtures/auth.ts` (auth fixture), `docs/guide/34-linear-sync.md` (reference pattern for Ch 35)
- New wiring introduced in this slice: `mock-github` Docker service, `GITHUB_API_URL` env var on api container, `githubSync` selector block in helpers
- What remains before the milestone is truly usable end-to-end: nothing — S04 is the terminal slice

## Tasks

- [x] **T01: Mock GitHub REST API server + docker-compose integration** `est:45m`
  - Why: Unblocks the E2E test. The mock server provides canned responses for all 6 GitHub API endpoints the client calls, so the E2E test can run without a real GitHub account.
  - Files: `e2e/mock-github-api/server.py`, `docker-compose.test.yml`
  - Do: Clone `e2e/mock-linear-api/server.py` structure, replace GraphQL substring matching with REST path-based routing (do_GET + do_PATCH). Include rate-limit headers on every response. Canned data: 2 repos, 2 issues + 1 PR, 1 timeline cross-reference event, PATCH echo-back. Add `--selftest` mode. Wire into docker-compose.test.yml as `mock-github` service on port 8080. Add `GITHUB_API_URL: http://mock-github:8080` to api environment.
  - Verify: `python e2e/mock-github-api/server.py --selftest` exits 0. `docker compose -f docker-compose.test.yml config` shows mock-github service correctly wired.
  - Done when: Selftest passes and docker-compose config validates with mock-github service and GITHUB_API_URL env var.

- [ ] **T02: Playwright E2E test for GitHub sync lifecycle** `est:1h`
  - Why: Primary runtime validation for GH-01 through GH-07. Proves the full vertical works against Docker test stack with the mock server from T01.
  - Files: `e2e/tests/32-github-sync/github-sync.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Add `githubSync` selector block to selectors.ts. Write ~12-phase test following linear-sync.spec.ts pattern: cleanup → install basic-pkm → install github-sync → open settings → connect PAT → select repos → configure bidirectional → sync now → verify tasks via SPARQL (≥3 including PR) → verify PR-to-issue edge → verify sync stats diagnostic surface shows status and counts → admin detail → cleanup. Use generous timeouts (240s total, 30s per phase). APPS section starts collapsed — click header to expand. Use `ownerRequest` for SPARQL queries.
  - Verify: `npx playwright test e2e/tests/32-github-sync/github-sync.spec.ts` passes. All 12 phases complete successfully.
  - Done when: E2E test passes against Docker test stack on port 3901 with mock-github providing canned responses.

- [ ] **T03: Chapter 35 user guide + glossary and navigation updates** `est:30m`
  - Why: Documents the GitHub sync workflow for end users. Completes GH-07 requirement coverage alongside T01+T02.
  - Files: `docs/guide/35-github-sync.md`, `docs/guide/README.md`, `docs/guide/appendix-d-glossary.md`, `docs/guide/34-linear-sync.md`
  - Do: Clone Ch 34 structure, adapt for GitHub: Prerequisites, Installing the App, Connecting to GitHub (PAT only), Selecting Repositories, Sync Configuration, Manual Sync, Understanding Sync Stats, Field Mapping tables (GitHub→bpkm:Task from M017-RESEARCH), Push Sync, PR-to-Issue Linking (unique to GitHub), Admin Monitoring, Troubleshooting, See Also. Add Ch 35 entry to README TOC. Add "GitHub Sync" glossary entry. Update Ch 34 "Next" nav link to point to Ch 35. Set Ch 35 nav links: Previous=Ch 34, Next=Appendix A.
  - Verify: File exists with ≥10 heading sections and field mapping table. `grep "35-github-sync" docs/guide/README.md` finds TOC entry. `grep -i "github sync" docs/guide/appendix-d-glossary.md` finds entry. Navigation links chain correctly.
  - Done when: Ch 35 exists with complete content, README TOC updated, glossary entry added, navigation links form correct chain (Ch 34 → Ch 35 → Appendix A).

## Files Likely Touched

- `e2e/mock-github-api/server.py`
- `docker-compose.test.yml`
- `e2e/tests/32-github-sync/github-sync.spec.ts`
- `e2e/helpers/selectors.ts`
- `docs/guide/35-github-sync.md`
- `docs/guide/README.md`
- `docs/guide/appendix-d-glossary.md`
- `docs/guide/34-linear-sync.md`
