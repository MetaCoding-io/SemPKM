---
id: T02
parent: S04
milestone: M024
provides:
  - Playwright E2E spec for Monday.com Sync full lifecycle (13 phases)
  - mondaySync selector block in shared selectors.ts
key_files:
  - e2e/tests/42-monday-sync/monday-sync.spec.ts
  - e2e/helpers/selectors.ts
key_decisions:
  - Used hx-post attribute selectors (form[hx-post*="save-column-mapping"]) for column/label mapping form submit buttons since these forms lack CSS class names — matches actual HTML structure from templates
  - Used .filter({ hasText }) for Configure Columns/Labels buttons rather than positional selectors, since connect_status.html conditionally renders the Labels button only after columns are configured
patterns_established:
  - Monday.com E2E test adds two extra phases (6: column mapping, 7: label mapping) beyond the Jira 12-phase pattern — these phases iterate select dropdowns and pick first non-empty options
observability_surfaces:
  - Each of the 13 phases has a named comment block for Playwright failure diagnosis
  - SPARQL verification in Phase 10 confirms RDF objects actually created in triplestore
  - Playwright screenshots/traces captured on failure in test-results/ directory
duration: 25m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Playwright E2E spec + selectors

**Created 372-line Playwright E2E spec for Monday.com Sync with 13-phase lifecycle and mondaySync selector block in selectors.ts**

## What Happened

Added the `mondaySync` selector block (14 selectors) to `e2e/helpers/selectors.ts` after the existing `jiraSync` block. Selectors match the actual HTML from the Monday.com Sync frontend templates — using `#monday-token` for the single API token input, `.board-checkbox-item` for board selection, `form[hx-post*="save-column-mapping"]` for the column mapping form, and `form[hx-post*="save-label-mapping"]` for the label mapping form.

Created `e2e/tests/42-monday-sync/monday-sync.spec.ts` (372 lines) following the Jira E2E spec's structure but adapted for Monday.com's unique features:
- **Single API token** connection (Phase 4) instead of Jira's 3-field email+token+siteURL form
- **Column mapping phase** (Phase 6): clicks "Configure Columns" link, waits for htmx-loaded form with property-to-column select dropdowns, picks first non-empty option for each, saves
- **Label mapping phase** (Phase 7): clicks "Configure Labels" link (only visible after columns are configured), maps status/priority labels via select dropdowns, saves
- All 13 phases: cleanup → install basic-pkm → install monday-sync → workspace open → connect → board select → configure columns → configure labels → sync direction → sync now → SPARQL verify → admin verify → cleanup uninstall

## Verification

1. File exists: `e2e/tests/42-monday-sync/monday-sync.spec.ts` — ✅
2. TypeScript syntax parse via `ts.createSourceFile()` — ✅ (4 top-level statements)
3. `grep -c 'mondaySync' e2e/helpers/selectors.ts` → 1 — ✅
4. `grep -c 'Phase [0-9]' monday-sync.spec.ts` → 13 — ✅ (all phases present)
5. No TypeScript errors specific to our file (tsc --noEmit shows no 42-monday-sync errors) — ✅
6. Mock selftest still passes: 12/12 checks ✓ — ✅
7. docker-compose.test.yml validates cleanly — ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f e2e/tests/42-monday-sync/monday-sync.spec.ts` | 0 | ✅ pass | <1s |
| 2 | `node -e "ts.createSourceFile(…)"` (TypeScript parse) | 0 | ✅ pass | <1s |
| 3 | `grep -c 'mondaySync' e2e/helpers/selectors.ts` | 0 | ✅ pass | <1s |
| 4 | `grep -c 'Phase [0-9]' monday-sync.spec.ts` → 13 | 0 | ✅ pass | <1s |
| 5 | `npx tsc --noEmit \| grep 42-monday-sync` → no output | 0 | ✅ pass | 3s |
| 6 | `python3 e2e/mock-monday-api/server.py --selftest` | 0 | ✅ pass | <1s |
| 7 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass | <1s |
| 8 | Failure-path: `selftest \| grep -c '✗'` → 0 | 0 | ✅ pass | <1s |

## Diagnostics

- **Playwright test run**: `npx playwright test e2e/tests/42-monday-sync/monday-sync.spec.ts` — requires full Docker test stack running
- **Phase failure location**: Each phase has `// Phase N —` comment; Playwright error report includes line number mapping to exact phase
- **Selector debugging**: All 14 `SEL.mondaySync.*` selectors are derived from actual template HTML; if a selector fails, compare against the template file listed in the selector's comment
- **SPARQL verification phase**: Phase 10 independently verifies Task creation via triplestore query — if sync appears to succeed but SPARQL fails, the sync engine is not persisting objects correctly

## Deviations

- Selectors for column/label mapping submit buttons use `form[hx-post*="save-column-mapping"]` and `form[hx-post*="save-label-mapping"]` instead of the plan's `.column-mapping-form` and `.label-mapping-form` class selectors, because the actual templates don't have those CSS classes — they use htmx `hx-post` attributes on bare `<form>` elements
- Configure Labels button uses `.filter({ hasText: /Configure Labels/i })` instead of `a.btn-configure-labels` because the template uses plain `a.btn.btn-sm` without a specific class differentiating it from Configure Columns

## Known Issues

- Full E2E test requires Docker stack and cannot be verified in the worktree without running `docker compose -f docker-compose.test.yml up`
- Other test files in the e2e/ directory have pre-existing TypeScript errors (unrelated to this task)

## Files Created/Modified

- `e2e/tests/42-monday-sync/monday-sync.spec.ts` — New 372-line Playwright E2E spec with 13-phase lifecycle test
- `e2e/helpers/selectors.ts` — Added `mondaySync` selector block (14 selectors) for Monday.com Sync UI elements
- `.gsd/milestones/M024/slices/S04/S04-PLAN.md` — Marked T02 done, added failure-path diagnostic verification step
- `.gsd/milestones/M024/slices/S04/tasks/T02-PLAN.md` — Added Observability Impact section
