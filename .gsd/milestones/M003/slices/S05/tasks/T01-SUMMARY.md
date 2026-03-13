---
id: T01
parent: S05
milestone: M003
provides:
  - UserFavorite SQLAlchemy model for per-user starred objects
  - Alembic migration 009 creating user_favorites table
  - Unit tests covering full CRUD and toggle logic
key_files:
  - backend/app/favorites/models.py
  - backend/migrations/versions/009_user_favorites.py
  - backend/tests/test_favorites.py
key_decisions:
  - Followed existing project ORM patterns (uuid PK, DateTime(timezone=True), String for IRI, ondelete CASCADE FK)
patterns_established:
  - favorites package at backend/app/favorites/ for all favorites-related code
  - In-memory SQLite async test fixtures for model-level unit tests (db_session, user fixtures)
observability_surfaces:
  - user_favorites SQL table queryable directly
  - UniqueConstraint raises IntegrityError on duplicate (user_id, object_iri) — callers must handle
duration: 10min
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: UserFavorite model, migration, and unit tests

**Created UserFavorite ORM model, Alembic migration 009, and 6 unit tests covering create, duplicate rejection, delete, per-user list, and toggle logic.**

## What Happened

Created the `backend/app/favorites/` package with the `UserFavorite` model following existing project ORM patterns (uuid PK, `ForeignKey("users.id", ondelete="CASCADE")`, `String(2048)` for object IRI, `DateTime(timezone=True)` with `server_default=func.now()`). Added a `UniqueConstraint` on `(user_id, object_iri)` and an index on `user_id`.

Migration 009 chains from 008 and creates the `user_favorites` table with matching columns, constraint, and index. The migration is fully reversible (downgrade/upgrade tested).

Added the model import to `backend/migrations/env.py` for Alembic autogenerate awareness.

Wrote 6 async unit tests using in-memory SQLite: create+read, duplicate rejection (IntegrityError), delete, per-user list filtering, toggle-add, and toggle-remove.

## Verification

- `docker compose exec api bash -c "cd /app && python -m alembic upgrade head"` — migration 009 applied successfully
- `docker compose exec api bash -c "cd /app && python -m alembic downgrade 008"` + `upgrade head` — reversible
- `backend/.venv/bin/pytest tests/test_favorites.py -v` — all 6 tests passed
- Slice-level verification: `pytest backend/tests/test_favorites.py -v` — PASS (this task's check)
- Slice-level verification: `npx playwright test e2e/tests/20-favorites/` — not yet applicable (no UI yet)
- Slice-level verification: `curl .../browser/favorites/list` — not yet applicable (no endpoint yet)

## Diagnostics

- Query `user_favorites` table directly via SQLite client to inspect stored favorites
- Model importable from `app.favorites.models.UserFavorite`
- UniqueConstraint violation raises `sqlalchemy.exc.IntegrityError` — callers must catch and handle

## Deviations

None.

## Known Issues

- The Docker container does not mount `backend/migrations/` — migration file had to be copied in via `docker compose cp`. Future tasks that add migrations will need the same approach or a container rebuild.
- pytest is not installed in the production Docker image (dev deps skipped in Dockerfile). Tests run against the local venv.

## Files Created/Modified

- `backend/app/favorites/__init__.py` — empty package init
- `backend/app/favorites/models.py` — UserFavorite ORM model with uuid PK, user_id FK, object_iri, created_at, unique constraint
- `backend/migrations/versions/009_user_favorites.py` — Alembic migration creating user_favorites table with index
- `backend/migrations/env.py` — added UserFavorite import for Alembic awareness
- `backend/tests/test_favorites.py` — 6 async unit tests for model CRUD operations
