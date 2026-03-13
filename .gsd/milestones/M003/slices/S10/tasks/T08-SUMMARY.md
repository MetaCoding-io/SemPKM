---
id: T08
parent: S10
milestone: M003
provides:
  - e2e test for federation UI partials (inbox, collab, shared-graphs, contacts, shared-nav, inbox notifications)
  - e2e test for VFS MountSpec CRUD lifecycle (list, create, update, delete, preview, properties)
  - e2e test for VFS browser page and tree endpoint
  - e2e test for debug pages access control (owner 200, member 403)
key_files:
  - e2e/tests/18-federation/federation-ui.spec.ts
  - e2e/tests/13-v24-coverage/vfs-mountspec.spec.ts
  - e2e/tests/05-admin/debug-pages.spec.ts
key_decisions:
  - Debug routes are at /sparql and /events (no /debug/ prefix) — the pre-existing test stubs had wrong URLs (/debug/sparql, /debug/events) which were corrected
  - VFS mount test exercises full CRUD lifecycle (create → list → update → preview → properties → delete → verify deletion) plus validation (duplicate path rejection, invalid strategy rejection) in 2 consolidated tests
patterns_established:
  - For VFS mount e2e tests, create a mount with a unique path, exercise all CRUD operations, then delete and verify cleanup — keeps test isolated
  - Federation UI partials can all be tested in a single test() since they are independent GET endpoints returning HTML/JSON with no mutation side effects
observability_surfaces:
  - none — test-only task with no production code changes
duration: 30m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T08: Federation UI, VFS MountSpec, debug pages tests

**Rewrote pre-existing broken test stubs into 5 working test functions (1 federation + 2 VFS + 2 debug) covering all three endpoint categories — all passing.**

## What Happened

Replaced the pre-existing test stubs for federation UI, VFS MountSpec, and debug pages with real implementations:

1. **Federation UI** (`federation-ui.spec.ts`): Consolidated 6 separate test stubs into 1 test function that exercises all federation partials and endpoints — inbox-partial (HTML), collab-partial (HTML), shared-graphs (JSON array), contacts (JSON array), shared-nav (HTML), and inbox notifications (JSON array via LDN endpoint).

2. **VFS MountSpec** (`vfs-mountspec.spec.ts`): Rewrote 3 weak stubs into 2 comprehensive test functions. The first exercises the full mount CRUD lifecycle: list → create (flat strategy) → verify in list → update (change to by-type) → preview (by-type directories) → properties (SHACL-derived property list) → delete → verify deletion. The second tests the VFS browser page, tree endpoint, invalid strategy rejection, and duplicate path rejection.

3. **Debug pages** (`debug-pages.spec.ts`): Fixed incorrect URLs (stubs had `/debug/sparql` and `/debug/events`, but actual routes are `/sparql` and `/events` with no prefix). Consolidated 4 stubs into 2 test functions — one for owner access (both pages return 200 with HTML), one for member denial (both pages return 403+).

## Verification

- `cd e2e && npx playwright test tests/18-federation/federation-ui.spec.ts --project=chromium` — 1 passed
- `cd e2e && npx playwright test tests/13-v24-coverage/vfs-mountspec.spec.ts --project=chromium` — 2 passed
- `cd e2e && npx playwright test tests/05-admin/debug-pages.spec.ts --project=chromium` — 2 passed
- All 5 tests pass when run individually; combined runs hit the 5/minute magic-link rate limit (expected and consistent with T01-T07 behavior)

### Slice-level checks (intermediate — T08 of T12):
- `rg "test.skip(" e2e/tests/ -c -g '*.ts'` → 17 remaining (T09-T11 stubs — expected)
- Router coverage for T08 endpoints confirmed: federation/router.py, vfs/mount_router.py, debug/router.py

## Diagnostics

None — test-only task with no production code changes.

## Deviations

- Pre-existing debug pages test stubs used incorrect URLs `/debug/sparql` and `/debug/events`. The actual FastAPI debug router has no prefix — routes are mounted at `/sparql` and `/events`. Fixed in the rewrite.

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/18-federation/federation-ui.spec.ts` — rewrote from 6 stubs to 1 consolidated test covering all federation partials
- `e2e/tests/13-v24-coverage/vfs-mountspec.spec.ts` — rewrote from 3 stubs to 2 tests covering full mount CRUD and VFS browser
- `e2e/tests/05-admin/debug-pages.spec.ts` — rewrote from 4 stubs to 2 tests with corrected URLs and access control verification
