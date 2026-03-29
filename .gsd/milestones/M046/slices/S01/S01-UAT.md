# S01: Auth Fixture — Session Caching & Member Login — UAT

**Milestone:** M046
**Written:** 2026-03-29T01:32:27.972Z

## UAT: Auth Fixture — Session Caching & Member Login

### Preconditions
- Docker test stack running at http://localhost:3901
- Instance set up with owner account (owner@test.local)
- E2E test dependencies installed (`cd e2e && npm install`)

### Test 1: Member Email Domain Fix
**Steps:**
1. Run: `cd e2e && npx playwright test tests/07-multi-user/member-permissions.spec.ts --project=chromium --reporter=list`
2. Observe: All 6 member-permissions tests pass (member workspace access, object create, object edit, admin restriction x3)

**Expected:** 6 passed, 0 failed. Previously all 6 failed with null token from magic-link.

### Test 2: Admin Access Control with Member
**Steps:**
1. Run: `cd e2e && npx playwright test tests/05-admin/admin-access-control.spec.ts --project=chromium --reporter=list`
2. Observe: All 4 tests pass (3 member-cannot-access + 1 owner-can-access)

**Expected:** 4 passed, 0 failed. Previously 3 member tests failed.

### Test 3: Dark Mode Per-User Settings
**Steps:**
1. Run: `cd e2e && npx playwright test tests/06-settings/dark-mode.spec.ts --project=chromium --reporter=list`
2. Observe: All 3 tests pass including "per-user settings: owner dark mode does not affect member"

**Expected:** 3 passed, 0 failed. Previously the per-user test failed.

### Test 4: Debug Pages Access Control
**Steps:**
1. Run: `cd e2e && npx playwright test tests/05-admin/debug-pages.spec.ts --project=chromium --reporter=list`
2. Observe: Both tests pass (owner access + member restriction)

**Expected:** 2 passed, 0 failed. Previously member restriction test failed.

### Test 5: Full Auth-Dependent Suite Regression
**Steps:**
1. Run all 4 files together: `cd e2e && npx playwright test tests/05-admin/admin-access-control.spec.ts tests/07-multi-user/member-permissions.spec.ts tests/06-settings/dark-mode.spec.ts tests/05-admin/debug-pages.spec.ts --project=chromium --reporter=list`
2. Observe: All 15 tests pass in a single run

**Expected:** 15 passed, 0 failed, runtime under 30s.

### Test 6: Token Caching Works (Performance)
**Steps:**
1. Run the full suite twice in sequence
2. Compare timing: second run should be equal or faster (cached tokens skip setup)

**Expected:** No auth fixture failures on second run — cached tokens validated via /api/auth/me.

### Edge Case: Invite Already Exists (409)
**Steps:**
1. Run member-permissions tests twice without resetting the instance
2. Second run's invite call returns 409 (already invited)

**Expected:** 409 is treated as success — member login proceeds normally, all tests pass.
