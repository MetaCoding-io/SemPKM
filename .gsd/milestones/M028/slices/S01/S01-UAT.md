# S01: Backend AI endpoints with Bearer auth — UAT

**Milestone:** M028
**Written:** 2026-03-20

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All endpoints are verified via 59 unit tests with mocked LLM and triplestore. No live runtime required — contract verification proves all request/response schemas, auth paths, and degradation behaviors. Live LLM integration is tested in S03.

## Preconditions

- Backend venv has test dependencies installed (`pytest`, `pytest-asyncio`, `httpx`)
- Working directory is `backend/`
- No Docker stack required — all tests use mocked services

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_ai_endpoints.py tests/test_llm_proxy.py tests/test_claim_detection.py tests/test_claim_matching.py -v
```
All 59 tests pass in <2s.

## Test Cases

### 1. All AI endpoints reject unauthenticated requests

1. Run `pytest tests/test_ai_endpoints.py::TestAuthRequired -v`
2. **Expected:** 6 tests pass — each of the 6 endpoints returns HTTP 401 when no auth is provided

### 2. LLM stream returns SSE with Bearer token

1. Run `pytest tests/test_llm_proxy.py::TestLLMStreamAcceptsBearerToken -v`
2. **Expected:** POST /api/llm/stream with valid Bearer token returns SSE stream with `text/event-stream` content-type and `X-Accel-Buffering: no` header

### 3. LLM stream returns SSE with cookie auth

1. Run `pytest tests/test_llm_proxy.py::TestLLMStreamAcceptsCookieAuth -v`
2. **Expected:** POST /api/llm/stream with valid session cookie returns SSE stream

### 4. LLM status returns availability JSON

1. Run `pytest tests/test_llm_proxy.py::TestLLMStatusAvailable -v`
2. Run `pytest tests/test_llm_proxy.py::TestLLMStatusUnavailable -v`
3. **Expected:** When LLM configured: `{available: true, provider: "api.openai.com"}`. When not configured: `{available: false, provider: null}`

### 5. Claim detection with valid LLM response

1. Run `pytest tests/test_claim_detection.py::TestDetectClaimsEndpointSuccess -v`
2. **Expected:** POST /api/ai/detect-claims with page content returns `{claims: [{text, confidence, type}]}` parsed from mock LLM response

### 6. Claim parser handles malformed LLM output

1. Run `pytest tests/test_claim_detection.py::TestParseClaimsMalformedJson -v`
2. Run `pytest tests/test_claim_detection.py::TestParseClaimsMarkdownCodeBlock -v`
3. **Expected:** Malformed JSON returns `{claims: [], parse_error: "..."}`. Markdown code block extracts JSON successfully.

### 7. Match-claims returns graph matches with indicators

1. Run `pytest tests/test_claim_matching.py::TestMatchClaimsSuccess -v`
2. **Expected:** POST /api/ai/match-claims returns matches with `indicator` field on each matched_object showing `corroborates`, `contradicts`, `contested`, or `related`

### 8. Contradiction indicator logic is bidirectional

1. Run `pytest tests/test_claim_matching.py::TestComputeIndicatorContradicts -v`
2. **Expected:** 3 tests pass — established-vs-speculative, established-vs-possible, and speculative-vs-established all return `contradicts`

### 9. Match-claims caps results at 5 per claim

1. Run `pytest tests/test_claim_matching.py::TestMatchClaimsCapsAtFive -v`
2. **Expected:** Even with >5 FTS results, each claim's matched_objects array has at most 5 entries

### 10. Research gap detection finds open questions without evidence

1. Run `pytest tests/test_claim_matching.py::TestFindResearchGapsWithMatches -v`
2. **Expected:** Response includes `research_gaps` array with open research questions that have keyword overlap with claims but lack linked evidence

### 11. Suggest-relationships deduplicates URL and FTS matches

1. Run `pytest tests/test_ai_endpoints.py::TestSuggestRelationships::test_suggest_relationships_deduplicates -v`
2. **Expected:** Object matched by both URL and FTS appears once (URL match takes priority)

### 12. Summarize includes graph context in LLM prompt

1. Run `pytest tests/test_ai_endpoints.py::TestSummarize::test_summarize_includes_graph_context -v`
2. **Expected:** LLM request body contains graph context objects (IRI, label, type, snippet) in the prompt

### 13. Well-known discovery includes AI capabilities

1. Run `pytest tests/test_ai_endpoints.py::TestWellKnownAICapabilities -v`
2. **Expected:** GET /.well-known/sempkm response contains all 6 AI endpoint paths and `ai-insights` in capabilities

## Edge Cases

### LLM not configured — all LLM-dependent endpoints degrade gracefully

1. Run `pytest tests/test_ai_endpoints.py::TestGracefulDegradation -v`
2. **Expected:** detect-claims returns 503 `{"error": "LLM not configured"}`; summarize returns 503; match-claims works normally (no LLM needed)

### Empty content on detect-claims

1. Run `pytest tests/test_claim_detection.py::TestDetectClaimsEndpointEmptyContent -v`
2. **Expected:** Returns 400 with error message about empty content

### Empty claims array on match-claims

1. Run `pytest tests/test_claim_matching.py::TestMatchClaimsEmptyClaims -v`
2. **Expected:** Returns `{matches: [], research_gaps: []}` — not an error

### Research model not installed

1. Run `pytest tests/test_claim_matching.py::TestMatchClaimsResearchModelNotInstalled -v`
2. **Expected:** Match-claims still returns FTS results; type resolution gracefully handles missing res:Claim/res:Evidence types

### SearchService error during match-claims

1. Run `pytest tests/test_claim_matching.py::TestMatchClaimsSearchServiceError -v`
2. **Expected:** Per-claim degradation — failed claims have empty matched_objects; other claims still return results

### Suggest-relationships with empty input

1. Run `pytest tests/test_ai_endpoints.py::TestSuggestRelationships::test_suggest_relationships_empty_input -v`
2. **Expected:** Returns 400 — at least url or title or claims must be provided

### LLM call error during detect-claims

1. Run `pytest tests/test_claim_detection.py::TestDetectClaimsEndpointLLMError -v`
2. **Expected:** Returns `{claims: [], parse_error: "LLM call failed: ..."}` — not a 500

## Failure Signals

- Any test returning non-zero exit code
- Import errors in `backend/app/api/ai.py` (missing dependencies)
- 401 on endpoints that should accept Bearer tokens
- 500 instead of 503 when LLM is not configured
- Missing endpoint paths in well-known discovery response
- `parse_error` returning None when LLM output is truly unparseable

## Requirements Proved By This UAT

- EXT-22 — Bearer-authenticated LLM proxy (tests 2, 3)
- EXT-23 — Claim detection with structured JSON (tests 5, 6)
- EXT-24 — Claim-to-graph matching via FTS (tests 7, 9)
- EXT-25 — Contradiction/corroboration indicators (tests 7, 8)
- EXT-26 — Research question gap detection (test 10)
- EXT-27 — Relationship suggestions (tests 11)
- EXT-28 — Personalized summary with graph context (test 12)
- EXT-31 — Graceful degradation when LLM unavailable (edge case 1)

## Not Proven By This UAT

- Claim extraction quality on real page content (requires live LLM — S03 scope)
- Actual SPARQL queries against a real RDF4J triplestore (all SPARQL mocked — S03 scope)
- Extension sidebar consuming these endpoints (S02 scope)
- End-to-end flow from page visit → claim detection → graph match → accept suggestion (S03 E2E test)
- LLM latency within 5s requirement (requires live LLM)

## Notes for Tester

- All tests use mocked services — no Docker stack, no LLM, no triplestore needed
- The 2 deprecation warnings about httpx per-request cookies are harmless (httpx API evolution)
- Test run should complete in <2s; if significantly slower, check for network-level mock timeouts
- To inspect the actual endpoint code: `backend/app/api/ai.py` (1119 lines, well-documented)
