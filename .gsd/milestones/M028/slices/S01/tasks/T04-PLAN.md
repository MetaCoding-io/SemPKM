---
estimated_steps: 8
estimated_files: 4
---

# T04: Add relationship suggestions, personalized summary, and integration tests

**Slice:** S01 — Backend AI endpoints with Bearer auth
**Milestone:** M028

## Description

Complete the AI endpoint surface by adding the final two endpoints (`POST /api/ai/suggest-relationships` and `POST /api/ai/summarize`), then write integration tests that exercise all 6 endpoints together, verifying the full contract including graceful degradation. This task closes the S01 slice.

**Relationship suggestions** reuse the same SPARQL/FTS patterns as the context-query endpoint (`backend/app/api/router.py` — `context_query()` function). The idea: given a page's URL, title, and detected claims, find existing objects that share references or topics, and suggest creating edges.

**Personalized summary** is the simplest endpoint: take page content + graph context objects (from match-claims results), send to LLM with a prompt that says "summarize this page in the context of what the user already knows", return the summary string.

**Relevant skill:** `test` — for generating pytest unit tests.

## Steps

1. In `backend/app/api/ai.py`, add Pydantic models for suggest-relationships:
   ```python
   class SuggestRelationshipsRequest(BaseModel):
       url: str = ""
       title: str = ""
       claims: list[ClaimInput] = []

   class RelationshipSuggestion(BaseModel):
       type: str  # "link" | "evidence" | "supports" | "contradicts"
       label: str  # human-readable suggestion text
       target_iri: str
       target_label: str
       reason: str  # why this suggestion was made

   class SuggestRelationshipsResponse(BaseModel):
       suggestions: list[RelationshipSuggestion] = []
   ```

2. Add `POST /ai/suggest-relationships` endpoint:
   - Depends on `get_current_user_or_api` (uses triplestore, search_service, label_service from app.state)
   - Validate at least one of url/title/claims is provided (400 otherwise)
   - Phase 1 — URL matching: If URL provided, run same SPARQL as context_query (find objects with matching URL string value). For each match, suggest `type="link"`, reason="cites same URL".
   - Phase 2 — Keyword matching: Combine title + claim texts into search keywords. Run FTS via SearchService. For each result, check type:
     - If it's a `res:Claim` → suggest `type="supports"` or `type="contradicts"` based on keyword similarity
     - If it's a Note/Concept → suggest `type="link"`, reason="discusses similar topic"
     - If it's a `res:Evidence` → suggest `type="evidence"`, reason="may provide evidence"
   - Deduplicate by target_iri (first match wins)
   - Cap at 10 suggestions total
   - Return `SuggestRelationshipsResponse`

3. Add Pydantic models for summarize:
   ```python
   class GraphContextItem(BaseModel):
       iri: str
       label: str
       type: str = ""
       snippet: str = ""

   class SummarizeRequest(BaseModel):
       content: str
       graph_context: list[GraphContextItem] = []

   class SummarizeResponse(BaseModel):
       summary: str
   ```

4. Add `POST /ai/summarize` endpoint:
   - Depends on `get_current_user_or_api` and `get_db_session`
   - Validates content is not empty (400 if empty)
   - Checks LLM availability — returns 503 if not configured
   - Builds summarization prompt:
     - System: "Summarize the following page content. The user has existing knowledge about these topics: [list graph_context items with labels and types]. Incorporate references to the user's existing knowledge where relevant. Be concise (2-3 paragraphs)."
     - User: page content (truncated to ~4000 chars)
   - Makes non-streaming LLM call via httpx
   - Extracts summary from response `choices[0].message.content`
   - Returns `SummarizeResponse(summary=...)`
   - On LLM error, returns `SummarizeResponse(summary="Unable to generate summary. Please try again.")`

5. Ensure the well-known discovery endpoint (updated in T01) includes all 6 new endpoint paths in the endpoints dict. Verify the `get_well_known()` function in `backend/app/api/router.py` has entries for: `llm_stream`, `llm_status`, `detect_claims`, `match_claims`, `suggest_relationships`, `summarize`.

