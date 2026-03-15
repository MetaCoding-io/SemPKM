---
id: T01
parent: S04
milestone: M005
provides:
  - GET /browser/tag-suggestions endpoint with SPARQL-backed tag autocomplete
  - build_tag_suggestions_sparql and parse_tag_bindings pure functions
  - tag_suggestions.html template for rendering suggestion items
key_files:
  - backend/app/browser/search.py
  - backend/app/templates/browser/tag_suggestions.html
  - backend/tests/test_tag_suggestions.py
key_decisions:
  - Extracted _sparql_escape, build_tag_suggestions_sparql, and parse_tag_bindings as module-level pure functions for testability
patterns_established:
  - Tag suggestion SPARQL pattern — UNION across both tag predicates, GROUP BY + COUNT for frequency, CONTAINS/LCASE for filtering
observability_surfaces:
  - logger.debug("Tag suggestions for q='%s': %d results", ...) on every request
  - GET /browser/tag-suggestions?q=<term> directly inspectable via curl
  - SPARQL failures logged at WARNING with exc_info, endpoint returns empty HTML gracefully
duration: 15m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Backend tag-suggestions endpoint with template and tests

**Added GET /browser/tag-suggestions endpoint that queries both bpkm:tags and schema:keywords via SPARQL UNION, returns frequency-ordered HTML suggestions**

## What Happened

Added the tag suggestions endpoint to `search.py` with three extracted pure functions (`_sparql_escape`, `build_tag_suggestions_sparql`, `parse_tag_bindings`) for testability. The endpoint accepts a `q` query parameter, builds a SPARQL query with UNION across both tag predicates, applies case-insensitive CONTAINS filtering when q is non-empty, and returns up to 30 results ordered by frequency DESC then alphabetically. Created `tag_suggestions.html` template that renders each result as a `.suggestion-item` div with an onclick handler that finds the closest `.tag-autocomplete-field`, sets the input value, and clears the dropdown. Wrote 22 unit tests covering query generation, escaping, result parsing, and escaping integration.

## Verification

- `backend/.venv/bin/pytest backend/tests/test_tag_suggestions.py -v` — **22/22 passed**
- Slice verification: `pytest tests/test_tag_suggestions.py -v` ✅ PASS
- Remaining slice checks (browser-side tag autocomplete wiring) are T02 scope — expected to not pass yet

## Diagnostics

- `GET /browser/tag-suggestions?q=test` — returns HTML partial directly (curl-inspectable)
- `logger.debug("Tag suggestions for q='%s': %d results", ...)` — shows query term and result count
- SPARQL failures caught and logged at WARNING level with traceback; endpoint returns empty HTML

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/search.py` — Added `_sparql_escape`, `build_tag_suggestions_sparql`, `parse_tag_bindings` helpers and `tag_suggestions` endpoint
- `backend/app/templates/browser/tag_suggestions.html` — New template rendering tag suggestion items with onclick handlers
- `backend/tests/test_tag_suggestions.py` — 22 unit tests covering query generation, escaping, parsing, and integration
- `.gsd/milestones/M005/slices/S04/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
