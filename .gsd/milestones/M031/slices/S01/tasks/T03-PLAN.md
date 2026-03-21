---
estimated_steps: 5
estimated_files: 3
---

# T03: Unit tests for scope query filtering and variant dropdown data

**Slice:** S01 — Carousel Removal + View Scope Binding
**Milestone:** M031

## Description

Create unit tests proving the scope_query filtering works correctly in `build_dynamic_query()` and that `get_view_specs_for_type()` returns the correct model-declared variants. These tests are the contract verification for S01's boundary outputs — consumed by S02 (multiple instances with scopes), S03 (saved queries everywhere), and S04 (kanban with scope support).

Uses the existing pytest infrastructure in `backend/tests/` with conftest fixtures.

**Skill:** Load the `test` skill if needed for test patterns.

## Steps

1. **Create test file.** Create `backend/tests/test_view_scope.py`.

2. **Test build_dynamic_query without scope_filter.** Write tests verifying:
   - `build_dynamic_query(None, 'table')` returns a SELECT query without any sub-select scope constraint
   - `build_dynamic_query(type_iri, 'table')` returns a query with a type filter but no scope constraint
   - `build_dynamic_query(None, 'graph')` returns a CONSTRUCT query without scope constraint

3. **Test build_dynamic_query with scope_filter.** Write tests verifying:
   - `build_dynamic_query(None, 'table', scope_filter="?s a <urn:test:Type> .")` returns a SELECT query containing a sub-select that constrains ?s
   - `build_dynamic_query(type_iri, 'table', scope_filter="...")` combines both type filter and scope filter
   - The scope sub-select uses the correct variable name (`?s` for SELECT, matches what the outer query expects)
   - `build_dynamic_query(None, 'graph', scope_filter="...")` applies scope to CONSTRUCT query

4. **Test _extract_where_body utility.** Write tests for `_extract_where_body()`:
   - Extracts WHERE body from `SELECT ?s ?title WHERE { ?s a <urn:Type> . ?s dcterms:title ?title } LIMIT 100` → returns `?s a <urn:Type> . ?s dcterms:title ?title`
   - Handles queries with FROM clauses
   - Handles queries with nested braces
   - Returns empty string or the input itself for malformed queries (graceful degradation)

5. **Test get_view_specs_for_type.** Write tests verifying:
   - Returns only ViewSpecs whose `target_class` matches the given `type_iri`
   - Returns empty list for types with no model-declared specs
   - Does not include generic specs (generic specs have no `target_class` or an empty one)
   - These tests need a mocked `ViewSpecService` with a few test ViewSpecs registered

## Must-Haves

- [ ] Tests cover build_dynamic_query with and without scope_filter
- [ ] Tests cover _extract_where_body utility
- [ ] Tests cover get_view_specs_for_type filtering
- [ ] All tests pass: `cd backend && python -m pytest tests/test_view_scope.py -v`

## Verification

- `cd backend && python -m pytest tests/test_view_scope.py -v` — all tests pass, zero failures
- Tests cover at least 6 scenarios (no scope, with scope, combined type+scope, WHERE extraction, type filtering, empty type filtering)

## Inputs

- `backend/app/views/service.py` — from T02: `build_dynamic_query()` with `scope_filter` parameter, `_extract_where_body()`, `get_view_specs_for_type()`
- `backend/tests/conftest.py` — existing test fixtures and patterns
- `backend/app/views/service.py` — `ViewSpec` dataclass, `ViewSpecService` class

## Expected Output

- `backend/tests/test_view_scope.py` — test file with 8-12 test functions covering all scope filtering scenarios
