---
id: T04
parent: S03
milestone: M002
provides:
  - 15 unit tests covering complete auth token lifecycle (magic link, invitation, setup)
key_files:
  - backend/tests/test_auth_tokens.py
key_decisions:
  - Used time.sleep(1) for expiry tests because itsdangerous checks age > max_age (not >=), so max_age=0 with a freshly-created token passes unless at least 1 second has elapsed
patterns_established:
  - Group token tests by class (TestMagicLinkTokens, TestInvitationTokens, TestSetupTokens) matching the token type
  - Use tmp_path fixture for setup token file operations to avoid filesystem side effects
  - Cross-salt resistance test pattern — verify tokens signed with one salt cannot be verified with another
observability_surfaces:
  - none (pure test code)
duration: 8m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T04: Write auth token lifecycle tests

**Wrote 15 tests covering magic link, invitation, and setup token create/verify/expiry/tamper/delete lifecycle.**

## What Happened

Created `backend/tests/test_auth_tokens.py` with three test classes covering all public functions in `app.auth.tokens`:

- **TestMagicLinkTokens** (5 tests): create returns string, roundtrip verify recovers email, expired token returns None, tampered token returns None, wrong-salt (invitation salt) returns None.
- **TestInvitationTokens** (5 tests): create returns string, roundtrip verify recovers email+role dict, expired token returns None, tampered token returns None, wrong-salt (magic link salt) returns None.
- **TestSetupTokens** (5 tests): creates file and returns token, idempotent on second call, delete removes file, re-create after delete gives new token, delete on nonexistent file doesn't raise.

Initial run had 2 failures: `max_age_seconds=0` didn't trigger expiry because itsdangerous uses strict `age > max_age` comparison, and a freshly-created token has age=0 which is not > 0. Fixed by adding `time.sleep(1)` before the expired-token assertions to guarantee the token ages past the threshold.

## Verification

- `cd backend && .venv/bin/pytest tests/test_auth_tokens.py -v` — 15 passed in 2.03s
- `cd backend && .venv/bin/pytest tests/ -v` — 103 passed in 2.56s (all 5 modules)
- `cd backend && .venv/bin/pytest tests/ -v --tb=short 2>&1 | tail -5` — 103 passed, 0 failures
- Per-module counts: test_auth_tokens (15), test_iri_validation (31), test_rdf_serialization (15), test_sparql_client (23), test_sparql_utils (19)
- No Docker, triplestore, database, or running server required
- All slice-level verification checks pass (this is the final task in S03)

## Diagnostics

- Run `cd backend && .venv/bin/pytest tests/test_auth_tokens.py -v` — each test name describes the exact auth scenario
- Use `--tb=long` for full tracebacks on failure
- Test names follow pattern `test_<token_type>_<scenario>` for easy identification

## Deviations

- Plan recommended `max_age_seconds=0` without sleep for expiry testing. Added `time.sleep(1)` because itsdangerous requires `age > max_age` (strict greater-than), not `age >= max_age`. This adds ~2s to test runtime but is the correct and reliable approach.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_auth_tokens.py` — created with 15 tests covering magic link, invitation, and setup token lifecycle
