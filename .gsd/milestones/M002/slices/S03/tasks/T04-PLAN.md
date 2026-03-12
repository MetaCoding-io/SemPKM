---
estimated_steps: 3
estimated_files: 1
---

# T04: Write auth token lifecycle tests

**Slice:** S03 — Backend Test Foundation
**Milestone:** M002

## Description

Write unit tests for the complete auth token lifecycle in `app.auth.tokens`: magic link tokens (create/verify/expiry/tamper), invitation tokens (create/verify/expiry/tamper with payload), and setup tokens (create/load/delete on disk). These are security-critical and currently untested. Tests must use the `reset_serializer` fixture from conftest to prevent `_serializer` singleton pollution between tests.

## Steps

1. Create `backend/tests/test_auth_tokens.py` with imports from `app.auth.tokens` for all public functions and `tokens` module reference for `_serializer` reset verification.
2. Write magic link token tests:
   - `create_magic_link_token()` returns a non-empty string.
   - `verify_magic_link_token()` roundtrip: create with email, verify recovers same email.
   - Expired token: create, verify with `max_age_seconds=0` returns `None`.
   - Tampered token: modify token string, verify returns `None`.
   - Wrong-salt resistance: create magic link token, try to verify as invitation token — returns `None`.
3. Write invitation token tests:
   - `create_invitation_token()` returns a non-empty string.
   - `verify_invitation_token()` roundtrip: create with email+role, verify recovers dict with matching `email` and `role`.
   - Expired token: create, verify with `max_age_seconds=0` returns `None`.
   - Tampered token: modify token string, verify returns `None`.
4. Write setup token tests (using `tmp_path` fixture):
   - `load_or_create_setup_token(path)` creates file at path and returns token string.
   - Second call to `load_or_create_setup_token(path)` returns the same token (idempotent).
   - `delete_setup_token(path)` removes the file.
   - After delete, `load_or_create_setup_token(path)` creates a new (different) token.
   - `delete_setup_token` on non-existent file does not raise.

## Must-Haves

- [ ] Magic link: create, roundtrip verify, expiry, tamper resistance
- [ ] Invitation: create, roundtrip verify with email+role payload, expiry, tamper resistance
- [ ] Setup token: create/load idempotency, delete, re-create after delete
- [ ] All tests use `reset_serializer` fixture (autouse from conftest) — no singleton pollution

## Verification

- `cd backend && .venv/bin/pytest tests/test_auth_tokens.py -v` — all pass
- At least 12 tests covering all three token types
- Run full suite: `cd backend && .venv/bin/pytest tests/ -v` — all tests across all 5 modules pass

## Observability Impact

- Signals added/changed: None (pure test code)
- How a future agent inspects this: test names describe the exact auth scenario (e.g., `test_magic_link_expired_token_returns_none`)
- Failure state exposed: assertion failures show token values and expected outcomes

## Inputs

- `backend/app/auth/tokens.py` — all public functions: `create_magic_link_token`, `verify_magic_link_token`, `create_invitation_token`, `verify_invitation_token`, `load_or_create_setup_token`, `delete_setup_token`
- `backend/tests/conftest.py` — from T01, `reset_serializer` fixture and `SECRET_KEY` env var isolation
- Research notes — `max_age_seconds=0` recommended for expiry testing (no `time.sleep`)

## Expected Output

- `backend/tests/test_auth_tokens.py` — created with 12+ tests covering full token lifecycle
- Full test suite (`cd backend && .venv/bin/pytest tests/ -v`) passes with 25+ total tests across all 5 modules
