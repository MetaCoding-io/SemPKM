---
estimated_steps: 6
estimated_files: 1
---

# T01: Implement POST /api/context-query endpoint

**Slice:** S03 — Context-Query, E2E Tests, and User Guide
**Milestone:** M013

## Description

Build the context-query endpoint that accepts page metadata (URL, title, keywords) and returns related objects from the knowledge graph. This is the only genuinely new logic in M013 — it combines URL matching via SPARQL with keyword matching via SearchService/FTS and aggregates results.

## Steps

1. Read `backend/app/browser/search.py` to understand how `search_references()` uses SearchService for FTS queries
2. Read `backend/app/services/search.py` to understand the SearchService API (LuceneSail keyword search)
3. Define Pydantic models in `backend/app/api/router.py`:
   - `ContextQueryRequest(url: str | None = None, title: str | None = None, keywords: str | None = None)`
   - `ContextResult(iri: str, label: str, type_iri: str | None, type_label: str | None, match_type: str, snippet: str | None)`
   - `ContextQueryResponse(results: list[ContextResult], total: int)`
4. Implement `POST /api/context-query` on `api_surface_router`:
   - Validate at least one field is provided (else 400)
   - URL matching: SPARQL `SELECT DISTINCT ?s WHERE { GRAPH <urn:sempkm:current> { ?s ?p ?val . FILTER(STR(?val) = "{escaped_url}") } } LIMIT 20`
   - Keyword matching: combine title + keywords into search text, call search_service
   - Merge and deduplicate results by IRI
   - Resolve labels via LabelService.resolve_batch()
   - Resolve types via SPARQL `SELECT ?s ?type WHERE { GRAPH <urn:sempkm:current> { ?s a ?type } }`
5. Handle edge cases: empty results → `{results: [], total: 0}`, SPARQL errors → log warning + skip that result set
6. Protect with `Depends(get_current_user_or_api)`

## Must-Haves

- [ ] URL matching finds objects with any property containing the exact URL
- [ ] Keyword matching uses existing FTS/LuceneSail infrastructure
- [ ] Results are deduplicated when same object matches both URL and keywords
- [ ] Empty results return 200 with empty array (not 404 or error)
- [ ] At least one of url/title/keywords required (400 otherwise)

## Verification

- `cd backend && python -m pytest tests/test_api_surface.py -v -k "context_query"`
- After Docker: `curl -X POST http://localhost:3000/api/context-query -H "Content-Type: application/json" -d '{"keywords":"project"}'`

## Inputs

- `backend/app/api/router.py` — existing router with types/shapes endpoints from S02
- `backend/app/services/search.py` — SearchService for FTS
- `backend/app/browser/search.py` — reference implementation for FTS usage

## Observability Impact

- **New signal:** `POST /api/context-query` response includes `match_type` per result (`url`, `keyword`, or `title`) and `total` count — agents can verify matching behavior from response payload alone.
- **Inspection surface:** Response shape `{results: [...], total: N}` is self-describing; empty results return `{results: [], total: 0}` (not an error).
- **Failure visibility:** SPARQL errors during URL or keyword matching logged at WARNING level with `exc_info=True`; the endpoint degrades gracefully (skips that result set) rather than returning 500.
- **Diagnostic path:** `POST /api/context-query` with empty body → 400 with `"At least one of url, title, or keywords is required"` confirms validation is active.

## Expected Output

- `backend/app/api/router.py` — with `/api/context-query` endpoint and Pydantic models
