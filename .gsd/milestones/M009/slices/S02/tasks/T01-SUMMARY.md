---
id: T01
parent: S02
milestone: M009
provides:
  - JWT token generation/validation utility for platform↔app auth
key_files:
  - backend/app/apps/tokens.py
  - backend/tests/test_app_tokens.py
key_decisions:
  - Grace period uses two-pass decode — normal first, then verify_exp=False with manual check
  - get_secret() wraps auth._get_secret_key() to centralize import path for app-layer code
patterns_established:
  - App tokens use "app:{app_id}" sub claim format
  - Validator returns dict|None — no exceptions leak to callers
  - Claim enforcement (required fields) deferred to SDK, not validator
observability_surfaces:
  - DEBUG logs on token generation (app_id + expiry), validation success (sub), grace acceptance/rejection
  - WARNING logs on invalid tokens (exception type, no token value)
duration: 15m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: JWT token generation and validation

**Created app JWT utility with generate, validate, and grace-period support — 17 tests passing.**

## What Happened

Built `backend/app/apps/tokens.py` with three public functions:
- `generate_app_token()` — HS256 JWT with `sub`, `permissions`, `iat`, `exp` claims
- `validate_app_token()` — decode with grace period support; returns claims dict or None
- `get_secret()` — delegates to `app.auth.tokens._get_secret_key()`

The grace period implementation uses a two-pass approach: first normal decode catches `ExpiredSignatureError`, then a second decode with `verify_exp=False` checks if `exp + grace_seconds >= now`. This avoids clock skew issues while keeping the normal path fast.

Test suite covers: valid token, expired, wrong secret, tampered, wrong algorithm, missing claims, garbage input, grace-within, grace-beyond, and `get_secret()` delegation.

## Verification

```
cd backend && .venv/bin/pytest tests/test_app_tokens.py -v
17 passed in 0.10s
```

Slice-level verification status:
- ✅ `tests/test_app_tokens.py` — 17/17 pass
- ⬜ `tests/test_sdk_app.py` — not yet created (T02)
- ⬜ `tests/test_app_proxy.py` — not yet created (T03)
- ⬜ `tests/test_sdk_integration.py` — not yet created (T04)

## Diagnostics

- Token generation/validation logs at DEBUG level: `grep "app token" <logfile>`
- Invalid tokens logged at WARNING with exception class name, never the token value
- Stateless utility — no persistent state to inspect; failures are None returns

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/tokens.py` — JWT generation, validation, and secret delegation utility
- `backend/tests/test_app_tokens.py` — 17 unit tests covering all specified scenarios
- `.gsd/milestones/M009/slices/S02/tasks/T01-PLAN.md` — added Observability Impact section
