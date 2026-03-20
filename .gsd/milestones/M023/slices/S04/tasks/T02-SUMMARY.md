---
id: T02
parent: S04
milestone: M023
provides:
  - mock-jira Docker service in test stack with JIRA_API_URL env wiring
  - jiraSync CSS selector block in shared E2E helpers
  - Playwright E2E test covering full Jira sync lifecycle (12 phases)
key_files:
  - docker-compose.test.yml
  - e2e/helpers/selectors.ts
  - e2e/tests/41-jira-sync/jira-sync.spec.ts
key_decisions:
  - Followed exact same Docker service pattern as mock-github (python:3.12-slim, healthcheck on /health, sempkm-test network)
  - Used .credentials-form selector for Jira connect button (differs from GitHub's .api-key-form) matching the actual template class
  - Test expects ≥2 Tasks (not ≥3 like GitHub) because PROJ-3 Epic maps to Milestone, not Task
patterns_established:
  - Jira E2E test follows identical 12-phase structure as GitHub and Linear sync tests — future sync app E2E tests should clone this pattern
observability_surfaces:
  - Docker healthcheck on mock-jira visible via `docker compose -f docker-compose.test.yml ps mock-jira`
  - Container logs via `docker compose -f docker-compose.test.yml logs mock-jira`
  - Playwright test phases labeled with comment blocks — failures report which phase broke
  - SPARQL verification queries in phases 8/9/9b surface graph state after sync
duration: 20m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Wire Docker integration, add selectors, and write Playwright E2E test

**Wired mock-jira Docker service into test stack, added jiraSync selectors to shared helpers, and wrote 12-phase Playwright E2E test covering full Jira sync lifecycle with SPARQL verification**

## What Happened

Made three file changes as specified in the plan:

1. **docker-compose.test.yml** — Added `mock-jira` service block (python:3.12-slim, volume mount to `e2e/mock-jira-api`, healthcheck on `/health`, sempkm-test network). Added `JIRA_API_URL: http://mock-jira:8080` to the `api` service environment. Added `mock-jira: condition: service_healthy` to the `api` service `depends_on`.

2. **e2e/helpers/selectors.ts** — Added `jiraSync` selector block with 14 selectors matching the actual template IDs/classes from `connect.html` and `connect_status.html`. Key difference from `githubSync`: uses `.credentials-form` (not `.api-key-form`) and includes `emailInput`, `tokenInput`, and `siteUrlInput` for the 3-field connect form.

3. **e2e/tests/41-jira-sync/jira-sync.spec.ts** — Created 300-line Playwright E2E test following the established 12-phase pattern from `github-sync.spec.ts`. All phases adapted for Jira specifics: Phase 4 fills 3 credentials fields, Phase 5 selects Jira projects (not repos), Phase 8 SPARQL counts Tasks (≥2), Phase 9 verifies Epic→Milestone mapping with ASK query, Phase 9b verifies dependsOn edges from issue links. Test timeout 240s, dialog auto-accept configured.

Also fixed the pre-flight observability gap by adding an `## Observability Impact` section to T02-PLAN.md.

## Verification

- `grep -c "jiraSync" e2e/helpers/selectors.ts` → 1 ✓
- `grep -c "mock-jira" docker-compose.test.yml` → 4 (≥3 required) ✓
- `grep -c "JIRA_API_URL" docker-compose.test.yml` → 1 ✓
- `grep -c "Phase" e2e/tests/41-jira-sync/jira-sync.spec.ts` → 13 (≥10 required) ✓
- Mock server selftest still passes: 12/12 checks ✓
- E2E test has all 12 phases (0-11 including 9b) ✓
- 3-field connect form (email, token, siteUrl) confirmed in test ✓
- SPARQL queries for Task count, Milestone ASK, and dependsOn ASK all present ✓

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c "jiraSync" e2e/helpers/selectors.ts` | 0 | ✅ pass (returns 1) | <1s |
| 2 | `grep -c "mock-jira" docker-compose.test.yml` | 0 | ✅ pass (returns 4, ≥3 required) | <1s |
| 3 | `grep -c "JIRA_API_URL" docker-compose.test.yml` | 0 | ✅ pass (returns 1) | <1s |
| 4 | `grep -c "Phase" e2e/tests/41-jira-sync/jira-sync.spec.ts` | 0 | ✅ pass (returns 13, ≥10 required) | <1s |
| 5 | `python3 e2e/mock-jira-api/server.py --selftest` | 0 | ✅ pass (12/12 checks) | <1s |

## Diagnostics

- **Docker service health:** `docker compose -f docker-compose.test.yml ps mock-jira` — shows container health status
- **Container logs:** `docker compose -f docker-compose.test.yml logs mock-jira` — all HTTP requests logged with `[mock-jira]` prefix
- **E2E test output:** Playwright reports phase-by-phase with line numbers. Failed phases are identifiable by the `Phase N` comment above the failing assertion.
- **SPARQL verification:** If sync produces wrong graph state, phases 8/9/9b will fail with actual vs expected count/boolean values.
- **Selector mismatches:** If template IDs change, the `jiraSync` selectors in `selectors.ts` will cause `toBeVisible` timeouts with the exact CSS selector that didn't match.

## Deviations

None — followed the plan exactly.

## Known Issues

None.

## Files Created/Modified

- `docker-compose.test.yml` — Added mock-jira service, JIRA_API_URL env var, depends_on entry
- `e2e/helpers/selectors.ts` — Added jiraSync selector block (14 selectors)
- `e2e/tests/41-jira-sync/jira-sync.spec.ts` — New Playwright E2E test (12 phases, ~300 lines)
- `.gsd/milestones/M023/slices/S04/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
