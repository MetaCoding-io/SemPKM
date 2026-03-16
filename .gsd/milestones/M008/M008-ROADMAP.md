# M008: Spatial Canvas — Resizable Nodes, Property Flip & Live Embeds

**Vision:** Transform the spatial canvas from a read-only graph surface into a composable working surface where nodes are resizable, can flip to show properties, and where views, dashboards, SPARQL queries, and objects can be placed as live interactive panels.

## Success Criteria

- User resizes a node to 500px wide by dragging a corner handle, saves canvas, reloads — node is still 500px wide
- User flips an object node to properties view, sees SHACL-derived property table with correct values from the triplestore, flips back to markdown
- User places a Table View on the canvas via toolbar picker, the iframe loads with real triplestore data, rows are clickable
- User drags a dashboard from the explorer onto the canvas, it renders as a resizable iframe with live dashboard content
- Canvas session with mixed node types (regular objects, resized nodes, property-flipped, view embeds, dashboard embeds) saves and restores correctly after page reload
- Edges connect correctly to resized nodes (edgePoint reads offsetWidth/offsetHeight from DOM — automatic)
- Old canvas sessions without width/height/nodeType fields load without errors, defaulting to 260px width

## Key Risks / Unknowns

- **Resize vs drag pointer event conflict** — Both resize handles and node header use pointerdown. Must prove they don't interfere.
- **innerHTML rebuild destroys iframes** — `renderNodes()` rebuilds `state.layer.innerHTML` on every drag frame. Iframes recreated via innerHTML lose loaded state. Dual-layer rendering (static embed layer + dynamic node layer) is the likely solution.
- **htmx navigation inside iframes** — `hx-push-url` and `hx-target` could cause iframe content to navigate away. `?embed=1` must suppress chrome and URL pushing.
- **Property flip endpoint doesn't exist yet** — The existing `get_object()` is too heavy (8 queries, full page context). Need a lightweight JSON endpoint returning SHACL-derived property values.

## Proof Strategy

- Resize vs drag conflict → retire in S01 by proving resize handles work alongside node drag with no interference, edges update correctly, and sizes persist across save/load
- innerHTML rebuild vs iframe persistence → retire in S03 by proving embed nodes survive drag operations and state changes without losing iframe content
- htmx inside iframes → retire in S03 by proving `?embed=1` templates load correctly in iframes with functional interactivity and no navigation escapes

## Verification Classes

- Contract verification: unit tests for canvas properties endpoint, embed URL construction, canvas document serialization with new fields
- Integration verification: canvas ↔ triplestore (property flip fetches real SHACL data), iframe ↔ view/dashboard endpoints (real content renders in embeds), canvas save/load round-trip with all node types
- Operational verification: features work after Docker restart with persisted canvas sessions
- UAT / human verification: browser verification of resize interaction feel, property table rendering, iframe interactivity

## Milestone Definition of Done

This milestone is complete only when all are true:

- All slice deliverables complete — resize, property flip, embeds, tests, and docs shipped
- Node resize persists in canvas document JSON and round-trips through save/load
- Property flip fetches SHACL data from real triplestore and renders inline in the node
- At least view and dashboard embeds render in iframes with real content
- Toolbar picker and explorer drag both create embed nodes
- Canvas save/load preserves all new node types and sizes
- Old canvas sessions load without errors (backward compat)
- E2E Playwright tests pass for resize, property flip, embed placement, and save/load
- User guide updated with canvas features documentation
- No conflict markers in any committed file

## Requirement Coverage

- Covers: CANVAS-01, CANVAS-02, CANVAS-03, CANVAS-04, CANVAS-05
- Partially covers: none
- Leaves for later: none
- Orphan risks: none — all 5 active requirements mapped to slices

**CANVAS-01** (resizable nodes) → primary S01, supporting none
**CANVAS-02** (property flip) → primary S02, supporting none
**CANVAS-03** (view/dashboard embeds) → primary S03, supporting none
**CANVAS-04** (SPARQL/object embeds) → primary S03, supporting none
**CANVAS-05** (embed add UX) → primary S03, supporting none

Research-identified candidate requirements (CANVAS-06 max iframe count, CANVAS-07 lazy loading, CANVAS-08 link routing, CANVAS-09 embed mode for object read) are folded into S03's acceptance criteria rather than tracked as separate requirements. They are table-stakes for embeds to be usable.

## Slices

- [x] **S01: Resizable Canvas Nodes** `risk:high` `depends:[]`
  > After this: User drags corner handle on any canvas node to resize it. Width and height persist across save/load. Edges connect correctly to resized nodes. Old sessions load at default 260px.

- [x] **S02: Property Flip on Object Nodes** `risk:medium` `depends:[]`
  > After this: User clicks flip button on object node header, sees SHACL-derived property table with real values from triplestore, clicks again to return to markdown. Properties cached per-node.

- [x] **S03: Live Embeds — Infrastructure, Types & Add UX** `risk:medium` `depends:[S01]`
  > After this: User places views, dashboards, SPARQL results, and object read views on canvas via toolbar picker or explorer drag. Embeds render as resizable iframes with live content. Save/load preserves embed nodes. Max 8 embeds enforced.

- [x] **S04: E2E Tests & User Guide** `risk:low` `depends:[S01,S02,S03]`
  > After this: Playwright E2E tests cover resize, property flip, embed placement, and save/load. User guide Chapter 29 documents all canvas features.

## Boundary Map

### S01 → S03

Produces:
- Extended canvas node model in `state.nodes[]` with `width`, `height` fields (default 260, undefined means 260)
- `getDocument()` / `applyDocument()` serialize/deserialize width/height with fallback defaults
- Resize handle pointer event system with `state.resizingNodeId` flag and `stopPropagation()` pattern
- CSS `.spatial-node` without fixed width, with `min-width: 160px; min-height: 80px`
- Proven that variable-dimension nodes work with edge rendering (`edgePoint()` reads DOM measurements)

Consumes:
- nothing (first slice)

### S01 → S04

Produces:
- Resize interaction testable end-to-end (save, reload, verify dimensions persist)

### S02 → S04

Produces:
- `GET /api/canvas/properties?iri=<IRI>` endpoint returning JSON `{properties: [...], type_label}`
- Flip button in node header toggling `node.showProperties` state
- Inline property table rendering in node body
- Property cache in `state.propertyCache[nodeId]`

Consumes:
- nothing (independent of S01)

### S03 → S04

Produces:
- `base_embed.html` template (lightweight, no sidebar/CDN zoo)
- `?embed=1` query param support on view, dashboard, SPARQL, and object read endpoints
- Embed node type (`node.nodeType = 'embed'`, `node.embedConfig = {type, id, url}`)
- Dual-layer rendering (static embed layer for iframes + dynamic layer for regular nodes)
- Toolbar picker UI for adding embeds
- Explorer drag-drop extended for view/dashboard/query drag onto canvas
- Canvas document schema with `nodeType`, `embedConfig` fields
- Max embed count enforcement (8)

Consumes:
- S01: resize handle system, variable-dimension CSS, extended node model with width/height
