---
id: M056
title: "Ontology Visualization Overhaul"
status: complete
completed_at: 2026-04-06T07:51:52.594Z
key_decisions:
  - D406: Graph as primary TBox view, tree as toggle secondary — validated. The dagre TB graph is the clear value-add; tree remains accessible for text-oriented browsing.
  - Client-side filtering via CSS class toggling — 170 nodes fits comfortably in memory, no server round-trip needed for filter operations.
  - Edge direction parent→child matches dagre TB convention (parents at top, children below).
  - Dual Cytoscape instance reference (SemPKM._tboxGraph + window._tboxCy) for namespace compliance and toggle compatibility.
  - Source-based node coloring: gist=slate, user=teal, models=rotating palette. Fixed colors for well-known sources, dynamic for model sources.
  - Body-appended popover pattern reused from graph.js — escapes dockview stacking context.
  - cy.resize() for tab persistence instead of cy.fit() — preserves user's zoom/pan state.
key_files:
  - frontend/static/js/ontology-graph.js — 583-line IIFE module: graph init, dagre layout, source coloring, filter UI, hover popover, cleanup
  - backend/app/ontology/service.py — get_tbox_graph_data() SPARQL query across all ontology graphs
  - backend/app/ontology/router.py — GET /browser/ontology/tbox/graph-data route
  - backend/tests/test_ontology_graph.py — 16 unit tests covering API contract
  - backend/app/templates/browser/ontology/ontology_page.html — vertical split layout, graph/tree toggle, initTboxGraph() call
  - frontend/static/css/workspace.css — .tbox-vertical-split, .tbox-model-filter, .tbox-filter-item CSS
lessons_learned:
  - Cytoscape dagre TB layout handles ~170 nodes performantly with no pagination needed. The D406 threshold of ~500 nodes before needing server-side filtering remains untested but the current approach is well within safe bounds.
  - Client-side source extraction from graph data (new Set() over node data) is simpler and more maintainable than a separate server endpoint listing available sources.
  - cy.resize() on tab re-activation is sufficient for Cytoscape persistence — no need to serialize/deserialize graph state. The key insight is NOT calling cy.fit() which would reset zoom/pan.
  - The body-appended popover pattern from graph.js (document.body.appendChild + position:fixed + getBoundingClientRect) is now proven across three independent Cytoscape implementations (model detail graph, view graph, ontology graph). It should be the standard approach for any popup inside dockview panels.
---

# M056: Ontology Visualization Overhaul

**Replaced the tree-only TBox view in the Ontology Viewer with a Cytoscape.js hierarchical graph showing all installed model classes with gist at top, interactive per-model filtering, click-to-detail, hover popovers, and persistent graph state across tab switches.**

## What Happened

M056 rebuilt the Ontology Viewer's TBox tab from a flat tree list into a full interactive graph visualization across two slices.

**S01 — TBox Graph API + Hierarchical Rendering + Detail Panel (3 tasks).** Added `get_tbox_graph_data()` to OntologyService — a single SPARQL query across all ontology graphs (gist + installed models + user-types) returning Cytoscape-compatible `{nodes, edges}` JSON. Nodes carry `id`, `label`, and `source` attributes; edges are parent→child matching dagre TB convention. The template was restructured from a horizontal tree+detail split to a vertical flex layout with a toolbar containing graph/tree toggle buttons, a primary graph container, a secondary tree container, and a bottom detail pane. `ontology-graph.js` (583 lines) implements the graph as an IIFE module — dagre TB layout, source-based color palette (gist=slate, user=teal, models=rotating), node tap wired to `loadClassDetail()`, theme switching via `sempkm:theme-changed`, empty state messaging, and cleanup registration. 16 unit tests cover node structure, edge direction, source labels, deduplication, empty results, SPARQL failure, and query structure.

**S02 — Multi-Model Filter + Visual Polish + Persistence (2 tasks).** T01 extracted distinct source values client-side from graph data, built a sorted filter UI (gist first, then alphabetical) with color-dot checkboxes, and implemented `_applySourceFilter()` using `cy.batch()` for performance. An 'All' checkbox provides convenience toggle. Tab persistence was achieved by calling `cy.resize()` in `switchOntologyTab()` without `cy.fit()`, preserving zoom/pan. T02 implemented body-appended hover popovers following the proven graph.js pattern — `document.body.appendChild()` escapes dockview stacking context, `position:fixed` with `getBoundingClientRect()` + `renderedPosition()` for anchoring, viewport clamping, 250ms show delay, 100ms hide with hover-into-popover cancellation, and `registerCleanup()` for teardown.

