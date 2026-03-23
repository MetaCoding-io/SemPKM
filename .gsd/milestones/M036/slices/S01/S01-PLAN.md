# S01: Eisenhower Matrix — Model Archive + Quadrant Renderer

**Goal:** Ship a complete vertical slice from model archive to interactive quadrant view — user installs business-planning model, creates an Eisenhower Matrix, sees items in a 2×2 quadrant view, and drags items between quadrants with RDF property updates.
**Demo:** After installing the business-planning model via Admin > Mental Models, the user creates a new Eisenhower Matrix (bp:EisenhowerMatrix). Opening the object shows its SHACL form. Switching to the quadrant view renders items in a 2×2 grid labeled by urgency×importance. Dragging an item from one quadrant to another fires an `object.patch` command updating `bp:urgency` and `bp:importance` properties on the underlying RDF triples.

## Must-Haves

- `business-planning` model archive with manifest.yaml, ontology, SHACL shapes, ViewSpecs, and seed data for Eisenhower types (bp:EisenhowerMatrix, bp:EisenhowerItem)
- Shared base types (bp:FrameworkItem, bp:QuadrantItem) that S02–S04 will extend
- `quadrant` renderer type added to `_VALID_RENDERERS` and wired into the `generic_view` elif chain
- Backend data endpoint `/browser/views/generic/quadrant/data` returning JSON with items grouped by quadrant
- SHACL shapes with `sh:in` constraints on `bp:urgency` (high/low) and `bp:importance` (high/low) for form generation
- Frontend quadrant template + JS + CSS with drag-to-reclassify using `object.patch` command API
- Dark mode support via CSS variables
- Drag uses `stopPropagation()` to prevent dockview interference (proven pattern from kanban.js)

## Proof Level

- This slice proves: integration (model install → object creation → custom renderer → drag interaction → RDF update)
- Real runtime required: yes (triplestore for SPARQL, model install for SHACL forms)
- Human/UAT required: yes (visual layout, drag interaction)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — unit test for quadrant query builder and data grouping
- Docker Compose stack: install model via Admin, create EisenhowerMatrix, open quadrant view, verify 4 quadrants render
- Manual drag test: drag an item between quadrants and verify the SPARQL data reflects the updated urgency/importance

## Observability / Diagnostics

- Runtime signals: `logger.info("generic_view: renderer=quadrant type=%s ...")` in router, `logger.info("execute_quadrant_query: ...")` in service
- Inspection surfaces: `/browser/views/generic/quadrant/data?type=<iri>` JSON endpoint for debugging quadrant data
- Failure visibility: quadrant template shows `error_message` div when type has no quadrant-axis properties; JS console.error on patch failure with IRI + status
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `backend/app/views/router.py` (elif chain), `backend/app/views/service.py` (query builder pattern), `backend/app/views/registry.py` (RENDERER_REGISTRY), `backend/app/models/manifest.py` (ManifestSchema), `frontend/static/js/kanban.js` (drag pattern reference)
- New wiring introduced: `quadrant` renderer branch in generic_view, `execute_quadrant_query` in ViewSpecService, quadrant data endpoint, `register_renderer("quadrant", ...)` call
- What remains before the milestone is truly usable end-to-end: S02 (BMC renderer), S03 (OKR + Decision Matrix), S04 (extended frameworks), S05 (cross-model edges + E2E + docs)

## Tasks

- [ ] **T01: Create business-planning model archive with Eisenhower types** `est:1h30m`
  - Why: The model archive is the foundation — ontology defines the types, SHACL shapes drive form generation, ViewSpecs declare the quadrant renderer, seed data provides sample items. S02–S04 extend this archive.
  - Files: `models/business-planning/manifest.yaml`, `models/business-planning/ontology/business-planning.jsonld`, `models/business-planning/shapes/business-planning.jsonld`, `models/business-planning/views/business-planning.jsonld`, `models/business-planning/seed/business-planning.jsonld`
  - Do: Create the 6-file model archive. Define shared base types (bp:FrameworkItem, bp:QuadrantItem) and Eisenhower-specific types (bp:EisenhowerMatrix, bp:EisenhowerItem). SHACL shapes must include `sh:in` constraints on bp:urgency and bp:importance. ViewSpecs must declare `sempkm:rendererType: "quadrant"` for Eisenhower. Seed data must include a sample matrix with 4+ items spanning all quadrants. Follow basic-pkm patterns exactly for JSON-LD context, property groups, and icon definitions.
  - Verify: `cd backend && .venv/bin/python -c "from app.models.manifest import parse_manifest; from pathlib import Path; m = parse_manifest(Path('/app/models/business-planning')); print(m.modelId, m.version)"` succeeds in Docker container, or locally: `python -c "from backend.app.models.manifest import parse_manifest; from pathlib import Path; m = parse_manifest(Path('models/business-planning')); print(m.modelId, m.version)"`
  - Done when: manifest.yaml validates, all JSON-LD files parse without error, SHACL shapes have correct sh:in constraints, ViewSpecs declare quadrant renderer type

