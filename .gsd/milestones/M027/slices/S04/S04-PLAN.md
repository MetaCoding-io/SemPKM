# S04: E2E Tests + User Guide

**Goal:** Playwright E2E test exercises the full Notion import wizard flow against Docker test stack, and user guide chapter documents the complete workflow.
**Demo:** Run `cd e2e && npx playwright test tests/60-notion-import/notion-import.spec.ts --project=chromium` and the test passes. Open `docs/guide/39-notion-import.md` and it has a complete 7-step wizard walkthrough. All three navigation files reference the new chapter.

## Must-Haves

- Synthetic Notion export ZIP fixture at `e2e/fixtures/notion-export.zip` with 2 databases, cross-DB relations, and standalone pages — filenames use exactly 32 hex char Notion IDs
- Playwright E2E spec at `e2e/tests/60-notion-import/notion-import.spec.ts` exercising upload → scan → type mapping → property mapping → relation mapping → preview → execute → summary
- E2E test uses `test.describe.serial` and verifies import creates objects (stat card count > 0)
- User guide chapter at `docs/guide/39-notion-import.md` following Chapter 24 pattern with 7 wizard steps
- Navigation updates in all three files: `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`
- Chapter 38 "Next" link updated to point to Chapter 39; Chapter 39 "Next" points to Appendix A
- Glossary entry for "Notion Import" in `docs/guide/appendix-d-glossary.md`
- All 69 existing Notion unit tests still pass (zero regressions)

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (E2E test runs against Docker stack)
- Human/UAT required: no

## Observability / Diagnostics

- **E2E test traces**: Playwright traces are captured on failure in `e2e/test-results/` — contains screenshots, DOM snapshots, and network logs for each wizard step
- **Import progress SSE stream**: The execute step emits `import_progress`, `import_complete`, and `import_error` SSE events at `/browser/notion/{import_id}/execute/stream` — inspectable via browser DevTools EventSource panel or `curl -N`
- **Import summary stat cards**: After import completes, the summary page shows Created/Edges/Skipped/Duration as `.import-stat-card` elements — the Created count is the primary success signal
- **Scanner warnings**: Scan results surface any fixture issues (malformed CSV, missing IDs) in the Warnings section of scan results
- **Failure visibility**: If the E2E test fails, Playwright captures a screenshot + trace at the failing step; the test report shows which wizard step failed and the DOM state at that point
- **Redaction**: No user secrets in fixtures — all data is synthetic test content

## Verification

- `cd e2e && npx playwright test tests/60-notion-import/notion-import.spec.ts --project=chromium` — passes
- `cd backend && python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py tests/test_notion_executor.py -v` — 69/69 pass (regression check)
- `test -f docs/guide/39-notion-import.md` — exists
- `grep "39-notion-import" docs/guide/README.md` — returns entry
- `grep "39-notion-import" docs/guide/index.html` — returns entry
- `grep "39-notion-import" backend/app/templates/guide.html` — returns entry
- `grep "Notion Import" docs/guide/appendix-d-glossary.md` — returns entry
- `grep "Chapter 39" docs/guide/38-hosted-demo.md` — navigation link exists
- `grep -rn "^<<<<<<< " e2e/tests/60-notion-import/ docs/guide/39-notion-import.md` — zero conflict markers
- `cd e2e && npx playwright test tests/60-notion-import/notion-import.spec.ts --project=chromium 2>&1 | grep -c 'FAIL\|Error'` — returns 0 (no failures in diagnostic output)

## Integration Closure

- Upstream surfaces consumed: Complete wizard flow from S01+S02+S03 (upload, scan, mapping, execute endpoints), Docker test stack, auth fixture
- New wiring introduced in this slice: none (test + docs only)
- What remains before the milestone is truly usable end-to-end: nothing — this is the terminal slice

## Tasks

- [x] **T01: Create Notion export fixture ZIP and Playwright E2E test** `est:45m`
  - Why: Proves the full wizard flow works end-to-end against the real Docker stack, validating NOTION-01 through NOTION-03
  - Files: `e2e/fixtures/notion-export.zip`, `e2e/tests/60-notion-import/notion-import.spec.ts`
  - Do: Build a synthetic Notion export ZIP with 2 databases (Tasks + Projects), cross-DB relation column, and 1 standalone page — all filenames with exactly 32 hex char IDs. Write the Playwright spec following `batch-import.spec.ts` pattern with `test.describe.serial`: (1) full flow test (upload → scan → type map → property map → relation map → preview → import → summary with stat card assertions), (2) verify objects in workspace, (3) cleanup via discard
  - Verify: `cd e2e && npx playwright test tests/60-notion-import/notion-import.spec.ts --project=chromium` passes
  - Done when: E2E test passes against Docker test stack with all wizard steps exercised and import summary showing created count > 0

- [x] **T02: Write user guide chapter and update navigation files** `est:30m`
  - Why: Documents the Notion import workflow for users and completes the milestone's documentation requirement
  - Files: `docs/guide/39-notion-import.md`, `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`, `docs/guide/38-hosted-demo.md`, `docs/guide/appendix-d-glossary.md`
  - Do: Write Chapter 39 following Chapter 24 (Obsidian Onboarding) as template — Prerequisites, Upload, Scan Results, Type Mapping, Property Mapping, Relation Mapping, Preview, Import, concept mapping table, troubleshooting. Update all three navigation files with Ch 39 entry. Update Ch 38 "Next" link to Ch 39. Add "Notion Import" glossary entry
  - Verify: All six navigation grep checks pass; markdown is well-formed; Chapter 38→39→Appendix A chain is connected
  - Done when: `docs/guide/39-notion-import.md` exists with complete 7-step guide, all three navigation files updated, glossary entry added

## Files Likely Touched

- `e2e/fixtures/notion-export.zip`
- `e2e/tests/60-notion-import/notion-import.spec.ts`
- `docs/guide/39-notion-import.md`
- `docs/guide/README.md`
- `docs/guide/index.html`
- `backend/app/templates/guide.html`
- `docs/guide/38-hosted-demo.md`
- `docs/guide/appendix-d-glossary.md`
