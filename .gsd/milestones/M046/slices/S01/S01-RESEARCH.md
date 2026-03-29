# S01 Research: Auth Fixture — Session Caching & Member Login

## Summary

All memberPage-dependent E2E tests fail with `"Magic link request did not return a token for member@test.local"`. The root cause is **Pydantic `EmailStr` rejecting the `.local` TLD** on the invite endpoint. The invite silently fails (422), so the member user is never created and has no pending invitation, which causes the magic-link endpoint to return `token: null` (F-018 unknown-email guard). Session caching is a secondary optimization — not the cause of failures.

## Root Cause — Confirmed via Live Tests

The `memberPage` fixture in `e2e/fixtures/auth.ts` follows this sequence:
1. `POST /api/auth/invite { email: "member@test.local", role: "member" }` — uses `InviteRequest` schema
2. `POST /api/auth/magic-link { email: "member@test.local" }` — uses `MagicLinkRequest` schema
3. `POST /api/auth/verify { token: <from step 2> }`

Step 1 fails because `InviteRequest.email` is typed as `EmailStr` (Pydantic), which rejects `.local` TLDs. The fixture ignores the invite error (`// Ignore if already invited`). Step 2 then hits the F-018 guard — no user exists, no pending invitation exists → returns generic message with `token: null`. Step 3 never executes. All 11 failing tests across 4 files hit this path.

**Verified live:** `curl -s -X POST http://localhost:3901/api/auth/invite ... '{"email":"member@test.local","role":"member"}'` returns `422: "The part after the @-sign is a special-use or reserved name"`.

## Failing Tests (11 total, 4 files)

| File | Failing Tests | Root Cause |
|------|--------------|------------|
| `e2e/tests/05-admin/admin-access-control.spec.ts` | 3 (all memberPage tests) | memberPage fixture fails |
| `e2e/tests/07-multi-user/member-permissions.spec.ts` | 6 (all tests) | memberPage fixture fails |
| `e2e/tests/06-settings/dark-mode.spec.ts` | 1 (per-user isolation test) | memberPage fixture fails |
| `e2e/tests/05-admin/debug-pages.spec.ts` | 1 (member access test) | memberPage fixture fails |

**Not failing:** `session-management.spec.ts` already passes (5/5) — it imports from auth fixtures but doesn't use `memberPage`.

## Recommendation

### Fix 1: Change test email from `.local` to `.example.com` (Primary fix)

Change `MEMBER_EMAIL` in `e2e/fixtures/auth.ts` from `member@test.local` to `member@example.com` (RFC 2606 reserved domain, accepted by `EmailStr`). Also change `OWNER_EMAIL` to `owner@example.com` for consistency, which requires changing the `SetupRequest` email default too — or just the fixture constant.

**Why not change `InviteRequest` to use `str`?** The `EmailStr` validation on the invite endpoint is a reasonable security measure for production. The test should use valid emails. The invite-flow test already uses `@example.com` with an explanatory comment: "Use example.com (RFC 2606 reserved) — .local TLD is rejected by pydantic EmailStr".

**Migration concern:** The owner user is created during setup with `owner@test.local`. Changing it to `owner@example.com` requires the test DB to be clean (no pre-existing owner). The test stack uses ephemeral volumes, so a `docker compose down -v && up` cycle handles this. But for the currently-running stack, the owner email is already set. Two approaches:
- A: Change only `MEMBER_EMAIL` (simpler, fixes all 11 failures)
- B: Change both emails (cleaner, requires stack restart for the owner change)

**Recommended: Option A** — change only `MEMBER_EMAIL` to `member@example.com`. The owner flow already works with `@test.local` because setup and magic-link both use plain `str`, not `EmailStr`. Changing the owner email is unnecessary risk.

### Fix 2: Session caching (Performance optimization)

Currently every test that uses `ownerSessionToken` (directly or via `ownerPage`/`ownerRequest`/`memberPage`) triggers a new magic-link + verify cycle. With `workers: 1`, all tests run in one Node process, so module-level caching works:

```typescript
let _cachedOwnerToken: string | null = null;
let _cachedMemberToken: string | null = null;
```

In the `ownerSessionToken` fixture, check the cache first and only do a magic-link round-trip on cache miss. Same for `memberPage`. This eliminates ~200+ redundant DB writes (magic token creation, used-token tracking, session creation) across the full suite.

**Cache invalidation:** The `session-management.spec.ts` test explicitly tests logout which invalidates a session. But it creates its own sessions via `request` fixture — it doesn't use the cached `ownerSessionToken`. No cache invalidation is needed.

### Fix 3: Fixture error handling improvement (Minor)

The `memberPage` fixture should propagate invite errors instead of silently ignoring them. Change:
```typescript
// Current: silently ignores 422
await ownerCtx.post(`${BASE_URL}/api/auth/invite`, {
  data: { email: MEMBER_EMAIL, role: 'member' },
});
```
To check for non-2xx/non-409 (already exists) responses and throw with a descriptive error.

## Implementation Landscape

### Files to Modify

| File | Change |
|------|--------|
| `e2e/fixtures/auth.ts` | (1) Change `MEMBER_EMAIL` to `member@example.com`, (2) Add module-level token caching, (3) Improve invite error handling |

### Files NOT Modified

- `backend/app/auth/schemas.py` — `EmailStr` on `InviteRequest` stays (correct for production)
- `backend/app/auth/router.py` — No changes needed
- Test spec files — They import `MEMBER_EMAIL` from the fixture, so they auto-pick up the change

### Natural Seams

This is a single-file fix. All changes are in `e2e/fixtures/auth.ts`. The tasks divide as:

1. **T01: Fix member email + caching** — Change `MEMBER_EMAIL`, add token caching, improve error handling
2. **T02: Verify all affected tests pass** — Run admin-access-control, member-permissions, dark-mode, debug-pages

Or combine into a single task since it's all one file.

### Verification

```bash
cd e2e && npx playwright test tests/05-admin/admin-access-control.spec.ts tests/07-multi-user/member-permissions.spec.ts tests/06-settings/dark-mode.spec.ts tests/05-admin/debug-pages.spec.ts --project=chromium --reporter=list
```

Expected: all 11 previously-failing tests pass. Additionally `session-management.spec.ts` should continue passing (regression check).

### Risks

- **Low:** Changing `MEMBER_EMAIL` could affect other test files that import `MEMBER_EMAIL` — but only 3 files import it, and they use it for display assertions, not for login logic. The actual login happens in the fixture.
- **Low:** Session caching could mask a session-invalidation bug. Mitigated by: (1) session-management tests create their own sessions, (2) cached tokens are validated via `/api/auth/me` before use.
