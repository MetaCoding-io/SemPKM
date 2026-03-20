---
estimated_steps: 5
estimated_files: 2
---

# T01: Create Notion export fixture ZIP and Playwright E2E test

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M027

## Description

Build a synthetic Notion export ZIP fixture and write a Playwright E2E spec that exercises the full 7-step Notion import wizard against the Docker test stack. This validates NOTION-01 (ZIP import), NOTION-02 (database→type mapping), and NOTION-03 (relation→edge resolution) end-to-end.

The E2E test follows the established `batch-import.spec.ts` pattern from the Obsidian importer — `test.describe.serial` with three sequential tests: full flow, verify objects, and cleanup.

**Relevant skill:** `test` (E2E testing patterns)

## Steps

1. **Create the fixture ZIP** — Build a directory structure matching Notion's export format:
   ```
   My Workspace abc123abc123abc123abc123abc123ab/
   ├── Tasks aaaaaaaabbbbbbbbccccccccdddddddd/
   │   ├── Tasks aaaaaaaabbbbbbbbccccccccdddddddd.csv
   │   ├── Design Homepage 11111111222222223333333344444444.md
   │   └── Fix Login Bug 55555555666666667777777788888888.md
   ├── Projects eeeeeeeeffffffffaaaaaaaabbbbbbbb/
   │   ├── Projects eeeeeeeeffffffffaaaaaaaabbbbbbbb.csv
   │   ├── Website Redesign ccccccccddddddddeeeeeeeeffffffff.md
   │   └── Mobile App 1111111122222222aaaaaaaabbbbbbbb.md
   └── Meeting Notes aabbccddaabbccddaabbccddaabbccdd.md
   ```

   **Tasks CSV columns:** `Name,Status,Priority,Due Date,Project` — the "Project" column contains values like "Website Redesign, Mobile App" matching titles in the Projects database. This exercises cross-DB relation detection (>80% overlap).

   **Projects CSV columns:** `Name,Description,Start Date,Status`

   **CRITICAL:** All Notion IDs must be exactly 32 hex characters. The scanner's `_strip_notion_id` regex requires this — `r'\s+[0-9a-f]{32}`. Use lowercase hex only.

   **Body markdown files:** 2-3 lines of markdown content each. The filename (before the Notion ID) must match the corresponding CSV row's Name column.

   **Standalone page:** `Meeting Notes aabbccddaabbccddaabbccddaabbccdd.md` lives outside any database folder — exercises standalone page detection.

   Create the fixture by writing a Python script or shell commands that builds the directory tree and zips it, saving to `e2e/fixtures/notion-export.zip`.

2. **Create the E2E test directory and spec file** at `e2e/tests/60-notion-import/notion-import.spec.ts`. Import from `../../fixtures/auth` and `../../helpers/wait-for`. Use `test.describe.serial`.

3. **Test 1 — Full import flow: upload through summary.** Set timeout to 120s. Steps:
   - Navigate to `/browser/notion/import`
   - Discard any existing import (idempotent cleanup — check for `button:has-text("Discard")`)
   - Upload `notion-export.zip` via `#notion-zip` file input
   - Wait for scan results (`.import-stat-cards` visible, timeout 30s)
   - Click "Continue to Type Mapping" button (`button:has-text("Continue to Type Mapping")`)
   - Wait for `.type-mapping-table`
   - Map databases using `.mapping-select` dropdowns — select first non-empty option for each
   - Click "Next: Property Mapping" button → wait 3s for load
   - Click "Next: Relation Mapping" button (wait for it to be visible) → wait 3s
   - Click "Next: Preview" button → wait for preview content
   - Click Import button (`.import-actions button` containing "Import")
   - Wait for "Import Complete" text (timeout 60s — SSE-driven import)
   - Assert 4 `.import-stat-card` elements visible
   - Assert "Created" stat card has count > 0
   - Assert "Browse Imported Objects" button visible

4. **Test 2 — Verify imported objects exist in workspace.** Navigate to `/browser/`, wait for nav tree, confirm tree nodes exist (count > 0).

5. **Test 3 — Cleanup: discard import.** Navigate to `/browser/notion/import`, click Discard button if visible, wait for upload zone to reappear.

## Must-Haves

- [ ] `e2e/fixtures/notion-export.zip` exists with correct Notion directory/file naming (32 hex char IDs)
- [ ] ZIP contains 2 databases with CSV files, body markdown files, and 1 standalone page
- [ ] Tasks CSV has a "Project" relation column with values matching Projects database titles
- [ ] `e2e/tests/60-notion-import/notion-import.spec.ts` has 3 serial tests
- [ ] Test uploads ZIP, navigates all 7 wizard steps, and asserts on import summary
- [ ] Created count > 0 assertion proves objects were actually imported

## Verification

- `cd e2e && npx playwright test tests/60-notion-import/notion-import.spec.ts --project=chromium` — all 3 tests pass
- `unzip -l e2e/fixtures/notion-export.zip` — shows expected directory structure with 32-char hex IDs
- `cd backend && python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py tests/test_notion_executor.py -v` — 69/69 pass (regression check)

## Inputs

- `e2e/tests/14-obsidian-import/batch-import.spec.ts` — Reference pattern for wizard E2E test structure (test.describe.serial, upload → steps → summary → verify → cleanup)
- `e2e/fixtures/auth.ts` — Auth fixture providing `ownerPage` and `ownerRequest`
- `e2e/helpers/wait-for.ts` — `waitForIdle` and `waitForWorkspace` helpers
- S01/S02/S03 summaries — CSS selectors for wizard UI elements:
  - Upload zone: `.import-upload-zone`
  - File input: `#notion-zip`
  - Upload submit: `.upload-selected-file button[type="submit"]`
  - Stat cards: `.import-stat-cards`
  - Type mapping table: `.type-mapping-table`
  - Mapping dropdowns: `.mapping-select`
  - Navigation buttons: button text "Next: Property Mapping", "Next: Relation Mapping", "Next: Preview"
  - Import button: `.import-actions button` containing "Import"
  - Summary text: "Import Complete"
  - Summary stat cards: `.import-stat-card`
  - Stat numbers: `.stat-number`
  - Browse button: `button:has-text("Browse Imported Objects")`
  - Discard button: `button:has-text("Discard")`

## Expected Output

- `e2e/fixtures/notion-export.zip` — Synthetic Notion export ZIP (~2KB) with 2 databases, cross-DB relations, 4 body files, 1 standalone page
- `e2e/tests/60-notion-import/notion-import.spec.ts` — ~150-line Playwright spec with 3 serial tests exercising the full wizard flow

## Observability Impact

- **New signals**: E2E test produces Playwright trace files on failure, capturing screenshot + DOM snapshot at each wizard step. Test assertions surface the import stat card values (Created, Edges, Skipped, Duration) as pass/fail signals.
- **Inspection**: Run the test with `--trace on` to always capture traces; view with `npx playwright show-trace`. The fixture ZIP can be inspected with `unzip -l e2e/fixtures/notion-export.zip`.
- **Failure visibility**: If the wizard flow breaks in any step, the serial test identifies exactly which step failed — upload, scan, type mapping, property mapping, relation mapping, preview, or execute. The stat card assertions confirm objects were actually created, not just that the UI rendered.
