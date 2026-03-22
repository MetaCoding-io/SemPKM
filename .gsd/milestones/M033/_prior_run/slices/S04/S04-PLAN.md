# S04: Isometric 2.5D Graph View

**Goal:** Add an "Isometric" layout option to the graph view that stratifies nodes into horizontal z-layers by RDF type, creating a 2.5D visual effect with translucent layer planes.
**Demo:** User selects "Isometric" from the graph view layout picker. Nodes arrange on horizontal z-layers stratified by RDF type. Translucent layer planes visible behind nodes. Edges connect across layers. Switching to another layout cleanly removes layer nodes.

## Must-Haves

- Custom Cytoscape layout extension registered via `cytoscape('layout', 'isometric', ...)`
- Nodes grouped by `data('type')` into layers with grid positioning within each layer
- Isometric stagger offset between layers creating visual depth
- Compound parent nodes per layer with translucent background (layer planes)
- "Isometric" option appears in the graph layout picker dropdown
- Compound layer nodes cleaned up when switching to another layout
- Layer nodes skipped by popover handler (no tooltips on layer planes)
- Filter propagates to compound parents (fade when all children filtered)
- Node expansion re-runs isometric layout when active

## Verification

- `test -f frontend/static/js/isometric-layout.js` — layout extension file exists
- `grep -q "isometric" backend/app/views/router.py` — backend registers layout
- `grep -q "isometric-layout.js" backend/app/templates/base.html` — script loaded
- `grep -q "'isometric'" frontend/static/js/graph.js` — registered in LAYOUT_REGISTRY
- `grep -q "_isometricLayer" frontend/static/js/graph.js` — compound parent handling exists
- `grep -q "_isometricLayer" frontend/static/js/isometric-layout.js` — layer sentinel flag set
- `node -e "const fs=require('fs'); const src=fs.readFileSync('frontend/static/js/isometric-layout.js','utf8'); if(!src.includes('layoutPositions')) process.exit(1); if(!src.includes(\"cytoscape('layout'\")) process.exit(1); console.log('OK')"` — correct Cytoscape extension protocol

## Tasks

- [x] **T01: Create isometric layout extension** `est:1h30m`
  - Why: The core ~200-line JS file that implements the custom Cytoscape layout — grouping nodes by type into layers, computing isometric grid positions, injecting compound parent nodes for translucent layer planes.
  - Files: `frontend/static/js/isometric-layout.js`
  - Do: Implement IsometricLayout constructor + run() + stop(). Group nodes by `data('type')` into layers. Compute grid positions within each layer with vertical stagger between layers. Inject compound parent nodes with `_isometricLayer: true` sentinel. Register via `cytoscape('layout', 'isometric', IsometricLayout)`. Handle edge cases: single-type graphs, missing types → "Other" layer, cap at 8 layers.
  - Verify: `node -e "const fs=require('fs'); const src=fs.readFileSync('frontend/static/js/isometric-layout.js','utf8'); if(!src.includes('layoutPositions')) process.exit(1); if(!src.includes(\"cytoscape('layout'\")) process.exit(1); console.log('OK')"`
  - Done when: `isometric-layout.js` exists with a valid Cytoscape layout extension that computes layered positions

- [x] **T02: Wire isometric layout into graph system and verify** `est:1h`
  - Why: The layout extension file alone doesn't appear in the UI or integrate with existing graph features. This task connects it to the layout picker, style system, cleanup logic, popover handler, filter, and expansion — then verifies the full integration.
  - Files: `frontend/static/js/graph.js`, `backend/app/views/router.py`, `backend/app/templates/base.html`
  - Do: (1) Add `isometric-layout.js` script tag to base.html after graph.js. (2) Add `{"name": "isometric", "label": "Isometric"}` to both `available_layouts` arrays in router.py (~line 431 and ~line 1090). (3) Add `'isometric'` entry to `LAYOUT_REGISTRY` in graph.js. (4) Add compound parent node styles (`node[_isometricLayer]`) to `buildSemanticStyle()`. (5) Add isometric cleanup to `changeLayout()` — un-parent children and remove layer nodes when switching away. (6) Skip `_isometricLayer` nodes in the mouseover popover handler. (7) Propagate filter to compound parents. (8) Re-run isometric layout on expansion if active.
  - Verify: All verification commands from the slice-level verification section pass
  - Done when: "Isometric" appears in graph layout picker, compound parent styles render, switching layouts cleans up layer nodes, popovers don't fire on layer planes

## Observability / Diagnostics

- **Runtime signals:** `console.debug('[isometric]')` logs layer count and node count on each layout run. `window._sempkmIsometricState` exposes `{ layers, totalNodes, timestamp }` for browser console inspection.
- **Inspection surfaces:** In browser DevTools, `window._sempkmIsometricState.layers` shows each layer's parentId, label, nodeCount, and layerIndex. `cy.nodes('[_isometricLayer]')` in the Cytoscape console lists all compound parent nodes.
- **Failure visibility:** If no nodes have a `type` data field, all nodes go to a single "Other" layer — visible in the diagnostic state and console log. If the layout extension is not loaded, `changeLayout('isometric')` silently falls back to `{ name: 'isometric' }` which Cytoscape ignores — check `LAYOUT_REGISTRY` keys to diagnose.
- **Redaction:** No user data or secrets involved. Type IRIs and labels are logged — acceptable for diagnostic use.

## Files Likely Touched

- `frontend/static/js/isometric-layout.js` (new)
- `frontend/static/js/graph.js`
- `backend/app/views/router.py`
- `backend/app/templates/base.html`
