---
estimated_steps: 52
estimated_files: 3
skills_used: []
---

# T01: Model filter checkboxes + tab persistence

## Description

Add per-model filter checkboxes to the TBox toolbar and client-side node show/hide in ontology-graph.js. Also fix tab persistence by adding `cy.resize()` to `switchOntologyTab()`.

### Context

`ontology-graph.js` fetches graph data with nodes that have a `source` field (e.g. 'gist', 'basic-pkm', 'crm', 'user'). The `_colorForSource()` function assigns colors. The toolbar in `ontology_page.html` currently has graph/tree toggle buttons and a 'Hide gist' checkbox. We need a filter container after the existing controls.

### Key patterns

- Extract distinct source values client-side: `new Set(data.nodes.map(n => n.source))`
- Use `node.hide()` / `node.show()` for Cytoscape element visibility (not CSS classes)
- Hide edges where EITHER endpoint node is hidden: `edge.source().hidden() || edge.target().hidden()`
- Color dots use the same `_colorForSource()` function
- 'All' checkbox as convenience toggle — checked when all individual checkboxes checked
- Export `SemPKM.filterTboxBySource(sourceName, visible)` for programmatic access
- Tab persistence: in `switchOntologyTab()`, after adding `ontology-pane--active`, check `tabId === 'tbox'` and call `cy.resize()` — NO `cy.fit()` (that resets zoom/pan)

## Steps

1. Read `frontend/static/js/ontology-graph.js` to understand the current IIFE structure and `_renderTboxGraph()`.
2. In `_renderTboxGraph()`, after Cytoscape init, extract distinct sources from `data.nodes` via `new Set()`. Build a sorted array (gist first if present, then alpha).
3. Create a `_buildFilterUI(container, sources, isDark)` function that:
   - Creates a `div.tbox-model-filter` element
   - Adds an 'All' checkbox label
   - For each source: adds a checkbox label with a color-dot `span` (background-color from `_colorForSource()`), the source name, and an `onchange` handler
   - 'All' checkbox toggles all others
   - Individual checkbox change recalculates 'All' state
   - Returns the container element
4. Create a `_applySourceFilter(cy, activeSources)` function that:
   - Iterates all nodes — `node.hide()` if `activeSources` doesn't include `node.data('source')`, else `node.show()`
   - Iterates all edges — `edge.hide()` if either endpoint is hidden, else `edge.show()`
5. Insert the filter UI into the toolbar. In `_renderTboxGraph()`, find the `.tbox-view-toolbar` element in the container's parent (the `.tbox-main-view`) and append the filter div after the existing controls.
6. Export `SemPKM.filterTboxBySource` and `SemPKM._tboxSourceColors` (source→color map for external use).
7. Add CSS for `.tbox-model-filter` in `frontend/static/css/workspace.css`:
   - Flex row with gap, wrapping allowed, aligned center
   - `.tbox-filter-dot` — 10px circle with the source color
   - `.tbox-filter-item` — flex row, label+checkbox+dot, font-size 0.78rem matching existing filter toggle
8. In `ontology_page.html`, update `switchOntologyTab()`: after `target.classList.add('ontology-pane--active')`, add:
   ```javascript
   if (tabId === 'tbox') {
     var cy = (window.SemPKM && window.SemPKM._tboxGraph) || window._tboxCy;
     if (cy) { cy.resize(); }
   }
   ```
   No `cy.fit()` — that would reset user's zoom/pan position.
9. Verify with grep checks.

## Must-Haves

- [ ] Filter checkboxes rendered per distinct source in the graph data
- [ ] Color dots match node colors from `_colorForSource()`
- [ ] Unchecking a source hides its nodes AND edges connected to hidden nodes
- [ ] 'All' checkbox toggles all individual checkboxes
- [ ] `cy.resize()` called in `switchOntologyTab()` when TBox tab activates
- [ ] No `cy.fit()` on tab switch — zoom/pan preserved

## Verification

- `grep -q 'filterTboxBySource\|_applySourceFilter\|tbox-model-filter' frontend/static/js/ontology-graph.js && echo 'PASS: filter function exists'`
- `grep -q 'tbox-model-filter' frontend/static/css/workspace.css && echo 'PASS: filter CSS exists'`
- `grep -q 'cy.resize()' backend/app/templates/browser/ontology/ontology_page.html && echo 'PASS: tab persistence fix'`
- `grep -c 'cy.fit()' backend/app/templates/browser/ontology/ontology_page.html` returns at most the existing one in `toggleTboxView` — NOT in `switchOntologyTab`

## Inputs

- ``frontend/static/js/ontology-graph.js` — S01 IIFE with _colorForSource(), _renderTboxGraph(), SemPKM.initTboxGraph()`
- ``backend/app/templates/browser/ontology/ontology_page.html` — S01 template with toolbar, switchOntologyTab(), toggleTboxView()`
- ``frontend/static/css/workspace.css` — S01 .tbox-vertical-split, .tbox-filter-toggle styles`

## Expected Output

- ``frontend/static/js/ontology-graph.js` — adds _buildFilterUI(), _applySourceFilter(), SemPKM.filterTboxBySource export`
- ``backend/app/templates/browser/ontology/ontology_page.html` — cy.resize() added to switchOntologyTab()`
- ``frontend/static/css/workspace.css` — .tbox-model-filter, .tbox-filter-dot, .tbox-filter-item styles`

## Verification

grep -q 'filterTboxBySource' frontend/static/js/ontology-graph.js && grep -q 'tbox-model-filter' frontend/static/css/workspace.css && grep -q 'cy.resize' backend/app/templates/browser/ontology/ontology_page.html && echo 'T01 PASS'
