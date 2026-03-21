---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T02: Add SPARQL graph visualization tab for triple-pattern results

**Slice:** S05 — SPARQL + Ontology + Graph + Full-Height Polish
**Milestone:** M031

## Description

Users running triple-pattern SPARQL queries (e.g., `SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 50`) can only see results as a table. This task adds a Table/Graph tab switcher above results so users can visualize triple-pattern results as an interactive Cytoscape.js graph. Cytoscape.js is already globally available via CDN in `base.html`.

## Steps

1. **Add triple-pattern detection** in `frontend/static/js/sparql-console.js`. Create a function `isTriplePattern(vars, bindings)` that returns `true` when:
   - `vars` has exactly 3 items, AND
   - Either the var names look like subject/predicate/object patterns (s/p/o, subject/predicate/object, sub/pred/obj), OR
   - In a sample of the first ~10 bindings, most values for all 3 vars are URIs (type === 'uri')
   This heuristic avoids false positives on arbitrary 3-column queries.

2. **Add tab switcher UI** in the `executeQuery()` flow (after `renderResultTable`). When `isTriplePattern(vars, bindings)` returns true, inject a tab bar above the results area (`<div class="sparql-result-tabs">`) with two tabs: "Table" (active by default) and "Graph". The table tab shows the existing `sparql-results-table-wrap` content. The graph tab shows a new `<div class="sparql-graph-container">` with a Cytoscape instance.

3. **Build Cytoscape elements from bindings**. Create a function `buildGraphElements(vars, bindings)` that:
   - Maps var[0] → subject, var[1] → predicate, var[2] → object
   - Collects unique subject and object URIs/values as nodes (id = URI or literal value, label = shortened URI or literal)
   - Creates edges from subject → object with predicate as label
   - Returns `{ nodes: [...], edges: [...] }` in Cytoscape element format
   - Uses `shortenUri()` (from T01) to shorten URI labels

4. **Initialize Cytoscape on Graph tab click**. When the user clicks the Graph tab:
   - Build elements via `buildGraphElements()`
   - Create a Cytoscape instance in the `.sparql-graph-container` div
   - Use an `fcose` or `cose-bilkent` layout (both available via CDN)
   - Style nodes with labels and edges with predicate labels
   - Add basic interactions: fit-to-view button, node hover showing full IRI
   - Follow the pattern from `backend/app/templates/admin/model_ontology_diagram.html` (lines 73-130) for Cytoscape config

5. **Add CSS for tab switcher and graph container** in `frontend/static/css/views.css`. Style `.sparql-result-tabs` as a simple tab bar. Style `.sparql-graph-container` with `min-height: 400px` and the same grid background as `.graph-container`. Ensure the graph container is hidden when the Table tab is active and vice versa.

## Must-Haves

- [ ] `isTriplePattern()` function detects 3-variable queries with URI-heavy results
- [ ] Tab switcher renders only for triple-pattern results (not for arbitrary queries)
- [ ] Graph tab initializes Cytoscape.js with nodes and edges from bindings
- [ ] Nodes show shortened URIs as labels; edges show predicate labels
- [ ] Tab switching works without re-fetching data (both views share the same bindings)

## Verification

- `grep -q "isTriplePattern\|sparql-result-tabs" frontend/static/js/sparql-console.js` — detection function and tab UI exist
- `grep -q "sparql-graph-container\|sparql-result-tabs" frontend/static/css/views.css` — CSS exists
- `grep -q "cytoscape" frontend/static/js/sparql-console.js` — Cytoscape initialization present

## Inputs

- `frontend/static/js/sparql-console.js` — existing `executeQuery()` flow, `renderResultTable()`, `shortenUri()`
- `frontend/static/css/views.css` — existing SPARQL result styles
- `backend/app/templates/admin/model_ontology_diagram.html` — reference Cytoscape.js initialization pattern
- `backend/app/templates/browser/sparql_panel.html` — SPARQL panel HTML structure

## Expected Output

- `frontend/static/js/sparql-console.js` — new `isTriplePattern()`, `buildGraphElements()`, tab switcher logic, Cytoscape init
- `frontend/static/css/views.css` — new `.sparql-result-tabs`, `.sparql-graph-container` styles

## Observability Impact

- **Graph tab detection:** `isTriplePattern()` logs nothing — it's a pure heuristic. To debug, call `isTriplePattern(vars, bindings)` directly in the browser console with sample data.
- **Graph rendering:** The Cytoscape instance is stored in a module-level variable `sparqlCyInstance`. Inspect it in the browser console to check node/edge counts, layout state, or call `sparqlCyInstance.fit()` to refit.
- **Tab switcher DOM:** The `.sparql-result-tabs` element is injected only when `isTriplePattern()` returns true. Absence in the DOM means the detection heuristic didn't trigger — check that the query has exactly 3 vars and URI-heavy bindings.
- **Failure state:** If Cytoscape fails to initialize (e.g., CDN not loaded), a `console.error('Failed to initialize SPARQL graph:', err)` is logged and the graph container shows an error message.
