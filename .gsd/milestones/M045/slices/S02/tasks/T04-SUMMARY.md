---
id: T04
parent: S02
milestone: M045
provides: []
requires: []
affects: []
key_files: ["Caddyfile.cloud"]
key_decisions: []
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran grep checks confirming no CDN domains in CSP and HSTS header present. Ran test_app_token_isolation.py with correct venv Python — 12/12 passed. All 7 slice-level verification items confirmed passing."
completed_at: 2026-03-29T00:08:05.705Z
blocker_discovered: false
---

# T04: Removed 3 stale CDN domains from Caddyfile.cloud CSP and added HSTS header with 2-year max-age

> Removed 3 stale CDN domains from Caddyfile.cloud CSP and added HSTS header with 2-year max-age

## What Happened
---
id: T04
parent: S02
milestone: M045
key_files:
  - Caddyfile.cloud
key_decisions:
  - (none)
duration: ""
verification_result: passed
completed_at: 2026-03-29T00:08:05.705Z
blocker_discovered: false
---

# T04: Removed 3 stale CDN domains from Caddyfile.cloud CSP and added HSTS header with 2-year max-age

**Removed 3 stale CDN domains from Caddyfile.cloud CSP and added HSTS header with 2-year max-age**

## What Happened

Edited the Caddyfile.cloud header block to remove https://unpkg.com, https://cdn.jsdelivr.net, and https://cdnjs.cloudflare.com from both script-src and style-src CSP directives. Added Strict-Transport-Security header with max-age=63072000, includeSubDomains, and preload. Confirmed the slice-level test_app_token_isolation.py verification failure was a PATH issue (bare 'python' not found), not a test failure — all 12 tests pass with the venv interpreter.

## Verification

Ran grep checks confirming no CDN domains in CSP and HSTS header present. Ran test_app_token_isolation.py with correct venv Python — 12/12 passed. All 7 slice-level verification items confirmed passing.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `! grep -q 'unpkg.com|cdn.jsdelivr.net|cdnjs.cloudflare.com' Caddyfile.cloud && grep -q 'Strict-Transport-Security' Caddyfile.cloud` | 0 | ✅ pass | 50ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_app_token_isolation.py -v` | 0 | ✅ pass | 80ms |


## Deviations

None.

## Known Issues

Slice-level verification command uses bare 'python' which doesn't exist — should use 'cd backend && .venv/bin/python -m pytest'.

## Files Created/Modified

- `Caddyfile.cloud`


## Deviations
None.

## Known Issues
Slice-level verification command uses bare 'python' which doesn't exist — should use 'cd backend && .venv/bin/python -m pytest'.
