---
id: T01
parent: S04
milestone: M035
provides:
  - SSE streaming mock LLM server with pattern-matched copilot canned responses
  - mock-llm Docker service in test compose stack
key_files:
  - e2e/mock-llm-api/server.py
  - docker-compose.test.yml
key_decisions:
  - Pattern matching priority: claims > SPARQL > create-object > summarize > generic (backward compat first)
  - SSE chunks split by word with trailing space to match OpenAI tokenization style
patterns_established:
  - _select_response() pattern-matching function for adding new canned response routes
observability_surfaces:
  - "[mock-llm] POST /v1/chat/completions stream=true|false route=copilot|claims" log on every request
  - GET /health returns {"status": "ok"} for Docker healthcheck and manual inspection
  - "python server.py --selftest" exercises all 12 routes and reports pass/fail per check
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Upgrade mock LLM server with SSE streaming and copilot canned responses

**Upgraded mock LLM server with SSE streaming, pattern-matched copilot canned responses (SPARQL, create-object, summarize, generic), and added mock-llm service to docker-compose.test.yml**

## What Happened

The existing mock LLM server only returned hardcoded claims JSON for every POST request and ignored the `stream` field entirely. Upgraded it to:

1. **Parse request bodies** — extracts `stream` field and last user message content for pattern matching.
2. **Pattern-matched canned responses** — five routes: "claim"/"extract" → claims JSON (M028 backward compat), "how many"/"project" → SPARQL code block, "create"+"task" → create_object JSON block, "summarize"/"context" → prose summary, default → generic helpful response.
3. **SSE streaming** — when `stream: true`, splits response into word-by-word SSE chunks in OpenAI `chat.completion.chunk` format, ending with `data: [DONE]` sentinel. Each chunk has proper `delta.content` and the final chunk has `finish_reason: "stop"`.
4. **Non-streaming mode** still works via `_build_completion_response()` which wraps content in the standard `chat.completion` envelope.
5. **Selftest expanded** from 5 to 12 checks covering all routes in both streaming and non-streaming modes, verifying SSE format, content routing, and JSON structure.
6. **docker-compose.test.yml** — added `mock-llm` service following the exact `mock-linear` pattern (python:3.12-slim, volume mount, healthcheck), added it to `api` depends_on, and set `LLM_API_URL` env var.

## Verification

- `python3 e2e/mock-llm-api/server.py --selftest` — 12/12 checks passed
- `docker compose -f docker-compose.test.yml config --quiet` — validated without errors
- `cd backend && python -m pytest tests/test_copilot_service.py tests/test_ai_personas.py tests/test_object_creation_chat.py tests/test_graph_context.py tests/test_conversation_service.py -v` — 139 tests passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 e2e/mock-llm-api/server.py --selftest` | 0 | ✅ pass | <1s |
| 2 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py tests/test_ai_personas.py tests/test_object_creation_chat.py tests/test_graph_context.py tests/test_conversation_service.py -v` | 0 | ✅ pass | 1.4s |
| 4 | `python3 e2e/mock-llm-api/server.py --selftest 2>&1 \| grep -c '✗'` | — | ✅ pass (0 failures) | <1s |

## Diagnostics

- **Selftest:** `python3 e2e/mock-llm-api/server.py --selftest` — exercises all routes without Docker, reports per-check pass/fail.
- **Health probe:** `curl http://mock-llm:8080/health` from within Docker network returns `{"status": "ok"}`.
- **Request logs:** Every request logged to stderr as `[mock-llm] POST /v1/chat/completions stream=true route=copilot` — visible via `docker compose logs mock-llm`.
- **Pattern debugging:** To test a specific route, send a POST with a message containing the trigger keywords and check the response content.

## Deviations

- Added `LLM_API_URL` env var to the api service in docker-compose.test.yml — not in the task plan but needed for the backend to discover the mock LLM endpoint during E2E tests.
- Backend regression tests showed 139 passing (not 126 as estimated in the slice plan) — the count was approximate.

## Known Issues

None.

## Files Created/Modified

- `e2e/mock-llm-api/server.py` — upgraded with SSE streaming, 5-route pattern matching, extended selftest (12 checks)
- `docker-compose.test.yml` — added mock-llm service, LLM_API_URL env var, depends_on entry
- `.gsd/milestones/M035/slices/S04/tasks/T01-PLAN.md` — added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M035/slices/S04/S04-PLAN.md` — added diagnostic verification step (pre-flight fix)
