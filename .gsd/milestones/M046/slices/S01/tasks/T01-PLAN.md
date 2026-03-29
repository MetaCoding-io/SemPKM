---
estimated_steps: 29
estimated_files: 1
skills_used: []
---

# T01: Fix member email domain, add session caching, and verify all 11 tests pass

## Description

All 11 memberPage-dependent E2E tests fail because `MEMBER_EMAIL = 'member@test.local'` is rejected by Pydantic `EmailStr` on the `/api/auth/invite` endpoint (`.local` is a special-use TLD). The invite silently fails (422), so the member user is never created, and the magic-link endpoint returns `token: null`.

This task fixes the email domain, adds module-level session token caching to eliminate redundant auth round-trips, and improves the invite error handling to propagate real failures.

## Steps

1. In `e2e/fixtures/auth.ts`, change `MEMBER_EMAIL` from `'member@test.local'` to `'member@example.com'` (RFC 2606 reserved domain, accepted by `EmailStr`).

2. Add module-level cache variables above the fixture definitions:
   ```typescript
   let _cachedOwnerToken: string | null = null;
   let _cachedMemberToken: string | null = null;
   ```

3. In the `ownerSessionToken` fixture, check `_cachedOwnerToken` first. On cache miss, do the existing setup/login flow and store the result. On cache hit, validate the token is still good with a quick `GET /api/auth/me` check — if it fails, clear cache and re-login.

4. In the `memberPage` fixture, check `_cachedMemberToken` first. On cache miss, do the invite + login flow and store the result. On cache hit, validate with `/api/auth/me` — if it fails, clear cache and re-login.

5. In the `memberPage` fixture, change the invite call to check the response status. If the response is not 2xx and not 409 (already invited), throw an error with the response body so future fixture failures are immediately diagnosable.

6. Run all 4 affected test files plus session-management as regression check:
   ```bash
   cd e2e && npx playwright test tests/05-admin/admin-access-control.spec.ts tests/07-multi-user/member-permissions.spec.ts tests/06-settings/dark-mode.spec.ts tests/05-admin/debug-pages.spec.ts tests/04-session/session-management.spec.ts --project=chromium --reporter=list
   ```

## Must-Haves

- [ ] `MEMBER_EMAIL` is `'member@example.com'`
- [ ] `OWNER_EMAIL` remains `'owner@test.local'` (no change — it works because setup/magic-link use plain `str`, not `EmailStr`)
- [ ] Module-level `_cachedOwnerToken` and `_cachedMemberToken` variables with `/api/auth/me` validation before reuse
- [ ] Invite error handling: non-2xx, non-409 responses throw with descriptive error message
- [ ] All 11 previously-failing tests pass
- [ ] session-management tests still pass (regression)

## Verification

```bash
cd e2e && npx playwright test tests/05-admin/admin-access-control.spec.ts tests/07-multi-user/member-permissions.spec.ts tests/06-settings/dark-mode.spec.ts tests/05-admin/debug-pages.spec.ts tests/04-session/session-management.spec.ts --project=chromium --reporter=list
```

Expected: all tests pass (11 previously-failing + 5 session-management = 16+ passing tests, 0 failures).

## Inputs

- ``e2e/fixtures/auth.ts` — current auth fixture with MEMBER_EMAIL = 'member@test.local' and no session caching`
- ``backend/app/auth/schemas.py` — reference only: confirms InviteRequest.email uses EmailStr (do not modify)`
- ``e2e/tests/05-admin/admin-access-control.spec.ts` — imports MEMBER_EMAIL, uses memberPage fixture (3 tests)`
- ``e2e/tests/07-multi-user/member-permissions.spec.ts` — imports MEMBER_EMAIL, uses memberPage fixture (6 tests)`
- ``e2e/tests/06-settings/dark-mode.spec.ts` — imports MEMBER_EMAIL, uses memberPage fixture (1 test)`
- ``e2e/tests/05-admin/debug-pages.spec.ts` — uses memberPage fixture (1 test)`

## Expected Output

- ``e2e/fixtures/auth.ts` — updated with member@example.com email, module-level token caching, and invite error propagation`

## Verification

cd e2e && npx playwright test tests/05-admin/admin-access-control.spec.ts tests/07-multi-user/member-permissions.spec.ts tests/06-settings/dark-mode.spec.ts tests/05-admin/debug-pages.spec.ts tests/04-session/session-management.spec.ts --project=chromium --reporter=list 2>&1 | tail -20
