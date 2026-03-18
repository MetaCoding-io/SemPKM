---
estimated_steps: 5
estimated_files: 2
---

# T01: Build dual-auth FastAPI dependency

**Slice:** S01 — Dual-Auth, CORS, nginx fix, and Well-Known Endpoint
**Milestone:** M013

## Description

Create a `get_current_user_or_api` FastAPI dependency in `auth/dependencies.py` that resolves a User from either a session cookie OR a Bearer API token in the Authorization header. This is the foundation for all M013 endpoints — external clients send Bearer tokens, the htmx frontend sends cookies, and both need to work.

## Steps

1. Read `backend/app/auth/dependencies.py` to understand the existing `get_current_user` and `get_session_token` dependencies
2. Read `backend/app/auth/service.py` lines around `verify_api_token` to understand the async token verification API
3. Add a helper `_extract_bearer_token(authorization: str | None) -> str | None` that parses the Authorization header and returns the token if scheme is Bearer, None otherwise
4. Add `get_current_user_or_api(request: Request, sempkm_session: str | None = Cookie(None), authorization: str | None = Header(None), db: AsyncSession = Depends(get_db_session)) -> User` that:
   - First tries session cookie path (if `sempkm_session` is present, look up session in DB — same logic as `get_current_user`)
   - If no valid session, tries Bearer token path (extract token from `authorization` header, call `request.app.state.auth_service.verify_api_token(token)`)
   - If neither succeeds, raises HTTP 401
5. Verify `get_current_user` is unchanged — existing htmx routes still use it

## Must-Haves

- [ ] `get_current_user_or_api` accepts session cookie and returns User (backward compat with frontend)
- [ ] `get_current_user_or_api` accepts `Authorization: Bearer <token>` and returns User via AuthService
- [ ] Returns HTTP 401 with clear message when neither auth method succeeds
- [ ] Existing `get_current_user` dependency is untouched

## Verification

- Import and call `get_current_user_or_api` in test — mock request with cookie returns user, mock request with bearer returns user, mock request with neither raises 401
- `cd backend && python -m pytest tests/test_api_surface.py -v -k "dual_auth"`

## Inputs

- `backend/app/auth/dependencies.py` — existing session-only auth dependencies
- `backend/app/auth/service.py` — `AuthService.verify_api_token()` method

## Observability Impact

- **New signal:** `get_current_user_or_api` uses structured `logging.debug()` to record which auth path resolved (cookie vs bearer), visible in FastAPI debug logs
- **Failure state:** HTTP 401 with `detail` field distinguishing "Not authenticated" (no credentials) vs "Invalid or expired API token" (bad bearer) vs "Invalid or expired session" (bad cookie) — inspectable via `curl -v` or test assertions
- **Inspection:** `AuthService.verify_api_token` updates `ApiToken.last_used_at` on success — queryable in DB to confirm bearer auth is being exercised

## Expected Output

- `backend/app/auth/dependencies.py` — with new `get_current_user_or_api` dependency added
