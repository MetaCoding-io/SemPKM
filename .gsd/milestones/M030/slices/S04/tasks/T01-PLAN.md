---
estimated_steps: 8
estimated_files: 1
---

# T01: Write E2E Playwright test for lint filter system

**Slice:** S04 — E2E Tests & User Guide
**Milestone:** M030

## Description

Write `e2e/tests/10-lint-dashboard/lint-filters.spec.ts` — a Playwright E2E test spec that exercises the full M030 acceptance criteria against the Docker test stack. The test proves three layers work together: (1) the validation pipeline fix from S01 (rules fire in production), (2) the 10 data quality rules from S02 (warnings/infos appear for real objects), and (3) the lint filter system from S03 (suppress, dismiss, presets, settings management).

The test is primarily API-driven for reliability — htmx UI timing is fragile. API calls arrange data and verify filtering; browser interactions verify only UI-visible outcomes (lint dashboard rendering, settings management page).

**Key knowledge from KNOWLEDGE.md:**
- Docker test stack must run from main tree for auth fixture (worktree code must be synced first)
- Async validation has ~5s delay after object creation — tests must wait
- `source_shape` is always populated on `LintResultItem` (changed in S03)
- Workspace explorer sections start collapsed — tests must click section headers to expand
- The lint dashboard loads via `hx-trigger="revealed"` when its panel tab becomes visible

## Steps

1. **Read existing patterns.** Study `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` for the `openBottomPanelTab()` helper, imports, and assertion patterns. Study `e2e/fixtures/auth.ts` and `e2e/fixtures/seed-data.ts` for available fixtures (`ownerPage`, `ownerSessionToken`, `ownerRequest`, `BASE_URL`, `SEED`, `TYPES`).

2. **Create the test file** at `e2e/tests/10-lint-dashboard/lint-filters.spec.ts`. Import from fixtures and helpers. Configure `test.describe.configure({ mode: 'serial' })` since tests build on each other's state.

3. **Test: Create objects triggering data quality warnings.** Use `ownerRequest` (or `ownerPage.context().request`) to `POST /api/commands` creating:
   - A Note with title but no body → triggers `EmptyBodyValidationShape` (Info)
   - A Note with comma-in-tags → triggers `CommaInTagsValidationShape` (Warning)
   
   Wait 8-10 seconds for async validation, then `GET /api/lint/results?page=1` and verify results contain entries with matching `source_shape` values (`urn:sempkm:model:basic-pkm:EmptyBodyValidationShape`, `urn:sempkm:model:basic-pkm:CommaInTagsValidationShape`). Store the created object IRIs and identified `source_shape` values for later tests.

4. **Test: Suppress a rule type via API and verify filtering.** `POST /api/lint/suppress` with `{ rule_source_iri: "<CommaInTagsValidationShape IRI>" }`. Then `GET /api/lint/results?page=1` and verify comma-in-tags results are excluded from response. Also verify the suppression appears in `GET /api/lint/suppressions`. Open lint dashboard in browser and verify suppressed results are absent (use `openBottomPanelTab` helper + text assertion).

5. **Test: Dismiss a specific result via API and verify filtering.** `POST /api/lint/dismiss` with `{ object_iri: "<created note IRI>", rule_source_iri: "<EmptyBodyValidationShape IRI>" }`. Then `GET /api/lint/results?page=1` and verify that specific (object+rule) pair is excluded but other results for the same rule on different objects remain.

6. **Test: Preset save/apply cycle.** `POST /api/lint/presets` to save current suppressions as a named preset (e.g., "Test Preset"). Verify `GET /api/lint/presets` returns it. `DELETE /api/lint/suppressions` to clear all suppressions. Verify `GET /api/lint/results` now includes previously-suppressed results. `POST /api/lint/presets/{id}/apply` to restore. Verify `GET /api/lint/results` excludes suppressed results again.

7. **Test: Lint settings management in browser.** Navigate to lint dashboard, click "Manage Filters" link, verify the lint settings section renders with suppressions, dismissals, and presets listed. Clear all suppressions from settings. Verify suppressions are empty. Navigate back to dashboard.

8. **Test: Cleanup.** `DELETE /api/lint/suppressions`, `DELETE /api/lint/dismissals`, delete created presets via `DELETE /api/lint/presets/{id}`.

## Must-Haves

- [ ] Test creates objects via POST /api/commands that trigger at least 2 different data quality rules
- [ ] Test waits for async validation (≥5s) before asserting on lint results
- [ ] Test verifies suppress excludes results for that rule from GET /api/lint/results
- [ ] Test verifies dismiss excludes specific (object, rule) pair from GET /api/lint/results
- [ ] Test verifies preset save → clear → apply cycle restores filter state
- [ ] Test verifies lint settings management section renders with correct content
- [ ] All API calls use ownerSessionToken cookie for auth
- [ ] Tests are serial (mode: 'serial') since they build state incrementally

## Verification

- `cd e2e && npx playwright test tests/10-lint-dashboard/lint-filters.spec.ts --reporter=list` — all tests pass
- The Docker test stack must be running with M030 code synced to the main tree

## Inputs

- `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` — reference for `openBottomPanelTab()` helper pattern, imports, assertion style
- `e2e/fixtures/auth.ts` — provides `ownerPage`, `ownerSessionToken`, `ownerRequest`, `BASE_URL`
- `e2e/fixtures/seed-data.ts` — provides `SEED` and `TYPES` constants (e.g., `TYPES.Note`)
- `e2e/helpers/wait-for.ts` — provides `waitForWorkspace()`, `waitForIdle()`
- S03 summary — API endpoints: `POST /api/lint/suppress`, `DELETE /api/lint/suppress/{id}`, `GET /api/lint/suppressions`, `DELETE /api/lint/suppressions`, `POST /api/lint/dismiss`, `DELETE /api/lint/dismiss/{id}`, `GET /api/lint/dismissals`, `DELETE /api/lint/dismissals`, `POST /api/lint/presets`, `GET /api/lint/presets`, `PUT /api/lint/presets/{id}`, `DELETE /api/lint/presets/{id}`, `POST /api/lint/presets/{id}/apply`
- S03 summary — Pydantic models: `SuppressRequest { rule_source_iri }`, `DismissRequest { object_iri, rule_source_iri }`, `PresetCreateRequest { name, suppressed_rules[] }`
- S03 summary — `source_shape` is always populated on `LintResultItem` (not just detail mode)
- S02 summary — key source_shape IRIs: `urn:sempkm:model:basic-pkm:EmptyBodyValidationShape` (Info), `urn:sempkm:model:basic-pkm:CommaInTagsValidationShape` (Warning), `urn:sempkm:model:basic-pkm:TitlelessObjectValidationShape` (Warning)

## Expected Output

- `e2e/tests/10-lint-dashboard/lint-filters.spec.ts` — new E2E test file with 5-7 serial tests covering the full lint filter acceptance flow
