---
phase: 51-spatial-canvas-ux
plan: 01
subsystem: ui
tags: [canvas, spatial, graph-exploration, vanilla-js]

requires:
  - phase: none
    provides: existing canvas.js spatial canvas implementation
provides:
  - Per-node expand/delete/chevron controls
  - Expand provenance tracking for scoped collapse
  - Empty canvas with hint text
  - Cleaned toolbar (no Load/Load Neighbors)
affects: [51-02-drag-drop, 51-03-sessions]

tech-stack:
  added: []
  patterns: [inline-svg-icons, expand-provenance-tracking, scoped-collapse]

key-files:
  created: []
  modified:
    - frontend/static/js/canvas.js
    - frontend/static/css/workspace.css
    - backend/app/templates/browser/canvas_page.html

key-decisions:
  - "Inline SVG constants for icons instead of Lucide re-scan on every render"
  - "Scoped collapse via expandProvenance map tracking which expand loaded which nodes"

patterns-established:
  - "Expand provenance: state.expandProvenance[nodeId] = [childIds] for scoped collapse"
  - "Inline SVG icon constants at IIFE top to avoid Lucide createElement overhead"

requirements-completed: []

duration: 3min
completed: 2026-03-08
---

# Phase 51 Plan 01: Per-Node Controls Summary

**Per-node expand/delete/chevron buttons with provenance-based scoped collapse, empty canvas hint, and toolbar cleanup**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T06:02:38Z
- **Completed:** 2026-03-08T06:05:14Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Canvas starts empty with centered hint text instead of hardcoded demo nodes
- Each node header shows chevron (toggle body), expand (+), and delete (x) buttons
- Expand loads 1-hop neighbors via /api/canvas/subgraph with circular positioning
- Scoped collapse via expandProvenance ensures collapsing one expand does not remove nodes shared by another
- Provenance persisted in getDocument()/applyDocument() for save/load

## Task Commits

Each task was committed atomically:

1. **Task 1: Update canvas_page.html toolbar and add hint element** - `b98b886` (feat)
2. **Task 2: Implement per-node controls, provenance tracking, and empty canvas logic** - `efa984a` (feat)

## Files Created/Modified
- `backend/app/templates/browser/canvas_page.html` - Removed Load/Load Neighbors buttons, updated title, added hint element
- `frontend/static/js/canvas.js` - Per-node controls, expandProvenance, removeNode, toggleExpand, expandNode, empty state
- `frontend/static/css/workspace.css` - Node header flex layout, button styles, chevron rotation, hint overlay

## Decisions Made
- Used inline SVG constants (SVG_CHEVRON, SVG_PLUS, SVG_X) to avoid Lucide re-scan on every renderNodes() call
- Scoped collapse tracks provenance per expand -- nodes shared by multiple expands survive individual collapse

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Canvas ready for Plan 02 (drag-drop from nav tree) -- screenToWorld() and renderNodes() are stable APIs
- Plan 03 (sessions) can build on getDocument()/applyDocument() which now include expandProvenance

---
## Self-Check: PASSED

*Phase: 51-spatial-canvas-ux*
*Completed: 2026-03-08*
