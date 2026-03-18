---
id: T02
parent: S01
milestone: M009
provides:
  - 5 SQLAlchemy ORM models for app platform state (AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission)
  - Alembic migration 013 creating all 5 tables with FK cascade and composite index
key_files:
  - backend/app/apps/models.py
  - backend/migrations/versions/013_app_tables.py
key_decisions:
  - Used Mapped[T] + mapped_column() pattern (matching WorkflowSpec) rather than legacy Column() style
  - Added ORM relationships with cascade="all, delete-orphan" on AppInstance for programmatic cascade in addition to DB-level ondelete CASCADE
  - Boolean server_default="0" for SQLite compatibility (SQLite stores booleans as integers)
patterns_established:
  - App platform models live in backend/app/apps/models.py, separate from mental model models
  - All child tables FK to app_instances.app_id with ondelete CASCADE
observability_surfaces:
  - app_instances.status / error_message / restart_count — primary lifecycle state columns queried by future AppManager
  - app_task_runs.status / error_message / duration_ms — task execution history for debugging
  - app_task_config.paused — user-initiated task suppression flag
duration: 10m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: SQLAlchemy models + Alembic migration 013

**Defined 5 SQLAlchemy ORM models and Alembic migration 013 for app platform persistent state tracking.**

## What Happened

Created `backend/app/apps/models.py` with 5 models matching design §11 SQL schemas exactly:
- **AppInstance** — app registry with status/PID/socket/restart tracking (TEXT PK on app_id)
- **AppTaskRun** — task execution history with autoincrement PK, composite index on (app_id, task_id)
- **AppTaskConfig** — user-adjustable interval overrides and pause state (composite PK)
- **AppRendererPref** — which app renders which type_iri in read/edit mode (composite PK)
- **AppPermission** — approved permissions snapshot with approval metadata (1:1 with AppInstance)

All child tables have `ForeignKey("app_instances.app_id", ondelete="CASCADE")`. ORM-level relationships with `cascade="all, delete-orphan"` added on AppInstance for programmatic cascade.

Created `backend/migrations/versions/013_app_tables.py` with revision chain 012→013. Tables created in dependency order; downgrade drops in reverse order with explicit index drop.

`PyJWT` and `packaging` deps were already added to pyproject.toml in T01 — no changes needed there.

## Verification

- `from app.apps.models import AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission` → **OK** (all 5 importable)
- `ast.parse(open('migrations/versions/013_app_tables.py').read())` → **OK** (migration syntactically valid)
- Introspected all models programmatically: table names, column types, PKs, nullability, and FKs all match design §11
- Manifest tests still pass: `pytest tests/test_app_manifest.py` → **60 passed**

### Slice-level verification status (intermediate — T02 of T04):
- ✅ `pytest tests/test_app_manifest.py -v` — 60 passed
- ✅ Models importable from `app.apps.models`
- ✅ Manifest schema importable from `app.apps.manifest`
- ⏳ `pytest tests/test_app_manager.py -v` — not yet (T03 scope)
- ⏳ `pytest tests/test_app_lifecycle_contract.py -v` — not yet (T04 scope)
- ⏳ Manager + registry importable — not yet (T03 scope)

## Diagnostics

- To inspect model schema: `PYTHONPATH=. python -c "from app.apps.models import AppInstance; print([(c.name, str(c.type)) for c in AppInstance.__table__.columns])"`
- Migration chain: revision 013 depends on 012 — run `alembic history` to verify chain integrity
- All FK constraints use ondelete CASCADE — deleting an app_instances row cascades to all child tables

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/models.py` — 5 SQLAlchemy ORM models for app platform state
- `backend/migrations/versions/013_app_tables.py` — Alembic migration creating all 5 tables
- `.gsd/milestones/M009/slices/S01/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
