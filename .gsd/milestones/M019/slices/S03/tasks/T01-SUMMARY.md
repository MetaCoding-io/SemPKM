---
id: T01
parent: S03
milestone: M019
provides:
  - Mock Todoist API server with canned responses and selftest
  - TODOIST_API_URL env var override in todoist_client.py and auth.py
  - mock-todoist Docker service wired into test stack
key_files:
  - e2e/mock-todoist-api/server.py
  - apps/todoist-sync/services/todoist_client.py
  - apps/todoist-sync/services/auth.py
  - docker-compose.test.yml
key_decisions:
  - Mock routes include /rest/v2/ prefix so TODOIST_API_URL=http://mock-todoist:8080/rest/v2 maps cleanly to how TodoistClient builds URLs
patterns_established:
  - Mock Todoist server follows same stdlib http.server + selftest pattern as mock-github-api and mock-google-calendar-api
observability_surfaces:
  - Mock server logs each request to stderr as [mock-todoist] METHOD /path → STATUS
  - Selftest prints pass/fail per endpoint with [selftest] FAIL prefix and non-zero exit on failure
  - docker compose logs mock-todoist for request inspection in Docker
duration: 12min
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Build mock Todoist API server, add env var override, and wire Docker service

**Built mock Todoist API server (10 endpoints, 10 selftest checks), added TODOIST_API_URL env var override to client and auth modules, wired mock-todoist service into docker-compose.test.yml**

## What Happened

Created `e2e/mock-todoist-api/server.py` following the established mock-github-api pattern. The mock handles all Todoist REST v2 endpoints used by the app: GET projects/tasks/labels, POST close/reopen/update/create, plus /health. Close and reopen correctly return 204 with empty body. Auth validation checks Bearer token, returns 401 on missing/invalid.

Added `import os` and `os.environ.get("TODOIST_API_URL", ...)` to both `todoist_client.py` (module-level constant) and `auth.py` (inline in `verify_token()`). The default value is the production Todoist URL, so existing behavior is unchanged.

Wired `mock-todoist` service into `docker-compose.test.yml` with the same pattern as other mocks (python:3.12-slim, health check via urllib, sempkm-test network). Added `TODOIST_API_URL` env var to the api service and `mock-todoist` to depends_on with service_healthy condition.

## Verification

1. `python3 e2e/mock-todoist-api/server.py --selftest` — 10/10 checks passed (health, projects, tasks, labels, auth failure, close 204, reopen 204, update, create, project content validation)
2. `./backend/.venv/bin/pytest backend/tests/test_todoist_*.py -v` — 239 tests passed in 0.46s (no regressions from env var change)
3. `docker compose -f docker-compose.test.yml config --quiet` — validated without error
4. `rg "os.environ" apps/todoist-sync/services/todoist_client.py apps/todoist-sync/services/auth.py` — both files confirmed using env var

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 e2e/mock-todoist-api/server.py --selftest` | 0 | ✅ pass | <1s |
| 2 | `./backend/.venv/bin/pytest backend/tests/test_todoist_*.py -v` | 0 | ✅ pass | 0.46s |
| 3 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass | 4.6s |
| 4 | `rg "os.environ" apps/todoist-sync/services/todoist_client.py apps/todoist-sync/services/auth.py` | 0 | ✅ pass | <1s |

## Diagnostics

- **Mock server health:** `python3 e2e/mock-todoist-api/server.py --selftest` — tests all endpoints without starting a server
- **Docker request logs:** `docker compose -f docker-compose.test.yml logs mock-todoist` — shows timestamped request/status pairs
- **Failure format:** Selftest prints `[selftest] FAIL: {endpoint} — expected {expected}, got {actual}` with non-zero exit

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `e2e/mock-todoist-api/server.py` — New mock Todoist REST API v2 server (canned responses, auth validation, selftest)
- `apps/todoist-sync/services/todoist_client.py` — Added `import os`, changed `TODOIST_API_URL` to read from env var with production default
- `apps/todoist-sync/services/auth.py` — Added `import os`, changed `verify_token()` to use env var for API URL
- `docker-compose.test.yml` — Added mock-todoist service, TODOIST_API_URL env var on api service, depends_on entry
