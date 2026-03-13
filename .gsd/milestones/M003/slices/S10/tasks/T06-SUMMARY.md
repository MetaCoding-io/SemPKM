---
id: T06
parent: S10
milestone: M003
provides:
  - e2e test for auth rate limiting (429 on magic-link endpoint after >5 requests/minute)
  - e2e test for owner invite flow (invite → magic-link → verify → member role check)
  - e2e test for member invite denial (owner-only permission enforcement)
key_files:
  - e2e/tests/99-rate-limiting/rate-limiting.spec.ts
  - e2e/tests/07-multi-user/invite-flow.spec.ts
key_decisions:
  - Moved rate-limiting test to 99-rate-limiting/ directory so it runs LAST in the suite — rate-limit tests exhaust the per-IP request budget which breaks auth fixtures in subsequent test files if run earlier
  - Used example.com (RFC 2606 reserved) instead of test.local for invite email addresses — pydantic EmailStr rejects .local TLD as a reserved special-use name, while MagicLinkRequest uses a lenient plain str validator
  - Consolidated invite flow into 1 test() function (3 assertions in 1 test) to stay within the 5/minute magic-link rate limit
patterns_established:
  - Rate-limit e2e tests that exhaust endpoint budgets must run after all tests that depend on those endpoints — use a high-numbered directory prefix (99-) to guarantee last execution
  - InviteRequest uses pydantic EmailStr with strict validation — use RFC 2606 domains (example.com) not .local TLD in test data
observability_surfaces:
  - none
duration: 45m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T06: Auth rate limiting & invite flow tests

**Added e2e tests for auth rate limiting (429 response) and owner invite flow (invite → login → role verification → member denial) — both passing.**

## What Happened

Rewrote the existing rate-limiting and invite-flow test files. The rate-limiting test sends rapid magic-link requests and verifies a 429 response with a "Rate limit exceeded" error body. The invite-flow test exercises the full owner invite cycle: owner invites a new email via API, the invited user requests a magic link, verifies the token to create a session, confirms their role is "member" via /api/auth/me, then attempts to invite another user and verifies the request is denied (≥400 status).

Key challenge: rate-limit tests exhaust the per-IP endpoint budget (slowapi in-memory, 5/minute for magic-link, 10/minute for verify). Running rate-limit tests before other auth-dependent tests would break their auth fixtures. Solved by moving the rate-limiting spec to `99-rate-limiting/` so Playwright's alphabetical file ordering runs it last.

Also discovered that the `InviteRequest` schema uses pydantic `EmailStr` which rejects `.local` TLD, unlike `MagicLinkRequest` which uses a lenient `str` validator. Fixed by using `@example.com` (RFC 2606 reserved domain) for test email addresses.

## Verification

```
cd e2e && npx playwright test tests/07-multi-user/invite-flow.spec.ts tests/99-rate-limiting/rate-limiting.spec.ts --project=chromium
# 2 passed (1.3s)
```

Slice-level checks (intermediate — T06 of T12):
- `rg "test.skip\(" e2e/tests/ -c -g '*.ts'` — 17 remaining stubs (expected; later tasks cover these)

## Diagnostics

None — test-only task with no production code changes.

## Deviations

- Rate-limiting test moved from `e2e/tests/00-setup/rate-limiting.spec.ts` to `e2e/tests/99-rate-limiting/rate-limiting.spec.ts` — original placement broke every subsequent auth-dependent test in the same suite run
- Rate-limiting test targets magic-link endpoint (as specified) rather than verify endpoint — the 99- directory ordering ensures it can't poison other tests
- Invite flow email changed from `@test.local` to `@example.com` due to pydantic EmailStr validation rejecting `.local` TLD

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/99-rate-limiting/rate-limiting.spec.ts` — rate-limit test (moved from 00-setup/, tests 429 on magic-link)
- `e2e/tests/07-multi-user/invite-flow.spec.ts` — invite flow test (consolidated 3 tests → 1, fixed email domain)
