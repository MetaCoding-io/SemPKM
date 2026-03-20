---
estimated_steps: 5
estimated_files: 3
---

# T01: Implement DEMO_MODE auth bypass with unit tests

**Slice:** S01 — Read-only enforcement + DEMO_MODE anonymous access
**Milestone:** M025

## Description

Add a `DEMO_MODE` environment variable that, when set to `true`, makes all three auth dependency functions (`get_current_user`, `optional_current_user`, `get_current_user_or_api`) return a synthetic read-only guest user without any database lookup or session/cookie check. This is the foundation for anonymous demo access — per decision D244.

The synthetic user must be a real `User` object (not a mock) so that all downstream code that accesses `user.id`, `user.email`, `user.role`, `user.display_name` works without changes. The role must be `"guest"` — this already restricts SPARQL access and other role-gated endpoints.

**Skill note:** Load the `test` skill if needed for pytest patterns.

## Steps

1. **Add `demo_mode` setting to `backend/app/config.py`:**
   - Add `demo_mode: bool = False` field to the `Settings` class
   - This reads from `DEMO_MODE` env var (pydantic-settings auto-converts)

2. **Create a module-level synthetic demo user in `backend/app/auth/dependencies.py`:**
   - Import `uuid` (already imported via `User` model)
   - Create a `_demo_user()` function that returns a `User` object with:
     - `id = uuid.UUID("00000000-0000-0000-0000-000000000000")` (fixed, deterministic)
     - `email = "demo@sempkm.app"`
     - `display_name = "Demo Visitor"`
     - `role = "guest"`
   - The User object is an SQLAlchemy model, so create it with `User(id=..., email=..., display_name=..., role="guest")` — do NOT call `db.add()` or persist it. It's a transient object.
   - Log once on first call: `logger.info("DEMO_MODE active — returning synthetic guest user")`

3. **Add demo_mode early return to all three auth dependencies:**
   - `get_current_user`: At the very start, before `token = Depends(get_session_token)`, check `if settings.demo_mode: return _demo_user()`. **Important:** FastAPI evaluates `Depends()` arguments before the function body runs, so you must restructure `get_current_user` to use `Request` parameter and manually extract the cookie, OR create a new parallel dependency that checks demo_mode first. The cleanest approach: add a wrapper that checks `settings.demo_mode` first and only falls through to the real auth logic if not in demo mode. Specifically:
     - Keep the existing `get_current_user` as `_get_current_user_real` (rename it)
     - Create new `get_current_user` that checks `settings.demo_mode` first, returns `_demo_user()` if true, otherwise delegates to `_get_current_user_real`
     - BUT: the Depends() chain complicates this. Simpler approach: add the check inside the existing function body — `if settings.demo_mode: return _demo_user()` as the first line. The `token = Depends(get_session_token)` will still execute, but in demo mode there's no cookie, so it would raise 401 BEFORE our check runs.
     - **Correct approach:** Override `get_session_token` to return a dummy value in demo mode. Or better: create an `async def get_current_user(request: Request, ...)` that checks demo_mode FIRST. Use a single dependency function that handles both paths:
       ```python
       async def get_current_user(
           request: Request,
           sempkm_session: str | None = Cookie(None),
           db: AsyncSession = Depends(get_db_session),
       ) -> User:
           if settings.demo_mode:
               return _demo_user()
           # ... existing session lookup logic (moved from old get_current_user)
       ```
     - This replaces the `token: str = Depends(get_session_token)` dependency chain with inline cookie extraction, which avoids the 401 from `get_session_token` in demo mode.
   - `optional_current_user`: Add `if settings.demo_mode: return _demo_user()` as first line (this is simpler — it already handles None cookies)
   - `get_current_user_or_api`: Add `if settings.demo_mode: return _demo_user()` as first line

4. **Write unit tests in `backend/tests/test_demo_mode.py`:**
   - Test that `_demo_user()` returns a User with correct fields (id, email, display_name, role="guest")
   - Test that `get_current_user` returns synthetic user when `settings.demo_mode = True` (mock settings)
   - Test that `get_current_user` raises 401 when `settings.demo_mode = False` and no cookie (existing behavior)
   - Test that `optional_current_user` returns synthetic user when demo mode
   - Test that `get_current_user_or_api` returns synthetic user when demo mode
   - Test that the synthetic user's role is "guest" (important for downstream permission checks)
   - Use `monkeypatch` to set `settings.demo_mode = True/False` for each test
   - Pattern: look at `backend/tests/test_auth_tokens.py` or `backend/tests/conftest.py` for existing test patterns

5. **Run tests and verify no regressions:**
   - `cd backend && python -m pytest tests/test_demo_mode.py -v`
   - `cd backend && python -m pytest tests/test_auth_tokens.py -v` (ensure existing auth tests still pass)

## Must-Haves

- [ ] `demo_mode: bool = False` in Settings class
- [ ] `_demo_user()` returns transient User with role="guest", fixed UUID, email="demo@sempkm.app"
- [ ] `get_current_user` returns synthetic user when DEMO_MODE=true WITHOUT triggering 401 from missing cookie
- [ ] `optional_current_user` returns synthetic user when DEMO_MODE=true
- [ ] `get_current_user_or_api` returns synthetic user when DEMO_MODE=true
- [ ] Default behavior (DEMO_MODE unset/false) is completely unchanged
- [ ] Unit tests cover all demo-mode paths and non-demo-mode is unaffected

## Verification

- `cd backend && python -m pytest tests/test_demo_mode.py -v` — all tests pass
- `cd backend && python -m pytest tests/ -x --timeout=30` — no regressions in existing tests (spot-check)

## Inputs

- `backend/app/config.py` — Settings class (add demo_mode field)
- `backend/app/auth/dependencies.py` — Three auth dependency functions to modify
- `backend/app/auth/models.py` — User model definition (for synthetic user construction)
- Decision D244 — specifies the approach (synthetic guest user with role: "guest")

## Observability Impact

- **New log signal:** `logger.info("DEMO_MODE active — returning synthetic guest user")` emitted on first demo-mode auth resolution in `dependencies.py`. Appears once in container logs on first request.
- **Inspectable state:** `settings.demo_mode` is readable via Python shell or debugger. The synthetic user's `role="guest"` is visible in any endpoint that returns user info.
- **Failure visibility:** If the DEMO_MODE bypass is misconfigured, requests without a session cookie will receive HTTP 401 (visible in browser network tab or curl). If the synthetic user has incorrect fields, downstream permission checks raise 403 with a role-mismatch detail message.
- **Non-demo-mode unchanged:** When `DEMO_MODE` is unset or `false`, the three auth functions behave identically to before this change — verifiable by running existing auth tests.

## Expected Output

- `backend/app/config.py` — Updated with `demo_mode: bool = False`
- `backend/app/auth/dependencies.py` — Updated with demo_mode checks in all three auth functions + `_demo_user()` helper
- `backend/tests/test_demo_mode.py` — New test file with 6-8 unit tests
