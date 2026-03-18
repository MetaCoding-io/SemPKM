---
id: T02
parent: S04
milestone: M009
provides:
  - openAppPageTab() global function for opening app pages as dockview tabs
  - specialType 'app-page' routing in workspace-layout.js special-panel factory
key_files:
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
key_decisions:
  - Tab key format app-page:{appId}:{pageId} for dedup — matches existing dashboard/workflow patterns
patterns_established:
  - App page tab opener follows identical structure to openDashboardTab (tabKey, dedup, _tabMeta, addPanel with special-panel component)
observability_surfaces:
  - window.openAppPageTab callable from browser console for manual testing
  - window._dockview.panels.map(p => p.id) shows open app-page tab IDs
  - htmx error responses render directly in tab content area (standard special-panel behavior)
duration: 8m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Workspace JS — openAppPageTab + special-panel handler

**Added `openAppPageTab()` function and `app-page` specialType routing for dockview tab creation from sidebar clicks.**

## What Happened

Two surgical edits to existing JS files:

1. Added `openAppPageTab(appId, pageId, label)` to `workspace.js` immediately after `openDashboardTab()`. Follows the identical pattern: composite tab key for dedup, existing-panel activation check, `_tabMeta` registration, `dv.api.addPanel()` with `special-panel` component and `app-page` specialType.

2. Added `app-page` case to `workspace-layout.js` special-panel factory, after the `generic-view` block and before the `htmx.ajax` call. Routes to `/browser/apps/{appId}/page/{pageId}`.

## Verification

- `grep -c "openAppPageTab" frontend/static/js/workspace.js` → 2 ✅ (definition + window export)
- `grep -c "app-page" frontend/static/js/workspace-layout.js` → 1 ✅
- Slice-level checks:
  - `grep -c "apps_router" backend/app/browser/router.py` → 2 ✅ (from T01)
  - `grep -c "APPS" backend/app/templates/browser/workspace.html` → 1 ✅ (from T01)
  - All 4 grep-based slice verification checks pass
  - Tests (`test_app_browser.py`) — not yet created (T03 scope)
  - Fixture fix (`manifest.yaml`) — not yet done (T03 scope)

## Diagnostics

- Call `window.openAppPageTab('some-app', 'main', 'Test Page')` in browser console to test tab creation without sidebar
- Inspect `window._dockview.panels.map(p => p.id)` to see active app-page tabs
- Backend errors from `/browser/apps/…` render as htmx error content in the tab

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js` — added `openAppPageTab()` function + `window.openAppPageTab` export after `openDashboardTab()`
- `frontend/static/js/workspace-layout.js` — added `app-page` specialType case in special-panel factory
- `.gsd/milestones/M009/slices/S04/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
