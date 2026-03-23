---
estimated_steps: 5
estimated_files: 4
---

# T03: Add glossary entries and verify three-file nav sync

**Slice:** S01 — M034 Feature Documentation
**Milestone:** M040

## Description

Add M034 concept definitions to Appendix D (Glossary) and verify that the three guide navigation files (README.md, index.html, guide.html) are consistent with each other. Since T01-T02 extend existing chapters rather than creating new ones, nav files likely don't need new entries — but the research flagged existing drift (duplicate chapter 29 in README.md, chapters 25-26 out of sequence) that should be noted.

## Steps

1. Add glossary entries (alphabetically placed) for: Calendar View, Cross-View Drag, Gantt Chart, Recurrence (RRULE), Review Workflow, Scope Propagation, Task Template, Timeline View
2. Cross-reference glossary entries to the relevant chapters (chapter 7 for views, chapter 28 for templates/workflows)
3. Diff the chapter listings in README.md, index.html, and guide.html to identify any sync drift
4. Fix any drift found (missing entries, duplicate numbers, ordering inconsistencies)
5. Verify all 3 files list the same set of chapters

## Must-Haves

- [ ] 8 new glossary entries for M034 concepts
- [ ] Glossary entries reference correct chapter numbers
- [ ] Three nav files are consistent (same chapter set, same order within each Part)

## Verification

- `grep -c "Calendar View\|Timeline View\|Recurrence\|Task Template\|Review Workflow\|Gantt\|Cross-View\|Scope Propagation" docs/guide/appendix-d-glossary.md` returns >= 7
- Three-file sync check: `diff <(grep -oP '\d+(?=-[a-z])' docs/guide/README.md | sort -n) <(grep -oP 'data-file="\K\d+' docs/guide/index.html | sort -n)` shows no differences (or only expected appendix differences)

## Inputs

- `docs/guide/appendix-d-glossary.md` — existing glossary to extend
- `docs/guide/README.md` — markdown TOC
- `docs/guide/index.html` — static docs site sidebar
- `backend/app/templates/guide.html` — in-app guide template

## Expected Output

- `docs/guide/appendix-d-glossary.md` — extended with 8 new M034 terms
- `docs/guide/README.md` — verified/fixed for consistency
- `docs/guide/index.html` — verified/fixed for consistency
- `backend/app/templates/guide.html` — verified/fixed for consistency
