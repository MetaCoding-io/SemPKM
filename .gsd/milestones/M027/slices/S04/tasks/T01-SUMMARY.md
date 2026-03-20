---
id: T01
parent: S04
milestone: M027
provides:
  - Synthetic Notion export ZIP fixture for E2E testing
  - Playwright E2E spec exercising the full 7-step Notion import wizard
key_files:
  - e2e/fixtures/notion-export.zip
  - e2e/tests/60-notion-import/notion-import.spec.ts
key_decisions:
  - Followed the batch-import.spec.ts pattern from Obsidian importer for wizard E2E structure
patterns_established:
  - Notion E2E test uses test.describe.serial with 3 sequential tests (flow → verify → cleanup)
observability_surfaces:
  - Playwright traces on failure in e2e/test-results/ with screenshots and DOM snapshots per wizard step
  - Import stat card assertions confirm Created count > 0 (objects actually imported)
duration: 15m
verification_result: passed
completed_at: 2026-03-20T12:09:00-04:00
blocker_discovered: false
---

# T01: Create Notion export fixture ZIP and Playwright E2E test

**Created synthetic Notion export ZIP (2 databases, cross-DB relations, 1 standalone page) and 3-test Playwright E2E spec exercising the full 7-step import wizard against Docker test stack**

## What Happened

Built the fixture ZIP at `e2e/fixtures/notion-export.zip` containing a directory structure matching Notion's export format: workspace root with 32-char hex IDs on all filenames, Tasks and Projects databases with CSV + body markdown files, and a standalone Meeting Notes page. The Tasks CSV includes a "Project" relation column with values matching Projects database titles, exercising the cross-DB relation detection.

Created the Playwright spec at `e2e/tests/60-notion-import/notion-import.spec.ts` with `test.describe.serial` containing 3 tests:
1. **Full import flow** (120s timeout) — uploads ZIP, navigates all 7 wizard steps (upload → scan → type mapping → property mapping → relation mapping → preview → execute), waits for SSE-driven import completion, asserts 4 stat cards visible, Created > 0, Browse button visible
2. **Verify workspace** — navigates to `/browser/`, confirms nav tree has imported objects
3. **Cleanup** — navigates back to import page, clicks Discard to clean up

All CSS selectors were verified against the actual Jinja templates in `backend/app/templates/notion/partials/`.

## Verification

- All 3 E2E tests pass on first attempt (18.2s total): full flow (9.8s), verify workspace (4.3s), cleanup (2.8s)
- All 69 backend unit tests pass (0.42s) — zero regressions
- ZIP structure verified with `unzip -l` — all 10 entries have valid 32-char hex Notion IDs
- Zero conflict markers in test files

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx playwright test tests/60-notion-import/notion-import.spec.ts --project=chromium` | 0 | ✅ pass | 18.2s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py tests/test_notion_executor.py -v` | 0 | ✅ pass | 0.42s |
| 3 | `unzip -l e2e/fixtures/notion-export.zip` | 0 | ✅ pass | <1s |
| 4 | `grep -rn "^<<<<<<< " e2e/tests/60-notion-import/` | 1 (no matches) | ✅ pass | <1s |
| 5 | `test -f docs/guide/39-notion-import.md` | 1 | ⏳ T02 | — |
| 6 | `grep "39-notion-import" docs/guide/README.md` | 1 | ⏳ T02 | — |
| 7 | `grep "39-notion-import" docs/guide/index.html` | 1 | ⏳ T02 | — |
| 8 | `grep "39-notion-import" backend/app/templates/guide.html` | 1 | ⏳ T02 | — |
| 9 | `grep "Notion Import" docs/guide/appendix-d-glossary.md` | 1 | ⏳ T02 | — |
| 10 | `grep "Chapter 39" docs/guide/38-hosted-demo.md` | 1 | ⏳ T02 | — |

Checks 5-10 are T02 scope (user guide chapter) and expected to fail at this stage.

## Diagnostics

- **Playwright traces**: On test failure, traces/screenshots are saved to `e2e/test-results/`. View with `npx playwright show-trace <trace.zip>`.
- **Fixture inspection**: `unzip -l e2e/fixtures/notion-export.zip` shows the full directory tree. Extract with `unzip -d /tmp/notion-test e2e/fixtures/notion-export.zip` to inspect CSV/markdown content.
- **Import summary**: The E2E test asserts on `.import-stat-card` elements — Created count > 0 proves objects were actually persisted to the triplestore.

## Deviations

None — implementation followed the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `e2e/fixtures/notion-export.zip` — Synthetic Notion export fixture with 2 databases (Tasks, Projects), cross-DB relation column, 4 body markdown files, 1 standalone page
- `e2e/tests/60-notion-import/notion-import.spec.ts` — Playwright E2E spec with 3 serial tests exercising the full 7-step import wizard
- `.gsd/milestones/M027/slices/S04/S04-PLAN.md` — Added Observability/Diagnostics section and failure-path verification check
- `.gsd/milestones/M027/slices/S04/tasks/T01-PLAN.md` — Added Observability Impact section
