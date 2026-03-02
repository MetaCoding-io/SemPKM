---
phase: 30-dockview-phase-a-migration
plan: 01
subsystem: ui
tags: [dockview, dockview-core, workspace, layout, tabs, drag-drop, split-pane]

# Dependency graph
requires:
  - phase: 10-workspace-layout
    provides: workspace-layout.js editor-group architecture, WorkspaceLayout class
provides:
  - DockviewComponent-based workspace layout replacing Split.js/custom-drag
  - createComponent factory for object-editor, view-panel, special-panel
  - dockview toJSON/fromJSON layout persistence via sessionStorage
  - _tabMeta sidecar for tab metadata (label, dirty, typeIcon, typeColor)
  - dockview CDN links in workspace.html head block
  - Activated dockview-sempkm-bridge.css token mappings
affects: [30-02, 30-03, workspace.js, editor integration, panel management]

# Tech tracking
tech-stack:
  added: [dockview-core@4.11.0]
  patterns: [DockviewComponent init, createComponent factory, onDidVisibilityChange for CodeMirror/Cytoscape refresh, htmx.process on layout change for DOM reparenting]

key-files:
  created: []
  modified:
    - frontend/static/js/workspace-layout.js
    - backend/app/templates/browser/workspace.html
    - frontend/static/css/dockview-sempkm-bridge.css

key-decisions:
  - "DockviewComponent CDN global resolved via DockviewCore.DockviewComponent || window.DockviewComponent for bundle compatibility"
  - "WorkspaceLayout class retained as thin metadata sidecar (no groups[], no save/restore, no addTabToGroup)"
  - "New sessionStorage key sempkm_workspace_layout_dv replaces old sempkm_workspace_layout (old key cleared on init)"
  - "renderGroupTabBar kept as no-op stub -- dockview renders tab bars natively"
  - "Bridge CSS loaded BEFORE dockview.css so SemPKM token overrides take effect"

patterns-established:
  - "createComponent factory pattern: options.name routes to component type, params.containerElement for htmx.ajax target"
  - "onDidVisibilityChange for CodeMirror requestMeasure and Cytoscape resize on tab re-show"
  - "htmx.process on .dv-content-container after layout changes (DOM reparenting by dockview)"
  - "try/catch around dv.fromJSON with fallback to buildDefaultLayout (no dv.clear() on failure)"

requirements-completed: [DOCK-01]

# Metrics
duration: 2min
completed: 2026-03-02
---

# Phase 30 Plan 01: Dockview Core Integration Summary

**Replaced Split.js/custom-drag editor-group system with dockview-core 4.11.0 in workspace-layout.js (1073 -> 382 lines), added CDN links and activated CSS token bridge**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-02T04:14:23Z
- **Completed:** 2026-03-02T04:17:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Rewrote workspace-layout.js from 1073 to 382 lines, replacing Split.js horizontal splits and custom HTML5 drag-drop with DockviewComponent
- Added createComponent factory routing object-editor, view-panel, and special-panel types through htmx.ajax
- Wired all three pitfall guards: htmx.process on layout change, onDidVisibilityChange for CodeMirror/Cytoscape, try/catch around fromJSON
- Added dockview-core@4.11.0 CDN links to workspace.html with correct load order (bridge CSS before dockview CSS)
- Removed static group-1 HTML from editor-groups-container (dockview creates all internal DOM)
- Activated dockview-sempkm-bridge.css by removing "STATUS: Pattern file" comment

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite workspace-layout.js with DockviewComponent** - `83c64f8` (feat)
2. **Task 2: Update workspace.html CDN links and activate dockview-sempkm-bridge.css** - `1647fa6` (feat)

## Files Created/Modified
- `frontend/static/js/workspace-layout.js` - Rewritten: DockviewComponent init, createComponent factory, event wiring, metadata sidecar
- `backend/app/templates/browser/workspace.html` - Added dockview CDN links in head block, emptied editor-groups-container
- `frontend/static/css/dockview-sempkm-bridge.css` - Removed STATUS pattern file comment, CSS content unchanged

## Decisions Made
- Resolved CDN global name with fallback: `DockviewCore.DockviewComponent || window.DockviewComponent`
- Retained WorkspaceLayout as thin metadata sidecar with only `_dv` reference and `activeGroupId`
- Used new sessionStorage key `sempkm_workspace_layout_dv` to avoid conflicts with old layout format
- Kept `renderGroupTabBar` as no-op stub for backward compatibility
- Omitted `createTabComponent` (dockview uses built-in tab rendering with `title` field)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- workspace-layout.js ready for Plan 02 (workspace.js caller migration) to update tab open/close calls to use dockview API
- Plan 03 (E2E test adaptation) can verify the new dockview-based workspace behavior
- All window exports preserved with same names for backward compatibility

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 30-dockview-phase-a-migration*
*Completed: 2026-03-02*
