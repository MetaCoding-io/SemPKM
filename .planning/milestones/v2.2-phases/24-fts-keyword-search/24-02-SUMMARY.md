---
phase: 24-fts-keyword-search
plan: 02
subsystem: search
tags: [fts, lucene-sail, ninja-keys, command-palette, search-api, keyword-search]

# Dependency graph
requires:
  - phase: 24-01
    provides: SearchService with search() method, get_search_service dependency injection
provides:
  - GET /api/search endpoint returning structured JSON with iri, type, label, snippet, score
  - Ctrl+K command palette FTS integration with debounced search and result display
  - Type icon SVG mapping for Basic PKM types in search results
  - User guide for keyword search feature
  - E2E test suite for FTS search (7 tests)
affects: [28]

# Tech tracking
tech-stack:
  added: []
  patterns: [ninja-keys change event for live search, debounced fetch with AbortController, inline SVG icons in ninja-keys]

key-files:
  created:
    - docs/guide/22-keyword-search.md
    - e2e/tests/08-search/fts-search.spec.ts
  modified:
    - backend/app/sparql/router.py
    - frontend/static/js/workspace.js

key-decisions:
  - "Used inline SVG strings for type icons in ninja-keys (not IconService) -- simpler client-side mapping, no extra API call"
  - "User guide numbered 22 (not 21 as in plan) because 21-sparql-console.md already existed"
  - "ninja-keys 'change' event with e.detail.search confirmed as correct API for intercepting search input in v1.2.2"

patterns-established:
  - "FTS palette pattern: ninja-keys change event listener with debounce + AbortController for cancellation"
  - "Type icon client-side mapping: _typeToIcon() matches on local name portion of type IRI"

requirements-completed: [FTS-02, FTS-03]

# Metrics
duration: 12min
completed: 2026-03-01
---

# Phase 24 Plan 02: Search API Endpoint + Ctrl+K Palette FTS Integration Summary

**GET /api/search endpoint with debounced ninja-keys palette integration showing type icon + label + snippet for FTS results**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-01T05:35:17Z
- **Completed:** 2026-03-01T05:48:04Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added GET /api/search endpoint to /api router with query validation (min 2 chars) and structured JSON response
- Integrated FTS results into Ctrl+K ninja-keys command palette with 300ms debounce and AbortController for request cancellation
- Results display type icon (inline SVG), object label, and snippet in the 'Search' section of the palette
- Clicking a search result calls openTab() to open the object in the editor
- Created user guide at docs/guide/22-keyword-search.md
- Created 7 E2E tests covering API validation, palette integration, and debounce behavior -- all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add GET /api/search endpoint** - `3cb7234` (feat)
2. **Task 2: Ctrl+K palette FTS integration, user guide, and E2E tests** - `8427430` (feat)

## Files Created/Modified
- `backend/app/sparql/router.py` - Added search_knowledge_base route (GET /api/search) with query validation and SearchService dependency
- `frontend/static/js/workspace.js` - Added _initFtsSearch() and _typeToIcon() functions for ninja-keys FTS integration
- `docs/guide/22-keyword-search.md` - User guide for keyboard search feature
- `e2e/tests/08-search/fts-search.spec.ts` - 7 Playwright tests for FTS endpoint and palette integration

## Decisions Made
- Used inline SVG strings for type icons in ninja-keys rather than the backend IconService. This avoids an extra API call and keeps the icon mapping simple -- just four Basic PKM types (Note, Project, Person, Concept) with a document fallback. The plan explicitly allowed this simpler approach.
- Numbered the user guide as `22-keyword-search.md` instead of `21-keyword-search.md` because `21-sparql-console.md` already existed from Phase 23.
- Confirmed ninja-keys v1.2.2 dispatches `'change'` CustomEvent with `detail.search` containing the current search string -- this is the correct event to intercept.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] User guide filename collision**
- **Found during:** Task 2 (Part B - User guide creation)
- **Issue:** Plan specified `docs/guide/21-keyword-search.md` but `21-sparql-console.md` already existed
- **Fix:** Used `22-keyword-search.md` as the next available number
- **Files modified:** docs/guide/22-keyword-search.md
- **Verification:** File created successfully at unique path
- **Committed in:** 8427430

**2. [Rule 1 - Bug] E2E test URL path and fixture patterns**
- **Found during:** Task 2 (Part C - E2E tests)
- **Issue:** Plan's test code used `/workspace` URL and `page` fixture, but the workspace is at `/browser/` and auth requires `ownerPage` fixture
- **Fix:** Used `${BASE_URL}/browser/` and `ownerPage` fixture with `waitForWorkspace()` helper, matching existing test patterns
- **Files modified:** e2e/tests/08-search/fts-search.spec.ts
- **Verification:** All 7 tests pass
- **Committed in:** 8427430

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correct file naming and test execution. No scope creep.

## Issues Encountered
- ninja-keys element resolves to "hidden" in Playwright's `waitForSelector` because the custom element has no visible dimensions when the palette is closed. Used `waitForWorkspace()` instead, matching existing keyboard shortcut test patterns.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- FTS-01, FTS-02, FTS-03 all complete -- Phase 24 is fully done
- Search is live in the command palette for any query >= 2 characters
- LuceneSail indexes all new writes automatically
- Ready for Phase 28 UI Polish + Integration Testing

## Self-Check: PASSED

- All 4 created/modified files verified present on disk
- Both task commits (3cb7234, 8427430) verified in git log

---
*Phase: 24-fts-keyword-search*
*Completed: 2026-03-01*
