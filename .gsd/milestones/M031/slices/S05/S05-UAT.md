# S05 UAT: SPARQL + Ontology + Graph + Full-Height Polish

**Preconditions:**
- Docker stack running (`docker compose up -d`)
- At least one Mental Model installed (e.g., Basic PKM)
- Some objects exist in the triplestore (seed data or manually created)
- Browser at `http://localhost:8080`

---

## Test 1: SPARQL IRI Pill Rendering (SPARQL-10)

**Goal:** Model ontology IRIs render as styled vocab pills, not plain spans.

1. Open the SPARQL console (Ctrl+J → SPARQL tab, or bottom panel)
2. Run: `SELECT ?s ?type WHERE { ?s a ?type } LIMIT 20`
3. **Expected:** The `?type` column shows ontology class IRIs as styled pills:
   - `.sparql-vocab-pill` elements with dashed border, italic label, and a small icon badge
   - NOT plain `<span class="sparql-uri">` with raw `urn:sempkm:model:*` strings
4. Run: `SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 20`
5. **Expected:** Predicate IRIs from model ontologies (e.g., `bpkm:taskStatus`) render as vocab pills or shortened QNames, not raw `urn:sempkm:model:basic-pkm:taskStatus`

**Edge case:** Internal IRIs (e.g., `urn:sempkm:query:*`, `urn:sempkm:user:*`) should NOT render as vocab pills — they are system-internal and should show as plain URIs or shortened QNames.

---

## Test 2: Dynamic Prefix Shortening (SPARQL-11)

**Goal:** `shortenUri()` uses dynamic prefixes from the model, not just hardcoded well-known prefixes.

1. Open browser devtools console
2. Check `reversePrefixMap` is populated: `Object.keys(reversePrefixMap).length > 0`
3. Run a SPARQL query that returns model ontology IRIs
4. **Expected:** Model IRIs are shortened using model-declared prefixes (e.g., `pkm:Person` instead of `urn:sempkm:model:basic-pkm:Person`)
5. Well-known prefixes still work: `rdf:type`, `rdfs:label`, `dcterms:title` etc.

---

## Test 3: SPARQL Graph Visualization Tab (SPARQL-09)

**Goal:** Triple-pattern queries show a Table/Graph tab switcher with interactive graph visualization.

1. Open the SPARQL console
2. Run: `SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 30`
3. **Expected:** A tab bar appears above results with "Table" and "Graph" buttons, plus a "Triple pattern detected" hint text
4. Click the "Graph" tab
5. **Expected:** A Cytoscape.js graph renders with:
   - Nodes for unique subjects and objects (blue circles for URIs, round-rectangles for literals)
   - Directed edges labeled with predicate names
   - Node hover shows full IRI in a tooltip
   - Edge hover shows the predicate label
   - Graph is zoomable and pannable
6. Click back to "Table" tab
7. **Expected:** Original table view reappears, no data re-fetch
8. Run a non-triple-pattern query: `SELECT ?s ?label WHERE { ?s rdfs:label ?label } LIMIT 10`
9. **Expected:** No Table/Graph tab switcher appears — only the normal results table

**Edge case:** Run with `LIMIT 5` (small result) — graph should render with dagre layout (hierarchical). Run with `LIMIT 50` — should use fcose layout.

---

## Test 4: TBox Property Description Tooltips (ONTO-04)

**Goal:** Property names in TBox class detail show description tooltips on hover.

1. Navigate to an object (e.g., a Project or Person)
2. Click the type link to open the TBox class detail (or navigate to the ontology browser)
3. Locate a property that has `rdfs:comment` or `skos:definition` in the model ontology
4. Hover over the property name
5. **Expected:** A browser-native tooltip appears showing the property's description text
6. Hover over a property that has no description
7. **Expected:** No empty tooltip appears (the `title` attribute is omitted, not empty)

---

## Test 5: Admin Model Graph Full-Viewport (ONTO-05)

**Goal:** The admin model ontology diagram fills the available viewport height.

