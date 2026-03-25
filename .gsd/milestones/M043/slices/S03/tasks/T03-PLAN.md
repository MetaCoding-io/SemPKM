---
estimated_steps: 17
estimated_files: 4
skills_used: []
---

# T03: Session management: revoke-all, cap at 10, periodic cleanup, file permissions

1. Wire revoke_all_sessions to a Settings endpoint:
   - Add POST /api/auth/sessions/revoke-all endpoint in backend/app/auth/router.py
   - Calls existing revoke_all_sessions(user_id) method
   - After revoking, create a new session for the current user (so they stay logged in)
   - Return count of revoked sessions

2. Add session cap in create_session():
   - Before creating a new session, count active sessions for the user
   - If count >= 10, delete the oldest session(s) to make room
   - Use a single query: DELETE FROM user_sessions WHERE user_id=? AND token NOT IN (SELECT token FROM user_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 9)

3. Schedule periodic session cleanup:
   - Add cleanup_expired_sessions() call to a BackgroundTasks in the lifespan function, running daily
   - Also clean up expired UsedMagicToken rows in the same schedule
   - Use asyncio.create_task with a simple sleep loop in the lifespan

4. Restrict secret key file permissions (F-038):
   - After writing data/.secret-key, call os.chmod(path, 0o600)
   - Same for data/.setup-token

Unit tests: verify revoke-all endpoint returns count, verify session cap evicts oldest, verify cleanup removes expired sessions.

## Inputs

- `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md`

## Expected Output

- `backend/app/auth/router.py`
- `backend/app/auth/service.py`
- `backend/app/main.py`
- `backend/app/auth/tokens.py`

## Verification

cd backend && .venv/bin/python -m pytest tests/ -v -x -k 'session or cleanup' --timeout=60
