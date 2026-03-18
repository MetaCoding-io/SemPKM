---
estimated_steps: 3
estimated_files: 1
---

# T02: Unit tests for context-query endpoint

**Slice:** S03 — Context-Query, E2E Tests, and User Guide
**Milestone:** M013

## Description

Add unit tests for the context-query endpoint covering URL matching, keyword matching, empty results, validation, and result deduplication.

## Steps

1. Add tests to `backend/tests/test_api_surface.py`:
   - `test_context_query_url_match` — mock triplestore returns matching IRIs for URL, response has match_type "url"
   - `test_context_query_keyword_match` — mock SearchService returns FTS results, response has match_type "keyword"
   - `test_context_query_empty_results` — no matches returns `{results: [], total: 0}`
   - `test_context_query_requires_field` — empty body `{}` returns 400
   - `test_context_query_requires_auth` — no credentials returns 401
   - `test_context_query_deduplicates` — same IRI from both URL + keyword match appears only once
2. Mock TriplestoreClient.query() and SearchService with predetermined return data
3. Run full test suite: `python -m pytest tests/ --tb=short -q`

## Must-Haves

- [ ] ≥6 tests covering all context-query code paths
- [ ] Mocks use realistic triplestore response shapes
- [ ] No regressions in existing test suite

## Verification

- `cd backend && python -m pytest tests/test_api_surface.py -v -k "context_query"` — all green

## Inputs

- `backend/app/api/router.py` — context-query endpoint from T01
- `backend/tests/test_api_surface.py` — existing test file from S01/S02

## Observability Impact

- **Signals changed**: None — tests don't alter runtime behavior
- **Inspection**: Test names in `pytest -v -k context_query` output confirm each code path is exercised (URL match, keyword match, dedup, validation, auth, type enrichment, graceful degradation)
- **Failure visibility**: `pytest` exit code and per-test PASS/FAIL status; CI regression detection via test count assertion

## Expected Output

- `backend/tests/test_api_surface.py` — expanded with ≥6 context-query tests
