---
id: T03
parent: S02
milestone: M045
provides: []
requires: []
affects: []
key_files: ["backend/app/main.py", "backend/app/apps/tokens.py", "backend/app/apps/manager.py", "backend/app/apps/router.py", "backend/tests/test_app_token_isolation.py"]
key_decisions: ["Per-app keys derived via HMAC-SHA256(platform_key, app_id) — deterministic, no extra storage, unique per app"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "12 unit tests pass: 3 for key derivation properties, 2 for cross-app token isolation, 4 parametrized for weak key rejection, 3 for allowed keys. All 5 modified files pass syntax check via ast.parse. T02 zip validator tests also pass (16/16) when invoked via venv python."
completed_at: 2026-03-29T00:06:41.896Z
blocker_discovered: false
---

# T03: Add weak SECRET_KEY startup rejection and per-app JWT key isolation via HMAC-SHA256 derivation

> Add weak SECRET_KEY startup rejection and per-app JWT key isolation via HMAC-SHA256 derivation

## What Happened
---
id: T03
parent: S02
milestone: M045
key_files:
  - backend/app/main.py
  - backend/app/apps/tokens.py
  - backend/app/apps/manager.py
  - backend/app/apps/router.py
  - backend/tests/test_app_token_isolation.py
key_decisions:
  - Per-app keys derived via HMAC-SHA256(platform_key, app_id) — deterministic, no extra storage, unique per app
duration: ""
verification_result: passed
completed_at: 2026-03-29T00:06:41.897Z
blocker_discovered: false
---

# T03: Add weak SECRET_KEY startup rejection and per-app JWT key isolation via HMAC-SHA256 derivation

**Add weak SECRET_KEY startup rejection and per-app JWT key isolation via HMAC-SHA256 derivation**

## What Happened

Implemented two security hardening features: (1) Weak key rejection — added _WEAK_KEYS set to main.py Security Startup Warnings section; server raises SystemExit(1) when secret_key matches a known weak value and demo_mode is False. (2) Per-app JWT key isolation — added get_app_secret(app_id) to tokens.py using HMAC-SHA256(platform_key, app_id), updated manager.py and router.py to derive per-app signing keys instead of using the platform-wide key directly. A compromised app token can no longer forge tokens for other apps.

## Verification

12 unit tests pass: 3 for key derivation properties, 2 for cross-app token isolation, 4 parametrized for weak key rejection, 3 for allowed keys. All 5 modified files pass syntax check via ast.parse. T02 zip validator tests also pass (16/16) when invoked via venv python.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_app_token_isolation.py -v` | 0 | ✅ pass | 100ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_zip_validator.py -v` | 0 | ✅ pass | 540ms |
| 3 | `ast.parse syntax check on 5 modified files` | 0 | ✅ pass | 50ms |


## Deviations

None.

## Known Issues

Slice-level verification command uses bare 'python' which doesn't exist on this system — must use '.venv/bin/python -m pytest' instead.

## Files Created/Modified

- `backend/app/main.py`
- `backend/app/apps/tokens.py`
- `backend/app/apps/manager.py`
- `backend/app/apps/router.py`
- `backend/tests/test_app_token_isolation.py`


## Deviations
None.

## Known Issues
Slice-level verification command uses bare 'python' which doesn't exist on this system — must use '.venv/bin/python -m pytest' instead.
