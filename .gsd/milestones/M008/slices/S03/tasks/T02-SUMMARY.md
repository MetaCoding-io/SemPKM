---
id: T02
parent: S03
milestone: M008
provides:
  - Dual-layer rendering architecture separating regular nodes (innerHTML rebuild) from embed nodes (persistent DOM)
  - addEmbedNode() function for programmatic embed placement with max-8 limit
  - Embed node data model (nodeType: 'embed', embedConfig: {type, id, url, label})
  - Save/load serialization for embed nodes with backward-compatible old session loading
key_files:
  - frontend/static/js/canvas.js
  - frontend/static/css/workspace.css
  - backend/app/templates/browser/canvas_page.html
key_decisions:
  - Embed nodes use CSS.escape() for all data-node-id attribute selectors to safely handle IDs with special characters
  - Embed layer uses pointer-events:none on container with pointer-events:auto on individual embed nodes so clicks pass through to regular nodes below
  - Orphan cleanup runs on every renderNodes() call by diffing embed layer children against state.nodes
  - iframe load event listener attached during initial DOM creation, not re-attached on position updates
patterns_established:
  - Dual-layer pattern: state.layer for innerHTML-rebuilt regular nodes, state.embedLayer for persistent DOM embed nodes
  - Position-only update pattern for embed layer: only style.left/top/width/height change, never innerHTML
  - onEmbedLayerClick handler for embed-specific click events (delete button), separate from onLayerClick
observability_surfaces:
  - setStatus('Embed added: ...') on successful placement
  - showToast('Maximum of 8 embeds reached') on limit rejection
  - SemPKMCanvas.exportState() includes nodeType/embedConfig per embed node
  - SemPKMCanvas.addEmbed() exposed on window for console testing
  - data-embed-type attribute on embed DOM elements for inspection
  - .spatial-embed-loading.loaded class indicates iframe finished loading
duration: 45min
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Dual-layer rendering and embed node type

**Introduced dual-layer canvas architecture where embed iframes persist across renderNodes() innerHTML rebuilds, with full data model, serialization, and cleanup.**

## What Happened

Implemented the architectural crux of the live embeds feature: a second rendering layer (`state.embedLayer` / `.spatial-canvas-embed-layer`) that sits above the regular node layer and manages embed node DOM persistently. When `renderNodes()` rebuilds `state.layer.innerHTML` (destroying all regular node DOM), embed nodes in the embed layer are untouched — only their CSS positioning properties update.

Key changes:
1. Added `<div class="spatial-canvas-embed-layer">` to `canvas_page.html` as a sibling after `.spatial-canvas-layer`
2. In `renderNodes()`, embed nodes (`nodeType === 'embed'`) are skipped from the innerHTML string. After the rebuild, a separate loop creates new embed DOM elements or updates position/size of existing ones, and removes orphans.
3. `addEmbedNode(embedConfig, clientX, clientY)` creates embed nodes with a max-8 limit, generates unique IDs, and exposes as `SemPKMCanvas.addEmbed`.
4. `removeNode()` extended to explicitly remove embed DOM from the embed layer.
5. `getDocument()`/`applyDocument()` extended to serialize/restore `nodeType` and `embedConfig`. Old sessions without these fields load without errors.
6. `applyTransform()` applies the same CSS transform to both layers so pan/zoom stays in sync.
7. `nodeBoxes` now queries `state.viewport` (covering both layers) so edges can connect to embed nodes.
8. Resize handle interaction works on embed nodes via the existing pointer event system (resize DOM lookup extended to check embed layer).
9. CSS for embed layer (pointer-events pass-through), embed node styling, iframe sizing, and loading overlay with fade on load.

## Verification

- ✅ `SemPKMCanvas.addEmbed({type:'view', id:'test', url:'/browser/views/generic/table?embed=1', label:'Table View'}, 500, 300)` — iframe loads with live table content
- ✅ Iframe DOM reference identity preserved after `renderNodes()` call — `sameIframeRef: true`
- ✅ Delete button click removes embed from both DOM and state — `embedLayerChildren: 0, embedNodesInState: 0`
- ✅ Pan/zoom transforms match between layer and embedLayer — `match: true`
- ✅ `exportState()` includes `nodeType: 'embed'` and `embedConfig` for embed nodes, absent for regular nodes
- ✅ Save/restore round-trip: export → clear → import restores embed with iframe reloading content
- ✅ Old session import (no nodeType fields) loads without errors — all regular nodes render normally
- ✅ 9th embed rejected with toast: `Maximum of 8 embeds reached`
- ✅ All 3 nodes (2 regular + 1 embed) queryable from viewport for edge rendering
- ✅ No JS console errors
- ✅ `browser_assert`: embed layer visible, iframe visible, no console errors — all PASS

### Slice-level checks (this task):
- ✅ `SemPKMCanvas.exportState()` includes `nodeType: 'embed'` and `embedConfig` for embed nodes
- ✅ Browser: drag regular node around → iframe doesn't flash/reload (sameIframeRef verified)
- ✅ Browser: attempt 9th embed → toast rejection message
- ⏳ Browser: save canvas, reload → embed nodes restore (verified via importState round-trip; full server save/reload deferred to integration test)
- ⏳ Browser: place embed node via toolbar picker (toolbar picker is T03)
- ⏳ Backend test: `test_canvas_embeds.py` (test file creation deferred to appropriate task)

## Diagnostics

- **Embed presence**: `document.querySelector('.spatial-canvas-embed-layer').children.length` — count of live embed DOM elements
- **Embed state**: `SemPKMCanvas.exportState().nodes.filter(n => n.nodeType === 'embed')` — all embed nodes with config
- **Iframe load status**: `.spatial-embed-loading.loaded` class presence — if absent after several seconds, iframe load failed
- **Layer transform sync**: Compare `document.querySelector('.spatial-canvas-layer').style.transform` vs `document.querySelector('.spatial-canvas-embed-layer').style.transform` — must match

## Deviations

None — implemented exactly as planned.

## Known Issues

None discovered.

## Files Created/Modified

- `frontend/static/js/canvas.js` — dual-layer rendering, addEmbedNode(), embed serialization, nodeBoxes via viewport, embed cleanup in removeNode(), applyTransform for both layers, onEmbedLayerClick handler, addEmbed on public API
- `frontend/static/css/workspace.css` — embed layer positioning, embed node styling, iframe sizing, loading overlay with .loaded fade, dark theme support for embed header/loading
- `backend/app/templates/browser/canvas_page.html` — added `.spatial-canvas-embed-layer` div inside viewport
- `.gsd/milestones/M008/slices/S03/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
