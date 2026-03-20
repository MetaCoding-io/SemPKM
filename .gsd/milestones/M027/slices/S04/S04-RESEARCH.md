# S04: E2E Tests + User Guide — Research

**Date:** 2026-03-20
**Depth:** Light — well-established patterns with 5+ prior examples in codebase (Jira S04, Monday S04, GitHub S04, Demo S04, Obsidian import E2E)

## Summary

This slice produces two independent deliverables: (1) a Playwright E2E test exercising the full Notion import wizard flow against the Docker test stack, and (2) a user guide chapter documenting the workflow. Both follow patterns with extensive prior art — the Obsidian import E2E test (`e2e/tests/14-obsidian-import/batch-import.spec.ts`) is the closest template for the E2E test, and Chapter 24 (`docs/guide/24-obsidian-onboarding.md`, 232 lines) is the closest template for the user guide. Additionally, three navigation files must be updated (README TOC, index.html sidebar, guide.html in-app page) per KNOWLEDGE.md rule "User guide has THREE files that must stay in sync."

The E2E test requires a synthetic Notion export ZIP fixture with at least 2 databases (with cross-DB relations) and standalone pages. The unit tests already have a `_create_notion_export()` helper that builds the exact directory/CSV structure — the fixture ZIP should replicate this structure as a static ZIP file.

## Recommendation

**Two independent tasks, parallelizable:**

1. **T01 — E2E Test + Fixture ZIP** — Create `e2e/fixtures/notion-export.zip` with a synthetic Notion export (2 databases, cross-DB relations, standalone pages), then write `e2e/tests/60-notion-import/notion-import.spec.ts` following the Obsidian `batch-import.spec.ts` pattern. The test exercises: upload → scan → type mapping → property mapping → relation mapping → preview → execute → summary → verify objects via SPARQL.

2. **T02 — User Guide + Navigation Updates** — Write `docs/guide/39-notion-import.md` following Chapter 24 (Obsidian Onboarding) as the template. Update all three navigation files: `docs/guide/README.md` (TOC entry), `docs/guide/index.html` (sidebar entry), `backend/app/templates/guide.html` (in-app button). Update `docs/guide/appendix-d-glossary.md` with Notion Import entry. Update navigation chain (Ch 38 → Ch 39, Ch 39 → Appendix A).

## Implementation Landscape

### Key Files

**E2E test (create):**
- `e2e/fixtures/notion-export.zip` — Synthetic Notion export ZIP fixture. Must contain: workspace root folder with Notion ID suffix, 2+ database folders (each with matching-name CSV + .md body files with 32-hex-char Notion IDs), cross-DB relation column in one CSV, 1+ standalone .md pages outside database folders
- `e2e/tests/60-notion-import/notion-import.spec.ts` — Full wizard E2E test

**E2E test (reference patterns):**
- `e2e/tests/14-obsidian-import/batch-import.spec.ts` — Closest pattern. Uses `test.describe.serial`, uploads ZIP, clicks through wizard steps, asserts on summary stat cards, verifies objects in workspace. 3 serial tests (full flow, verify objects, cleanup).
- `e2e/fixtures/auth.ts` — Auth fixture providing `ownerPage` and `ownerRequest`
- `e2e/helpers/wait-for.ts` — `waitForIdle`, `waitForWorkspace` helpers

**User guide (create):**
- `docs/guide/39-notion-import.md` — New chapter (chapter number 39 follows Monday.com Sync at 38-hosted-demo → rename consideration: since hosted-demo is 38, Notion import becomes 39)

**User guide (reference patterns):**
- `docs/guide/24-obsidian-onboarding.md` — Closest template (232 lines). Covers: prerequisites, upload, scan results, type mapping, property mapping, preview, import, summary
- `docs/guide/36-jira-sync.md` — Good for field mapping table format and troubleshooting sections

**Navigation files (update — ALL THREE per KNOWLEDGE.md):**
- `docs/guide/README.md` — Add Ch 39 entry after Ch 38
- `docs/guide/index.html` — Add sidebar `<li>` after line 481 (38. Hosted Demo)
- `backend/app/templates/guide.html` — Add `<button>` entry after line 390 (38. Hosted Demo)
- `docs/guide/38-hosted-demo.md` — Update "Next" link from Appendix A to Ch 39
- `docs/guide/appendix-d-glossary.md` — Add "Notion Import" glossary entry

### Build Order

1. **T01: E2E Test + Fixture** — Build the fixture ZIP first (blocks the test), then the spec. The fixture must follow Notion's naming convention exactly: `My Workspace abc123abc123abc123abc123abc123ab/Tasks abc123abc123abc123abc123abc123ab/Tasks abc123abc123abc123abc123abc123ab.csv`. The scanner's `_strip_notion_id` regex expects exactly 32 hex chars after a space.

