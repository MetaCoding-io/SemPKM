---
id: T03
parent: S01
milestone: M040
provides:
  - 8 glossary entries for M034 planning concepts (Calendar View, Cross-View Drag, Gantt Chart, Recurrence/RRULE, Review Workflow, Scope Propagation, Task Template, Timeline View)
  - Three-file nav sync verified and fixed (index.html duplicate 25/26 removed, guide.html missing Mental Model Catalog added)
key_files:
  - docs/guide/appendix-d-glossary.md
  - docs/guide/index.html
  - backend/app/templates/guide.html
key_decisions: []
patterns_established:
  - Glossary entries follow pattern: bold term, definition paragraph, cross-reference to relevant chapter
observability_surfaces:
  - none
duration: 15m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: Add glossary entries and verify three-file nav sync

**Added 8 M034 glossary entries with chapter cross-references and fixed three-file nav sync drift (duplicate index.html entries, missing guide.html Mental Model Catalog).**

## What Happened

Added alphabetically-placed glossary entries for: Calendar View, Cross-View Drag, Gantt Chart, Recurrence (RRULE), Review Workflow, Scope Propagation, Task Template, and Timeline View. Each entry includes a definition and a cross-reference to the relevant chapter (chapter 7 for views, chapter 28 for templates/workflows).

Diffed all three navigation files and found three drift issues:
1. `index.html` Part VIII had duplicate entries for chapters 25-26 with malformed labels (`# Chapter 25:` prefix) — they were already correctly listed in Part IX. Removed the duplicates.
2. `guide.html` was missing the Mental Model Catalog entry (both README and index.html had two chapter 29 entries). Added it after App Platform.
3. Confirmed README.md structure was already correct (both 29-app-platform and 29-mental-model-catalog listed).

After fixes, all three files list identical chapter sets with zero diff.

## Verification

- Glossary term grep returns 11 (≥ 7 threshold)
- Slice-level glossary grep returns 6 (≥ 5 threshold)  
- Chapter 7 line count: 478 (≥ 450 target)
- Three-file sync: `diff` on sorted chapter refs between README/index/guide returns exit 0

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c "Calendar View\|Timeline.*View\|Map View" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass (21 ≥ 3) | <1s |
| 2 | `grep -c "Task Template\|Review Workflow" docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass (4 ≥ 2) | <1s |
| 3 | `grep -c "Calendar View\|Timeline View\|Recurrence\|Task Template\|Review Workflow" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass (6 ≥ 5) | <1s |
| 4 | `wc -l docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass (478 ≥ 450) | <1s |
| 5 | `diff README-vs-index sorted chapter refs` | 0 | ✅ pass (identical) | <1s |
| 6 | `diff README-vs-guide sorted chapter refs` | 0 | ✅ pass (identical) | <1s |
| 7 | `grep -c glossary terms (task-level, ≥7)` | 0 | ✅ pass (11 ≥ 7) | <1s |

## Diagnostics

This is a documentation-only task. No runtime signals, logs, or failure state to inspect. Verify content by grepping the glossary file for term definitions and diffing nav files for sync.

## Deviations

None. The planner anticipated possible drift and it was confirmed and fixed as described.

## Known Issues

- Chapter 29 is shared by two files (29-app-platform.md and 29-mental-model-catalog.md). This is pre-existing and not introduced by this task. A future renumbering could assign 29A/29B or shift Mental Model Catalog to a different number.

## Files Created/Modified

- `docs/guide/appendix-d-glossary.md` — Added 8 new M034 glossary entries
- `docs/guide/index.html` — Removed duplicate chapter 25/26 entries from Part VIII
- `backend/app/templates/guide.html` — Added missing Mental Model Catalog entry
