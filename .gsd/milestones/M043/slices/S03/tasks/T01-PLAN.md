---
estimated_steps: 15
estimated_files: 3
skills_used: []
---

# T01: Single-use magic links + no-SMTP restriction + stop token logging

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

## Inputs

- `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md`

## Expected Output

- `backend/app/auth/models.py`
- `backend/app/auth/tokens.py`
- `backend/app/auth/router.py`
- `backend/migrations/versions/xxx_add_used_magic_tokens.py`

## Verification

cd backend && .venv/bin/python -m pytest tests/ -v -x -k 'magic or auth' --timeout=60