2. **T02: User Guide** — Independent of T01. Follow Ch 24 structure adapted for Notion's 7-step wizard (Upload, Scan, Types, Properties, Relations, Preview, Import).

### Fixture ZIP Structure

The ZIP must exercise both import passes and all scanner features:

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

**Tasks CSV** — columns: Name, Status (select), Priority (select), Due Date (date), Project (relation → Projects)
**Projects CSV** — columns: Name, Description (text), Start Date (date), Status (select)

The "Project" column in Tasks CSV contains values like "Website Redesign, Mobile App" — matching titles in the Projects database. This exercises cross-DB relation detection (>80% overlap) and Pass 2 edge resolution.

### E2E Test Flow

The spec follows `batch-import.spec.ts` pattern with these wizard-specific steps:

1. Navigate to `/browser/notion/import`
2. Discard any existing import (idempotent cleanup)
3. Upload `notion-export.zip` via `#notion-zip` file input
4. Wait for scan results (`.import-stat-cards` visible)
5. Click "Continue to Type Mapping" button
6. Map databases using `.mapping-select` dropdowns (select first available type for each)
7. Click "Next: Property Mapping" → wait for `.property-mapping` or next step content
8. Click "Next: Relation Mapping" → wait for relation mapping step
9. Click "Next: Preview" → wait for preview content
10. Click Import button (`.import-actions button` with hx-post to execute)
11. Wait for "Import Complete" text (up to 60s for SSE-driven import)
12. Assert 4 stat cards visible in summary
13. Assert created count > 0
14. Verify objects exist via SPARQL query or workspace nav tree

### CSS Selectors for E2E

Key selectors from the Notion templates:
- Upload zone: `.import-upload-zone`
- File input: `#notion-zip`
- Upload submit: `.upload-selected-file button[type="submit"]`
- Stat cards: `.import-stat-cards`
- Type mapping table: `.type-mapping-table`
- Mapping dropdowns: `.mapping-select`
- Navigation buttons: `.mapping-nav .btn-primary` (Next), `.mapping-nav .btn-outline` (Back)
- Import button: `.import-actions button` (on preview page)
- Summary title: `text=Import Complete`
- Summary stat cards: `.import-stat-card`
- Summary stat numbers: `.stat-number`
- Browse button: `button:has-text("Browse Imported Objects")`
- Discard button: `button:has-text("Discard")`

### User Guide Structure (following Ch 24)

1. Introduction — what Notion import does, what it preserves
2. Prerequisites — Mental Model installed, Notion ZIP export instructions
3. Step 1: Upload — navigate to Admin > Import > Notion, upload ZIP
4. Step 2: Review Scan Results — databases, columns with type badges, standalone pages, detected relations
5. Step 3: Type Mapping — map databases to types, standalone page type
6. Step 4: Property Mapping — map columns to RDF predicates, auto-suggest
7. Step 5: Relation Mapping — map detected relations to edge predicates
8. Step 6: Preview — review sample mapped objects
9. Step 7: Import — SSE progress, summary stats
10. After Import — browsing objects, re-importing, discarding
11. How Notion Concepts Map to SemPKM — comparison table (Database→Type, Row→Object, Property→RDF predicate, Relation→Edge, Page→Note)
12. Troubleshooting — common issues

### Verification Approach

**E2E test:**
- `cd e2e && npx playwright test tests/60-notion-import/notion-import.spec.ts --project=chromium` — passes against Docker test stack
- Alternatively, verify the spec parses: `npx tsc --noEmit tests/60-notion-import/notion-import.spec.ts` (or `node -e "require('...')"`)

**User guide:**
- `docs/guide/39-notion-import.md` exists and is well-formed markdown
- `grep "39-notion-import" docs/guide/README.md` — returns TOC entry
- `grep "39-notion-import" docs/guide/index.html` — returns sidebar entry
- `grep "39-notion-import" backend/app/templates/guide.html` — returns in-app button
- `grep "Notion Import" docs/guide/appendix-d-glossary.md` — returns glossary entry
- Navigation chain: Ch 38 links to Ch 39, Ch 39 links to Appendix A

**Regression:**
- `cd backend && python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py tests/test_notion_executor.py -v` — all 69 existing tests still pass
- `grep -rn "^<<<<<<< " backend/app/notion/ e2e/tests/60-notion-import/ docs/guide/39-notion-import.md` — zero conflict markers

## Constraints

- The fixture ZIP filenames must have exactly 32 hex char Notion IDs (the scanner's `_strip_notion_id` regex: `r'\s+[0-9a-f]{32}$'`)
- The E2E test must use `test.describe.serial` — wizard steps are sequential and state-dependent
- The Docker test stack must have `basic-pkm` model installed for type mapping dropdowns to have options
- The user guide chapter number must be 39 (follows 38-hosted-demo.md in the existing sequence)
- All three navigation files must be updated together per KNOWLEDGE.md rule
