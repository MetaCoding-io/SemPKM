---
id: T01
parent: S03
milestone: M028
provides:
  - Mock OpenAI-compatible LLM server for E2E testing (canned claim JSON responses)
  - mock-llm service in docker-compose.test.yml with healthcheck and api dependency
key_files:
  - e2e/mock-llm-api/server.py
  - docker-compose.test.yml
key_decisions:
  - Followed established mock-jira pattern exactly (BaseHTTPRequestHandler + SilentHandler selftest)
  - Claims response uses clean JSON (strategy 1 direct json.loads) matching _parse_claims_response() expectations
patterns_established:
  - Mock LLM server pattern reusable for any future OpenAI-compatible mock needs
observability_surfaces:
  - "[mock-llm]" prefixed stderr logs for all requests (visible in docker compose logs)
  - GET /health liveness endpoint for Docker healthcheck
  - --selftest mode with per-check pass/fail output and structured summary line
  - 404 responses return structured JSON {"message": "Not Found"} not HTML
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Create mock LLM server and add to Docker compose

**Created mock OpenAI-compatible LLM server with canned claim extraction response and wired into Docker test stack as mock-llm service**

## What Happened

Created `e2e/mock-llm-api/server.py` following the established `mock-jira-api/server.py` pattern. The server implements three endpoints: `GET /health` (Docker liveness), `GET /v1/models` (returns test-model for Settings connection test), and `POST /v1/chat/completions` (returns OpenAI-format response with `choices[0].message.content` containing valid claim JSON with 3 claims: factual/likely, statistical/established, analytical/speculative). The `--selftest` mode validates all 5 test cases (3 happy paths + 2 404s) without needing Docker.

Added `mock-llm` service to `docker-compose.test.yml` after mock-monday, using the same Python 3.12-slim image pattern. Added `mock-llm` to the api service's `depends_on` with `condition: service_healthy`. No `MOCK_LLM_URL` env var was added — the LLM URL is configured at runtime via the Settings API.

Applied pre-flight observability fixes: added Observability / Diagnostics section to S03-PLAN.md, diagnostic failure-path verification to slice checks, and Observability Impact section to T01-PLAN.md.

## Verification

- `python3 e2e/mock-llm-api/server.py --selftest` — 5/5 checks passed, exit 0
- `python3 -c "import ast; ast.parse(open('e2e/mock-llm-api/server.py').read())"` — syntax valid
- `grep "mock-llm" docker-compose.test.yml` — returns service definition + api depends_on entry
- `grep -c "MOCK_LLM_URL" docker-compose.test.yml` — returns 0 (no env var added)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 e2e/mock-llm-api/server.py --selftest` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('e2e/mock-llm-api/server.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `grep "mock-llm" docker-compose.test.yml` | 0 | ✅ pass | <1s |
| 4 | `grep -c "MOCK_LLM_URL" docker-compose.test.yml` → 0 | 1 (grep no-match) | ✅ pass | <1s |

### Slice-Level Verification (partial — T01 is first of 3 tasks)

| # | Check | Status |
|---|-------|--------|
| 1 | `python3 e2e/mock-llm-api/server.py --selftest` passes | ✅ pass |
| 2 | `e2e/tests/25-extension/extension-ai-insights.spec.ts` exists | ⬜ T02 |
| 3 | `grep "mock-llm" docker-compose.test.yml` returns service | ✅ pass |
| 4 | `grep "40-ai-features"` in navigation files | ⬜ T03 |
| 5 | `docs/guide/40-ai-features.md` exists | ⬜ T03 |
| 6 | Chapter 39 nav footer updated | ⬜ T03 |
| 7 | Glossary entries ≥3 | ⬜ T03 |

## Diagnostics

- **Offline validation:** `python3 e2e/mock-llm-api/server.py --selftest` — runs 5 endpoint checks without Docker
- **Docker logs:** `docker compose -f docker-compose.test.yml logs mock-llm` — shows `[mock-llm]` prefixed request logs
- **Health status:** `docker compose -f docker-compose.test.yml ps` — mock-llm shows healthy/unhealthy
- **Error shape:** Unrecognized paths return `{"message": "Not Found"}` with HTTP 404

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `e2e/mock-llm-api/server.py` — New: Mock OpenAI-compatible LLM server with canned claim JSON responses, 3 endpoints, selftest mode
- `docker-compose.test.yml` — Modified: Added mock-llm service with healthcheck; added to api depends_on
- `.gsd/milestones/M028/slices/S03/S03-PLAN.md` — Modified: Added Observability / Diagnostics section and diagnostic verification check
- `.gsd/milestones/M028/slices/S03/tasks/T01-PLAN.md` — Modified: Added Observability Impact section
