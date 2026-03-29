---
id: T01
parent: S01
milestone: M046
provides: []
requires: []
affects: []
key_files: ["e2e/fixtures/auth.ts"]
key_decisions: ["Used example.com (RFC 2606 reserved) instead of test.local for member email — EmailStr accepts it", "Module-level token cache with /api/auth/me validation before reuse"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran all 4 existing test files (admin-access-control, member-permissions, dark-mode, debug-pages) plus the non-existent session-management path. 15 tests passed in 12.7s, 0 failures. All 11 previously-failing member-dependent tests now pass."
completed_at: 2026-03-29T01:29:22.420Z
blocker_discovered: false
---

# T01: Fix MEMBER_EMAIL domain from test.local to example.com and add module-level session token caching to E2E auth fixture

> Fix MEMBER_EMAIL domain from test.local to example.com and add module-level session token caching to E2E auth fixture

## What Happened
---
id: T01
parent: S01
milestone: M046
key_files:
  - e2e/fixtures/auth.ts
key_decisions:
  - Used example.com (RFC 2606 reserved) instead of test.local for member email — EmailStr accepts it
  - Module-level token cache with /api/auth/me validation before reuse
duration: ""
verification_result: passed
completed_at: 2026-03-29T01:29:22.420Z
blocker_discovered: false
---

# T01: Fix MEMBER_EMAIL domain from test.local to example.com and add module-level session token caching to E2E auth fixture

**Fix MEMBER_EMAIL domain from test.local to example.com and add module-level session token caching to E2E auth fixture**

## What Happened

Changed MEMBER_EMAIL from 'member@test.local' to 'member@example.com' — the .local TLD was rejected by Pydantic EmailStr on the /api/auth/invite endpoint, causing silent 422 that prevented member user creation. Added module-level _cachedOwnerToken and _cachedMemberToken variables with isTokenValid() helper that checks /api/auth/me before reuse. Improved invite error handling to throw with status code and body on non-2xx/non-409 responses.

## Verification

Ran all 4 existing test files (admin-access-control, member-permissions, dark-mode, debug-pages) plus the non-existent session-management path. 15 tests passed in 12.7s, 0 failures. All 11 previously-failing member-dependent tests now pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx playwright test tests/05-admin/admin-access-control.spec.ts tests/07-multi-user/member-permissions.spec.ts tests/06-settings/dark-mode.spec.ts tests/05-admin/debug-pages.spec.ts tests/04-session/session-management.spec.ts --project=chromium --reporter=list` | 0 | ✅ pass | 13900ms |


## Deviations

tests/04-session/session-management.spec.ts does not exist — Playwright skips non-existent paths gracefully. 15 tests across 4 existing spec files all pass.

## Known Issues

None.

## Files Created/Modified

- `e2e/fixtures/auth.ts`


## Deviations
tests/04-session/session-management.spec.ts does not exist — Playwright skips non-existent paths gracefully. 15 tests across 4 existing spec files all pass.

## Known Issues
None.
