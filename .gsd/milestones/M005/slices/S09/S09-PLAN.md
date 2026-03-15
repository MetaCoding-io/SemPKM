# S09: E2E Tests & Docs

**Goal:** Playwright E2E test coverage for the five user-visible M005 implementation slices (S01–S05), plus user guide documentation updates for new features.

**Demo:** `npx playwright test --grep "Tag Hierarchy|Ops Log|Model Refresh"` passes against the Docker test stack; docs/guide chapters 04, 05, 10, and 14 document the new features.

## Must-Haves

- Playwright spec `e2e/tests/24-tag-hierarchy/tag-hierarchy.spec.ts` tests hierarchical tag tree expansion and tag autocomplete in edit forms
- Playwright spec `e2e/tests/25-ops-log/ops-log.spec.ts` tests operations log page rendering and filter
- Playwright spec `e2e/tests/25-ops-log/model-refresh.spec.ts` tests refresh button click and ops log entry creation
- `docs/guide/04-workspace-interface.md` documents hierarchical tag tree under "By Tag" mode
- `docs/guide/05-working-with-objects.md` documents tag autocomplete in editing section
- `docs/guide/10-managing-mental-models.md` documents "Refreshing Model Artifacts" workflow
- `docs/guide/14-system-health-and-debugging.md` documents Operations Log under Debug Tools
- No new E2E spec for S01 query migration — existing `sparql-advanced.spec.ts` already covers it

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (E2E tests run against Docker test stack)
- Human/UAT required: no

## Verification

- `cd e2e && npx playwright test tests/24-tag-hierarchy/ --reporter=list` — passes
- `cd e2e && npx playwright test tests/25-ops-log/ --reporter=list` — passes
- `grep -l "hierarchical\|nested.*tag\|sub-folder" docs/guide/04-workspace-interface.md` — returns file
- `grep -l "autocomplete\|suggestions" docs/guide/05-working-with-objects.md` — returns file
- `grep -l "Refresh.*Artifact\|refresh_artifacts" docs/guide/10-managing-mental-models.md` — returns file
- `grep -l "Operations Log\|ops-log\|PROV-O" docs/guide/14-system-health-and-debugging.md` — returns file

## Observability / Diagnostics

- Runtime signals: Playwright test reporter output (pass/fail per test)
- Inspection surfaces: E2E test spec files; `npx playwright test --list` shows registered tests
- Failure visibility: Playwright trace files in `e2e/test-results/` on failure
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: all 5 implementation slices (S01–S05) — their UI endpoints, templates, and data-testid attributes
- New wiring introduced in this slice: `SEL.opsLog` selector group added to `e2e/helpers/selectors.ts`
- What remains before the milestone is truly usable end-to-end: nothing — S09 is the final slice

## Tasks

- [x] **T01: Playwright E2E tests for tag hierarchy and autocomplete** `est:45m`
  - Why: TAG-04 and TAG-05 need E2E coverage; tag tree hierarchy expansion and autocomplete are user-visible features with async htmx behavior that benefits from integration testing
  - Files: `e2e/tests/24-tag-hierarchy/tag-hierarchy.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Create spec with 3 tests: (1) hierarchical tag folders with `/` nesting show nested sub-folders when expanded, (2) tag count badges reflect total counts, (3) tag autocomplete dropdown appears in edit form when typing. Follow existing `tag-explorer.spec.ts` patterns. Consolidate into a single `test.describe` to minimize auth fixture usage (rate limit). Use `ownerPage` fixture only. Add `tagHierarchy` selector group to SEL. Use `waitForIdle` after all htmx interactions.
  - Verify: `cd e2e && npx playwright test tests/24-tag-hierarchy/ --reporter=list`
  - Done when: all 3 tests pass against the running test stack

- [x] **T02: Playwright E2E tests for operations log and model refresh** `est:45m`
  - Why: LOG-01 and MIG-01 need E2E coverage; ops log page and model refresh button are admin features that should be regression-tested
  - Files: `e2e/tests/25-ops-log/ops-log.spec.ts`, `e2e/tests/25-ops-log/model-refresh.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Create ops-log.spec.ts with 2 tests: (1) ops log page renders with table and at least one entry from model install, (2) activity type filter narrows results. Create model-refresh.spec.ts with 1 test: (1) refresh button exists, click triggers hx-confirm dialog, endpoint responds (success or known error). Register `ownerPage.on('dialog', ...)` BEFORE clicking refresh button. Add `opsLog` selector group to SEL. Account for the known basic-pkm JSON parsing error — assert button exists and response appears (success OR error message, not crash).
  - Verify: `cd e2e && npx playwright test tests/25-ops-log/ --reporter=list`
  - Done when: all 3 tests pass against the running test stack

- [x] **T03: User guide documentation updates for M005 features** `est:30m`
  - Why: four user-visible features (tag hierarchy, autocomplete, model refresh, ops log) need documentation in the user guide
  - Files: `docs/guide/04-workspace-interface.md`, `docs/guide/05-working-with-objects.md`, `docs/guide/10-managing-mental-models.md`, `docs/guide/14-system-health-and-debugging.md`
  - Do: (1) In chapter 04, expand the By Tag row in the Explorer Modes table and add a "Hierarchical Tags" subsection describing `/`-delimited nesting, folder icons, count badges, and lazy expansion. (2) In chapter 05, add a "Tag Autocomplete" paragraph after the existing tags mention at line 111, covering type-ahead suggestions, frequency ordering, and free-entry of new tags. (3) In chapter 10, add a "Refreshing Model Artifacts" section after the model removal section, covering what refresh does, when to use it, and what it preserves (seed data, user data). (4) In chapter 14, add an "Operations Log" subsection under Debug Tools (before Troubleshooting), covering access via Admin portal, what's logged, activity types, filter, pagination, and PROV-O vocabulary.
  - Verify: `for f in docs/guide/04-workspace-interface.md docs/guide/05-working-with-objects.md docs/guide/10-managing-mental-models.md docs/guide/14-system-health-and-debugging.md; do echo "--- $f ---"; head -5 "$f"; done` — files exist and have expected headers
  - Done when: all four guide chapters contain the new documentation sections with correct content

## Files Likely Touched

- `e2e/tests/24-tag-hierarchy/tag-hierarchy.spec.ts` (new)
- `e2e/tests/25-ops-log/ops-log.spec.ts` (new)
- `e2e/tests/25-ops-log/model-refresh.spec.ts` (new)
- `e2e/helpers/selectors.ts` (extend SEL with opsLog selectors)
- `docs/guide/04-workspace-interface.md` (expand By Tag mode)
- `docs/guide/05-working-with-objects.md` (add autocomplete)
- `docs/guide/10-managing-mental-models.md` (add refresh section)
- `docs/guide/14-system-health-and-debugging.md` (add ops log section)
s/guide/04-workspace-interface.md` (expand By Tag mode)
- `docs/guide/05-working-with-objects.md` (add autocomplete)
- `docs/guide/10-managing-mental-models.md` (add refresh section)
- `docs/guide/14-system-health-and-debugging.md` (add ops log section)
