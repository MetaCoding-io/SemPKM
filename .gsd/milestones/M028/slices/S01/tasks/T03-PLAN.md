---
estimated_steps: 7
estimated_files: 3
---

# T03: Add claim-to-graph matching endpoint with contradiction indicators

**Slice:** S01 — Backend AI endpoints with Bearer auth
**Milestone:** M028

## Description

Add `POST /api/ai/match-claims` to the AI router. This is the most complex endpoint in S01 — it takes an array of detected claims, queries the knowledge graph via SPARQL/FTS for matching objects (Claims, Evidence, ResearchQuestions, Notes, Concepts), computes contradiction/corroboration indicators by comparing confidence levels, and detects research question gaps.

**Key design decisions (from D266):**
- Use FTS keyword search via LuceneSail, not embeddings
- Rank by FTS relevance score, cap at 5 matches per claim
- Degrade gracefully when Research model is not installed (match against all types, not just research-specific)

**Research model schema (from `models/research/`):**
- `res:Claim` has `res:confidence` with values: `established`, `supported`, `contested`, `speculative`, `refuted`
- `res:Evidence` has `res:evidenceType` (empirical-data, statistical-finding, etc.) and `res:strength` (strong, moderate, weak, etc.)
- `res:ResearchQuestion` has `res:status` with values: `open`, `partially-answered`, `answered`, `abandoned`
- Type IRIs use prefix `urn:sempkm:model:research:` (e.g., `urn:sempkm:model:research:Claim`)

**Existing patterns to reuse:**
- `SearchService.search()` in `backend/app/services/search.py` — FTS via LuceneSail, returns `SearchResult(iri, type, label, snippet, score)`
- Context-query SPARQL patterns in `backend/app/api/router.py` — type resolution, label resolution via label_service

**Relevant skill:** `test` — for generating pytest unit tests.

## Steps

1. In `backend/app/api/ai.py`, add Pydantic models:
   ```python
   class ClaimInput(BaseModel):
       text: str
       confidence: str = "possible"
       type: str = "factual"

   class MatchClaimsRequest(BaseModel):
       claims: list[ClaimInput]

   class MatchedObject(BaseModel):
       iri: str
       label: str
       type_iri: str | None = None
       type_label: str | None = None
       match_type: str  # "fts" | "url" | "exact"
       indicator: str | None = None  # "contradicts" | "corroborates" | "contested" | "related"
       confidence: str | None = None  # existing object's confidence level
       fts_score: float | None = None

   class ClaimMatch(BaseModel):
       claim_text: str
       matched_objects: list[MatchedObject] = []

   class ResearchGap(BaseModel):
       iri: str
       label: str
       question_text: str | None = None
       status: str | None = None

   class MatchClaimsResponse(BaseModel):
       matches: list[ClaimMatch] = []
       research_gaps: list[ResearchGap] = []
   ```

