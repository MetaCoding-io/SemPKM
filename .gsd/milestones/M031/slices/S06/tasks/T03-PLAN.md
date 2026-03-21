---
estimated_steps: 3
estimated_files: 3
skills_used:
  - test
---

# T03: Create seed data module for sample dashboards and workflows

**Slice:** S06 — Dashboard & Workflow Builder UX
**Milestone:** M031

## Description

Create a seed data module that inserts a sample "Getting Started" dashboard and a "Create & Review" workflow for users who have none. The seed function is called during app startup and is idempotent — it checks `list_for_user()` before creating anything.

## Steps

1. **Create `backend/app/dashboard/seed.py`** with an async function `seed_sample_data`:
   ```python
   async def seed_sample_data(
       dashboard_service: DashboardService,
       workflow_service: WorkflowService,
       user_id: uuid.UUID,
   ) -> dict:
       """Create sample dashboard and workflow if user has none.
       
       Returns dict with keys 'dashboard_created' and 'workflow_created' (bool).
       """
   ```
   The function:
   - Calls `dashboard_service.list_for_user(user_id)`. If empty, creates a "Getting Started" dashboard with `layout="sidebar-main"` and two blocks:
     - Block 1: `type="markdown"`, `slot="sidebar"`, `config={"content": "# Welcome\n\nThis is a sample dashboard..."}` (brief welcome text explaining dashboards)
     - Block 2: `type="view-embed"`, `slot="main"`, `config={"spec_iri": "", "renderer_type": "table"}` (empty spec_iri means "default view" — the dashboard renderer handles this gracefully)
   - Calls `workflow_service.list_for_user(user_id)`. If empty, creates a "Create & Review" workflow with two steps:
     - Step 1: `type="form"`, `label="Create"`, `config={"target_class": ""}` (empty target_class — user configures it)
     - Step 2: `type="view"`, `label="Review"`, `config={"spec_iri": "", "renderer_type": "table"}`
   - Returns `{"dashboard_created": True/False, "workflow_created": True/False}` for logging.

2. **Wire seed into app startup** in `backend/app/main.py`. In the existing startup lifecycle (where `dashboard_service` and `workflow_service` are created), add a call to run seed data. The simplest approach: add a helper function that queries the first user from the DB and calls `seed_sample_data`. Pattern:
   ```python
   from app.dashboard.seed import seed_sample_data
   
   # In the startup block, after services are initialized:
   async def _run_seed_data(app):
       """Seed sample data for users who have no dashboards/workflows."""
       from sqlalchemy import select
       from app.auth.models import User as UserModel
       async with app.state.async_session_factory() as session:
           result = await session.execute(select(UserModel).limit(1))
           user = result.scalar_one_or_none()
           if user:
               outcome = await seed_sample_data(
                   app.state.dashboard_service,
                   app.state.workflow_service,
                   user.id,
               )
               if outcome.get("dashboard_created") or outcome.get("workflow_created"):
                   logger.info("Seeded sample data: %s", outcome)
   ```
   Call `await _run_seed_data(app)` in the startup handler, wrapped in try/except so seed failures don't block app startup. Log any errors at warning level.

3. **Write a unit test** in `backend/tests/test_seed_data.py`:
   - Test `seed_sample_data` with mocked services:
     - When `list_for_user` returns empty lists → `create` is called for both dashboard and workflow, function returns `{"dashboard_created": True, "workflow_created": True}`.
     - When `list_for_user` returns non-empty lists → `create` is NOT called, function returns `{"dashboard_created": False, "workflow_created": False}`.
   - Use `unittest.mock.AsyncMock` for the service mocks.
   - Test is self-contained — no DB required.

## Must-Haves

- [ ] `seed_sample_data` creates a dashboard when user has none
- [ ] `seed_sample_data` creates a workflow when user has none
- [ ] `seed_sample_data` does NOT create duplicates when data already exists
- [ ] Startup hook is wired in `main.py` with error handling (seed failure doesn't crash the app)
- [ ] Unit test covers both the "empty" and "already exists" cases

## Verification

- `python3 -c "import ast; ast.parse(open('backend/app/dashboard/seed.py').read())"` succeeds
- `rg 'seed_sample' backend/app/main.py` returns a match
- `cd backend && python -m pytest tests/test_seed_data.py -x -q` passes

## Inputs

- `backend/app/dashboard/service.py` — `DashboardService` with `create()` and `list_for_user()` methods
- `backend/app/workflow/service.py` — `WorkflowService` with `create()` and `list_for_user()` methods
- `backend/app/main.py` — app startup lifecycle where services are initialized (has `app.state.dashboard_service` and `app.state.workflow_service`)

## Expected Output

- `backend/app/dashboard/seed.py` — new seed data module with `seed_sample_data` function
- `backend/app/main.py` — updated with seed data startup hook
- `backend/tests/test_seed_data.py` — unit test for seed data idempotency
