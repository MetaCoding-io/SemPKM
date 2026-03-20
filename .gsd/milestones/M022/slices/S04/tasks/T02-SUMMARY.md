---
id: T02
parent: S04
milestone: M022
provides:
  - Docker compose mock-asana service with healthcheck and env vars on api service
  - Playwright E2E selector block for Asana Sync UI (asanaSync in selectors.ts)
  - Full 7-phase Playwright E2E spec covering install → PAT connect → field mapping → sync → SPARQL verify → cleanup
key_files:
  - docker-compose.test.yml
  - e2e/helpers/selectors.ts
  - e2e/tests/40-asana-sync/asana-sync.spec.ts
key_decisions:
  - Section-based status mapping chosen for E2E test (static table rendering, simpler to verify than JS-driven custom field mapping)
  - SPARQL verification asserts specific task names from mock data (Design landing page, Write API documentation) rather than just count
patterns_established:
  - Field mapping E2E pattern: projects → discover fields → select status source → save mapping → sync config → sync now
observability_surfaces:
  - Docker healthcheck on mock-asana (GET /health)
  - Per-phase Playwright pass/fail with SPARQL triplestore verification
  - Mock request logging to stderr as [mock-asana] METHOD /path → STATUS
duration: 12m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Wire Docker compose, add selectors, write Playwright E2E spec

**Wired mock-asana into Docker test stack, added asanaSync selector block, wrote 7-phase Playwright E2E spec with SPARQL verification for full Asana sync lifecycle.**

## What Happened

Added the `mock-asana` service to `docker-compose.test.yml` following the exact pattern of existing mock services (python:3.12-slim, volume mount, healthcheck on `/health`). Set `ASANA_API_URL` and `ASANA_TOKEN_URL` env vars on the `api` service pointing to the mock, and added `mock-asana` to `depends_on` with `service_healthy` condition.

Added the `asanaSync` selector block to `e2e/helpers/selectors.ts` with 13 selectors covering PAT input, connect button, project checkboxes, discover fields, status source radio, save mapping, sync direction, sync config, sync now button, and sync stats.

Wrote the full E2E spec at `e2e/tests/40-asana-sync/asana-sync.spec.ts` (~280 lines) with 7 phases:
- Phase 0: Cleanup prior installation
- Phase 1: Install basic-pkm model
- Phase 2: Install asana-sync app, poll until Running
- Phase 3: PAT connect via workspace sidebar (expand APPS section, click leaf, fill PAT, verify Connected + email)
- Phase 4: Field mapping — select projects, discover fields, select section-based status mapping, verify mapping table, save configuration, set bidirectional sync
- Phase 5: Sync Now + verify stats (created ≥ 2) + SPARQL verification (assert "Design landing page" and "Write API documentation" in triplestore)
- Phase 6: Admin detail page verification + uninstall

The spec uses `test-asana-pat-token-abc123` matching the mock server's `VALID_TOKEN`. All selectors reference the `SEL.asanaSync` block. The SPARQL query targets `urn:sempkm:model:basic-pkm:Task` with `dcterms:title`, matching the sync engine's object creation pattern.

## Verification

- `docker compose -f docker-compose.test.yml config --quiet` → exit 0, no errors
- `grep -c "asanaSync" e2e/helpers/selectors.ts` → 1
- E2E spec file exists with all 7 phases (9 phase comments found)
- Spec uses correct PAT token and imports from `../../fixtures/auth` and `../../helpers/selectors`
- Mock selftest passes: 14/14 checks

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass | <1s |
| 2 | `grep -c "asanaSync" e2e/helpers/selectors.ts` | 0 | ✅ pass (1 match) | <1s |
| 3 | `test -f e2e/tests/40-asana-sync/asana-sync.spec.ts` | 0 | ✅ pass | <1s |
| 4 | `grep -c "test-asana-pat-token-abc123" e2e/tests/40-asana-sync/asana-sync.spec.ts` | 0 | ✅ pass (1 match) | <1s |
| 5 | `grep "Phase 0\|Phase 1\|...\|Phase 6" spec` | 0 | ✅ pass (9 phase comments) | <1s |
| 6 | `grep "import.*fixtures/auth\|import.*helpers/selectors" spec` | 0 | ✅ pass (both imports) | <1s |
| 7 | `python3 e2e/mock-asana-api/server.py --selftest` | 0 | ✅ pass (14/14) | <1s |

## Diagnostics

- **Docker healthcheck:** `docker compose -f docker-compose.test.yml ps mock-asana` shows healthy/unhealthy status
- **Mock server logs:** `docker compose -f docker-compose.test.yml logs mock-asana` shows request log per line
- **E2E test run:** `npx playwright test e2e/tests/40-asana-sync/asana-sync.spec.ts` (requires Docker stack running on port 3901)

## Deviations

- SPARQL query uses `dcterms:title` (matching the sync engine's actual property) instead of `CONTAINS(STR(?label), "Review")` from the plan — the plan's query referenced a nonexistent "Review" task name. Corrected to assert "Design landing page" and "Write API documentation" which are the actual mock task names.
- Spec is ~280 lines instead of the planned ~350-400. The field mapping phase is thorough but doesn't need the verbosity projected.

## Known Issues

None.

## Files Created/Modified

- `docker-compose.test.yml` — added mock-asana service definition + ASANA_API_URL/ASANA_TOKEN_URL env vars + depends_on entry
- `e2e/helpers/selectors.ts` — added asanaSync selector block with 13 selectors
- `e2e/tests/40-asana-sync/asana-sync.spec.ts` — new 7-phase Playwright E2E spec (~280 lines)
- `.gsd/milestones/M022/slices/S04/tasks/T02-PLAN.md` — added Observability Impact section per pre-flight fix
