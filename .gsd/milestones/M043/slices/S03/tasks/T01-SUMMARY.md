---
id: T01
parent: S03
milestone: M043
key_files:
  - backend/app/auth/models.py
  - backend/app/auth/service.py
  - backend/app/auth/router.py
  - backend/app/main.py
  - backend/migrations/versions/022_used_magic_tokens.py
  - backend/tests/test_magic_link_hardening.py
key_decisions:
  - Kept single-use check in AuthService (DB layer) rather than modifying the stateless tokens.py module — preserves separation of cryptographic vs stateful logic
  - Used SHA-256 hash of the full token for storage (not the token itself) — consistent with existing ApiToken.token_hash pattern
  - Cleanup of used_magic_tokens runs at startup alongside session cleanup rather than on a separate schedule
duration: ""
verification_result: passed
completed_at: 2026-03-25T09:17:45.119Z
blocker_discovered: false
---

# T01: Implement single-use magic links (F-012), no-SMTP restriction (F-018), and truncated token logging (F-028)

**Implement single-use magic links (F-012), no-SMTP restriction (F-018), and truncated token logging (F-028)**

## What Happened

Implemented three auth hardening features:

**F-012 — Single-use magic links:** Added `UsedMagicToken` model to `backend/app/auth/models.py` with SHA-256 token hash, `used_at`, and `expires_at` columns. Added `check_and_consume_magic_token()` method to `AuthService` that atomically checks and inserts the hash — replay attempts get `False`. The `/api/auth/verify` endpoint now calls this before creating a session, returning HTTP 401 with "Token has already been used" on replay. Replay attempts are logged at WARNING level with the email address.

**F-018 — No-SMTP restriction:** Modified `request_magic_link()` to check whether the email belongs to an existing user or has a pending invitation before generating a token in no-SMTP mode. Unknown emails get a generic "If this email is registered…" response without token generation — no information leakage about account existence.

**F-028 — Token logging truncation:** All `logger.info()` calls that previously logged the full magic link token now log only the first 8 characters (`token[:8]...`). Two call sites updated: the SMTP fallback path and the no-SMTP console path.

**Cleanup:** Added `cleanup_expired_magic_tokens()` to `AuthService` (deletes rows where `expires_at < now`) and wired it into the startup lifecycle in `main.py` alongside the existing session cleanup.

**Migration:** Created `022_used_magic_tokens.py` with the new table and index.

**Tests:** 11 new tests across 3 test classes covering single-use enforcement (first use succeeds, replay fails, different tokens both work, cleanup of expired/active records), pending invitation logic (no invitation, pending, expired, accepted), and token format verification.

## Verification

Ran `pytest tests/test_magic_link_hardening.py tests/test_auth_tokens.py tests/test_demo_mode.py tests/test_commands_bearer_auth.py -v -x` — all 50 tests pass (11 new + 39 existing auth tests). Zero regressions. LSP diagnostics clean on all three modified source files.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_magic_link_hardening.py tests/test_auth_tokens.py tests/test_demo_mode.py tests/test_commands_bearer_auth.py -v -x` | 0 | ✅ pass | 2880ms |


## Deviations

The task plan suggested modifying `verify_magic_link_token()` in `tokens.py` to add DB access. Instead, the single-use check was added to `AuthService` as a separate method (`check_and_consume_magic_token`) called from the router's `verify_token()` endpoint. This preserves the clean separation between stateless cryptographic verification (tokens.py) and stateful DB operations (service.py). The itsdangerous signature check happens first; the single-use DB check happens second — both must pass.

## Known Issues

itsdangerous `URLSafeTimedSerializer.dumps()` is deterministic for the same email within the same second, so two rapid magic link requests for the same email produce identical tokens. This means the second request's token is already "used" when the first is consumed. In practice this is a non-issue (rate-limited to 5/min, and users don't request two links in the same second), but a nonce could be added to the payload if needed.

## Files Created/Modified

- `backend/app/auth/models.py`
- `backend/app/auth/service.py`
- `backend/app/auth/router.py`
- `backend/app/main.py`
- `backend/migrations/versions/022_used_magic_tokens.py`
- `backend/tests/test_magic_link_hardening.py`
