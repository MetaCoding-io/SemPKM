# S04 — Research: E2E Tests & User Guide

**Date:** 2026-03-20
**Status:** Complete

## Summary

S04 is straightforward: write a Playwright E2E test spec that exercises the full lint filter system against the Docker test stack, and extend the user guide to document lint filtering (suppress, dismiss, presets) and the new data quality rules.

Both deliverables follow well-established patterns in this codebase. The E2E test follows the `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` and `e2e/tests/04-validation/lint-panel.spec.ts` patterns — API-driven test arrangement via `ownerSessionToken` cookies, `waitForWorkspace`/`waitForIdle` helpers, and htmx-aware assertions. The user guide extends Chapter 14 ("System Health and Debugging") which already documents the lint dashboard basics, plus updates the three navigation files (README.md, index.html, guide.html) per the knowledge base rule.

No new technologies, no risky integrations, no ambiguous requirements.

## Recommendation

Two tasks, sequential:

1. **T01: E2E Playwright test** — Write `e2e/tests/10-lint-dashboard/lint-filters.spec.ts` covering the acceptance criteria from M030-CONTEXT.md: create objects triggering data quality warnings → suppress a rule type → verify disappearance → dismiss specific result → verify dismissal → save preset → apply preset → manage via settings (clear suppressions → results reappear). Uses API-driven arrangement for speed and reliability.

2. **T02: User guide updates** — Extend `docs/guide/14-system-health-and-debugging.md` with new sections covering data quality rules, suppressing rules, dismissing individual results, preset management, and lint settings. Update navigation in all three files (README.md, index.html, guide.html). Add glossary entries in appendix-d.

## Implementation Landscape

### Key Files

**E2E test (T01):**

- `e2e/tests/10-lint-dashboard/lint-filters.spec.ts` — **new file.** The E2E test spec covering lint filter CRUD and UI interactions. Belongs in the existing `10-lint-dashboard/` directory alongside `lint-dashboard.spec.ts`.
- `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` — existing lint dashboard E2E tests. Reference for `openBottomPanelTab()` helper, `waitForWorkspace`/`waitForIdle` imports, and assertion patterns.
- `e2e/tests/04-validation/lint-panel.spec.ts` — existing lint panel E2E tests. Reference for per-object lint panel assertions and API-driven object creation.
- `e2e/fixtures/auth.ts` — authentication fixtures providing `ownerPage`, `ownerSessionToken`, `ownerRequest`, `BASE_URL`. The test will use `ownerRequest` for API calls and `ownerPage` for UI verification.
- `e2e/fixtures/seed-data.ts` — seed data constants (SEED, TYPES). The test will create objects via API using `TYPES.Note` for data quality rule triggers.
- `e2e/helpers/wait-for.ts` — `waitForWorkspace()`, `waitForIdle()` helpers for htmx settling.
- `e2e/helpers/selectors.ts` — `SEL.lint.panel` and `SEL.lint.violation` selectors. May need extension for new filter UI elements.

**Filter API endpoints (hit by E2E test):**

- `POST /api/lint/suppress` — body: `{ rule_source_iri: string }` → 201
- `DELETE /api/lint/suppress/{id}` → 200
- `GET /api/lint/suppressions` → `SuppressionResponse[]`
- `DELETE /api/lint/suppressions` → `{ deleted: int }` (clear all)
- `POST /api/lint/dismiss` — body: `{ object_iri: string, rule_source_iri: string }` → 201
- `DELETE /api/lint/dismiss/{id}` → 200
- `GET /api/lint/dismissals` → `DismissalResponse[]`
- `DELETE /api/lint/dismissals` → `{ deleted: int }`
- `POST /api/lint/presets` — body: `{ name: string, suppressed_rules: string[] }` → 201
- `GET /api/lint/presets` → `PresetResponse[]`
- `PUT /api/lint/presets/{id}` — body: `{ name?: string, suppressed_rules?: string[] }`
- `DELETE /api/lint/presets/{id}` → 200
- `POST /api/lint/presets/{id}/apply` → 200

**Lint results API (for verifying filtering works):**

- `GET /api/lint/results?page=1` → `{ results: LintResultItem[], total: int, ... }` — each `LintResultItem` has `source_shape: string | null` which is the stable identifier for suppress/dismiss operations.

**User guide (T02):**

- `docs/guide/14-system-health-and-debugging.md` — extend the existing "Global Lint Dashboard" section (~line 341) with new subsections for data quality rules, suppress/dismiss, presets, and lint settings. This chapter already documents the dashboard basics, filter toolbar, and understanding violations.
- `docs/guide/README.md` — no new chapter entry needed (Chapter 14 title unchanged). But if the section is substantial enough to warrant a standalone chapter (39), add it here.
- `docs/guide/index.html` — same: update only if adding a new chapter.
- `backend/app/templates/guide.html` — same: update only if adding a new chapter.
- `docs/guide/appendix-d-glossary.md` — add glossary entries: Lint Suppression, Lint Dismissal, Lint Preset, Data Quality Rules.

