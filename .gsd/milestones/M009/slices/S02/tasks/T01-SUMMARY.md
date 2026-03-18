---
id: T01
parent: S02
milestone: M009
provides:
  - JWT generation/validation utility for platform↔app authentication
  - get_secret() delegation to platform key resolver
  - Grace period support for token renewal flows
key_files:
  - backend/app/apps/tokens.py
  - backend/tests/test_app_tokens.py
key_decisions:
  - Grace period implemented as retry-with-manual-exp-check rather than leeway parameter, giving explicit control over acceptance window
patterns_established:
  - App token claims structure: {sub: "app:{app_id}", permissions: {…}, iat, exp}
  - Validation returns dict|None — no exceptions leak to callers
observability_surfaces:
  - DEBUG log on token generation (app_id + expiry timestamp)
  - DEBUG log on successful validation (sub claim)
  - WARNING log on invalid tokens (exception type, no token value)
  - DEBUG log on grace window accept/reject decisions
duration: 10m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: JWT token generation and validation

**Added HS256 JWT generation/validation utility with grace period support for app↔platform authentication**

## What Happened

Created `backend/app/apps/tokens.py` with three public functions:
- `generate_app_token()` — encodes HS256 JWT with `sub`, `permissions`, `iat`, `exp` claims
- `validate_app_token()` — decodes and validates, returns claims dict or None on any failure, supports grace period for token renewal
- `get_secret()` — delegates to `app.auth.tokens._get_secret_key()` to centralise secret resolution

Created `backend/tests/test_app_tokens.py` with 18 unit tests covering: valid round-trip, expired rejection, tampered payload, wrong secret, wrong algorithm, missing claims passthrough, garbage input, grace period (within/beyond/default-off), grace + tampered, grace + wrong secret, claims structure, and get_secret delegation.

## Verification

All 18 tests pass:

```
cd backend && .venv/bin/pytest tests/test_app_tokens.py -v
```

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/pytest tests/test_app_tokens.py -v` | 0 | ✅ pass | 0.04s |
| 2 | `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v` | — | ⬜ not yet (T02) | — |
| 3 | `cd backend && .venv/bin/pytest tests/test_app_proxy.py -v` | — | ⬜ not yet (T03) | — |
| 4 | `cd backend && .venv/bin/pytest tests/test_sdk_integration.py -v` | — | ⬜ not yet (T04) | — |

## Diagnostics

- Inspect token behavior: `grep "app token" <logfile>` covers generation, validation success, and rejection reasons
- All logging at DEBUG level except invalid tokens at WARNING
- Stateless utility — no persistent failure state; failures surface as None return values

## Deviations

None.

## Known Issues

- PyJWT 2.12 warns about HMAC key length < 32 bytes — only triggers with short test secrets, not production keys from `_get_secret_key()` (which generates 64-byte keys)

## Files Created/Modified

- `backend/app/apps/tokens.py` — new: JWT generation, validation with grace period, secret delegation
- `backend/tests/test_app_tokens.py` — new: 18 unit tests covering all must-have scenarios
