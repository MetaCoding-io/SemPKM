---
id: T01
parent: S09
milestone: M005
provides:
  - Playwright E2E spec for tag hierarchy expansion, count badges, and autocomplete
  - tagHierarchy selector group in SEL helpers
key_files:
  - e2e/tests/24-tag-hierarchy/tag-hierarchy.spec.ts
  - e2e/helpers/selectors.ts
key_decisions:
  - Seed data lacks hierarchical tags; tests create their own via the command API (ownerPage.request) in a setup helper
  - Tags must use full IRI `urn:sempkm:model:basic-pkm:tags` as predicate (bpkm prefix not in COMMON_PREFIXES)
  - Tag autocomplete test clears input before typing to avoid appending to pre-existing tag values
patterns_established:
  - API-based test data setup via ownerPage.request.post() with session cookie extraction from ownerPage.context().cookies()
  - Using pressSequentially() with delay for htmx debounce-triggered inputs
  - Waiting for specific suggestion text content rather than any .suggestion-item to avoid false matches from focus-triggered unfiltered results
observability_surfaces:
  - npx playwright test tests/24-tag-hierarchy/ --reporter=list — 3 pass/fail results
  - Playwright trace files in e2e/test-results/ on failure
duration: 25m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Playwright E2E tests for tag hierarchy and autocomplete

**Added 3-test Playwright spec covering hierarchical tag folder expansion, count badges, and tag autocomplete suggestions in edit forms**

## What Happened

Created `e2e/tests/24-tag-hierarchy/tag-hierarchy.spec.ts` with 3 tests using the `ownerPage` fixture:

1. **Hierarchical tag folders expand to show nested sub-folders** — creates test objects with `/`-delimited tags (`e2ehier/alpha`, `e2ehier/beta`) via the command API, switches explorer to by-tag mode, verifies the `e2ehier` root folder appears as a folder node, clicks to expand, and asserts `alpha` and `beta` sub-folder nodes appear inside `.tree-children`.

2. **Tag folders show count badges with correct totals** — verifies the root folder badge shows ≥ 3 (2 alpha + 1 beta objects), expands the folder, and verifies sub-folder badges show ≥ 2 for alpha and ≥ 1 for beta.

3. **Tag autocomplete shows suggestions when typing in edit form** — opens an object, clicks the Edit button (`.mode-toggle`), expands properties if collapsed, clears the tag input, types "arch" with `pressSequentially()` (delay: 150ms) to trigger the debounced htmx fetch, and asserts a suggestion containing "arch" (matching "architecture") appears.

Key discovery: seed data has no hierarchical (`/`-delimited) tags. The plan assumed `architect/build` etc. existed. Solved by creating test objects with hierarchical tags in a setup helper via the command API. Tags must use the full IRI `urn:sempkm:model:basic-pkm:tags` because the `bpkm` prefix is not registered in `COMMON_PREFIXES`.

Added `tagHierarchy` selector group to `SEL` in `e2e/helpers/selectors.ts` with selectors for folder nodes, object leaves, tree children, count badges, labels, autocomplete fields, inputs, dropdown, and suggestion items.

## Verification

- `cd e2e && npx playwright test tests/24-tag-hierarchy/ --reporter=list --project=chromium` — 3 passed (15.9s)
- `cd e2e && npx playwright test tests/24-tag-hierarchy/ --reporter=list --project=firefox` — 3 passed (18.3s)
- Existing `tests/20-tags/tag-explorer.spec.ts` test 2 (by-tag explorer) still passes — selector additions are additive

### Slice-level verification (partial — T01 is first task):
- ✅ `cd e2e && npx playwright test tests/24-tag-hierarchy/ --reporter=list` — passes
- ⬜ `cd e2e && npx playwright test tests/25-ops-log/ --reporter=list` — not yet created (T02)
- ⬜ `grep -l "hierarchical..." docs/guide/04-workspace-interface.md` — not yet written (T03)
- ⬜ `grep -l "autocomplete..." docs/guide/05-working-with-objects.md` — not yet written (T03)
- ⬜ `grep -l "Refresh..." docs/guide/10-managing-mental-models.md` — not yet written (T03)
- ⬜ `grep -l "Operations Log..." docs/guide/14-system-health-and-debugging.md` — not yet written (T03)

## Diagnostics

- Run `npx playwright test tests/24-tag-hierarchy/ --reporter=list` to check test health
- On failure, trace files in `e2e/test-results/` contain DOM snapshots, network, and screenshots
- Rate-limit flakiness: tests consume 3 magic-link tokens; if run <60s after other tests, rate limit (5/min) may cause auth failures on retry — wait and re-run

## Deviations

- Seed data has no hierarchical tags (plan assumed `architect/build`, `garden/cultivate` existed). Solved by creating test data via the command API in a setup helper function rather than relying on seed data.
- Removed `test.beforeAll` approach in favor of a helper function called from the first test, because `beforeAll` doesn't have access to `ownerPage` fixture and raw `request` context lacks the session cookie management needed for the nginx proxy.
- Tags require full IRI `urn:sempkm:model:basic-pkm:tags` (not compact `bpkm:tags`) because `bpkm` prefix is not in `COMMON_PREFIXES`.

## Known Issues

- Pre-existing flaky test in `tests/20-tags/tag-explorer.spec.ts` test 1 ("tag pills visible on object with tags") — properties toggle expansion timing issue unrelated to this task.

## Files Created/Modified

- `e2e/tests/24-tag-hierarchy/tag-hierarchy.spec.ts` — new spec file with 3 passing tests
- `e2e/helpers/selectors.ts` — added `tagHierarchy` selector group
- `.gsd/milestones/M005/slices/S09/tasks/T01-PLAN.md` — added Observability Impact section
