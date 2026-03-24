---
estimated_steps: 5
estimated_files: 4
skills_used:
  - test
---

# T01: ContextRule model, migration, and RulesEngine service with unit tests

**Slice:** S02 — Auto-Persona Rules Engine & Settings UI
**Milestone:** M037

## Description

Create the data model and core evaluation logic for context-aware auto-persona rules. The ContextRule SQLAlchemy model stores per-user rules with JSON conditions (AND logic) and a target persona_id. The Alembic migration creates the `context_rules` table and adds a `manual_override` boolean to the existing `user_context` table. The RulesEngine class loads enabled rules sorted by priority (desc) and returns the first matching persona_id, or None.

## Steps

1. Create `backend/app/context/rules_models.py` with the `ContextRule` SQLAlchemy model:
   - `id` (UUID PK), `user_id` (FK to `users.id` with CASCADE, indexed), `name` (String 255, not null), `priority` (Integer, default 0), `conditions` (JSON — stores a dict like `{"location_zone": "office", "time_period": "work_hours"}`), `persona_id` (String 36, not null — stores the target persona UUID as string), `enabled` (Boolean, default True), `created_at` (DateTime, server_default now), `updated_at` (DateTime, server_default now, onupdate now)
   - Table name: `context_rules`
   - Import from `app.db.base import Base`

2. Create Alembic migration `backend/migrations/versions/019_context_rules.py`:
   - Revision ID: `019`, Revises: `018`
   - `upgrade()`: Create `context_rules` table with all columns from step 1. Add `manual_override` Boolean column to `user_context` table (server_default false, nullable=False — use `batch_alter_table` for SQLite compatibility).
   - `downgrade()`: Drop `context_rules` table. Remove `manual_override` column from `user_context` (batch_alter_table).

3. Create `backend/app/context/rules_engine.py` with the `RulesEngine` class:
   - Constructor takes `session_factory` (same pattern as ContextService/PersonaService)
   - `async def evaluate(self, user_id: uuid.UUID, context_data: dict) -> str | None` — loads all enabled `ContextRule` rows for user_id sorted by `priority` DESC, then `created_at` ASC (tiebreaker). For each rule, check if ALL conditions match the context_data: for each key in `rule.conditions`, `context_data.get(key)` must equal the condition value. Skip conditions where the value is None/null. First matching rule wins — return its `persona_id`. Return None if no rule matches.
   - `async def create_rule(self, user_id, name, conditions, persona_id, priority=0, enabled=True) -> ContextRule`
   - `async def list_rules(self, user_id) -> list[ContextRule]`
   - `async def get_rule(self, rule_id, user_id) -> ContextRule | None`
   - `async def update_rule(self, rule_id, user_id, **updates) -> ContextRule | None`
   - `async def delete_rule(self, rule_id, user_id) -> bool`
   - Add structured logging: `context.rule_matched` with rule name and persona_id, `context.no_rule_matched` when no rule fires

4. Write `backend/tests/test_rules_engine.py` — comprehensive unit tests using the same in-memory SQLite pattern as `test_context_service.py`:
   - Fixture: db_engine (create_async_engine sqlite+aiosqlite://), session_factory, user_id, rules_engine
   - Test evaluate: single rule match, multiple rules with priority ordering (highest priority wins), AND conditions (all must match), partial context (context has fewer fields than conditions → no match), disabled rules skipped, no rules → None, rule with empty conditions → always matches, conditions with null value ignored
   - Test CRUD: create, list (ordered by priority desc), get, update, delete, delete nonexistent returns False, get nonexistent returns None, authorization (wrong user_id returns None/False)
   - Target: 12-15 tests

5. Verify migration applies cleanly: `cd backend && alembic upgrade head` (or check that the migration file is syntactically correct via Python import)

## Must-Haves

- [ ] ContextRule model with all specified fields and JSON conditions column
- [ ] Alembic migration 019 creates `context_rules` and adds `manual_override` to `user_context`
- [ ] RulesEngine.evaluate() returns correct persona_id with priority ordering and AND logic
- [ ] RulesEngine.evaluate() returns None when no rule matches or all rules disabled
- [ ] CRUD methods (create, list, get, update, delete) work with user_id authorization
- [ ] All unit tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py -v` — all tests pass
- `python -c "import ast; ast.parse(open('backend/migrations/versions/019_context_rules.py').read())"` — migration is syntactically valid

## Inputs

- `backend/app/context/models.py` — existing UserContext model (migration adds manual_override column)
- `backend/app/context/service.py` — pattern reference for session_factory usage
- `backend/app/db/base.py` — Base class for SQLAlchemy models
- `backend/migrations/versions/018_user_context.py` — previous migration (revision chain)
- `backend/tests/test_context_service.py` — test pattern reference (in-memory SQLite fixtures)

## Expected Output

- `backend/app/context/rules_models.py` — ContextRule SQLAlchemy model
- `backend/app/context/rules_engine.py` — RulesEngine class with evaluate() and CRUD methods
- `backend/migrations/versions/019_context_rules.py` — Alembic migration for context_rules table + manual_override column
- `backend/tests/test_rules_engine.py` — comprehensive unit tests (12-15 tests)
