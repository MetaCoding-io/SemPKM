---
id: S57
parent: M001
milestone: M001
provides:
  - snapToGrid function (24px grid alignment) in canvas.js
  - Keyboard navigation handler with 7 key bindings
  - Node selection state with focus ring styling
  - Edge label readability via paint-order stroke halo
  - Wave 0 E2E test stubs for CANV-01 through CANV-05
  - WIKILINK_RE regex for wiki-link pre-processing in canvas.js
  - Ghost node rendering and click-to-resolve handler
  - POST /api/canvas/resolve-wikilinks endpoint for title-to-IRI batch resolution
  - Dashed green wiki-link edge styling distinct from solid blue RDF edges
  - window.getSelectedIris() export for multi-select state access with labels
  - addNodesFromBulkDrop() with 3-column grid placement and edge auto-discovery
  - fetchBulkEdges() for batch edge retrieval from backend
  - POST /api/canvas/batch-edges endpoint for inter-IRI edge discovery via SPARQL
  - Multi-item drag payload bundling in tree_children.html ondragstart
requires: []
affects: []
key_files: []
key_decisions:
  - "Spatial order for Tab cycling: sort by y then x (top-to-bottom, left-to-right)"
  - "Auto-select next node after Delete for continuous keyboard navigation"
  - "Click canvas background deselects current node"
  - "Wiki-link pre-processing uses wikilink: URI scheme for unresolved targets, enabling ghost node detection in second-pass"
  - "DOMPurify configured with ADD_URI_SAFE_PROTOCOLS to preserve wikilink: scheme hrefs"
  - "Ghost nodes deduplicated by id to avoid multiple stubs for the same target"
  - "Markdown edge labels now use link textContent instead of hardcoded 'link'"
  - "Multi-item drag detection checks if dragged item is in selection AND selection has >1 items, else falls back to single-item"
  - "Grid placement uses 260px + GRID column width and 120px + GRID row height for readable spacing"
  - "fetchBulkEdges sends ALL canvas node IRIs (not just new ones) for complete cross-group edge discovery"
  - "Confirmation dialog threshold set at 20 nodes to prevent accidental canvas crowding"
patterns_established:
  - "snapToGrid pattern: Math.round(value / GRID) * GRID applied at all placement sites but NOT on load"
  - "Keyboard guard pattern: check activeElement tag and closest() for dv-tabs-container/cm-editor"
  - "wikilink: scheme pattern: unresolved wiki-links encoded as wikilink:TARGET for post-render detection"
  - "Ghost node pattern: semi-transparent dashed-border stubs with click-to-resolve via backend API"
  - "Bulk drop pattern: __canvasDragPayload.items array for multi-item, single {iri, label} for backward compat"
  - "Batch edge discovery pattern: POST /api/canvas/batch-edges with SPARQL VALUES clause across current+inferred graphs"
observability_surfaces: []
drill_down_paths: []
duration: 3min
verification_result: passed
completed_at: 2026-03-10
blocker_discovered: false
---
# S57: Spatial Canvas

**# Phase 57 Plan 01: Snap-to-Grid, Edge Labels & Keyboard Navigation Summary**

## What Happened

# Phase 57 Plan 01: Snap-to-Grid, Edge Labels & Keyboard Navigation Summary

**24px snap-to-grid alignment on all node placements, paint-order stroke halo on edge labels, and full keyboard navigation with arrow keys, Tab cycling, Delete, Enter, Escape, and Ctrl+S**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T06:27:00Z
- **Completed:** 2026-03-10T06:30:47Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Nodes now snap to 24px grid during drag, expansion, and nav-tree drop (backward-compatible with pre-snap saved sessions)
- Edge labels have a readable paint-order stroke halo that creates a surface-colored background without extra SVG elements
- Full keyboard navigation: arrow keys (24px/120px steps), Tab/Shift+Tab spatial cycling, Delete immediate removal, Enter expand toggle, Escape deselect, Ctrl+S save
- 5 Wave 0 E2E test stub files covering all phase requirements (CANV-01 through CANV-05, 27 test.todo cases)
- Click-to-select with visible focus ring (accent outline + shadow)

## Task Commits

Each task was committed atomically:

1. **Task 0: Create Wave 0 E2E test stubs** - `0af73de` (test)
2. **Task 1: Snap-to-grid function and edge label polish** - `3ba0c1f` (feat)
3. **Task 2: Keyboard navigation and node selection** - `233cca5` (feat)

## Files Created/Modified
- `e2e/tests/17-spatial-canvas/snap-to-grid.spec.ts` - CANV-01 test stubs (4 cases)
- `e2e/tests/17-spatial-canvas/edge-labels.spec.ts` - CANV-02 test stubs (3 cases)
- `e2e/tests/17-spatial-canvas/keyboard-nav.spec.ts` - CANV-03 test stubs (9 cases)
- `e2e/tests/17-spatial-canvas/bulk-drop.spec.ts` - CANV-04 test stubs (6 cases)
- `e2e/tests/17-spatial-canvas/wiki-link-edges.spec.ts` - CANV-05 test stubs (5 cases)
- `frontend/static/js/canvas.js` - snapToGrid function, keyboard handler, selection state, spatial sort
- `frontend/static/css/workspace.css` - Focus ring styling, edge label paint-order halo

