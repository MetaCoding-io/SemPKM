---
estimated_steps: 5
estimated_files: 3
---

# T01: Create `require_role_or_api` factory and wire commands endpoint to dual-auth

**Slice:** S01 — Backend auth fix + extension scaffold with working capture
**Milestone:** M014

## Description

The `POST /api/commands` endpoint uses `require_role("owner", "member")` which internally chains to `get_current_user` — a cookie-only auth dependency. Bearer tokens sent via `Authorization` header are silently ignored, resulting in 401. This blocks the browser extension from creating objects.

Create a parallel `require_role_or_api(*roles)` factory in `dependencies.py` that chains to `get_current_user_or_api` (dual-auth, already exists and tested from M013) instead of `get_current_user`. Then update `commands/router.py` to use it. Leave all existing `require_role` usages unchanged to avoid breaking htmx routes.

This is a ~20-line backend change (D165) plus comprehensive unit tests.

## Steps

1. Open `backend/app/auth/dependencies.py`. Add a new factory function `require_role_or_api(*roles)` immediately after the existing `require_role(*roles)` function (around line 110). It should mirror `require_role` exactly but use `get_current_user_or_api` as its inner dependency instead of `get_current_user`:
   ```python
   def require_role_or_api(*roles: str):
       """Factory returning a dependency that checks the user's role.

       Like require_role, but accepts both session cookie and Bearer API
       token authentication via get_current_user_or_api.

       Usage for API endpoints that need Bearer token support:
           @router.post("/commands", dependencies=[Depends(require_role_or_api("owner", "member"))])
       """

       async def _check_role(
           current_user: User = Depends(get_current_user_or_api),
       ) -> User:
           if current_user.role not in roles:
               raise HTTPException(
                   status_code=status.HTTP_403_FORBIDDEN,
                   detail=f"Requires role: {', '.join(roles)}",
               )
           return current_user

       return _check_role
   ```

2. Open `backend/app/commands/router.py`. Change the import to include `require_role_or_api`:
   ```python
   from app.auth.dependencies import require_role_or_api
   ```
   Change the `execute_commands` endpoint's dependency from:
   ```python
   user: User = Depends(require_role("owner", "member")),
   ```
   to:
   ```python
   user: User = Depends(require_role_or_api("owner", "member")),
   ```
   Remove the old `require_role` import if it's no longer used in this file.

3. Create `backend/tests/test_commands_bearer_auth.py` with tests:
   - `test_require_role_or_api_accepts_bearer_token` — Verify the factory resolves a user from Bearer token
   - `test_require_role_or_api_accepts_cookie` — Verify cookie auth still works
   - `test_require_role_or_api_rejects_wrong_role` — Verify 403 for insufficient role
   - `test_require_role_or_api_rejects_no_credentials` — Verify 401 with no auth
   - `test_require_role_or_api_rejects_invalid_bearer` — Verify 401 with bad token
   - `test_commands_endpoint_accepts_bearer` — Integration test: POST /api/commands with Bearer token creates an object (mock EventStore/dispatch)
   - `test_commands_endpoint_rejects_guest_bearer` — Integration test: guest role gets 403
   
   Use the same test patterns from `test_api_surface.py` — in-memory SQLite, mock triplestore, AsyncClient with ASGI transport. Look at how `test_api_surface.py` sets up `db_engine`, `db_session`, `test_user`, `valid_session`, and `valid_api_token` fixtures. Reuse those patterns.

4. Run existing tests to verify no regression:
   ```bash
   cd backend && python -m pytest tests/test_api_surface.py -v
   ```

5. Run the new tests:
   ```bash
   cd backend && python -m pytest tests/test_commands_bearer_auth.py -v
   ```

## Must-Haves

- [ ] `require_role_or_api` factory exists in `dependencies.py` with identical signature to `require_role`
- [ ] `require_role_or_api` chains to `get_current_user_or_api` (not `get_current_user`)
- [ ] `POST /api/commands` uses `require_role_or_api("owner", "member")`
- [ ] Existing `require_role` function is unchanged (no modifications to its code)
- [ ] All other files importing `require_role` are unchanged
- [ ] Unit tests cover: bearer acceptance, cookie acceptance, wrong role rejection, no-credentials rejection, invalid bearer rejection, integration with commands endpoint

## Verification

- `cd backend && python -m pytest tests/test_commands_bearer_auth.py -v` — all tests pass
- `cd backend && python -m pytest tests/test_api_surface.py -v` — no regression in existing dual-auth tests
- `cd backend && python -m pytest tests/ -v --tb=short` — full test suite passes

## Inputs

- `backend/app/auth/dependencies.py` — Contains `require_role` (cookie-only factory) and `get_current_user_or_api` (dual-auth dependency). The new factory mirrors `require_role` but uses `get_current_user_or_api`.
- `backend/app/commands/router.py` — Line 86 has `user: User = Depends(require_role("owner", "member"))`. This is the single line to change.
- `backend/tests/test_api_surface.py` — Reference for test fixture patterns (in-memory SQLite, mock services, AsyncClient)

## Expected Output

- `backend/app/auth/dependencies.py` — New `require_role_or_api(*roles)` factory function (~15 lines)
- `backend/app/commands/router.py` — Import changed, dependency on line 86 updated
- `backend/tests/test_commands_bearer_auth.py` — 7+ tests covering the factory and commands endpoint Bearer auth
