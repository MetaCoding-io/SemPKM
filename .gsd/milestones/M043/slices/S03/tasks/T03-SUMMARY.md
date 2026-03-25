---
id: T03
parent: S03
milestone: M043
key_files:
  - backend/app/auth/service.py
  - backend/app/auth/router.py
  - backend/app/auth/tokens.py
  - backend/app/auth/schemas.py
  - backend/app/main.py
  - backend/tests/test_session_management.py
key_decisions:
  - Session cap uses subquery DELETE to keep newest N-1 sessions ordered by created_at DESC — single query, no N+1
  - Periodic cleanup uses asyncio.create_task with sleep loop rather than APScheduler or BackgroundTasks — zero new dependencies, proper cancellation on shutdown
  - Revoke-all creates a fresh session after revoking so the caller stays authenticated — no forced re-login
duration: ""
verification_result: passed
completed_at: 2026-03-25T14:43:16.727Z
blocker_discovered: false
---

# T03: Add session management: revoke-all endpoint, per-user session cap at 10, periodic daily cleanup, and 0o600 file permissions on secret key and setup token

**Add session management: revoke-all endpoint, per-user session cap at 10, periodic daily cleanup, and 0o600 file permissions on secret key and setup token**

## What Happened

Implemented all four session management features from the task plan:

**1. Revoke-all sessions endpoint (POST /api/auth/sessions/revoke-all):** Added to `router.py` with `RevokeAllSessionsResponse` schema. Calls existing `revoke_all_sessions(user_id)`, then creates a fresh session so the caller stays logged in via a new cookie. Returns the count of revoked sessions. Logs the action at INFO level with user ID and count.

**2. Session cap in create_session():** Modified `create_session()` in `service.py` to accept a `max_sessions` parameter (default 10). Before inserting a new session, counts active sessions for the user. If count >= max, deletes all sessions except the newest (max-1) using a subquery-based DELETE. Logs eviction count at INFO level. The cap keeps the most recent sessions by `created_at DESC` ordering.

**3. Periodic session cleanup:** Added an `asyncio.create_task` background loop in `main.py`'s lifespan that runs `cleanup_expired_sessions()` and `cleanup_expired_magic_tokens()` every 24 hours. The task is properly cancelled during shutdown. Startup-time cleanup was already wired in T01 — this adds the recurring schedule.

**4. File permissions (F-038):** Added `os.chmod(path, 0o600)` after writing both `data/.secret-key` and `data/.setup-token` in `tokens.py`. Existing files that are read (not written) are unaffected.

**Tests:** 14 new tests across 4 classes: TestRevokeAllSessions (3 tests: count, zero, user isolation), TestSessionCap (4 tests: enforces limit, evicts oldest by timestamp, below-cap no eviction, custom cap), TestSessionCleanup (4 tests: expired sessions, active sessions, expired magic tokens, active magic tokens), TestFilePermissions (3 tests: secret key permissions, setup token permissions, existing key not overwritten).

## Verification

Ran `cd backend && .venv/bin/python -m pytest tests/test_session_management.py -v -x` — all 14 new tests pass. Ran full auth test suite (6 test files, 90 tests total) — all pass with zero regressions. LSP diagnostics clean on tokens.py; service.py and router.py show only pre-existing Pyright issues (SQLAlchemy rowcount typing, scope attribute from T02). Verified slice-level logging requirements: magic link replay logged at WARNING, session cleanup logged with count, periodic cleanup logs at INFO.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_session_management.py -v -x` | 0 | ✅ pass | 440ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_session_management.py tests/test_magic_link_hardening.py tests/test_token_scopes.py tests/test_auth_tokens.py tests/test_demo_mode.py tests/test_commands_bearer_auth.py -v` | 0 | ✅ pass | 3730ms |


## Deviations

The session cap test was adjusted to check counts rather than specific token eviction, because sessions created in rapid succession share the same `created_at` timestamp — SQLite's ordering is non-deterministic for identical timestamps. Added a separate test with manually-set timestamps to verify oldest-eviction behavior deterministically.

## Known Issues

None.

## Files Created/Modified

- `backend/app/auth/service.py`
- `backend/app/auth/router.py`
- `backend/app/auth/tokens.py`
- `backend/app/auth/schemas.py`
- `backend/app/main.py`
- `backend/tests/test_session_management.py`
