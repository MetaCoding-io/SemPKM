# S03: E2E Tests + User Guide

**Goal:** Mock Todoist API server passes selftest, Playwright E2E test covers full Todoist sync lifecycle, and Chapter 37 user guide documents everything with field mapping tables.
**Demo:** `python e2e/mock-todoist-api/server.py --selftest` exits cleanly; `npx playwright test e2e/tests/37-todoist-sync/` runs structurally complete (may hit pre-existing subprocess issue); `docs/guide/37-todoist-sync.md` renders correctly with all field mapping tables.

## Must-Haves

- Mock Todoist API server with canned responses for projects, tasks, labels, close, reopen, update, create, plus health and selftest endpoints
- `TODOIST_API_URL` env var override in `todoist_client.py` and `auth.py` so Docker test stack can redirect to mock
- Docker service `mock-todoist` wired in `docker-compose.test.yml` with health check and API env var
- E2E Playwright test covering: cleanup → install basic-pkm → install todoist-sync → connect PAT → select projects → configure sync → Sync Now → verify tasks via SPARQL → admin detail → cleanup
- `todoistSync` selectors block in `e2e/helpers/selectors.ts`
- Chapter 37 user guide with field mapping tables (priority inversion, status, due dates, labels), close/reopen pattern, troubleshooting
- README TOC updated, glossary entry added, appendix A env var added, navigation chain Ch 36 → Ch 37 → Appendix A

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (Docker test stack with mock Todoist API)
- Human/UAT required: no

## Verification

- `python e2e/mock-todoist-api/server.py --selftest` — exits 0 with all checks passed
- `python -m pytest backend/tests/test_todoist_*.py -v` — 239 existing unit tests still pass (env var change is backward-compatible)
- `rg "os.environ" apps/todoist-sync/services/todoist_client.py apps/todoist-sync/services/auth.py` — both files use env var override
- `docker compose -f docker-compose.test.yml config --quiet` — Docker service definition valid
- `rg "hx-(post|get)=" apps/todoist-sync/frontend/templates/ | grep -v "/app/todoist-sync/"` — empty (all htmx URLs prefixed)
- `rg "37-todoist" docs/guide/` — appears in README, glossary, appendix, ch. 36 footer
- `rg "Todoist Sync" docs/guide/appendix-d-glossary.md` — glossary entry exists
- `rg "TODOIST_API_URL" docs/guide/appendix-a-environment-variables.md` — env var documented
- Mock server selftest validates error path: `GET /tasks` without `Authorization` header returns 401 (failure-path diagnostic check)

## Observability / Diagnostics

- Runtime signals: Mock server logs each request to stderr (`[mock-todoist] METHOD /path → STATUS`). Selftest prints pass/fail per endpoint check.
- Inspection surfaces: `python e2e/mock-todoist-api/server.py --selftest` for mock health. `docker compose -f docker-compose.test.yml logs mock-todoist` for request logs. E2E test phase comments identify exact failure point.
- Failure visibility: Selftest prints `[selftest] FAIL: {endpoint} — expected {expected}, got {actual}` with non-zero exit code. E2E test failure shows which phase failed (0-9) with Playwright trace.
- Redaction constraints: Mock PAT token `test-todoist-pat-token-abc123` is test-only, no redaction needed.

## Integration Closure

