# S01: TBox Graph API + Hierarchical Rendering + Detail Panel

**Goal:** TBox tab in the Ontology Viewer shows a hierarchical Cytoscape graph with gist classes at the top layer and model types below, with a toggle to switch between graph/tree view, and a bottom detail panel that loads class properties/relationships/instance count when a node is clicked.
**Demo:** After this: Open Ontology Viewer → TBox tab shows a hierarchical Cytoscape graph with gist classes at top, model types below. Toggle between graph/tree view. Click a node → detail panel shows class properties and instance count.

## Tasks
- [x] **T01: Added GET /browser/ontology/tbox/graph-data JSON endpoint returning all TBox classes and subClassOf edges as Cytoscape-compatible graph data** — Create a new JSON endpoint at `/browser/ontology/tbox/graph-data` that queries all TBox classes across gist + installed model ontology graphs + user-types and returns Cytoscape-compatible graph data.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| RDF4J triplestore | Return empty {nodes:[], edges:[]} with logged error | Same — async query timeout logged | Should not occur — SPARQL result format is fixed |

## Steps

1. Read `backend/app/ontology/service.py` — understand `get_ontology_graph_iris()`, `get_root_classes()`, `_build_from_clauses()` patterns
2. Add a new method `get_tbox_graph_data()` to `OntologyService` that:
   - Gets all ontology graph IRIs via `get_ontology_graph_iris()`
   - Queries ALL `owl:Class` instances (not just roots) with their labels and `rdfs:subClassOf` parents
   - Returns nodes as `[{id: iri, label: str, source: 'gist'|'model-id'|'user'}]`
   - Returns edges as `[{source: parent_iri, target: child_iri, label: 'subClassOf'}]` (direction: parent→child for dagre TB to put parents on top)
   - Determines `source` using the existing `_property_source()` helper
   - Filters out owl:Thing and blank nodes
3. Add a new route `GET /browser/ontology/tbox/graph-data` to `backend/app/ontology/router.py` that:
   - Calls `ontology_service.get_tbox_graph_data()`
   - Returns `JSONResponse` with `{nodes: [...], edges: [...]}`
   - Catches exceptions and returns empty arrays with error logged
4. Write unit tests in `backend/tests/test_ontology_graph.py`:
   - Test that `get_tbox_graph_data()` returns correct node structure
   - Test that edges connect correct parent→child pairs
   - Test that source labels are correctly assigned
   - Mock the triplestore client to return known SPARQL results

## Must-Haves

- [ ] `get_tbox_graph_data()` queries ALL classes across all ontology graphs, not just roots
- [ ] Nodes include `id` (IRI), `label`, and `source` fields
- [ ] Edges represent `rdfs:subClassOf` with direction parent→child (so dagre TB puts parents at top)
- [ ] owl:Thing nodes and blank nodes are excluded
- [ ] Endpoint returns JSON, not HTML
- [ ] Error handling: empty arrays returned on SPARQL failure, not 500

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_ontology_graph.py -v` passes
- The endpoint is reachable and returns valid JSON with nodes and edges arrays

## Observability Impact

- Signals added: `logger.info("TBox graph-data: %d nodes, %d edges from %d graphs", ...)` on successful query
- How a future agent inspects: `curl localhost:4000/browser/ontology/tbox/graph-data` (with auth cookie)
- Failure state exposed: SPARQL errors logged with `exc_info=True`
  - Estimate: 45m
  - Files: backend/app/ontology/service.py, backend/app/ontology/router.py, backend/tests/test_ontology_graph.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_ontology_graph.py -v
- [x] **T02: Restructured TBox pane from horizontal tree+detail split to vertical graph/tree view on top with toggle and detail panel on bottom** — Rework the TBox pane in `ontology_page.html` from horizontal split (tree left + detail right) to a vertical layout: graph/tree view area on top with a toggle button, detail panel on bottom. The graph view is the primary view per D406.

## Steps

1. Read `backend/app/templates/browser/ontology/ontology_page.html` — understand current TBox pane structure
2. Read workspace.css lines 563-900 — understand current ontology CSS
3. Restructure the `#ontology-tbox` pane in `ontology_page.html`:
   - Replace `.tbox-split` (horizontal) with a new `.tbox-vertical-split` (vertical flex column)
   - Top area: `.tbox-main-view` containing:
     - A small toolbar with graph/tree toggle button (graph active by default)
     - `.tbox-graph-container` div (visible by default) — empty div with `id="tbox-graph"` for Cytoscape to mount into
     - `.tbox-tree-container` div (hidden by default) — wraps the existing tree scroll + filter bar content
   - Bottom area: `.tbox-detail-pane` (same as existing, just moves to bottom)
   - The toggle button uses `data-view="graph"` / `data-view="tree"` to switch visibility
4. Add a `toggleTboxView(btn, viewName)` function in the `<script>` block that:
   - Shows/hides `.tbox-graph-container` and `.tbox-tree-container`
   - Updates toggle button active state
   - On switching to graph: if Cytoscape instance exists, calls `cy.resize()` to recalculate dimensions
5. Add CSS in `frontend/static/css/workspace.css` for:
   - `.tbox-vertical-split` — flex column, height 100%
   - `.tbox-main-view` — flex: 1, min-height: 0, position relative
   - `.tbox-graph-container` — width 100%, height 100%, position absolute (fills the main view area)
   - `.tbox-tree-container` — same dimensions, hidden by default
   - `.tbox-view-toggle` — small button group in toolbar
   - `.tbox-detail-pane` — adjust for bottom position (height ~250px, border-top, overflow-y auto)
6. Ensure the "Hide gist" checkbox and existing tree htmx triggers still work when tree view is visible
7. Ensure all existing modals (create/edit/delete class, property) still work — they are positioned via `.ccf-overlay` which is absolute/fixed, so layout changes shouldn't affect them

