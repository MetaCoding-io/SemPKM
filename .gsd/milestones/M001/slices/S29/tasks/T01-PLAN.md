# T01: 29-fts-fuzzy-search 01

**Slice:** S29 — **Milestone:** M001

## Description

Implement typo-tolerant fuzzy search in the backend by adding `_normalize_query()` to `SearchService` and exposing a `fuzzy: bool` parameter on the `/api/search` endpoint.

Purpose: Users can find objects despite typos (e.g. "knowlege" finds "knowledge"). Fuzzy mode is opt-in per-request; default is exact search (no change to existing behaviour). Tokens shorter than 5 characters always use exact match to avoid short-token dictionary-scan noise.

Output: Modified `search.py` with `_normalize_query()`, modified `router.py` with `fuzzy` param, optional `sempkm-repo.ttl` with `fuzzyPrefixLength=2`.

## Must-Haves

- [ ] "GET /api/search?q=knowlege&fuzzy=true returns results for 'knowledge' objects"
- [ ] "GET /api/search?q=alice+smith&fuzzy=true fuzzy-expands 'alice' and 'smith' (both >=5 chars) independently"
- [ ] "Short tokens (<5 chars) are NOT fuzzy-expanded even when fuzzy=true (e.g. 'of' stays 'of', not 'of~1')"
- [ ] "GET /api/search?q=hello without fuzzy param behaves identically to before (no behaviour change for existing callers)"
- [ ] "User-typed operator suffixes (~, *, ?) are not double-appended by normalization"

## Files

- `backend/app/services/search.py`
- `backend/app/sparql/router.py`
- `config/rdf4j/sempkm-repo.ttl`
