# S03: Context-Query, E2E Tests, and User Guide

**Goal:** Ship the `POST /api/context-query` endpoint (find related objects by URL and keywords), add Playwright E2E tests for all four API endpoints, and write user guide documentation for the API surface.
**Demo:** `POST /api/context-query {"url": "https://example.com"}` returns related objects. E2E tests pass against Docker stack. User guide chapter documents all endpoints with request/response examples.

## Must-Haves

- `POST /api/context-query` accepts JSON with `url`, `title`, `keywords` fields (all optional)
- URL matching: SPARQL query finds objects with matching property values (exact URL match via FILTER)
- Keyword matching: FTS via SearchService for title/keywords (leverages existing LuceneSail)
- Results include object IRI, label, type, type label, matched field, relevance indicator
- Pydantic request/response models
- Empty results return empty array, not error
- Playwright E2E test exercising all four M013 endpoints through Docker
- User guide page in `docs/guide/` documenting the API surface

## Verification

- `cd backend && python -m pytest tests/test_api_surface.py -v -k "context_query"` — unit tests pass
- `curl -X POST http://localhost:3000/api/context-query -H "Content-Type: application/json" -d '{"url":"https://example.com"}'` — returns JSON results array (possibly empty if no matching data)
- `curl -X POST http://localhost:3000/api/context-query -H "Content-Type: application/json" -d '{"keywords":"project"}'` — returns objects with "project" in text
- E2E tests: `cd e2e && npx playwright test tests/30-api-surface/ --project=chromium` — passes
- `docs/guide/31-api-surface.md` exists with endpoint documentation

## Observability / Diagnostics

- Runtime signals: context-query returns `match_type` per result indicating how it matched (url, keyword, title)
- Inspection surfaces: `/api/context-query` response includes result count and match details
- Failure visibility: SPARQL query errors logged at WARNING, returned as 500 with sanitized message
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `get_current_user_or_api` from S01, CORS/nginx config from S01, type metadata patterns from S02
- New wiring introduced in this slice: context-query endpoint wires SearchService + TriplestoreClient + LabelService together for the first time in a single query flow
- What remains before the milestone is truly usable end-to-end: nothing — this slice completes the milestone

## Tasks

- [ ] **T01: Implement POST /api/context-query endpoint** `est:1h`
  - Why: The context-query endpoint is the only genuinely new logic in M013 — it combines URL matching via SPARQL with keyword matching via SearchService (FTS/LuceneSail) and aggregates results. Everything else was serialization of existing service output.
  - Files: `backend/app/api/router.py`
  - Do:
    1. Define Pydantic request model `ContextQueryRequest`: `url: str | None = None`, `title: str | None = None`, `keywords: str | None = None`
    2. Define Pydantic response models: `ContextResult(iri: str, label: str, type_iri: str, type_label: str, match_type: str, snippet: str | None)`, `ContextQueryResponse(results: list[ContextResult], total: int)`
    3. Implement `POST /api/context-query` on `api_surface_router`:
       - Validate at least one of url/title/keywords is provided, else return 400
       - **URL matching**: Build SPARQL query that finds objects with any property value matching the URL — `SELECT DISTINCT ?s WHERE { GRAPH <urn:sempkm:current> { ?s ?p ?url . FILTER(STR(?url) = "{escaped_url}") } }` limited to 20 results
       - **Keyword matching**: If title or keywords provided, use `request.app.state.search_service` to run FTS search (existing `search_references` function pattern) with the combined text
       - **Merge results**: deduplicate by IRI, label via LabelService, type via ShapesService
       - **Enrich**: For each result, resolve label from LabelService, type from SPARQL `?s rdf:type ?type`, type label from ShapesService types
    4. Protect with `Depends(get_current_user_or_api)`
    5. Handle empty results gracefully (return `{results: [], total: 0}`)
  - Verify: `python -m pytest tests/test_api_surface.py -v -k "context_query"`
  - Done when: Endpoint returns merged, deduplicated results from URL + keyword matching