## Decisions Made
- Spatial order for Tab cycling: sort by y then x (top-to-bottom, left-to-right) -- matches visual mental model
- Auto-select next node after Delete: avoids forcing user to re-select for continuous keyboard operation
- Click on canvas background deselects current node: natural UX pattern
- Tab and Ctrl+S work even without a selected node (Tab starts cycling, Ctrl+S always saves)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- snapToGrid function and GRID constant available for Plans 02 and 03 to reuse
- Selection state (state.selectedNodeId) ready for future features
- E2E test stubs ready for implementation when feature code lands

## Self-Check: PASSED

All 8 files verified present. All 3 task commits verified in git log.

---
*Phase: 57-spatial-canvas*
*Completed: 2026-03-10*

# Phase 57 Plan 02: Wiki-Link Edge Rendering Summary

**Wiki-link [[syntax]] pre-processing with dashed green edges, ghost nodes for unresolved targets, and batch title-to-IRI resolution endpoint**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T06:34:28Z
- **Completed:** 2026-03-10T06:38:54Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Wiki-links in node markdown bodies (`[[target]]`, `[[target|alias]]`) are parsed and rendered as dashed green edges on the canvas, visually distinct from solid blue RDF edges
- Ghost nodes appear for wiki-link targets not yet on the canvas -- small semi-transparent stubs with dashed green border that can be clicked to resolve
- New POST /api/canvas/resolve-wikilinks endpoint performs batch title-to-IRI resolution via single SPARQL query matching against 5 label properties
- Markdown edge labels now show the actual link display text instead of generic "link"

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend wiki-link resolution endpoint** - `628fa6c` (feat)
2. **Task 2: Wiki-link pre-processing, edge styling, and ghost nodes** - `9dcc94b` (feat)

## Files Created/Modified
- `backend/app/canvas/schemas.py` - WikilinkResolveRequest/WikilinkResolveResponse Pydantic schemas
- `backend/app/canvas/router.py` - POST /resolve-wikilinks endpoint with batch SPARQL resolution
- `frontend/static/js/canvas.js` - WIKILINK_RE regex, wikiLinkTitleMap, ghost node rendering and click handler, edge label improvement
- `frontend/static/css/workspace.css` - Dashed green wiki-link edge styling, ghost node styling, dark theme overrides

## Decisions Made
- Used `wikilink:` URI scheme for unresolved targets so they survive marked.js + DOMPurify and can be detected in the second-pass edge rendering
- Added `ADD_URI_SAFE_PROTOCOLS: ['wikilink']` to DOMPurify to prevent stripping of custom scheme hrefs
- Ghost nodes deduplicated by id to avoid rendering multiple stubs for the same wiki-link target
- Changed markdown edge labels from hardcoded 'link' to actual `linkEl.textContent` for all link types

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Wiki-link edges and ghost nodes ready for integration with bulk drag-drop (Plan 03)
- wikiLinkTitleMap pattern reusable for any title-based node resolution
- resolve-wikilinks endpoint available for any frontend feature needing title-to-IRI mapping

## Self-Check: PASSED

All 4 files verified present. All 2 task commits verified in git log.

---
*Phase: 57-spatial-canvas*
*Completed: 2026-03-10*

# Phase 57 Plan 03: Bulk Drag-Drop & Auto-Edge Discovery Summary

**Multi-select nav tree drag-drop onto spatial canvas with 3-column grid placement, batch SPARQL edge discovery between dropped nodes, and 20-node confirmation threshold**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-10T06:41:32Z
- **Completed:** 2026-03-10T06:44:36Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Users can shift/ctrl-click multiple nav tree items and drag them all onto the canvas at once
- Dropped nodes are placed in a 3-column grid at the drop point, snapped to 24px grid
- After placement, POST /api/canvas/batch-edges discovers all RDF edges between canvas nodes via SPARQL VALUES query across current and inferred graphs
- Duplicate nodes silently skipped, confirmation dialog shown for drops exceeding 20 nodes
- Single-item drag-drop remains fully backward compatible

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend batch-edges endpoint and frontend multi-select export** - `03f6ddc` (feat)
2. **Task 2: Multi-item drag payload and canvas bulk drop handler** - `b44155f` (feat)

## Files Created/Modified
- `backend/app/canvas/schemas.py` - BatchEdgesRequest/BatchEdge/BatchEdgesResponse Pydantic schemas
- `backend/app/canvas/router.py` - POST /api/canvas/batch-edges endpoint with SPARQL VALUES query, dedup, predicate label fallback
- `frontend/static/js/workspace.js` - window.getSelectedIris() export returning {iri, label} objects from multi-select state
- `frontend/static/js/canvas.js` - addNodesFromBulkDrop() grid placement, fetchBulkEdges() edge discovery, bulk payload detection in onDrop/onDragEnd
- `backend/app/templates/browser/tree_children.html` - ondragstart bundles multi-select items into __canvasDragPayload.items array

## Decisions Made
- Multi-item drag detection checks if the dragged item is in the current selection AND selection has more than 1 item -- otherwise falls back to single-item for backward compatibility
- Grid placement uses 260px + 24px column width and 120px + 24px row height for readable node spacing
- fetchBulkEdges sends ALL canvas node IRIs (not just newly dropped ones) so cross-group edges between old and new nodes are also discovered
- Confirmation threshold at 20 nodes -- below that, drops are instant without interruption

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All Phase 57 plans (01, 02, 03) complete -- spatial canvas feature fully implemented
- Canvas supports single-item drop, bulk drop with grid layout, keyboard navigation, wiki-link edges, ghost nodes, and edge auto-discovery
- E2E test stubs from Plan 01 ready for test implementation

## Self-Check: PASSED

All 5 files verified present. All 2 task commits verified in git log.

---
*Phase: 57-spatial-canvas*
*Completed: 2026-03-10*
