---
phase: 57-spatial-canvas
plan: 02
subsystem: ui
tags: [canvas, wiki-link, ghost-node, sparql, spatial, markdown]

# Dependency graph
requires:
  - phase: 57-01
    provides: snapToGrid function, GRID constant, renderNodes structure, edge rendering
provides:
  - WIKILINK_RE regex for wiki-link pre-processing in canvas.js
  - Ghost node rendering and click-to-resolve handler
  - POST /api/canvas/resolve-wikilinks endpoint for title-to-IRI batch resolution
  - Dashed green wiki-link edge styling distinct from solid blue RDF edges
affects: [57-03-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: [wikilink: URI scheme for ghost node detection, DOMPurify ADD_URI_SAFE_PROTOCOLS for custom schemes, batch SPARQL title resolution with VALUES clause]

key-files:
  created: []
  modified:
    - frontend/static/js/canvas.js
    - frontend/static/css/workspace.css
    - backend/app/canvas/router.py
    - backend/app/canvas/schemas.py

key-decisions:
  - "Wiki-link pre-processing uses wikilink: URI scheme for unresolved targets, enabling ghost node detection in second-pass"
  - "DOMPurify configured with ADD_URI_SAFE_PROTOCOLS to preserve wikilink: scheme hrefs"
  - "Ghost nodes deduplicated by id to avoid multiple stubs for the same target"
  - "Markdown edge labels now use link textContent instead of hardcoded 'link'"

patterns-established:
  - "wikilink: scheme pattern: unresolved wiki-links encoded as wikilink:TARGET for post-render detection"
  - "Ghost node pattern: semi-transparent dashed-border stubs with click-to-resolve via backend API"

requirements-completed: [CANV-05]

# Metrics
duration: 4min
completed: 2026-03-10
---

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
