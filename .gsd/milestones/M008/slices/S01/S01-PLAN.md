# S01: Resizable Canvas Nodes

**Goal:** Canvas nodes can be resized by dragging corner/edge handles. Width and height persist in the canvas document JSON and survive save/load round-trips. Old sessions without dimensions default to 260px.
**Demo:** User drags the bottom-right corner of a canvas node to 500px wide, saves canvas, reloads page, node is still 500px wide. Edges connect correctly to the resized node.

## Must-Haves

- Corner and edge resize handles on every `.spatial-node`
- Resize via pointer events with `stopPropagation()` to prevent node drag interference
- Min constraints: 160px width, 80px height
- Width/height stored per-node in `getDocument()` output and restored by `applyDocument()`
- Backward compat: old sessions without `width`/`height` default to 260px width, auto height
- Grid snapping applied to resize dimensions
- Edges auto-adapt (already proven: `edgePoint()` reads `el.offsetWidth`/`el.offsetHeight`)

## Proof Level

- This slice proves: integration (resize interaction + persistence + edge rendering)
- Real runtime required: yes (browser interaction for pointer events, save/load round-trip)
- Human/UAT required: no (E2E test covers it, but resize "feel" may warrant human check)

## Verification

- `e2e/tests/17-spatial-canvas/canvas-resize.spec.ts` — E2E test covering:
  - Resize a node via pointer events on the resize handle
  - Verify the node's rendered width changed
  - Save canvas, reload page, verify dimensions persisted
  - Load a session without width/height fields, verify 260px default
- `backend/tests/test_canvas_resize.py` — Unit test for document serialization round-trip with width/height fields and backward compat defaults
- **Diagnostic check:** After resize, `SemPKMCanvas.exportState()` includes `width`/`height` on the resized node; if resize failed silently, these fields are absent. Browser console should show no errors during resize interaction.

## Observability / Diagnostics

- Runtime signals: `state.resizingNodeId` tracks active resize (inspectable via `SemPKMCanvas.exportState()`)
- Inspection surfaces: `SemPKMCanvas.exportState()` returns document with width/height per node; browser devtools can inspect `.spatial-node` inline styles
- Failure visibility: resize handle CSS visibility is the primary diagnostic — if handles aren't visible, the CSS isn't loaded; if resize doesn't start, `pointerdown` isn't firing on the handle element
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: none (first slice)
- New wiring introduced: `state.resizingNodeId` flag, resize pointer event handlers, `width`/`height` fields in node model
- What remains before the milestone is truly usable end-to-end: S02 (property flip), S03 (embeds), S04 (E2E + docs)

## Tasks

- [x] **T01: Implement resize handles, interaction, and persistence** `est:2h`
  - Why: This is the core deliverable — resize handles on canvas nodes, pointer event system for resizing, width/height persistence in canvas document, and backward compatibility for old sessions.
  - Files: `frontend/static/js/canvas.js`, `frontend/static/css/workspace.css`
  - Do: (1) Remove fixed `width: 260px` from `.spatial-node` CSS, add `min-width: 160px; min-height: 80px`. (2) Add resize handle HTML to `renderNodes()` — a `<div class="spatial-node-resize-handle">` at bottom-right corner of each node. (3) Add resize CSS (handle positioning, cursor, visibility on hover/selected). (4) Add `state.resizingNodeId` + resize pointer event logic in `onPointerDown`/`onPointerMove`/`onPointerUp` — handle's `pointerdown` sets `state.resizingNodeId`, `stopPropagation()` prevents node drag. (5) During resize move: compute new width/height from pointer delta, snap to grid, enforce min constraints, apply via inline `style.width`/`style.height` on the node element AND update the node model's `width`/`height`. (6) Extend `getDocument()` to serialize `width`/`height` per node. (7) Extend `applyDocument()` to restore `width`/`height` with default fallback (undefined means 260px width, auto height). (8) In `renderNodes()`, apply `style="width:Xpx"` from `node.width` when defined. (9) Update bulk-drop `colWidth` to use a reasonable default (260) rather than assuming all nodes are 260px.
  - Verify: Open canvas in browser, resize a node by dragging corner handle, save, reload — dimensions persist. Drag a node header — resize doesn't interfere. Old sessions load at 260px default.
  - Done when: Resize works without interfering with drag, dimensions persist across save/load, old sessions load without errors at 260px default width.

- [x] **T02: Unit test and E2E test for resize persistence** `est:1h`
  - Why: Proves the risk (resize vs drag conflict) is retired, proves persistence round-trip, and provides regression safety for S03 which builds on this.
  - Files: `backend/tests/test_canvas_resize.py`, `e2e/tests/17-spatial-canvas/canvas-resize.spec.ts`
  - Do: (1) Write `test_canvas_resize.py` — unit test that constructs a canvas document JSON with width/height fields, round-trips through a mock save/load, and verifies dimensions are preserved. Also test backward compat: document without width/height fields should parse without error. (2) Write `canvas-resize.spec.ts` — E2E test: navigate to canvas, drop a node via API, use Playwright pointer events to resize the node's handle, assert rendered width changed, save canvas via API, reload, assert dimensions persisted. Also verify that a session created without width/height loads cleanly (260px default).
  - Verify: `cd backend && python -m pytest tests/test_canvas_resize.py -v` passes. E2E test in `canvas-resize.spec.ts` passes against running Docker stack.
  - Done when: Both test files pass, covering resize interaction, persistence round-trip, backward compat, and edge rendering with resized nodes.

## Files Likely Touched

- `frontend/static/js/canvas.js` — resize handles, pointer events, state model, getDocument/applyDocument
- `frontend/static/css/workspace.css` — remove fixed width, add resize handle styles, min constraints
- `backend/tests/test_canvas_resize.py` — unit test for document serialization
- `e2e/tests/17-spatial-canvas/canvas-resize.spec.ts` — E2E test for resize + persistence
