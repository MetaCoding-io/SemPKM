---
estimated_steps: 7
estimated_files: 2
---

# T01: Playwright E2E tests for tag hierarchy and autocomplete

**Slice:** S09 — E2E Tests & Docs
**Milestone:** M005

## Description

Create Playwright E2E tests covering the hierarchical tag tree (TAG-04) and tag autocomplete (TAG-05) features. Three tests in one spec file, using the `ownerPage` fixture for all tests to stay within the 5/min magic-link rate limit. Tests verify that `/`-delimited tags render as nested folders in the By Tag explorer, that expanding a hierarchical folder shows sub-folders with correct count badges, and that typing in a tag input field in an edit form shows autocomplete suggestions from the graph.

## Steps

1. Add `tagHierarchy` selectors to `e2e/helpers/selectors.ts` — reuse existing `data-testid="tag-folder"` and `data-testid="tag-object"` from `tag_tree.html`/`tag_tree_folder.html`, add selectors for sub-folder nodes and autocomplete dropdown (`.tag-autocomplete-field`, `.suggestion-item`)
2. Create `e2e/tests/24-tag-hierarchy/tag-hierarchy.spec.ts` with imports from auth fixtures, selectors, and wait helpers
3. Write test 1 — "hierarchical tag folders expand to show nested sub-folders": navigate to workspace, switch to by-tag mode, find a tag folder that contains `/` nested tags (e.g. `architect` which has `architect/build`), click it, wait for htmx settle, assert sub-folder nodes appear with `data-testid="tag-folder"` inside the expanded children area
4. Write test 2 — "tag folders show count badges with correct totals": in same by-tag mode, verify that hierarchical folders show `.tree-count-badge` elements with numeric values ≥ 1, and that sub-folder count badges are also present after expansion
5. Write test 3 — "tag autocomplete shows suggestions when typing in edit form": navigate to workspace, open a seed object with tags (click a type section to expand, click an object leaf), switch to edit mode, find a tag input field (`.tag-autocomplete-field input`), type slowly to trigger debounced htmx fetch, wait for `.suggestion-item` elements to appear in the autocomplete dropdown, assert at least one suggestion is visible. Handle the case where the input might be in the "Advanced" collapsible section.
6. Ensure all `waitForIdle(ownerPage)` calls are placed after htmx interactions to prevent assertion flakiness
7. Ensure test 3 uses `{ slowly: true }` or equivalent character-by-character typing to trigger the htmx debounce, and waits generously (3-5 seconds) for the suggestion response

## Must-Haves

- [ ] Three tests pass in `tag-hierarchy.spec.ts`
- [ ] Tests use `ownerPage` fixture (no `memberPage`) to minimize rate limit impact
- [ ] Tests follow existing tag-explorer.spec.ts patterns for mode switching and element selection
- [ ] Tag autocomplete test types slowly to trigger debounced fetch
- [ ] All htmx interactions followed by `waitForIdle()` calls

## Verification

- `cd e2e && npx playwright test tests/24-tag-hierarchy/tag-hierarchy.spec.ts --reporter=list` — 3 tests pass
- No other test files in the directory are broken by the new selectors

## Inputs

- `e2e/tests/20-tags/tag-explorer.spec.ts` — reference pattern for tag tree tests, mode switching, folder expansion
- `e2e/helpers/selectors.ts` — existing SEL object to extend
- `e2e/helpers/wait-for.ts` — waitForWorkspace, waitForIdle helpers
- `e2e/fixtures/auth.ts` — ownerPage fixture
- `backend/app/templates/browser/tag_tree.html` — `data-testid="tag-folder"` attribute
- `backend/app/templates/browser/tag_tree_folder.html` — sub-folder rendering with `data-testid="tag-folder"`
- `backend/app/templates/browser/tag_suggestions.html` — `.suggestion-item` class for autocomplete items
- S03 summary: hierarchical tags like `architect/build`, `garden/cultivate` exist in basic-pkm seed data
- S04 summary: autocomplete uses `htmx:configRequest` listener, `.tag-autocomplete-field` wrapper

## Observability Impact

- **New signal:** `npx playwright test tests/24-tag-hierarchy/ --reporter=list` reports 3 pass/fail results for tag hierarchy and autocomplete features
- **Inspection:** Playwright trace files in `e2e/test-results/` on failure capture DOM snapshots, network, and screenshots
- **Failure visibility:** Test failures surface as non-zero exit codes; specific assertion failures name the element selector and expected state

## Expected Output

- `e2e/tests/24-tag-hierarchy/tag-hierarchy.spec.ts` — new spec file with 3 passing tests
- `e2e/helpers/selectors.ts` — extended with tag hierarchy and autocomplete selectors
