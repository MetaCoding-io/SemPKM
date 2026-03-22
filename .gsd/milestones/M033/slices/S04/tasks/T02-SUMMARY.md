---
id: T02
parent: S04
milestone: M033
provides:
  - Full integration of isometric layout into graph system — layout picker, styles, cleanup, event guards, filter propagation, expansion handling
key_files:
  - frontend/static/js/graph.js
  - backend/app/views/router.py
  - backend/app/templates/base.html
key_decisions:
  - Compound parent styles use `events: 'no'` for CSS-level interaction suppression plus explicit JS guards in tap/dbltap/mouseover for defense-in-depth
  - Dark/light theme colors chosen inline via isDark ternary to match existing buildSemanticStyle pattern
patterns_established:
  - Isometric cleanup pattern in changeLayout() — un-parent children before removing compound parents to avoid orphaning nodes
observability_surfaces:
  - "LAYOUT_REGISTRY['isometric'] — confirms registration in browser console"
  - "cy.nodes('[_isometricLayer]').length — confirms cleanup after switching away (should be 0)"
  - "cy.nodes('[_isometricLayer].filtered-out') — shows which layers were hidden by filter"
duration: 15m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Wire isometric layout into graph system and verify

**Wired isometric-layout.js into graph.js (LAYOUT_REGISTRY, compound styles, cleanup, event guards, filter propagation, expansion), added "Isometric" to both router.py layout lists, and loaded the script in base.html.**

## What Happened

Connected the T01 isometric layout extension to the full graph system across three files:

1. **base.html** — Added `<script>` tag for `isometric-layout.js` immediately after `graph.js` so the extension self-registers with Cytoscape before any graph initialization.

2. **router.py** — Added `{"name": "isometric", "label": "Isometric"}` to both the `available_layouts` inline list (generic_view, ~line 431) and the `built_in_layouts` list (graph_view, ~line 1090). This makes "Isometric" appear in the layout picker dropdown.

3. **graph.js** — Six integration points:
   - **LAYOUT_REGISTRY**: Added `'isometric'` entry with animation config
   - **buildSemanticStyle()**: Added `node[_isometricLayer]` compound parent styles with theme-aware colors (dark: lighter tones, light: darker tones), translucent backgrounds, `events: 'no'` to prevent CSS-level interactions
   - **changeLayout()**: Added isometric cleanup — when switching away, un-parents all children from layer nodes then removes the compound parents
   - **Event handlers**: Added `_isometricLayer` early-return guards in tap, dbltap, and mouseover handlers to prevent popovers/selection/expansion on layer plane nodes
   - **filterGraph()**: Added propagation to compound parents — if all children of a layer are filtered out, the layer plane itself gets `filtered-out`
   - **_expandNode()**: When isometric is active, new nodes trigger a full isometric re-layout instead of the local sub-layout, so they get correctly parented to type layers

## Verification

All 8 slice-level verification commands pass. All 8 must-haves are met.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f frontend/static/js/isometric-layout.js` | 0 | ✅ pass | <1s |
| 2 | `grep -q "isometric" backend/app/views/router.py` | 0 | ✅ pass | <1s |
| 3 | `grep -q "isometric-layout.js" backend/app/templates/base.html` | 0 | ✅ pass | <1s |
| 4 | `grep -q "'isometric'" frontend/static/js/graph.js` | 0 | ✅ pass | <1s |
| 5 | `grep -q "_isometricLayer" frontend/static/js/graph.js` | 0 | ✅ pass | <1s |
| 6 | `grep -q "_isometricLayer" frontend/static/js/isometric-layout.js` | 0 | ✅ pass | <1s |
| 7 | `node -e "...includes('layoutPositions')...includes(\"cytoscape('layout'\")..."` | 0 | ✅ pass | <1s |
| 8 | `grep -c "isometric" backend/app/views/router.py` returns 2 | 0 | ✅ pass | <1s |

## Diagnostics

- **Browser console:** `Object.keys(LAYOUT_REGISTRY)` lists all registered layouts including `'isometric'`
- **After layout switch:** `cy.nodes('[_isometricLayer]').length` should be 0 after switching away from isometric — non-zero means cleanup failed
- **Filter inspection:** `cy.nodes('[_isometricLayer].filtered-out')` shows which layer planes were hidden by the text filter
- **Expansion:** When expanding a node during isometric, the console shows `[isometric] Layout computed: N layers, M nodes` from the full re-layout
- **Failure mode:** If `isometric-layout.js` 404s, `LAYOUT_REGISTRY['isometric']` still exists but Cytoscape has no registered layout — selecting "Isometric" produces no visible change

## Deviations

None. All changes match the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/graph.js` — Added LAYOUT_REGISTRY entry, compound parent styles, changeLayout cleanup, event handler guards, filter propagation, expansion handling
- `backend/app/views/router.py` — Added "Isometric" to both available_layouts and built_in_layouts
- `backend/app/templates/base.html` — Added isometric-layout.js script tag after graph.js
- `.gsd/milestones/M033/slices/S04/tasks/T02-PLAN.md` — Added Observability Impact section
