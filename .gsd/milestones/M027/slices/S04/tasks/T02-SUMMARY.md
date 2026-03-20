---
id: T02
parent: S04
milestone: M027
provides:
  - "Chapter 39: Notion Import user guide (272 lines, 7 wizard steps, concept mapping table, troubleshooting)"
  - "All three navigation files updated with Ch 39 entry"
  - "Glossary entry for Notion Import"
key_files:
  - docs/guide/39-notion-import.md
  - docs/guide/README.md
  - docs/guide/index.html
  - backend/app/templates/guide.html
  - docs/guide/38-hosted-demo.md
  - docs/guide/appendix-d-glossary.md
key_decisions:
  - "Followed Ch 24 (Obsidian Onboarding, 232 lines) as structural template, adapted for Notion's 7-step wizard with added Relation Mapping step"
patterns_established:
  - "Notion Import glossary entry placed alphabetically between Monday.com Sync and Named Graph"
observability_surfaces:
  - "Chapter served at /guide/39-notion-import.md — 404 means missing file in docs/guide/ volume mount"
duration: 10m
verification_result: passed
completed_at: 2026-03-20T12:15:00-04:00
blocker_discovered: false
---

# T02: Write user guide chapter and update navigation files

**Wrote Chapter 39: Notion Import (272-line user guide) with 7 wizard steps, concept mapping table, and troubleshooting; updated all three navigation files, Ch 38 next-link, and glossary.**

## What Happened

Created `docs/guide/39-notion-import.md` following Ch 24 (Obsidian Onboarding) as the structural template, adapted for Notion's database/column/relation model. The chapter covers: Prerequisites (Mental Model + Notion export instructions), all 7 wizard steps (Upload, Scan Results, Type Mapping, Property Mapping, Relation Mapping, Preview, Import), After Import actions, a Notion→SemPKM concept mapping table, a troubleshooting section with 5 common issues, and See Also links.

Updated all three navigation files per the KNOWLEDGE.md rule: `README.md` TOC, `index.html` sidebar `<li>`, and `guide.html` in-app htmx `<button>`. Updated Ch 38's "Next" link to point to Ch 39 (was Appendix A). Added "Notion Import" glossary entry in `appendix-d-glossary.md` alphabetically between "Monday.com Sync" and "Named Graph".

## Verification

All 9 task-level verification checks pass. Navigation chain verified: Ch 37 → Ch 38 → Ch 39 → Appendix A.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/39-notion-import.md` | 0 | ✅ pass | <1s |
| 2 | `wc -l docs/guide/39-notion-import.md` (272 ≥ 150) | 0 | ✅ pass | <1s |
| 3 | `grep "39-notion-import" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 4 | `grep "39-notion-import" docs/guide/index.html` | 0 | ✅ pass | <1s |
| 5 | `grep "39-notion-import" backend/app/templates/guide.html` | 0 | ✅ pass | <1s |
| 6 | `grep "Chapter 39" docs/guide/38-hosted-demo.md` | 0 | ✅ pass | <1s |
| 7 | `grep "Notion Import" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass | <1s |
| 8 | `grep "Appendix A" docs/guide/39-notion-import.md` | 0 | ✅ pass | <1s |
| 9 | `grep -rn "^<<<<<<< " docs/guide/39-notion-import.md` | 1 (no matches) | ✅ pass | <1s |

## Diagnostics

Documentation-only task — no runtime diagnostics. The chapter is served as static Markdown via the `/guide/<filename>` endpoint. A 404 on `/guide/39-notion-import.md` would indicate a missing file in the `docs/guide/` volume mount.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/39-notion-import.md` — New 272-line user guide chapter with 7 wizard steps, concept mapping table, and troubleshooting
- `docs/guide/README.md` — Added Ch 39 TOC entry after Ch 38
- `docs/guide/index.html` — Added Ch 39 sidebar `<li>` after Ch 38
- `backend/app/templates/guide.html` — Added Ch 39 in-app htmx `<button>` after Ch 38
- `docs/guide/38-hosted-demo.md` — Updated "Next" link from Appendix A to Ch 39
- `docs/guide/appendix-d-glossary.md` — Added "Notion Import" glossary entry
- `.gsd/milestones/M027/slices/S04/tasks/T02-PLAN.md` — Added Observability Impact section per pre-flight requirement
