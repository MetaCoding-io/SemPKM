---
id: T03
parent: S01
milestone: M028
provides:
  - "POST /api/ai/match-claims endpoint accepting claim arrays and returning FTS matches with contradiction/corroboration indicators"
  - "_compute_indicator() helper for confidence-level comparison between detected and existing claims"
  - "_find_research_gaps() helper detecting open research questions with keyword overlap but no linked evidence"
  - "Pydantic models: ClaimInput, MatchClaimsRequest, MatchedObject, ClaimMatch, ResearchGap, MatchClaimsResponse"
key_files:
  - backend/app/api/ai.py
  - backend/tests/test_claim_matching.py
key_decisions:
  - "Indicator logic uses bidirectional contradiction — both high-existing/low-detected and low-existing/high-detected map to 'contradicts', since confidence-level divergence is the signal"
  - "Research gap keyword overlap uses a minimum threshold of 2 meaningful words (stop words filtered) — balances false positives vs. coverage"
  - "SearchService errors degrade per-claim (empty matched_objects for that claim) rather than failing the whole request"
  - "_RES_EVIDENCE and _RES_RESEARCH_QUESTION constants defined as module-level API for downstream task reuse (T04)"
patterns_established:
  - "app.state service access pattern for match-claims: triplestore_client, label_service, search_service from request.app.state (no db session needed)"
  - "Test pattern for triplestore-dependent endpoints: _build_match_app() takes mock search_service, triplestore, label_service as constructor params"
  - "SPARQL query sequencing: type resolution → confidence resolution → research gap detection, each with independent try/except for graceful degradation"
observability_surfaces:
  - "logger.debug on every /ai/match-claims request: user email, claim count, total matches, research gap count"
  - "logger.warning with exc_info=True on SearchService errors, SPARQL failures, and research gap detection failures"
  - "Response body indicator field shows contradiction/corroboration status per matched object"
duration: 25min
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T03: Add claim-to-graph matching endpoint with contradiction indicators

**Added POST /api/ai/match-claims with FTS-based graph matching, confidence-level contradiction/corroboration indicators, and research question gap detection — 22 tests passing**

## What Happened

Implemented the full claim-to-graph matching pipeline in `backend/app/api/ai.py`:

1. **Pydantic models** — `ClaimInput`, `MatchClaimsRequest`, `MatchedObject`, `ClaimMatch`, `ResearchGap`, `MatchClaimsResponse` define the request/response contract.

2. **`_compute_indicator()`** — Compares detected claim confidence against existing graph object confidence. Only `res:Claim` objects get typed indicators (`corroborates`, `contradicts`, `contested`); all other types default to `related`. Contradiction is bidirectional: established-vs-speculative and speculative-vs-established both return `contradicts`.

3. **`_find_research_gaps()`** — Queries SPARQL for open/partially-answered `res:ResearchQuestion` objects, computes keyword overlap with claim texts (stop words filtered, minimum 2 shared meaningful words), then checks if matching RQs lack linked evidence. Caps at 5 gaps.

4. **`POST /ai/match-claims` endpoint** — For each claim: runs FTS via SearchService (limit 20), resolves types via SPARQL VALUES query, fetches confidence for `res:Claim` objects, computes indicators, resolves labels via label_service, caps at 5 matches sorted by FTS score. Then runs research gap detection across all claim texts. Each step has independent error handling for graceful degradation.

5. **22 unit tests** covering all indicator logic branches, endpoint success/error/auth/empty paths, result capping, research model absence, search service errors, and research gap detection.

## Verification

All 22 tests in `test_claim_matching.py` pass. All 12 prior tests in `test_claim_detection.py` pass. All 8 prior tests in `test_llm_proxy.py` pass. No regressions.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_claim_matching.py -v` | 0 | ✅ pass | 0.57s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_claim_detection.py -v` | 0 | ✅ pass | 0.71s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_llm_proxy.py -v` | 0 | ✅ pass | 0.71s |
| 4 | `python3 -c "import ast; ast.parse(open('backend/app/api/ai.py').read())"` | 0 | ✅ pass | <1s |

Slice-level checks status (this is task 3 of 4):
- ✅ `test_llm_proxy.py` — all pass
- ✅ `test_claim_detection.py` — all pass
- ✅ `test_claim_matching.py` — all pass
- ⬜ `test_ai_endpoints.py` — not yet created (T04)

## Diagnostics

- **Smoke test:** `POST /api/ai/match-claims` with `{"claims": [{"text": "any text"}]}` — non-empty `matches` array confirms FTS round-trip
- **Indicator inspection:** Each `matched_objects[]` entry has `indicator` field showing `contradicts`/`corroborates`/`contested`/`related`
- **Research gaps:** `research_gaps` array in response body; empty with no error when Research model not installed
- **Failure signals:** `logger.warning` with `exc_info=True` on SearchService, SPARQL, or gap detection failures; partial results returned (not 500)
- **Logs:** `logger.debug` on every request includes user email, claim count, total match count, gap count

## Deviations

- Plan specified 14 named tests; implementation has 22 tests covering additional edge cases (bidirectional contradiction, empty string confidence, multiple corroboration variants, reverse-direction contradicts). All plan-specified test scenarios are covered.
- Added `_extract_keywords()` as a reusable helper function factored out of `_find_research_gaps()` for cleaner keyword overlap logic.

## Known Issues

- Pyright hints that `_RES_EVIDENCE` and `_RES_RESEARCH_QUESTION` are unused in `ai.py` — these are module-level constants exported for test imports and downstream T04 use. Not a real issue.

## Files Created/Modified

- `backend/app/api/ai.py` — Added match-claims endpoint, Pydantic models, indicator computation, research gap detection, keyword extraction helper
- `backend/tests/test_claim_matching.py` — 22 unit tests covering indicator logic, endpoint behavior, auth, error handling, and research gaps
- `.gsd/milestones/M028/slices/S01/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
