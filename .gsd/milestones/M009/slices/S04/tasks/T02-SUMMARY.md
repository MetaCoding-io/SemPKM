---
id: T02
parent: S04
milestone: M009
provides:
  - openAppPageTab() JS function for opening app pages as dockview tabs
  - specialType 'app-page' routing in workspace-layout.js special-panel factory
key_files:
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
key_decisions:
  - Tab key format app-page:{appId}:{pageId} matches dashboard:{id} convention for dedup
patterns_established:
  - App page tab opening follows openDashboardTab() pattern — tab key, dedup check, _tabMeta, special-panel component
observability_surfaces:
  - window.openAppPageTab callable from browser console for tab creation testing
  - window._dockview.panels.map(p => p.id) shows open app-page tabs
  - htmx error responses render directly in tab content area (standard special-panel behavior)
duration: 8m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Workspace JS — openAppPageTab + special-panel handler

**Added openAppPageTab() function and app-page specialType handler for dockview tab creation from APPS sidebar**

## What Happened

Two targeted JS edits:

1. Added `openAppPageTab(appId, pageId, label)` to `workspace.js` immediately after `openDashboardTab()` and its window export. The function uses tab key `app-page:{appId}:{pageId}` for dedup, creates a `special-panel` with `specialType: 'app-page'`, and is exported as `window.openAppPageTab`.

2. Added `app-page` case in `workspace-layout.js`'s special-panel factory `init` function, after the `generic-view` block. When `specialType === 'app-page'` and both `appId` and `pageId` params are present, the URL is set to `/browser/apps/{appId}/page/{pageId}`.

Both files pass `node --check` syntax validation.

## Verification

- `grep -c "openAppPageTab" frontend/static/js/workspace.js` → 2 (definition + window export) ✅
- `grep -c "app-page" frontend/static/js/workspace-layout.js` → 1 ✅
- `node --check` on both JS files — no syntax errors ✅
- `python -m pytest tests/test_app_browser.py -v` — all 10 tests pass ✅ (T01 tests still green)
- Slice-level grep checks all pass (apps_router=2, APPS=1, etc.)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c "openAppPageTab" frontend/static/js/workspace.js` | 0 | ✅ pass (2) | <1s |
| 2 | `grep -c "app-page" frontend/static/js/workspace-layout.js` | 0 | ✅ pass (1) | <1s |
| 3 | `node --check frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 4 | `node --check frontend/static/js/workspace-layout.js` | 0 | ✅ pass | <1s |
| 5 | `python -m pytest tests/test_app_browser.py -v` | 0 | ✅ pass (10/10) | 0.55s |
| 6 | `grep -c "apps_router" backend/app/browser/router.py` | 0 | ✅ pass (2) | <1s |
| 7 | `grep -c "APPS" backend/app/templates/browser/workspace.html` | 0 | ✅ pass (1) | <1s |

## Diagnostics

- Call `openAppPageTab('test-app', 'main', 'Test')` in browser console to verify tab creation without the sidebar
- Inspect `window._dockview.panels.map(p => p.id)` to see open app-page tabs
- If backend route is missing, htmx swaps error response body directly into the tab content area

## Deviations

None.

## Known Issues

- `grep "ui:" backend/tests/fixtures/test_sdk_app/manifest.yaml` returns empty — fixture manifest fix is T03's responsibility per the slice plan.

## Files Created/Modified

- `frontend/static/js/workspace.js` — added `openAppPageTab()` function + `window.openAppPageTab` export after `openDashboardTab()`
- `frontend/static/js/workspace-layout.js` — added `app-page` specialType case in special-panel factory routing to `/browser/apps/{appId}/page/{pageId}`
