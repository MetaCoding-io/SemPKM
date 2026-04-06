---
id: T01
parent: S02
milestone: M056
key_files:
  - frontend/static/js/ontology-graph.js
  - backend/app/templates/browser/ontology/ontology_page.html
  - frontend/static/css/workspace.css
key_decisions:
  - Used cy.batch() for filter operations to avoid per-node layout thrashing
  - Filter UI built client-side from graph data sources, not from server-provided list
  - Exported _tboxSourceColors map for downstream popover use
duration: 
verification_result: passed
completed_at: 2026-04-06T07:41:34.079Z
blocker_discovered: false
---

# T01: Added per-model filter checkboxes with color dots to TBox toolbar and fixed graph persistence on tab switch via cy.resize()

**Added per-model filter checkboxes with color dots to TBox toolbar and fixed graph persistence on tab switch via cy.resize()**

## What Happened

Added three functions to ontology-graph.js: _buildFilterUI() creates checkbox labels with color-dot spans per distinct source in the graph data, _applySourceFilter() uses cy.batch() to show/hide nodes and edges based on active sources, and filterTboxBySource() provides a programmatic API exported on window.SemPKM. The filter UI is built inside _renderTboxGraph() after Cytoscape init — it extracts distinct sources via new Set(), sorts them (gist first, then alpha), and appends the checkbox container to the existing .tbox-view-toolbar. An 'All' checkbox toggles all individual checkboxes. Edges connected to hidden nodes are also hidden. For tab persistence, added cy.resize() in switchOntologyTab() when tabId === 'tbox' — no cy.fit(), preserving zoom/pan state. CSS added to workspace.css for .tbox-model-filter, .tbox-filter-item, and .tbox-filter-dot. Also exported SemPKM._tboxSourceColors map for T02's hover popover.

## Verification

All four slice-level grep checks pass. JS syntax validated via node -c. cy.fit() count in ontology_page.html is exactly 1 (existing in toggleTboxView), confirming no cy.fit() was added to switchOntologyTab.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q 'filterTboxBySource|_applySourceFilter|tbox-model-filter' frontend/static/js/ontology-graph.js` | 0 | ✅ pass | 50ms |
| 2 | `grep -q 'tbox-model-filter' frontend/static/css/workspace.css` | 0 | ✅ pass | 50ms |
| 3 | `grep -q 'cy.resize()' backend/app/templates/browser/ontology/ontology_page.html` | 0 | ✅ pass | 50ms |
| 4 | `grep -c 'cy.fit()' backend/app/templates/browser/ontology/ontology_page.html → 1` | 0 | ✅ pass | 50ms |
| 5 | `node -c frontend/static/js/ontology-graph.js` | 0 | ✅ pass | 100ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/ontology-graph.js`
- `backend/app/templates/browser/ontology/ontology_page.html`
- `frontend/static/css/workspace.css`
