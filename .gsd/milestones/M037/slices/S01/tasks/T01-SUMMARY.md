---
id: T01
parent: S01
milestone: M037
provides:
  - UserContext SQLAlchemy model with per-user upsert semantics
  - ContextService with update/get_current and TTL-based staleness
  - ContextBroadcast SSE fan-out manager
  - Alembic migration 018 creating user_context table
key_files:
  - backend/app/context/models.py
  - backend/app/context/service.py
  - backend/app/context/broadcast.py
  - backend/migrations/versions/018_user_context.py
key_decisions:
  - Reused SSEEvent from app.lint.broadcast rather than duplicating the dataclass
  - ContextData uses string-typed user_id (matches PersonaData pattern for JSON serialization)
patterns_established:
  - Upsert pattern in ContextService.update() — SELECT then INSERT/UPDATE, only writing fields explicitly provided
  - Naive datetime guard in get_current() — replace(tzinfo=utc) before timedelta math (from KNOWLEDGE.md)
observability_surfaces:
  - context.update structured log on every upsert (user_id, location_zone, device_id)
  - context.stale structured log when staleness detected on read (user_id, age_seconds, ttl)
  - ContextData.is_stale field in API response
  - ContextBroadcast.client_count property for monitoring connected SSE clients
duration: 15m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Context domain — model, migration, service, and broadcast

**Created context domain package with UserContext model, ContextService (upsert + TTL staleness), ContextBroadcast (SSE fan-out), and Alembic migration 018**

## What Happened

Created the `backend/app/context/` package with four files forming the data layer for user context awareness. The `UserContext` model has a unique constraint on `user_id` (one row per user, enforcing upsert semantics). `ContextService` provides two methods: `update()` which does SELECT→INSERT/UPDATE only for fields explicitly passed, and `get_current()` which computes `is_stale` by comparing `updated_at` against a configurable TTL (default 900s / 15 minutes). The naive-datetime SQLite guard from KNOWLEDGE.md is applied before timedelta computation. `ContextBroadcast` follows the exact `LintBroadcast` fan-out pattern with `subscribe()`/`unsubscribe()`/`publish()` and reuses `SSEEvent` from `app.lint.broadcast`. Migration 018 chains from 017 and creates the `user_context` table with a unique index on `user_id`.

## Verification

All three task-level verification checks passed:
1. All imports succeed (`UserContext`, `ContextService`, `ContextData`, `ContextBroadcast`)
2. Table name assertion `user_context` confirmed
3. Migration file exists at expected path

Additional structural checks confirmed: `user_id` is unique+indexed with FK to `users.id`, default TTL is 900s, `ContextBroadcast` subscribe/unsubscribe/client_count works correctly, `ContextData` defaults are correct.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from app.context.models import UserContext; from app.context.service import ContextService, ContextData; from app.context.broadcast import ContextBroadcast; print('All imports OK')"` | 0 | ✅ pass | <1s |
| 2 | `cd backend && .venv/bin/python -c "from app.context.models import UserContext; assert UserContext.__tablename__ == 'user_context'; print('Table name OK')"` | 0 | ✅ pass | <1s |
| 3 | `test -f backend/migrations/versions/018_user_context.py` | 0 | ✅ pass | <1s |
| 4 | Structural checks (unique, index, FK, TTL, broadcast fan-out) | 0 | ✅ pass | <1s |

## Diagnostics

- `ContextData.is_stale` field: True when context age exceeds TTL, False after fresh update, provides the primary staleness signal
- `ContextBroadcast.client_count`: number of active SSE subscribers, available as a property
- Structured logs: `context.update` on every upsert (includes user_id, location_zone, device_id); `context.stale` on stale reads (includes age_seconds, ttl)
- `None` return from `get_current()` indicates user has never posted context

## Deviations

- Added a failure-path verification step to the slice plan as required by pre-flight observability gap check (unauthenticated POST returns 401, GET response includes `is_stale` field)

## Known Issues

None.

## Files Created/Modified

- `backend/app/context/__init__.py` — Package init for context awareness module
- `backend/app/context/models.py` — UserContext SQLAlchemy model (user_id unique+indexed FK, location/activity/time/calendar/device fields)
- `backend/app/context/service.py` — ContextService with update (upsert) and get_current (TTL staleness), plus ContextData dataclass
- `backend/app/context/broadcast.py` — ContextBroadcast SSE fan-out manager reusing SSEEvent from lint.broadcast
- `backend/migrations/versions/018_user_context.py` — Alembic migration 018 creating user_context table with unique user_id index
- `.gsd/milestones/M037/slices/S01/S01-PLAN.md` — Added failure-path verification step per pre-flight requirement
