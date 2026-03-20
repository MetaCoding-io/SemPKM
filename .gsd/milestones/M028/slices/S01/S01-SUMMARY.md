---
id: S01
parent: M028
milestone: M028
provides:
  - "POST /api/llm/stream — Bearer-authenticated SSE proxy for OpenAI-compatible chat completions"
  - "GET /api/llm/status — LLM availability endpoint returning {available, provider} for feature gating"
  - "POST /api/ai/detect-claims — structured claim extraction from page text via LLM with 3-strategy JSON parsing fallback"
  - "POST /api/ai/match-claims — FTS-based graph matching with contradiction/corroboration indicators and research question gap detection"
  - "POST /api/ai/suggest-relationships — URL + FTS keyword matching for relationship suggestions, no LLM required"
  - "POST /api/ai/summarize — LLM-generated personalized summary incorporating graph context objects"
  - "All 6 endpoints use get_current_user_or_api for dual-auth (cookie + Bearer)"
  - "Well-known discovery updated with all AI endpoint paths and ai-insights/llm-stream capabilities"
requires:
  - slice: none
    provides: first slice in M028
affects:
  - S02 (extension sidebar consumes all 6 endpoints)
  - S03 (E2E tests exercise endpoints against Docker stack)
key_files:
  - backend/app/api/ai.py
  - backend/app/main.py
  - backend/app/api/router.py
  - backend/tests/test_llm_proxy.py
  - backend/tests/test_claim_detection.py
  - backend/tests/test_claim_matching.py
  - backend/tests/test_ai_endpoints.py
key_decisions:
  - "D263: New /api/llm/stream with dual-auth instead of modifying existing /browser/settings/llm/chat/stream — avoids breaking htmx Settings page"
  - "Invalid confidence/type values from LLM are silently normalized to defaults (possible/factual) — maximizes extraction even with imperfect LLM compliance"
  - "Content truncation at 4000 chars — balances context window limits vs. extraction quality"
  - "Bidirectional contradiction — both high-existing/low-detected and low-existing/high-detected map to 'contradicts'"
  - "Research gap keyword overlap requires minimum 2 meaningful words (stop words filtered) — balances false positives vs. coverage"
  - "suggest-relationships does not require LLM — uses SPARQL URL matching + FTS keyword matching only"
  - "Summarize returns fallback text on LLM error instead of 500 — stable response contract"
patterns_established:
  - "AI router module: ai_router = APIRouter(prefix='/api', tags=['ai']) — all AI endpoints in one module"
  - "Non-streaming LLM call: httpx.AsyncClient POST to /v1/chat/completions with stream:false, parse response.json()['choices'][0]['message']['content']"
  - "3-strategy JSON parsing: direct json.loads → markdown code block extraction → brace boundary extraction → parse_error"
  - "Pydantic request/response models for all AI endpoints with typed fields"
  - "Per-claim graceful degradation: SearchService/SPARQL errors produce empty results for that claim, not request failure"
  - "Test pattern: _build_ai_app() / _build_match_app() with dependency_overrides for mocked services"
observability_surfaces:
  - "GET /api/llm/status — returns {available, provider} for extension feature gating"
  - "logger.debug on every AI request: user email, input sizes, result counts"
  - "logger.warning(exc_info=True) on all failure paths: LLM connectivity, SPARQL, FTS, label resolution"
  - "parse_error field in detect-claims response body surfaces LLM output parsing failures to callers"
  - "HTTP 503 with {error: 'LLM not configured'} on all LLM-dependent endpoints"
  - "GET /.well-known/sempkm includes all 6 AI endpoint paths and ai-insights capability"
drill_down_paths:
  - .gsd/milestones/M028/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M028/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M028/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M028/slices/S01/tasks/T04-SUMMARY.md
duration: 85m (T01:15m + T02:25m + T03:25m + T04:20m)
verification_result: passed
completed_at: 2026-03-20
---

# S01: Backend AI endpoints with Bearer auth

**All 6 AI backend endpoints implemented with dual Bearer+cookie auth, 59 unit tests covering claim extraction, graph matching with contradiction indicators, research gap detection, relationship suggestions, personalized summary, and graceful degradation — ready for extension sidebar consumption in S02**