- [ ] **T02: Wire quadrant renderer into view router + backend data endpoint** `est:1h30m`
  - Why: The view router needs a `quadrant` branch in the elif chain (matching the kanban/calendar/map/timeline pattern) and a `/browser/views/generic/quadrant/data` JSON endpoint. The ViewSpecService needs `_detect_quadrant_axes()` and `execute_quadrant_query()` methods.
  - Files: `backend/app/views/router.py`, `backend/app/views/service.py`, `backend/app/views/registry.py`, `backend/app/templates/browser/quadrant_view.html`
  - Do: (1) Add "quadrant" to `_VALID_RENDERERS` set. (2) Add `elif renderer == "quadrant"` branch in `generic_view()` — detect two sh:in axis properties via `_detect_quadrant_axes()`, call `execute_quadrant_query()`, render `quadrant_view.html`. (3) Add quadrant branch to `generic_view_data()` returning JSON `{quadrants: [{x: "high", y: "high", label: "Do First", items: [...]}, ...]}`. (4) Add `_detect_quadrant_axes()` to ViewSpecService — finds two properties with sh:in ["high","low"] values, preferring paths containing "urgency"/"importance". (5) Add `execute_quadrant_query()` to ViewSpecService — SELECT query grouping items by the two axis values. (6) Register "quadrant" in RENDERER_REGISTRY. (7) Create basic `quadrant_view.html` Jinja2 template (the JS/CSS comes in T03).
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — test `_detect_quadrant_axes` returns correct fields for Eisenhower shape, test `execute_quadrant_query` returns 4 quadrant buckets
  - Done when: quadrant route serves HTML template, data endpoint returns JSON with 4 quadrant groups, unit tests pass

- [ ] **T03: Frontend quadrant renderer — template, CSS, drag-to-reclassify JS** `est:1h30m`
  - Why: The visual 2×2 quadrant grid and drag-to-reclassify interaction are the user-facing deliverable of this slice. Must support dark mode and prevent dockview drag interference.
  - Files: `backend/app/templates/browser/quadrant_view.html`, `frontend/static/js/quadrant.js`, `frontend/static/css/quadrant.css`
  - Do: (1) Build `quadrant_view.html` with type_filter_pills, view_toolbar, and a `.quadrant-board` container with 4 `.quadrant-cell` divs arranged in a CSS Grid 2×2 layout. Each cell has axis labels (e.g., "Urgent + Important → Do First") and contains draggable `.quadrant-card` items. (2) Create `quadrant.css` with CSS Grid layout, axis labels on borders, quadrant color coding (green/yellow/orange/red for priority quadrants), dark mode via CSS variables, `.view-flex-column` wrapper for full-height. (3) Create `quadrant.js` with `initQuadrant(boardEl)` — HTML5 drag-drop handlers with `stopPropagation()`, on drop: extract target quadrant's x/y axis values, fire two `object.patch` commands (one for each axis property), optimistic DOM move with revert on failure. Follow kanban.js patterns exactly. (4) Wire `<script>` tag in template to call `initQuadrant()`.
  - Verify: Start Docker stack, install business-planning model, create an EisenhowerMatrix with seed data, open quadrant view — 4 quadrants visible with items placed correctly, drag an item to a different quadrant and verify the item moves and stays after page reload.
  - Done when: 2×2 grid renders with correct axis labels and color coding, items display in correct quadrants based on urgency/importance values, drag-to-reclassify updates both axis properties via command API, dark mode works, dockview drag interference prevented

- [ ] **T04: Quadrant backend unit tests** `est:45m`
  - Why: Backend unit tests verify the quadrant axis detection and query builder logic independently of a running triplestore, ensuring the data pipeline is correct before integration testing.
  - Files: `backend/tests/test_quadrant.py`
  - Do: (1) Test `_detect_quadrant_axes()` with mock SHACL shapes — verify it finds two sh:in properties with high/low values. (2) Test `_detect_quadrant_axes()` returns None when no quadrant-compatible properties exist. (3) Test the SPARQL query builder produces correct SELECT with two axis bindings. (4) Test quadrant grouping logic — items distributed into 4 buckets by (x,y) axis values, with an "unset" bucket for items missing axis values. Follow the pattern in existing tests (e.g., test_kanban.py if it exists, or other service tests).
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — all tests pass
  - Done when: 4+ test cases pass covering axis detection, query building, and result grouping

## Files Likely Touched

- `models/business-planning/manifest.yaml`
- `models/business-planning/ontology/business-planning.jsonld`
- `models/business-planning/shapes/business-planning.jsonld`
- `models/business-planning/views/business-planning.jsonld`
- `models/business-planning/seed/business-planning.jsonld`
- `backend/app/views/router.py`
- `backend/app/views/service.py`
- `backend/app/views/registry.py`
- `backend/app/templates/browser/quadrant_view.html`
- `frontend/static/js/quadrant.js`
- `frontend/static/css/quadrant.css`
- `backend/tests/test_quadrant.py`
