---
estimated_steps: 5
estimated_files: 5
skills_used: []
---

# T02: Wire quadrant renderer into view router + backend data endpoint

**Slice:** S01 — Eisenhower Matrix — Model Archive + Quadrant Renderer
**Milestone:** M036

## Description

Add the `quadrant` renderer type to the backend view system. This means: adding "quadrant" to `_VALID_RENDERERS`, adding an `elif renderer == "quadrant"` branch in `generic_view()` (following the exact pattern of the existing kanban branch), creating `_detect_quadrant_axes()` and `execute_quadrant_query()` methods on ViewSpecService, adding a quadrant branch to `generic_view_data()` for the JSON data endpoint, registering the renderer in RENDERER_REGISTRY, and creating the initial Jinja2 template shell.

The quadrant renderer detects two SHACL properties with `sh:in` containing exactly ["high", "low"] values, uses them as the X and Y axes, and groups items into 4 quadrant buckets. The JSON data endpoint returns `{quadrants: [{x_value, y_value, label, items: [{iri, label}]}], axes: {x: {path, name}, y: {path, name}}}`.

## Steps

1. **Add quadrant to `_VALID_RENDERERS` and `RENDERER_REGISTRY`** in `backend/app/views/router.py` and `backend/app/views/registry.py`:
   - Add `"quadrant"` to the `_VALID_RENDERERS` set (line ~208 in router.py)
   - Add `"quadrant": {"type": "quadrant", "template": "browser/quadrant_view.html"}` to `RENDERER_REGISTRY` in registry.py

2. **Add `_detect_quadrant_axes()` to ViewSpecService** in `backend/app/views/service.py`:
   - Query SHACL shapes for the given type_iri
   - Find properties with `sh:in` containing exactly the values `"high"` and `"low"` (or two string values — keep it general)
   - Return two `PropertyShape` objects (x_axis, y_axis) — prefer property paths containing "urgency" for x and "importance" for y (case-insensitive)
   - Return `(None, None)` if fewer than 2 qualifying properties found
   - Pattern: follow `_detect_status_field()` structure

3. **Add `execute_quadrant_query()` to ViewSpecService** in `backend/app/views/service.py`:
   - Accept `type_iri`, `x_axis: PropertyShape`, `y_axis: PropertyShape`, `x_values: list[str]`, `y_values: list[str]`, optional `scope_filter`
   - Build a SELECT SPARQL query: `SELECT ?s ?label ?xValue ?yValue WHERE { ?s a <type> ; <x_path> ?xValue ; <y_path> ?yValue . OPTIONAL { ?s dcterms:title ?label } }` with scope injection
   - Group results into quadrant buckets: one per (x_value, y_value) combination
   - Return `{"quadrants": [...], "axes": {"x": {...}, "y": {...}}, "total": N}`
   - Assign labels per quadrant: for Eisenhower, high/high="Do First", high/low="Schedule", low/high="Delegate", low/low="Eliminate". Use a generic labeling pattern: "X: {x_val} / Y: {y_val}" unless known framework-specific labels exist.

4. **Add quadrant branch to `generic_view()`** in router.py (insert before the `else: # kanban` block):
   - Follow the exact pattern of the timeline/map branches: check type_iri, call `_detect_quadrant_axes()`, handle no-axes-found with error message, call `execute_quadrant_query()`, build context dict, render `quadrant_view.html`
   - Context must include: `quadrants`, `axes`, `type_label`, `type_iri`, `selected_type`, `types`, `model_view_specs`, `scope_query`, `user_saved_queries`, `model_saved_queries`, `is_generic`, `renderer`, `pagination_base_url`, `pag_extra`, `spec`

5. **Add quadrant branch to `generic_view_data()`** in router.py:
   - Update the guard: add `"quadrant"` to the valid renderers for data endpoint (currently only graph, calendar, map, timeline)
   - Return JSONResponse with quadrant data for the `quadrant` renderer
   - Create **initial `quadrant_view.html`** template in `backend/app/templates/browser/` — use `view-flex-column` wrapper, include `type_filter_pills.html` and `view_toolbar.html`, render a `.quadrant-board` container with 4 `.quadrant-cell` divs using a server-rendered Jinja2 loop. Each cell contains draggable `.quadrant-card` items. Include a `<script>` tag to call `initQuadrant()`. T03 will build the full CSS and JS.

## Must-Haves

- [ ] `"quadrant"` in `_VALID_RENDERERS` and `RENDERER_REGISTRY`
- [ ] `_detect_quadrant_axes()` finds two sh:in properties with "high"/"low" values
- [ ] `execute_quadrant_query()` returns items grouped into 4 quadrant buckets
- [ ] `generic_view()` renders `quadrant_view.html` for `renderer == "quadrant"`
- [ ] `generic_view_data()` returns JSON for `renderer == "quadrant"`
- [ ] Template includes type_filter_pills, view_toolbar, and quadrant grid structure

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — if T04 runs first; otherwise verify manually:
- `python3 -c "from app.views.router import _VALID_RENDERERS; assert 'quadrant' in _VALID_RENDERERS; print('OK')"` (from backend dir)
- `rg 'quadrant' backend/app/views/router.py | wc -l` returns > 5 (multiple references)
- `test -f backend/app/templates/browser/quadrant_view.html && echo OK`

## Inputs

- `backend/app/views/router.py` — existing elif chain to extend (current renderers: table, card, graph, calendar, map, timeline, kanban)
- `backend/app/views/service.py` — ViewSpecService with `_detect_status_field()` and `execute_kanban_query()` as patterns
- `backend/app/views/registry.py` — RENDERER_REGISTRY to extend
- `backend/app/templates/browser/kanban_view.html` — reference template structure
- `models/business-planning/shapes/business-planning.jsonld` — SHACL shapes with sh:in constraints (from T01)

## Expected Output

- `backend/app/views/router.py` — updated with quadrant branches in generic_view() and generic_view_data()
- `backend/app/views/service.py` — updated with _detect_quadrant_axes() and execute_quadrant_query()
- `backend/app/views/registry.py` — updated with quadrant entry in RENDERER_REGISTRY
- `backend/app/templates/browser/quadrant_view.html` — Jinja2 template for quadrant grid
