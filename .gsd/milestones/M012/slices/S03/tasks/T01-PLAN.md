---
estimated_steps: 4
estimated_files: 5
---

# T01: Backend model, migration, service, and unit tests

**Slice:** S03 — Workspace Personas
**Milestone:** M012

## Description

Create the backend foundation for the persona system: a `Persona` SQLAlchemy model, Alembic migration, and `PersonaService` with full CRUD plus activation and state-save semantics. Validate everything with comprehensive unit tests using in-memory SQLite. This task has zero frontend dependencies — it establishes the data layer that T02 (API routes) and T03 (frontend JS) will consume.

Follow the `DashboardSpec` / `DashboardService` pattern closely — same model structure (UUID PK, user_id FK, JSON text columns, timestamps), same service pattern (async session factory, dataclass read models, user-scoped operations).

**Relevant skill:** `test` (for unit test generation patterns)

## Steps

1. Create `backend/app/persona/__init__.py` (empty module init).

2. Create `backend/app/persona/models.py` with `Persona` SQLAlchemy model:
   - `id`: UUID primary key, default `uuid.uuid4`
   - `user_id`: UUID FK to `users.id` with `ondelete="CASCADE"`, indexed
   - `name`: String(255), not nullable
   - `layout_json`: Text, default `"{}"`, server_default `"{}"`
   - `sidebar_positions_json`: Text, default `"{}"`, server_default `"{}"`
   - `explorer_mode`: String(50), default `"by-type"`, server_default `"by-type"`
   - `is_active`: Boolean, default `False`, server_default `sa.false()` (SQLAlchemy `false()` for DDL)
   - `created_at`: DateTime(timezone=True), server_default `func.now()`
   - `updated_at`: DateTime(timezone=True), server_default `func.now()`, `onupdate=func.now()`
   - Import from `app.db.base import Base`
   - Table name: `personas`

3. Create `backend/migrations/versions/013_personas.py` following `012_workflow_specs.py` pattern exactly:
   - `revision = "013"`, `down_revision = "012"`
   - `upgrade()`: `op.create_table("personas", ...)` with all columns matching the model
   - `downgrade()`: `op.drop_table("personas")`
   - Include index on `user_id` column

4. Create `backend/app/persona/service.py` with `PersonaData` dataclass and `PersonaService` class:
   - `PersonaData` dataclass: `id` (str), `user_id` (str), `name` (str), `layout_json` (str), `sidebar_positions_json` (str), `explorer_mode` (str), `is_active` (bool), `created_at` (str), `updated_at` (str)
   - `PersonaService.__init__(self, session_factory)` — stores session factory
   - `async create(user_id, name, layout_json="", sidebar_positions_json="", explorer_mode="by-type") -> PersonaData` — creates persona, returns data
   - `async list_for_user(user_id) -> list[PersonaData]` — returns all personas for user, ordered by name. **Important:** For the list endpoint, include all fields. The router will decide what to expose.
   - `async get(persona_id) -> PersonaData | None`
   - `async update(persona_id, user_id, **updates) -> PersonaData | None` — update name only. Returns None if not found or wrong user.
   - `async delete(persona_id, user_id) -> bool` — delete persona. If the deleted persona was active and other personas exist, activate the first remaining one. Returns True if deleted.
   - `async activate(persona_id, user_id) -> PersonaData | None` — deactivate all user's personas, then activate this one. Returns None if not found or wrong user.
   - `async get_active(user_id) -> PersonaData | None` — returns the active persona or None.
   - `async save_state(persona_id, user_id, layout_json=None, sidebar_positions_json=None, explorer_mode=None) -> PersonaData | None` — update state fields (only provided ones). Returns None if not found or wrong user.
   - Private `_to_data(spec: Persona) -> PersonaData` — converts ORM model to dataclass.

5. Create `backend/tests/test_persona_service.py` with 12+ tests:
   - Fixture: `async_session_factory` (in-memory SQLite, `Base.metadata.create_all`), `service`, `user_id` — same pattern as `test_dashboard.py`
   - `test_create_persona` — create with name, verify returned data has correct fields
   - `test_list_personas_empty` — list returns empty for new user
   - `test_list_personas_ordered` — create multiple, list returns alphabetically sorted
   - `test_get_persona` — create then get by ID
   - `test_get_persona_not_found` — returns None for nonexistent ID
   - `test_update_persona_name` — update name, verify change
   - `test_update_wrong_user` — returns None when user_id doesn't match
   - `test_delete_persona` — delete returns True, persona gone from list
   - `test_delete_active_activates_another` — delete active persona → another gets activated
   - `test_activate_persona` — activate one, verify is_active=True, others False
   - `test_activate_only_one_active` — create 3, activate each in turn, only last is active
   - `test_get_active` — activate one, `get_active()` returns it
   - `test_get_active_none` — no personas → returns None
   - `test_save_state` — save layout_json + positions + mode, verify stored
   - `test_save_state_partial` — save only layout_json, others unchanged

## Must-Haves

- [ ] `Persona` model has all 9 columns (id, user_id, name, layout_json, sidebar_positions_json, explorer_mode, is_active, created_at, updated_at)
- [ ] Migration 013 creates `personas` table with proper types and FK
- [ ] `PersonaService` has all 8 methods (create, list_for_user, get, update, delete, activate, get_active, save_state)
- [ ] `activate()` enforces single-active-persona constraint (deactivate all, then activate one)
- [ ] `delete()` of active persona auto-activates another if available
- [ ] All 12+ unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_persona_service.py -v` — all tests pass
- `grep -c "async def test_" backend/tests/test_persona_service.py` returns 12 or more

## Observability Impact

- **New signals:** `PersonaService` methods log via `logging.getLogger(__name__)` — `INFO` on create/activate/delete, `WARNING` on not-found or wrong-user access attempts.
- **Inspection surface:** `personas` SQLite table queryable via `sqlite3 backend/sempkm.db "SELECT id, name, is_active FROM personas"`. Service methods return `PersonaData` dataclasses with all fields for programmatic inspection.
- **Failure visibility:** All service methods return `None` or `False` for not-found/wrong-user instead of raising exceptions — callers (T02 router) translate these to 404/403 HTTP responses. Unit tests verify these failure paths explicitly.
- **Test verification:** `pytest tests/test_persona_service.py -v` output shows per-test pass/fail with descriptive names covering all business rules.

## Inputs

- `backend/app/dashboard/models.py` — reference model pattern (SQLAlchemy model with UUID PK, user FK, JSON text columns, timestamps)
- `backend/app/dashboard/service.py` — reference service pattern (async CRUD with session factory, dataclass read model)
- `backend/migrations/versions/012_workflow_specs.py` — reference migration pattern (revision chain, create_table)
- `backend/tests/test_dashboard.py` — reference test pattern (in-memory SQLite fixtures)
- `backend/app/db/base.py` — Base class for SQLAlchemy models
- `backend/app/auth/models.py` — User model (for FK and test fixture)

## Expected Output

- `backend/app/persona/__init__.py` — empty module init
- `backend/app/persona/models.py` — Persona SQLAlchemy model
- `backend/app/persona/service.py` — PersonaService with CRUD + activate + save_state
- `backend/migrations/versions/013_personas.py` — Alembic migration creating personas table
- `backend/tests/test_persona_service.py` — 12+ unit tests all passing
