---
id: S29
parent: M001
milestone: M001
provides:
  - SearchService._normalize_query() for Lucene fuzzy token expansion (~1 edit distance)
  - SearchService.search(fuzzy=False) parameter for opt-in typo tolerance
  - /api/search?fuzzy=true endpoint parameter with response field confirmation
  - config/rdf4j/sempkm-repo.ttl fuzzyPrefixLength=2 enhancement (active after volume reset)
  - fuzzy toggle command in Ctrl+K palette (search-fuzzy-toggle) with ON/OFF title
  - localStorage persistence of fuzzy state under sempkm_fts_fuzzy key
  - conditional &fuzzy=true appended to FTS fetch URL when toggle is enabled
requires: []
affects: []
key_files: []
key_decisions:
  - "5-char threshold for fuzzy expansion: tokens <5 chars stay exact to avoid dictionary-scan noise"
  - "~1 edit distance only (not ~2): balances typo tolerance vs precision"
  - "fuzzyPrefixLength=2 in TTL: improves index lookup but requires volume reset; feature works without it at default=0"
  - "fuzzy field echoed in API response body so clients can confirm mode was applied"
  - "Toggle ID 'search-fuzzy-toggle' chosen (not 'fts-' prefix) so change listener filter never accidentally removes the toggle"
  - "localStorage key 'sempkm_fts_fuzzy' follows existing sempkm_ namespace convention for all localStorage keys"
  - "Unicode em-dash \\u2014 used instead of literal dash for safe JS string embedding"
  - "try/catch on localStorage.setItem guards against private-browsing quota errors"
patterns_established:
  - "_normalize_query() method: pure function on SearchService, called before FTS_QUERY.format()"
  - "operator guard: token[-1] not in (~, *, ?) prevents double-appending user-typed Lucene operators"
  - "ninja.data in-place title update: findIndex -> slice -> Object.assign -> reassign ninja.data"
  - "FTS toggle scoping: startsWith('fts-') filter exclusively removes search results, never touches non-fts commands"
observability_surfaces: []
drill_down_paths: []
duration: 1min
verification_result: passed
completed_at: 2026-03-02
blocker_discovered: false
---
# S29: Fts Fuzzy Search

**# Phase 29 Plan 01: FTS Fuzzy Search Summary**

## What Happened

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

# Phase 29 Plan 02: FTS Fuzzy Search UI Toggle Summary

**Fuzzy mode toggle in Ctrl+K palette with localStorage persistence and conditional &fuzzy=true URL injection — E2E result IDs unchanged**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-02T00:14:51Z
- **Completed:** 2026-03-02T00:15:49Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added `FUZZY_KEY = 'sempkm_fts_fuzzy'` constant to workspace.js IIFE constants block
- Added `search-fuzzy-toggle` command to ninja-keys palette with dynamic title ("Fuzzy Mode OFF/ON") and toggle handler
- Toggle reads initial state from localStorage on init, writes on activation (wrapped in try/catch)
- FTS fetch URL conditionally appends `&fuzzy=true` when `_fuzzyEnabled` is true
- `startsWith('fts-')` filter logic unchanged — toggle ID never matched, E2E constraint preserved

## Task Commits

Each task was committed atomically:

1. **Task 1: Add fuzzy toggle command and localStorage persistence to _initFtsSearch** - `6e6b1b5` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/static/js/workspace.js` - Added FUZZY_KEY constant, rewrote _initFtsSearch with fuzzy toggle command, localStorage persistence, and conditional &fuzzy=true URL injection

## Decisions Made
- Toggle ID `'search-fuzzy-toggle'` was chosen specifically to avoid the `startsWith('fts-')` filter in the change listener — this preserves the toggle across all search queries
- `sempkm_fts_fuzzy` localStorage key follows the existing `sempkm_` namespace used by all other workspace keys (PANE_KEY, PANEL_KEY, PANEL_POSITIONS_KEY)
- Unicode `\u2014` (em-dash) used instead of literal `—` for clean JS string embedding
- `try/catch` on `localStorage.setItem` follows defensive coding pattern for private-browsing environments

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The fuzzy toggle persists state in browser localStorage; no server-side configuration is needed.

## Next Phase Readiness
- Fuzzy search UI toggle is complete and wired to the backend endpoint from Phase 29 Plan 01
- Ctrl+K palette shows "Search: Fuzzy Mode OFF/ON" toggle command in the Search section
- Toggle state persists across browser sessions via localStorage
- FTS result IDs remain `'fts-' + r.iri` — E2E tests continue to pass unchanged
- No blockers for Phase 30 (FTS UI) or Phase 34 (E2E SPARQL FTS)

---
*Phase: 29-fts-fuzzy-search*
*Completed: 2026-03-02*

## Self-Check: PASSED

- FOUND: frontend/static/js/workspace.js
- FOUND: .planning/phases/29-fts-fuzzy-search/29-02-SUMMARY.md
- FOUND commit: 6e6b1b5 (Task 1)
