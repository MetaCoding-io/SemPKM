---
estimated_steps: 7
estimated_files: 1
---

# T02: Extend seed script with Phase 5 — create demo dashboard and demo user row

**Slice:** S03 — Demo tour + dashboard + CTA banner
**Milestone:** M025

## Description

Extend `scripts/seed-demo-data.py` with a new Phase 5 that creates a demo user row in the SQLite `users` table (needed for FK constraint) and a pre-built demo dashboard demonstrating cross-view context filtering. The dashboard uses a deterministic UUID so the demo tour (T01) can navigate to it. Phase numbering: existing Phase 4 (verification) becomes Phase 6, new Phase 5 (dashboard) goes after Phase 3 (bodies).

## Steps

1. **Add imports** at the top of `seed-demo-data.py`:
   ```python
   import json
   import uuid as _uuid
   from app.db.session import async_session_factory
   from app.auth.models import User
   from app.dashboard.models import DashboardSpec
   ```

2. **Define constants** near the top of the file alongside existing namespace constants:
   ```python
   DEMO_USER_UUID = _uuid.UUID("00000000-0000-0000-0000-000000000000")
   DEMO_DASHBOARD_UUID = _uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
   ```

3. **Write `phase_5_dashboard()` async function** that:
   - Opens a session via `async_session_factory()`
   - Uses `session.merge()` to insert-or-update a `User` row:
     ```python
     demo_user = User(
         id=DEMO_USER_UUID,
         email="demo@sempkm.app",
         display_name="Demo Visitor",
         role="guest",
     )
     await session.merge(demo_user)
     await session.flush()
     ```
   - Checks if dashboard already exists:
     ```python
     from sqlalchemy import select
     result = await session.execute(
         select(DashboardSpec).where(DashboardSpec.id == DEMO_DASHBOARD_UUID)
     )
     existing = result.scalar_one_or_none()
     ```
   - If not existing, creates a `DashboardSpec` with:
     - `id=DEMO_DASHBOARD_UUID`
     - `user_id=DEMO_USER_UUID`
     - `name="Demo Dashboard"`
     - `description="A pre-built dashboard demonstrating cross-view context filtering. Click a row in the table to filter the graph."`
     - `layout="sidebar-main"`
     - `blocks_json` = JSON array with two blocks:
       - Sidebar block: `{"type": "view-embed", "slot": "sidebar", "config": {"view_iri": "urn:sempkm:view:generic-table", "emits_context": true}}`
       - Main block: `{"type": "view-embed", "slot": "main", "config": {"view_iri": "urn:sempkm:view:generic-graph", "listens_to_context": "iri"}}`
   - Commits the session
   - Prints progress: `[5/6] Creating demo dashboard...` and `  ✓ Demo dashboard created` or `  ✓ Demo dashboard already exists (skipped)`

4. **Renumber Phase 4 → Phase 6** — The existing verification phase (currently labeled `[4/4]`) becomes `[6/6]`. Update all progress print statements from `[4/4]` to `[6/6]`. The existing edge phase `[2/4]` → `[2/6]`, bodies phase `[3/4]` → `[3/6]`, etc.

   Actually, simpler approach: just renumber the current 4 phases. New numbering:
   - Phase 1: Install models `[1/6]`
   - Phase 2: Cross-model edges `[2/6]`
   - Phase 3: Markdown bodies `[3/6]`
   - Phase 4: Demo user + dashboard `[4/6]`  ← NEW (use phase 4 slot, shift verification)
   - Phase 5: (reserved, or skip to keep it clean)
   
   Better: keep it simple — add Phase 5 and renumber verification to Phase 6. Total phases: 5 real + 1 verify = 6 phases. Update the `[N/M]` labels throughout.

   Wait — actually the existing code uses `[1/4]` through `[4/4]`. The simplest approach: insert Phase 5 before the existing Phase 4 (verification), then renumber verification to `[5/5]`. So:
   - Phase 1: Install models `[1/5]`
   - Phase 2: Cross-model edges `[2/5]`  
   - Phase 3: Markdown bodies `[3/5]`
   - Phase 4: Demo dashboard `[4/5]` ← NEW
   - Phase 5: Verify `[5/5]` (was Phase 4)