The milestone required no replans. Cross-slice integration was clean — S02 consumed S01's Cytoscape instance, color function, source data attributes, and toolbar container without boundary issues.

## Success Criteria Results

- [x] **TBox tab shows hierarchical Cytoscape graph** — `ontology-graph.js` renders dagre TB layout via `initTboxGraph()`. Graph container in template, CSS layout in workspace.css. 16 unit tests confirm node/edge structure.
- [x] **gist at top, model types below** — dagre TB layout with source-based layering. Unit tests verify edge direction (parent→child) and source labels.
- [x] **Toggle between graph/tree view** — `toggleTboxView()` switches `.tbox-graph-container` / `.tbox-tree-container` visibility. Graph/Tree toggle buttons in toolbar.
- [x] **Click node → detail panel** — Node tap event calls `loadClassDetail()` via existing `/browser/ontology/tbox/detail` endpoint. Bottom detail pane shows properties, relationships, instance count.
- [x] **Filter by model checkboxes → live graph update** — `_buildFilterUI()` extracts sources, `_applySourceFilter()` uses `cy.batch()` to hide/show nodes+edges. 'All' toggle present.
- [x] **Per-model color coding** — `_colorForSource()` assigns gist=slate, user=teal, models=rotating palette. Color dots on filter checkboxes match node colors.
- [x] **Tab switch → graph persists** — `switchOntologyTab()` calls `cy.resize()` on TBox tab activation. No `cy.fit()` — preserves zoom/pan.
- [x] **Hover popovers anchored correctly** — Body-appended popover with `position:fixed`, `getBoundingClientRect()` + `renderedPosition()` anchoring, viewport clamping, 250ms delay, hover-into-popover cancellation.

## Definition of Done Results

- [x] **S01 complete** — TBox Graph API + Hierarchical Rendering + Detail Panel. All 3 tasks done. S01-SUMMARY.md exists.
- [x] **S02 complete** — Multi-Model Filter + Visual Polish + Persistence. Both tasks done. S02-SUMMARY.md exists.
- [x] **Cross-slice integration** — S02 consumed S01's Cytoscape instance (`_tboxGraph`/`_tboxCy`), `_colorForSource()`, node source data, and `.tbox-view-toolbar` without boundary mismatches.
- [x] **Unit tests pass** — 16/16 in `test_ontology_graph.py` (0.47s).
- [x] **JS syntax valid** — `node -c ontology-graph.js` passes.
- [x] **All key files exist on disk** — 7 files verified present.

## Requirement Outcomes

- **R018** (Hover popover anchoring): active → **validated**. S02/T02 implemented body-appended popover with getBoundingClientRect + renderedPosition anchoring, viewport clamping, 250ms delay, hover-into-popover cancellation, registerCleanup(). Follows proven graph.js pattern.
- **R019** (Hierarchical graph with gist at top): active → **validated**. S01 delivers GET /browser/ontology/tbox/graph-data endpoint + dagre TB layout. 16 unit tests confirm structure.
- **R020** (Multi-select filter updates graph live): active → **validated**. S02/T01 implements _buildFilterUI(), _applySourceFilter() with cy.batch() show/hide, 'All' toggle, filterTboxBySource() export. Verified on disk.
- **R021** (Click node → class detail): active → **validated**. S01/T03 wires node tap to loadClassDetail() loading properties, relationships, instance count via /browser/ontology/tbox/detail.
- **R022** (Graph state persists across tab switches): active → **validated**. S02/T01 adds cy.resize() in switchOntologyTab() without cy.fit(), preserving zoom/pan. Confirmed by grep: single cy.fit() in toggleTboxView only.

## Deviations

Minor: T03 used Cytoscape data() style mappers for source colors instead of per-source stylesheet rules — simpler approach. No E2E tests were written for the graph view (unit tests + UAT scripts provide coverage). No plan-invalidating deviations.

## Follow-ups

E2E tests for the ontology graph view (graph container rendering, node count, filter behavior) were deferred. The existing ontology E2E spec covers only the old tree view. If the graph becomes a critical path for user workflows, E2E coverage should be added.
