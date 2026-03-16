# S01: Resizable Canvas Nodes — UAT

**Milestone:** M008
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: Resize interaction and persistence are fully covered by 11 unit tests and 2 E2E tests. The canvas is an existing feature — this slice adds resize handles to it. No new pages or complex UX flows requiring human-experience validation.

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one canvas session exists (or user creates one via Spatial Canvas in explorer)
- At least two objects exist in the knowledge base (for edge rendering test)

## Smoke Test

Open Spatial Canvas, drop an object onto it, hover over the node — a triangular resize indicator should appear at the bottom-right corner. Drag it to make the node wider. Save the canvas, reload the page, open the same session — the node should still be the resized width.

## Test Cases

### 1. Corner resize handle visibility

1. Open Spatial Canvas and add a node (drag from explorer or bulk-drop)
2. Hover over the node
3. **Expected:** A small triangular indicator appears at the bottom-right corner of the node. Cursor changes to diagonal resize (↘) when hovering the corner area.

### 2. Resize a node wider via corner handle

1. Position the mouse over the bottom-right corner of a canvas node
2. Press and hold mouse button on the corner resize handle
3. Drag to the right ~250px
4. Release mouse button
5. **Expected:** Node width increases from ~260px to ~500px (grid-snapped). Node height may also increase if dragged diagonally. The node content reflows to fill the wider space.

### 3. Resize does not interfere with node drag

1. Resize a node to ~500px wide (per test case 2)
2. Click and drag the node's header area (the title bar, not the resize handle)
3. Move the node to a different position on the canvas
4. **Expected:** The node moves without changing its width. The 500px width is preserved. No visual glitches during the move.

### 4. Right edge resize

1. Hover near the right edge of a canvas node (not the corner)
2. Cursor should change to horizontal resize (↔)
3. Drag the right edge to the right
4. **Expected:** Node width increases. Height remains unchanged.

### 5. Bottom edge resize

1. Hover near the bottom edge of a canvas node (not the corner)
2. Cursor should change to vertical resize (↕)
3. Drag the bottom edge downward
4. **Expected:** Node height increases. Width remains unchanged.

### 6. Minimum size constraint

1. Resize a node by dragging the corner handle toward the top-left (making it smaller)
2. Try to shrink below 160px wide or 80px tall
3. **Expected:** Node stops shrinking at 160px width and 80px height. Cannot go smaller.

### 7. Grid snapping during resize

1. Resize a node slowly via the corner handle
2. Observe the width/height values (inspect via browser devtools or `SemPKMCanvas.exportState()`)
3. **Expected:** Width and height snap to the canvas grid increment (multiples of the grid size, typically 8px or similar).

### 8. Save and reload persistence

1. Resize a node to approximately 500px wide
2. Open browser console and run `SemPKMCanvas.exportState()` — note the width value
3. Save the canvas session (via save button or Ctrl+S)
4. Reload the page (F5)
5. Open the same canvas session
6. **Expected:** The resized node renders at ~500px wide. `SemPKMCanvas.exportState()` shows the same width value.

### 9. Edge rendering with resized nodes

1. Place two nodes on the canvas that have an edge between them (e.g. a Project and a Note linked via dcterms:references)
2. Resize the first node to ~500px wide, leave the second at default ~260px
3. **Expected:** The edge line connects to the correct box edges of both nodes — the wider node's connection point adjusts to its actual width. No edge clipping or misalignment.

## Edge Cases

### Backward compatibility with old sessions

1. Open browser console
2. Import a canvas document without width/height fields: `SemPKMCanvas.importState({nodes:[{id:"test",label:"Old Node",x:100,y:100}],edges:[],viewport:{x:0,y:0,scale:1}})`
3. **Expected:** Node renders at default 260px width. No JavaScript errors in console. `SemPKMCanvas.exportState()` does NOT include width or height for this node (undefined, not 0).

### Mixed session with resized and default nodes

1. Place 3 nodes on canvas
2. Resize only the first node to 400px wide
3. Save and reload
4. **Expected:** First node is 400px. Second and third nodes are default 260px. Export state shows width only on the first node.

### Rapid resize followed by immediate drag

1. Resize a node quickly (fast mouse movement on corner handle)
2. Immediately after releasing, click and drag the node header
3. **Expected:** Node drag works normally after resize completes. No "stuck" resize state.

## Failure Signals

- Resize handle not visible on hover → CSS not loaded or `.spatial-node-resize-handle` class missing
- Resize triggers node drag instead → `stopPropagation()` not working on handle's `pointerdown`
- Node snaps back to 260px after resize → `renderNodes()` not reading `node.width` for inline style
- Width/height lost after save/reload → `getDocument()` not serializing dimensions or `applyDocument()` not restoring them
- JavaScript errors mentioning `resizingNodeId` or `resizeHandleType` → state field initialization issue
- Edge misaligned after resize → `edgePoint()` not reading actual `offsetWidth`/`offsetHeight`

## Requirements Proved By This UAT

- CANVAS-01 — Full coverage: resize interaction (test cases 1-7), persistence (test case 8), edge rendering (test case 9), backward compat (edge cases), minimum constraints (test case 6)

## Not Proven By This UAT

- Property flip (CANVAS-02) — separate slice S02
- Embed nodes with resize (CANVAS-03–05) — separate slice S03
- E2E automated regression — covered by `canvas-resize.spec.ts`, not this manual UAT

## Notes for Tester

- The corner handle is intentionally subtle — a small triangular gradient, not a large icon. Look carefully at the bottom-right corner on hover.
- Right edge and bottom edge handles are invisible hit areas (no visual indicator). The cursor change is the only signal.
- Grid snapping means you won't get exact pixel values from free-form dragging — sizes round to the nearest grid increment.
- If the Docker stack was recently restarted, wait for RDF4J to finish initializing before testing canvas save/load.
