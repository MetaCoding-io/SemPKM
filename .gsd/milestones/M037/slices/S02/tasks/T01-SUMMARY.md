---
id: T01
parent: S02
milestone: M037
provides:
  - ContextRule SQLAlchemy model (context_rules table)
  - RulesEngine service with evaluate() and CRUD
  - Alembic migration 019 (context_rules + manual_override on user_context)
  - 19 unit tests covering evaluation logic and CRUD
key_files:
  - backend/app/context/rules_models.py
  - backend/app/context/rules_engine.py
  - backend/migrations/versions/019_context_rules.py
  - backend/tests/test_rules_engine.py
key_decisions:
  - Null condition values act as wildcards (skipped during evaluation) rather than requiring explicit null match
  - Empty conditions dict matches any context unconditionally (catch-all rule pattern)
patterns_established:
  - In-memory SQLite tests for models with FK to users.id must import app.auth.models.User to register the table in Base.metadata
observability_surfaces:
  - "context.rule_matched" structured log (user_id, rule_name, persona_id)
  - "context.no_rule_matched" structured log (user_id)
  - "context.rule_created/updated/deleted" CRUD audit logs
duration: 15m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: ContextRule model, migration, and RulesEngine service with unit tests

**Added ContextRule model, Alembic migration 019, and RulesEngine service with priority-ordered AND-condition evaluation and full CRUD — 19 unit tests pass.**

## What Happened

Created four files implementing the context-to-persona rules subsystem:

1. **rules_models.py** — `ContextRule` SQLAlchemy model with UUID PK, user_id FK, name, priority, JSON conditions, persona_id, enabled flag, and timestamps.

2. **019_context_rules.py** — Alembic migration creating the `context_rules` table with index on user_id, and adding `manual_override` boolean column to the existing `user_context` table (using `batch_alter_table` for SQLite compatibility).

3. **rules_engine.py** — `RulesEngine` class following the same `session_factory` pattern as `ContextService`. The `evaluate()` method loads enabled rules sorted by priority DESC / created_at ASC, checks all non-null conditions against context data (AND logic), and returns the first matching rule's persona_id. CRUD methods (create, list, get, update, delete) all scope by user_id for authorization. Structured logging on every evaluation and CRUD operation.

4. **test_rules_engine.py** — 19 async tests covering: single match, priority ordering, AND conditions (full match + partial no-match), disabled rule skip, no rules, empty conditions (catch-all), null condition wildcards, tiebreaker ordering, plus full CRUD including authorization checks for wrong-user access.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py -v` — 19/19 passed in 0.42s
- `python -c "import ast; ast.parse(open('backend/migrations/versions/019_context_rules.py').read())"` — syntax valid

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py -v` | 0 | ✅ pass | 0.42s |
| 2 | `python -c "import ast; ast.parse(open('backend/migrations/versions/019_context_rules.py').read())"` | 0 | ✅ pass | <1s |

## Diagnostics

- **Structured logs:** grep for `context.rule_matched`, `context.no_rule_matched`, `context.rule_created`, `context.rule_updated`, `context.rule_deleted` in application logs
- **Database:** `SELECT * FROM context_rules WHERE user_id = ?` to inspect rules; `SELECT manual_override FROM user_context WHERE user_id = ?` to check override flag
- **Rule evaluation trace:** The `evaluate()` method logs the winning rule name and persona_id on every match, user_id on no-match — enables end-to-end tracing of auto-switch decisions

## Deviations

- Added `import app.auth.models.User` to test file to register the `users` table in SQLAlchemy metadata — required because ContextRule has FK to `users.id` and in-memory SQLite needs all referenced tables in the metadata. The existing `test_context_service.py` has the same latent issue (its tests also fail with the same FK error).

## Known Issues

- `test_context_service.py` has the same FK resolution bug — it needs `from app.auth.models import User` to work. Not fixed here since it's outside this task's scope.

## Files Created/Modified

- `backend/app/context/rules_models.py` — ContextRule SQLAlchemy model (new)
- `backend/app/context/rules_engine.py` — RulesEngine service with evaluate() and CRUD (new)
- `backend/migrations/versions/019_context_rules.py` — Alembic migration for context_rules table + manual_override column (new)
- `backend/tests/test_rules_engine.py` — 19 unit tests for evaluation logic and CRUD (new)
- `.gsd/milestones/M037/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section (modified)
