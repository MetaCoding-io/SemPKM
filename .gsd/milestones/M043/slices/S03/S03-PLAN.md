# S03: Auth Hardening — Magic Links, Token Scopes, Sessions

**Goal:** Make magic links single-use (F-012), implement fine-grained API token scopes (F-016), add session management features (F-013), restrict no-SMTP magic links to known users (F-018), stop logging tokens in plaintext (F-028).
**Demo:** Magic link replay returns 401. New API token creation UI shows scope checkboxes. Settings page has 'Log out all devices' button. Token created with sparql:read scope gets 403 on object mutation.

## Must-Haves

- UsedMagicToken SQLAlchemy model with token_hash + expires_at\n- verify_magic_link_token checks and records usage atomically\n- ApiToken model gains scope field (comma-separated string, default '*')\n- Scope enforcement in get_current_user_or_api checks token scope vs endpoint\n- Existing tokens migrated to scope='*' via Alembic\n- revoke_all_sessions wired to Settings endpoint\n- Session cap: create_session evicts oldest when count > 10\n- cleanup_expired_sessions scheduled daily\n- request_magic_link returns 404 for unknown emails when SMTP not configured\n- Magic link tokens no longer logged at INFO — only masked prefix

## Proof Level

- This slice proves: Unit tests for each auth change + integration test for scope enforcement

## Integration Closure

API token scope field is backward-compatible — existing tokens get wildcard scope via Alembic migration. Session management features use existing service methods.

## Verification

- Magic link replay attempts logged at WARNING. Scope enforcement denials logged with token ID and attempted endpoint. Session cleanup logged with count.

## Tasks

- [x] **T01: Single-use magic links + no-SMTP restriction + stop token logging** `est:3h`
  1. Create UsedMagicToken model in backend/app/auth/models.py:
   - token_hash: str (SHA-256 of the token, indexed)
   - used_at: datetime
   - expires_at: datetime

2. Modify verify_magic_link_token() in backend/app/auth/tokens.py:
   - After signature verification succeeds, compute SHA-256 hash of the token
   - Check UsedMagicToken table — if hash exists, reject as already-used
   - Insert hash + used_at + expires_at in same transaction
   - Return email only on success

3. Modify request_magic_link() in backend/app/auth/router.py:
   - When SMTP is not configured: check if email belongs to an existing user or has a pending invitation. Return generic 'magic link sent' message for unknown emails (don't reveal whether account exists). Don't generate token for unknown emails.
   - Stop logging the full token at INFO level (F-028). Log only first 8 chars: `token[:8]...`

4. Create Alembic migration for UsedMagicToken table.

5. Add periodic cleanup: delete expired rows from UsedMagicToken (expires_at < now) — can reuse the session cleanup schedule.

Unit tests: verify token replay returns 401, verify unknown email without SMTP returns generic response, verify token is not logged in full.
  - Files: `backend/app/auth/models.py`, `backend/app/auth/tokens.py`, `backend/app/auth/router.py`
  - Verify: cd backend && .venv/bin/python -m pytest tests/ -v -x -k 'magic or auth' --timeout=60

- [x] **T02: Fine-grained API token scopes with enforcement middleware** `est:4h`
  1. Add scope field to ApiToken model in backend/app/auth/models.py:
   - scope: str (comma-separated, default='*' for full access)
   - Define scope constants: 'sparql:read', 'sparql:write', 'objects:read', 'objects:write', 'models:admin', 'users:admin', 'commands:execute', 'copilot:use', '*'

2. Create Alembic migration: ADD COLUMN scope TEXT DEFAULT '*' to api_tokens table.

3. Update token creation endpoint in backend/app/auth/router.py:
   - Accept optional scope parameter in create token request body
   - Default to '*' if not specified
   - Validate scope values against allowed set

4. Add scope enforcement:
   - Create a scope_required() dependency factory in backend/app/auth/dependencies.py
   - For token-authenticated requests: check if any of the token's scopes match the required scope (wildcard '*' always matches)
   - For session-authenticated requests: bypass scope check (sessions inherit full role permissions)
   - Add scope_required() to key endpoints: SPARQL router (sparql:read), commands router (commands:execute), copilot router (copilot:use), objects mutation endpoints (objects:write), admin model endpoints (models:admin)

5. Update token creation UI endpoint to accept and display scope choices.

Unit tests: verify scoped token gets 403 on out-of-scope endpoint, verify wildcard token works everywhere, verify session auth bypasses scope check.
  - Files: `backend/app/auth/models.py`, `backend/app/auth/dependencies.py`, `backend/app/auth/router.py`, `backend/app/sparql/router.py`, `backend/app/api/router.py`, `backend/app/copilot/router.py`
  - Verify: cd backend && .venv/bin/python -m pytest tests/ -v -x -k 'token or scope or auth' --timeout=60

- [x] **T03: Session management: revoke-all, cap at 10, periodic cleanup, file permissions** `est:3h`
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
  - Files: `backend/app/auth/router.py`, `backend/app/auth/service.py`, `backend/app/main.py`, `backend/app/auth/tokens.py`
  - Verify: cd backend && .venv/bin/python -m pytest tests/ -v -x -k 'session or cleanup' --timeout=60

## Files Likely Touched

- backend/app/auth/models.py
- backend/app/auth/tokens.py
- backend/app/auth/router.py
- backend/app/auth/dependencies.py
- backend/app/sparql/router.py
- backend/app/api/router.py
- backend/app/copilot/router.py
- backend/app/auth/service.py
- backend/app/main.py
