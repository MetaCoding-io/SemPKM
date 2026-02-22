---
phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness
plan: 02
subsystem: auth
tags: [itsdangerous, fastapi, session-auth, cookie, passwordless, setup-wizard, rbac]

# Dependency graph
requires:
  - phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness
    provides: "SQLAlchemy ORM models (User, UserSession, Invitation), async engine, session factory"
provides:
  - "Token module: signed magic-link and invitation tokens via itsdangerous"
  - "AuthService: user CRUD, session lifecycle with sliding window, invitation flow"
  - "FastAPI auth dependencies: get_current_user, require_role, optional_current_user"
  - "Auth router: /auth/setup, /auth/magic-link, /auth/verify, /auth/logout, /auth/me, /auth/status"
  - "App lifespan SQL init: table creation, AuthService wiring, setup mode detection"
  - "First-run setup flow: terminal token display, POST claim, httpOnly session cookie"
affects: [06-03, 06-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [cookie-session-auth, sliding-window-session, setup-wizard-flow, naive-utc-datetimes]

key-files:
  created:
    - backend/app/auth/tokens.py
    - backend/app/auth/schemas.py
    - backend/app/auth/service.py
    - backend/app/auth/dependencies.py
    - backend/app/auth/router.py
  modified:
    - backend/app/main.py
    - backend/app/dependencies.py

key-decisions:
  - "Naive UTC datetimes throughout auth code for SQLite compatibility (timezone-aware fails on comparisons)"
  - "Setup token is random (secrets.token_urlsafe), not signed -- stored on disk and verified by string match"
  - "Logout revokes session in DB via token deletion, not just cookie clearing"
  - "Magic link verify auto-creates member user if email not found (passwordless first-login)"

patterns-established:
  - "Cookie-based session auth: httpOnly sempkm_session cookie with DB-backed session lookup"
  - "Sliding window sessions: auto-extend when past 50% of configured lifetime"
  - "Setup wizard flow: terminal token -> POST /auth/setup -> owner created + session cookie"
  - "_utcnow() helper for naive UTC datetimes in SQLite-compatible code"

requirements-completed: [AUTH-02, AUTH-03, AUTH-04, RBAC-01, RBAC-02, RBAC-03]

# Metrics
duration: 8min
completed: 2026-02-22
---

# Phase 6 Plan 02: Authentication Core Summary

**Session-based passwordless auth with itsdangerous tokens, httpOnly cookie sessions with sliding window, and first-run setup wizard flow**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-22T06:44:00Z
- **Completed:** 2026-02-22T06:52:27Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Complete auth subsystem: token generation, service layer, FastAPI dependencies, and REST endpoints
- First-run setup wizard: terminal displays setup token, POST /auth/setup claims instance, returns httpOnly session cookie
- Session lifecycle with sliding window extension at 50% lifetime threshold
- Role-based access control dependencies (get_current_user, require_role) ready for any endpoint

## Task Commits

Each task was committed atomically:

1. **Task 1: Token module, auth schemas, and auth service** - `2b0d658` (feat)
2. **Task 2: Auth dependencies, router, and app wiring** - `92810f4` (feat)

## Files Created/Modified
- `backend/app/auth/tokens.py` - Token generation/verification: setup, magic link, invitation
- `backend/app/auth/schemas.py` - Pydantic request/response models for all auth endpoints
- `backend/app/auth/service.py` - AuthService: user CRUD, session lifecycle, invitation flow
- `backend/app/auth/dependencies.py` - FastAPI dependencies: get_current_user, require_role, optional_current_user
- `backend/app/auth/router.py` - Auth endpoints: setup, magic-link, verify, logout, me, status
- `backend/app/main.py` - SQL table creation, AuthService init, setup mode detection, auth router registration
- `backend/app/dependencies.py` - Added get_auth_service dependency

## Decisions Made
- Used naive UTC datetimes (`_utcnow()` helper) throughout auth code because SQLite returns timezone-naive datetimes, causing TypeError on comparisons with timezone-aware `datetime.now(UTC)`
- Setup token is random `secrets.token_urlsafe(32)`, not cryptographically signed -- it's stored on disk and compared by string equality (simpler, equally secure for its purpose)
- Logout endpoint revokes the session record in the database (not just clearing the cookie), ensuring immediate invalidation
- Magic link `/auth/verify` auto-creates a member user if the email doesn't exist yet, supporting passwordless first-login flow

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed SQLite naive datetime comparison**
- **Found during:** Task 2 (auth dependencies)
- **Issue:** `datetime.now(UTC)` produces timezone-aware datetimes, but SQLite stores/returns naive datetimes. Comparing them raises `TypeError: can't compare offset-naive and offset-aware datetimes`.
- **Fix:** Created `_utcnow()` helper that returns `datetime.now(UTC).replace(tzinfo=None)` for consistent naive UTC datetimes. Applied in both `dependencies.py` and `service.py`.
- **Files modified:** `backend/app/auth/dependencies.py`, `backend/app/auth/service.py`
- **Verification:** Full auth flow works end-to-end with session lookup and sliding window extension
- **Committed in:** `92810f4` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed recursive _utcnow() in service.py**
- **Found during:** Task 2 (verification)
- **Issue:** `replace_all` substitution of `datetime.now(UTC)` also replaced the implementation inside `_utcnow()` itself, causing infinite recursion (`RecursionError: maximum recursion depth exceeded`).
- **Fix:** Restored `datetime.now(UTC).replace(tzinfo=None)` inside the `_utcnow()` function definition.
- **Files modified:** `backend/app/auth/service.py`
- **Verification:** Setup endpoint completes without recursion error
- **Committed in:** `92810f4` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correct datetime handling with SQLite. No scope creep.

## Issues Encountered
None beyond the auto-fixed datetime issues.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Auth dependencies (`get_current_user`, `require_role`) ready to protect any existing endpoint
- Plan 03 can now retrofit auth enforcement on commands, SPARQL, and model management endpoints
- Magic link token generation ready for when SMTP is configured (currently logs in debug mode)
- Invitation flow fully implemented in AuthService, ready for invitation endpoints

## Self-Check: PASSED

All 5 created files verified on disk. Both task commits (2b0d658, 92810f4) verified in git log.

---
*Phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness*
*Completed: 2026-02-22*
