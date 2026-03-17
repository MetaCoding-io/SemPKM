---
estimated_steps: 4
estimated_files: 3
---

# T02: SQLAlchemy models + Alembic migration 013 + new deps

**Slice:** S01 — Manifest, DB Schema & Subprocess Lifecycle
**Milestone:** M009

## Description

Define the 5 SQLAlchemy models for app platform state tracking and create the Alembic migration to build the tables. These tables store app instance status, task execution history, user-adjustable task config, renderer preferences, and approved permissions.

## Steps

1. Create `backend/app/apps/models.py` with 5 SQLAlchemy models matching the design §11 SQL schemas:

   **AppInstance:**
   - `app_id` TEXT PRIMARY KEY
   - `version` TEXT NOT NULL
   - `status` TEXT NOT NULL DEFAULT 'stopped' (running|stopped|error|installing)
   - `pid` INTEGER nullable
   - `socket_path` TEXT nullable
   - `started_at` TIMESTAMP nullable
   - `installed_at` TIMESTAMP NOT NULL (server_default=func.now())
   - `manifest_hash` TEXT NOT NULL
   - `error_message` TEXT nullable
   - `restart_count` INTEGER DEFAULT 0

   **AppTaskRun:**
   - `id` INTEGER PRIMARY KEY AUTOINCREMENT
   - `app_id` TEXT NOT NULL FK → app_instances.app_id (ondelete CASCADE)
   - `task_id` TEXT NOT NULL
   - `run_id` TEXT NOT NULL (UUID as string)
   - `started_at` TIMESTAMP NOT NULL
   - `finished_at` TIMESTAMP nullable
   - `status` TEXT NOT NULL DEFAULT 'running' (running|success|error)
   - `duration_ms` INTEGER nullable
   - `error_message` TEXT nullable
   - `summary` TEXT nullable
   - Index on (app_id, task_id)

   **AppTaskConfig:**
   - Composite PK: `app_id` TEXT + `task_id` TEXT
   - `app_id` FK → app_instances.app_id (ondelete CASCADE)
   - `interval_override` TEXT nullable
   - `paused` BOOLEAN DEFAULT FALSE

   **AppRendererPref:**
   - Composite PK: `type_iri` TEXT + `mode` TEXT
   - `app_id` TEXT NOT NULL FK → app_instances.app_id (ondelete CASCADE)

   **AppPermission:**
   - `app_id` TEXT PRIMARY KEY FK → app_instances.app_id (ondelete CASCADE)
   - `permissions_json` TEXT NOT NULL
   - `approved_at` TIMESTAMP NOT NULL
   - `approved_by` TEXT NOT NULL

   Use the existing SQLAlchemy pattern from the codebase: `from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, func` and `from sqlalchemy.orm import DeclarativeBase` (check existing models for the exact base class import pattern).

2. Create `backend/migrations/versions/013_app_tables.py`:
   - `revision = "013"`, `down_revision = "012"`
   - `upgrade()`: Create all 5 tables using `op.create_table()` with proper column types and constraints
   - `downgrade()`: Drop all 5 tables in reverse dependency order (AppPermission, AppRendererPref, AppTaskConfig, AppTaskRun, AppInstance)
   - Follow the exact pattern from `012_workflow_specs.py` (use `sa.Column`, `sa.String`, `sa.Text`, `sa.ForeignKey`, etc.)

3. Verify models are importable: `python -c "from app.apps.models import AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission; print('OK')"`

4. Verify migration file is syntactically valid: `python -c "import ast; ast.parse(open('migrations/versions/013_app_tables.py').read()); print('OK')"`

## Must-Haves

- [ ] 5 SQLAlchemy models with correct column types, defaults, and FK relationships
- [ ] Alembic migration 013 creating all tables with proper revision chain (revises 012)
- [ ] CASCADE delete from app_instances propagates to child tables
- [ ] All models importable from `app.apps.models`

## Verification

- `cd backend && python -c "from app.apps.models import AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission; print('OK')"` — importable
- `cd backend && python -c "import ast; ast.parse(open('migrations/versions/013_app_tables.py').read()); print('OK')"` — migration valid
- Models have correct table names and column types matching design §11

## Inputs

- `.gsd/design/APP-PLATFORM-DESIGN.md` §11 (SQLite tables for app monitoring) — exact SQL schema
- `backend/migrations/versions/012_workflow_specs.py` — migration file pattern
- `backend/app/apps/__init__.py` — package from T01

## Observability Impact

These models define the persistent state surface for the entire app platform:
- `app_instances.status` / `error_message` / `restart_count` — primary lifecycle observability; future agents query these columns to determine app health
- `app_task_runs.status` / `error_message` / `duration_ms` — task execution history; enables debugging slow or failing tasks
- `app_task_config.paused` — indicates user-initiated suppression of task scheduling
- No new log lines or endpoints in this task (schema only); runtime observability is added in T03+ when the manager writes to these tables

## Expected Output

- `backend/app/apps/models.py` — 5 SQLAlchemy model classes
- `backend/migrations/versions/013_app_tables.py` — Alembic migration creating all 5 tables
