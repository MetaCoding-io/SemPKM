---
estimated_steps: 9
estimated_files: 3
---

# T02: Dual-layer rendering and embed node type

**Slice:** S03 — Live Embeds — Infrastructure, Types & Add UX
**Milestone:** M008

## Description

The architectural crux of this slice. The current `renderNodes()` in canvas.js rebuilds `state.layer.innerHTML` on every call (line 952), destroying all DOM state. Iframes recreated via innerHTML lose their loaded page. This task introduces dual-layer rendering: regular nodes continue using innerHTML rebuild on `state.layer`, while embed nodes live in a separate persistent `state.embedLayer` where only `style.left`/`style.top`/`style.width`/`style.height` are updated — never innerHTML.

This task also defines the embed node data model (`nodeType: 'embed'`, `embedConfig: {type, id, url, label}`), wires resize handles and edge rendering for the embed layer, and extends serialization for save/load.

## Steps

1. **Add embed layer to canvas HTML template.** In `backend/app/templates/browser/canvas_page.html`, add `<div class="spatial-canvas-embed-layer"></div>` inside `.spatial-canvas-viewport`, as a sibling after `.spatial-canvas-layer`. This ensures both layers receive the same pan/zoom CSS transform from `applyTransform()`.

2. **Initialize embed layer in `mountCanvas()`.** In `frontend/static/js/canvas.js`, after line ~191 where `state.layer` is assigned, add: `state.embedLayer = viewport.querySelector('.spatial-canvas-embed-layer');`. Also register event listeners on the embed layer or ensure the existing viewport-level listeners cover it.

3. **Add `addEmbedNode(embedConfig, clientX, clientY)` function.** Creates a node with: `nodeType: 'embed'`, `embedConfig` (object with `type`, `id`, `url`, `label`), default width 400, height 300, position computed from clientX/clientY (same viewport-to-canvas math as `addNodeFromDrag`). Before adding, count nodes where `nodeType === 'embed'` — reject with `showToast('Maximum of 8 embeds reached')` if >= 8. Push to `state.nodes`, call `renderNodes()`. Expose as `window.SemPKMCanvas.addEmbed = addEmbedNode` for console testing.

4. **Split `renderNodes()` into regular + embed paths.** The core change. In `renderNodes()` (line 891):
   - In the `state.nodes.map()` that builds `nodesHtml`, **skip** nodes where `node.nodeType === 'embed'` — they don't go into the innerHTML string.
   - After the innerHTML rebuild of `state.layer`, process embed nodes separately:
     - For each embed node, check if `state.embedLayer` already has an element with `data-node-id` matching. If not, create the embed node DOM element (article with header, iframe, loading overlay, resize handles) and append to `state.embedLayer`. Set iframe `src` to `node.embedConfig.url`. Attach `load` event listener to iframe that hides the loading overlay.
     - If the element exists, update only `style.left`, `style.top`, `style.width`, `style.height` from the node model.
   - Clean up orphaned embed DOM elements: query all `[data-node-id]` in `state.embedLayer`, remove any whose nodeId is not in `state.nodes`.

5. **Embed node HTML structure.** Each embed node in the embed layer should be:
   ```html
   <article class="spatial-node spatial-node-embed" data-node-id="..." data-embed-type="..." style="left:Xpx;top:Ypx;width:Wpx;height:Hpx;">
     <header class="spatial-node-header">
       <span class="spatial-node-title">Label</span>
       <button class="spatial-node-delete" type="button" title="Remove embed">✕</button>
     </header>
     <div class="spatial-node-embed-body">
       <iframe src="..." class="spatial-embed-iframe"></iframe>
       <div class="spatial-embed-loading">Loading...</div>
     </div>
     <div class="spatial-node-resize-handle"></div>
     <div class="spatial-node-resize-handle-right"></div>
     <div class="spatial-node-resize-handle-bottom"></div>
   </article>
   ```
   Use inline SVG for the delete button (same `SVG_X` constant as regular nodes). No chevron, no flip, no expand buttons — embeds don't have those features.

6. **Extend `removeNode()` to clean up embed DOM.** After filtering `state.nodes` and `state.edges`, also remove the persistent DOM element from `state.embedLayer`: `var embedEl = state.embedLayer.querySelector('[data-node-id="' + nodeId + '"]'); if (embedEl) embedEl.remove();`.

7. **Extend nodeBoxes for edge rendering.** In `renderNodes()`, after the line that builds `nodeBoxes` from `state.layer.querySelectorAll('.spatial-node')` (line ~954), also query `state.embedLayer.querySelectorAll('.spatial-node')` and add those to `nodeBoxes`. This ensures edges can connect to embed nodes. Use `state.viewport.querySelectorAll('.spatial-node')` as a simpler alternative that covers both layers.

