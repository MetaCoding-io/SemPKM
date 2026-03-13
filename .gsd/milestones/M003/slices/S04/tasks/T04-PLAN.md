---
estimated_steps: 5
estimated_files: 3
---

# T04: E2E test for tag pills and by-tag explorer mode

**Slice:** S04 — Tag System Fix & Tag Explorer
**Milestone:** M003

## Description

Write Playwright E2E tests verifying the full integration: tag pills render correctly for basic-pkm seed objects, the by-tag explorer mode shows real tag folders with counts, and expanding a tag shows clickable objects. Also update the existing explorer-mode-switching spec to expect real content instead of the old placeholder when switching to by-tag.

## Steps

1. Create `e2e/tests/20-tags/tag-explorer.spec.ts`. Use the existing auth fixture pattern (`import { test, expect } from '../../fixtures/auth'`). Keep to 2-3 test blocks max to stay within auth rate limit.
2. Test 1 — "tag pills visible on object with tags":
   - Navigate to workspace, wait for tree
   - Open a basic-pkm seed object known to have tags (e.g., first Note type object)
   - Assert `.tag-pill` elements are visible in the object read view
   - Assert at least one pill text starts with `#`
   - Assert individual tag values (not comma-separated string)
3. Test 2 — "by-tag explorer shows tag folders and expansion works":
   - Switch explorer dropdown to `by-tag`
   - Wait for tag tree to load (`[data-testid="tag-folder"]` or `.tree-node` within explorer tree body)
   - Assert at least 3 tag folders visible (basic-pkm seed has many tags)
   - Assert tag folders show count badges
   - Click a tag folder to expand
   - Wait for children to load (`[data-testid="tag-object"]` or `.tree-leaf`)
   - Assert at least 1 object leaf visible
   - Click the object leaf and verify object tab opens
4. Update `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts`:
   - Find the test that switches to by-tag and expects placeholder content
   - Update expectations to match real tag tree content (`.tree-node` or tag folders instead of placeholder message)
   - Ensure the round-trip test (by-tag → by-type → by-tag) still works with real content
5. Run the full E2E suite for both test directories: `cd e2e && npx playwright test tests/20-tags/ tests/19-explorer-modes/ --reporter=list`

## Must-Haves

- [ ] Tag pill E2E test verifies `.tag-pill` elements visible with `#` prefix
- [ ] By-tag explorer E2E verifies real tag folders appear (not placeholder)
- [ ] Tag expansion E2E verifies objects load under expanded tag folder
- [ ] Object click-through from tag tree opens object tab
- [ ] Existing explorer-mode-switching tests updated and passing
- [ ] Tests stay within auth rate limit (≤5 magic-link calls/minute)

## Verification

- `cd e2e && npx playwright test tests/20-tags/ --reporter=list` — tag tests pass
- `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list` — updated mode-switching tests pass
- No test uses more than 2 authenticated page fixtures (respects rate limit)

## Observability Impact

- Signals added/changed: None (test-only task)
- How a future agent inspects this: Run the E2E tests; failures show Playwright traces and screenshots
- Failure state exposed: Playwright test reports with trace archives on failure

## Inputs

- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — existing tests referencing by-tag placeholder
- `e2e/fixtures/auth.ts` — auth fixture for authenticated page
- `e2e/helpers/selectors.ts` — SEL constants for explorer elements
- `e2e/helpers/wait-for.ts` — `waitForWorkspace`, `waitForIdle` helpers
- T01-T03 completed: seed data has array tags, by-tag explorer returns real content, tag pills render

## Expected Output

- `e2e/tests/20-tags/tag-explorer.spec.ts` — new E2E test file with 2-3 tests
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — updated expectations for by-tag mode
