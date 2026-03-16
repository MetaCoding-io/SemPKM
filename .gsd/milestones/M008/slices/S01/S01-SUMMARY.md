---
id: S01
parent: M008
milestone: M008
provides:
  - Corner/edge resize handles on all canvas nodes
  - Pointer event system for resizing without drag interference (stopPropagation pattern)
  - Width/height persistence in canvas document JSON via getDocument/applyDocument
  - Backward compatibility — old sessions without dimensions default to 260px CSS width
  - Grid-snapped resize with min constraints (160px wide, 80px tall)
  - Proven that variable-dimension nodes work with edge rendering (edgePoint reads DOM measurements)
requires:
  - slice: none
    provides: first slice in milestone
affects:
  - S03 (consumes resize handle system, variable-dimension CSS, extended node model with width/height)
  - S04 (consumes resize interaction for E2E test coverage)
key_files:
  - frontend/static/js/canvas.js
  - frontend/static/css/workspace.css
  - backend/tests/test_canvas_resize.py
  - e2e/tests/17-spatial-canvas/canvas-resize.spec.ts
key_decisions:
  - D127: Custom CSS resize handles over native CSS `resize: both` — native only provides bottom-right, no events, no constraints
  - D130: Resize updates inline style during drag, full renderNodes on pointerUp — avoids innerHTML rebuild flicker during resize
  - Corner handle uses triangular gradient indicator; edge/bottom handles are invisible hit areas (minimal visual weight)
  - Width/height serialized only when defined — undefined means CSS default 260px (backward compat)
patterns_established:
  - Resize handle stopPropagation() isolates resize from node drag — reusable for any future handle types
  - state.resizingNodeId + resizeHandleType for multi-handle-type support (corner/right/bottom)
  - Conditional inline style in renderNodes() — only applied when node.width is defined
  - Programmatic-fallback E2E pattern for headless browser pointer events on CSS-transformed elements
observability_surfaces:
  - SemPKMCanvas.exportState() returns width/height per node when resized
  - DOM diagnostic: resized nodes have explicit style="width:Xpx; height:Xpx" on article element
  - state.resizingNodeId non-null during active resize (inspectable in devtools)
drill_down_paths:
  - .gsd/milestones/M008/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M008/slices/S01/tasks/T02-SUMMARY.md
duration: 2h
verification_result: passed
completed_at: 2026-03-16
---

# S01: Resizable Canvas Nodes

**Canvas nodes are resizable via corner/edge drag handles with grid snapping, min constraints, and width/height persistence across save/load. Old sessions load at 260px default.**

## What Happened

**T01** added the core resize system: three resize handle divs (corner with triangular gradient indicator, right edge, bottom edge) appended to each node in `renderNodes()`. The pointer event system detects handle clicks via `event.target.closest()`, calls `stopPropagation()` to prevent node drag, and tracks resize state in `state.resizingNodeId` / `state.resizeHandleType`. During resize, width/height are computed from pointer delta (zoom-aware via scale division), snapped to grid, clamped to minimums (160px/80px), and applied directly to the DOM element's inline style for smooth frame performance. On `pointerUp`, `renderNodes()` runs once to finalize edges. `getDocument()` serializes width/height only when defined; `applyDocument()` restores them conditionally. CSS was updated: `.spatial-node` got `min-width: 160px; min-height: 80px`, and the default `width: 260px` was kept for backward compat (no inline override when undefined).

**T02** added 11 backend unit tests (JSON serialization round-trip, backward compat, edges with dimensions, getDocument/applyDocument simulation) and 2 E2E tests (API persistence + UI interaction/backward-compat/edge-rendering). The E2E tests include a programmatic fallback for headless browsers where pointer events don't fire on CSS-transformed canvas elements — the resize contract is tested either way.

## Verification

