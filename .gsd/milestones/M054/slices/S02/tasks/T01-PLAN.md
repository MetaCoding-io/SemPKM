---
estimated_steps: 19
estimated_files: 6
skills_used: []
---

# T01: ExplorerConfigSpec model, migration, service, and CRUD API endpoints

Create the ExplorerConfigSpec SQLAlchemy model, Alembic migration 026, async CRUD service following DashboardService pattern, 4 REST API endpoints (GET list, POST create, PATCH update, DELETE), preset seeding (By Type, By Tag built-in configs), and unit tests.

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

## Inputs

- ``backend/app/dashboard/models.py` — DashboardSpec pattern to follow for model structure`
- ``backend/app/dashboard/service.py` — DashboardService pattern to follow for CRUD service`
- ``backend/app/dashboard/router.py` — API endpoint pattern (_get_dashboard_service dependency helper)`
- ``backend/app/browser/workspace.py` — existing workspace_router to add endpoints to`
- ``backend/app/main.py` — lifespan function to wire service`
- ``backend/migrations/versions/025_add_source_model.py` — latest migration for down_revision`

## Expected Output

- ``backend/app/browser/explorer_models.py` — ExplorerConfigSpec SQLAlchemy model`
- ``backend/app/browser/explorer_config_service.py` — async CRUD service with preset seeding`
- ``backend/migrations/versions/026_add_explorer_configs.py` — Alembic migration`
- ``backend/app/browser/workspace.py` — 4 new API endpoints added`
- ``backend/app/main.py` — ExplorerConfigService wired on app.state`
- ``backend/tests/test_explorer_config_service.py` — unit tests for CRUD + presets`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_explorer_config_service.py -v && .venv/bin/python -c "from app.browser.explorer_models import ExplorerConfigSpec; print('Model OK')" && .venv/bin/python -c "from app.browser.explorer_config_service import ExplorerConfigService; print('Service OK')"
