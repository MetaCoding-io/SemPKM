---
estimated_steps: 4
estimated_files: 2
---

# T04: E2E tests for VFS explorer modes

**Slice:** S03 — VFS-Driven Explorer Modes
**Milestone:** M003

## Description

Create end-to-end Playwright tests that verify VFS mounts appear in the explorer dropdown, folders expand correctly, and object click-through opens workspace tabs. Tests run against the full Docker Compose stack with a real triplestore. Each test creates a mount via the API as setup, verifying the full integration from mount creation → dropdown appearance → tree rendering → object interaction.

## Steps

1. **Add mount explorer selectors to `selectors.ts`.** Add to the existing `explorer` section: `mountOption: 'option[value^="mount:"]'`, `mountFolderNode: '[data-testid="mount-folder"]'`, `mountObjectLeaf: '[data-testid="mount-object"]'`. These map to the `data-testid` attributes added to mount tree templates in T01.

2. **Create test file with setup/teardown.** `e2e/tests/20-vfs-explorer/vfs-explorer.spec.ts`. In `test.beforeAll`: authenticate, create a by-type VFS mount via `POST /api/vfs/mounts` (with strategy `by-type`, scope `all`). Store the returned mount `id` for use in tests. In `test.afterAll`: delete the mount via `DELETE /api/vfs/mounts/{id}`. This ensures tests are self-contained.

3. **Write ≤5 tests (rate limit constraint).** Tests:
   - **"mount option appears in explorer dropdown after page load"** — Navigate to workspace, wait for mount options to be injected (poll for `option[value^="mount:"]`), verify the created mount's name appears in the dropdown.
   - **"selecting mount mode loads mount-organized tree with folder nodes"** — Select the mount option in the dropdown, wait for `#explorer-tree-body` to update, verify `.tree-node` folder elements appear with `data-testid="mount-folder"`.
   - **"expanding a folder shows object leaves"** — Click a folder node, wait for children to load, verify `.tree-leaf` elements appear with `data-testid="mount-object"`.
   - **"clicking an object leaf opens object tab (EXP-05)"** — Click an object leaf, verify a dockview tab opens with the object's content (check for object view panel or tab title matching the object label).
   - **"switching back to by-type restores normal tree"** — Select "By Type" in the dropdown, verify `[data-testid="nav-section"]` elements reappear (regression guard).

4. **Handle test prerequisites.** The by-type strategy needs at least one object in the triplestore with an `rdf:type` to produce folders. The E2E test stack's seed data should provide this. If the mount tree is empty (no objects in scope), the test verifies the empty state message instead. Use appropriate `waitForSelector` calls with reasonable timeouts for async mount injection and htmx swaps.

## Must-Haves

- [ ] ≤5 tests to stay within auth magic-link rate limit
- [ ] Mount created via API in beforeAll, deleted in afterAll
- [ ] Test verifies mount option appears in dropdown (EXP-04)
- [ ] Test verifies object click-through opens tab (EXP-05)
- [ ] Test verifies switching back to built-in mode works (regression guard)
- [ ] All tests pass against E2E test stack

## Verification

- `cd e2e && npx playwright test tests/20-vfs-explorer/ --reporter=list --project=chromium` — all tests pass
- No regressions in existing E2E suites: `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list --project=chromium` — 5/5 pass

## Observability Impact

- Signals added/changed: None (tests are verification)
- How a future agent inspects this: Run `npx playwright test tests/20-vfs-explorer/ --reporter=list` — test names map directly to EXP-04 and EXP-05 requirements; failures include screenshots in `e2e/test-results/`
- Failure state exposed: Playwright captures screenshot + trace on failure in `e2e/test-results/`

## Inputs

- T01 backend — mount handler, children endpoint, templates (must be deployed in E2E stack)
- T03 frontend — dynamic mount dropdown injection (must be deployed in E2E stack)
- `e2e/helpers/selectors.ts` — existing explorer selectors
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — reference for explorer E2E test patterns
- `POST /api/vfs/mounts` and `DELETE /api/vfs/mounts/{id}` — mount CRUD API for test setup/teardown

## Expected Output

- `e2e/tests/20-vfs-explorer/vfs-explorer.spec.ts` — ≤5 E2E tests, all passing
- `e2e/helpers/selectors.ts` — mount explorer selectors added
