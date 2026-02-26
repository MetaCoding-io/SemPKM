---
phase: 19-bug-fixes-and-e2e-test-hardening
plan: "01"
subsystem: api
tags: [fastapi, eventstore, dependency-injection, cors, security, sparql, iri-validation]

# Dependency graph
requires: []
provides:
  - EventStore injected via FastAPI DI in all 4 write handlers in browser/router.py
  - Label cache invalidated after every write (save body, create object, patch object, undo)
  - UTC timestamps for dcterms:modified in both browser/router.py timestamp sites
  - CORS config driven by CORS_ORIGINS env var (no wildcard + credentials bug)
  - COOKIE_SECURE env var controls session cookie secure flag (default True)
  - /sparql and /commands debug pages require owner role
  - IRI validation at all 6 SPARQL interpolation points in browser/router.py
affects: [19-02, 19-03, future-backend-work]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - get_event_store dependency function follows existing get_label_service/get_triplestore_client pattern
    - IRI validation via urlparse before SPARQL f-string interpolation
    - Conditional CORS: specific origins with credentials OR wildcard without credentials

key-files:
  created: []
  modified:
    - backend/app/dependencies.py
    - backend/app/browser/router.py
    - backend/app/config.py
    - backend/app/main.py
    - backend/app/auth/router.py
    - backend/app/debug/router.py

key-decisions:
  - "Conditional CORS: empty CORS_ORIGINS means wildcard without credentials; non-empty means specific origins with credentials"
  - "COOKIE_SECURE defaults True for production safety; set COOKIE_SECURE=false in local dev"
  - "IRI validation uses urlparse scheme+netloc check; urn: IRIs will not pass (scheme present, netloc absent) — acceptable since all object IRIs are https://"
  - "EventStore commit result stored in event_result variable in undo_event to enable label invalidation"

patterns-established:
  - "get_event_store: async def returning request.app.state.event_store, matches other dependency functions"
  - "_validate_iri: urlparse-based guard before SPARQL interpolation, raises HTTPException(400)"

requirements-completed: [BUG-01, BUG-02, BUG-03, BUG-04]

# Metrics
duration: 13min
completed: 2026-02-26
---

# Phase 19 Plan 01: Backend Bug Fixes Summary

**EventStore DI with label cache invalidation, UTC timestamps, CORS env var, cookie secure flag, debug endpoint owner guard, and IRI injection protection across browser/router.py**

## Performance

- **Duration:** 13 min
- **Started:** 2026-02-26T00:52:50Z
- **Completed:** 2026-02-26T01:05:50Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Replaced 4 ad-hoc `EventStore(client)` constructions with DI (`Depends(get_event_store)`) across all write handlers
- Added `label_service.invalidate(event_result.affected_iris)` after every `event_store.commit()` — stale labels no longer persist after rename
- Fixed `datetime.now()` to `datetime.now(timezone.utc)` at both timestamp sites in browser/router.py
- Fixed CORS wildcard + credentials=True violation; now controlled by `CORS_ORIGINS` env var
- `COOKIE_SECURE` env var controls session cookie secure flag (defaults True)
- `/sparql` and `/commands` debug routes now require owner role via `require_role("owner")`
- Added `_validate_iri` helper applied at 6 IRI decode/use sites preventing SPARQL injection

## Task Commits

Each task was committed atomically:

1. **Task 1: EventStore DI + label cache invalidation + UTC datetime + IRI validation** - `d0d41e0` (fix)
2. **Task 2: CORS env var, cookie secure, debug endpoint owner guard** - `8cd75b5` (fix)

## Files Created/Modified
- `backend/app/dependencies.py` - Added `get_event_store` dependency function following existing pattern
- `backend/app/browser/router.py` - 4 write handlers use DI EventStore; label invalidation after each commit; UTC datetime; `_validate_iri` at 6 sites; HTTPException import
- `backend/app/config.py` - Added `cors_origins: str = ""` and `cookie_secure: bool = True` settings fields
- `backend/app/main.py` - Replaced static wildcard CORS with conditional based on `cors_origins_list`
- `backend/app/auth/router.py` - `secure=settings.cookie_secure` (was hardcoded False)
- `backend/app/debug/router.py` - `require_role("owner")` guards on both debug endpoints (was `get_current_user`)

## Decisions Made
- Conditional CORS: empty `CORS_ORIGINS` means wildcard without credentials; non-empty means specific origins with credentials. This is the correct pattern per CORS spec.
- `COOKIE_SECURE` defaults `True` for production safety. Local dev requires setting `COOKIE_SECURE=false` explicitly.
- IRI validation uses `urlparse(iri).scheme and urlparse(iri).netloc` — rejects `urn:` IRIs (no netloc). Acceptable since all object IRIs are `https://`-form. Event IRIs in `undo_event` are decoded separately via `_unquote` with no SPARQL interpolation, so no guard needed there.
- `undo_event` previously discarded the commit result — now stored as `event_result` to enable `label_service.invalidate(event_result.affected_iris)`.

## Deviations from Plan

None - plan executed exactly as written. All 6 IRI decode sites were found and patched as specified.

## Issues Encountered

None - all changes were straightforward surgical edits with no unexpected complications.

## User Setup Required

New environment variables available but not required:
- `CORS_ORIGINS`: comma-separated allowed origins (empty = wildcard without credentials)
- `COOKIE_SECURE`: set to `false` for local HTTP development (default `true`)

No mandatory configuration changes — existing deployments work unchanged.

## Next Phase Readiness
- All backend security/correctness bugs fixed; 19-02 (frontend fixes) can proceed independently
- Label cache will now be accurate after every write operation
- Debug endpoints properly guarded against non-owner access

---
*Phase: 19-bug-fixes-and-e2e-test-hardening*
*Completed: 2026-02-26*