## What Happened

Built the complete backend AI endpoint surface in a single module (`backend/app/api/ai.py`, 1119 lines) across 4 tasks:

**T01 — AI Router Foundation:** Created the `ai_router` module with two foundational endpoints. `POST /api/llm/stream` is an SSE proxy for OpenAI-compatible chat completions, copied from the existing Settings page streaming pattern but swapped to `get_current_user_or_api` for dual-auth (cookie + Bearer token). `GET /api/llm/status` returns `{available: bool, provider: string|null}` by checking LLMConfigService, enabling S02's extension sidebar to feature-gate AI capabilities. Mounted the router in `main.py` and updated the well-known discovery endpoint with all planned AI paths and `llm-stream`/`ai-insights` capabilities.

**T02 — Claim Detection:** Added `POST /api/ai/detect-claims` accepting page content with URL and title. The prompt instructs the LLM to return JSON with `{claims: [{text, confidence, type}]}` structure. The response parser implements a 3-strategy fallback: direct `json.loads` → markdown code block regex extraction → brace-boundary parsing. Invalid confidence/type values are normalized to defaults rather than rejected, maximizing extraction quality with imperfect LLM compliance. Content is truncated at 4000 chars to manage context windows.

**T03 — Graph Matching with Contradiction Indicators:** Added `POST /api/ai/match-claims`, the most complex endpoint. For each claim: runs FTS via SearchService (limit 20), resolves types via SPARQL VALUES query, fetches confidence for `res:Claim` objects, computes indicators (`corroborates`/`contradicts`/`contested`/`related`), and caps at 5 matches per claim sorted by FTS score. Contradiction detection is bidirectional — both established-vs-speculative and speculative-vs-established map to `contradicts`. Research gap detection finds open `res:ResearchQuestion` objects with keyword overlap (≥2 meaningful words after stop-word filtering) that lack linked evidence.

**T04 — Relationship Suggestions and Summary:** Added the final two endpoints. `POST /api/ai/suggest-relationships` runs SPARQL URL matching + FTS keyword matching (no LLM needed), deduplicates by IRI, and caps at 10 suggestions. `POST /api/ai/summarize` builds a summarization prompt incorporating the user's knowledge graph objects as context, makes a non-streaming LLM call, and returns fallback text on LLM error instead of a 500.

All endpoints share the same patterns: Pydantic request/response models, `get_current_user_or_api` dual-auth, 503 with `{"error": "LLM not configured"}` when LLM unavailable, per-operation graceful degradation, and structured debug logging.

## Verification

