---
phase: 49-indieauth-provider
plan: 01
subsystem: auth
tags: [indieauth, oauth2, pkce, sqlalchemy, alembic, mf2py]

requires:
  - phase: 48-webid-profile
    provides: "WebID profile URLs and build_profile_url helper"
provides:
  - "IndieAuthCode and IndieAuthToken SQLAlchemy models"
  - "IndieAuthService with code generation, token exchange, refresh rotation, introspection, revocation"
  - "Scope registry (profile, email)"
  - "Pydantic schemas for token/introspection responses"
  - "Alembic migration 006 for indieauth tables"
affects: [49-02, 49-03, 49-04]

tech-stack:
  added: [mf2py]
  patterns: [hash-only-storage, pkce-s256, token-rotation]

key-files:
  created:
    - backend/app/indieauth/__init__.py
    - backend/app/indieauth/models.py
    - backend/app/indieauth/scopes.py
    - backend/app/indieauth/schemas.py
    - backend/app/indieauth/service.py
    - backend/migrations/versions/006_indieauth_tables.py
  modified:
    - backend/pyproject.toml

key-decisions:
  - "Store only SHA-256 hashes of codes/tokens, never plaintext"
  - "60s TTL for authorization codes, 1h access tokens, 30d refresh tokens"
  - "Refresh token rotation on every use (old token deleted, new pair issued)"
  - "SSRF guard on client_id fetching via loopback IP rejection"

patterns-established:
  - "Hash-only storage: all secrets hashed with SHA-256 before DB write"
  - "Token rotation: refresh always issues new pair and deletes old"

requirements-completed: [IAUTH-02, IAUTH-03, IAUTH-04]

duration: 2min
completed: 2026-03-08
---

# Phase 49 Plan 01: IndieAuth Core Service Summary

**IndieAuth data model with PKCE S256, authorization code flow, token rotation, and introspection service layer**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-08T07:40:38Z
- **Completed:** 2026-03-08T07:42:38Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- IndieAuthCode and IndieAuthToken SQLAlchemy models with SHA-256 hash-only storage
- Full IndieAuth service: code generation, PKCE exchange, refresh rotation, introspection, revocation
- Scope registry with profile and email scopes, validation function
- Alembic migration 006 creating both tables with proper indexes

## Task Commits

Each task was committed atomically:

1. **Task 1: Create IndieAuth module with models, scopes, and migration** - `3c9d586` (feat)
2. **Task 2: Create IndieAuth service with code, token, and introspection logic** - `c004170` (feat)

## Files Created/Modified
- `backend/app/indieauth/__init__.py` - Module init with docstring
- `backend/app/indieauth/models.py` - IndieAuthCode and IndieAuthToken ORM models
- `backend/app/indieauth/scopes.py` - Scope registry and validate_scopes function
- `backend/app/indieauth/schemas.py` - TokenResponse, IntrospectionResponse, ClientInfo schemas
- `backend/app/indieauth/service.py` - IndieAuthService with all business logic methods
- `backend/migrations/versions/006_indieauth_tables.py` - Alembic migration for both tables
- `backend/pyproject.toml` - Added mf2py dependency

## Decisions Made
- Store only SHA-256 hashes of codes and tokens (plaintext never persisted)
- 60-second TTL for authorization codes per IndieAuth spec recommendation
- 1-hour access tokens, 30-day refresh tokens with rotation on every use
- SSRF protection on client_id fetching by rejecting loopback IPs
- Lazy import of mf2py only in fetch_client_info to avoid import overhead

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Service layer ready for Plan 02 (HTTP endpoints / routes)
- Models ready for migration execution on next Docker rebuild
- Schemas ready for endpoint response serialization

---
*Phase: 49-indieauth-provider*
*Completed: 2026-03-08*
