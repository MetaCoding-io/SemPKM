---
id: T02
parent: S01
milestone: M009
provides:
  - 5 SQLAlchemy models (AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission) for app platform state tracking
  - Alembic migration 014 creating all 5 tables with FK cascade constraints and composite indexes
key_files:
  - backend/app/apps/models.py
  - backend/migrations/versions/014_app_tables.py
key_decisions:
  - "Migration numbered 014 (not 013 as task plan estimated) because 013_personas.py already existed on this branch"
patterns_established:
  - "App platform models use Text() for all string columns (matching SQLite schema from design §11) rather than String(N) — no length constraints at DB level"
  - "Composite PKs defined via multiple primary_key=True on mapped_column (same pattern as existing codebase)"
observability_surfaces:
  - "app_instances.status / error_message / restart_count — primary lifecycle observability columns"
  - "app_task_runs.status / duration_ms / error_message — task execution history for debugging"
  - "app_task_config.paused — user-initiated task scheduling suppression"
duration: 8m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: SQLAlchemy models + Alembic migration 014 for app platform tables

**Defined 5 SQLAlchemy ORM models matching design §11 SQL schemas and created Alembic migration 014 with all tables, FK cascade constraints, and composite index on app_task_runs(app_id, task_id)**

## What Happened

Created `backend/app/apps/models.py` with 5 SQLAlchemy models using the modern `Mapped`/`mapped_column` pattern (matching WorkflowSpec and Persona models in the codebase):

- **AppInstance** — app_id TEXT PK, status with server_default 'stopped', restart_count with server_default 0, all columns from design §11
- **AppTaskRun** — autoincrement INTEGER PK, app_id FK with CASCADE, composite index on (app_id, task_id) for query performance
- **AppTaskConfig** — composite PK (app_id, task_id), both with proper FK CASCADE
- **AppRendererPref** — composite PK (type_iri, mode), app_id FK with CASCADE
- **AppPermission** — app_id PK and FK with CASCADE, permissions_json, approved_at, approved_by

Created `backend/migrations/versions/014_app_tables.py` (numbered 014 because 013_personas.py already existed). The migration creates all 5 tables in dependency order and drops them in reverse order. The downgrade also drops the composite index before the table.

Both `PyJWT` and `packaging` deps were already present in pyproject.toml from T01.

## Verification

1. Models importable: `from app.apps.models import AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission` — OK
2. Migration syntactically valid: `ast.parse()` — OK
3. Programmatic assertions verified: correct table names, primary keys, FK CASCADE on all 4 child tables, composite index name

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from app.apps.models import AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission; print('OK')"` | 0 | ✅ pass | <1s |
| 2 | `cd backend && python3 -c "import ast; ast.parse(open('migrations/versions/014_app_tables.py').read()); print('OK')"` | 0 | ✅ pass | <1s |
| 3 | Model structure assertions (PKs, FKs, index, CASCADE) | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_app_manifest.py -v` (T01 regression) | 0 | ✅ pass (61/61) | <1s |
| 5 | `cd backend && .venv/bin/python -c "from app.apps.manifest import AppManifestSchema, parse_app_manifest; print('OK')"` | 0 | ✅ pass | <1s |
| 6 | `cd backend && .venv/bin/python -c "from app.apps.manager import AppManager; ..."` | 1 | ⏳ expected (T03 scope) | <1s |

## Diagnostics

These models are schema-only with no runtime behavior. To inspect:
- `AppInstance.__table__.columns` — lists all columns with types and defaults
- `AppTaskRun.__table__.indexes` — shows the composite index
- `AppPermission.__table__.foreign_keys` — shows CASCADE FK configuration
- Migration can be dry-run verified via `alembic upgrade head` in Docker (not attempted — no running DB in CI context)

## Deviations

- **Migration number 014 instead of 013:** The task plan estimated the migration would be 013, but `013_personas.py` already existed from M008 work. Used 014 with `down_revision = "013"` to maintain the correct revision chain.
- **No pyproject.toml changes:** The plan called for adding PyJWT and packaging deps, but they were already added during T01 execution.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/models.py` — 5 SQLAlchemy model classes (AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission)
- `backend/migrations/versions/014_app_tables.py` — Alembic migration creating all 5 tables with FKs, indexes, and proper downgrade
