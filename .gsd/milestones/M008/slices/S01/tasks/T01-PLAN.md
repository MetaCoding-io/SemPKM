---
estimated_steps: 9
estimated_files: 2
---

# T01: Implement resize handles, interaction, and persistence

**Slice:** S01 — Resizable Canvas Nodes
**Milestone:** M008

## Description

Add resize handles to canvas nodes, implement the pointer event system for resizing, persist width/height in the canvas document JSON, and ensure backward compatibility for old sessions without dimensions.

The key risk this retires is **resize vs drag pointer event conflict**. Both resize handles and node header use `pointerdown`. The solution: resize handle's `pointerdown` calls `event.stopPropagation()` and sets `state.resizingNodeId`, which causes `onPointerMove` to compute new dimensions instead of drag offsets.

## Steps

1. **CSS: Remove fixed width, add min constraints.** In `frontend/static/css/workspace.css`, change `.spatial-node` from `width: 260px` to `min-width: 160px; min-height: 80px`. The node width will now be controlled by inline styles (when resized) or default to content-based width. Add a default `width: 260px` that can be overridden by inline style — this ensures non-resized nodes keep their current appearance.

   Actually, the better approach: keep a CSS default width but make it overridable. Set `.spatial-node { width: 260px; min-width: 160px; min-height: 80px; }` — the inline `style="width:Xpx"` from renderNodes will override the CSS default when a node has been resized. This preserves backward compat visually.

2. **CSS: Resize handle styles.** Add `.spatial-node-resize-handle` positioned absolutely at the bottom-right corner of the node. Cursor: `nwse-resize`. Size: ~12×12px. Semi-transparent, visible on hover/selected state. Also add `.spatial-node-resize-handle-right` (right edge, `ew-resize` cursor) and `.spatial-node-resize-handle-bottom` (bottom edge, `ns-resize` cursor) for edge resizing. The bottom-right corner handle is the primary one.

3. **JS: Add resize handle HTML to `renderNodes()`.** Inside the node `<article>` template in `renderNodes()`, append a `<div class="spatial-node-resize-handle"></div>` after the markdown body. When a node has `width` or `height` set, apply inline `style="width:Xpx; height:Xpx"` on the `<article>` element.

4. **JS: Add `state.resizingNodeId` and resize tracking state.** Add to `state`:
   - `resizingNodeId: null` — ID of node being resized
   - `resizeStartX: 0`, `resizeStartY: 0` — pointer start position in screen coords
   - `resizeStartWidth: 0`, `resizeStartHeight: 0` — node dimensions at resize start

5. **JS: Resize `pointerdown` handler.** In `onPointerDown`, before the node drag check, detect if `event.target.closest('.spatial-node-resize-handle')`. If so:
   - Call `event.stopPropagation()` to prevent bubbling to node drag
   - Find the parent `.spatial-node` element and its data-node-id
   - Look up the node model
   - Read current DOM dimensions: `el.offsetWidth`, `el.offsetHeight`
   - Set `state.resizingNodeId`, `state.resizeStartX/Y` from event, `state.resizeStartWidth/Height` from DOM
   - Return early (do not enter drag or pan mode)

6. **JS: Resize `pointerMove` handler.** In `onPointerMove`, check `state.resizingNodeId` first (before `state.nodeDragId` check). If resizing:
   - Compute deltaX = `(event.clientX - state.resizeStartX) / state.scale` (account for zoom)
   - Compute deltaY = `(event.clientY - state.resizeStartY) / state.scale`
   - New width = `snapToGrid(Math.max(160, state.resizeStartWidth + deltaX))`
   - New height = `snapToGrid(Math.max(80, state.resizeStartHeight + deltaY))`
   - Update node model: `node.width = newWidth; node.height = newHeight`
   - Apply directly to DOM element to avoid full re-render on every frame: find the element by `data-node-id` and set `style.width` and `style.height`. Only call `renderNodes()` at the end (in `onPointerUp`) for a clean final state.
   - Actually, since `renderNodes()` is called on every drag frame already (for node dragging), we should be consistent. But resize is different — we don't need to rebuild innerHTML for resize. Instead, just update the inline style. Call `renderNodes()` once on `pointerUp` to finalize edge positions.

7. **JS: Resize `pointerUp` handler.** In `onPointerUp`, check `state.resizingNodeId`. If set:
   - Clear `state.resizingNodeId`
   - Call `renderNodes()` to finalize edges and DOM state
   - Return early

8. **JS: Extend `getDocument()` and `applyDocument()`.** In `getDocument()`, add `width` and `height` to the node serialization (only when they're defined — undefined means default 260px). In `applyDocument()`, read `width` and `height` with no default — undefined means "use CSS default" (260px). In `renderNodes()`, apply inline style only when `node.width` is defined.

9. **JS: Update bulk-drop `colWidth`.** The `addNodesFromBulkDrop` function uses `var colWidth = 260 + GRID`. This is fine as a default — new nodes don't have custom widths. No change needed here.

## Must-Haves

- [ ] `.spatial-node` has `min-width: 160px; min-height: 80px` in CSS
- [ ] Resize handle visible on each node (bottom-right corner at minimum)
- [ ] Resize via pointer events works without triggering node drag
- [ ] Width/height snapped to grid during resize
- [ ] `getDocument()` serializes width/height when defined
- [ ] `applyDocument()` restores width/height (undefined = CSS default 260px)
- [ ] Old sessions without width/height load without errors
- [ ] Node inline style applies resized dimensions in `renderNodes()`

## Verification

- Open canvas in browser, add a node, resize it by dragging the corner handle
- Confirm drag still works (header drag moves node, corner drag resizes)
- Save canvas, reload page — resized node keeps its dimensions
- Create a canvas session via API without width/height fields, load it — nodes render at 260px default
- Check edges between a resized node and a normal node — edges connect to correct box edges

## Observability Impact

- **New state field:** `state.resizingNodeId` — non-null while a resize is in progress. Inspectable via `SemPKMCanvas.exportState()` indirectly (the node's `width`/`height` are updated in real-time during resize, so calling `exportState()` mid-resize returns current dimensions).
- **Persisted fields:** `width` and `height` on each node in the canvas document JSON. Present only when the node has been resized; absent means CSS default (260px).
- **DOM diagnostic:** Resized nodes have explicit `style="width:Xpx; height:Xpx"` on the `<article>` element. Non-resized nodes have no width/height inline style.
- **CSS diagnostic:** If `.spatial-node-resize-handle` elements are not visible on hover/selection, the CSS is not loaded or not specific enough.
- **Failure shapes:** If resize doesn't start on handle mousedown, the `pointerdown` handler isn't matching `.spatial-node-resize-handle`. If resize triggers drag instead, `stopPropagation()` is not firing.

## Inputs

- `frontend/static/js/canvas.js` — existing canvas implementation with `renderNodes()`, `onPointerDown/Move/Up`, `getDocument()`, `applyDocument()`, `state` object
- `frontend/static/css/workspace.css` — existing `.spatial-node` styles starting at line 4816
- Roadmap decisions: D127 (custom handles over CSS resize), min 160×80, grid snapping

## Expected Output

- `frontend/static/js/canvas.js` — extended with resize handle HTML, pointer event system, width/height persistence
- `frontend/static/css/workspace.css` — updated `.spatial-node` styles + new `.spatial-node-resize-handle` styles
