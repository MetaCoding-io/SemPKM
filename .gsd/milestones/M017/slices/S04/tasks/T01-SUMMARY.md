---
id: T01
parent: S04
milestone: M017
provides:
  - Mock GitHub REST API server with 6 GET routes + 1 PATCH route
  - docker-compose.test.yml integration with mock-github service and GITHUB_API_URL env var
key_files:
  - e2e/mock-github-api/server.py
  - docker-compose.test.yml
key_decisions:
  - Used SilentHandler subclass approach for selftest to avoid real socket/network overhead
patterns_established:
  - REST path-based mock server pattern (parallel to GraphQL substring mock-linear pattern)
observability_surfaces:
  - Mock server logs each request as "[mock-github] {method} {path} → {status}" to stderr
  - Docker healthcheck on /health endpoint
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Mock GitHub REST API server + docker-compose integration

**Built mock GitHub REST API server with canned responses for all GitHubClient endpoints and wired it into docker-compose.test.yml as the mock-github service.**

## What Happened

Created `e2e/mock-github-api/server.py` by cloning the mock-linear-api pattern but replacing GraphQL substring matching with REST path-based routing via `do_GET` and `do_PATCH`. The server provides canned data covering all edge cases the E2E test needs:

- 2 repos (one public, one private)
- 3 issues: open issue with labels/assignee/milestone, closed issue with state_reason, and an open PR (with `pull_request` key)
- Timeline cross-reference event linking PR #3 to issue #1
- PATCH echo-back that merges request fields with base issue data

Rate-limit headers (`X-RateLimit-Remaining: 4999`, `X-RateLimit-Reset: {future}`) are included on every response to prevent the client's `_check_rate_limit()` from sleeping.

The selftest uses a `SilentHandler` subclass that overrides response methods to capture status/body without needing a real socket — cleaner than the mock-linear approach of just checking JSON round-trippability.

Updated `docker-compose.test.yml`: added `mock-github` service (same Python 3.12-slim image and healthcheck pattern as mock-linear), added `GITHUB_API_URL: http://mock-github:8080` to the api environment, and added `mock-github: condition: service_healthy` to api depends_on.

## Verification

1. `python3 e2e/mock-github-api/server.py --selftest` — 9/9 checks pass (all GET endpoints, PATCH, 404)
2. `docker compose -f docker-compose.test.yml config --services` — lists `mock-github`
3. `docker compose -f docker-compose.test.yml config` — shows `GITHUB_API_URL: http://mock-github:8080` in api environment

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 e2e/mock-github-api/server.py --selftest` | 0 | ✅ pass | <1s |
| 2 | `docker compose --env-file /dev/null -f docker-compose.test.yml config --services` | 0 | ✅ pass | <1s |
| 3 | `docker compose --env-file /dev/null -f docker-compose.test.yml config \| grep GITHUB_API_URL` | 0 | ✅ pass | <1s |

## Diagnostics

- **Mock server request log:** `docker compose -f docker-compose.test.yml logs mock-github` shows `[mock-github] GET /user → 200` style entries on stderr
- **Healthcheck:** Docker healthcheck pings `http://localhost:8080/health` every 3s
- **Selftest for pre-flight:** Run `python3 e2e/mock-github-api/server.py --selftest` before starting Docker to verify canned data integrity

## Deviations

- Selftest is more thorough than mock-linear's (9 endpoint checks vs simple JSON round-trip). This validates actual routing logic, not just data shapes.

## Known Issues

None.

## Files Created/Modified

- `e2e/mock-github-api/server.py` — New mock GitHub REST API server (426 lines) with 6 GET routes, 1 PATCH route, selftest, rate-limit headers
- `docker-compose.test.yml` — Added mock-github service, GITHUB_API_URL env var, depends_on entry