1. Navigate to Admin → Models → select a model → Ontology Diagram tab
2. **Expected:** The Cytoscape graph area fills the viewport below the admin nav and model header/tabs — approximately `calc(100vh - 250px)` tall
3. Resize the browser window
4. **Expected:** The graph area adjusts dynamically to fill the new viewport height
5. **Compare:** The graph should NOT have a fixed 600px minimum height that leaves empty space below on large screens or causes scrolling on small screens

---

## Test 6: Admin Graph Edge Hover Tooltips (ONTO-06)

**Goal:** Hovering an edge in the admin model graph shows a popover with property info.

1. On the admin model ontology diagram (from Test 5)
2. Hover over an edge (line connecting two class nodes)
3. **Expected:** A popover appears showing:
   - The property label (e.g., "hasProject")
   - The domain → range path (e.g., "ActionItem → Project")
   - The property description (if available in the model)
4. Move the mouse away from the edge
5. **Expected:** The popover disappears after ~150ms
6. Hover a node
7. **Expected:** The existing node hover popover still works correctly (no regression)

---

## Test 7: Full-Height Graph View (VIEW-13)

**Goal:** The graph view fills its panel height with no outer scrollbar.

1. Open "Graph View" from the explorer sidebar
2. **Expected:** The Cytoscape graph container fills the entire panel area below the toolbar
3. The view should NOT have an outer scrollbar on the view container
4. Resize the dockview panel by dragging a divider
5. **Expected:** The graph area adjusts to fill the new panel size
6. Open the browser devtools → Elements → inspect `.graph-container`
7. **Expected:** Computed style shows `flex: 1` and `min-height: 0`, NOT `height: calc(100% - 90px)`

---

## Test 8: Full-Height Kanban View (VIEW-13)

**Goal:** The kanban view fills its panel height with no outer scrollbar.

1. Open "Kanban View" from the explorer sidebar (requires objects with a status field)
2. **Expected:** The kanban board fills the panel area below the toolbar
3. Columns should scroll vertically within themselves if content overflows
4. The view container itself should NOT have an outer scrollbar
5. Inspect `.kanban-board` in devtools
6. **Expected:** Shows `flex: 1; min-height: 0; overflow-x: auto`

---

## Test 9: Graph Popover Z-Index (VIEW-14)

**Goal:** Node/edge popovers near the top of the graph view render fully visible above all chrome.

1. Open "Graph View" from the explorer sidebar
2. Pan the graph so that a node is near the very top of the view area (close to the dockview tab bar)
3. Hover over that node
4. **Expected:** The popover renders ABOVE the dockview tab bar, fully visible. It should NOT be clipped or hidden behind the toolbar/tabs.
5. In devtools, inspect the popover element
6. **Expected:** The popover is a child of `document.body` (not inside `.graph-container`), with `position: fixed` and `z-index: 9999`
7. Navigate away from the graph view (click another tab)
8. Run in console: `document.body.querySelectorAll('.graph-popover').length`
9. **Expected:** Returns `0` — popovers are cleaned up when the graph is destroyed

---

## Test 10: Table and Cards View Regression Check

**Goal:** Verify table and cards views still work correctly after CSS changes.

1. Open "Table View" from the explorer sidebar
2. **Expected:** Table renders with natural vertical scrolling within the panel. No layout regression.
3. Open "Cards View" from the explorer sidebar
4. **Expected:** Cards render in a grid with natural vertical scrolling. No layout regression.
5. Both views should NOT have the `.view-flex-column` wrapper (they don't need it)

---

## Summary Checklist

| # | Test | Requirement | Pass? |
|---|------|-------------|-------|
| 1 | SPARQL vocab pill rendering | SPARQL-10 | ☐ |
| 2 | Dynamic prefix shortening | SPARQL-11 | ☐ |
| 3 | SPARQL graph visualization tab | SPARQL-09 | ☐ |
| 4 | TBox property tooltips | ONTO-04 | ☐ |
| 5 | Admin graph full-viewport | ONTO-05 | ☐ |
| 6 | Admin graph edge tooltips | ONTO-06 | ☐ |
| 7 | Full-height graph view | VIEW-13 | ☐ |
| 8 | Full-height kanban view | VIEW-13 | ☐ |
| 9 | Graph popover z-index | VIEW-14 | ☐ |
| 10 | Table/cards regression | VIEW-13 | ☐ |
