---
id: S02
parent: M056
milestone: M056
provides:
  - SemPKM.filterTboxBySource(sourceName, visible) — programmatic source filtering API
  - SemPKM._tboxSourceColors — source-to-color map for external consumers
requires:
  - slice: S01
    provides: TBox graph API, Cytoscape.js rendering, _colorForSource(), ontology-graph.js IIFE structure
affects:
  []
key_files:
  - frontend/static/js/ontology-graph.js
  - backend/app/templates/browser/ontology/ontology_page.html
  - frontend/static/css/workspace.css
key_decisions:
  - Used cy.batch() for filter operations to avoid per-node layout thrashing
  - Filter UI built client-side from graph data sources, not server-provided list
  - Reused existing .graph-popover CSS from views.css — inline background-color on source badge overrides base style without new rules
  - Exported _tboxSourceColors map for downstream popover use
patterns_established:
  - Per-model filter checkboxes with client-side source extraction, sorted with gist first
  - cy.resize() on tab activation for Cytoscape persistence — no cy.fit() to preserve zoom/pan
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M056/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M056/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T07:45:19.212Z
blocker_discovered: false
---

# S02: Multi-Model Filter + Visual Polish + Persistence

**Added per-model filter checkboxes with live graph updates, body-appended hover popovers with correct dockview anchoring, and tab-switch persistence via cy.resize().**

## What Happened

Two tasks delivered the three S02 features against the ontology-graph.js IIFE and supporting files.

**T01 — Model filtering + tab persistence.** Extracted distinct source values client-side from graph data via `new Set()`, built a sorted filter UI (gist first, then alpha) with color-dot checkboxes matching `_colorForSource()`. `_applySourceFilter()` uses `cy.batch()` to avoid per-node layout thrashing — nodes outside the active set are hidden, and edges touching hidden nodes are also hidden. An 'All' checkbox provides convenience toggle. The filter container appends to the existing `.tbox-view-toolbar`. For tab persistence, `switchOntologyTab()` now calls `cy.resize()` when activating the TBox tab — this fixes the Cytoscape container measuring issue without resetting zoom/pan (no `cy.fit()`). Exported `SemPKM.filterTboxBySource()` and `SemPKM._tboxSourceColors` for programmatic and downstream use.

**T02 — Hover popover.** Implemented the proven graph.js body-appended popover pattern: `document.body.appendChild(popover)` escapes the dockview stacking context, `position:fixed` with `getBoundingClientRect()` + `renderedPosition()` for anchoring, viewport overflow clamping on right and bottom edges. 250ms hover delay prevents flicker, 100ms hide delay with hover-into-popover cancellation (`_popoverHovered` flag). Content shows class label, source badge with inline background-color from the source color palette, and full IRI. Reused existing `.graph-popover` CSS from views.css — no new CSS rules needed. Cleanup via `registerCleanup()` removes the popover from body and clears timers on panel destruction.

## Verification

All 9 verification checks pass:
1. `grep -q 'filterTboxBySource' ontology-graph.js` → PASS (filter function exists)
2. `grep -q 'tbox-model-filter' workspace.css` → PASS (filter CSS exists)
3. `grep -q 'cy.resize' ontology_page.html` → PASS (tab persistence fix)
4. `grep -c 'cy.fit()' ontology_page.html` → 1 (existing toggleTboxView only, not in switchOntologyTab)
5. `grep -q 'document.body.appendChild' ontology-graph.js` → PASS (body-appended popover)
6. `grep -q 'graph-popover' ontology-graph.js` → PASS (uses graph-popover class)
7. `grep -q 'getBoundingClientRect' ontology-graph.js` → PASS (position:fixed anchoring)
8. `grep -q 'removeChild.*popover' ontology-graph.js` → PASS (cleanup registered)
9. `node -c ontology-graph.js` → PASS (JS syntax valid)

## Requirements Advanced

None.

## Requirements Validated

- R018 — T02: body-appended popover with getBoundingClientRect + renderedPosition anchoring, viewport clamping, 250ms show delay, hover-into-popover cancellation, registerCleanup
- R020 — T01: per-model filter checkboxes with cy.batch() show/hide, All toggle, edge hiding, filterTboxBySource() exported
- R022 — T01: cy.resize() in switchOntologyTab for tbox tab, no cy.fit(), grep confirms single cy.fit() in toggleTboxView only

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `frontend/static/js/ontology-graph.js` — Added _buildFilterUI(), _applySourceFilter(), filterTboxBySource(), _esc(), body-appended hover popover with graph-popover class, cleanup registration
- `backend/app/templates/browser/ontology/ontology_page.html` — Added cy.resize() call in switchOntologyTab() for tbox tab persistence
- `frontend/static/css/workspace.css` — Added .tbox-model-filter, .tbox-filter-item, .tbox-filter-dot CSS rules
