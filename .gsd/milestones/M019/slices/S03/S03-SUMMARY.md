---
id: S03
parent: M019
milestone: M019
provides:
  - Mock Todoist REST API v2 server with 10-endpoint selftest
  - TODOIST_API_URL env var override in todoist_client.py and auth.py
  - mock-todoist Docker service wired into docker-compose.test.yml
  - 11-phase Playwright E2E test for full Todoist sync lifecycle
  - todoistSync selector block in e2e/helpers/selectors.ts
  - Chapter 37 user guide with field mapping tables, priority inversion, close/reopen pattern, troubleshooting
  - README TOC, glossary, appendix A, and navigation chain updates
requires:
  - slice: S01
    provides: todoist_client.py, auth.py, field_mapper.py, sync_engine.py, app.py, connect templates
  - slice: S02
    provides: push_sync(), close/reopen methods, settings UI, push-changes handler
affects: []
key_files:
  - e2e/mock-todoist-api/server.py
  - apps/todoist-sync/services/todoist_client.py
  - apps/todoist-sync/services/auth.py
  - docker-compose.test.yml
  - e2e/tests/37-todoist-sync/todoist-sync.spec.ts
  - e2e/helpers/selectors.ts
  - docs/guide/37-todoist-sync.md
  - docs/guide/README.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/36-google-calendar-sync.md
key_decisions:
  - Mock routes include /rest/v2/ prefix so TODOIST_API_URL=http://mock-todoist:8080/rest/v2 maps cleanly to how TodoistClient builds URLs
patterns_established:
  - Mock Todoist server follows same stdlib http.server + selftest pattern as mock-github-api and mock-google-calendar-api
  - Todoist E2E follows same phase structure as github-sync.spec.ts and google-calendar-sync.spec.ts
observability_surfaces:
  - Mock server logs each request to stderr as [mock-todoist] METHOD /path → STATUS
  - Selftest prints pass/fail per endpoint with [selftest] FAIL prefix and non-zero exit on failure
  - E2E test phase comments (0–10) identify exact failure point in Playwright trace
  - docker compose logs mock-todoist for request inspection in Docker
drill_down_paths:
  - .gsd/milestones/M019/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M019/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M019/slices/S03/tasks/T03-SUMMARY.md
duration: 39m
verification_result: passed
completed_at: 2026-03-19
---

# S03: E2E Tests + User Guide

**Mock Todoist API server (10 endpoints, 10 selftest checks), Playwright E2E test (11 phases covering full sync lifecycle), and Chapter 37 user guide with priority inversion tables, close/reopen documentation, and troubleshooting**

## What Happened

Three tasks assembled the final-assembly proof layer for the Todoist Sync app.

**T01 — Mock server + env var + Docker wiring.** Built `e2e/mock-todoist-api/server.py` with canned responses for all Todoist REST v2 endpoints: GET projects/tasks/labels, POST close/reopen/update/create, plus /health. Close and reopen return 204 with empty body (matching real Todoist behavior). Auth validation returns 401 on missing/invalid Bearer token. Selftest exercises all 10 endpoints without starting a server. Added `TODOIST_API_URL` env var override to both `todoist_client.py` and `auth.py` — defaults to production URL, so existing behavior unchanged and all 239 unit tests pass. Wired `mock-todoist` service into `docker-compose.test.yml` with health check, network, and API env var on the api service.

**T02 — Playwright E2E test.** Added `todoistSync` selector block (11 selectors) to `selectors.ts`, cross-checked against template HTML. Created 11-phase E2E test following the established github-sync pattern: cleanup → install basic-pkm → install todoist-sync → open app settings → connect PAT → select projects → configure bidirectional sync → Sync Now → SPARQL verification (task count + priority inversion: Todoist 4 → "critical") → admin detail → cleanup. Pre-existing subprocess 500 error documented in comments.

**T03 — Chapter 37 user guide.** ~290 lines covering prerequisites, installation, connecting (PAT), project selection, sync configuration, manual sync, field mapping tables (priority inversion all 4 levels, status pull/push, due dates, labels, external link, sync metadata), close/reopen endpoint pattern, loop prevention, admin monitoring, and troubleshooting (5 subsections). Updated README TOC, glossary (Todoist Sync entry), appendix A (TODOIST_API_URL), and Ch 36 navigation footer (Next → Ch 37).

