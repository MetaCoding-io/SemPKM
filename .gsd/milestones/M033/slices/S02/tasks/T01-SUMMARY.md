---
id: T01
parent: S02
milestone: M033
provides:
  - Lucide SVG icon toggle for graph nodes with localStorage persistence
  - Memoized _lucideSvgDataUri() helper for Lucide-to-data-URI conversion
  - Icon mode parameter on buildSemanticStyle() for background-image injection
key_files:
  - frontend/static/js/graph.js
  - frontend/static/css/views.css
  - backend/app/templates/browser/graph_view.html
key_decisions:
  - Used lucide.icons[PascalCase] + lucide.createElement() API from UMD bundle for programmatic SVG generation
  - Memoized per (iconName, strokeColor) pair since theme switches change stroke color
  - Clear SVG URI cache on theme switch to regenerate with correct stroke color
patterns_established:
  - _lucideSvgDataUri(iconName, strokeColor) as reusable Lucide → data URI pipeline
  - Icon mode as third parameter to buildSemanticStyle(typeColors, isDark, iconMode)
observability_surfaces:
  - "console.warn '[graph] Lucide icon not found: <name>' when PascalCase lookup fails"
  - "console.warn '[graph] lucide UMD not loaded' when CDN script unavailable"
  - "localStorage key 'sempkm_graph_icon_mode' inspectable in DevTools"
  - "#graph-icon-toggle button .active class indicates icon mode on"
duration: 20m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Add Lucide SVG icon toggle to graph nodes

**Added memoized Lucide SVG data URI pipeline and toolbar icon toggle to graph view with localStorage persistence and theme-aware stroke colors.**

## What Happened

Implemented the icon toggle feature for the graph view in three files:

1. **graph.js** — Added `_lucideSvgDataUri(iconName, strokeColor)` that converts kebab-case Lucide icon names to PascalCase for lookup in `lucide.icons`, creates SVG elements via `lucide.createElement()`, serializes to data URIs, and caches results per (name, color) pair. Modified `buildSemanticStyle()` to accept a third `iconMode` parameter — when true, it injects `background-image` styles with Lucide SVGs and sets uniform ellipse shapes. Added `_setIconMode(mode)` and `_toggleGraphIcons()` for toggling, with localStorage read on graph init. Updated all three existing `buildSemanticStyle()` call sites (init, expand, theme switch) to pass `_currentIconMode`. Theme switch clears the SVG URI cache since stroke color changes.

2. **graph_view.html** — Added icon toggle button after the Fit button with `data-lucide="shapes"` icon, onclick wired to `window._toggleGraphIcons()`.

3. **views.css** — Styled `.graph-icon-toggle-btn` matching `.graph-fit-btn` sizing, added `.active` state with primary color highlight, and added `svg` child rule with `flex-shrink: 0` per CLAUDE.md Lucide-in-flex convention.

## Verification

All five task-level checks passed:

- `_lucideSvgDataUri` present in graph.js (2 occurrences)
- `_setIconMode` and `_toggleGraphIcons` present in graph.js (5 occurrences)
- `sempkm_graph_icon_mode` localStorage key referenced in graph.js (2 occurrences)
- `graph-icon-toggle` present in graph_view.html (1 occurrence)
- `graph-icon-toggle-btn` present in views.css (4 occurrences)
- JavaScript syntax validation passed (`node -c graph.js`)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg -c '_lucideSvgDataUri' frontend/static/js/graph.js` | 0 | ✅ pass (2) | <1s |
| 2 | `rg -c '_setIconMode\|_toggleGraphIcons' frontend/static/js/graph.js` | 0 | ✅ pass (5) | <1s |
| 3 | `rg -c 'sempkm_graph_icon_mode' frontend/static/js/graph.js` | 0 | ✅ pass (2) | <1s |
| 4 | `rg -c 'graph-icon-toggle' backend/app/templates/browser/graph_view.html` | 0 | ✅ pass (1) | <1s |
| 5 | `rg -c 'graph-icon-toggle-btn' frontend/static/css/views.css` | 0 | ✅ pass (4) | <1s |
| 6 | `node -c frontend/static/js/graph.js` | 0 | ✅ pass | <1s |

## Diagnostics

- **Icon lookup failures:** Open browser DevTools console, filter for `[graph]` — shows warnings for missing icons or unavailable lucide UMD
- **Icon mode state:** `localStorage.getItem('sempkm_graph_icon_mode')` → `'icon'`, `'shape'`, or `null`
- **Toggle button state:** `document.getElementById('graph-icon-toggle').classList.contains('active')` → true when icon mode is on
- **Graceful degradation:** If lucide CDN fails, icon toggle silently falls back to shape-only mode (no crash)

## Deviations

- Added SVG URI cache invalidation on theme switch — not in plan but necessary because stroke color changes between dark/light themes, so cached SVGs with the old color would be incorrect.
- Added `_updateIconToggleButton()` call in `_renderGraph()` after cy instance creation — the DOMContentLoaded listener alone isn't reliable since graph templates render inside dockview panels asynchronously.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/graph.js` — Added `_lucideSvgDataUri()`, `_setIconMode()`, `_toggleGraphIcons()`, `_updateIconToggleButton()`, updated `buildSemanticStyle()` with iconMode param, updated 3 call sites to pass icon mode, cache invalidation on theme switch
- `frontend/static/css/views.css` — Added `.graph-icon-toggle-btn`, `.graph-icon-toggle-btn:hover`, `.graph-icon-toggle-btn.active`, `.graph-icon-toggle-btn svg` rules
- `backend/app/templates/browser/graph_view.html` — Added icon toggle button to `.graph-toolbar`
- `.gsd/milestones/M033/slices/S02/S02-PLAN.md` — Added Observability / Diagnostics section