- [ ] **T02: Unit tests for context-query endpoint** `est:30m`
  - Why: Verify query building, result merging, and edge cases (no matches, URL-only, keywords-only, both, empty request body).
  - Files: `backend/tests/test_api_surface.py`
  - Do:
    1. Test context-query:
       - `test_context_query_url_match` — URL matching returns results with match_type "url"
       - `test_context_query_keyword_match` — keyword matching returns results with match_type "keyword"
       - `test_context_query_empty_results` — no matches returns empty array
       - `test_context_query_requires_field` — empty request body returns 400
       - `test_context_query_requires_auth` — no credentials → 401
       - `test_context_query_deduplicates` — same IRI from URL + keyword match appears once
    2. Mock TriplestoreClient and SearchService with known return data
  - Verify: `cd backend && python -m pytest tests/test_api_surface.py -v -k "context_query"` — all green
  - Done when: ≥6 tests covering all context-query paths

- [ ] **T03: E2E Playwright test for API surface** `est:45m`
  - Why: Standing requirement — all user-visible behavior needs Playwright tests. The API endpoints are the user-visible surface for external clients. Tests prove the full pipeline (nginx → FastAPI → triplestore) works with real data.
  - Files: `e2e/tests/30-api-surface/api-surface.spec.ts`
  - Do:
    1. Create `e2e/tests/30-api-surface/api-surface.spec.ts`
    2. Test setup: authenticate via existing auth fixture to get session cookie
    3. Test 1: `GET /.well-known/sempkm` — verify response has version, endpoints, capabilities keys
    4. Test 2: `GET /api/types` — verify response has types array with ≥1 entry, each with iri and label
    5. Test 3: `GET /api/shapes/{type_iri}` — use a known type IRI from test 2, verify response has properties array
    6. Test 4: `GET /api/shapes/urn:nonexistent:Type` — verify 404 response
    7. Test 5: `POST /api/context-query` with keywords — verify response has results array (may be empty)
    8. Use `request.newContext()` / `page.request` API for direct HTTP calls (not browser navigation)
  - Verify: `cd e2e && npx playwright test tests/30-api-surface/ --project=chromium`
  - Done when: ≥5 E2E tests pass against running Docker stack

- [ ] **T04: User guide documentation** `est:30m`
  - Why: Standing requirement — user-visible features need guide documentation. The API surface is the integration point for extension developers and third-party clients.
  - Files: `docs/guide/31-api-surface.md`, `docs/guide/README.md`, `docs/guide/appendix-d-glossary.md`
  - Do:
    1. Create `docs/guide/31-api-surface.md` with sections:
       - Overview: what the API surface is for, authentication methods
       - Instance Discovery (`/.well-known/sempkm`): request/response examples
       - Available Types (`GET /api/types`): request/response examples, field descriptions
       - SHACL Shapes (`GET /api/shapes/{type_iri}`): request/response examples, property field descriptions
       - Context Query (`POST /api/context-query`): request body, response format, matching behavior
       - Authentication: session cookies vs Bearer tokens, how to get an API key
       - CORS: browser extension usage notes
    2. Update `docs/guide/README.md` to include Chapter 31 in table of contents
    3. Update navigation footer on preceding chapter (Chapter 30) to link to Chapter 31
    4. Add glossary entries: "API Surface", "Context Query", "Instance Discovery"
  - Verify: `ls docs/guide/31-api-surface.md` exists; `grep "31" docs/guide/README.md` shows entry
  - Done when: Complete guide page with all four endpoints documented, linked in TOC

## Files Likely Touched

- `backend/app/api/router.py` — context-query endpoint
- `backend/tests/test_api_surface.py` — context-query unit tests
- `e2e/tests/30-api-surface/api-surface.spec.ts` — E2E tests
- `docs/guide/31-api-surface.md` — user guide
- `docs/guide/README.md` — TOC update
- `docs/guide/30-personas.md` — navigation footer update
- `docs/guide/appendix-d-glossary.md` — glossary entries