- Upstream surfaces consumed: `apps/todoist-sync/services/todoist_client.py` (TODOIST_API_URL constant), `apps/todoist-sync/services/auth.py` (hardcoded verify URL), `apps/todoist-sync/app.py` (route handlers), `apps/todoist-sync/frontend/templates/*.html` (UI selectors), all S01+S02 outputs
- New wiring introduced in this slice: `mock-todoist` Docker service in `docker-compose.test.yml`, `TODOIST_API_URL` env var on `api` service, E2E test spec file, `todoistSync` selector block
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Build mock Todoist API server, add env var override, and wire Docker service** `est:45m`
  - Why: The E2E test needs a mock Todoist API running in Docker, and the app code needs `TODOIST_API_URL` env var so the Docker test stack redirects API calls to the mock. This is the foundation for T02.
  - Files: `e2e/mock-todoist-api/server.py`, `apps/todoist-sync/services/todoist_client.py`, `apps/todoist-sync/services/auth.py`, `docker-compose.test.yml`
  - Do: Build mock server with canned responses (projects, tasks, labels, close/reopen/update/create, health, selftest with ~10 checks including auth validation). Add `import os` and `os.environ.get("TODOIST_API_URL", ...)` to both todoist_client.py and auth.py. Add `mock-todoist` service and `TODOIST_API_URL` env var to docker-compose.test.yml.
  - Verify: `python e2e/mock-todoist-api/server.py --selftest` exits 0. `python -m pytest backend/tests/test_todoist_*.py -v` — 239 tests still pass. `docker compose -f docker-compose.test.yml config --quiet` succeeds.
  - Done when: Mock server selftest passes with all endpoint checks, env var override works without breaking existing tests, Docker compose validates.

- [x] **T02: Write Playwright E2E test and add todoist selectors** `est:45m`
  - Why: Proves the full Todoist sync lifecycle end-to-end through the Docker test stack — the integration-level evidence for TD-01 through TD-07.
  - Files: `e2e/tests/37-todoist-sync/todoist-sync.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Add `todoistSync` selector block to selectors.ts matching template IDs/classes. Write E2E test following github-sync.spec.ts phase structure: cleanup → install basic-pkm → install todoist-sync → open app settings → connect PAT → select projects → configure bidirectional sync → Sync Now → verify tasks via SPARQL (check priority inversion: Todoist 4 → critical) → admin detail → cleanup. Document pre-existing subprocess issue in comments.
  - Verify: `npx playwright test e2e/tests/37-todoist-sync/ --list` shows the test. Test file compiles without TypeScript errors.
  - Done when: E2E test file is structurally complete with all phases, selectors are defined, test is runnable (may hit pre-existing subprocess issue at Phase 2).

- [x] **T03: Write Chapter 37 user guide and update documentation chain** `est:40m`
  - Why: Completes the user-facing documentation for Todoist sync — field mapping tables, priority inversion explanation, close/reopen pattern, and troubleshooting. Updates all cross-reference points.
  - Files: `docs/guide/37-todoist-sync.md`, `docs/guide/README.md`, `docs/guide/appendix-d-glossary.md`, `docs/guide/appendix-a-environment-variables.md`, `docs/guide/36-google-calendar-sync.md`
  - Do: Write Ch. 37 following Ch. 35 structure: Prerequisites, Installing, Connecting (PAT), Selecting Projects, Sync Configuration, Manual Sync, Sync Stats, Field Mapping tables (priority inversion 1↔low through 4↔critical, status, due dates, labels, external link), Push Sync (close/reopen pattern), Admin Monitoring, Troubleshooting, See Also. Update README TOC (add line 37), glossary (add Todoist Sync entry), appendix A (add TODOIST_API_URL), and Ch. 36 navigation footer (Next → Ch 37).
  - Verify: `rg "37-todoist" docs/guide/` shows hits in README, glossary, appendix, ch. 36. `rg "Todoist Sync" docs/guide/appendix-d-glossary.md` finds entry. `rg "TODOIST_API_URL" docs/guide/appendix-a-environment-variables.md` finds entry.
  - Done when: Chapter 37 is complete with all field mapping tables, all cross-references are wired, navigation chain is Ch 36 → Ch 37 → Appendix A.

## Files Likely Touched

- `e2e/mock-todoist-api/server.py`
- `apps/todoist-sync/services/todoist_client.py`
- `apps/todoist-sync/services/auth.py`
- `docker-compose.test.yml`
- `e2e/tests/37-todoist-sync/todoist-sync.spec.ts`
- `e2e/helpers/selectors.ts`
- `docs/guide/37-todoist-sync.md`
- `docs/guide/README.md`
- `docs/guide/appendix-d-glossary.md`
- `docs/guide/appendix-a-environment-variables.md`
- `docs/guide/36-google-calendar-sync.md`
