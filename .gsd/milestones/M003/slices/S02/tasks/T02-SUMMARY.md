---
id: T02
parent: S02
milestone: M003
provides:
  - 16 unit tests covering hierarchy SPARQL query structure, handler registration, children endpoint validation, deduplication, and error fallback
key_files:
  - backend/tests/test_hierarchy_explorer.py
key_decisions:
  - Test SPARQL structure by mock-capturing the query string passed to client.query() rather than extracting query building into separate functions — avoids refactoring production code just for testability
patterns_established:
  - Hierarchy test pattern: mock request.app.state.triplestore_client as AsyncMock, capture SPARQL via call_args[0][0], assert query structure
  - Children endpoint tested by calling explorer_children() directly with mock deps, verifying HTTPException for invalid IRIs
observability_surfaces:
  - none (tests are verification, not runtime)
duration: 10m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Backend unit tests for hierarchy SPARQL and endpoint validation

**Created 16 unit tests covering hierarchy root/children SPARQL query structure, handler registration, deduplication logic, error fallback, and children endpoint IRI validation.**

## What Happened

Created `backend/tests/test_hierarchy_explorer.py` with 16 tests across 4 test classes:

1. **TestHierarchyRootSPARQL** (6 tests): Verifies root query uses `FILTER NOT EXISTS` for `dcterms:isPartOf`, scopes to `GRAPH <urn:sempkm:current>`, selects `?obj` and `?type`, renders `hierarchy_tree.html`, deduplicates multi-type objects, and falls back to empty results on triplestore failure.

2. **TestHierarchyChildrenSPARQL** (3 tests): Verifies children query contains the parent IRI in `dcterms:isPartOf`, scopes to `GRAPH <urn:sempkm:current>`, and renders `hierarchy_children.html`.

3. **TestHierarchyHandlerRegistration** (3 tests): Confirms `_handle_hierarchy` is registered in `EXPLORER_MODES` under key `"hierarchy"`, is an async callable, and does not reference `explorer_placeholder.html` (confirming it's no longer a placeholder).

4. **TestChildrenEndpointValidation** (4 tests): Tests that `explorer_children()` raises HTTP 400 for invalid IRIs, empty strings, and SPARQL injection payloads, while accepting valid IRIs and proceeding to query.

No changes needed to `test_explorer_modes.py` — all 8 existing tests pass unchanged since T01 preserved the handler signature compatibility via `**_kwargs`.

## Verification

- `cd backend && python -m pytest tests/test_hierarchy_explorer.py -v` — 16/16 passed
- `cd backend && python -m pytest tests/test_explorer_modes.py -v` — 8/8 passed
- `cd backend && python -m pytest tests/ -v --tb=short` — 154/154 passed, 0 failures, no regressions

Slice-level verification (partial — T02 is intermediate):
- ✅ `cd backend && python -m pytest tests/test_explorer_modes.py tests/test_hierarchy_explorer.py -v` — all 24 pass
- ⏳ E2E tests — T03 scope
- ⏳ Manual browser verification — T03 scope

## Diagnostics

`python -m pytest tests/test_hierarchy_explorer.py -v` — test names map directly to hierarchy mode behaviors. Failures indicate which specific query structure check or validation assertion broke.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_hierarchy_explorer.py` — new test file with 16 tests across 4 classes covering SPARQL structure, handler registration, and endpoint validation
