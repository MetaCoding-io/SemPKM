---
estimated_steps: 7
estimated_files: 2
---

# T01: Dynamic query builder and generic view registration with unit tests

**Slice:** S01 — Generic Views & Explorer Consolidation
**Milestone:** M007

## Description

Build the SHACL-to-SPARQL dynamic query builder that converts PropertyShape metadata into SPARQL SELECT queries, and register 3 generic ViewSpec objects in memory. This is the riskiest piece — the SPARQL must be correct for all types, handle the "All Types" fallback, produce stable deterministic column lists, and pass through `scope_to_current_graph()`. Unit tests validate all this before any endpoint wiring.

## Steps

1. **Read `ViewSpecService` class** in `backend/app/views/service.py` to understand the `ViewSpec` dataclass fields and existing `execute_table_query()` / `execute_cards_query()` / `execute_graph_query()` signatures. Note how `scope_to_current_graph()` is called and what `sparql_query` format the execute methods expect.

2. **Read `ShapesService`** in `backend/app/services/shapes.py` to understand `get_form_for_type(type_iri) -> NodeShapeForm | None` and `get_types() -> list[dict]`. Note the `PropertyShape` dataclass fields: `path` (IRI string), `name` (human label), `datatype`, `order` (float), etc.

3. **Add `register_generic_views()` method** to `ViewSpecService`. Creates 3 in-memory `ViewSpec` objects:
   - `ViewSpec(spec_iri="urn:sempkm:view:generic-table", label="Table View", target_class="", renderer_type="table", sparql_query="", source_model="system")`
   - Same pattern for `generic-cards` (renderer_type="card") and `generic-graph` (renderer_type="graph")
   - Store them in a `self._generic_specs: list[ViewSpec]` instance attribute
   - Add a helper `get_generic_spec(renderer: str) -> ViewSpec | None` that returns the right one

4. **Add `get_generic_columns(type_iri: str | None) -> tuple[list[PropertyShape], list[str]]`** method. If `type_iri` is None or empty, return default columns list: `["label", "type", "created", "modified"]` with no PropertyShapes. If `type_iri` is provided, call `self._shapes_service.get_form_for_type(type_iri)`. If result is None or has ≤2 properties, return default columns. Otherwise, sort properties by `(order, name)` for determinism, extract column variable names from property paths (local name of the IRI, e.g. `http://example.org/title` → `title`), and return both the shapes and column names. The `ShapesService` instance needs to be accessible — it's likely passed via DI in `main.py`. Check how `ViewSpecService.__init__` receives dependencies and add `shapes_service: ShapesService` as a new constructor parameter.

5. **Add `build_dynamic_query(type_iri: str | None) -> tuple[str, list[str]]`** method. Returns `(sparql_query_string, column_names)`. Logic:
   - Call `get_generic_columns(type_iri)` to get shapes and columns
   - If using default columns (no type or sparse type): build a SPARQL SELECT with `?s ?label ?type ?created ?modified` using standard predicates: `rdfs:label`/`dcterms:title` for label (COALESCE), `rdf:type` for type, `dcterms:created` for created, `dcterms:modified` for modified. All in OPTIONAL blocks except `?s`.
   - If using SHACL columns: build SELECT with `?s` plus one variable per PropertyShape. Each property becomes an `OPTIONAL { ?s <property_path> ?varname . }` clause. Add a type filter: `?s rdf:type <type_iri> .` Also include `?label` via the standard label COALESCE pattern.
   - The query MUST NOT include `FROM` clause — `scope_to_current_graph()` will inject it.
   - Variable names derived from property path local names must be sanitized (replace non-alphanumeric with `_`, deduplicate by appending `_2`, `_3`, etc.).
   - For graph renderer: build a CONSTRUCT query following the pattern: `CONSTRUCT { ?s ?p ?o . ?s rdf:type ?type . ?s rdfs:label ?label . } WHERE { ?s ?p ?o . ?s rdf:type ?type . OPTIONAL { ?s rdfs:label|dcterms:title ?label } }` with optional type filter and LIMIT 200.

6. **Write unit tests** in `backend/tests/test_dynamic_query_builder.py`. Mock `ShapesService.get_form_for_type()` to return known `NodeShapeForm` objects. Test scenarios:
   - All Types (no type_iri): query has default columns, no type filter, returns 4 columns
   - Typed with rich shapes (≥3 properties): query has SHACL columns, type filter present
   - Typed with sparse shapes (≤2 properties): falls back to default columns
   - Type not found (get_form_for_type returns None): falls back to default columns
   - Column order stability: two calls with same type return same column order
   - Variable name sanitization: property paths with special chars get clean var names
   - Variable name deduplication: two properties with same local name get `_2` suffix
   - Graph renderer: returns CONSTRUCT query with LIMIT 200
   - `register_generic_views()`: creates exactly 3 specs with correct IRIs and renderer types
   - `get_generic_spec()`: returns correct spec by renderer name, None for invalid

7. **Verify**: `cd backend && python -m pytest tests/test_dynamic_query_builder.py -v` — all tests pass. Then check LSP diagnostics on `service.py` for type errors.

## Must-Haves

- [ ] `build_dynamic_query()` produces valid SPARQL SELECT for typed and untyped cases
- [ ] Default column fallback when no type, ≤2 properties, or type not found
- [ ] Column sort by `(order, name)` for deterministic output
- [ ] Variable name sanitization and deduplication
- [ ] `register_generic_views()` creates 3 ViewSpec with `urn:sempkm:view:generic-*` IRIs
- [ ] Graph renderer builds CONSTRUCT with LIMIT 200
- [ ] ≥8 unit test scenarios pass

## Verification

- `cd backend && python -m pytest tests/test_dynamic_query_builder.py -v` — all tests pass
- LSP diagnostics on `backend/app/views/service.py` — no type errors

## Observability Impact

- Signals added/changed: `logger.info("Registered %d generic views", count)` in `register_generic_views()`; `logger.debug("build_dynamic_query: type=%s, columns=%d", type_iri, len(columns))` in query builder
- How a future agent inspects this: call `build_dynamic_query()` directly in a test or REPL to see generated SPARQL
- Failure state exposed: returns default columns on any ShapesService failure (graceful degradation)

## Inputs

- `backend/app/views/service.py` — ViewSpec dataclass, ViewSpecService class with execute_*_query() methods
- `backend/app/services/shapes.py` — ShapesService with get_form_for_type() and get_types(), PropertyShape dataclass
- `backend/app/sparql/client.py` — scope_to_current_graph() function (consumed by execute methods, not called directly by builder)

## Expected Output

- `backend/app/views/service.py` — new methods: `register_generic_views()`, `get_generic_spec()`, `get_generic_columns()`, `build_dynamic_query()`. ShapesService added as constructor dependency.
- `backend/tests/test_dynamic_query_builder.py` — ≥10 unit tests covering all scenarios
