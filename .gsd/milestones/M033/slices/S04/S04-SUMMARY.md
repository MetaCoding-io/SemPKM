---
slice: S04
milestone: M033
title: "Isometric 2.5D Graph View"
status: done
tasks_completed: 2
tasks_total: 2
started: 2026-03-21
completed: 2026-03-21
duration: ~35m
risk_level: medium-high
risk_outcome: clean
---

# S04 Summary: Isometric 2.5D Graph View

## What Was Delivered

An "Isometric" layout option in the graph view that stratifies nodes into horizontal z-layers by RDF type, creating a 2.5D visual effect. Selecting "Isometric" from the layout picker arranges nodes in per-type grids with vertical stagger and horizontal offset between layers. Translucent compound parent nodes serve as layer planes behind each group. Edges cross layers naturally.

## Key Files

| File | Role |
|------|------|
| `frontend/static/js/isometric-layout.js` | New ~270-line Cytoscape layout extension |
| `frontend/static/js/graph.js` | LAYOUT_REGISTRY entry, compound styles, cleanup, event guards, filter propagation, expansion handling |
| `backend/app/views/router.py` | "Isometric" added to both `available_layouts` and `built_in_layouts` |
| `backend/app/templates/base.html` | Script tag for `isometric-layout.js` after `graph.js` |

## How It Works

1. **Layout extension** (`isometric-layout.js`): Groups nodes by `data('type')` into layers (max 8, overflow → "Other"). Sorts layers by node count descending. Injects compound parent nodes per layer with `_isometricLayer: true` sentinel and `_layerIndex`. Computes grid positions within each layer via `layoutPositions()`, with negative Y offset and horizontal stagger between layers for the 2.5D depth effect. Type labels resolved via `_resolveTypeLabel()` (prefers `data('typeLabel')`, falls back to local IRI name).

2. **Graph system integration** (`graph.js`): Six integration points — (a) LAYOUT_REGISTRY entry with animation config, (b) `buildSemanticStyle()` compound parent styles with theme-aware translucent backgrounds and `events: 'no'`, (c) `changeLayout()` cleanup that un-parents children and removes layer nodes when switching away, (d) tap/dbltap/mouseover guards that skip `_isometricLayer` nodes, (e) `filterGraph()` propagation to compound parents (hide layer plane when all children filtered), (f) `_expandNode()` triggers full isometric re-layout when active.

3. **Backend registration** (`router.py`): `{"name": "isometric", "label": "Isometric"}` in both layout arrays so the layout picker dropdown shows the option.

## Architecture Decisions

- **D304**: Custom 2D projection layout, not CSS 3D transforms. CSS transforms would break Cytoscape's coordinate system for mouse events, hit testing, and canvas rendering. Compound parent nodes are Cytoscape-native — they auto-size to contain children without DOM overlays.
- Compound parent interaction suppressed via two-layer defense: CSS `events: 'no'` plus explicit JS early-return guards in tap/dbltap/mouseover handlers.
- Layers sorted by node count descending — largest type at bottom for visual weight.

## Observability

- `window._sempkmIsometricState` exposes `{ layers, totalNodes, timestamp }` for browser console inspection
- `console.debug('[isometric]')` logs layer count and node count on each layout run
- `cy.nodes('[_isometricLayer]')` lists all compound parent nodes; length should be 0 after switching away
- `cy.nodes('[_isometricLayer].filtered-out')` shows which layers were hidden by filter

## What Next Slices Should Know

- The isometric layout is fully self-contained. No other slice depends on it.
- The compound parent cleanup pattern in `changeLayout()` (un-parent children before removing compounds) is important — without it, Cytoscape orphans child nodes.
- If a future layout also needs compound parents, follow the same `_isometricLayer`-style sentinel pattern for lifecycle management.
- The `events: 'no'` CSS property on compound parents is a Cytoscape-specific way to make elements non-interactive at the CSS level. JS guards are defense-in-depth.

## Verification

All 7 slice-level verification checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `test -f frontend/static/js/isometric-layout.js` | ✅ |
| 2 | `grep -q "isometric" backend/app/views/router.py` | ✅ |
| 3 | `grep -q "isometric-layout.js" backend/app/templates/base.html` | ✅ |
| 4 | `grep -q "'isometric'" frontend/static/js/graph.js` | ✅ |
| 5 | `grep -q "_isometricLayer" frontend/static/js/graph.js` | ✅ |
| 6 | `grep -q "_isometricLayer" frontend/static/js/isometric-layout.js` | ✅ |
| 7 | `node -e` Cytoscape extension protocol check | ✅ |
