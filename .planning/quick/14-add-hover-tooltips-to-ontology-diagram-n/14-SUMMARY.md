---
phase: quick-14
plan: 01
subsystem: ui
tags: [svg, popover, shacl, ontology, hover, jinja]

requires:
  - phase: quick-12
    provides: SVG ontology relationship diagram template and endpoint
  - phase: quick-13
    provides: Dynamic viewBox, curved edges, arrowhead fixes
provides:
  - Hover popovers on ontology diagram nodes showing SHACL properties and instance counts
affects: [admin, model-detail, ontology-diagram]

tech-stack:
  added: []
  patterns: [graph-popover CSS reuse for SVG hover, Jinja tojson filter for safe JSON embedding]

key-files:
  created: []
  modified:
    - backend/app/admin/router.py
    - backend/app/templates/admin/model_ontology_diagram.html

key-decisions:
  - "Reuse existing graph-popover CSS classes instead of adding new styles"
  - "Use Jinja tojson filter for safe JSON serialization of node data"
  - "Limit properties to 6 per popover to keep tooltip manageable"

patterns-established:
  - "SVG hover popover: embed data as JSON via Jinja, position via getBoundingClientRect relative to container"

requirements-completed: [QUICK-14]

duration: 3min
completed: 2026-03-01
---

# Quick Task 14: Add Hover Tooltips to Ontology Diagram Summary

**Hover popovers on ontology SVG nodes showing SHACL property names/types and instance counts, reusing graph-popover CSS**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T16:30:14Z
- **Completed:** 2026-03-01T16:33:16Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Enriched ontology diagram endpoint with SHACL property data and live instance counts per node
- Added interactive hover popovers to SVG node circles using existing graph-popover CSS classes
- Popover shows type label, instance count badge, and up to 6 SHACL properties (name + type)
- Viewport boundary adjustment prevents popover overflow on right and bottom edges

## Task Commits

Each task was committed atomically:

1. **Task 1: Enrich ontology diagram endpoint with SHACL properties and instance counts** - `1702cff` (feat)
2. **Task 2: Add popover HTML and hover JS to ontology diagram template** - `db58b97` (feat)

## Files Created/Modified
- `backend/app/admin/router.py` - Added shape-property lookup, analytics call, and node enrichment with properties/instance_count
- `backend/app/templates/admin/model_ontology_diagram.html` - Added ontology-node class/data attrs, graph-popover div, JSON data block, and hover JS with positioning

## Decisions Made
- Reused existing graph-popover CSS classes from views.css (no new CSS needed)
- Used Jinja `|tojson` filter for safe JSON serialization of node property data
- Limited properties to max 6 per popover to keep the tooltip compact
- Added 150ms hide delay to allow mouse travel from node to popover
- Set panel position:relative via JS (not CSS) to avoid touching views.css

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ontology diagram now has full interactive hover tooltips
- No blockers for further diagram enhancements

## Self-Check: PASSED

- FOUND: backend/app/admin/router.py
- FOUND: backend/app/templates/admin/model_ontology_diagram.html
- FOUND: 14-SUMMARY.md
- FOUND: 1702cff (Task 1 commit)
- FOUND: db58b97 (Task 2 commit)

---
*Quick Task: 14*
*Completed: 2026-03-01*
