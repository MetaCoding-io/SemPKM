---
id: S03
parent: M013
milestone: M013
provides:
  - POST /api/context-query endpoint with URL matching (SPARQL) + keyword matching (FTS/LuceneSail), deduplication, and type/label enrichment
  - 7 Playwright E2E tests covering all four M013 API endpoints through the full Docker stack
  - User guide Chapter 31 documenting the API surface with request/response examples, auth, CORS, and error handling
  - 18 context-query unit tests (13 endpoint + 5 SPARQL escape helper)
requires:
  - slice: S01
    provides: get_current_user_or_api dependency, CORS headers, nginx Authorization forwarding
  - slice: S02
    provides: GET /api/types, GET /api/shapes/{type_iri}, Pydantic response models for type metadata
affects: []
key_files:
  - backend/app/api/router.py
  - backend/tests/test_api_surface.py
  - e2e/tests/30-api-surface/api-surface.spec.ts
  - docs/guide/31-api-surface.md
  - docs/guide/README.md
  - docs/guide/30-personas.md
  - docs/guide/appendix-d-glossary.md
key_decisions:
  - URL match_type wins over keyword when same IRI appears in both result sets (first-match-wins dedup)
  - match_type is "title" when only title is provided without keywords, "keyword" otherwise
  - CORS documented as reverse-proxy configuration (nginx) rather than built-in middleware, matching actual architecture
patterns_established:
  - Context-query uses dict[iri, match_type] for dedup across URL and FTS result sets
  - Graceful degradation: each stage (URL match, keyword match, label resolve, type resolve) catches exceptions independently and logs at WARNING
  - API-only E2E tests use ownerRequest fixture for session-authenticated HTTP calls without browser navigation
  - Chain tests (shapes test fetches real type IRI from types endpoint) to avoid hardcoded seed-data dependencies
  - Guide chapters follow navigation chain pattern: previous footer → next, README TOC lists all, glossary cross-references chapter numbers
observability_surfaces:
  - POST /api/context-query response includes match_type per result and total count
  - Empty body → 400 with "At least one of url, title, or keywords is required"
  - SPARQL/FTS errors logged at WARNING with exc_info, gracefully degraded (not 500)
drill_down_paths:
  - .gsd/milestones/M013/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M013/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M013/slices/S03/tasks/T03-SUMMARY.md
  - .gsd/milestones/M013/slices/S03/tasks/T04-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-17
---

# S03: Context-Query, E2E Tests, and User Guide

**Shipped the context-query endpoint, 7 E2E tests for all four API endpoints, 18 context-query unit tests, and Chapter 31 user guide — completing M013's API surface for external clients**

## What Happened

This slice delivered the final three deliverables of M013: the context-query endpoint, E2E test coverage, and user guide documentation.

**T01 — Context-query endpoint:** Added `POST /api/context-query` to `api_surface_router` in `backend/app/api/router.py`. The endpoint accepts `{url, title, keywords}` (all optional, at least one required) and runs two matching strategies: (1) URL matching via SPARQL `FILTER(STR(?val) = "...")` against all property values in the current graph, and (2) keyword/title matching via `SearchService.search()` (LuceneSail FTS). Results are merged into a `dict[iri → match_type]` for deduplication (URL matches take precedence), then enriched with labels via `LabelService.resolve_batch()` and types via a SPARQL `?s a ?type` VALUES query. Each enrichment stage catches exceptions independently — the endpoint degrades gracefully rather than returning 500. Nine unit tests were included in T01 covering URL match, keyword match, title match, empty results, validation (400), auth (401), deduplication, type enrichment, and Bearer token auth.

**T02 — Extended unit tests:** Added 4 graceful degradation tests (SPARQL failure, FTS failure, label resolution failure, type resolution failure) and 5 SPARQL escape helper tests (`TestSparqlEscapeStr`) for injection prevention in the URL matching query. Total: 18 context-query-related tests, 62 across the full API surface test file.

**T03 — E2E Playwright tests:** Created `e2e/tests/30-api-surface/api-surface.spec.ts` with 7 tests exercising all four M013 endpoints through the full Docker Compose stack. Tests use the `ownerRequest` fixture for authenticated HTTP calls and `anonApi` for auth-gate verification. The shapes test chains off the types endpoint (fetches a real type IRI) to avoid hardcoded seed-data dependencies. All 7 pass in ~1.6s.

**T04 — User guide:** Created `docs/guide/31-api-surface.md` with full documentation of all four endpoints including purpose, curl examples, JSON response examples, and field description tables. Sections cover authentication (session cookies vs Bearer tokens), CORS (reverse proxy configuration), and standard error responses. Updated README TOC, Chapter 30 navigation footer, and added three glossary entries (API Surface, Context Query, Instance Discovery).