### E2E Test Strategy

The test should be primarily API-driven for reliability (htmx UI timing is fragile) with selective browser verification for UI-visible outcomes. Pattern:

1. **Arrange** — Create objects via `POST /api/commands` that trigger specific data quality rules (e.g., Note with comma-in-tags, Note with no body). Wait for async validation (5s timeout).
2. **Verify baseline** — `GET /api/lint/results` confirms expected warnings/infos are present with known `source_shape` values.
3. **Suppress** — `POST /api/lint/suppress` with a `source_shape` from step 2. Then `GET /api/lint/results` confirms results for that shape are excluded. Browser: open lint dashboard, verify suppressed results are gone and "N rules suppressed" badge shows.
4. **Dismiss** — `POST /api/lint/dismiss` with a specific `(object_iri, source_shape)`. Then `GET /api/lint/results` confirms that specific result excluded but others for the same rule remain.
5. **Preset** — `POST /api/lint/presets` to save current suppressions. `DELETE /api/lint/suppressions` to clear all. `POST /api/lint/presets/{id}/apply` to restore. Verify results match pre-clear state.
6. **Settings** — Browser: navigate to lint settings via "Manage Filters" link, verify suppressions/dismissals/presets listed, clear all suppressions, verify results reappear.
7. **Cleanup** — `DELETE /api/lint/suppressions`, `DELETE /api/lint/dismissals`, delete created presets.

**Key source_shape IRIs to target:**
- `urn:sempkm:model:basic-pkm:EmptyBodyValidationShape` — Info, triggers on Notes without body
- `urn:sempkm:model:basic-pkm:CommaInTagsValidationShape` — Warning, triggers on tags containing commas
- `urn:sempkm:model:basic-pkm:TitlelessObjectValidationShape` — Warning, triggers on objects with no title

The test should create a Note with `properties: { "dcterms:title": "Test Note" }` (no body → empty body info) and a Note with tags containing commas → comma-in-tags warning.

### User Guide Content Structure

Extend Chapter 14 "Global Lint Dashboard" section with:

1. **Data Quality Rules** — Table of the 9 (+1) rules with severity, what they detect, which models they apply to, and how to fix.
2. **Suppressing Rule Types** — How to hide all results for a specific rule (eye-off button), what happens, how to un-suppress.
3. **Dismissing Individual Results** — How to dismiss a specific finding on one object (× button), when to use it.
4. **Filter Presets** — Save current suppressions as a named preset, switch between presets, apply a preset.
5. **Managing Filters** — Lint Settings page for viewing/removing suppressions, dismissals, and presets. "Clear All" actions.

### Build Order

1. **T01: E2E test first.** The test proves the M030 acceptance criteria end-to-end against the Docker stack. This is the primary verification deliverable. If tests reveal issues with the S01-S03 implementation, they need fixing before docs are written.
2. **T02: User guide second.** Documents the verified, working system. Depends on T01 to confirm everything works as expected.

### Verification Approach

**T01:** `cd e2e && npx playwright test tests/10-lint-dashboard/lint-filters.spec.ts` against the Docker test stack. All test phases pass. The Docker stack needs to be running with the M030 worktree code synced to the main tree (volume mounts resolve from the main tree per KNOWLEDGE.md).

**T02:** `cat docs/guide/14-system-health-and-debugging.md | wc -l` confirms content was added. Verify all 4 glossary entries present in appendix-d. Verify cross-references are correct.

## Constraints

- Docker test stack must be running from the main tree with M030 code synced (per KNOWLEDGE.md: "E2E tests: Docker stack must run from main tree for auth fixture").
- Async validation has a ~5s delay after object creation — tests must wait for validation to complete before asserting on lint results.
- The `source_shape` field is always populated on `LintResultItem` (changed in S03 from optional/detail-only to always-present) — E2E tests can rely on it.
- Lint filter endpoints are at `/api/lint/` (not `/lint/`) — mounted under the API router prefix.
- User guide has THREE files that must stay in sync: `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html` (KNOWLEDGE.md rule). Since we're extending Chapter 14 rather than adding a new chapter, only the glossary additions need syncing.

## Common Pitfalls

- **htmx swap timing** — The lint dashboard loads via `hx-trigger="revealed"` when its panel tab becomes visible. After opening the bottom panel tab, use `waitForIdle(page)` + a generous timeout before asserting on content. The existing `lint-dashboard.spec.ts` uses `waitForTimeout(3000)` after switching tabs.
- **Dismiss buttons only on warnings/infos** — Per D283, violations don't get dismiss buttons. Tests asserting dismiss UI must target warning/info results, not violations.
- **Over-fetch pagination** — When filters are active, the API returns filtered results with adjusted pagination. The `total` count in the response reflects the filtered total, not the raw SPARQL count.
- **Stale validation results** — If the Docker stack has been running for a while, lint results reflect the last validation run. Creating a new object triggers a new validation run, but old objects' results remain until manually re-validated or re-edited.
