---
estimated_steps: 4
estimated_files: 2
---

# T02: Backend unit tests for hierarchy SPARQL and endpoint validation

**Slice:** S02 — Hierarchy Explorer Mode
**Milestone:** M003

## Description

Create `test_hierarchy_explorer.py` with unit tests covering the hierarchy SPARQL query structure, handler registration, and children endpoint input validation. Update `test_explorer_modes.py` if the handler signature changed (e.g. `label_service` added to dispatcher). These tests verify correctness without requiring a running triplestore — they inspect query strings, mock the triplestore client, and test pure validation logic.

## Steps

1. **Create `test_hierarchy_explorer.py` with SPARQL query structure tests.**
   Import the hierarchy handler and children endpoint. Write tests that verify:
   - Root query contains `FILTER NOT EXISTS { ?obj dcterms:isPartOf` (not OPTIONAL)
   - Root query scoped to `GRAPH <urn:sempkm:current>`
   - Children query contains `dcterms:isPartOf` with the parent IRI
   - Children query scoped to `GRAPH <urn:sempkm:current>`
   - Approach: either extract the SPARQL query building into a testable function, or mock `client.query()` and capture the SPARQL string passed to it.

2. **Add handler registration and signature tests.**
   - `_handle_hierarchy` is in `EXPLORER_MODES` under key `"hierarchy"`
   - `_handle_hierarchy` is an async callable
   - `_handle_hierarchy` is no longer a placeholder (doesn't render `explorer_placeholder.html`)

3. **Add children endpoint validation tests.**
   - Test that `_validate_iri` rejects invalid IRIs (leveraging existing `test_iri_validation.py` patterns)
   - Test that the children endpoint function exists on the router and accepts a `parent` query param
   - If feasible with FastAPI TestClient or mock, test 400 response for invalid IRI

4. **Update `test_explorer_modes.py` if needed.**
   - If T01 changed the handler signature (added `label_service` param to `explorer_tree` dispatch), verify existing tests still pass
   - If the `_handle_hierarchy` import test checks for placeholder behavior, update it to reflect real handler behavior

## Must-Haves

- [ ] Root SPARQL query validated to use `FILTER NOT EXISTS` for `dcterms:isPartOf`
- [ ] Both queries validated to scope to `GRAPH <urn:sempkm:current>`
- [ ] `_handle_hierarchy` confirmed as async callable in registry
- [ ] Children endpoint validates IRI input (invalid → 400)
- [ ] All existing `test_explorer_modes.py` tests still pass
- [ ] All new tests pass with `python -m pytest tests/test_hierarchy_explorer.py -v`

## Verification

- `cd backend && python -m pytest tests/test_hierarchy_explorer.py -v` — all new tests pass
- `cd backend && python -m pytest tests/test_explorer_modes.py -v` — all existing tests pass
- `cd backend && python -m pytest tests/ -v --tb=short` — no regressions across test suite

## Observability Impact

- Signals added/changed: None (tests are verification, not runtime)
- How a future agent inspects this: `python -m pytest tests/test_hierarchy_explorer.py -v` — test names map directly to hierarchy mode behaviors
- Failure state exposed: pytest output shows which specific query structure or validation check failed

## Inputs

- `backend/app/browser/workspace.py` — T01's updated `_handle_hierarchy` and `explorer_children` endpoint
- `backend/tests/test_explorer_modes.py` — existing 8 tests for mode registry
- `backend/tests/test_iri_validation.py` — reference for IRI validation test patterns
- `backend/app/browser/_helpers.py` — `_validate_iri()` function

## Expected Output

- `backend/tests/test_hierarchy_explorer.py` — new test file with 6-10 tests covering SPARQL structure, handler registration, and endpoint validation
- `backend/tests/test_explorer_modes.py` — updated if handler signature changed (minor import/assertion tweaks)
