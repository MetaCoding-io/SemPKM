---
phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, aiosqlite, asyncpg, sqlite, postgresql, orm, docker]

# Dependency graph
requires:
  - phase: 01-core-data-foundation
    provides: "Docker Compose infrastructure, FastAPI app with config"
provides:
  - "SQLAlchemy async ORM base (DeclarativeBase)"
  - "Dual-database engine factory (SQLite/PostgreSQL)"
  - "AsyncSession factory and FastAPI dependency"
  - "User, UserSession, Invitation, InstanceConfig ORM models"
  - "Alembic migration infrastructure with render_as_batch=True"
  - "Initial migration creating 4 auth tables"
  - "Hardened Docker Compose (no RDF4J port exposure, persistent data volume)"
affects: [06-02, 06-03, 06-04]

# Tech tracking
tech-stack:
  added: [sqlalchemy, alembic, aiosqlite, asyncpg, itsdangerous]
  patterns: [dual-database-engine-factory, async-session-dependency, string-role-fields]

key-files:
  created:
    - backend/app/db/base.py
    - backend/app/db/engine.py
    - backend/app/db/session.py
    - backend/app/auth/models.py
    - backend/alembic.ini
    - backend/migrations/env.py
    - backend/migrations/script.py.mako
    - backend/migrations/versions/001_initial_auth_tables.py
  modified:
    - backend/pyproject.toml
    - backend/app/config.py
    - docker-compose.yml
    - backend/Dockerfile

key-decisions:
  - "String(20) for role columns instead of Enum to avoid SQLite/PostgreSQL dialect differences"
  - "render_as_batch=True in Alembic env.py for SQLite ALTER TABLE compatibility"
  - "RDF4J port removed from Docker Compose host mapping (security hardening)"
  - "Auto-generated secret key path persisted to data volume"

patterns-established:
  - "Dual-database engine factory: create_engine() returns AsyncEngine based on DATABASE_URL scheme"
  - "AsyncSession FastAPI dependency: get_db_session() yields session with commit/rollback"
  - "String role fields with application-layer validation instead of SQL Enum"

requirements-completed: [AUTH-01, INFRA-01]

# Metrics
duration: 4min
completed: 2026-02-22
---

# Phase 6 Plan 01: SQL Data Layer Foundation Summary

**SQLAlchemy 2.0 async ORM with 4 auth tables, Alembic migrations with SQLite batch mode, and Docker hardening with persistent data volume**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22T06:36:45Z
- **Completed:** 2026-02-22T06:40:55Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- SQL data layer foundation with User, UserSession, Invitation, InstanceConfig models supporting both SQLite and PostgreSQL via the same schema
- Alembic migration infrastructure with render_as_batch=True for SQLite compatibility and async engine support
- Docker Compose security hardened: RDF4J port no longer exposed to host, persistent data volume for SQLite and secrets

## Task Commits

Each task was committed atomically:

1. **Task 1: Dependencies, config, and Docker hardening** - `3e33af9` (feat)
2. **Task 2: SQLAlchemy ORM models, database engine, and Alembic migrations** - `378d27c` (feat)

## Files Created/Modified
- `backend/app/db/base.py` - DeclarativeBase for all ORM models
- `backend/app/db/engine.py` - Dual-database async engine factory (SQLite/PostgreSQL)
- `backend/app/db/session.py` - AsyncSession factory and FastAPI dependency
- `backend/app/auth/models.py` - User, UserSession, Invitation, InstanceConfig ORM models
- `backend/alembic.ini` - Alembic configuration
- `backend/migrations/env.py` - Async Alembic env with render_as_batch=True
- `backend/migrations/script.py.mako` - Alembic migration template
- `backend/migrations/versions/001_initial_auth_tables.py` - Initial migration creating 4 tables with indexes
- `backend/pyproject.toml` - Added sqlalchemy, alembic, aiosqlite, asyncpg, itsdangerous
- `backend/app/config.py` - Extended with database_url, secret_key, session_duration, SMTP settings
- `docker-compose.yml` - Removed RDF4J port, added sempkm_data volume, added DB env vars
- `backend/Dockerfile` - Added /app/data directory and VOLUME directive

## Decisions Made
- Used String(20) for role columns instead of Enum type to avoid SQLite/PostgreSQL dialect differences (per Research Pitfall 1)
- Configured render_as_batch=True in both offline and online Alembic modes for SQLite ALTER TABLE compatibility
- Removed RDF4J 8080:8080 port exposure from docker-compose.yml per locked decision
- Auto-generated secret key path stored in data volume for zero-config local setup

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- SQL database layer ready for auth service (Plan 02) to build on
- ORM models importable, engine factory tested, session dependency available
- Alembic migration infrastructure ready for schema evolution
- Docker infrastructure hardened and persistent data volume configured

## Self-Check: PASSED

All 10 created files verified on disk. Both task commits (3e33af9, 378d27c) verified in git log.

---
*Phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness*
*Completed: 2026-02-22*
