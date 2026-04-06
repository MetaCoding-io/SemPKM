---
id: T04
parent: S01
milestone: M054
key_files:
  - backend/app/templates/browser/workspace.html
  - frontend/static/js/workspace.js
  - backend/app/browser/explorer_config.py
  - frontend/static/js/explorer-config.js
  - backend/tests/test_explorer_config.py
  - backend/tests/test_explorer_modes.py
  - e2e/helpers/selectors.ts
key_decisions:
  - Strip prop: prefix in ExplorerConfig.__post_init__ rather than in frontend or endpoint — single responsibility boundary
  - Remove EXPLORER_MODE_KEY localStorage entirely rather than mapping — config system supersedes it
  - Persona explorer_mode backward compat maps by-tag to group_by=tag via config system
duration: 
verification_result: passed
completed_at: 2026-04-06T04:44:47.585Z
blocker_discovered: false
---

# T04: Wire config builder into workspace, replace old explorer dropdown, verify end-to-end with grouped/sorted tree

**Wire config builder into workspace, replace old explorer dropdown, verify end-to-end with grouped/sorted tree**

## What Happened

Replaced the flat explorer mode dropdown with a gear-icon configure button that toggles the composable config panel. Updated refreshNavTree to delegate to the config system's refreshExplorerTree. Removed all EXPLORER_MODE_KEY localStorage handling and initExplorerMode/initExplorerMountOptions functions. Updated persona code for backward compat (by-tag maps to group_by=tag). Fixed critical prop: prefix stripping bug in ExplorerConfig.__post_init__. Added tests for prefix stripping, endpoint registration, and verified the full flow in the browser.

## Verification

42/42 unit tests pass. Browser verification confirmed: config panel opens, type/group/sort dropdowns populate from API, grouped tree renders with status folders and sorted items, reset restores default tree. Static assets served at 200 from nginx.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_explorer_config.py tests/test_explorer_modes.py -v` | 0 | ✅ pass | 820ms |
| 2 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:3901/js/explorer-config.js` | 0 | ✅ pass | 100ms |
| 3 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:3901/css/explorer-config.css` | 0 | ✅ pass | 100ms |

## Deviations

Added prop: prefix stripping in ExplorerConfig.__post_init__ — necessary integration fix not in original plan. Cleaned stale explorer-mode-select references from explorer-config.js. Added config selectors to E2E selectors.ts.

## Known Issues

E2E tests using SEL.explorer.modeSelect (19-explorer-modes, 20-tags, 20-vfs-explorer, 24-tag-hierarchy) will fail because the select element was removed. Legacy /browser/explorer/tree?mode=X endpoint still exists for backward compat.

## Files Created/Modified

- `backend/app/templates/browser/workspace.html`
- `frontend/static/js/workspace.js`
- `backend/app/browser/explorer_config.py`
- `frontend/static/js/explorer-config.js`
- `backend/tests/test_explorer_config.py`
- `backend/tests/test_explorer_modes.py`
- `e2e/helpers/selectors.ts`
