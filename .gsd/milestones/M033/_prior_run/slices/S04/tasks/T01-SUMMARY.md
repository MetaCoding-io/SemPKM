---
id: T01
parent: S04
milestone: M033
provides:
  - Cytoscape.js isometric layout extension with type-stratified z-layers
key_files:
  - frontend/static/js/isometric-layout.js
key_decisions:
  - Layers sorted by node count descending (largest at bottom for visual weight)
  - Grid centering per layer so columns are horizontally balanced
  - _resolveTypeLabel helper for clean IRI → label fallback
patterns_established:
  - Cytoscape custom layout extension pattern with layoutPositions() and compound parent injection
observability_surfaces:
  - "window._sempkmIsometricState: { layers, totalNodes, timestamp }"
  - "console.debug('[isometric]') messages on each layout run"
duration: 20m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Create isometric layout extension

**Created isometric-layout.js — a Cytoscape.js layout extension that stratifies graph nodes into horizontal z-layers by RDF type with isometric stagger and compound parent layer planes.**

## What Happened

Built `frontend/static/js/isometric-layout.js` (~210 lines) implementing the `IsometricLayout` constructor, `run()`, and `stop()` methods. The layout:

1. Cleans up any existing `[_isometricLayer]` compound parents (handles re-layout)
2. Groups all non-parent nodes by `data('type')`, with typeless nodes falling into "Other"
3. Caps at 8 layers — excess types are merged into "Other"
4. Sorts layers by node count descending (largest at bottom/layer 0)
5. Injects compound parent nodes per layer with `_isometricLayer: true` sentinel and `_layerIndex`
6. Computes grid positions via Cytoscape's `layoutPositions()` — grid within each layer, negative Y offset and horizontal stagger between layers for 2.5D depth

Type labels are resolved via a `_resolveTypeLabel()` helper that prefers `data('typeLabel')`, falling back to the local name extracted from the IRI (after last `/` or `#`).

Added `window._sempkmIsometricState` for runtime inspection and `console.debug('[isometric]')` for diagnostic logging.

## Verification

All three task-level checks pass:
- File exists at `frontend/static/js/isometric-layout.js`
- Contains `layoutPositions`, `cytoscape('layout'`, and `_isometricLayer`
- Exactly 1 occurrence of `function IsometricLayout`

Slice-level checks that apply to this task (2 of 7):
- `_isometricLayer` present in `isometric-layout.js` ✅
- `layoutPositions` and `cytoscape('layout'` present ✅

Remaining 5 slice-level checks are T02 scope (graph.js integration, router.py, base.html wiring).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f frontend/static/js/isometric-layout.js` | 0 | ✅ pass | <1s |
| 2 | `node -e "...includes('layoutPositions')...includes(\"cytoscape('layout'\")...includes('_isometricLayer')..."` | 0 | ✅ pass | <1s |
| 3 | `grep -c "function IsometricLayout" frontend/static/js/isometric-layout.js` | 0 (output: 1) | ✅ pass | <1s |
| 4 | `grep -q "_isometricLayer" frontend/static/js/isometric-layout.js` | 0 | ✅ pass | <1s |

## Diagnostics

- **Browser DevTools:** `window._sempkmIsometricState` shows `{ layers: [...], totalNodes: N, timestamp }` after any isometric layout run
- **Cytoscape console:** `cy.nodes('[_isometricLayer]')` lists all injected compound parent nodes
- **Console log:** `[isometric] Layout computed: N layers, M nodes` appears on each `run()` invocation
- **Failure mode:** If the script fails to load, `cytoscape('layout', 'isometric', ...)` never fires and the layout name is unregistered — `changeLayout('isometric')` will silently no-op

## Deviations

None. Implementation matches the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/isometric-layout.js` — new Cytoscape.js layout extension (~210 lines)
- `.gsd/milestones/M033/slices/S04/S04-PLAN.md` — added Observability / Diagnostics section, marked T01 done
- `.gsd/milestones/M033/slices/S04/tasks/T01-PLAN.md` — added Observability Impact section
