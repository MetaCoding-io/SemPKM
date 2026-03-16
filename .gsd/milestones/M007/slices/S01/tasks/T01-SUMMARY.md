---
id: T01
parent: S01
milestone: M007
provides:
  - build_dynamic_query() on ViewSpecService — SHACL-to-SPARQL with default fallback
  - register_generic_views() creating 3 in-memory ViewSpec objects
  - get_generic_columns() with deterministic sort and deduplication
  - _var_name_from_iri() helper for IRI-to-SPARQL-variable sanitization
key_files:
  - backend/app/views/service.py
  - backend/tests/test_dynamic_query_builder.py
  - backend/app/main.py
key_decisions:
  - ShapesService added as optional constructor parameter to ViewSpecService (backward compatible)
  - Generic specs use renderer_type "card" (not "cards") to match ViewSpec convention
  - Variable deduplication uses _2, _3 suffix via seen-count dict
  - Graph CONSTRUCT query includes LIMIT 200 as hard cap
  - Default columns threshold is >2 properties (≤2 falls back to defaults)
patterns_established:
  - _var_name_from_iri() for safe SPARQL variable names from property IRIs
  - get_generic_columns() as reusable column resolution with graceful degradation
  - Static _build_*_select() methods for testable SPARQL generation
observability_surfaces:
  - logger.info("Registered %d generic views", count) at startup
  - logger.debug("build_dynamic_query: type=%s, columns=%d", ...) on each query build
  - Graceful degradation on ShapesService failure → default columns returned
duration: 25min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Dynamic query builder and generic view registration with unit tests

**Added SHACL-to-SPARQL dynamic query builder and 3 generic ViewSpec registrations with 32 passing unit tests.**

## What Happened

Added four new methods to `ViewSpecService`:

1. **`register_generic_views()`** — creates 3 in-memory ViewSpec objects with well-known IRIs (`urn:sempkm:view:generic-table`, `generic-card`, `generic-graph`), renderer types table/card/graph, source_model="system", and empty sparql_query (built dynamically per request).

2. **`get_generic_columns(type_iri)`** — resolves column metadata from SHACL PropertyShapes. Falls back to 4 default columns (label, type, created, modified) when no type provided, no shape found, shape has ≤2 properties, or ShapesService throws. Sorts by `(order, name)` for determinism. Deduplicates variable names (same local name from different namespaces gets `_2` suffix).

3. **`build_dynamic_query(type_iri, renderer)`** — orchestrates query building. For table/card: delegates to `get_generic_columns()` then builds either a default SELECT (with OPTIONAL blocks for label/type/created/modified) or a SHACL SELECT (with OPTIONAL per PropertyShape + type filter). For graph: builds a CONSTRUCT with `?s ?p ?o` pattern and LIMIT 200. No FROM clauses — `scope_to_current_graph()` injects those at execution time.

4. **`get_generic_spec(renderer)`** — lookup helper for generic specs by renderer type.

Also added `_var_name_from_iri()` module-level helper that sanitizes IRI local names into valid SPARQL variable names (replaces non-alphanumeric with `_`, strips leading digits).

Updated `main.py` to pass `shapes_service` to `ViewSpecService` constructor. The parameter is optional and backward-compatible.

Enhanced `get_view_spec_by_iri()` to check generic specs for `urn:sempkm:view:generic-*` IRIs.

## Verification

- `cd backend && uv run --extra dev python -m pytest tests/test_dynamic_query_builder.py -v` — **32 tests pass** covering:
  - Generic view registration (7 tests): creates 3 specs, correct IRIs, correct renderer types, system source, lookup by renderer, invalid lookup, lookup before registration
  - Column resolution (7 tests): no type, empty type, type not found, sparse shape, rich shape, order stability, ShapesService exception
  - Variable naming (6 tests): fragment IRI, slash IRI, special chars, leading digits, all digits, colon delimiter
  - Variable deduplication (1 test): same local name from different namespaces
  - Query building (11 tests): all types default, typed with rich shapes, sparse fallback, type not found, no FROM clause, graph CONSTRUCT, graph with type filter, OPTIONAL blocks, label inclusion, default select with type filter
- LSP diagnostics on `service.py` — no type errors

### Slice-level verification status (T01 is first of 4 tasks):
- ✅ `cd backend && python -m pytest tests/test_dynamic_query_builder.py -v` — all pass
- ⬜ Browser: Table View from explorer (T02)
- ⬜ Browser: type pill filtering (T03)
- ⬜ Browser: carousel integration (T03)
- ⬜ Browser: pagination/filter (T02)
- ⬜ Browser: Saved Views folder (T04)
- ⬜ Browser: no per-type folders (T04)
- ✅ Diagnostic: graceful degradation on ShapesService failure (unit test verified)
- ⬜ Diagnostic: 404 for invalid renderer (T02)

## Diagnostics

- Call `build_dynamic_query(type_iri, renderer)` directly to see generated SPARQL
- `register_generic_views()` logs count at INFO level
- `build_dynamic_query()` logs type + column count at DEBUG level
- On any ShapesService failure, defaults are returned silently (logged at WARNING)

## Deviations

- Used renderer_type `"card"` instead of `"cards"` in the plan — matches the existing ViewSpec convention used by model-declared views throughout the codebase.

## Known Issues

None.

## Files Created/Modified

- `backend/app/views/service.py` — added `register_generic_views()`, `get_generic_spec()`, `get_generic_columns()`, `build_dynamic_query()`, `_build_default_select()`, `_build_shacl_select()`, `_build_graph_query()`, `_var_name_from_iri()`. Added `ShapesService` import and constructor parameter. Enhanced `get_view_spec_by_iri()` for generic spec lookup.
- `backend/tests/test_dynamic_query_builder.py` — 32 unit tests across 6 test classes
- `backend/app/main.py` — passes `shapes_service` to `ViewSpecService` constructor
