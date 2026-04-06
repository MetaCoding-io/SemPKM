---
estimated_steps: 23
estimated_files: 3
skills_used: []
---

# T02: Frontend config selector with save/load persistence and preset options

Add a config selector UI above the config builder panel that shows saved configs and presets. Wire save/load to the CRUD API. Add Hierarchy as a special option alongside the composable presets.

Steps:
1. Update `backend/app/templates/browser/explorer_config_panel.html` to add:
   - A config selector row above the config builder with a `<select>` dropdown listing saved configs and presets
   - A name `<input>` for saving/naming configs
   - 'Save' and 'Delete' buttons next to the selector
   - The selector has option groups: 'Presets' (By Type, By Tag, Hierarchy) and 'Saved Configs'
2. Update `frontend/static/js/explorer-config.js` to add config persistence:
   - `loadConfigList()` — fetches GET /api/explorer/configs, populates selector dropdown with presets + user configs
   - `saveCurrentConfig()` — reads name input + current dropdown values, POST /api/explorer/configs
   - `loadSelectedConfig(id)` — applies config from selector (sets dropdowns from config_json, calls applyExplorerConfig)
   - `deleteSelectedConfig(id)` — DELETE /api/explorer/configs/{id}, refreshes list
   - Hierarchy preset: when selected, calls the legacy `htmx.ajax('GET', '/browser/explorer/tree?mode=hierarchy', ...)` instead of the composable config tree. This is a special case — hierarchy is NOT an ExplorerConfig.
   - On page load: call `loadConfigList()` to populate selector. Restore last active config from localStorage UUID reference.
   - After save/delete: refresh the config list dropdown.
3. Update `frontend/static/css/explorer-config.css` to style the config selector row, name input, and save/delete buttons.
4. Call initExplorerConfig + loadConfigList on page load from workspace.html or workspace.js initialization.

Constraints:
- Hierarchy uses the legacy mode=hierarchy endpoint, not the config-tree endpoint. When hierarchy is selected, hide the config builder panel (filter/group/sort don't apply).
- Active config ID stored in localStorage key 'sempkm_explorer_active_config' — just the UUID string.
- Config selector uses apiFetch() for all API calls (Knowledge Pattern #13).
- Presets from API have is_preset=true — disable the Delete button for presets.
- After applying a saved config, the summary bar should update to show the config name.

## Inputs

- ``backend/app/browser/explorer_config_service.py` — T01's service providing the CRUD API`
- ``backend/app/browser/workspace.py` — T01's API endpoints`
- ``frontend/static/js/explorer-config.js` — existing config builder module to extend`
- ``backend/app/templates/browser/explorer_config_panel.html` — existing config panel to extend`
- ``frontend/static/css/explorer-config.css` — existing styles to extend`

## Expected Output

- ``frontend/static/js/explorer-config.js` — extended with loadConfigList, saveCurrentConfig, loadSelectedConfig, deleteSelectedConfig, hierarchy special case`
- ``backend/app/templates/browser/explorer_config_panel.html` — config selector dropdown, name input, save/delete buttons added`
- ``frontend/static/css/explorer-config.css` — config selector row styles added`

## Verification

Browser verification: open workspace → config selector shows presets and saved configs. Save a config with name → reload page → config appears in selector → click to apply → tree renders correctly. Select Hierarchy preset → tree renders hierarchy mode. Select By Type preset → tree renders type-grouped mode.
