---
phase: 35-owl2-rl-inference
plan: 02
subsystem: ui, api, sparql
tags: [owl2-rl, inference, sparql, named-graphs, cytoscape, htmx, css-grid]

requires:
  - phase: 35-01
    provides: InferenceService writes triples to urn:sempkm:inferred
provides:
  - SPARQL queries include urn:sempkm:inferred alongside urn:sempkm:current
  - scope_to_current_graph(include_inferred=True) parameter
  - Relations panel shows inferred badge with source annotation
  - Object read view two-column layout (user left, inferred right)
  - Graph view dashed edges for inferred triples
  - Label service resolves from both current and inferred graphs
affects: [35-03, 35-04, inference-panel, graph-view, relations-panel]

tech-stack:
  added: []
  patterns: [UNION SPARQL pattern for dual-graph source annotation, FROM clause injection for inferred graph]

key-files:
  created: []
  modified:
    - backend/app/rdf/namespaces.py
    - backend/app/sparql/client.py
    - backend/app/browser/router.py
    - backend/app/views/service.py
    - backend/app/services/labels.py
    - backend/app/templates/browser/properties.html
    - backend/app/templates/browser/object_read.html
    - frontend/static/css/workspace.css
    - frontend/static/js/graph.js

key-decisions:
  - "UNION pattern for relations (not FROM) to annotate source graph per triple"
  - "Separate inferred properties query in get_object() for clean two-column data flow"
  - "Inferred edge identification via supplementary SELECT query after CONSTRUCT for graph view"
  - "User-created triples always deduplicated over inferred (user takes precedence)"

patterns-established:
  - "UNION SPARQL pattern: query GRAPH current + GRAPH inferred with BIND source annotation"
  - "FROM dual-graph: add FROM inferred alongside FROM current for merged default graph queries"
  - "Cytoscape inferred-edge class: edges with inferred flag get dashed line style"

requirements-completed: []

duration: 6min
completed: 2026-03-04
---

# Phase 35 Plan 02: Inferred Triple Display Summary

**Dual-graph SPARQL queries with UNION source annotation, inferred badges in relations panel, two-column object read layout, and dashed graph edges for OWL 2 RL inferred triples**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-04T06:00:58Z
- **Completed:** 2026-03-04T06:07:41Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- All SPARQL queries now include urn:sempkm:inferred graph for complete data visibility
- Relations panel annotates each triple with source ("user" or "inferred") and shows subtle inferred badge
- Object read view uses CSS grid two-column layout with collapsible inferred column
- Graph view identifies inferred edges and renders them with dashed lines via Cytoscape.js
- Label service resolves labels from both current and inferred graphs
- Deduplication ensures user-created triples always take precedence over inferred duplicates

## Task Commits

Each task was committed atomically:

1. **Task 1: Modify SPARQL queries to include inferred graph** - `cff017d` (feat)
2. **Task 2: Update templates and CSS for inferred badge, two-column layout, and dashed graph edges** - `62ec4a9` (feat)

**Plan metadata:** (pending)

## Files Created/Modified
- `backend/app/rdf/namespaces.py` - Added INFERRED_GRAPH_IRI constant
- `backend/app/sparql/client.py` - scope_to_current_graph() gains include_inferred parameter
- `backend/app/browser/router.py` - UNION queries for relations, inferred_values for object read
- `backend/app/views/service.py` - Graph view includes inferred graph, identifies inferred edges
- `backend/app/services/labels.py` - Label resolution from both current and inferred graphs
- `backend/app/templates/browser/properties.html` - Inferred badge on relation items
- `backend/app/templates/browser/object_read.html` - Two-column layout with inferred column
- `frontend/static/css/workspace.css` - Inferred badge, two-column grid, stale indicator styles
- `frontend/static/js/graph.js` - Dashed line style for inferred edges in Cytoscape

## Decisions Made
- Used UNION pattern (not FROM) for relations queries to annotate each triple with its source graph -- this is required because FROM merges graphs into the default graph and loses source provenance
- Separate SPARQL query for inferred properties in get_object() rather than mixing with user query -- cleaner data separation for template rendering
- Supplementary SELECT query after CONSTRUCT in graph view to identify which edges are inferred -- CONSTRUCT loses named graph provenance
- User-created triples always take precedence: deduplication removes inferred triples that already exist in current graph

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All SPARQL queries and UI templates are ready to display inferred triples
- Requires Plan 01 (InferenceService) to populate urn:sempkm:inferred with actual data
- Plan 03 (Inference bottom panel) and Plan 04 (admin configuration) can proceed independently

## Self-Check: PASSED

All 9 files verified present. Both task commits (cff017d, 62ec4a9) confirmed in git log.

---
*Phase: 35-owl2-rl-inference*
*Completed: 2026-03-04*