## Verification

- `cd backend && .venv/bin/pytest tests/test_api_surface.py -v` — 62 passed (0 failures)
- `cd backend && .venv/bin/pytest tests/test_api_surface.py -v -k "context_query"` — 13 passed
- `cd e2e && npx playwright test tests/30-api-surface/ --project=chromium` — 7 passed in 1.6s
- `docs/guide/31-api-surface.md` exists with all four endpoint sections
- `grep "31" docs/guide/README.md` — Chapter 31 in TOC
- `grep "API Surface\|Context Query\|Instance Discovery" docs/guide/appendix-d-glossary.md` — 3 entries present
- Navigation chain verified: Ch30 → Ch31 → Appendix A

## Requirements Advanced

- API-04 — Context-query endpoint implemented with URL + keyword matching, deduplication, type enrichment, and 18 unit tests + 7 E2E tests
- API-08 — User guide Chapter 31 documents all four endpoints with request/response examples, authentication methods, CORS guidance, and glossary entries

## Requirements Validated

- API-04 — `POST /api/context-query` accepts JSON with url/title/keywords, returns deduplicated results with IRI, label, type, match_type, snippet. 13 context-query unit tests + 5 SPARQL escape tests + 2 E2E tests (keyword match + validation) prove success paths, error cases, graceful degradation, and auth enforcement.
- API-08 — `docs/guide/31-api-surface.md` documents all four endpoints with request/response examples, authentication methods, CORS behavior, and error responses. Linked in README TOC and glossary with 3 cross-referenced entries.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T02 added 9 tests beyond the plan's minimum 6 — 4 graceful degradation tests and 5 SPARQL escape helper tests. These exercise the independent exception-catching pattern and injection prevention without meaningful added cost.
- T03 delivered 7 E2E tests instead of the minimum 5 — the extra auth-gate and validation tests are cheap to run and verify important edge cases.
- T04 documented CORS as reverse-proxy configuration rather than built-in middleware, which is more accurate to the actual architecture (no CORSMiddleware in backend).

## Known Limitations

- Context-query v1 searches literal values only — no edge traversal (finding objects linked to matching objects). This is by design per D162.
- FTS keyword matching depends on LuceneSail indexing — results may lag behind recent writes if the index hasn't been updated.
- Context-query results don't include a relevance score for keyword matches — the FTS engine returns matches but the endpoint doesn't surface ranking.

## Follow-ups

- none — this slice completes M013. All four API endpoints are shipped with unit tests, E2E tests, and documentation.

## Files Created/Modified

- `backend/app/api/router.py` — Added ContextQueryRequest/ContextResult/ContextQueryResponse models and POST /api/context-query endpoint
- `backend/tests/test_api_surface.py` — Added 18 tests (13 context-query endpoint + 5 SPARQL escape helper)
- `e2e/tests/30-api-surface/api-surface.spec.ts` — 7 E2E tests for all M013 API endpoints
- `docs/guide/31-api-surface.md` — Chapter 31 documenting the full API surface
- `docs/guide/README.md` — Added Chapter 31 to table of contents
- `docs/guide/30-personas.md` — Updated navigation footer to link to Chapter 31
- `docs/guide/appendix-d-glossary.md` — Added API Surface, Context Query, Instance Discovery entries

## Forward Intelligence

### What the next slice should know
- M013 is complete. The API surface (`/.well-known/sempkm`, `/api/types`, `/api/shapes/{type_iri}`, `/api/context-query`) is the integration contract for the browser extension (M015). All four endpoints require authentication (cookie or Bearer token) and return JSON with CORS headers via nginx.

### What's fragile
- The context-query SPARQL URL matching uses string interpolation with `_sparql_escape_str()` for the URL value. While escaping is tested (5 tests), extremely long URLs or URLs with unusual Unicode could potentially cause issues in the SPARQL engine.
- FTS keyword matching depends on `search_service` being available on `app.state` — if SearchService initialization fails at startup, the keyword matching path silently degrades.

### Authoritative diagnostics
- `cd backend && .venv/bin/pytest tests/test_api_surface.py -v` — 62 tests covering all four endpoints, auth dependency, and edge cases. This is the single most trustworthy signal for the API surface.
- `cd e2e && npx playwright test tests/30-api-surface/ --project=chromium` — 7 E2E tests proving the full stack (nginx → FastAPI → triplestore) works with real auth.

### What assumptions changed
- CORS was assumed to be `Access-Control-Allow-Origin: *` as a built-in feature — actually it's configured at the nginx reverse proxy layer. The user guide documents this accurately.
