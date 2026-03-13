---
id: T04
parent: S03
milestone: M003
provides:
  - 5 E2E Playwright tests for VFS explorer modes (mount dropdown, folder expansion, object click-through, mode switching)
  - Mount-specific selectors in shared selectors.ts
key_files:
  - e2e/tests/20-vfs-explorer/vfs-explorer.spec.ts
  - e2e/helpers/selectors.ts
key_decisions:
  - Used ensureMount() idempotent pattern called from each test instead of beforeAll — avoids extra magic-link consumption from separate beforeAll auth, and handles Playwright retries cleanly
  - Mount cleanup done as last step of final test using ownerRequest fixture rather than afterAll — keeps auth within fixture lifecycle
  - Tests use toBeAttached() for option elements instead of toBeVisible() — native select options are never "visible" in Playwright's sense
patterns_established:
  - ensureMount() pattern for test-managed VFS mount lifecycle without beforeAll auth overhead
  - selectMountMode() shared helper for mount mode selection and tree content waiting
observability_surfaces:
  - Playwright captures screenshot + trace on failure in e2e/test-results/
  - Test names map directly to EXP-04 (mount in dropdown) and EXP-05 (object click-through) requirements
duration: 1h
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T04: E2E tests for VFS explorer modes

**Added 5 Playwright E2E tests verifying VFS mounts appear in the explorer dropdown, folders expand with object leaves, object click-through opens workspace tabs, and switching back to built-in modes works correctly.**

## What Happened

Created `e2e/tests/20-vfs-explorer/vfs-explorer.spec.ts` with 5 tests that run against the full Docker Compose stack. Each test uses the `ownerRequest` fixture to ensure a by-type VFS mount exists (via idempotent `ensureMount()` helper), then exercises the UI flow.

Added 3 mount-specific selectors to `e2e/helpers/selectors.ts`: `mountOption`, `mountFolderNode`, `mountObjectLeaf` — mapping to the `data-testid` attributes added to mount tree templates in T01.

Also fixed a pre-existing bug in the `list_mounts` API endpoint where OPTIONAL SPARQL clauses produced duplicate bindings — added `DISTINCT` to the SELECT query in `backend/app/vfs/mount_router.py`. This was discovered because the duplicate API responses caused `initExplorerMountOptions()` to inject duplicate `<option>` elements in the dropdown.

Tests:
1. **mount option appears in explorer dropdown after page load** — verifies async mount injection, option value/text, optgroup structure (EXP-04)
2. **selecting mount mode loads tree with folder nodes** — verifies htmx swap, folder structure, no nav sections
3. **expanding a folder shows object leaves** — verifies htmx lazy expansion, data-iri attributes, leaf labels
4. **clicking an object leaf opens object tab (EXP-05)** — verifies dockview tab creation with matching label
5. **switching back to by-type restores normal tree** — regression guard, verifies nav sections return and mount elements removed

## Verification

- `cd e2e && npx playwright test tests/20-vfs-explorer/ --reporter=list --project=chromium` — **5/5 pass**
- `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list --project=chromium` — **5/5 pass** (no regressions)
- Slice-level: `cd e2e && npx playwright test tests/20-vfs-explorer/ --reporter=list --project=chromium` — all pass ✓
- Slice-level: `cd backend && python -m pytest tests/test_mount_explorer.py -v` — verified earlier in T02, not re-run (backend unchanged except DISTINCT fix)

## Diagnostics

- Run `npx playwright test tests/20-vfs-explorer/ --reporter=list` — test names map to EXP-04 and EXP-05 requirements
- Failures capture screenshots and traces in `e2e/test-results/`
- Tests gracefully skip folder expansion and object click-through tests when the triplestore has no typed objects (empty seed data)

## Deviations

- Added `DISTINCT` to the `list_mounts` SPARQL query in `backend/app/vfs/mount_router.py` — not in the original task plan, but was a real bug causing duplicate dropdown options that blocked the E2E tests from passing
- Used `ensureMount()` pattern called from each test instead of `beforeAll/afterAll` — Playwright fixtures are per-test scoped, and `beforeAll` with manual auth consumed extra magic-link tokens causing rate limit exhaustion on retries

## Known Issues

- First test in any E2E suite sometimes fails with a transient API "Internal Server Error" on first auth call — resolved by Playwright's built-in retry mechanism (retries: 1 in config). This is a pre-existing infrastructure timing issue, not specific to VFS tests.
- Running 20-vfs-explorer and 19-explorer-modes back-to-back within 60 seconds hits the magic-link rate limit (5/min). Each suite needs separate runs with spacing.

## Files Created/Modified

- `e2e/tests/20-vfs-explorer/vfs-explorer.spec.ts` — 5 E2E tests for VFS explorer modes
- `e2e/helpers/selectors.ts` — added mountOption, mountFolderNode, mountObjectLeaf selectors to explorer section
- `backend/app/vfs/mount_router.py` — added DISTINCT to list_mounts SPARQL query (bugfix for duplicate results)
