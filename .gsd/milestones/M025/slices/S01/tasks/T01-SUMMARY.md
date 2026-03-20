---
id: T01
parent: S01
milestone: M025
provides:
  - DEMO_MODE auth bypass returning synthetic guest user from all three auth dependencies
  - _demo_user() helper creating transient User with role="guest"
key_files:
  - backend/app/config.py
  - backend/app/auth/dependencies.py
  - backend/tests/test_demo_mode.py
key_decisions:
  - Restructured get_current_user to inline cookie extraction (replacing Depends(get_session_token)) so demo_mode check runs before any 401 can fire
patterns_established:
  - Demo-mode guard pattern: check settings.demo_mode as the first line in auth dependencies, return _demo_user() immediately
observability_surfaces:
  - logger.info("DEMO_MODE active — returning synthetic guest user") on first demo-mode auth call
  - Synthetic user role="guest" visible in any downstream permission check
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Implement DEMO_MODE auth bypass with unit tests

**Added demo_mode setting and synthetic guest user bypass to all three auth dependency functions, with 14 unit tests covering demo and non-demo paths**

## What Happened

Added `demo_mode: bool = False` to the `Settings` class in `config.py`, which reads from the `DEMO_MODE` env var via pydantic-settings.

Created `_demo_user()` in `dependencies.py` that returns a transient (non-persisted) `User` object with a deterministic nil UUID, `email="demo@sempkm.app"`, `display_name="Demo Visitor"`, and `role="guest"`. Logs once on first invocation.

Modified all three auth dependency functions:
- **`get_current_user`**: Restructured to inline cookie extraction (replacing the `Depends(get_session_token)` chain) so the `settings.demo_mode` check runs before any 401 can fire from a missing cookie. The old `get_session_token` function is preserved since it's still used by the logout endpoint.
- **`optional_current_user`**: Added `settings.demo_mode` check as first line — simpler since this function already handles missing cookies gracefully.
- **`get_current_user_or_api`**: Added `settings.demo_mode` check as first line before any cookie/bearer resolution.

Wrote 14 unit tests in `test_demo_mode.py` organized into 5 test classes covering: `_demo_user()` field correctness, demo-mode returns from all three auth functions, non-demo-mode behavior unchanged (401/None), settings default, and role security check.

## Verification

- `python -m pytest tests/test_demo_mode.py -v` — 14/14 passed
- `python -m pytest tests/test_auth_tokens.py -v` — 15/15 passed (no regressions)
- `python -m pytest tests/ -x -q` — 1304 passed, 1 pre-existing failure in `test_jira_sync_engine.py` (unrelated)
- `DEMO_MODE=false python -c "from app.auth.dependencies import get_current_user; print('non-demo auth unchanged')"` — module loads cleanly
- LSP diagnostics: clean on both modified files

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_demo_mode.py -v` | 0 | ✅ pass | 0.94s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_auth_tokens.py -v` | 0 | ✅ pass | 2.03s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/ -x -q` | 1 | ⚠️ pre-existing failure (test_jira_sync_engine, unrelated) | 9.78s |
| 4 | `cd backend && DEMO_MODE=false .venv/bin/python -c "from app.auth.dependencies import get_current_user; print('ok')"` | 0 | ✅ pass | <1s |

Slice-level verification (partial — T01 is not the final task):
- `cd backend && python -m pytest tests/test_demo_mode.py -v` — ✅ passes
- E2E test — ⬜ not yet created (T03)
- Diagnostic import check — ✅ passes

## Diagnostics

- **Runtime signal**: `DEMO_MODE active — returning synthetic guest user` log line appears once on first auth-resolved request when `DEMO_MODE=true`. Grep container logs for this string.
- **Inspect synthetic user**: Any endpoint returning user info will show `id=00000000-0000-0000-0000-000000000000`, `email=demo@sempkm.app`, `role=guest`.
- **Failure mode**: If bypass fails, workspace returns 302→`/login.html` (no session cookie → 401 → redirect). Visible in browser network tab or `curl -v`.

## Deviations

- Restructured `get_current_user` signature: replaced `token: str = Depends(get_session_token)` with `sempkm_session: str | None = Cookie(None)` and inline None-check. This is required because FastAPI evaluates `Depends()` arguments before the function body, so the 401 from `get_session_token` would fire before any demo_mode check could run. The `get_session_token` function is preserved since it's still used by the logout endpoint in `router.py`.

## Known Issues

- Pre-existing test failure in `test_jira_sync_engine.py::TestComputeStatus::test_no_errors_returns_success` — unrelated to this change.

## Files Created/Modified

- `backend/app/config.py` — Added `demo_mode: bool = False` setting
- `backend/app/auth/dependencies.py` — Added `_demo_user()` helper, `_DEMO_USER_UUID` constant, demo_mode checks in `get_current_user`, `optional_current_user`, `get_current_user_or_api`
- `backend/tests/test_demo_mode.py` — New: 14 unit tests for demo-mode auth bypass
- `.gsd/milestones/M025/slices/S01/S01-PLAN.md` — Added diagnostic verification step (pre-flight fix)
- `.gsd/milestones/M025/slices/S01/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
