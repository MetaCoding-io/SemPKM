# S04: E2E Tests & User Guide

**Goal:** Playwright E2E tests prove the full M030 acceptance criteria end-to-end against the Docker test stack, and the user guide documents data quality rules and the lint filter system.
**Demo:** Run `npx playwright test tests/10-lint-dashboard/lint-filters.spec.ts` — all tests pass, proving the pipeline fix, data quality rules, and filter CRUD work in production. Chapter 14 has new sections covering the 10 data quality rules, suppress/dismiss workflow, presets, and lint settings.

## Must-Haves

- Playwright E2E test covering: create objects that trigger data quality warnings → verify lint results via API → suppress a rule type → verify suppression works → dismiss a specific result → save/restore a named preset → manage filters via settings (clear all → results reappear)
- User guide Chapter 14 extended with data quality rules table, suppressing rules, dismissing results, presets, and lint settings documentation
- Glossary entries for Lint Suppression, Lint Dismissal, Lint Preset, Data Quality Rules

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (Docker test stack)
- Human/UAT required: no

## Verification

- `cd e2e && npx playwright test tests/10-lint-dashboard/lint-filters.spec.ts` — all tests pass against Docker test stack
- `wc -l docs/guide/14-system-health-and-debugging.md` — confirms substantial content added (should be >550 lines, up from 429)
- `grep -c "Lint Suppression\|Lint Dismissal\|Lint Preset\|Data Quality" docs/guide/appendix-d-glossary.md` — returns ≥4

## Integration Closure

- Upstream surfaces consumed: S01 pipeline fix (rules load, `advanced=True`), S02 data quality rules (10 SHACL-AF rules in model TTL files), S03 lint filter system (13 API endpoints, dismiss/suppress UI, preset selector, lint settings)
- New wiring introduced in this slice: none (E2E tests and docs only)
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Write E2E Playwright test for lint filter system** `est:1h30m`
  - Why: Primary verification deliverable proving M030 acceptance criteria end-to-end against the running Docker stack. Covers pipeline fix (rules fire), data quality rules (warnings appear), and full filter CRUD (suppress, dismiss, presets, settings management).
  - Files: `e2e/tests/10-lint-dashboard/lint-filters.spec.ts`
  - Do: Write a serial test suite exercising the full acceptance flow: (1) create objects triggering data quality warnings via API, (2) verify lint results contain expected warnings/infos via GET /api/lint/results, (3) suppress a rule type via POST /api/lint/suppress and verify results excluded, (4) dismiss a specific result via POST /api/lint/dismiss and verify exclusion, (5) save a preset via POST /api/lint/presets, clear all suppressions, apply preset to restore, (6) open lint settings in browser and verify management UI shows suppressions/dismissals/presets, (7) clear suppressions and verify results reappear, (8) cleanup. Use API-driven arrangement with selective browser verification for UI-visible outcomes. Follow the patterns from lint-dashboard.spec.ts (openBottomPanelTab helper, waitForWorkspace/waitForIdle, ownerSessionToken cookies).
  - Verify: `cd e2e && npx playwright test tests/10-lint-dashboard/lint-filters.spec.ts --reporter=list` — all tests pass
  - Done when: All E2E test phases pass against Docker test stack, proving pipeline fix + data quality rules + filter CRUD work end-to-end

- [x] **T02: Extend user guide with data quality rules and lint filter documentation** `est:45m`
  - Why: Documents the verified, working system for end users. Covers the 10 new data quality rules, suppress/dismiss workflows, preset management, and lint settings.
  - Files: `docs/guide/14-system-health-and-debugging.md`, `docs/guide/appendix-d-glossary.md`
  - Do: (1) Add new sections to Chapter 14 after the existing "Global Lint Dashboard" section: "Data Quality Rules" (table of 10 rules with severity, trigger, model, how to fix), "Suppressing Rule Types" (eye-off button, what happens, how to un-suppress), "Dismissing Individual Results" (× button on warnings/infos, not violations, when to use), "Filter Presets" (save current suppressions, apply/switch, manage), "Lint Settings" (manage suppressions/dismissals/presets, clear all, remove individual). (2) Add 4 glossary entries to appendix-d: Lint Suppression, Lint Dismissal, Lint Preset, Data Quality Rules. (3) Update the existing "Lint Dashboard" glossary entry to mention filtering. No new chapter needed — extending Chapter 14 means the three navigation files (README.md, index.html, guide.html) don't need chapter-level updates.
  - Verify: `wc -l docs/guide/14-system-health-and-debugging.md` shows >550 lines; `grep -c "Lint Suppression\|Lint Dismissal\|Lint Preset\|Data Quality" docs/guide/appendix-d-glossary.md` returns ≥4
  - Done when: Chapter 14 has all 5 new sections with accurate content matching the S03 implementation, glossary has 4 new entries

## Observability / Diagnostics

- **Runtime signals:** No new runtime signals — this slice adds E2E tests and documentation only.
- **Inspection surfaces:** `wc -l docs/guide/14-system-health-and-debugging.md` to verify Chapter 14 was extended. `grep "Lint Suppression\|Lint Dismissal\|Lint Preset\|Data Quality" docs/guide/appendix-d-glossary.md` to verify glossary entries exist. E2E test run output (`npx playwright test`) shows pass/fail for each lint filter scenario.
- **Failure visibility:** E2E test failures produce Playwright trace files in `e2e/test-results/`. Test reporter output shows which specific assertion failed and at which step.
- **Redaction:** No secrets involved — tests use session cookies obtained from the auth fixture which reads a setup token from the Docker container.

## Files Likely Touched

- `e2e/tests/10-lint-dashboard/lint-filters.spec.ts` (new)
- `docs/guide/14-system-health-and-debugging.md`
- `docs/guide/appendix-d-glossary.md`
