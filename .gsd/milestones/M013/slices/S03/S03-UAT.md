# S03: Context-Query, E2E Tests, and User Guide — UAT

**Milestone:** M013
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven for docs, live-runtime for endpoints)
- Why this mode is sufficient: Endpoint behavior verified by 62 unit tests + 7 E2E tests against live Docker stack. Documentation verified by file existence and content checks.

## Preconditions

- Docker test stack running: `docker compose -f docker-compose.test.yml up -d` (port 3901)
- At least one Mental Model installed (basic-pkm) with seed data
- Backend virtualenv available: `cd backend && source .venv/bin/activate`
- E2E test dependencies installed: `cd e2e && npm install`

## Smoke Test

```bash
curl -s -X POST http://localhost:3901/api/context-query \
  -H "Content-Type: application/json" \
  -d '{"keywords":"project"}' | python3 -m json.tool
```
Should return JSON with `results` array and `total` integer (results may be empty if no matching seed data, but response structure must be correct). Returns 401 if unauthenticated — that's expected, use a session cookie for full verification.

## Test Cases

### 1. Context-query with URL matching

1. Identify a URL that exists as a property value in the triplestore (e.g., check a Note or Project object's properties)
2. `POST /api/context-query` with `{"url": "<that-url>"}` using a valid session cookie
3. **Expected:** 200 response with `results` array containing at least one entry where `match_type` is `"url"`, each result has `iri`, `label`, `type_iri`, `type_label`, and `snippet` fields

### 2. Context-query with keyword matching

1. `POST /api/context-query` with `{"keywords": "project"}` using a valid session cookie
2. **Expected:** 200 response with `results` array (may be empty if no FTS matches), `total` count matches array length. If results are present, each has `match_type` `"keyword"`.

### 3. Context-query with title matching

1. `POST /api/context-query` with `{"title": "Note"}` using a valid session cookie
2. **Expected:** 200 response with `results` array. Results have `match_type` `"title"`. Title-only queries route through the same FTS path as keywords.

### 4. Context-query validation — empty body

1. `POST /api/context-query` with `{}` using a valid session cookie
2. **Expected:** 400 response with `detail` containing "At least one of url, title, or keywords is required"

### 5. Context-query auth enforcement

1. `POST /api/context-query` with `{"keywords": "test"}` and NO session cookie or Bearer token
2. **Expected:** 401 response (JSON, not a 302 redirect)

### 6. E2E test suite passes

1. `cd e2e && npx playwright test tests/30-api-surface/ --project=chromium`
2. **Expected:** 7 tests pass — well-known discovery, auth gate, types listing, shapes retrieval, shapes 404, keyword search, empty body validation

### 7. Unit test suite passes

1. `cd backend && .venv/bin/pytest tests/test_api_surface.py -v`
2. **Expected:** 62 tests pass (10 well-known + 8 types + 11 shapes + 15 dual-auth + 13 context-query + 5 SPARQL escape)

### 8. User guide Chapter 31 completeness

1. Open `docs/guide/31-api-surface.md`
2. **Expected:** Contains sections for all four endpoints:
   - Instance Discovery (`GET /.well-known/sempkm`)
   - Available Types (`GET /api/types`)
   - SHACL Shapes (`GET /api/shapes/{type_iri}`)
   - Context Query (`POST /api/context-query`)
3. Each section has example curl request and example JSON response
4. Authentication section covers both session cookies and Bearer tokens
5. CORS section documents reverse proxy configuration

### 9. Guide navigation chain

1. Check `docs/guide/README.md` — Chapter 31 listed in TOC
2. Check `docs/guide/30-personas.md` — footer links to Chapter 31
3. Check `docs/guide/31-api-surface.md` — footer links to Appendix A
4. **Expected:** All three navigation links present and pointing to correct files

### 10. Glossary entries

1. Open `docs/guide/appendix-d-glossary.md`
2. **Expected:** Contains entries for "API Surface", "Context Query", and "Instance Discovery" with cross-references to Chapter 31

## Edge Cases

### Empty results for valid query

1. `POST /api/context-query` with `{"url": "https://definitely-not-in-the-graph.example.com"}` using valid auth
2. **Expected:** 200 with `{"results": [], "total": 0}` — not 404 or error

### Context-query with all three fields

1. `POST /api/context-query` with `{"url": "https://example.com", "title": "Test", "keywords": "project"}` using valid auth
2. **Expected:** 200 response with deduplicated results. Same IRI should not appear twice.

### Shapes endpoint — nonexistent type

1. `GET /api/shapes/urn:nonexistent:FakeType` using valid auth
2. **Expected:** 404 with detail message about type not found

### Bearer token authentication on context-query

1. `POST /api/context-query` with `{"keywords": "test"}` using `Authorization: Bearer <valid-api-token>` header (no cookie)
2. **Expected:** 200 response — Bearer auth accepted on all API endpoints

## Failure Signals

- Any test returning non-200 for valid authenticated requests → auth dependency broken
- Context-query returning 500 instead of degraded results → graceful degradation pattern not working
- Empty body returning 200 instead of 400 → validation not enforced
- E2E tests timing out → Docker stack not running or nginx misconfigured
- Guide file missing or not in README TOC → documentation task incomplete
- Glossary entries missing → cross-referencing not done

## Requirements Proved By This UAT

- API-04 — Context-query endpoint with URL matching, keyword matching, deduplication (tests 1-5, edge cases)
- API-08 — User guide documents all four endpoints (tests 8-10)

## Not Proven By This UAT

- Context-query performance under large triplestore datasets — unit tests use mocked data
- FTS ranking accuracy — results are returned but scoring quality not assessed
- Edge traversal for context-query — intentionally deferred per D162

## Notes for Tester

- The context-query endpoint's keyword matching depends on LuceneSail FTS indexing. If the test stack was just started, the index may not have all seed data yet — give it 30 seconds after startup.
- The E2E tests (test case 6) require the Docker test stack on port 3901. Run `docker compose -f docker-compose.test.yml up -d` and wait for healthy status before running.
- Context-query URL matching searches ALL property values in `urn:sempkm:current`, not just specific URL-type properties. This is intentional — any property containing a matching string value is found.
