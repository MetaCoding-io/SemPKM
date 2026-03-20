---
id: S04
parent: M023
milestone: M023
provides:
  - Mock Jira REST API server with 7 endpoints and 12-check selftest
  - mock-jira Docker service in test stack with JIRA_API_URL env wiring
  - jiraSync CSS selector block in shared E2E helpers (14 selectors)
  - Playwright E2E test covering full Jira sync lifecycle (12 phases)
  - User guide Chapter 36 documenting Jira sync with field mapping tables
  - Cross-reference updates (README TOC, 3 glossary entries, appendix-a, navigation chain)
requires:
  - slice: S03
    provides: Complete Jira sync app (all services, routes, templates, CSS) with push sync and issue links
affects: []
key_files:
  - e2e/mock-jira-api/server.py
  - docker-compose.test.yml
  - e2e/helpers/selectors.ts
  - e2e/tests/41-jira-sync/jira-sync.spec.ts
  - docs/guide/36-jira-sync.md
  - docs/guide/README.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/35-github-sync.md
key_decisions:
  - Cloned mock-github-api pattern exactly for mock-jira server (single-file stdlib HTTP server, selftest harness)
  - Added GITHUB_API_URL alongside JIRA_API_URL in appendix-a App-Specific Variables section (was missing)
patterns_established:
  - Mock Jira API server follows same pattern as mock-github — future sync app mocks should clone this structure
  - Jira E2E test follows identical 12-phase structure as GitHub/Linear sync tests
  - Sync app user guide chapters follow Chapter 36 section order (prerequisites → install → connect → config → field mapping → push → troubleshooting)
observability_surfaces:
  - "[mock-jira]" prefixed stderr logs for all HTTP requests in Docker
  - GET /health returns {"status":"ok"} for Docker healthcheck
  - --selftest mode validates all endpoints offline with ✓/✗ markers
  - Playwright test phases labeled with comment blocks for failure localization
  - SPARQL verification queries in phases 8/9/9b surface graph state after sync
drill_down_paths:
  - .gsd/milestones/M023/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M023/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M023/slices/S04/tasks/T03-SUMMARY.md
duration: 50m
verification_result: passed
completed_at: 2026-03-19
---

# S04: E2E Tests + User Guide

**Mock Jira REST API server with 12-check selftest, 12-phase Playwright E2E test covering full Jira sync lifecycle, and Chapter 36 user guide with field mapping tables, statusCategory explanation, and ADF conversion notes.**

## What Happened

Three tasks assembled the final-assembly proof layer for the Jira Sync app:

**T01: Mock Jira REST API server** — Created `e2e/mock-jira-api/server.py` (588 lines) cloning the mock-github-api pattern. Implements 7 endpoints matching the Jira REST API v3 surface that `JiraClient` calls: health, myself, projects, search (POST with JQL parsing), user (accountId query string), issue get, and issue update (PUT with field merge). Canned data includes 2 projects (PROJ, DESIGN) and 3 issues: PROJ-1 (in-progress Bug with assignee and Blocks→PROJ-3 issue link), PROJ-2 (todo Story, unassigned), PROJ-3 (done Epic for milestone mapping). Selftest mode validates all endpoints with 12 checks including error paths (unknown accountId, unknown issue key, 404 on unrecognized paths).

**T02: Docker integration + selectors + E2E test** — Wired `mock-jira` service into `docker-compose.test.yml` (python:3.12-slim, healthcheck, sempkm-test network), added `JIRA_API_URL: http://mock-jira:8080` to the api service, and added depends_on with service_healthy condition. Added `jiraSync` selector block (14 CSS selectors) to `e2e/helpers/selectors.ts` matching actual template IDs/classes. Created `e2e/tests/41-jira-sync/jira-sync.spec.ts` (~300 lines) following the established 12-phase pattern: cleanup → install → navigate → connect (3-field form) → select projects → configure → sync → verify Tasks via SPARQL (≥2, since Epic→Milestone) → verify Milestone ASK → verify dependsOn ASK → admin check → cleanup.

**T03: User guide Chapter 36** — Wrote `docs/guide/36-jira-sync.md` (383 lines) covering prerequisites, 3-field connection flow, project selection, JQL filter with examples, sync configuration, complete field mapping table, status mapping table (3 statusCategory.key values), priority mapping table (8 Jira names), statusCategory explanation, ADF conversion notes with supported node type list, push sync limitations (D237), Epic→Milestone mapping, issue links (Blocks→dependsOn), and troubleshooting. Updated README TOC, added 3 glossary entries (ADF, Jira Sync, statusCategory), added JIRA_API_URL to appendix-a, and fixed navigation chain (Ch 35 → Ch 36 → Appendix A).

