---
phase: 27-vfs-write-auth
plan: 01
subsystem: auth
tags: [webdav, api-tokens, sqlalchemy, wsgidav, sha256, fastapi]

# Dependency graph
requires:
  - phase: 26-vfs-mvp-read-only
    provides: SemPKMWsgiAuthenticator skeleton, ApiToken ORM model, migration 003, wsgidav mount at /dav

provides:
  - ApiToken ORM model with full bidirectional User relationship (User.api_tokens + ApiToken.user)
  - AuthService.list_api_tokens and AuthService.revoke_api_token methods
  - GET /api/auth/tokens endpoint returning token list without plaintext
  - DELETE /api/auth/tokens/{token_id} endpoint returning 204/404
  - SemPKMWsgiAuthenticator sets environ["sempkm.user_id"] for DAV provider write path
  - TokenListItem Pydantic schema for list response

affects: [27-02-write-path, 27-03-settings-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Token revocation: DELETE endpoint user-scoped (user_id + token_id) preventing cross-user revocation"
    - "SHA-256 hash storage: plaintext only returned once on creation, never stored"
    - "DAV environ context: sempkm.user_id and sempkm.user_email set on successful Basic auth"

key-files:
  created: []
  modified:
    - backend/app/auth/models.py
    - backend/app/auth/service.py
    - backend/app/auth/router.py
    - backend/app/auth/schemas.py
    - backend/app/vfs/auth.py

key-decisions:
  - "ApiToken model naming: kept existing 'ApiToken' (not 'APIToken' from plan) to avoid breaking existing imports in main.py and vfs/auth.py"
  - "revoke_api_token deletes row (hard delete) rather than soft-deleting via revoked_at field — simpler, list query returns only active tokens automatically"
  - "environ sempkm.user_id added to basic_auth_user to support write path user context in plan 27-02"

patterns-established:
  - "Token CRUD: POST creates (201), GET lists without plaintext, DELETE revokes (204/404)"
  - "User-scoped deletes: revoke_api_token(user_id, token_id) always filters by both IDs"

requirements-completed: [VFS-03]

# Metrics
duration: 5min
completed: 2026-03-01
---

# Phase 27 Plan 01: VFS Write + Auth — Token Management Summary

**API token CRUD endpoints (POST/GET/DELETE /api/auth/tokens) with SHA-256 hash storage and wsgidav Basic auth validator setting user_id in WSGI environ**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-01T07:19:02Z
- **Completed:** 2026-03-01T07:24:00Z
- **Tasks:** 5
- **Files modified:** 5

## Accomplishments

- Completed the bidirectional ORM relationship between User and ApiToken (back-populates in both directions)
- Added `list_api_tokens` and `revoke_api_token` async methods to AuthService
- Added `GET /api/auth/tokens` and `DELETE /api/auth/tokens/{token_id}` FastAPI endpoints with correct 204/404 responses
- Fixed `SemPKMWsgiAuthenticator.basic_auth_user` to set `environ["sempkm.user_id"]` for downstream DAV provider write path use

## Task Commits

Each task was committed atomically:

1. **Task 27-01-1: Add APIToken ORM model relationships** - `9002b4e` (feat)
2. **Task 27-01-2: Alembic migration 003_api_tokens** - `c594c5b` (Phase 26-01, already committed)
3. **Task 27-01-3: Add AuthService token lifecycle methods** - `0b763a5` (feat)
4. **Task 27-01-4: VFS auth environ user_id** - `c252b8b` (feat)
5. **Task 27-01-5: GET and DELETE token endpoints** - `5e50e3e` (feat)

**Plan metadata:** (docs commit, see below)

## Files Created/Modified

- `backend/app/auth/models.py` - Added `User.api_tokens` relationship and `ApiToken.user` back-populates
- `backend/app/auth/service.py` - Added `list_api_tokens` and `revoke_api_token` async methods
- `backend/app/auth/router.py` - Added `GET /api/auth/tokens` and `DELETE /api/auth/tokens/{token_id}` endpoints
- `backend/app/auth/schemas.py` - Added `TokenListItem` Pydantic response model
- `backend/app/vfs/auth.py` - Refactored `basic_auth_user` to set `environ["sempkm.user_id"]`

## Decisions Made

- Kept `ApiToken` class name (Phase 26 convention) rather than renaming to `APIToken` (plan spec) — avoids breaking 5 existing import sites in main.py and vfs/auth.py
- Used hard-delete for `revoke_api_token` rather than soft-delete via `revoked_at` — cleaner list queries, no need to filter revoked_at in list endpoint
- Loaded User separately in `basic_auth_user` (two queries instead of join) to retrieve `user.id` for environ; join approach doesn't naturally expose user.id without extra work

## Deviations from Plan

### Pre-existing Work from Phase 26-01

The Phase 26-01 implementation (commit `c594c5b`) already built most of this plan's requirements:
- `ApiToken` ORM model (with extra `last_used_at` and `revoked_at` columns beyond plan spec)
- Alembic migration `003_api_tokens.py` (matches plan spec exactly)
- `SemPKMWsgiAuthenticator` in `vfs/auth.py` (named differently from plan's `SemPKMTokenAuthenticator`)
- `create_api_token` and `verify_api_token` AuthService methods
- `POST /api/auth/tokens` endpoint

**Remaining gaps filled in this plan:**
- User.api_tokens back-reference relationship (task 1)
- `list_api_tokens` and `revoke_api_token` methods (task 3)
- `environ["sempkm.user_id"]` in authenticator (task 4)
- `GET` and `DELETE /api/auth/tokens` endpoints (task 5)

**Total deviations:** 0 auto-fixes needed — all gaps were planned additions; pre-existing Phase 26 work was recognized and reused rather than re-implemented.

## Issues Encountered

None - the Phase 26 foundation was solid. Only additive changes needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Token auth foundation complete: create, list, revoke, validate via Basic auth
- `environ["sempkm.user_id"]` now available for DAV provider write path (plan 27-02)
- Plan 27-02 (write path) can proceed: provider has user context needed for event store writes
- Plan 27-03 (Settings UI) can proceed: GET/POST/DELETE endpoints fully operational

## Self-Check: PASSED

All 7 files confirmed present on disk. All 4 task commits (9002b4e, 0b763a5, c252b8b, 5e50e3e) confirmed in git log.

---
*Phase: 27-vfs-write-auth*
*Completed: 2026-03-01*
