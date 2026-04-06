# S02: Multi-Model Filter + Visual Polish + Persistence

**Goal:** Multi-model filter updates the TBox graph live, hover popovers are correctly anchored, and graph state persists across tab switches.
**Demo:** After this: Filter graph by model (checkboxes) → graph updates live. Per-model color coding distinguishes sources. Switch tabs → graph persists. Hover nodes → popovers anchored correctly.

## Tasks
- [x] **T01: Added per-model filter checkboxes with color dots to TBox toolbar and fixed graph persistence on tab switch via cy.resize()** — ## Description

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
  - Estimate: 45m
  - Files: frontend/static/js/ontology-graph.js, backend/app/templates/browser/ontology/ontology_page.html, frontend/static/css/workspace.css
  - Verify: grep -q 'filterTboxBySource' frontend/static/js/ontology-graph.js && grep -q 'tbox-model-filter' frontend/static/css/workspace.css && grep -q 'cy.resize' backend/app/templates/browser/ontology/ontology_page.html && echo 'T01 PASS'
- [ ] **T02: Body-appended hover popover on graph nodes** — ## Description

Add a hover popover to TBox graph nodes following the exact graph.js body-appended popover pattern (KNOWLEDGE.md: 'Popovers inside dockview panels must escape stacking context via document.body'). Shows class label, source badge, and IRI on hover. Correctly anchored via `position:fixed` + `getBoundingClientRect()`.

### Reference pattern from graph.js

The existing popover in `frontend/static/js/graph.js` (lines 430-585) establishes the proven pattern:
1. Create `div.graph-popover`, append to `document.body`
2. On `mouseover` node: start 250ms timer → build HTML → set `display:block`, position with `container.getBoundingClientRect()` + `node.renderedPosition()` + offset
3. Viewport overflow clamping: check `pRect.right > window.innerWidth - 8`, `pRect.bottom > window.innerHeight - 8`
4. On `mouseout` node: 100ms delayed hide, cancelled if mouse enters popover (`_popoverHovered` flag)
5. Popover has `mouseenter`/`mouseleave` handlers for the hover-into-popover UX
6. Cleanup: `registerCleanup()` removes popover from body

The CSS is fully reusable — `.graph-popover` in `frontend/static/css/views.css` already has `position:fixed`, `z-index:9999`, themed colors.

### Popover content for ontology nodes

Simpler than graph.js (no 'Open' button, no properties table):
- Header: class label (`.graph-popover-label`) + source badge (`.graph-popover-type`, text = source name, background-color = source color)
- Body: full IRI in monospace (`.graph-popover-iri`)
- No footer/open button — node tap already loads detail panel

## Steps

1. Read `frontend/static/js/ontology-graph.js` to find the exact location in `_renderTboxGraph()` after Cytoscape init.
2. In `_renderTboxGraph()`, after the cy instance is created:
   a. Create popover div: `var popover = document.createElement('div'); popover.className = 'graph-popover'; document.body.appendChild(popover);`
   b. Add `_popoverHovered` flag and `_hoverTimer` variable
   c. Add `mouseenter`/`mouseleave` on the popover div (same as graph.js)
3. Replace the existing `mouseover`/`mouseout` handlers on cy nodes:
   a. `mouseover`: clear any pending hide timer, start 250ms delay timer. On fire: build popover HTML, position using `container.getBoundingClientRect()` + `evt.target.renderedPosition()`, clamp to viewport, show.
   b. `mouseout`: clear hover timer, start 100ms delayed hide (check `_popoverHovered`).
4. Keep the existing `hovered` class add/remove for the size feedback (it's independent of the popover).
5. Build popover HTML:
   ```javascript
   var d = node.data();
   var html = '<div class="graph-popover-header">' +
     '<span class="graph-popover-label">' + _esc(d.label) + '</span>' +
     '<span class="graph-popover-type" style="background-color:' + d.sourceColor + '">' + _esc(d.source) + '</span>' +
   '</div>' +
   '<div style="padding:6px 14px 10px;"><span class="graph-popover-iri">' + _esc(d.id) + '</span></div>';
   ```
6. Add a simple `_esc()` HTML escaping function (same pattern as graph.js) if not already in scope.
7. In the cleanup registration, add `document.body.removeChild(popover)` to the cleanup callback.
8. Add one small CSS addition to `workspace.css`: `.tbox-graph-container .graph-popover-type` style for dynamic background-color override (the source badge needs inline `background-color` from `sourceColor` data, but the base `.graph-popover-type` has a fixed `background: var(--color-primary)` — the inline style will override correctly, but add a comment noting this intentional override).

## Must-Haves

- [ ] Popover appended to `document.body` (not inside the dockview panel)
- [ ] Positioned via `position:fixed` using `getBoundingClientRect()` + `renderedPosition()`
- [ ] Viewport overflow clamping (right edge, bottom edge)
- [ ] 250ms hover delay before showing (debounce)
- [ ] 100ms delayed hide with hover-into-popover cancellation
- [ ] Shows class label, source badge with source color, and full IRI
- [ ] `registerCleanup()` removes popover from body on panel destruction

## Verification

- `grep -q 'document.body.appendChild' frontend/static/js/ontology-graph.js && echo 'PASS: body-appended popover'`
- `grep -q 'graph-popover' frontend/static/js/ontology-graph.js && echo 'PASS: uses graph-popover class'`
- `grep -q 'getBoundingClientRect' frontend/static/js/ontology-graph.js && echo 'PASS: position:fixed anchoring'`
- `grep -q 'removeChild.*popover\|popover.*remove' frontend/static/js/ontology-graph.js && echo 'PASS: cleanup registered'`
  - Estimate: 30m
  - Files: frontend/static/js/ontology-graph.js
  - Verify: grep -q 'document.body.appendChild' frontend/static/js/ontology-graph.js && grep -q 'graph-popover' frontend/static/js/ontology-graph.js && grep -q 'getBoundingClientRect' frontend/static/js/ontology-graph.js && echo 'T02 PASS'