## Must-Haves

- [ ] Graph view is the default/primary view when TBox tab loads
- [ ] Toggle button switches between graph and tree views
- [ ] Bottom detail panel shows "Select a class to view its details" placeholder by default
- [ ] Existing tree functionality (expand/collapse, hide gist filter, lazy-load children) works when tree is shown
- [ ] Graph container has id="tbox-graph" for Cytoscape mounting
- [ ] Graph container fills 100% width and height of the main view area
- [ ] All existing modals (create class, create property, edit, delete) still function

## Verification

- `grep -q 'tbox-graph' backend/app/templates/browser/ontology/ontology_page.html` confirms graph container exists
- `grep -q 'toggleTboxView' backend/app/templates/browser/ontology/ontology_page.html` confirms toggle function exists
- `grep -q 'tbox-vertical-split' frontend/static/css/workspace.css` confirms new layout CSS exists
- Visual check: open Ontology Viewer → TBox tab shows graph container area (empty until T03 wires JS) and toggle button
  - Estimate: 30m
  - Files: backend/app/templates/browser/ontology/ontology_page.html, frontend/static/css/workspace.css
  - Verify: grep -q 'tbox-graph' backend/app/templates/browser/ontology/ontology_page.html && grep -q 'toggleTboxView' backend/app/templates/browser/ontology/ontology_page.html && grep -q 'tbox-vertical-split' frontend/static/css/workspace.css && echo 'PASS'
- [ ] **T03: Wire Cytoscape graph initialization, node click → detail, and graph/tree toggle** — Create `ontology-graph.js` that fetches TBox graph data from the API endpoint (T01), initializes a Cytoscape instance with dagre TB layout in the graph container (T02), handles node clicks to load class detail in the bottom panel, and integrates with the graph/tree toggle.

## Steps

1. Read `frontend/static/js/graph.js` — understand existing Cytoscape patterns (init, style builder, popover, layout registry, cleanup)
2. Read `backend/app/templates/browser/ontology/ontology_page.html` (T02 output) — understand the graph container ID and toggle mechanism
3. Create `frontend/static/js/ontology-graph.js` as a new IIFE module that:
   - Exports `window.SemPKM.initTboxGraph(containerId)` function
   - Fetches `/browser/ontology/tbox/graph-data` via `apiFetch()`
   - Converts response nodes/edges to Cytoscape elements format
   - Assigns per-source colors: gist nodes get a neutral slate color, each model source gets a distinct color (use a small palette), user-types get a teal accent
   - Initializes Cytoscape with dagre TB layout (`rankDir: 'TB'`, `rankSep: 60`, `nodeSep: 30`)
   - Styles nodes with labels, source-based colors, and selection highlight
   - On `tap` node event: calls `loadClassDetail(nodeIri)` (already defined in ontology_page.html) to load detail in the bottom panel
   - On `mouseover`/`mouseout` node events: adds/removes `.hovered` class for visual feedback
   - Stores the cy instance as `window.SemPKM._tboxGraph` for cleanup and toggle resize
   - Registers cleanup via `window.SemPKM.registerCleanup()` if available
4. Add a `<script src="/js/ontology-graph.js"></script>` tag in `ontology_page.html` (or lazy-load it)
5. Wire the graph initialization: when TBox tab is active and graph view is shown, call `SemPKM.initTboxGraph('tbox-graph')` — add this call to the template's `<script>` block, triggered on page load or on TBox tab activation
6. Wire the toggle: when switching to graph view, call `cy.resize()` + `cy.fit()` to recalculate layout after visibility change. When switching from graph to tree, no special handling needed.
7. Handle dark mode: listen for `sempkm:theme-changed` event and rebuild the Cytoscape stylesheet (same pattern as graph.js `switchGraphTheme`)
8. Handle empty state: if the API returns 0 nodes, show a "No ontology classes found" message in the container

## Must-Haves

- [ ] Cytoscape graph renders with dagre TB layout (top-down hierarchy)
- [ ] Gist classes appear at the top of the hierarchy, model classes below them
- [ ] Clicking a node loads class detail in the bottom panel
- [ ] Graph fills the available space (100% width and height)
- [ ] Graph respects dark/light theme
- [ ] Empty state handled gracefully
- [ ] Cleanup registered to destroy Cytoscape instance on panel dispose
- [ ] Uses `apiFetch()` for the data fetch (per KNOWLEDGE.md Pattern 13)

## Negative Tests

- **Malformed inputs**: API returns empty nodes array → show "No ontology classes found" message
- **Error paths**: API fetch fails → show error message in container, log to console
- **Boundary conditions**: Single node with no edges → graph renders the lone node centered

## Verification

- `test -f frontend/static/js/ontology-graph.js` confirms the file exists
- `grep -q 'initTboxGraph' frontend/static/js/ontology-graph.js` confirms the export
- `grep -q 'apiFetch' frontend/static/js/ontology-graph.js` confirms proper fetch usage
- `grep -q 'dagre' frontend/static/js/ontology-graph.js` confirms dagre layout usage
- Visual verification: Open Ontology Viewer → TBox shows hierarchical graph → click node → detail panel populates → toggle to tree → tree works → toggle back to graph → graph still there
  - Estimate: 1h
  - Files: frontend/static/js/ontology-graph.js, backend/app/templates/browser/ontology/ontology_page.html
  - Verify: test -f frontend/static/js/ontology-graph.js && grep -q 'initTboxGraph' frontend/static/js/ontology-graph.js && grep -q 'apiFetch' frontend/static/js/ontology-graph.js && grep -q 'dagre' frontend/static/js/ontology-graph.js && echo 'PASS'
