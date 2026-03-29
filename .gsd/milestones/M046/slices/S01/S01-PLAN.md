# S01: Auth Fixture — Session Caching & Member Login

**Goal:** All 11 memberPage-dependent E2E tests pass by fixing the auth fixture's member email domain and adding session token caching.
**Demo:** After this: Auth-dependent tests (admin-access-control, member-permissions, dark-mode, session-management) all pass without magic link failures

## Tasks
- [x] **T01: Fix MEMBER_EMAIL domain from test.local to example.com and add module-level session token caching to E2E auth fixture** — ## Description

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
  - Estimate: 30m
  - Files: e2e/fixtures/auth.ts
  - Verify: cd e2e && npx playwright test tests/05-admin/admin-access-control.spec.ts tests/07-multi-user/member-permissions.spec.ts tests/06-settings/dark-mode.spec.ts tests/05-admin/debug-pages.spec.ts tests/04-session/session-management.spec.ts --project=chromium --reporter=list 2>&1 | tail -20