All 59 unit tests pass across 4 test files in 1.27s:

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_llm_proxy.py` | 8 | LLM stream SSE format, status endpoint, auth (Bearer + cookie), degradation |
| `test_claim_detection.py` | 12 | Parser (5 strategies), prompt builder (2), endpoint (5: success, 503, 400, 401, LLM error) |
| `test_claim_matching.py` | 22 | Indicator logic (13 branches), endpoint (4: success, empty, no-FTS, no-Research-model), auth, search errors, research gaps (2) |
| `test_ai_endpoints.py` | 17 | Auth enforcement (6 endpoints × 401), degradation (3), suggest-relationships (4), summarize (3), well-known (1) |

Additional verification:
- `python3 -c "import ast; ast.parse(open('backend/app/api/ai.py').read())"` — syntax valid
- `grep` confirms ai_router mounted in main.py (line 18 import, line 566 include)
- `grep` confirms all 6 endpoint paths + 2 capabilities in well-known discovery
- LSP diagnostics: 0 errors on ai.py

## Requirements Advanced

- EXT-22 — POST /api/llm/stream with Bearer token returns SSE stream; proven by 8 unit tests covering auth, streaming format, degradation
- EXT-23 — POST /api/ai/detect-claims returns structured claim JSON with confidence/type; proven by 12 unit tests covering parsing, prompt, endpoint
- EXT-24 — POST /api/ai/match-claims returns FTS matches ranked by relevance, capped at 5 per claim; proven by 22 unit tests
- EXT-25 — Contradiction/corroboration indicators based on confidence-level comparison; proven by 13 indicator logic tests
- EXT-26 — Research question gap detection with keyword overlap analysis; proven by 2 research gap tests + endpoint integration
- EXT-27 — POST /api/ai/suggest-relationships returns URL+FTS-based suggestions; proven by 4 integration tests
- EXT-28 — POST /api/ai/summarize incorporates graph context in LLM prompt; proven by 3 integration tests including graph context verification
- EXT-31 — Graceful degradation: 503 JSON for LLM-dependent endpoints, match-claims works without LLM; proven by 3 degradation tests

## Requirements Validated

- none — contract verification via unit tests advances these requirements; full validation requires S02 extension integration and S03 E2E tests against Docker stack

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T03 produced 22 tests instead of the planned ~14, covering additional edge cases (bidirectional contradiction, empty string confidence, multiple corroboration variants)
- `_extract_keywords()` factored out as a reusable helper from `_find_research_gaps()` — not planned but improves testability
- `pytest-asyncio` had to be installed in the venv at runtime — listed in pyproject.toml dev dependencies but not present in the Docker build

## Known Limitations

- All AI endpoints are tested with mocked LLM and triplestore — no integration test against real services yet (S03 scope)
- Content truncation at 4000 chars may lose context on very long pages — sufficient for v1
- Research gap detection keyword overlap minimum of 2 words may miss single-word topic matches
- FTS-based matching (not embedding-based) means semantic similarity is limited to keyword overlap (D266: deferred to pgvector adoption)

## Follow-ups

- S02 must implement the extension sidebar consuming all 6 endpoints with progressive loading
- S03 must add E2E tests with a mock LLM server to validate full integration against Docker stack
- S03 should validate claim extraction quality on real page content (news articles, Wikipedia, blog posts)

## Files Created/Modified

- `backend/app/api/ai.py` — new module (1119 lines): ai_router with all 6 endpoints, Pydantic models, prompt builders, response parsers, indicator logic, research gap detection
- `backend/app/main.py` — mounted ai_router (2 lines: import + include_router)
- `backend/app/api/router.py` — updated well-known with 6 AI endpoint paths + 2 capabilities
- `backend/tests/test_llm_proxy.py` — new (339 lines): 8 tests for LLM stream and status
- `backend/tests/test_claim_detection.py` — new (419 lines): 12 tests for claim extraction parsing and endpoint
- `backend/tests/test_claim_matching.py` — new (557 lines): 22 tests for graph matching, indicators, research gaps
- `backend/tests/test_ai_endpoints.py` — new (666 lines): 17 integration tests for all endpoints

## Forward Intelligence

### What the next slice should know
- All 6 endpoints accept and return the exact Pydantic schemas documented in the S01 boundary map — no deviations from the planned contract
- `GET /api/llm/status` is the feature gate: call it first, show "AI features require LLM configuration" if `available: false`
- `suggest-relationships` is the only endpoint that works without LLM — it can show results even when LLM is unconfigured
- The progressive loading pattern should be: status check → detect-claims → match-claims → suggest-relationships → summarize (each section renders as its call completes)
- Bearer auth on all endpoints uses the same API token infrastructure from M013/M014 — no new auth setup needed

### What's fragile
- `_parse_claims_response()` relies on LLM output being valid JSON or at least containing a JSON block — creative LLM responses (explanations, preambles) may produce `parse_error` results; the 3-strategy parser handles most cases but isn't bulletproof
- `_compute_indicator()` depends on the Research model's confidence vocabulary (`established`, `likely`, `possible`, `speculative`, `contested`) — if a model changes these values, indicators may default to `related` instead of typed indicators
- Research gap detection requires keyword overlap of ≥2 meaningful words — short research question titles may never match

### Authoritative diagnostics
- `GET /api/llm/status` — single source of truth for LLM availability; check this before any AI feature attempt
- `parse_error` field in detect-claims response — non-null means LLM returned unparseable output; the raw error message helps debug prompt issues
- `logger.warning` messages with `exc_info=True` — every failure path (LLM, SPARQL, FTS, label resolution) logs the full exception chain

### What assumptions changed
- No assumptions changed — all planned endpoints were implemented exactly as specified in the boundary map
- The test count exceeded estimates (59 vs. ~40 planned) due to additional edge cases discovered during development
