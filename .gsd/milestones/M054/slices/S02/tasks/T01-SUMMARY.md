---
id: T01
parent: S02
milestone: M054
key_files:
  - backend/app/browser/explorer_models.py
  - backend/app/browser/explorer_config_service.py
  - backend/migrations/versions/026_add_explorer_configs.py
  - backend/app/browser/workspace.py
  - backend/app/main.py
  - backend/tests/test_explorer_config_service.py
key_decisions:
  - Presets use user_id=NULL (system-level, visible to all users via OR query)
  - Update/delete structurally reject preset rows via is_preset=False in WHERE clause
  - list_for_user returns presets first (ORDER BY is_preset DESC, name ASC)
duration: 
verification_result: passed
completed_at: 2026-04-06T04:58:52.257Z
blocker_discovered: false
---

# T01: Created ExplorerConfigSpec model, async CRUD service with By Type/By Tag preset seeding, 4 REST API endpoints, Alembic migration 026, and 24 passing unit tests

**Created ExplorerConfigSpec model, async CRUD service with By Type/By Tag preset seeding, 4 REST API endpoints, Alembic migration 026, and 24 passing unit tests**

## What Happened

Built the full persistence layer for explorer configurations following the DashboardSpec/DashboardService pattern. Created the SQLAlchemy model with UUID PK, nullable user_id FK for system presets, config_json Text field, and is_preset Boolean. The service provides create/get/list_for_user/update/delete/get_or_create_presets methods. Presets (By Type, By Tag) are is_preset=True rows with user_id=NULL, visible to all users via OR query. Update and delete structurally reject preset rows. Added 4 REST endpoints to workspace_router (GET list, POST create, PATCH update, DELETE). Wired ExplorerConfigService in main.py lifespan. All 24 unit tests pass covering CRUD, presets, user isolation, and config_json round-trip.

## Verification

Ran pytest with 24 tests all passing (0.63s). Verified model and service imports succeed. Confirmed all 4 API routes are registered on workspace_router.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_explorer_config_service.py -v` | 0 | ✅ pass | 4000ms |
| 2 | `cd backend && .venv/bin/python -c "from app.browser.explorer_models import ExplorerConfigSpec; print('Model OK')"` | 0 | ✅ pass | 500ms |
| 3 | `cd backend && .venv/bin/python -c "from app.browser.explorer_config_service import ExplorerConfigService; print('Service OK')"` | 0 | ✅ pass | 500ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/explorer_models.py`
- `backend/app/browser/explorer_config_service.py`
- `backend/migrations/versions/026_add_explorer_configs.py`
- `backend/app/browser/workspace.py`
- `backend/app/main.py`
- `backend/tests/test_explorer_config_service.py`