5. **Update verification phase** — Add a dashboard check to Phase 5 (verification). Query the SQLite database for the dashboard count:
   ```python
   async with async_session_factory() as session:
       from sqlalchemy import func, select
       result = await session.execute(select(func.count()).select_from(DashboardSpec))
       dashboard_count = result.scalar()
   print(f"  dashboards: {dashboard_count} (expected ≥1)")
   ```

6. **Update `--verify-only` path** — When `--verify-only` is passed, the script skips phases 1-4 and runs only Phase 5 (verification). Make sure the dashboard count check is included in the verify-only path.

7. **Handle import ordering** — The `json` import is already at the top (standard library). `uuid` is already imported as well. The `app.db.session` and `app.auth.models` imports must come after the `sys.path` manipulation block that already exists at the top.

## Must-Haves

- [ ] Demo user row inserted into `users` table with UUID `00000000-0000-0000-0000-000000000000`
- [ ] Dashboard created with deterministic UUID `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee`
- [ ] Dashboard has `sidebar-main` layout with table view-embed (emits_context) and graph view-embed (listens_to_context)
- [ ] Dashboard owned by demo user UUID
- [ ] Phase is idempotent — re-running skips if dashboard exists
- [ ] Verification phase includes dashboard count check
- [ ] Phase numbering updated throughout the file

## Verification

- `python3 -c "import ast; ast.parse(open('scripts/seed-demo-data.py').read())"` — valid Python syntax
- `grep "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" scripts/seed-demo-data.py` — dashboard UUID present
- `grep "Demo Dashboard" scripts/seed-demo-data.py` — dashboard name present
- `grep "demo@sempkm.app" scripts/seed-demo-data.py` — demo user email present
- `grep "sidebar-main" scripts/seed-demo-data.py` — layout type present
- Run against live demo stack: `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py` — Phase 4 creates dashboard, Phase 5 shows dashboard count ≥1

## Inputs

- `scripts/seed-demo-data.py` — Existing 4-phase seed script (~800 lines). The script already has `sys.path` manipulation, imports from `app.*` modules, and uses `asyncio.run(main())` pattern. See S02 summary for full details.
- `backend/app/db/session.py` — Exports `async_session_factory = async_sessionmaker(engine, expire_on_commit=False)`. Used for SQLite session access.
- `backend/app/auth/models.py` — `User` model with `id` (UUID primary key), `email`, `display_name`, `role` columns.
- `backend/app/dashboard/models.py` — `DashboardSpec` model with `id`, `user_id` (FK to users.id), `name`, `description`, `layout`, `blocks_json` columns. `VALID_LAYOUTS = {"single", "sidebar-main", "grid-2x2", "grid-3", "top-bottom"}`. `VALID_BLOCK_TYPES = {"view-embed", "markdown", "object-embed", "create-form", "sparql-result", "divider"}`.
- Demo user UUID: `00000000-0000-0000-0000-000000000000` (from `backend/app/auth/dependencies.py` line 23).

## Expected Output

- `scripts/seed-demo-data.py` — Extended with Phase 4 (demo dashboard creation) and renumbered verification Phase 5. ~50 new lines. Dashboard uses well-known UUID matching T01's tour step 6.

## Observability Impact

- **New runtime signal:** Phase 4 prints `✓ Demo user ensured (demo@sempkm.app)` and either `✓ Demo dashboard created` or `✓ Demo dashboard already exists (skipped)` — distinguishes first-run creation from idempotent skip.
- **Verification surface:** Phase 5 now includes `Dashboards` row in the verification table, printing actual count vs expected `≥1`. `--verify-only` flag includes this check.
- **Inspection commands:** `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py --verify-only` shows all counts including dashboards. Direct SQLite query: `SELECT * FROM dashboard_specs WHERE id = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'`.
- **Failure visibility:** Phase 4 wrapped in `try/except` in main() — prints `✗ Phase 4 failed critically: {error}` and continues to Phase 5 verification. Dashboard count `0` in verification table signals creation failure.
