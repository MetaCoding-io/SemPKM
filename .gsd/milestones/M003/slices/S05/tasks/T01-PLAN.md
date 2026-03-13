---
estimated_steps: 5
estimated_files: 5
---

# T01: UserFavorite model, migration, and unit tests

**Slice:** S05 — Favorites System
**Milestone:** M003

## Description

Create the SQL storage layer for per-user favorites: a `UserFavorite` SQLAlchemy model, Alembic migration 009 to create the table, and unit tests proving CRUD operations work correctly. This is the foundation that the toggle/list endpoints and all UI will depend on.

## Steps

1. Create `backend/app/favorites/__init__.py` (empty) and `backend/app/favorites/models.py` with `UserFavorite` model — uuid PK, `user_id` FK to `users.id` (UUID, ondelete CASCADE), `object_iri` String(2048), `created_at` DateTime(timezone=True) with server_default=func.now(). Add `UniqueConstraint("user_id", "object_iri", name="uq_user_favorite")`.
2. Create `backend/migrations/versions/009_user_favorites.py` — revision `"009"`, down_revision `"008"`. Use `op.create_table` with columns matching model. Add index on `user_id` for list queries. Use `render_as_batch=True` pattern consistent with existing migrations (SQLite compat).
3. Add `from app.favorites.models import UserFavorite  # noqa: F401` import in `backend/migrations/env.py` so Alembic autogenerate is aware of the model.
4. Write `backend/tests/test_favorites.py` with unit tests: (a) create a UserFavorite row and read it back, (b) verify unique constraint rejects duplicate (user_id, object_iri), (c) delete a favorite and verify it's gone, (d) list favorites for a specific user (returns only that user's), (e) toggle logic test — insert if not exists, delete if exists.
5. Run migration against Docker dev stack and run tests to verify everything works.

## Must-Haves

- [ ] `UserFavorite` model follows project ORM patterns (uuid PK, DateTime with timezone, String for IRI)
- [ ] Alembic migration 009 chains from 008 and creates `user_favorites` table
- [ ] UniqueConstraint on (user_id, object_iri) prevents duplicate favorites
- [ ] Index on user_id for efficient per-user queries
- [ ] Model imported in migrations/env.py for Alembic awareness
- [ ] Unit tests pass covering create, duplicate rejection, delete, per-user list

## Verification

- `docker compose exec backend alembic upgrade head` — migration 009 applies without error
- `docker compose exec backend .venv/bin/pytest backend/tests/test_favorites.py -v` — all tests pass
- `docker compose exec backend alembic downgrade 008` and `upgrade head` — reversible migration

## Observability Impact

- Signals added/changed: None (data layer only, no runtime logging yet)
- How a future agent inspects this: Query `user_favorites` table directly via SQLite/PostgreSQL client; model is importable from `app.favorites.models`
- Failure state exposed: UniqueConstraint violation raises `IntegrityError` — callers must handle

## Inputs

- `backend/app/auth/models.py` — reference ORM pattern (uuid PK, FK to users.id, DateTime with timezone, UniqueConstraint)
- `backend/migrations/versions/008_sharing_promotion.py` — previous migration (down_revision target)
- `backend/migrations/env.py` — import location for new model
- `backend/app/db/session.py` — `get_db_session` dependency for async session access
- `backend/app/db/base.py` — `Base` declarative base for model inheritance

## Expected Output

- `backend/app/favorites/__init__.py` — empty package init
- `backend/app/favorites/models.py` — `UserFavorite` ORM model
- `backend/migrations/versions/009_user_favorites.py` — migration creating `user_favorites` table
- `backend/migrations/env.py` — updated with UserFavorite import
- `backend/tests/test_favorites.py` — unit tests for model CRUD