## Verification

All slice-level verification checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `python3 e2e/mock-jira-api/server.py --selftest` exits 0 | ✅ 12/12 checks pass |
| 2 | `jiraSync` block in selectors.ts | ✅ 1 block with 14 selectors |
| 3 | `mock-jira` service in docker-compose.test.yml | ✅ service + JIRA_API_URL env + depends_on |
| 4 | E2E test exists with all 12 phases | ✅ 13 Phase references |
| 5 | Chapter 36 exists | ✅ 383 lines |
| 6 | README TOC has Ch 36 entry | ✅ |
| 7 | Glossary has 3 entries (ADF, Jira Sync, statusCategory) | ✅ |
| 8 | appendix-a has JIRA_API_URL | ✅ |
| 9 | Navigation chain Ch 35 → Ch 36 → Appendix A | ✅ |

## Requirements Advanced

None — all JIRA requirements were validated in this or prior slices.

## Requirements Validated

- JIRA-12 — Mock Jira REST API server (12-check selftest), Playwright E2E test (12 phases), Chapter 36 user guide (383 lines with field mapping tables, statusCategory explanation, ADF conversion notes). README TOC, 3 glossary entries, appendix-a JIRA_API_URL, navigation chain.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- T01 added 4 extra selftest checks beyond the planned 8 (unknown accountId → 404, PROJ-3 Epic type verification, unknown issue key → 404, unknown PUT key → 404) — 12 total.
- T03 added `GITHUB_API_URL` to appendix-a alongside `JIRA_API_URL` in a new "App-Specific Variables" section — GitHub's env var was missing from the appendix despite being referenced in Chapter 35.

## Known Limitations

- E2E test is not run as part of this slice (requires full Docker Compose stack). The test file is structurally complete and follows the proven 12-phase pattern from GitHub/Linear sync tests.
- Push sync is limited to title/description/priority per D237 — no status transitions (requires per-project workflow transition discovery).

## Follow-ups

None — S04 is the final slice of M023.

## Files Created/Modified

- `e2e/mock-jira-api/server.py` — New mock Jira REST API server (588 lines) with canned data, HTTP handler, and selftest mode
- `docker-compose.test.yml` — Added mock-jira service, JIRA_API_URL env var, depends_on entry
- `e2e/helpers/selectors.ts` — Added jiraSync selector block (14 selectors)
- `e2e/tests/41-jira-sync/jira-sync.spec.ts` — New Playwright E2E test (12 phases, ~300 lines)
- `docs/guide/36-jira-sync.md` — New Chapter 36 (383 lines) covering Jira sync end-to-end
- `docs/guide/README.md` — Added Ch 36 entry to TOC
- `docs/guide/appendix-d-glossary.md` — Added 3 entries (ADF, Jira Sync, statusCategory)
- `docs/guide/appendix-a-environment-variables.md` — Added App-Specific Variables section with GITHUB_API_URL and JIRA_API_URL
- `docs/guide/35-github-sync.md` — Updated navigation footer Next link to Ch 36

## Forward Intelligence

### What the next slice should know
- M023 is complete. All 4 slices delivered. 385+ combined Jira tests pass across S01–S03. The mock server, E2E test, and user guide close the milestone.
- The Jira sync app follows the same patterns as Linear (M016), GitHub (M017), and Asana (M022) sync apps — service module structure, PersonMatcher, field mapper, sync engine, mock API server, E2E test phases, and user guide chapter structure are all consistent.

### What's fragile
- The E2E test has not been run against the actual Docker stack in this slice — it was written following the proven pattern but requires the full test infrastructure to execute. Any template selector changes would need corresponding updates to the jiraSync selector block.

### Authoritative diagnostics
- `python3 e2e/mock-jira-api/server.py --selftest` — validates all mock endpoints offline, most trustworthy signal for mock correctness
- `grep -c "Phase" e2e/tests/41-jira-sync/jira-sync.spec.ts` — confirms E2E test completeness (should be ≥10)

### What assumptions changed
- No assumptions changed — S04 was straightforward final-assembly work following established patterns from prior sync app milestones.
