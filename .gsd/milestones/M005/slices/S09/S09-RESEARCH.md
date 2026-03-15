# S09: E2E Tests & Docs — Research

**Date:** 2026-03-14  
**Status:** Ready for planning

## Summary

S09 adds Playwright E2E test coverage for the five user-visible implementation slices (S01–S05) and updates user guide documentation. Research reveals that the E2E infrastructure is mature — 83 spec files already exist with well-established patterns (auth fixtures, selectors, dockview/htmx helpers). The existing `sparql-advanced.spec.ts` already exercises saved queries CRUD, history, and sharing against the now-RDF-backed QueryService, so S01's migration is effectively already integration-tested. New E2E tests are needed for: hierarchical tag tree expansion (S03), tag autocomplete in edit forms (S04), operations log admin page (S02), and the model refresh button (S05). Documentation updates target 3 existing guide chapters plus a new ops log section.

The main constraints are the 5/min magic-link rate limit (D069 pattern — consolidate tests per spec file), the test stack running at port 3901, and the need for actual seed data with `/`-delimited tags to test tag hierarchy. The basic-pkm seed data has tags like `architect/build`, `garden/cultivate` from the Ideaverse import, which are suitable for hierarchy testing.

## Recommendation

**Structure:** Create 3 new spec files in 2 test directories:
1. `e2e/tests/24-tag-hierarchy/tag-hierarchy.spec.ts` — hierarchical tag tree expansion and autocomplete
2. `e2e/tests/25-ops-log/ops-log.spec.ts` — operations log page rendering, filter, and pagination
3. `e2e/tests/25-ops-log/model-refresh.spec.ts` — refresh button click and ops log entry verification

**Do NOT create a new spec for S01 query migration.** The existing `sparql-advanced.spec.ts` already covers saved queries CRUD (create, list, update, delete), history (clear, record, fetch), and sharing — all of which now hit the RDF-backed QueryService. Running the existing spec IS the query migration E2E test.

**Documentation:** Update 3 existing chapters and add 1 new section:
1. `docs/guide/04-workspace-interface.md` — add hierarchical tag tree description under "By Tag" mode
2. `docs/guide/05-working-with-objects.md` — add tag autocomplete mention in editing section
3. `docs/guide/10-managing-mental-models.md` — add "Refreshing Model Artifacts" section
4. `docs/guide/14-system-health-and-debugging.md` — add "Operations Log" section under Debug Tools

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Auth fixtures | `e2e/fixtures/auth.ts` (ownerPage, ownerRequest, memberPage) | Handles setup, login, session cookies — use `ownerPage` for all UI tests |
| Selector constants | `e2e/helpers/selectors.ts` (SEL object) | Centralized CSS selectors — extend with new entries for ops-log |
| htmx wait helpers | `e2e/helpers/wait-for.ts` (waitForWorkspace, waitForIdle) | Critical for htmx-based pages — always call after navigation and interactions |
| Dockview tab helpers | `e2e/helpers/dockview.ts` (openObjectTab, openNewObjectForm) | Used to open edit forms for testing autocomplete |
| Seed data constants | `e2e/fixtures/seed-data.ts` (SEED, TYPES) | Reference IRIs for known objects with tags |
| API client | `e2e/helpers/api-client.ts` (ApiClient) | For API-level test arrangement (creating objects, SPARQL queries) |

## Existing Code and Patterns

- `e2e/tests/20-tags/tag-explorer.spec.ts` — **Reference pattern for tag tree tests.** Already tests flat tag folders and expansion. The hierarchy tests should extend this pattern for multi-level nesting.
- `e2e/tests/05-admin/admin-model-detail.spec.ts` — **Reference pattern for admin page E2E tests.** Shows how to navigate admin pages, verify table content, check button visibility.
- `e2e/tests/05-admin/admin-model-lifecycle.spec.ts` — **Reference pattern for model operations.** Shows dialog handling (`ownerPage.on('dialog', ...)`) needed for `hx-confirm` on the Refresh button.
- `e2e/tests/05-admin/sparql-advanced.spec.ts` — **Already tests S01 query migration end-to-end.** Saved query CRUD, history, sharing, promotion — all verified via API. No new tests needed for S01.
- `e2e/tests/20-favorites/favorites.spec.ts` — **Reference pattern for toggle interactions and section refresh.** Shows how to use `page.evaluate()` for API calls and `htmx.trigger()` for section refresh.
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — **Reference pattern for explorer mode switching.** Shows `selectOption(SEL.explorer.modeSelect, 'by-tag')` pattern used to get to tag tree.
- `backend/app/templates/admin/ops_log.html` — **Template with `data-testid="ops-log-table"`.** Use this for E2E assertions. Also has `#ops-log-filter` select and `.ops-log-type-badge` for filter/type assertions.
- `backend/app/templates/admin/models.html` — **Refresh button uses `hx-confirm` and `hx-post`.** E2E test must register `dialog` handler before clicking.
- `backend/app/templates/browser/tag_tree.html` / `tag_tree_folder.html` — **Templates use `data-testid="tag-folder"` and `data-testid="tag-object"`.** Already used in existing tag tests.
- `docs/guide/04-workspace-interface.md` — Line 86 mentions "By Tag" mode briefly. Needs expansion for hierarchy.
- `docs/guide/14-system-health-and-debugging.md` — Debug Tools section. Add Operations Log subsection.

## Constraints

