---
phase: 28-ui-polish-integration-testing
plan: "01"
subsystem: frontend-ui
tags: [ui-polish, css, javascript, drag-and-drop, theme, icons, accessibility]
dependency_graph:
  requires: []
  provides: [POLSH-01, POLSH-02]
  affects: [workspace-ui, nav-tree, right-pane]
tech_stack:
  added: []
  patterns: [html5-drag-drop, css-tokens, lucide-icons, localStorage-persistence]
key_files:
  created: []
  modified:
    - frontend/static/css/workspace.css
    - backend/app/templates/browser/workspace.html
    - frontend/static/js/workspace.js
    - docs/guide/04-workspace-interface.md
key_decisions:
  - "Used var(--color-text-muted) for all chevron/toggle icon colors — consistent with existing token system"
  - "Added SVG stroke override for Lucide icons (.group-chevron svg, .right-section-chevron svg) to ensure currentColor propagates"
  - "Used [data-drop-zone] attribute selector for drop zone highlight to avoid specificity conflicts"
  - "Panel positions keyed by 'sempkm_panel_positions' in localStorage; restored on DOMContentLoaded before workspace is interactive"
  - "window.swapPanel exported for E2E test programmatic access"
metrics:
  duration_minutes: 2
  tasks_completed: 4
  files_modified: 4
  completed_date: "2026-03-01"
---

# Phase 28 Plan 01: Icon Visibility Fix + Panel Drag-and-Drop Summary

**One-liner:** CSS token-based icon visibility fixes for all four chevron types plus HTML5 drag-and-drop sidebar panel rearrangement with localStorage persistence.

## What Was Built

### POLSH-01: Expander/Collapse Icon Visibility Fix

Added explicit `color: var(--color-text-muted)` rules to all four chevron/toggle icon selectors in `workspace.css`, preventing invisible-on-background states in dark mode:

- `.group-chevron` — Lucide `chevron-right` in sidebar group headers (_sidebar.html)
- `.explorer-section-chevron` — Unicode ▶ in workspace left pane (workspace.html)
- `.tree-toggle` — Unicode ▶ in nav tree type nodes (nav_tree.html)
- `.right-section-chevron` — Lucide `chevron-right` in right pane panel summaries

Also added `.group-chevron svg` and `.right-section-chevron svg` rules with `stroke: currentColor` to ensure Lucide SVG icons inherit the color token correctly.

No hardcoded hex colors were used. All fixes use `var(--color-*)` tokens from theme.css.

### POLSH-02: Sidebar Panel Drag-and-Drop

**HTML changes (workspace.html):**
- Added `data-panel-name="relations"` and `data-panel-name="lint"` to right-section `<details>` elements
- Added `draggable="true"` to both `.right-section-header` summaries
- Added `grip-vertical` Lucide icon (12x12, opacity 0.35) as drag handle affordance in each summary
- Added `data-drop-zone="right"` to `#right-content`
- Added `data-drop-zone="left"` to `#nav-tree`

**JavaScript (workspace.js):**
- `PANEL_POSITIONS_KEY = 'sempkm_panel_positions'` — localStorage key
- `initPanelDragDrop()` — sets up dragstart/dragend on document, dragover/dragleave/drop on both drop zones
- `swapPanel(panelName, targetZone)` — moves panel DOM to left (nav-tree) or right (right-content), adds/removes `.panel-header-in-left`, calls Lucide re-init
- `savePanelPositions()` — serializes current positions to localStorage
- `restorePanelPositions()` — reads localStorage and calls swapPanel for any 'left' panels
- Both `initPanelDragDrop()` and `restorePanelPositions()` called from `init()` on DOMContentLoaded
- `window.swapPanel` exported for E2E tests

**CSS (workspace.css):**
- `[data-drop-zone].panel-drag-over` — accent-colored highlight on valid drop targets
- `.panel-dragging` — 50% opacity on panel being dragged
- `.right-section-header[draggable="true"]` — grab/grabbing cursor
- `[data-panel-name] .right-section-header.panel-header-in-left` — recessed background for panels moved to left pane

**Docs (04-workspace-interface.md):**
- Added "Moving Sidebar Panels" subsection to the Details Panel section explaining the drag-and-drop workflow

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | cac6b45 | fix(28-01): add explicit color tokens for expander/collapse icons (POLSH-01) |
| 2 | 9d28ca2 | feat(28-01): add drag-and-drop markup to workspace panels (POLSH-02) |
| 3 | 391ecc2 | feat(28-01): implement panel drag-and-drop JS and CSS (POLSH-02) |
| 4 | f43452f | docs(28-01): document panel rearrangement and icon visibility |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] `frontend/static/css/workspace.css` — exists and contains `.group-chevron`, `.panel-drag-over`, `.panel-header-in-left`
- [x] `backend/app/templates/browser/workspace.html` — contains `data-panel-name`, `data-drop-zone`, `grip-vertical`
- [x] `frontend/static/js/workspace.js` — contains `initPanelDragDrop`, `swapPanel`, `PANEL_POSITIONS_KEY`, `restorePanelPositions`
- [x] `docs/guide/04-workspace-interface.md` — contains "Moving Sidebar Panels" section
- [x] All 4 per-task commits present (cac6b45, 9d28ca2, 391ecc2, f43452f)
