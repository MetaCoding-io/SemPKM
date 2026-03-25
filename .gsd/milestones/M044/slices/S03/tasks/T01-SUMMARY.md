---
id: T01
parent: S03
milestone: M044
key_files:
  - frontend/static/js/api-fetch.js
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/js/graph.js
  - frontend/static/js/federation.js
  - frontend/static/js/editor.js
  - frontend/static/js/tutorials.js
  - frontend/static/js/canvas.js
  - frontend/static/js/calendar.js
  - frontend/static/js/cleanup.js
  - frontend/static/js/sidebar.js
  - frontend/static/js/theme.js
  - frontend/static/js/settings.js
  - frontend/static/js/named-layouts.js
  - frontend/static/js/markdown-render.js
  - frontend/static/js/column-prefs.js
  - frontend/static/js/bmc.js
  - frontend/static/js/okr.js
  - frontend/static/js/quadrant.js
  - frontend/static/js/decision-matrix.js
  - frontend/static/js/kanban.js
  - frontend/static/js/recurrence-editor.js
  - frontend/static/js/vfs-browser.js
  - frontend/static/js/context-indicator.js
  - frontend/static/js/copilot.js
  - frontend/static/js/sparql-console.js
key_decisions:
  - Namespace bootstrap in api-fetch.js (earliest-loading custom JS)
  - Backward-compat shims via simple assignment — works for functions/objects but requires sync writes in initWorkspaceLayout() for reassigned references
  - Double-underscore globals (__canvasDragPayload etc.) left unmigrated — private by convention, not API exports
duration: ""
verification_result: passed
completed_at: 2026-03-25T19:07:45.616Z
blocker_discovered: false
---

# T01: Migrate all 26 JS files from window.X exports to window.SemPKM.X with backward-compat shims

**Migrate all 26 JS files from window.X exports to window.SemPKM.X with backward-compat shims**

## What Happened

Migrated all ~213 window.X export assignments across 26 JS files to window.SemPKM.X, with 157 backward-compat shims added. Bootstrap window.SemPKM = window.SemPKM || {} placed in api-fetch.js. All typeof guards and cross-IIFE calls also updated. Fixed 3 correctness issues post-migration: restored window.dockview (third-party), kept _sempkmSkipLayoutSave as old form for template compat, added sync writes in initWorkspaceLayout() for reassigned object references.

## Verification

All four task verification checks passed: syntax check (all JS files), namespace bootstrap exists, custom globals audit (only shims remain), typeof guards (zero old-style).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `JS syntax check (node -c for all JS files)` | 0 | ✅ pass | 6000ms |
| 2 | `rg 'window.SemPKM = window.SemPKM' frontend/static/js/api-fetch.js` | 0 | ✅ pass | 50ms |
| 3 | `Custom globals audit (rg + grep exclusions)` | 0 | ✅ pass | 100ms |
| 4 | `typeof guards audit` | 1 | ✅ pass (exit 1 = no matches = correct) | 50ms |


## Deviations

1. Added 3 sync lines inside initWorkspaceLayout() to keep window._dockview/_workspaceLayout/_tabMeta in sync — shims copy at load time but initWorkspaceLayout reassigns later. 2. Kept window._sempkmSkipLayoutSave read as old form — template writes to it, T02 hasn't migrated templates yet. 3. Fixed false positive: window.dockview is third-party, restored to original.

## Known Issues

workspace-layout.js line 360 calls bare loadRightPaneSection which was never defined — pre-existing bug (workspace.js exports refreshRightPaneSection). Not introduced by this migration.

## Files Created/Modified

- `frontend/static/js/api-fetch.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/federation.js`
- `frontend/static/js/editor.js`
- `frontend/static/js/tutorials.js`
- `frontend/static/js/canvas.js`
- `frontend/static/js/calendar.js`
- `frontend/static/js/cleanup.js`
- `frontend/static/js/sidebar.js`
- `frontend/static/js/theme.js`
- `frontend/static/js/settings.js`
- `frontend/static/js/named-layouts.js`
- `frontend/static/js/markdown-render.js`
- `frontend/static/js/column-prefs.js`
- `frontend/static/js/bmc.js`
- `frontend/static/js/okr.js`
- `frontend/static/js/quadrant.js`
- `frontend/static/js/decision-matrix.js`
- `frontend/static/js/kanban.js`
- `frontend/static/js/recurrence-editor.js`
- `frontend/static/js/vfs-browser.js`
- `frontend/static/js/context-indicator.js`
- `frontend/static/js/copilot.js`
- `frontend/static/js/sparql-console.js`