8. **Extend `getDocument()` and `applyDocument()` for embed data.** In `getDocument()`: when serializing a node, if `node.nodeType` exists, include `nodeType` and `embedConfig` in the serialized object. In `applyDocument()`: when restoring a node, if `n.nodeType` exists, set `node.nodeType` and `node.embedConfig` on the restored object. Old sessions without `nodeType` field → undefined (treated as regular nodes by the rendering split in step 4).

9. **Add CSS for embed layer and embed nodes.** In `frontend/static/css/workspace.css`:
   - `.spatial-canvas-embed-layer` — same absolute positioning as `.spatial-canvas-layer`, same width/height (9999px). No `pointer-events: none` on the container, `pointer-events: auto` on `.spatial-node-embed` elements. Actually: set `pointer-events: none` on `.spatial-canvas-embed-layer` and `pointer-events: auto` on `.spatial-node-embed` so clicks pass through empty areas to regular nodes below.
   - `.spatial-node-embed` — absolute positioning, same `.spatial-node` base styling but no markdown body styles.
   - `.spatial-embed-iframe` — `width: 100%; height: calc(100% - 36px); border: none; border-radius: 0 0 var(--radius) var(--radius);` (36px = header height).
   - `.spatial-embed-loading` — centered text/spinner over iframe area, hidden on iframe load via `.loaded` class.
   - `applyTransform()` must also apply transform to `state.embedLayer`. Currently it only sets `state.layer.style.transform`. Add `if (state.embedLayer) state.embedLayer.style.transform = state.layer.style.transform;`.

## Must-Haves

- [ ] Embed iframes survive `renderNodes()` innerHTML rebuild — no flash, no reload during regular node drag
- [ ] Embed nodes positioned correctly (pan/zoom transform applied to embed layer)
- [ ] Resize handles work on embed nodes (same pointer event system as regular nodes)
- [ ] Edges connect correctly to embed nodes
- [ ] `getDocument()`/`applyDocument()` serialize and restore nodeType + embedConfig
- [ ] Max 8 embeds enforced with toast message
- [ ] `removeNode()` cleans up embed DOM element
- [ ] Old sessions without nodeType load without errors

## Verification

- In browser, add an embed node via `SemPKMCanvas.addEmbed({type:'view', id:'test', url:'/browser/views/generic/table?embed=1', label:'Table View'}, 500, 300)`. Confirm iframe loads.
- Drag a regular node. Confirm the embed iframe doesn't flash/reload (check: does the loading overlay reappear? It shouldn't.).
- Resize the embed node via corner handle. Confirm iframe content area adjusts.
- Delete the embed node. Confirm DOM element removed from `.spatial-canvas-embed-layer`.
- Pan and zoom the canvas. Confirm embed nodes move with regular nodes.
- Run `SemPKMCanvas.exportState()` — confirm nodeType and embedConfig fields present on embed node, absent on regular nodes.
- Save session, reload page — confirm embed node restores with iframe reloading content.
- Old session (no nodeType fields) — load it, confirm no JS errors, all regular nodes render normally.
- Try adding 9 embeds — confirm 9th is rejected with toast.

## Inputs

- `canvas.js` current state: 1486 LOC with resize handles (S01), property flip (S02), innerHTML rebuild at line 952
- `canvas_page.html` with `.spatial-canvas-viewport > .spatial-canvas-layer` structure
- `workspace.css` with existing `.spatial-node` and resize handle styles
- S01 forward intelligence: `renderNodes()` rebuilds innerHTML every call; `state.resizingNodeId` priority chain; resize handles use stopPropagation
- S02 forward intelligence: three rendering paths in node body (properties, loading, markdown); `fetchNodeProperties` callback calls `renderNodes()` again

## Expected Output

- `frontend/static/js/canvas.js` — dual-layer rendering, addEmbedNode(), embed serialization, nodeBoxes extension, embed cleanup in removeNode()
- `frontend/static/css/workspace.css` — embed layer, embed node, iframe, loading overlay styles
- `backend/app/templates/browser/canvas_page.html` — embed layer div added

## Observability Impact

- **Runtime signals**: `addEmbedNode()` calls `setStatus('Embed added: ...')` for successful placement; toast on max-embed rejection (`Maximum of 8 embeds reached`)
- **DOM inspection**: Embed nodes live in `.spatial-canvas-embed-layer` (separate from `.spatial-canvas-layer`). Each embed has `data-node-id` and `data-embed-type` attributes. Iframe has class `.spatial-embed-iframe`. Loading overlay `.spatial-embed-loading` gains `.loaded` class when iframe finishes loading.
- **State inspection**: `SemPKMCanvas.exportState()` returns `nodeType: 'embed'` and `embedConfig: {type, id, url, label}` for embed nodes. Regular nodes have no `nodeType` field.
- **Failure visibility**: Stale `.spatial-embed-loading` overlay (without `.loaded` class) indicates the iframe failed to load. Iframe 404/500 errors visible in browser network tab. Orphaned embed DOM elements (without matching state node) are automatically cleaned up on each `renderNodes()` call.
