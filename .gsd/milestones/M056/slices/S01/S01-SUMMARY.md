---
id: S01
parent: M056
milestone: M056
provides:
  - GET /browser/ontology/tbox/graph-data endpoint — returns Cytoscape-compatible {nodes, edges} with source labels
  - SemPKM.initTboxGraph(containerId) — initializes graph in any container element
  - SemPKM._tboxGraph / window._tboxCy — live Cytoscape instance reference for S02 filtering and persistence
  - Node source data attribute — S02 can filter by source for multi-model filtering
  - .tbox-vertical-split layout with graph/tree toggle — S02 adds filter controls to toolbar
requires:
  []
affects:
  - S02
key_files:
  - backend/app/ontology/service.py
  - backend/app/ontology/router.py
  - backend/tests/test_ontology_graph.py
  - backend/app/templates/browser/ontology/ontology_page.html
  - frontend/static/css/workspace.css
  - frontend/static/js/ontology-graph.js
  - backend/app/templates/base.html
key_decisions:
  - D406: Client-side filtering via CSS class toggling — 170 nodes fits comfortably in memory
  - Edge direction parent→child matches dagre TB convention (parents at top)
  - Graph view is default/primary; tree view hidden behind toggle
  - Dual cy instance reference (SemPKM._tboxGraph + window._tboxCy) for namespace and toggle compat
  - Source-based node coloring: gist=slate, user=teal, models=rotating palette
  - Edge labels hidden to reduce visual noise
patterns_established:
  - TBox graph API returns flat {nodes, edges} JSON — same pattern could serve other graph views
  - Source-color assignment pattern: fixed colors for well-known sources, rotating palette for dynamic model sources
  - Vertical split layout with view toggle — reusable for any pane needing dual visualization modes
observability_surfaces:
  - logger.info on GET /browser/ontology/tbox/graph-data logs node count, edge count, graph count
  - SPARQL errors logged with exc_info=True
  - Empty state: 0-node response renders 'No ontology classes found' message in container
drill_down_paths:
  - .gsd/milestones/M056/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M056/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M056/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T07:32:02.127Z
blocker_discovered: false
---

# S01: TBox Graph API + Hierarchical Rendering + Detail Panel

**Added a Cytoscape.js hierarchical graph to the Ontology Viewer TBox tab — API endpoint, vertical layout with graph/tree toggle, dagre TB rendering with source-based coloring, and node-click detail panel.**

## What Happened

This slice replaced the tree-only TBox view in the Ontology Viewer with a full hierarchical Cytoscape.js graph as the primary view, while preserving the tree as an alternate view behind a toggle.

**T01 — API endpoint.** Added `get_tbox_graph_data()` to OntologyService — a single SPARQL query across all ontology graphs (gist + installed models + user-types) returning Cytoscape-compatible `{nodes, edges}` JSON. Nodes include `id` (IRI), `label`, and `source` (gist/model-id/user). Edges are parent→child direction matching dagre TB convention. owl:Thing and blank nodes are excluded. Parent nodes are auto-created when only referenced by children. Error handling returns empty arrays on SPARQL failure. Route at `GET /browser/ontology/tbox/graph-data`. 16 unit tests cover node structure, edge direction, source labels, deduplication, empty results, SPARQL failure, and query structure.

**T02 — Layout restructure.** Replaced the `.tbox-split` horizontal layout (tree left 320px, detail right) with `.tbox-vertical-split` vertical flex column. Top area has a toolbar with graph/tree toggle buttons and two view containers (graph visible by default, tree hidden). Bottom area is a 250px detail pane. `toggleTboxView()` handles visibility switching and Cytoscape resize on re-show. Fixed stale JS selectors from the old `.tbox-tree-pane` class.

**T03 — Cytoscape rendering.** Created `ontology-graph.js` as an IIFE module exporting `SemPKM.initTboxGraph()`. Fetches graph data via `apiFetch()`, assigns per-source colors (gist=slate, user=teal, models=rotating palette), renders with dagre TB layout, wires node tap to `loadClassDetail()`, handles hover feedback, theme switching via `sempkm:theme-changed`, empty state messaging, and cleanup registration. Dual instance reference (`SemPKM._tboxGraph` + `window._tboxCy`) for namespace and toggle compatibility.

## Verification

All slice-level verification passed:
- 16/16 unit tests pass: `cd backend && .venv/bin/python -m pytest tests/test_ontology_graph.py -v` (0.50s)
- T02 grep checks pass: tbox-graph in template, toggleTboxView in template, tbox-vertical-split in CSS
- T03 grep checks pass: ontology-graph.js exists, initTboxGraph exported, apiFetch used, dagre layout used
- Observability: logger.info on successful query logs node/edge/graph counts; SPARQL errors logged with exc_info=True

## Requirements Advanced

None.

## Requirements Validated

- R019 — GET /browser/ontology/tbox/graph-data returns all TBox classes + subClassOf edges. ontology-graph.js renders dagre TB hierarchy with gist at top, model types below. 16 unit tests pass.
- R021 — Node tap event calls loadClassDetail() which loads class properties, relationships, and instance count via /browser/ontology/tbox/detail endpoint.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Minor: T03 used Cytoscape data() style mappers for source colors instead of per-source stylesheet rules — simpler approach. T02 fixed stale .tbox-tree-pane selectors. No plan-invalidating deviations.

## Known Limitations

Graph renders all TBox classes in a single fetch — no pagination. Works for current scale (~170 nodes) but would need server-side filtering if scale exceeds ~500 nodes (D406 documents this tradeoff). Hover popover positioning (R018) is deferred to S02.

## Follow-ups

S02 covers multi-model filtering, per-model color coding, persistence across tab switches, and hover popover anchoring.

## Files Created/Modified

- `backend/app/ontology/service.py` — Added get_tbox_graph_data() method — SPARQL query across all ontology graphs returning Cytoscape-compatible {nodes, edges}
- `backend/app/ontology/router.py` — Added GET /browser/ontology/tbox/graph-data route returning JSONResponse
- `backend/tests/test_ontology_graph.py` — New: 16 unit tests covering node structure, edge direction, source labels, dedup, empty/error cases
- `backend/app/templates/browser/ontology/ontology_page.html` — Restructured TBox pane: vertical split, graph/tree toggle, graph container, initTboxGraph() call
- `frontend/static/css/workspace.css` — Added .tbox-vertical-split, .tbox-main-view, .tbox-graph-container, .tbox-tree-container, .tbox-view-toggle CSS
- `frontend/static/js/ontology-graph.js` — New: IIFE module — SemPKM.initTboxGraph(), dagre TB layout, source coloring, node click, theme switching, cleanup
- `backend/app/templates/base.html` — Added ontology-graph.js script tag
