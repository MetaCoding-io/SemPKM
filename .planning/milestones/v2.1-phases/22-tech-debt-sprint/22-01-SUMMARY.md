---
phase: 22-tech-debt-sprint
plan: 01
subsystem: database
tags: [alembic, migrations, session-cleanup, sqlite, fastapi-lifespan, docker]

# Dependency graph
requires: []
provides:
  - "Programmatic Alembic migration runner in FastAPI lifespan (replaces create_all)"
  - "Automatic expired session cleanup on application startup"
  - "Docker image includes alembic.ini and migrations/ directory"
  - "fileConfig fix preserves application loggers after Alembic runs"
affects: [22-02, 22-03, future-schema-migrations]

# Tech tracking
tech-stack:
  added: [alembic-programmatic-api]
  patterns: [asyncio-to-thread-for-sync-alembic, startup-session-purge]

key-files:
  created: []
  modified:
    - backend/app/main.py
    - backend/app/auth/service.py
    - backend/migrations/env.py
    - backend/Dockerfile

key-decisions:
  - "asyncio.to_thread wraps Alembic upgrade to avoid nested event loop (env.py uses asyncio.run internally)"
  - "AlembicConfig and alembic_command aliases avoid name collision with existing Config usage in main.py"

patterns-established:
  - "Alembic programmatic migration: use asyncio.to_thread(alembic_command.upgrade, cfg, 'head') in async lifespan"
  - "Startup cleanup pattern: call service cleanup methods in lifespan after service creation, log only if non-zero"

requirements-completed: [TECH-01, TECH-03]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 22 Plan 01: Alembic Migration Runner and Session Cleanup Summary

**Programmatic Alembic migration runner replaces create_all in FastAPI lifespan, with automatic expired session purge on startup**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T02:35:13Z
- **Completed:** 2026-03-01T02:37:24Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Replaced `Base.metadata.create_all()` with `alembic command.upgrade("head")` in application lifespan, enabling proper schema evolution without manual DB drops
- Added `cleanup_expired_sessions()` method to AuthService and integrated it into startup, preventing unbounded session table growth
- Fixed `fileConfig` in `migrations/env.py` with `disable_existing_loggers=False` to prevent Alembic from silencing application loggers
- Updated Dockerfile to include `alembic.ini` and `migrations/` directory in the container image

## Task Commits

Each task was committed atomically:

1. **Task 1: Add cleanup_expired_sessions to AuthService and fix Alembic env.py** - `a79c4b6` (feat)
2. **Task 2: Replace create_all with Alembic migration runner and add session cleanup to lifespan** - `528f1f3` (feat)

## Files Created/Modified
- `backend/app/auth/service.py` - Added `cleanup_expired_sessions()` method that deletes sessions where `expires_at <= now`
- `backend/migrations/env.py` - Fixed `fileConfig` call with `disable_existing_loggers=False`
- `backend/app/main.py` - Replaced `create_all` with Alembic programmatic migration runner; added session cleanup call; removed unused `Base` import; added `asyncio`, `alembic_command`, and `AlembicConfig` imports
- `backend/Dockerfile` - Added `COPY alembic.ini .` and `COPY migrations/ migrations/` before application code

## Decisions Made
- Used `asyncio.to_thread` to wrap synchronous Alembic `command.upgrade()` call because `env.py` uses `asyncio.run()` internally, which cannot nest inside FastAPI's running event loop
- Used `AlembicConfig` and `alembic_command` aliases to avoid name collision with existing `Config` usage in main.py
- Removed `Base` import from main.py since `create_all` is no longer used (verified no other references)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Alembic migration runner is in place; future schema changes only need a new migration file
- Session cleanup runs automatically on every startup
- Ready for Plan 02 (SMTP email transport) and Plan 03 (ViewSpec cache TTL)

## Self-Check: PASSED

All 4 modified files exist. Both task commits (a79c4b6, 528f1f3) verified in git log. SUMMARY.md created.

---
*Phase: 22-tech-debt-sprint*
*Completed: 2026-03-01*
