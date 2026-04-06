# S02 Research: Multi-Model Filter + Visual Polish + Persistence

## Calibration: Light Research

This is straightforward work applying established patterns already in the codebase. The ontology-graph.js IIFE, the graph.js popover system, and the CSS theming approach are all proven. Client-side filtering is a known pattern (`filterGraph()` in graph.js). Tab persistence needs one line (`cy.resize()`) in an existing function. The main integration challenge is wiring a filter UI into ontology-graph.js and adding a popover — both follow existing patterns exactly.

## Requirements Owned

| Req | Description | Key Constraint |
|-----|-------------|----------------|
| R018 | Hover popover correctly anchored to graph node | Must use body-append + position:fixed (dockview stacking context escape per KNOWLEDGE.md) |
| R020 | Multi-select model filter updates graph live | Client-side filtering — no server re-fetch needed for 170 nodes |
| R022 | Graph state persists across TBox/ABox/RBox tab switches | `cy.resize()` call in `switchOntologyTab()` |

## Summary

S01 delivered a working Cytoscape dagre graph in the TBox tab with source-based node coloring, node tap → detail panel, and a graph/tree toggle. S02 adds three features on top: (1) model filter checkboxes, (2) hover popovers, (3) tab switch persistence.

### What Exists (S01 deliverables)

**`ontology-graph.js`** — IIFE exporting `SemPKM.initTboxGraph(containerId)`. Fetches from `/browser/ontology/tbox/graph-data`, builds Cytoscape elements with per-source colors via `_colorForSource()`, renders dagre TB layout. Stores instance at `SemPKM._tboxGraph` and `window._tboxCy`. Has hover class feedback (`node.hovered`) and tap → `loadClassDetail()`. Theme switching via `sempkm:theme-changed`. Cleanup via `registerCleanup()`.

**`ontology_page.html`** — Vertical split layout. Toolbar has graph/tree toggle buttons + "Hide gist" checkbox. `switchOntologyTab()` toggles `.ontology-pane--active` class (CSS `display:block/none`). `toggleTboxView()` switches graph/tree and calls `cy.resize()` + `cy.fit()`.

**Node data structure:** Each Cytoscape node has `data: {id, label, source, sourceColor, borderColor}`. The `source` field is one of: `"gist"`, `"user"`, `"sempkm"`, or a model ID string like `"basic-pkm"`, `"crm"`, `"business-planning"`.

**Graph data endpoint:** `GET /browser/ontology/tbox/graph-data` returns `{nodes: [{id, label, source}], edges: [{source, target, label}]}`. Does NOT currently return `available_models` metadata.

### What's Missing (S02 scope)

1. **Model filter UI** — No filter controls exist. Need checkboxes or pills per model source with "All" toggle. Place in the toolbar (`.tbox-view-toolbar`).

2. **Client-side filtering** — `ontology-graph.js` has no filter function. Need to show/hide nodes by `source` data attribute. Pattern from `graph.js:filterGraph()` — toggle CSS class on elements, hide edges where either endpoint is filtered. Cytoscape doesn't use CSS classes for display — use `ele.style('display', 'none')` or `ele.hide()`/`ele.show()`.

3. **Hover popover** — `ontology-graph.js` only has hover class feedback (size increase). No popover. Need body-appended popover showing class label, source model, and basic metadata. The `graph.js` popover pattern is the reference: create `div.graph-popover`, append to `document.body`, position with `position:fixed` using container `getBoundingClientRect()` + rendered position, viewport overflow adjustment. The existing `.graph-popover` CSS in `views.css` is fully reusable.

4. **Tab switch persistence** — `switchOntologyTab()` in the template's inline `<script>` toggles pane classes but does NOT call `cy.resize()`. When TBox pane goes from `display:none` back to `display:block`, Cytoscape's container has stale dimensions. Fix: add `cy.resize()` call in `switchOntologyTab()` when activating the TBox tab.

5. **Available models metadata** — The filter UI needs to know which models have classes in the graph. Two approaches: (a) extract distinct `source` values from the returned nodes client-side, or (b) add `available_models` to the API response. Client-side extraction is simpler and avoids a backend change — just `new Set(data.nodes.map(n => n.source))`.

## Recommendation

### Approach

Three independent features with minimal interdependency:

**Feature 1: Model Filter (R020)**
- Extract distinct `source` values from fetched graph data in `ontology-graph.js`
- Render checkbox controls in the toolbar area (after "Hide gist")
- On checkbox change: iterate nodes, call `node.hide()` for unchecked sources, `node.show()` for checked. Hide edges where either endpoint is hidden. No re-layout needed — positions preserved.
- Add color dots next to model labels using the existing `_colorForSource()` palette
- "All" checkbox as a convenience toggle

**Feature 2: Hover Popover (R018)**
- Add body-appended popover div in `_renderTboxGraph()` following graph.js pattern exactly
- On `mouseover` node (with 250ms delay): show popover with label, source badge, IRI
- Position: `container.getBoundingClientRect()` + `node.renderedPosition()` + offset
- Viewport overflow clamping (right/bottom edge)
- On `mouseout`: delayed hide (100ms) to allow mouse-into-popover
- Register cleanup to remove popover div from body

**Feature 3: Tab Persistence (R022)**
- In `switchOntologyTab()` (inline script in `ontology_page.html`): after setting `ontology-pane--active`, check if TBox tab activated and call `cy.resize()`.
- No `cy.fit()` — that would reset the user's zoom/pan position, defeating persistence.

### File Changes

| File | Change |
|------|--------|
| `frontend/static/js/ontology-graph.js` | Add model filter extraction, filter toggle function, popover creation/positioning/show/hide, `SemPKM.filterTboxBySource()` export |
| `backend/app/templates/browser/ontology/ontology_page.html` | Add filter container div in toolbar, add `cy.resize()` to `switchOntologyTab()`, wire filter UI rendering |
| `frontend/static/css/workspace.css` | Add `.tbox-model-filter` styles (checkbox row, color dots) |

### Natural Task Decomposition

1. **T01: Model filter + source legend** — Add filter UI to toolbar, client-side show/hide by source, color-coded labels. Largest unit of work.
2. **T02: Hover popover** — Body-appended popover on node hover with viewport clamping. Independent from T01.
3. **T03: Tab persistence + polish** — `cy.resize()` on tab switch, verify graph survives tab round-trip. Smallest unit.

Tasks are independent — T01/T02 can be done in any order. T03 is a one-line fix plus verification.

### Verification Strategy

- **R020 (filter):** Grep for `filterTboxBySource` in ontology-graph.js. Grep for filter container in template. Manual: load graph → uncheck a model → nodes disappear → recheck → nodes reappear.
- **R018 (popover):** Grep for `graph-popover` creation in ontology-graph.js. Grep for `document.body.appendChild` in ontology-graph.js. Grep for `position: fixed` usage.
- **R022 (persistence):** Grep for `cy.resize()` in `switchOntologyTab` in template. Manual: zoom graph → switch to ABox → switch back to TBox → graph at same zoom.

## Skill Discovery

No additional skills needed. All technologies (Cytoscape.js, CSS, vanilla JS IIFE, Jinja2 templates) are already established patterns in the codebase. No external libraries to add.
