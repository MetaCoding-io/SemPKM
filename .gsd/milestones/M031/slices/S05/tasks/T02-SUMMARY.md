---
id: T02
parent: S05
milestone: M031
provides:
  - Triple-pattern detection heuristic (isTriplePattern) for 3-var SPARQL queries
  - Table/Graph tab switcher UI injected above results when triple-pattern detected
  - Cytoscape.js graph visualization with nodes from s/o bindings and edges from predicates
  - Graph elements builder (buildGraphElements) using shortenUri() for node/edge labels
  - Lazy Cytoscape initialization on first Graph tab click (no re-fetch needed)
key_files:
  - frontend/static/js/sparql-console.js
  - frontend/static/css/views.css
key_decisions:
  - Used dagre layout for small graphs (<30 nodes) and fcose for larger ones, matching the admin model graph pattern
  - Lazy-initialize Cytoscape on first Graph tab click rather than eagerly, to avoid wasting cycles when users only want the table
  - Literal nodes use round-rectangle shape with fixed width to visually distinguish from URI nodes (blue circles)
patterns_established:
  - sparqlCyInstance is a module-level variable — destroy before re-creating to prevent memory leaks from multiple query runs
  - injectGraphTab() cleans up previous tab bar and graph container before injecting new ones on each query execution
observability_surfaces:
  - Browser console: sparqlCyInstance is module-level, inspectable in devtools (e.g., sparqlCyInstance.nodes().length)
  - console.error on graph init failure in initSparqlGraph()
  - DOM inspection: .sparql-result-tabs element present means triple-pattern was detected; .sparql-graph-container holds the Cytoscape canvas
  - Cytoscape wheel sensitivity warning is expected and confirms successful initialization
duration: 30m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Add SPARQL graph visualization tab for triple-pattern results

**Add Table/Graph tab switcher for triple-pattern SPARQL results with interactive Cytoscape.js graph visualization showing shortened URI labels**

## What Happened

Added three new functions to `sparql-console.js`:

1. **`isTriplePattern(vars, bindings)`** — Detects triple-pattern queries by checking if the result has exactly 3 variables and either (a) the var names match common s/p/o patterns or (b) >60% of sampled bindings have URI values across all 3 vars.

2. **`buildGraphElements(vars, bindings)`** — Converts SPARQL bindings into Cytoscape element arrays. Maps vars[0]→subject, vars[1]→predicate, vars[2]→object. Deduplicates nodes, shortens URI labels via `shortenUri()`, and creates directed edges with predicate labels.

3. **`initSparqlGraph(container, vars, bindings)`** — Initializes a Cytoscape instance with theme-aware styling, dagre/fcose layout selection, node hover tooltips (showing full IRI), and edge hover tooltips. Literal nodes use a distinct round-rectangle shape.

4. **`injectGraphTab(tableWrap, vars, bindings)`** — Called after `renderResultTable()` in `executeQuery()`. When `isTriplePattern()` returns true, injects a tab bar with Table/Graph buttons and a "Triple pattern detected" hint. Graph tab lazy-initializes Cytoscape on first click. Tab switching toggles display without re-fetching data.

Added CSS in `views.css` for `.sparql-result-tabs` (tab bar with active state styling), `.sparql-graph-container` (400px min-height graph area with grid background), `.sparql-graph-tooltip` (monospace hover tooltip), and `.sparql-graph-error` (error state).

## Verification

All task-level and slice-level checks pass. UAT confirmed:
- Running `SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10` shows Table/Graph tab switcher with "Triple pattern detected" hint
- Graph tab renders Cytoscape visualization with nodes labeled `sempkm:current` and `sempkm:StateGraph`, edge labeled `rdf:type`
- Tab switching between Table and Graph works without re-fetching
- No console errors from graph initialization (only expected Cytoscape wheel sensitivity warning)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "isTriplePattern\|sparql-result-tabs" frontend/static/js/sparql-console.js` | 0 | ✅ pass | <1s |
| 2 | `grep -q "sparql-graph-container\|sparql-result-tabs" frontend/static/css/views.css` | 0 | ✅ pass | <1s |
| 3 | `grep -q "cytoscape" frontend/static/js/sparql-console.js` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('backend/app/sparql/router.py').read())"` | 0 | ✅ pass | <1s |
| 5 | `python3 -c "import ast; ast.parse(open('backend/app/ontology/service.py').read())"` | 0 | ✅ pass | <1s |
| 6 | `python3 -c "import ast; ast.parse(open('backend/app/admin/router.py').read())"` | 0 | ✅ pass | <1s |
| 7 | `grep -q "sparql-graph-tab\|sparql-result-tabs" frontend/static/js/sparql-console.js` | 0 | ✅ pass | <1s |
| 8 | Browser assert: tab switcher visible, Graph tab visible, "Triple pattern detected" text | all pass | ✅ pass | UAT |

## Diagnostics

- **Inspect graph tab detection:** Run a 3-variable query in SPARQL console. If `.sparql-result-tabs` is absent from the DOM, the `isTriplePattern()` heuristic didn't trigger — check that vars have exactly 3 items and bindings are URI-heavy.
- **Inspect graph rendering:** In browser console, `sparqlCyInstance` shows the Cytoscape instance. `sparqlCyInstance.nodes().length` and `sparqlCyInstance.edges().length` show element counts. `sparqlCyInstance.fit()` refits the view.
- **Graph init errors:** `console.error('Failed to initialize SPARQL graph:', err)` logs if Cytoscape.js fails to initialize (e.g., CDN not loaded).
- **Tab switching:** Both Table and Graph views share the same `bindings` array via closure — no re-fetch occurs. The graph container uses `display:none`/`display:block` toggling.

## Deviations

- Fixed `width: 'label'` deprecation in literal node style by using fixed `width: 80` instead — Cytoscape deprecated label-based sizing.
- Changed dagre detection from `typeof cytoscapeDagre` to `typeof dagre` since the CDN registers the extension automatically via the dagre global.
- Required a Docker frontend rebuild to pick up CSS changes (built assets are content-hashed and minified via `build.js`).

## Known Issues

- The Cytoscape "custom wheel sensitivity" console warning is cosmetic and expected — it fires because we set `wheelSensitivity: 0.3` following the admin graph pattern.
- In the collapsed bottom panel, the graph area is small. Users should expand the SPARQL panel for better graph visibility.

## Files Created/Modified

- `frontend/static/js/sparql-console.js` — Added `isTriplePattern()`, `buildGraphElements()`, `initSparqlGraph()`, `injectGraphTab()` functions; added `sparqlCyInstance` module var; integrated graph tab injection into `executeQuery()` flow
- `frontend/static/css/views.css` — Added `.sparql-result-tabs`, `.sparql-result-tab`, `.sparql-graph-tab-hint`, `.sparql-graph-container`, `.sparql-graph-tooltip`, `.sparql-graph-error` styles
- `.gsd/milestones/M031/slices/S05/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M031/slices/S05/S05-PLAN.md` — Marked T02 done