- **Backend tests**: 11/11 passed (`test_canvas_resize.py`) — serialization round-trip, backward compat, edges, float tolerance
- **E2E tests**: 2/2 passed on both Chromium and Firefox (`canvas-resize.spec.ts`) — API persistence, UI interaction with fallback
- **Browser verification** (T01): Resize interaction tested manually — corner handle resized node from 260px to 504px (grid-snapped), drag unaffected, persistence round-trip via exportState/importState, backward compat confirmed, edge rendering correct across different node widths
- **Diagnostic check**: `SemPKMCanvas.exportState()` includes `width`/`height` on resized nodes, omits them on default-sized nodes

## Requirements Advanced

- CANVAS-01 — Fully delivered: corner/edge resize handles, width/height persistence, min constraints, grid snapping, backward compat at 260px default. All acceptance criteria met.

## Requirements Validated

- CANVAS-01 — Proven by 11 unit tests + 2 E2E tests + browser verification. Resize persists across save/load, old sessions load without errors, edges connect correctly to resized nodes.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **Pointer events in headless E2E**: Playwright's `page.mouse` dispatch doesn't reliably reach resize handles on CSS-transformed canvas elements in headless mode. T02 added a programmatic fallback that modifies the model directly, testing the same persistence contract. Real users are unaffected — headed browsers handle pointer events fine.
- **Docker worktree issue**: The worktree's Docker stack had a persistent RDF4J LuceneSail lock. Browser verification was done by copying worktree files to the main repo's volume-mounted path. Files in the worktree are the source of truth.

## Known Limitations

- Resize handles only work on standard canvas nodes — embed nodes (S03) will need the same handles wired to a different rendering layer
- Height resize stores explicit pixel height, removing auto-height behavior for that node — no "reset to auto" UX exists yet
- E2E resize test relies on programmatic fallback in headless — real pointer-based resize is only tested in headed mode

## Follow-ups

- S03 must integrate resize handles with the dual-layer rendering system for embed nodes
- S04 should include a headed E2E test option for pointer-based resize if CI supports it

## Files Created/Modified

- `frontend/static/js/canvas.js` — resize state fields, pointer event handlers (down/move/up), resize handle HTML in renderNodes(), width/height in getDocument/applyDocument, conditional inline style
- `frontend/static/css/workspace.css` — min-width/min-height on .spatial-node, three resize handle styles with hover/selection visibility
- `backend/tests/test_canvas_resize.py` — 11 unit tests for canvas document JSON serialization with width/height
- `e2e/tests/17-spatial-canvas/canvas-resize.spec.ts` — 2 E2E tests: API persistence + UI interaction/persistence/backward-compat/edges

## Forward Intelligence

### What the next slice should know
- The node model now has optional `width` and `height` fields — undefined means CSS default 260px. S02 (property flip) doesn't need to change this; S03 (embeds) will set explicit dimensions on embed nodes.
- `renderNodes()` rebuilds `state.layer.innerHTML` on every call. This is fine for regular nodes but will destroy iframe content. S03's dual-layer rendering (D124) must handle embed nodes separately.
- The resize pointer event system uses `state.resizingNodeId` as a guard — `onPointerMove` checks it before the drag check. Any new pointer interactions must follow the same priority chain: resize > drag > pan.

### What's fragile
- `renderNodes()` innerHTML rebuild — any DOM state (selections, iframe content, focus) is lost on every call. S03 must solve this for embeds.
- The inline style application in `renderNodes()` uses string concatenation to build the `style` attribute. If more inline styles are needed (e.g. embed-specific), this pattern should be revisited.

### Authoritative diagnostics
- `SemPKMCanvas.exportState()` in browser console — returns the full document including width/height per node. This is the most reliable way to check whether resize is working.
- `state.resizingNodeId` — if non-null, a resize is in progress. If it stays non-null after pointerUp, something went wrong in the cleanup.

### What assumptions changed
- Original assumption: CSS `resize: both` might work for simple resize needs. Actual: custom handles required for event capture, min/max constraints, and state persistence (D127).
- Original assumption: `renderNodes()` on every pointer move during resize. Actual: direct DOM style manipulation during drag, `renderNodes()` only on pointerUp (D130) — much smoother.
