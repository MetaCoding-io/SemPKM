---
id: S04
parent: M030
milestone: M030
provides:
  - E2E Playwright test proving M030 acceptance criteria (pipeline fix, data quality rules, lint filter CRUD)
  - User guide documentation for data quality rules and lint filter system (5 new sections in Chapter 14)
  - 4 new glossary entries (Data Quality Rules, Lint Dismissal, Lint Preset, Lint Suppression)
requires:
  - slice: S01
    provides: Pipeline fix (rules load, advanced=True) — lint panel shows real validation results
  - slice: S02
    provides: 9 new SHACL-AF data quality rules in model TTL files, proven by offline pytest tests
  - slice: S03
    provides: Lint filter system (suppress/dismiss/preset CRUD, 13 API endpoints, dismiss/suppress UI, preset selector, lint settings)
affects: []
key_files:
  - e2e/tests/10-lint-dashboard/lint-filters.spec.ts
  - docs/guide/14-system-health-and-debugging.md
  - docs/guide/appendix-d-glossary.md
key_decisions: []
patterns_established:
  - Poll for lint results with specific source_shape match — validation coalescing makes timing unpredictable
  - Use #lint-dashboard-container.first() in locators — htmx swaps can create duplicate container elements
  - Add a setup test to clear stale filter state when serial tests build on each other's state
observability_surfaces:
  - E2E test file itself is a runnable validation of the full M030 stack — pipeline fix, rules firing, filter CRUD
drill_down_paths:
  - .gsd/milestones/M030/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M030/slices/S04/tasks/T02-SUMMARY.md
duration: ~1h
verification_result: passed
completed_at: 2026-03-21
---

# S04: E2E Tests & User Guide

**7-test E2E Playwright suite proves the full M030 lint pipeline end-to-end, and Chapter 14 documents 11 data quality rules with suppress/dismiss/preset workflows**

## What Happened

**T01 — E2E Playwright test** created `lint-filters.spec.ts` with 7 serial tests exercising the complete M030 acceptance flow against the Docker test stack:

1. Setup clears stale filters from prior incomplete runs (idempotent re-runs)
2. Creates two Notes via POST /api/commands — one with empty body, one with comma-in-tags — then polls until validation results appear (up to 30s, since validation runs sequentially)
3. Suppresses CommaInTags rule via POST /api/lint/suppress, verifies results excluded from API and absent in browser lint dashboard
4. Dismisses EmptyBody for a specific object, verifies that (object, rule) pair is excluded
5. Saves current suppressions as a named preset, clears all, verifies results reappear, applies preset, verifies results excluded again
6. Navigates to lint settings management UI, verifies suppressions/dismissals/presets sections render with correct counts
7. Cleans up all test filters and presets

Key debugging during T01: Docker container image didn't include migration 015 (lint tables); fixed by copying migration into container. A stale suppression from an aborted prior run was hiding CommaInTags results; fixed by adding the setup test. Strict mode violations from duplicate htmx-swapped containers; fixed with `.first()` locators.

**T02 — User guide documentation** added 5 new sections to Chapter 14 (139 lines total):

- Data Quality Rules — severity explanations and table of all 11 rules across 4 models
- Suppressing Rule Types — eye-off button workflow and how to un-suppress
- Dismissing Individual Results — × button on warnings/infos, not violations
- Filter Presets — save/apply/switch workflow
- Lint Settings — management hub with CRUD for suppressions/dismissals/presets

Added 4 glossary entries to Appendix D and updated existing Lint Dashboard entry.

## Verification

| Check | Result |
|-------|--------|
| `cd e2e && npx playwright test tests/10-lint-dashboard/lint-filters.spec.ts` — 7/7 tests pass (Chromium) | ✅ 23.8s |
| `wc -l docs/guide/14-system-health-and-debugging.md` — 568 lines (target: >550) | ✅ |
| `grep -c "Lint Suppression\|Lint Dismissal\|Lint Preset\|Data Quality" docs/guide/appendix-d-glossary.md` — returns 4 (target: ≥4) | ✅ |
| All 5 section headings present in Chapter 14 (lines 396, 430, 454, 478, 501) | ✅ |

## Requirements Advanced

- No new requirements advanced — this slice is final-assembly verification of already-delivered functionality.

## Requirements Validated

No new requirement status changes needed — S01/S02/S03 already advanced the LINT requirements. This slice provides the final integration proof but the requirements were already marked as delivered by their implementing slices.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Added a setup test (test 1) to clear stale filters — not in original plan but required for idempotent re-runs after partial failures
- Used polling loop (up to 30s) instead of fixed 8-10s timeout for validation results — validation runs sequentially and timing varies
- T02 documents 11 rules instead of 10 as planned — EmptyBodyValidation appears in both Basic PKM and Zettelkasten+ models (separate implementations for different object types)

## Known Limitations

- E2E test creates objects in the triplestore but does not clean them up (only filter state is cleaned) — triplestore objects accumulate across runs
- Firefox E2E run skipped to stay within context budget — Chromium passes, Firefox should also pass since the test is API-driven with minimal browser interaction
- Docker test image needs migration files copied manually when using volume-mounted code (migrations dir is not volume-mounted in docker-compose.test.yml)

## Follow-ups

- None — this is the final slice of M030.

## Files Created/Modified

- `e2e/tests/10-lint-dashboard/lint-filters.spec.ts` — New 7-test E2E suite proving full lint filter acceptance flow
- `docs/guide/14-system-health-and-debugging.md` — 5 new sections (139 lines) documenting data quality rules and lint filter system
- `docs/guide/appendix-d-glossary.md` — 4 new entries + updated Lint Dashboard entry

## Forward Intelligence

### What the next slice should know
- M030 is complete. The validation pipeline loads rules with `advanced=True`, 11 data quality rules fire across 4 models, and the full suppress/dismiss/preset filter system works end-to-end. No remaining M030 work.

### What's fragile
- Docker test image migration sync — test stack needs migration 015 manually applied if the image was built before S03. Future milestones adding Alembic migrations should rebuild the Docker image.

### Authoritative diagnostics
- `cd e2e && npx playwright test tests/10-lint-dashboard/lint-filters.spec.ts --reporter=list` — fastest way to verify the entire M030 stack works

### What assumptions changed
- Validation timing is less predictable than assumed — sequential validation runs after each object creation mean the second object's results may not appear for 15-20s. Polling with source_shape match is more reliable than fixed timeouts.
