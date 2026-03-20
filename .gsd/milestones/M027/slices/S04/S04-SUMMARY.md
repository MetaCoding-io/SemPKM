---
id: S04
parent: M027
milestone: M027
provides:
  - Playwright E2E test exercising the full 7-step Notion import wizard against Docker test stack
  - Synthetic Notion export ZIP fixture (2 databases, cross-DB relations, 1 standalone page)
  - Chapter 39 user guide documenting the complete Notion import workflow
  - Navigation updates in all 3 files (README, index.html, guide.html) plus glossary entry
requires:
  - slice: S01
    provides: Scanner module, upload UI, scan results UI
  - slice: S02
    provides: Type/property/relation mapping UI, preview
  - slice: S03
    provides: Two-pass import executor, SSE progress, import summary
affects: []
key_files:
  - e2e/fixtures/notion-export.zip
  - e2e/tests/60-notion-import/notion-import.spec.ts
  - docs/guide/39-notion-import.md
  - docs/guide/README.md
  - docs/guide/index.html
  - backend/app/templates/guide.html
  - docs/guide/38-hosted-demo.md
  - docs/guide/appendix-d-glossary.md
key_decisions:
  - Followed batch-import.spec.ts (Obsidian) pattern for wizard E2E structure with test.describe.serial
  - Followed Chapter 24 (Obsidian Onboarding) as structural template for Chapter 39, adapted for Notion's 7-step wizard
patterns_established:
  - Import wizard E2E tests use 3 serial tests (flow → verify → cleanup) matching the Obsidian pattern
  - User guide chapters follow the three-file navigation update rule (README, index.html, guide.html)
observability_surfaces:
  - Playwright traces on failure in e2e/test-results/ with screenshots and DOM snapshots per wizard step
  - Import stat card assertions confirm Created count > 0 (objects actually imported)
  - Chapter 39 served at /guide/39-notion-import.md — 404 means missing file in docs/guide/ volume mount
drill_down_paths:
  - .gsd/milestones/M027/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M027/slices/S04/tasks/T02-SUMMARY.md
duration: 25m
verification_result: passed
completed_at: 2026-03-20
---

# S04: E2E Tests + User Guide

**Playwright E2E test exercises full 7-step Notion import wizard (upload → scan → type map → property map → relation map → preview → import) against Docker test stack, and Chapter 39 user guide documents the complete workflow with concept mapping table and troubleshooting.**

## What Happened

T01 built the synthetic Notion export ZIP fixture at `e2e/fixtures/notion-export.zip` with a directory structure matching Notion's export format: workspace root with 32-char hex IDs on all filenames, Tasks and Projects databases (CSV + body markdown files), cross-DB relation column (Tasks.Project → Projects titles), and a standalone Meeting Notes page. The Playwright spec at `e2e/tests/60-notion-import/notion-import.spec.ts` uses `test.describe.serial` with 3 tests following the established Obsidian batch-import pattern:

1. **Full import flow** (120s timeout) — uploads ZIP, navigates all 7 wizard steps, waits for SSE-driven import completion, asserts 4 stat cards visible with Created > 0
2. **Verify workspace** — navigates to `/browser/`, confirms nav tree has imported objects
3. **Cleanup** — navigates back to import page, clicks Discard to clean up

T02 wrote Chapter 39 (272 lines) following Chapter 24 (Obsidian Onboarding) as structural template, covering: Prerequisites, all 7 wizard steps (Upload, Scan Results, Type Mapping, Property Mapping, Relation Mapping, Preview, Import), After Import actions, a Notion→SemPKM concept mapping table, troubleshooting section with 5 common issues, and See Also links. Updated all three navigation files per the KNOWLEDGE.md rule, updated Ch 38's "Next" link to point to Ch 39, and added "Notion Import" glossary entry.

## Verification

All slice-level verification checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | E2E test passes (3 tests, 18.2s) | ✅ |
| 2 | 69/69 backend unit tests pass (0.42s, zero regressions) | ✅ |
| 3 | `docs/guide/39-notion-import.md` exists (272 lines) | ✅ |
| 4 | README.md TOC has Ch 39 entry | ✅ |
| 5 | index.html sidebar has Ch 39 entry | ✅ |
| 6 | guide.html in-app page has Ch 39 entry | ✅ |
| 7 | Glossary has "Notion Import" entry | ✅ |
| 8 | Ch 38 "Next" points to Ch 39 | ✅ |
| 9 | Ch 39 "Next" points to Appendix A | ✅ |
| 10 | Zero conflict markers in new files | ✅ |

## Requirements Advanced

- NOTION-01 — E2E test exercises the full wizard flow proving all three sub-capabilities (ZIP import, database→type mapping, relation→edge resolution) work end-to-end

## Requirements Validated

- NOTION-01 — 69 unit tests (S01–S03) + Playwright E2E exercising the complete 7-step wizard flow + Chapter 39 user guide. All milestone definition-of-done criteria are now met.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None — both tasks followed their plans exactly.

## Known Limitations

- E2E test requires Docker test stack running (`docker compose -f docker-compose.test.yml up -d` from main tree)
- No Firefox E2E coverage — Playwright test runs on Chromium only (consistent with all other import wizard tests)
- Notion API integration remains explicitly out of scope per M027 CONTEXT; only ZIP export is supported

## Follow-ups

None — this is the terminal slice of M027. All milestone definition-of-done criteria are satisfied.

## Files Created/Modified

- `e2e/fixtures/notion-export.zip` — Synthetic Notion export fixture (2 databases, cross-DB relations, 1 standalone page, all 32-char hex IDs)
- `e2e/tests/60-notion-import/notion-import.spec.ts` — 149-line Playwright E2E spec with 3 serial tests
- `docs/guide/39-notion-import.md` — 272-line Chapter 39 user guide with 7 wizard steps, concept mapping table, troubleshooting
- `docs/guide/README.md` — Added Ch 39 TOC entry
- `docs/guide/index.html` — Added Ch 39 sidebar entry
- `backend/app/templates/guide.html` — Added Ch 39 in-app button
- `docs/guide/38-hosted-demo.md` — Updated "Next" link from Appendix A to Ch 39
- `docs/guide/appendix-d-glossary.md` — Added "Notion Import" glossary entry

## Forward Intelligence

### What the next slice should know
- M027 is complete. All 4 slices shipped. The Notion import wizard is fully functional with scanner (S01), mapping UI (S02), two-pass executor (S03), and E2E test + user guide (S04).
- The pattern established across S01–S04 mirrors the Obsidian import wizard exactly — same module structure, same SSE broadcast approach, same E2E test pattern. A third importer (e.g., Roam, Logseq) could follow the same template.

### What's fragile
- **Relation detection heuristic** — The scanner uses an 80% title-match heuristic to detect cross-DB relations. Exports with duplicate titles across databases may produce ambiguous results. This is a fundamental limitation of Notion's ZIP format (no IDs in CSV).
- **CSS selectors in E2E test** — The spec relies on specific CSS classes (`.import-stat-card`, `.wizard-step`, `.scan-results`) from the Jinja templates. Template restructuring would break the E2E test.

### Authoritative diagnostics
- `cd e2e && npx playwright test tests/60-notion-import/notion-import.spec.ts --project=chromium` — single command proves the entire wizard works end-to-end
- `cd backend && .venv/bin/python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py tests/test_notion_executor.py -v` — 69 unit tests prove all backend logic

### What assumptions changed
- No assumptions changed — S04 was a straightforward terminal slice (test + docs) with no surprises.
