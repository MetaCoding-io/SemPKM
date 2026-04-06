# S02: Config Persistence, Multi-Panel & Presets

**Goal:** Explorer configurations persist server-side with CRUD API; multiple independent OBJECTS sections can coexist; By Type, By Tag, and Hierarchy presets are available as built-in options.
**Demo:** After this: User saves a named config → reloads browser → config appears in selector → clicks Duplicate → second OBJECTS section with different config appears → selects By Type preset in the original → both render independently

## Tasks
- [x] **T01: Created ExplorerConfigSpec model, async CRUD service with By Type/By Tag preset seeding, 4 REST API endpoints, Alembic migration 026, and 24 passing unit tests** — Create the ExplorerConfigSpec SQLAlchemy model, Alembic migration 026, async CRUD service following DashboardService pattern, 4 REST API endpoints (GET list, POST create, PATCH update, DELETE), preset seeding (By Type, By Tag built-in configs), and unit tests.

Steps:
1. Create `backend/app/browser/explorer_models.py` with ExplorerConfigSpec model (id UUID PK, user_id FK users.id, name String(255), config_json Text, is_preset bool, created_at/updated_at DateTime). Follow DashboardSpec pattern exactly.
2. Create `backend/migrations/versions/026_add_explorer_configs.py` (revision='026', down_revision='025') creating the explorer_configs table.
3. Create `backend/app/browser/explorer_config_service.py` with ExplorerConfigService class (session_factory constructor, async create/list_for_user/get/update/delete/get_or_create_presets methods). Presets: 'By Type' = {group_by:'type', sort_by:'label', sort_order:'asc'}, 'By Tag' = {group_by:'tag', sort_by:'label', sort_order:'asc'}. Presets are is_preset=True rows with a fixed user_id (system user UUID or null). get_or_create_presets() creates them if they don't exist.
4. Add 4 API endpoints to workspace_router in `backend/app/browser/workspace.py`:
   - GET /api/explorer/configs — returns JSON list of user's configs + presets
   - POST /api/explorer/configs — creates new config from {name, config_json}
   - PATCH /api/explorer/configs/{config_id} — updates name or config_json
   - DELETE /api/explorer/configs/{config_id} — deletes user config (not presets)
   All require get_current_user auth. Use _get_explorer_config_service(request) helper like dashboard router pattern.
5. Wire ExplorerConfigService in `backend/app/main.py` lifespan: `app.state.explorer_config_service = ExplorerConfigService(async_session_factory)`
6. Create `backend/tests/test_explorer_config_service.py` with unit tests covering: create config, list configs, get by id, update config, delete config, preset auto-creation, user isolation (user A can't see user B's configs), delete preset rejected, config_json round-trip.

Constraints:
- Pattern source: DashboardSpec/DashboardService — copy the structure closely.
- In-memory SQLite FK constraint (Knowledge Pattern #8): test fixtures must import User model.
- Presets use is_preset=True and user_id=None (system-level, visible to all users).
- Migration down_revision must be '025'.
- Hierarchy is NOT stored as a preset row — it uses a separate rendering path (_handle_hierarchy). The frontend will handle hierarchy as a special option in the selector (T02 scope).
  - Estimate: 2h
  - Files: backend/app/browser/explorer_models.py, backend/app/browser/explorer_config_service.py, backend/migrations/versions/026_add_explorer_configs.py, backend/app/browser/workspace.py, backend/app/main.py, backend/tests/test_explorer_config_service.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_explorer_config_service.py -v && .venv/bin/python -c "from app.browser.explorer_models import ExplorerConfigSpec; print('Model OK')" && .venv/bin/python -c "from app.browser.explorer_config_service import ExplorerConfigService; print('Service OK')"
- [x] **T02: Added config selector dropdown with presets (By Type, By Tag, Hierarchy), save/load/delete for named configs, localStorage persistence across page reloads, and builder panel hide for Hierarchy mode** — Add a config selector UI above the config builder panel that shows saved configs and presets. Wire save/load to the CRUD API. Add Hierarchy as a special option alongside the composable presets.

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
  - Estimate: 2h
  - Files: frontend/static/js/explorer-config.js, backend/app/templates/browser/explorer_config_panel.html, frontend/static/css/explorer-config.css
  - Verify: Browser verification: open workspace → config selector shows presets and saved configs. Save a config with name → reload page → config appears in selector → click to apply → tree renders correctly. Select Hierarchy preset → tree renders hierarchy mode. Select By Type preset → tree renders type-grouped mode.
- [x] **T03: Refactored explorer config to section-scoped DOM access and added multi-panel OBJECTS duplication with independent configs** — Enable multiple independent OBJECTS explorer sections with a Duplicate button. Refactor ID-based DOM access to class-based section-scoped access.

Steps:
1. Refactor `frontend/static/js/explorer-config.js` DOM access:
   - Replace all `_el('explorer-config-type')` etc. with section-scoped helpers: `_sectionEl(sectionRoot, '.explorer-config-type')` using `sectionRoot.querySelector()`.
   - Change all element IDs in `explorer_config_panel.html` to classes (e.g., `id="explorer-config-type"` → `class="explorer-config-type"`).
   - Keep the primary section's `id="section-objects"` for backward compat.
   - Each function (`applyExplorerConfig`, `resetExplorerConfig`, `loadSelectedConfig`, etc.) takes an optional `sectionRoot` parameter (defaults to `document.getElementById('section-objects')`).
   - The config state (_configActive, _optionsData) becomes per-section. Use a Map keyed by section element or section index.
2. Add 'Duplicate' button in OBJECTS section header in `backend/app/templates/browser/workspace.html`:
   - Button in the header-actions span, next to the existing gear/refresh/plus buttons.
   - onclick calls `window.SemPKM.duplicateExplorerSection()`.
3. Implement `duplicateExplorerSection()` in `explorer-config.js`:
   - Clones the section-objects element structure.
   - Assigns a unique suffix (e.g., `section-objects-1`) to the clone's ID.
   - Inserts the clone after the original section in the sidebar.
   - Initializes config options for the clone (reuses cached _optionsData).
   - Each clone gets its own config state, tree body, and selector.
   - Clone's tree starts empty or with default nav_tree.
   - Add a 'Close' button in the cloned section header (to remove it).
4. Update `frontend/static/css/explorer-config.css` for multi-panel styling (duplicate sections visually distinct or identical).
5. Ensure each section's config selector and config builder operate independently — changing type in section A doesn't affect section B.

Constraints:
- Primary section retains `id="section-objects"` for any code that references it directly.
- Duplicated sections use the existing drag-reorder (`data-panel-name`) and `explorer-section` patterns.
- Each section's active config (localStorage UUID) is stored with a section-scoped key (e.g., `sempkm_explorer_active_config_0`, `sempkm_explorer_active_config_1`).
- The `refreshExplorerTree()` export should continue to work on the primary section for backward compat. Add `refreshExplorerTreeForSection(sectionRoot)` for section-specific refresh.
- The summary bar, config panel, and tree body are all section-scoped — no cross-section state leaking.
  - Estimate: 2h
  - Files: frontend/static/js/explorer-config.js, backend/app/templates/browser/explorer_config_panel.html, backend/app/templates/browser/workspace.html, frontend/static/css/explorer-config.css
  - Verify: Browser verification: click Duplicate → second OBJECTS section appears → configure each with different type filter/group → both render independently → close duplicate section → original unaffected. refreshExplorerTree() still works on primary section.
