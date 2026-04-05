# S01: Smart Type Dropdown

**Goal:** Replace the 37-pill type bar with a smart `<select>` dropdown filtered by renderer compatibility, and remove the View Variants dropdown.
**Demo:** After this: Open Kanban View → type dropdown shows only types with status fields. Open Table View → shows all types. No more 37-pill bar.

## Tasks
- [x] **T01: Add get_compatible_types() to ViewSpecService with JSON endpoint and renderer-filtered type lists in generic_view()** — Add a `get_compatible_types(renderer, exclude_iris)` method to ViewSpecService that leverages the existing `_detect_status_field()`, `_detect_date_fields()`, and `_detect_geo_fields()` methods to return only types whose SHACL shapes are compatible with a given renderer.

Then add a new endpoint `GET /browser/views/compatible-types?renderer=kanban` that returns JSON `{types: [{iri, label}]}`. Update `generic_view()` to call `get_compatible_types()` instead of `shapes_service.get_types()` so templates receive the already-filtered list.

**Renderer compatibility rules:**
- `table`, `card`, `graph`: all types (no filtering)
- `kanban`: types where `_detect_status_field(type_iri)` returns non-None
- `calendar`, `timeline`: types where `_detect_date_fields(type_iri)` returns non-None start field
- `map`: types where `_detect_geo_fields(type_iri)` returns non-None pair
- `quadrant`, `bmc`, `okr`, `decision-matrix`: all types (model-declared renderers, rare usage)

**Steps:**
1. Read `backend/app/views/service.py` — understand `_detect_status_field`, `_detect_date_fields`, `_detect_geo_fields` signatures
2. Add `async def get_compatible_types(self, renderer: str, exclude_iris: set[str] | None = None) -> list[dict]` to `ViewSpecService`:
   - Call `self._shapes_service.get_types(exclude_iris=exclude_iris)` to get all types
   - For `kanban`: iterate types, call `_detect_status_field(t['iri'])`, keep only those returning non-None
   - For `calendar`/`timeline`: iterate types, call `_detect_date_fields(t['iri'])`, keep only those with start_field
   - For `map`: iterate types, call `_detect_geo_fields(t['iri'])`, keep only those returning non-None pair
   - For all other renderers: return all types unfiltered
   - Log `compatible_types: renderer=%s total=%d compatible=%d`
3. Add `GET /browser/views/compatible-types?renderer=table` endpoint to `backend/app/views/router.py` that calls `get_compatible_types()`
4. In `generic_view()`, replace `types_list = await shapes_service.get_types(...)` with `types_list = await view_spec_service.get_compatible_types(renderer, ...)`
5. Add unit test `backend/tests/test_compatible_types.py` that mocks ShapesService to return a set of types, then verifies kanban filtering returns only status-field types
6. Run tests to verify
  - Estimate: 1h
  - Files: backend/app/views/service.py, backend/app/views/router.py, backend/tests/test_compatible_types.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_compatible_types.py -v
- [x] **T02: Replace 37-pill type bar with compact select dropdown across all 11 view templates and remove View Variants dropdown** — Replace the `type_filter_pills.html` template (37 buttons across 4 rows) with a `<select>` dropdown in a new `type_filter_dropdown.html` partial. Remove the View Variants dropdown from `view_toolbar.html` (D389). Update all 7 view templates. Update CSS.

**Steps:**
1. Create `backend/app/templates/browser/type_filter_dropdown.html`:
   - Single `<select class="type-filter-select">` with `<option value="">All Types</option>` default
   - Loop `{% for t in types %}` rendering `<option value="{{ t.iri }}" {% if selected_type == t.iri %}selected{% endif %}>{{ t.label }}</option>`
   - `onchange` handler: build URL `/browser/views/generic/{{ renderer }}?type=<value>` + preserve scope_query, then `htmx.ajax('GET', url, {target: 'closest .group-editor-area', swap: 'innerHTML'})`
   - Also persist selection: `localStorage.setItem('sempkm_generic_type_' + renderer, this.value)`
   - Wrap in a small container div `<div class="type-filter-dropdown">`
2. Update all 7 view templates — change `{% include "browser/type_filter_pills.html" %}` to `{% include "browser/type_filter_dropdown.html" %}`:
   - `table_view.html`, `cards_view.html`, `kanban_view.html`, `graph_view.html`, `calendar_view.html`, `timeline_view.html`, `map_view.html`
3. In `view_toolbar.html`, remove the View Variants dropdown block (the `{% if model_view_specs ... %}` select with class `view-variant-select`)
4. Update `frontend/static/css/views.css`:
   - Remove `.type-filter-pills`, `.type-pill`, `.type-pill:hover`, `.type-pill.active` rules
   - Add `.type-filter-dropdown` and `.type-filter-select` styling (compact select, matching toolbar aesthetic)
   - Remove `.view-variant-select` styles
5. Verify: open each view renderer in the browser and confirm dropdown appears, pills are gone, View Variants is gone

**Important constraints:**
- The `onchange` handler must preserve `scope_query` from the toolbar's `data-scope-query` attribute or the scope select's value
- The dropdown must show only the types passed in the `types` template variable (already filtered by T01's backend work)
- The `type_filter_pills.html` file should be kept but emptied (or deleted) — keeping it prevents include errors if any non-generic view still references it
  - Estimate: 1h
  - Files: backend/app/templates/browser/type_filter_dropdown.html, backend/app/templates/browser/type_filter_pills.html, backend/app/templates/browser/view_toolbar.html, backend/app/templates/browser/table_view.html, backend/app/templates/browser/cards_view.html, backend/app/templates/browser/kanban_view.html, backend/app/templates/browser/graph_view.html, backend/app/templates/browser/calendar_view.html, backend/app/templates/browser/timeline_view.html, backend/app/templates/browser/map_view.html, frontend/static/css/views.css
  - Verify: grep -r 'type_filter_pills' backend/app/templates/browser/ | grep -v 'type_filter_pills.html' | wc -l should return 0 (no templates include the old pills). grep -c 'type_filter_dropdown' backend/app/templates/browser/table_view.html backend/app/templates/browser/kanban_view.html returns 1 per file. grep -c 'view-variant-select' backend/app/templates/browser/view_toolbar.html returns 0.