2. Create helper function `_compute_indicator(detected_confidence: str, existing_confidence: str | None, existing_type_iri: str | None) -> str`:
   - If existing object is a `res:Claim`:
     - If existing confidence is "established"/"supported" and detected confidence is "speculative"/"possible" → "contradicts" (different confidence direction suggests disagreement)
     - If both are "established"/"supported"/"likely" → "corroborates"
     - If existing is "contested" → "contested"
     - Otherwise → "related"
   - If existing object is a `res:Evidence` → "related" (evidence doesn't contradict, it supports or refutes)
   - Otherwise → "related"

3. Create helper function `async def _find_research_gaps(triplestore, label_service, claim_texts: list[str]) -> list[ResearchGap]`:
   - Query SPARQL for all `res:ResearchQuestion` objects with status "open" or "partially-answered"
   - For each, get the `dcterms:title` and `res:description`
   - Check if any claim text has keyword overlap with the research question (simple word intersection, threshold ≥ 2 shared meaningful words)
   - For matching RQs, check if there's any `res:Evidence` linked to them — if not, it's a gap
   - Return gaps capped at 5

4. Add `POST /ai/match-claims` endpoint:
   - Depends on `get_current_user_or_api` (no db session needed — uses triplestore + search service from app.state)
   - Validate claims list is not empty (400 if empty)
   - For each claim:
     a. Run `search_service.search(claim.text, limit=20)` for FTS matches
     b. For each FTS result, resolve its type via SPARQL (`?iri a ?type` in `urn:sempkm:current`)
     c. For matches that are `res:Claim` type, fetch their `res:confidence` via SPARQL
     d. Compute indicator via `_compute_indicator()`
     e. Resolve labels via `label_service.resolve_batch()`
     f. Cap at 5 matches per claim, sorted by FTS score descending
   - Run `_find_research_gaps()` across all claim texts
   - Return `MatchClaimsResponse`
   - Handle SearchService/triplestore errors gracefully (log warning, return partial results)

5. Handle Research model not installed: The FTS search returns all types. The indicator logic checks `type_iri` — if it doesn't match `urn:sempkm:model:research:Claim`, the indicator defaults to "related". Research gaps query checks for `urn:sempkm:model:research:ResearchQuestion` — if no results, return empty gaps list. No errors thrown.

6. Write `backend/tests/test_claim_matching.py` with tests:
   - `test_compute_indicator_corroborates` — both established → "corroborates"
   - `test_compute_indicator_contradicts` — established vs speculative → "contradicts"
   - `test_compute_indicator_contested` — existing contested → "contested"
   - `test_compute_indicator_non_claim_type` — Evidence type → "related"
   - `test_compute_indicator_no_confidence` — missing confidence → "related"
   - `test_match_claims_success` — mock search service + triplestore returning matches → correct response structure
   - `test_match_claims_caps_at_five` — 20 FTS results → only 5 per claim in response
   - `test_match_claims_empty_claims` — empty claims list → 400
   - `test_match_claims_no_fts_results` — search returns empty → empty matches
   - `test_match_claims_research_model_not_installed` — no RQ type in graph → empty research_gaps, no error
   - `test_match_claims_requires_auth` — no auth → 401
   - `test_match_claims_search_service_error` — search throws → graceful degradation, partial results
   - `test_find_research_gaps_with_matches` — mock RQ objects + claim overlap → gaps returned
   - `test_find_research_gaps_no_overlap` — no keyword overlap → empty gaps

7. Run tests: `cd backend && python -m pytest tests/test_claim_matching.py -v`

## Must-Haves

- [ ] `POST /api/ai/match-claims` accepts claim array and returns matches with indicators
- [ ] FTS search via SearchService for each claim text
- [ ] Contradiction/corroboration indicators computed from confidence level comparison
- [ ] Research question gap detection for open/partially-answered questions lacking evidence
- [ ] Results capped at 5 matches per claim, sorted by FTS score
- [ ] Graceful behavior when Research model not installed (no errors, just fewer typed matches)
- [ ] All unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_claim_matching.py -v` — all 14 tests pass
- Indicator logic tests cover all confidence combinations
- Search service error produces partial results, not 500

## Observability Impact

- **New signals:** `logger.debug` on every `/ai/match-claims` request logs user email, claim count, total matches found, and research gap count. `logger.warning` with `exc_info=True` on SearchService or triplestore failures during matching.
- **Inspection:** Response body `matches[].matched_objects[].indicator` shows contradiction/corroboration status per match. `research_gaps` array shows open research questions with evidence gaps.
- **Failure visibility:** SearchService errors produce partial results (empty matches for that claim) rather than 500. Triplestore SPARQL failures for type/confidence resolution degrade to `indicator: "related"` and `confidence: null`. Missing Research model returns empty `research_gaps` with no error.
- **How to inspect:** `POST /api/ai/match-claims` with `{"claims": [{"text": "test"}]}` — non-empty `matches` array confirms FTS round-trip. Empty `research_gaps` with no error confirms graceful Research model absence.

## Inputs

- `backend/app/api/ai.py` — AI router from T01-T02 (must have ai_router + detect-claims endpoint)
- `backend/app/services/search.py` — SearchService with `search(query, limit)` method returning `SearchResult` objects with `iri`, `type`, `label`, `snippet`, `score` fields
- `backend/app/api/router.py` — context-query endpoint as pattern for type/label resolution SPARQL
- `models/research/manifest.yaml` — Research model namespace `urn:sempkm:model:research:` and type IRIs (Claim, Evidence, ResearchQuestion)
- `models/research/shapes/research.jsonld` — confidence enum values: `established`, `supported`, `contested`, `speculative`, `refuted`

## Expected Output

- `backend/app/api/ai.py` — updated with MatchClaimsRequest/Response models, indicator logic, gap detection, and endpoint
- `backend/tests/test_claim_matching.py` — 14 unit tests all passing
