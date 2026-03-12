# S29: Fts Fuzzy Search

**Goal:** Implement typo-tolerant fuzzy search in the backend by adding `_normalize_query()` to `SearchService` and exposing a `fuzzy: bool` parameter on the `/api/search` endpoint.
**Demo:** Implement typo-tolerant fuzzy search in the backend by adding `_normalize_query()` to `SearchService` and exposing a `fuzzy: bool` parameter on the `/api/search` endpoint.

## Must-Haves


## Tasks

- [x] **T01: 29-fts-fuzzy-search 01** `est:2min`
  - Implement typo-tolerant fuzzy search in the backend by adding `_normalize_query()` to `SearchService` and exposing a `fuzzy: bool` parameter on the `/api/search` endpoint.

Purpose: Users can find objects despite typos (e.g. "knowlege" finds "knowledge"). Fuzzy mode is opt-in per-request; default is exact search (no change to existing behaviour). Tokens shorter than 5 characters always use exact match to avoid short-token dictionary-scan noise.

Output: Modified `search.py` with `_normalize_query()`, modified `router.py` with `fuzzy` param, optional `sempkm-repo.ttl` with `fuzzyPrefixLength=2`.
- [x] **T02: 29-fts-fuzzy-search 02** `est:1min`
  - Add a user-controlled fuzzy toggle command to the Ctrl+K palette (ninja-keys) in `workspace.js`. The toggle persists its state in localStorage and appends `&fuzzy=true` to FTS fetch calls when enabled.

Purpose: FTS-04 requires fuzzy mode to be a user-controlled toggle in the Ctrl+K palette that persists across sessions. The backend fuzzy endpoint (Plan 01) is now live; this plan wires the UI side.

Output: Modified `workspace.js` with a `search-fuzzy-toggle` command in ninja-keys, localStorage persistence under `sempkm_fts_fuzzy`, and updated FTS fetch URL to conditionally include `&fuzzy=true`.

## Files Likely Touched

- `backend/app/services/search.py`
- `backend/app/sparql/router.py`
- `config/rdf4j/sempkm-repo.ttl`
- `frontend/static/js/workspace.js`
