---
estimated_steps: 39
estimated_files: 2
skills_used: []
---

# T03: Wire Cytoscape graph initialization, node click → detail, and graph/tree toggle

Create `ontology-graph.js` that fetches TBox graph data from the API endpoint (T01), initializes a Cytoscape instance with dagre TB layout in the graph container (T02), handles node clicks to load class detail in the bottom panel, and integrates with the graph/tree toggle.

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

## Inputs

- ``backend/app/ontology/router.py` — T01 output: the /browser/ontology/tbox/graph-data endpoint`
- ``backend/app/templates/browser/ontology/ontology_page.html` — T02 output: restructured template with graph container and toggle`
- ``frontend/static/js/graph.js` — reference patterns for Cytoscape init, styling, popover, cleanup`
- ``frontend/static/css/workspace.css` — T02 output: CSS for graph container`

## Expected Output

- ``frontend/static/js/ontology-graph.js` — new Cytoscape graph module for TBox visualization`
- ``backend/app/templates/browser/ontology/ontology_page.html` — updated with script tag and init call for ontology-graph.js`

## Verification

test -f frontend/static/js/ontology-graph.js && grep -q 'initTboxGraph' frontend/static/js/ontology-graph.js && grep -q 'apiFetch' frontend/static/js/ontology-graph.js && grep -q 'dagre' frontend/static/js/ontology-graph.js && echo 'PASS'
