---
id: T04
parent: S01
milestone: M028
provides:
  - "POST /api/ai/suggest-relationships endpoint with URL+FTS-based graph matching and deduplication"
  - "POST /api/ai/summarize endpoint with LLM-based personalized page summary incorporating graph context"
  - "17 integration tests covering auth, degradation, suggest-relationships, summarize, and well-known discovery"
key_files:
  - backend/app/api/ai.py
  - backend/tests/test_ai_endpoints.py
key_decisions:
  - "suggest-relationships does not require LLM — uses SPARQL URL matching + FTS keyword matching only; returns 400 on empty input instead of 503"
  - "Summarize fallback on LLM error returns SummarizeResponse with fallback text instead of 500 — keeps the response contract stable"
  - "Mocking pattern for async LLMConfigService methods: patch individual methods with new_callable=AsyncMock, not the class — avoids 'dict not awaitable' errors"
patterns_established:
  - "httpx mock response: use MagicMock (not AsyncMock) for resp.json() since httpx Response.json() is synchronous"
  - "Integration test app builder: _build_ai_app() + _build_well_known_app() as separate helpers for testing different routers"
observability_surfaces:
  - "logger.debug on every suggest-relationships and summarize request with user email, input sizes, and output counts"
  - "logger.warning(exc_info=True) on all failure paths: SPARQL, FTS, label resolution, LLM calls"
  - "GET /.well-known/sempkm returns all 6 AI endpoint paths and 'ai-insights' capability"
duration: 20min
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T04: Add relationship suggestions, personalized summary, and integration tests

**Added POST /api/ai/suggest-relationships (URL+FTS graph matching) and POST /api/ai/summarize (LLM personalized summary), plus 17 integration tests verifying auth, degradation, and well-known discovery across all 6 AI endpoints**

## What Happened

Added the final two AI endpoints to complete the S01 slice:

1. **suggest-relationships** — accepts URL, title, and claims; Phase 1 runs SPARQL to find objects citing the same URL, Phase 2 runs FTS combining title+claim text as keywords. Deduplicates by IRI (URL match wins), caps at 10 suggestions. Types suggestions as "link", "supports", "evidence" based on matched object type (Claim → supports, Evidence → evidence, others → link).

2. **summarize** — accepts page content and optional graph context items, builds a summarization prompt that references the user's existing knowledge graph objects, makes a non-streaming LLM call, and returns the summary. Returns 503 when LLM not configured, 400 on empty content, and a graceful fallback message on LLM errors.

3. **Integration tests** — 17 tests in `test_ai_endpoints.py` covering: 6 auth tests (one per endpoint), 3 degradation tests (LLM not configured), 4 suggest-relationships tests (success, empty input, URL match, deduplication), 3 summarize tests (success, empty content, graph context in prompt), 1 well-known discovery test.

The well-known endpoint already had all 6 AI paths from a prior task — verified it includes `suggest_relationships`, `summarize`, and `ai-insights` capability.

## Verification

- `test_ai_endpoints.py` — 17/17 passed
- All 4 test files combined — 59/59 passed with zero failures
- LSP diagnostics on `ai.py` — 0 errors (1 hint: unused constant from T03, used in tests)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_ai_endpoints.py -v` | 0 | ✅ pass | 0.77s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_llm_proxy.py tests/test_claim_detection.py tests/test_claim_matching.py tests/test_ai_endpoints.py -v` | 0 | ✅ pass | 1.28s |
| 3 | LSP diagnostics on `backend/app/api/ai.py` | — | ✅ pass (0 errors) | — |

## Diagnostics

- **Suggest-relationships smoke test:** `POST /api/ai/suggest-relationships` with `{"url": "https://example.com"}` — non-empty `suggestions` array confirms SPARQL+FTS round-trip
- **Summarize smoke test:** `POST /api/ai/summarize` with `{"content": "any text"}` — `summary` field in response confirms LLM round-trip
- **LLM unavailable:** suggest-relationships still works (no LLM needed); summarize returns 503 with `{"error": "LLM not configured"}`
- **Logs:** `logger.debug` on every request includes user email, input sizes, and result counts; `logger.warning` with `exc_info=True` on all failure paths

## Deviations

- Mock pattern for LLM tests: used `@patch("app.api.ai.LLMConfigService.get_config", new_callable=AsyncMock)` instead of patching the whole class — discovered that patching the class breaks async awaits. This matches the pattern established in `test_claim_detection.py`.
- Used `MagicMock` (not `AsyncMock`) for httpx response objects since `Response.json()` is synchronous — using `AsyncMock` causes `'coroutine' object is not subscriptable` errors.

## Known Issues

None.

## Files Created/Modified

- `backend/app/api/ai.py` — Added suggest-relationships and summarize endpoints with Pydantic models, SPARQL URL matching, FTS keyword matching, LLM summarization prompt builder
- `backend/tests/test_ai_endpoints.py` — New file: 17 integration tests covering all 6 AI endpoints (auth, degradation, business logic, well-known discovery)
- `.gsd/milestones/M028/slices/S01/tasks/T04-PLAN.md` — Added Observability Impact section (pre-flight fix)
