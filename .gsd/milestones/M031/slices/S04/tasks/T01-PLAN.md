---
estimated_steps: 5
estimated_files: 4
skills_used: []
---

# T01: Backend kanban endpoint, status detection, and unit tests

**Slice:** S04 — Kanban Renderer
**Milestone:** M031

## Description

Add the kanban renderer backend: status field auto-detection from SHACL shapes, SPARQL query execution with server-side grouping into columns, the kanban branch in `generic_view()`, and renderer registry entry. Write unit tests covering the detection and grouping logic.

## Steps

1. **Add `_detect_status_field()` to `ViewSpecService` (service.py)**
   - Method signature: `async def _detect_status_field(self, type_iri: str) -> tuple[PropertyShape | None, list[str]]`
   - Uses `self._shapes_service.get_form_for_type(type_iri)` to get the `NodeShapeForm`
   - Iterates `form.properties` looking for the first `PropertyShape` with non-empty `in_values`
   - Prefers a property whose `path` contains "status" (case-insensitive) — but falls back to the first with `in_values`
   - Returns `(property_shape, in_values)` or `(None, [])` if no suitable property found
   - Add fallback for when `self._shapes_service` is None → return `(None, [])`

2. **Add `_build_kanban_select()` static method to `ViewSpecService` (service.py)**
   - Builds a SELECT query: `SELECT ?s ?label ?statusValue WHERE { ?s rdf:type <type_iri> . ?s <status_path> ?statusValue . OPTIONAL { ?s rdfs:label|dcterms:title ?label } }`
   - Accepts optional `scope_filter` parameter — injects as `{ SELECT ?s WHERE { ... } }` sub-select (same pattern as `_build_default_select`)
   - Returns the SPARQL query string

3. **Add `execute_kanban_query()` to `ViewSpecService` (service.py)**
   - Method signature: `async def execute_kanban_query(self, type_iri: str, status_field: PropertyShape, status_values: list[str], scope_filter: str | None = None) -> dict`
   - Calls `_build_kanban_select()` to get the SPARQL query
   - Executes via `scope_to_current_graph()` + `self._client.query()`
   - Groups results into columns: `{"columns": [{"value": "todo", "label": "Todo", "items": [{"iri": ..., "label": ...}]}, ...], "status_field": {"path": ..., "name": ...}, "total": N}`
   - Column order follows the `status_values` list order from `sh:in`
   - Objects with no matching status go into an "Unset" column appended at the end
   - Column labels are title-cased versions of the status value

4. **Add kanban branch in `generic_view()` (router.py)**
   - Add `"kanban"` to `_VALID_RENDERERS` set
   - Add `elif renderer == "kanban":` branch after the `else: # graph` block (restructure the if/elif chain)
   - The kanban branch:
     - If no `type_iri`: render error message "Select a type to use Kanban View"
     - Call `await view_spec_service._detect_status_field(type_iri)` — if returns None, render "This type has no status-like properties for Kanban grouping"
     - Call `await view_spec_service.execute_kanban_query(type_iri, status_field, status_values, scope_filter_text)`
     - Render `kanban_view.html` with context including: `request`, `columns` (from result), `status_field`, `type_label`, `type_iri`, `selected_type`, `types` (for type pills), `model_view_specs`, `scope_query`, `user_saved_queries`, `model_saved_queries`, `is_generic: True`, `renderer: "kanban"`, `pagination_base_url`, `pag_extra`, `spec` (transient ViewSpec)
   - Add `logger.info("generic_view: renderer=kanban type=%s scope_query=%s", ...)` log line

5. **Register kanban in registry.py and write unit tests**
   - Add to `RENDERER_REGISTRY` in `registry.py`:
     ```python
     "kanban": {
         "type": "kanban",
         "template": "browser/kanban_view.html",
     },
     ```
   - Create `backend/tests/test_kanban.py` with tests:
     - `test_detect_status_field_with_sh_in` — property with `in_values` is found
     - `test_detect_status_field_prefers_status_path` — when multiple properties have `in_values`, prefers one with "status" in path
     - `test_detect_status_field_no_in_values` — returns None when no property has `in_values`
     - `test_detect_status_field_no_shapes_service` — returns None when shapes_service is None
     - `test_build_kanban_select_basic` — produces correct SPARQL
     - `test_build_kanban_select_with_scope` — scope_filter injected as sub-select
     - `test_execute_kanban_query_groups_by_status` — mock SPARQL results grouped correctly into columns
     - `test_execute_kanban_query_unset_column` — objects without status value go to "Unset" column
   - Follow the test pattern from `backend/tests/test_view_scope.py`: use `unittest.mock.AsyncMock` for shapes service, `MagicMock` for triplestore client

## Must-Haves

- [ ] `_detect_status_field()` correctly finds first `sh:in` property, preferring "status" in path
- [ ] `_build_kanban_select()` produces valid SPARQL with optional scope_filter sub-select
- [ ] `execute_kanban_query()` groups results into ordered columns matching `sh:in` values
- [ ] `"kanban"` in `_VALID_RENDERERS` and router dispatches to kanban branch
- [ ] `"kanban"` entry in `RENDERER_REGISTRY`
- [ ] All unit tests pass
- [ ] Graceful messages when no type selected or type has no status property

## Verification

- `python -m pytest backend/tests/test_kanban.py -v` — all tests pass
- `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` — no syntax errors
- `python3 -c "import ast; ast.parse(open('backend/app/views/service.py').read())"` — no syntax errors
- `grep -q '"kanban"' backend/app/views/registry.py` — registry entry present

## Inputs

- `backend/app/views/router.py` — existing generic_view() endpoint to add kanban branch
- `backend/app/views/service.py` — existing ViewSpecService to add kanban methods
- `backend/app/views/registry.py` — existing RENDERER_REGISTRY to add kanban entry
- `backend/app/services/shapes.py` — PropertyShape.in_values and ShapesService.get_form_for_type() used for status detection
- `backend/tests/test_view_scope.py` — reference test pattern (mock setup, assertions)
- `backend/app/sparql/client.py` — scope_to_current_graph() for query execution

## Expected Output

- `backend/app/views/service.py` — modified with `_detect_status_field()`, `_build_kanban_select()`, `execute_kanban_query()`
- `backend/app/views/router.py` — modified with kanban in `_VALID_RENDERERS` and kanban branch in `generic_view()`
- `backend/app/views/registry.py` — modified with kanban entry in `RENDERER_REGISTRY`
- `backend/tests/test_kanban.py` — new test file with 8+ unit tests

## Observability Impact

- **New log signal:** `logger.info("generic_view: renderer=kanban type=%s scope_query=%s", ...)` emitted on every kanban request — enables grep-based request monitoring.
- **New warning signal:** `logger.warning(...)` in `_detect_status_field()` when SHACL shapes lookup fails for a type — surfaces broken shapes data.
- **Inspection surface:** `GET /browser/views/generic/kanban?type=<iri>` renders kanban HTML or a user-facing error message when the type has no status property.
- **Failure visibility:** Kanban endpoint returns a graceful error template (not a 500) when no type is selected or the type lacks `sh:in` properties. SPARQL query failures in `execute_kanban_query()` are logged and return empty columns.
