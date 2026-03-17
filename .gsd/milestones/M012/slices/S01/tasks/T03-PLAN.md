---
estimated_steps: 5
estimated_files: 2
---

# T03: Unit tests for label resolution, helptext extraction, and suggestion endpoints

**Slice:** S01 — Event Log Polish — Labels, Helptext & Autocomplete
**Milestone:** M012

## Description

Provide contract-level unit test coverage for the new backend methods added in T01 and T02. Tests mock the triplestore client and validate that label resolution, helptext extraction, and suggestion endpoints behave correctly — including edge cases and error handling.

Follow the test patterns established in `backend/tests/test_event_user_lookup.py` (async tests with mocked dependencies) and `backend/tests/test_class_creation.py` (ShapesService testing with rdflib Graph fixtures).

## Steps

1. **Create `backend/tests/test_event_log_labels.py`** with tests for ShapesService predicate methods:
   - **Fixture**: Build a minimal rdflib `Graph` with known PropertyShapes:
     ```python
     # PropertyShape for dcterms:title with sh:name "Title" and sempkm:editHelpText "The display name..."
     # PropertyShape for rdfs:comment with sh:name "Description" and sh:description "A short description..."
     # PropertyShape for schema:dateCreated with sh:name "Date Created" and no helptext
     ```
   - Mock `ShapesService._fetch_shapes_graph()` to return this fixture graph
   - **Test `get_labels_for_predicates()`**:
     - Known predicate returns SHACL `sh:name` label (e.g., `dcterms:title` → "Title")
     - Unknown predicate returns nothing (empty dict entry)
     - Empty input returns empty dict
     - Multiple predicates resolved in single call
   - **Test `get_helptext_for_predicates()`**:
     - Predicate with `sempkm:editHelpText` returns that value
     - Predicate with only `sh:description` falls back to that
     - Predicate with neither returns nothing
     - Empty input returns empty dict
     - SPARQL error returns empty dict (mock `_fetch_shapes_graph` to raise)

2. **Test event_detail template context** (integration-level):
   - Create a mock `EventDetail` with known `new_values` containing predicate IRIs
   - Verify the route logic collects predicate IRIs correctly from both `new_values` and `data_triples`
   - Test the predicate IRI collection logic as a pure function (extract it if needed)

3. **Create `backend/tests/test_event_suggestions.py`** with tests for suggestion endpoints:
   - **Test `suggest-types`**:
     - Returns HTML with distinct operation types when events exist
     - Returns empty suggestions when no events exist
     - Mock triplestore `query()` to return known SPARQL result bindings
   - **Test `suggest-predicates`**:
     - Returns predicates with human-readable labels
     - `q` parameter filters by label prefix (case-insensitive)
     - Empty `q` returns all predicates (up to limit)
     - Returns empty suggestions for non-matching `q`
   - **Test `suggest-objects`**:
     - Returns objects with resolved labels
     - `q` parameter filters by label or IRI
     - Returns empty suggestions for non-matching `q`
     - Limit 20 enforced

4. **Test predicate filter in `list_events()`**:
   - Verify that `predicate_iri` parameter adds `FILTER EXISTS` clause to SPARQL
   - Mock client to capture the generated SPARQL and assert the clause is present
   - Verify `predicate_iri=None` does not add any extra filter

5. **Run all tests and verify no regressions**:
   - `cd backend && python -m pytest tests/test_event_log_labels.py tests/test_event_suggestions.py -v`
   - `cd backend && python -m pytest tests/ -v` — all existing tests still pass

## Must-Haves

- [ ] `test_event_log_labels.py` covers `get_labels_for_predicates()` and `get_helptext_for_predicates()` with positive, negative, and error cases
- [ ] `test_event_suggestions.py` covers all three suggestion endpoints with query filtering and empty state
- [ ] Predicate filter SPARQL generation tested
- [ ] All new tests pass
- [ ] No regressions in existing test suite

## Verification

- `cd backend && python -m pytest tests/test_event_log_labels.py -v` — all pass
- `cd backend && python -m pytest tests/test_event_suggestions.py -v` — all pass
- `cd backend && python -m pytest tests/ -v` — no regressions

## Inputs

- `backend/app/services/shapes.py` — from T01 with `get_helptext_for_predicates()` and `get_labels_for_predicates()`
- `backend/app/browser/events.py` — from T02 with suggestion endpoints and `pred` filter
- `backend/app/events/query.py` — from T02 with `predicate_iri` filter on `list_events()`
- `backend/tests/test_event_user_lookup.py` — reference pattern for async test fixtures
- `backend/tests/test_class_creation.py` — reference pattern for ShapesService testing with rdflib Graph

## Expected Output

- `backend/tests/test_event_log_labels.py` — ~10 tests covering label + helptext extraction from ShapesService
- `backend/tests/test_event_suggestions.py` — ~10 tests covering suggestion endpoints and predicate filter

## Observability Impact

This task is test-only — it does not add or modify runtime signals. The tests verify that existing observability holds under controlled conditions:

- **Graceful degradation tests**: Confirm `get_labels_for_predicates()` and `get_helptext_for_predicates()` return empty dicts (not exceptions) when `_fetch_shapes_graph()` raises — ensuring the `logger.warning("Failed to resolve predicate labels/helptext from shapes graph")` paths work correctly.
- **SPARQL filter tests**: Confirm the `FILTER EXISTS` clause for `predicate_iri` is correctly injected, which is the only runtime SPARQL modification from T02.
- **Future agent inspection**: Run `pytest tests/test_event_log_labels.py tests/test_event_suggestions.py -v` to verify contracts hold after any change to ShapesService predicate methods or suggestion endpoints.
