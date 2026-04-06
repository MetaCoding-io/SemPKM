---
estimated_steps: 32
estimated_files: 4
skills_used: []
---

# T04: Integration: wire config builder into workspace, replace old dropdown, verify end-to-end

Wire the config builder into the workspace, replace the old explorer mode dropdown, update refreshNavTree to use the new config system, and verify the full flow works end-to-end.

**Slice context:** T01-T03 built all components. This task integrates them and proves the slice demo works.

## Steps

1. Update `backend/app/templates/browser/workspace.html`:
   - Replace the `<select id='explorer-mode-select'>` dropdown with a Configure button (gear icon) that toggles the config panel
   - Include the `explorer_config_panel.html` partial in the OBJECTS section body, above `explorer-tree-body`
   - Add `<link>` for explorer-config.css and `<script>` for explorer-config.js
   - Keep the existing header action buttons (refresh, new object, bulk delete)

2. Update `frontend/static/js/workspace.js`:
   - Replace `refreshNavTree()` implementation: if a config is active (any filter/group/sort set), call `SemPKM.applyExplorerConfig()` instead of the old htmx mode-based fetch
   - If no config is active, default to the by-type tree (backward compat)
   - Remove the `EXPLORER_MODE_KEY` localStorage handling and the `explorer-mode-select` change listener
   - Update persona switching: personas that saved `explorer_mode` should map to the new config system (by-type → default, by-tag → group_by=tag)
   - Call `SemPKM.initExplorerConfig()` in the workspace init sequence

3. Update `frontend/nginx.conf` if needed — verify `/js/explorer-config.js` and `/css/explorer-config.css` are served (they should be, since nginx serves `/js/` and `/css/` from the static mount)

4. Update `backend/tests/test_explorer_modes.py`:
   - Update tests to verify the new config-tree endpoint is registered
   - Add test that old modes still work for backward compatibility (hierarchy and by-tag are still valid via the config system)

5. Verify in browser:
   - Navigate to /browser/ → OBJECTS section shows Configure button instead of dropdown
   - Click Configure → config panel expands with type/group/sort selectors
   - Select type=Task → tree shows only tasks
   - Select group=Status → tree shows folder nodes per status value
   - Select sort=Due Date → items sorted within groups
   - Click Apply → tree updates
   - Click Reset → default by-type tree restored
   - R009: type labels in tree show clean names without ' Shape' suffix
   - R010: composable layers produce correct results

**Key constraints:**
- nginx serves `/js/` and `/css/` — use those paths, not `/static/js/` (Knowledge pattern about nginx paths)
- Don't break existing object-open-on-click behavior in the tree
- Persona explorer_mode backward compat: map old values to new config

## Inputs

- ``backend/app/browser/explorer_config.py` — ExplorerConfig, query composition from T01`
- ``backend/app/browser/workspace.py` — config-tree and config-children endpoints from T02`
- ``frontend/static/js/explorer-config.js` — config builder JS module from T03`
- ``frontend/static/css/explorer-config.css` — config panel styling from T03`
- ``backend/app/templates/browser/explorer_config_panel.html` — config builder partial from T03`
- ``backend/app/templates/browser/workspace.html` — current OBJECTS section with explorer-mode-select dropdown`
- ``frontend/static/js/workspace.js` — current refreshNavTree, explorer mode handling`

## Expected Output

- ``backend/app/templates/browser/workspace.html` — OBJECTS section updated with config builder integration`
- ``frontend/static/js/workspace.js` — refreshNavTree updated to use config system`
- ``backend/tests/test_explorer_modes.py` — updated to cover new config-tree endpoint`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_explorer_config.py tests/test_explorer_modes.py -v
