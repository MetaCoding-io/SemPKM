---
id: T03
parent: S06
milestone: M031
provides:
  - seed_sample_data() function for idempotent sample data creation
  - "Getting Started" dashboard with sidebar-main layout, markdown + view-embed blocks
  - "Create & Review" workflow with form + view steps
  - Startup hook in main.py that seeds data for first user when none exists
key_files:
  - backend/app/dashboard/seed.py
  - backend/app/main.py
  - backend/tests/test_seed_data.py
key_decisions:
  - Seed runs only when setup_complete is True (user exists), skips entirely in first-run setup mode
  - Used local imports inside the startup helper to avoid polluting module-level imports in main.py
  - Seed targets only the first user from the DB (single-tenant assumption consistent with existing codebase)
patterns_established:
  - Idempotent seed pattern: check list_for_user() emptiness before creating, return dict of what was created for logging
observability_surfaces:
  - docker compose logs backend | grep -i seed — shows whether seed created data or was skipped
  - Seed failure logged at WARNING level with exc_info; never crashes the app
  - Individual seed actions logged at INFO level in seed.py with user_id
duration: 12m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T03: Create seed data module for sample dashboards and workflows

**Created idempotent seed_sample_data() module that inserts a "Getting Started" dashboard and "Create & Review" workflow for users with none, wired into app startup with error isolation.**

## What Happened

1. Created `backend/app/dashboard/seed.py` with an async `seed_sample_data(dashboard_service, workflow_service, user_id)` function. It checks `list_for_user()` for both dashboards and workflows independently — if a user has zero of either, it creates the sample. The dashboard uses `sidebar-main` layout with a markdown welcome block and a view-embed block. The workflow has a two-step form→view flow. Returns `{"dashboard_created": bool, "workflow_created": bool}` for logging.

2. Wired the seed into `backend/app/main.py` in the lifespan startup, after the setup mode detection block. The seed only runs when `setup_complete` is True (meaning at least one user exists). It queries the first user from the DB, calls `seed_sample_data`, and logs the outcome. The entire block is wrapped in try/except so seed failures never crash the app — errors are logged at WARNING level with full traceback.

3. Created `backend/tests/test_seed_data.py` with 4 test cases using AsyncMock:
   - Empty user → both dashboard and workflow created
   - User with existing data → nothing created, create() never called
   - Dashboard exists but no workflow → only workflow created
   - Workflow exists but no dashboard → only dashboard created

4. Added Observability Impact section to T03-PLAN.md (pre-flight fix).

## Verification

All three task-level checks pass. All nine slice-level verification checks pass (this is the final task of the slice).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('backend/app/dashboard/seed.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `rg 'seed_sample' backend/app/main.py` | 0 | ✅ pass (2 matches) | <1s |
| 3 | `docker compose exec api python -m pytest /app/test_seed_data.py -x -q` | 0 | ✅ pass (4 passed) | 0.2s |
| 4 | `grep -c 'field-help' backend/app/templates/browser/dashboard_builder.html` → 13 | 0 | ✅ pass (≥10) | <1s |
| 5 | `grep -c 'field-help' backend/app/templates/browser/workflow_builder.html` → 6 | 0 | ✅ pass (≥5) | <1s |
| 6 | `grep -c 'step-config-renderer' backend/app/templates/browser/workflow_builder.html` → 0 | 1 | ✅ pass (0 matches) | <1s |
| 7 | `grep -q 'class-search' ...dashboard_builder.html` | 0 | ✅ pass | <1s |
| 8 | `grep -q 'class-search' ...workflow_builder.html` | 0 | ✅ pass | <1s |
| 9 | `grep -q 'builder-error' ...dashboard_builder.html && ...workflow_builder.html` | 0 | ✅ pass | <1s |

## Diagnostics

- **Startup log:** `docker compose logs backend | grep -i seed` — shows "Seeded sample data: {'dashboard_created': True, 'workflow_created': True}" on first run with a user.
- **Idempotency:** On subsequent startups, no seed log lines appear (both `list_for_user()` return non-empty).
- **Failure resilience:** If seed raises an exception, `logger.warning("Seed sample data failed (non-fatal)", exc_info=True)` fires and startup continues normally.
- **Import verification:** `docker compose exec api python -c "from app.dashboard.seed import seed_sample_data; print('OK')"` confirms the module loads in the container.

## Deviations

- Used `sa_select` alias for the SQLAlchemy `select` import in main.py to avoid shadowing any existing `select` in scope (there wasn't one, but it's defensive).
- Added a 4th test case (workflow-exists-but-no-dashboard) beyond the plan's 2 required cases, for complete coverage of the mixed-state scenario.
- pytest-asyncio was not pre-installed in the Docker container venv; installed it to run the tests. Tests are self-contained and don't need the DB.

## Known Issues

None.

## Files Created/Modified

- `backend/app/dashboard/seed.py` — New seed data module with `seed_sample_data()` async function
- `backend/app/main.py` — Added seed data startup hook after setup mode detection, wrapped in try/except
- `backend/tests/test_seed_data.py` — Unit tests covering empty, existing, and mixed-state seed scenarios (4 tests)
- `.gsd/milestones/M031/slices/S06/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M031/slices/S06/S06-PLAN.md` — Marked T03 as done
