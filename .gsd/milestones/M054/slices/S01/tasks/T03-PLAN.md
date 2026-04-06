---
estimated_steps: 36
estimated_files: 3
skills_used: []
---

# T03: Frontend config builder UI and explorer JS module

Build the config builder panel UI and a new JS module that manages explorer configuration state, populates the builder dropdowns from the config-options API, and triggers tree re-renders.

**Slice context:** T01+T02 built the backend. This task builds the frontend config panel. T04 wires it into the workspace and replaces the old dropdown.

## Steps

1. Create `frontend/static/js/explorer-config.js` (IIFE pattern, exports to `window.SemPKM`):
   - `initExplorerConfig()` — called once on workspace load:
     - Fetch `/browser/explorer/config-options` to populate type/property/sort dropdowns
     - Bind event listeners on config selects
     - Store current config in module-scoped variable
   - `applyExplorerConfig()` — read current dropdown values, build query params, trigger htmx fetch of `/browser/explorer/config-tree?type_filter=X&group_by=Y&sort_by=Z&sort_order=asc` into `#explorer-tree-body`
   - `resetExplorerConfig()` — clear all selectors, reload default by-type tree
   - `refreshExplorerTree()` — re-apply current config (called after object CRUD)
   - Export: `window.SemPKM.initExplorerConfig`, `window.SemPKM.applyExplorerConfig`, `window.SemPKM.refreshExplorerTree`

2. Create `frontend/static/css/explorer-config.css`:
   - `.explorer-config-panel` — collapsible panel below the OBJECTS header, above the tree body
   - Three rows: Filter (type select), Group By (property select), Sort (property select + asc/desc toggle)
   - Compact styling matching workspace.css explorer theme (dark background, small text, subtle borders)
   - Apply/Reset buttons at bottom
   - Collapsed state: slim bar showing current config summary (e.g. 'Tasks → by Status → Due Date ↑')
   - Expanded state: full form with dropdowns

3. Create `backend/app/templates/browser/explorer_config_panel.html` partial:
   - Config builder form with three `<select>` elements:
     - Type filter: populated from config-options API types list, includes 'All Types' default
     - Group by: populated from config-options API properties for selected type, includes 'None' default; special entries 'By Type', 'By Tag' always available
     - Sort by: 'Label' (default), 'Date Created', plus type-specific properties
   - Sort order toggle button (asc/desc)
   - Apply button triggers `applyExplorerConfig()`
   - Configure toggle button (gear icon) in the OBJECTS header to expand/collapse

4. Wire the type filter dropdown to dynamically update the group-by and sort options:
   - When type changes → fetch properties for that type from config-options → repopulate group-by and sort dropdowns
   - Use `apiFetch()` from `api-fetch.js` (Knowledge pattern 13)

**Key constraints:**
- Follow IIFE pattern matching workspace.js, copilot.js
- Use `apiFetch()` for all fetch calls (Knowledge pattern 13)
- Size Lucide icons via CSS with flex-shrink:0 (CLAUDE.md rule)
- CSS colors use theme tokens via color-mix() (Knowledge pattern 14)
- No inline styles on SVGs (CLAUDE.md rule)

## Inputs

- ``frontend/static/js/workspace.js` — IIFE pattern, refreshNavTree(), explorer mode handling to understand current integration points`
- ``frontend/static/js/api-fetch.js` — apiFetch() for all HTTP calls`
- ``frontend/static/css/workspace.css` — explorer section styling to match`
- ``backend/app/templates/browser/workspace.html` — OBJECTS section structure, explorer-mode-select placement`

## Expected Output

- ``frontend/static/js/explorer-config.js` — config builder JS module with initExplorerConfig, applyExplorerConfig, refreshExplorerTree`
- ``frontend/static/css/explorer-config.css` — config panel styling`
- ``backend/app/templates/browser/explorer_config_panel.html` — config builder form partial`

## Verification

test -f frontend/static/js/explorer-config.js && test -f frontend/static/css/explorer-config.css && test -f backend/app/templates/browser/explorer_config_panel.html && rg 'SemPKM.initExplorerConfig' frontend/static/js/explorer-config.js && rg 'SemPKM.applyExplorerConfig' frontend/static/js/explorer-config.js && rg 'SemPKM.refreshExplorerTree' frontend/static/js/explorer-config.js && rg 'apiFetch' frontend/static/js/explorer-config.js
