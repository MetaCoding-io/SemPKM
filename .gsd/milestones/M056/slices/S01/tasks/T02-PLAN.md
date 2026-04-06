---
estimated_steps: 38
estimated_files: 2
skills_used: []
---

# T02: Restructure TBox pane layout with graph/tree toggle and bottom detail panel

Rework the TBox pane in `ontology_page.html` from horizontal split (tree left + detail right) to a vertical layout: graph/tree view area on top with a toggle button, detail panel on bottom. The graph view is the primary view per D406.

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

## Inputs

- ``backend/app/templates/browser/ontology/ontology_page.html` — current template with horizontal split layout`
- ``frontend/static/css/workspace.css` — current ontology CSS (lines 563-900)`

## Expected Output

- ``backend/app/templates/browser/ontology/ontology_page.html` — restructured TBox pane with graph/tree toggle and bottom detail panel`
- ``frontend/static/css/workspace.css` — new CSS for vertical split layout, graph container, toggle button`

## Verification

grep -q 'tbox-graph' backend/app/templates/browser/ontology/ontology_page.html && grep -q 'toggleTboxView' backend/app/templates/browser/ontology/ontology_page.html && grep -q 'tbox-vertical-split' frontend/static/css/workspace.css && echo 'PASS'
