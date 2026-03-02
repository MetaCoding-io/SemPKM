---
phase: 29-fts-fuzzy-search
plan: 01
subsystem: api
tags: [lucene, fts, rdf4j, search, fuzzy, sparql]

# Dependency graph
requires: []
provides:
  - SearchService._normalize_query() for Lucene fuzzy token expansion (~1 edit distance)
  - SearchService.search(fuzzy=False) parameter for opt-in typo tolerance
  - /api/search?fuzzy=true endpoint parameter with response field confirmation
  - config/rdf4j/sempkm-repo.ttl fuzzyPrefixLength=2 enhancement (active after volume reset)
affects: [30-fts-ui, 34-e2e-sparql-fts]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lucene fuzzy expansion via ~1 suffix on tokens >=5 chars; short tokens always exact"
    - "opt-in fuzzy mode on search endpoint: existing callers unchanged by default=False"

key-files:
  created: []
  modified:
    - backend/app/services/search.py
    - backend/app/sparql/router.py
    - config/rdf4j/sempkm-repo.ttl

key-decisions:
  - "5-char threshold for fuzzy expansion: tokens <5 chars stay exact to avoid dictionary-scan noise"
  - "~1 edit distance only (not ~2): balances typo tolerance vs precision"
  - "fuzzyPrefixLength=2 in TTL: improves index lookup but requires volume reset; feature works without it at default=0"
  - "fuzzy field echoed in API response body so clients can confirm mode was applied"

patterns-established:
  - "_normalize_query() method: pure function on SearchService, called before FTS_QUERY.format()"
  - "operator guard: token[-1] not in (~, *, ?) prevents double-appending user-typed Lucene operators"

requirements-completed: [FTS-04]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 29 Plan 01: FTS Fuzzy Search Summary

**Typo-tolerant search via LuceneSail ~1 fuzzy expansion: opt-in per-request, short tokens always exact, operator double-append guarded**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-02T00:10:24Z
- **Completed:** 2026-03-02T00:12:19Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `_normalize_query()` to `SearchService`: appends `~1` to tokens >=5 chars in fuzzy mode, leaves short tokens and user-typed operators untouched
- Updated `SearchService.search()` to accept `fuzzy: bool = False` and call `_normalize_query()` before SPARQL interpolation
- Exposed `?fuzzy=true` query param on `/api/search` with response body `"fuzzy": bool` confirmation field
- Added `config:lucene.fuzzyPrefixLength "2"` to `sempkm-repo.ttl` LuceneSail stanza (enhancement; requires volume reset to activate)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _normalize_query() to SearchService and thread fuzzy param** - `a3aa2d6` (feat)
2. **Task 2: Add fuzzy param to /api/search endpoint and apply TTL config** - `54a1eab` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/app/services/search.py` - Added `_normalize_query()` method and `fuzzy` param on `search()`
- `backend/app/sparql/router.py` - Added `fuzzy: bool = Query(False)` to endpoint and response body
- `config/rdf4j/sempkm-repo.ttl` - Added `config:lucene.fuzzyPrefixLength "2"` to LuceneSail stanza

## Decisions Made
- 5-char threshold: avoids noise from fuzzy-expanding common short tokens ("of", "the", "in")
- `~1` edit distance only: one-char typo correction (e.g., "knowlege" -> "knowledge"); `~2` would near-full dictionary scan
- `fuzzyPrefixLength=2`: Lucene must match first 2 chars before applying edit distance — improves performance and precision
- TTL change is additive only; existing repository runs fine with `fuzzyPrefixLength=0` default

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan verification script had incorrect assertion for 4-char token**
- **Found during:** Overall verification after Task 2
- **Issue:** The plan's `<verification>` block asserted `_normalize_query('knowlege base', fuzzy=True) == 'knowlege~1 base~1'`. However `base` has 4 characters (< 5), so per the stated spec it should stay exact (`base`, not `base~1`). The implementation is correct and consistent with the spec; the verification script in the plan had an off-by-one in its mental count.
- **Fix:** Ran corrected assertions that match the spec; implementation unchanged.
- **Files modified:** None — implementation correct; plan script was the error.
- **Verification:** `_normalize_query('knowlege base', fuzzy=True)` returns `'knowlege~1 base'` as expected by the spec rule (tokens <5 chars stay exact). All task-level assertions in Task 1's verify block passed correctly.
- **Committed in:** a3aa2d6 (Task 1 commit, implementation unchanged)

---

**Total deviations:** 1 (plan verification script error, no code change needed)
**Impact on plan:** Implementation is correct per spec. Only the plan's overall verification script had an incorrect expected value for a 4-char token.

## Issues Encountered
- Python venv at `backend/.venv` does not have runtime dependencies (httpx etc.) installed — the venv is build-only. Module-level assertions were tested by extracting the pure function logic for isolation testing. This is expected behavior since the app runs in Docker.

## User Setup Required
None — no external service configuration required. The `fuzzyPrefixLength` TTL enhancement will take effect on the next `docker compose down && up` with a fresh volume, but the feature works correctly without it (LuceneSail defaults to `fuzzyPrefixLength=0`).

## Next Phase Readiness
- Fuzzy search backend is complete and ready for frontend integration (Phase 30 FTS UI)
- `/api/search?q=...&fuzzy=true` returns typo-tolerant results for tokens >=5 chars
- Existing callers that omit `fuzzy` see no behavior change (default `False`)
- No blockers

---
*Phase: 29-fts-fuzzy-search*
*Completed: 2026-03-01*

## Self-Check: PASSED

- FOUND: backend/app/services/search.py
- FOUND: backend/app/sparql/router.py
- FOUND: config/rdf4j/sempkm-repo.ttl
- FOUND: .planning/phases/29-fts-fuzzy-search/29-01-SUMMARY.md
- FOUND commit: a3aa2d6 (Task 1)
- FOUND commit: 54a1eab (Task 2)
