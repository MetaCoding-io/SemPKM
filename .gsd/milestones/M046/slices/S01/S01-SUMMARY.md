---
id: S01
parent: M046
milestone: M046
provides:
  - Working memberPage fixture — downstream tests (admin-access-control, member-permissions, dark-mode, debug-pages) all pass
  - Session token caching — faster E2E runs for auth-dependent tests
requires:
  []
affects:
  - S06
key_files:
  - e2e/fixtures/auth.ts
key_decisions:
  - Used example.com (RFC 2606 reserved) instead of test.local for member email — EmailStr accepts it
  - Module-level token cache with /api/auth/me validation before reuse
  - Invite error handling: throw on non-2xx/non-409 instead of silently producing null token
patterns_established:
  - Module-level token caching with /api/auth/me validation before reuse — pattern for eliminating redundant auth round-trips in E2E fixtures
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M046/slices/S01/tasks/T01-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-29T01:32:27.972Z
blocker_discovered: false
---

# S01: Auth Fixture — Session Caching & Member Login

**Fixed member email domain (.local → example.com) and added session token caching, unblocking all 11 member-dependent E2E tests.**

## What Happened

All 11 memberPage-dependent E2E tests were failing because `MEMBER_EMAIL = 'member@test.local'` was silently rejected by Pydantic `EmailStr` on the `/api/auth/invite` endpoint. The `.local` TLD is a special-use domain (RFC 6762) that EmailStr doesn't accept as a valid email domain. The invite returned 422, but the test fixture didn't check the response status — so the member user was never created, the magic-link endpoint returned `token: null`, and all downstream member tests failed.

The fix was straightforward: changed `MEMBER_EMAIL` to `'member@example.com'` (RFC 2606 reserved domain, universally accepted by email validators). `OWNER_EMAIL` remains `'owner@test.local'` because the setup/magic-link endpoints use plain `str`, not `EmailStr`.

Additionally, added module-level session token caching (`_cachedOwnerToken`, `_cachedMemberToken`) with an `isTokenValid()` helper that checks `/api/auth/me` before reuse. This eliminates redundant auth round-trips when multiple tests in the same worker share fixtures.

Improved invite error handling: non-2xx, non-409 responses now throw with status code and body, making future fixture failures immediately diagnosable instead of silently producing null tokens.

## Verification

Ran all 4 affected test files (admin-access-control, member-permissions, dark-mode, debug-pages) plus session-management path. 15 tests passed in 14.1s, 0 failures. All 11 previously-failing member-dependent tests now pass.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

tests/04-session/session-management.spec.ts does not exist — Playwright skips non-existent paths gracefully. The plan referenced it as a regression check target, but it was never created. No impact on verification.

## Known Limitations

OWNER_EMAIL still uses test.local — works because setup/magic-link use str not EmailStr. If those endpoints ever add EmailStr validation, OWNER_EMAIL will need the same fix.

## Follow-ups

None.

## Files Created/Modified

- `e2e/fixtures/auth.ts` — Changed MEMBER_EMAIL from test.local to example.com, added module-level _cachedOwnerToken/_cachedMemberToken with isTokenValid() helper, improved invite error handling