- **Rate limit: 5 magic-link requests per minute** (slowapi, D069). Each `ownerPage`/`memberPage` fixture consumes one magic-link call. Consolidate related assertions into single test blocks. Max ~4 tests per spec file.
- **Sequential test execution** — `fullyParallel: false`, `workers: 1` in playwright.config.ts. Tests run against a shared Docker state.
- **Test stack at port 3901** — `docker-compose.test.yml` required. `npm run env:start` before tests.
- **No test isolation between spec files** — state mutations (favoriting, ops log entries) persist. Tests must handle pre-existing state gracefully (check before assert, clean up after).
- **Tag hierarchy data dependency** — Hierarchical tags (`architect/build`, `garden/cultivate`) come from basic-pkm seed data. If seed data changes, tag hierarchy tests break.
- **Model refresh known issue** — S05 Forward Intelligence notes basic-pkm archive has a JSON parsing error at runtime. Refresh button E2E test should expect either success or a specific error message in the UI.
- **htmx swap timing** — Always use `waitForIdle(page)` after interactions that trigger htmx swaps. The `waitForHtmxSettle()` helper is available for target-specific waits.

## Common Pitfalls

- **Tag tree folder expansion race condition** — After clicking a folder node, wait for both htmx settle AND content to appear. The `hx-trigger="click once"` means re-clicking won't re-fetch. Use `waitForIdle` + `waitForSelector` combo.
- **Explorer dropdown focus trap** — Per CLAUDE.md, `browser_click` with non-matching CSS selectors falls back to `select#explorer-mode-select`. This is a known issue in the E2E helper infrastructure. Use `page.selectOption()` for the mode select, not `browser_click`.
- **Ops log entries depend on prior admin actions** — The ops log page may be empty if no model install/inference/validation has run in the test stack session. Tests should either (a) trigger a model operation first, or (b) assert graceful empty state AND verify populated state by checking an API endpoint.
- **hx-confirm dialog interception** — Playwright auto-accepts dialogs but the handler must be registered BEFORE the triggering click. See `admin-model-lifecycle.spec.ts` line for the pattern: `ownerPage.on('dialog', (dialog) => dialog.accept())`.
- **Tag autocomplete htmx:configRequest** — The autocomplete uses a custom `htmx:configRequest` listener that intercepts requests to `/browser/tag-suggestions`. E2E tests should type slowly to trigger the debounced fetch, then assert the dropdown appears.

## Open Risks

- **Tag autocomplete E2E flakiness** — The autocomplete relies on htmx debounced GET requests + JavaScript `htmx:configRequest` event listener + DOM injection. Multiple async steps create timing windows. May need generous waits.
- **Ops log empty state on fresh test stack** — If the test stack was just started and no admin operations have occurred, the ops log page will be empty. The test should trigger a model operation (install PPV, or use existing basic-pkm install log) to ensure entries exist.
- **Model refresh error in basic-pkm** — The S05 summary notes a pre-existing JSON parsing error in the basic-pkm archive loader. The refresh E2E test must handle this: assert button exists and click succeeds, but verify either success message or error message appears (not a crash/500).

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Playwright | (checked available_skills) | none installed — standard Playwright patterns sufficient for this project |

No external skills needed. The E2E infrastructure is mature and well-documented within the codebase. Playwright usage follows standard patterns without framework-specific wrappers.

## Sources

- `e2e/playwright.config.ts` — test configuration (ports, timeouts, workers, projects)
- `e2e/fixtures/auth.ts` — auth fixture patterns (ownerPage, ownerRequest, magic-link login)
- `e2e/helpers/selectors.ts` — existing CSS selector constants (SEL object)
- `e2e/helpers/wait-for.ts` — htmx wait helpers (waitForWorkspace, waitForIdle)
- `e2e/tests/20-tags/tag-explorer.spec.ts` — existing tag explorer test (reference pattern)
- `e2e/tests/05-admin/sparql-advanced.spec.ts` — existing saved query CRUD + history tests (covers S01)
- `e2e/tests/05-admin/admin-model-lifecycle.spec.ts` — dialog handler pattern for hx-confirm
- S01–S05 summaries — Forward Intelligence sections for known fragilities

## Test Coverage Plan

### Already Covered (No New Tests Needed)

| Feature | Existing Coverage | File |
|---------|------------------|------|
| Saved queries CRUD (RDF-backed) | create, list, update, delete, get | `sparql-advanced.spec.ts` Part 6 |
| Query history (RDF-backed) | clear, record, fetch | `sparql-advanced.spec.ts` Part 5 |
| Query sharing | share, list shared, fork | `sparql-advanced.spec.ts` Part 7+ |
| Query promotion to view | promote, list promoted, demote | `sparql-advanced.spec.ts` Part 8+ |
| Flat tag tree (non-hierarchical) | folder render, count badges, leaf click | `tag-explorer.spec.ts` |

### New Tests Needed

| Feature | Spec File | Test Count | Priority |
|---------|-----------|-----------|----------|
| Hierarchical tag tree nesting | `24-tag-hierarchy/tag-hierarchy.spec.ts` | 2 | High |
| Tag autocomplete in edit form | `24-tag-hierarchy/tag-hierarchy.spec.ts` | 1 | High |
| Operations log page renders | `25-ops-log/ops-log.spec.ts` | 2 | Medium |
| Model refresh button (list + detail) | `25-ops-log/model-refresh.spec.ts` | 1 | Medium |

### Documentation Updates

| File | Change | Priority |
|------|--------|----------|
| `docs/guide/04-workspace-interface.md` | Expand "By Tag" mode description: add hierarchical nesting, folder icons, count badges, lazy expansion | High |
| `docs/guide/05-working-with-objects.md` | Add tag autocomplete mention in editing section: type-ahead suggestions, creating new tags | High |
| `docs/guide/10-managing-mental-models.md` | Add "Refreshing Model Artifacts" subsection: what it does, when to use it, what it preserves | Medium |
| `docs/guide/14-system-health-and-debugging.md` | Add "Operations Log" subsection under Debug Tools: how to access, what's logged, filter/pagination | Medium |
