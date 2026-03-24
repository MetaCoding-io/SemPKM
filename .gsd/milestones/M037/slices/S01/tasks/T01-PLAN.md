---
estimated_steps: 5
estimated_files: 5
skills_used: []
---

# T01: Context domain — model, migration, service, and broadcast

**Slice:** S01 — Backend Context API & Workspace Indicator
**Milestone:** M037

## Description

Create the `backend/app/context/` package with the four foundational files: SQLAlchemy model (`UserContext`), Alembic migration 018 creating the `user_context` table, `ContextService` with upsert + TTL-based staleness detection, and `ContextBroadcast` for SSE fan-out. This is the data layer that all other context features build on.

## Steps

1. Create `backend/app/context/__init__.py` (empty package init).
2. Create `backend/app/context/models.py` with `UserContext` SQLAlchemy model extending `app.db.base.Base`. Table name: `user_context`. Columns: `id` (UUID PK, default uuid4), `user_id` (UUID FK to `users.id` with `ondelete="CASCADE"`, indexed, unique — one row per user), `location_zone` (String(100), nullable), `activity` (String(50), nullable), `time_period` (String(50), nullable), `calendar_event` (String(500), nullable), `calendar_busy` (Boolean, default False), `device_id` (String(100), nullable), `updated_at` (DateTime with timezone, server_default=func.now(), onupdate=func.now()), `created_at` (DateTime with timezone, server_default=func.now()). Use the same patterns as `backend/app/persona/models.py` (Mapped types, mapped_column).
3. Create `backend/migrations/versions/018_user_context.py` following the pattern of `017_ai_personas.py`. Revision "018", down_revision "017". `upgrade()` creates the `user_context` table. `downgrade()` drops it. Include the unique constraint on `user_id`.
4. Create `backend/app/context/service.py` with `ContextService` class. Constructor takes `session_factory` (same pattern as `PersonaService`). Methods: (a) `async update(user_id: UUID, **fields) -> ContextData` — upsert: SELECT existing row by user_id, if exists UPDATE provided fields + updated_at, if not INSERT new row. Only update fields that are explicitly provided (not None). Return `ContextData` dataclass. (b) `async get_current(user_id: UUID, ttl_seconds: int = 900) -> ContextData | None` — SELECT by user_id, compute `is_stale` as `(now - updated_at).total_seconds() > ttl_seconds`. Handle naive vs aware datetime (see KNOWLEDGE.md: SQLite naive datetimes). Return None if no row exists. Define `ContextData` dataclass with all fields + `is_stale: bool` + `ttl_seconds: int`.
5. Create `backend/app/context/broadcast.py` as a direct adaptation of `backend/app/lint/broadcast.py`. Class name: `ContextBroadcast`. Same `subscribe()`, `unsubscribe()`, `publish()` methods with `asyncio.Queue` fan-out. Reuse the `SSEEvent` import from `app.lint.broadcast` (or define locally if cleaner — prefer reuse).

## Must-Haves

- [ ] `UserContext` model has `user_id` as unique + indexed FK to `users.id`
- [ ] Alembic migration 018 chains from 017 correctly
- [ ] `ContextService.update()` uses upsert (one row per user, not append)
- [ ] `ContextService.get_current()` computes `is_stale` correctly (handles naive datetimes from SQLite)
- [ ] `ContextBroadcast` follows exact fan-out pattern from `LintBroadcast`
- [ ] Default TTL is 900 seconds (15 minutes)

## Verification

- `cd backend && python -c "from app.context.models import UserContext; from app.context.service import ContextService, ContextData; from app.context.broadcast import ContextBroadcast; print('All imports OK')"`
- `cd backend && python -c "from app.context.models import UserContext; assert UserContext.__tablename__ == 'user_context'; print('Table name OK')"`
- `test -f backend/migrations/versions/018_user_context.py`

## Observability Impact

- Signals added/changed: `ContextService` uses Python `logging.getLogger(__name__)` for context.update and context.stale events
- How a future agent inspects this: `ContextData.is_stale` field, `ContextBroadcast.client_count` property
- Failure state exposed: `is_stale=True` when context is old; `None` return when user has no context

## Inputs

- `backend/app/persona/models.py` — SQLAlchemy model pattern to follow
- `backend/app/persona/service.py` — service pattern with session_factory, dataclass return type
- `backend/app/lint/broadcast.py` — SSE broadcast fan-out pattern to replicate
- `backend/migrations/versions/017_ai_personas.py` — migration chain predecessor
- `backend/app/db/base.py` — Base class for ORM models

## Expected Output

- `backend/app/context/__init__.py` — empty package init
- `backend/app/context/models.py` — UserContext SQLAlchemy model
- `backend/app/context/service.py` — ContextService with update/get_current + ContextData dataclass
- `backend/app/context/broadcast.py` — ContextBroadcast SSE fan-out manager
- `backend/migrations/versions/018_user_context.py` — Alembic migration creating user_context table
