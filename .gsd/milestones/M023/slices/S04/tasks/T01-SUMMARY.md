---
id: T01
parent: S04
milestone: M023
provides:
  - Mock Jira REST API server with 7 endpoints and selftest harness
key_files:
  - e2e/mock-jira-api/server.py
key_decisions:
  - Cloned mock-github-api pattern exactly (single-file stdlib HTTP server, _FakeRequestFile/_FakeWFile selftest harness)
  - 12 selftest checks covering all 7 endpoints plus 404/error paths
patterns_established:
  - Mock Jira API server uses same structure as mock-github-api — future sync app mocks should follow the same pattern
observability_surfaces:
  - "[mock-jira]" prefixed stderr logs for all HTTP requests
  - GET /health returns {"status":"ok"} for Docker healthcheck
  - --selftest mode validates all endpoints offline with ✓/✗ markers
duration: 15m
verification_result: passed
completed_at: 2026-03-19T23:33:00-04:00
blocker_discovered: false
---

# T01: Build mock Jira REST API server with selftest

**Built mock Jira REST API server at e2e/mock-jira-api/server.py with 7 endpoints (health, myself, projects, search, user, issue get, issue update) and 12-check selftest — all passing.**

## What Happened

Created `e2e/mock-jira-api/server.py` (588 lines) by cloning the structure from `e2e/mock-github-api/server.py`. The server implements all 7 endpoint patterns that `JiraClient` calls:

- **GET /health** — liveness check
- **GET /rest/api/3/myself** — authenticated user profile (accountId, displayName, email)
- **GET /rest/api/3/project** — 2 projects (PROJ and DESIGN)
- **POST /rest/api/3/search** — JQL search returning 3 issues with JSON body parsing
- **GET /rest/api/3/user?accountId=X** — user lookup via query string parameter
- **GET /rest/api/3/issue/{key}** — single issue by key from `_ISSUES_BY_KEY` dict
- **PUT /rest/api/3/issue/{key}** — field merge update with deep copy and timestamp

Canned data includes 3 issues in Jira REST API v3 nested `fields` format: PROJ-1 (in-progress Bug with assignee, issuelinks Blocks→PROJ-3), PROJ-2 (todo Story, unassigned), PROJ-3 (done Epic for milestone mapping). The selftest harness uses `_FakeRequestFile`, `_FakeWFile`, and `_make_fake_handler()` to simulate requests without a real socket.

## Verification

- `python3 e2e/mock-jira-api/server.py --selftest` exits 0 with all 12 checks showing ✓
- All 8 must-haves verified: 7 endpoints, POST search with JSON body, PUT update with fields merge, nested fields structure, PROJ-1 issuelinks Blocks→PROJ-3, PROJ-3 Epic type, user query string parsing, selftest exit 0

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 e2e/mock-jira-api/server.py --selftest` | 0 | ✅ pass | <1s |
| 2 | Slice: jiraSync in selectors.ts | — | ⬜ N/A (T02) | — |
| 3 | Slice: mock-jira in docker-compose.test.yml | — | ⬜ N/A (T02) | — |
| 4 | Slice: E2E test file exists | — | ⬜ N/A (T02) | — |
| 5 | Slice: Chapter 36 exists | — | ⬜ N/A (T03) | — |

## Diagnostics

- **Selftest:** `python3 e2e/mock-jira-api/server.py --selftest` — validates all endpoints offline, prints per-check ✓/✗ with summary
- **Docker logs:** `docker compose logs mock-jira` — all requests logged with `[mock-jira]` prefix to stderr
- **Health probe:** `curl http://localhost:8080/health` (or `http://mock-jira:8080/health` inside Docker network)
- **Error responses:** 404 returns `{"message": "Not Found"}`, 400 returns `{"message": "Invalid JSON"}` — structured and distinguishable

## Deviations

- Added 4 additional selftest checks beyond the plan's 8 (user with unknown accountId → 404, PROJ-3 Epic type verification, unknown issue key → 404, unknown PUT key → 404) for more thorough coverage — 12 total vs 8 planned.

## Known Issues

None.

## Files Created/Modified

- `e2e/mock-jira-api/server.py` — New mock Jira REST API server (588 lines) with canned data, HTTP handler, and selftest mode
- `.gsd/milestones/M023/slices/S04/S04-PLAN.md` — Added Observability / Diagnostics section (pre-flight fix)
- `.gsd/milestones/M023/slices/S04/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