6. Write `backend/tests/test_ai_endpoints.py` — integration-level tests exercising all endpoints:
   - **Auth tests** (one per endpoint, 6 tests):
     - `test_llm_stream_requires_auth`, `test_llm_status_requires_auth`, `test_detect_claims_requires_auth`, `test_match_claims_requires_auth`, `test_suggest_relationships_requires_auth`, `test_summarize_requires_auth` — all return 401 without auth
   - **Degradation tests** (3 tests):
     - `test_detect_claims_llm_not_configured` — returns 503
     - `test_summarize_llm_not_configured` — returns 503
     - `test_match_claims_works_without_llm` — match-claims doesn't need LLM, should still work
   - **Suggest-relationships tests** (4 tests):
     - `test_suggest_relationships_success` — mock search+triplestore → suggestions returned
     - `test_suggest_relationships_empty_input` — no url/title/claims → 400
     - `test_suggest_relationships_url_match` — mock URL match → link suggestion
     - `test_suggest_relationships_deduplicates` — same IRI from URL+FTS → single suggestion
   - **Summarize tests** (3 tests):
     - `test_summarize_success` — mock LLM → summary returned
     - `test_summarize_empty_content` — empty content → 400
     - `test_summarize_includes_graph_context` — verify prompt includes context items (check the request sent to mock LLM)
   - **Well-known integration** (1 test):
     - `test_well_known_includes_ai_capabilities` — GET /.well-known/sempkm includes "ai-insights" capability and new endpoint paths

7. Verify all 4 test files pass together: `cd backend && python -m pytest tests/test_llm_proxy.py tests/test_claim_detection.py tests/test_claim_matching.py tests/test_ai_endpoints.py -v`

8. Run LSP diagnostics on `backend/app/api/ai.py` to verify no type errors or missing imports.

## Must-Haves

- [ ] `POST /api/ai/suggest-relationships` returns relationship suggestions based on URL/keyword matching
- [ ] `POST /api/ai/summarize` returns LLM-generated summary incorporating graph context
- [ ] Both new endpoints return 503 when LLM not configured (summarize only — suggest doesn't need LLM)
- [ ] suggest-relationships returns 400 when no url/title/claims provided
- [ ] summarize returns 400 when content is empty
- [ ] Well-known discovery includes all 6 AI endpoint paths and "ai-insights" capability
- [ ] Integration tests verify auth on all 6 endpoints
- [ ] All tests pass across all 4 test files

## Verification

- `cd backend && python -m pytest tests/test_ai_endpoints.py -v` — all 17 tests pass
- `cd backend && python -m pytest tests/test_llm_proxy.py tests/test_claim_detection.py tests/test_claim_matching.py tests/test_ai_endpoints.py -v` — all tests pass (total ~50+ tests)
- LSP diagnostics on `backend/app/api/ai.py` — zero errors

## Inputs

- `backend/app/api/ai.py` — AI router from T01-T03 (must have ai_router, llm_stream, llm_status, detect-claims, match-claims)
- `backend/app/api/router.py` — well-known endpoint and context_query SPARQL patterns
- `backend/app/services/search.py` — SearchService for FTS
- `backend/tests/test_llm_proxy.py` — T01 test file for fixture patterns
- `backend/tests/test_claim_detection.py` — T02 test file
- `backend/tests/test_claim_matching.py` — T03 test file

## Expected Output

- `backend/app/api/ai.py` — complete with all 6 endpoints (llm/stream, llm/status, detect-claims, match-claims, suggest-relationships, summarize)
- `backend/app/api/router.py` — well-known updated with all AI endpoint paths and capabilities
- `backend/tests/test_ai_endpoints.py` — 17 integration tests all passing
- All 4 test files pass together with zero failures

## Observability Impact

- **New signals:** `logger.debug` on every `POST /api/ai/suggest-relationships` request (user email, URL, title, claim count, suggestion count); `logger.debug` on every `POST /api/ai/summarize` request (user email, content length, context items count, summary length)
- **Failure visibility:** suggest-relationships logs `logger.warning(exc_info=True)` on URL SPARQL, FTS, type resolution, or label resolution failures — partial results returned, not 500; summarize logs `logger.warning(exc_info=True)` on LLM call failure and returns fallback "Unable to generate summary" text
- **Inspection surfaces:** `GET /api/llm/status` (unchanged) probes LLM availability; `GET /.well-known/sempkm` now lists all 6 AI endpoints + "ai-insights" capability — extensions can discover full AI surface
- **Degradation:** suggest-relationships returns 400 on empty input; summarize returns 400 on empty content, 503 when LLM not configured; LLM errors produce graceful fallback summary text