## Verification

All slice-level verification checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `python3 e2e/mock-todoist-api/server.py --selftest` | 10/10 passed |
| 2 | `pytest backend/tests/test_todoist_*.py -v` | 239 passed in 0.46s |
| 3 | `rg "os.environ" apps/todoist-sync/services/todoist_client.py apps/todoist-sync/services/auth.py` | Both files confirmed |
| 4 | `docker compose -f docker-compose.test.yml config --quiet` | Valid |
| 5 | `rg "hx-(post\|get)=" apps/todoist-sync/frontend/templates/ \| grep -v "/app/todoist-sync/"` | Empty (all prefixed) |
| 6 | `rg "37-todoist" docs/guide/` | Hits in README, glossary, Ch 36 |
| 7 | `rg "Todoist Sync" docs/guide/appendix-d-glossary.md` | Entry present |
| 8 | `rg "TODOIST_API_URL" docs/guide/appendix-a-environment-variables.md` | Row present |
| 9 | `npx playwright test tests/37-todoist-sync/ --list` (from e2e/) | 2 tests listed (chromium + firefox) |
| 10 | Mock selftest 401 on missing auth | Verified in selftest check 5 |

## Requirements Advanced

- No formal TD requirements were tracked in REQUIREMENTS.md — the roadmap used TD-01 through TD-08 as informal coverage references only

## Requirements Validated

- None to formally update (TD requirements were not in REQUIREMENTS.md)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

None. All three tasks completed as planned.

## Known Limitations

- **Pre-existing subprocess 500 error:** E2E test Phase 2 (app install) may fail due to the subprocess startup issue documented across M016–M018. This is not Todoist-specific — it affects all app E2E tests equally.
- **E2E test is structurally complete but not runtime-proven:** The test covers all 11 phases and compiles without errors, but full end-to-end Docker execution may be blocked by the subprocess issue above.

## Follow-ups

- None. This is the final slice of M019.

## Files Created/Modified

- `e2e/mock-todoist-api/server.py` — Mock Todoist REST API v2 server (10 endpoints, auth validation, selftest)
- `apps/todoist-sync/services/todoist_client.py` — Added TODOIST_API_URL env var override
- `apps/todoist-sync/services/auth.py` — Added TODOIST_API_URL env var override in verify_token()
- `docker-compose.test.yml` — Added mock-todoist service, TODOIST_API_URL on api service, depends_on
- `e2e/tests/37-todoist-sync/todoist-sync.spec.ts` — 11-phase Playwright E2E test
- `e2e/helpers/selectors.ts` — Added todoistSync selector block (11 selectors)
- `docs/guide/37-todoist-sync.md` — Chapter 37 user guide (~290 lines, 37 sections)
- `docs/guide/README.md` — Added line 37 to TOC
- `docs/guide/appendix-d-glossary.md` — Added Todoist Sync glossary entry
- `docs/guide/appendix-a-environment-variables.md` — Added TODOIST_API_URL row
- `docs/guide/36-google-calendar-sync.md` — Updated navigation footer (Next → Ch 37)

## Forward Intelligence

### What the next slice should know
- This is the final slice of M019. The milestone is complete. All three slices delivered auth+client+pull (S01), push+settings (S02), and E2E+docs (S03).

### What's fragile
- The pre-existing subprocess startup issue continues to block full E2E runtime across all sync apps (M016–M019). A platform-level fix would unblock all app E2E tests simultaneously.

### Authoritative diagnostics
- `python3 e2e/mock-todoist-api/server.py --selftest` — exercises all mock endpoints without Docker, exits non-zero on any failure
- `pytest backend/tests/test_todoist_*.py -v` — 239 tests prove all unit-level behavior in <1s

### What assumptions changed
- No assumptions changed. The slice executed exactly as planned — Todoist's simple REST v2 API made this the lowest-risk sync app of the four.
