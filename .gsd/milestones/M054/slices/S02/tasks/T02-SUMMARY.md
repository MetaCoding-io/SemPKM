---
id: T02
parent: S02
milestone: M054
key_files:
  - frontend/static/js/explorer-config.js
  - backend/app/templates/browser/explorer_config_panel.html
  - frontend/static/css/explorer-config.css
  - backend/app/main.py
  - backend/app/templates/browser/workspace.html
key_decisions:
  - Hierarchy is a pseudo-preset using sentinel value __hierarchy__, not stored as ExplorerConfig
  - Preset seeding moved to app startup lifespan via get_or_create_presets()
  - API paths use /browser/api/explorer/configs matching workspace_router mount under /browser prefix
duration: 
verification_result: passed
completed_at: 2026-04-06T05:18:53.750Z
blocker_discovered: false
---

# T02: Added config selector dropdown with presets (By Type, By Tag, Hierarchy), save/load/delete for named configs, localStorage persistence across page reloads, and builder panel hide for Hierarchy mode

**Added config selector dropdown with presets (By Type, By Tag, Hierarchy), save/load/delete for named configs, localStorage persistence across page reloads, and builder panel hide for Hierarchy mode**

## What Happened

Extended the explorer config panel with a selector row containing a dropdown (Presets + Saved Configs optgroups), name input, Save and Delete buttons. Extended explorer-config.js with 6 new functions for config CRUD, Hierarchy pseudo-preset handling, and localStorage persistence. Fixed preset seeding in app startup and delete button state after config restoration.

## Verification

24/24 backend unit tests pass. Browser verification confirmed: preset selection renders correct tree views, Hierarchy uses legacy mode, save persists to API, reload restores from localStorage, delete removes config and resets tree.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_explorer_config_service.py -v` | 0 | ✅ pass | 630ms |

## Deviations

API paths use /browser/api/explorer/configs (workspace_router mount prefix). Added get_or_create_presets() to startup lifespan. Added _updateDeleteButton() call after localStorage restoration.

## Known Issues

Migration 026 wasn't volume-mounted into container, required manual docker compose cp.

## Files Created/Modified

- `frontend/static/js/explorer-config.js`
- `backend/app/templates/browser/explorer_config_panel.html`
- `frontend/static/css/explorer-config.css`
- `backend/app/main.py`
- `backend/app/templates/browser/workspace.html`
