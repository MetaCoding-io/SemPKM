---
id: T04
parent: S04
milestone: M012
provides:
  - User guide documentation for all M012 features (event log polish, body.diff, personas)
  - Updated Chapter 15 with predicate labels, helptext tooltips, autocomplete filters, body.diff sections
  - New Chapter 30 covering workspace personas (creation, switching, saving, deletion)
  - Updated TOC, navigation chain, and glossary entries
key_files:
  - docs/guide/15-event-log.md
  - docs/guide/30-personas.md
  - docs/guide/README.md
  - docs/guide/29-mental-model-catalog.md
  - docs/guide/appendix-d-glossary.md
key_decisions: []
patterns_established: []
observability_surfaces:
  - "grep -c 'Persona|Body Diff' docs/guide/appendix-d-glossary.md — returns ≥2"
  - "grep '30-personas' docs/guide/README.md — finds Chapter 30 in TOC"
  - "tail -3 docs/guide/29-mental-model-catalog.md — shows Next → Chapter 30"
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T04: User guide documentation for event log improvements and personas

**Added user guide documentation for all M012 features: updated Chapter 15 (event log) with predicate labels, helptext tooltips, autocomplete filters, and body.diff sections; created Chapter 30 (Workspace Personas); updated TOC, navigation chain, and glossary**

## What Happened

Updated five documentation files to cover all M012 features:

1. **Chapter 15 (Event Log)** — Added four new sections after "Browsing the Timeline": Predicate Labels (explains sh:name resolution to human-readable labels), Helptext Tooltips (describes dotted-underline indicators and SHACL annotation tooltips), Autocomplete Filters (documents the three autocomplete inputs for operation type, predicate, and object), and Body Diff Events (explains body.diff vs body.set, unified diff storage, and green/red rendering). Also added `body.diff` to the Diff button operation types list.

2. **Chapter 30 (Workspace Personas)** — Created new chapter with seven sections: introduction with use cases, Default Persona (auto-creation), Creating a Persona (sidebar + command palette), Switching Personas (auto-save + restore), Saving Persona State (manual + automatic triggers), Renaming and Deleting (API rename, sidebar delete), and What's Saved (panel layout, sidebar positions, explorer mode — explicitly noting what's NOT saved). Includes navigation footer linking to Chapter 29 (previous) and Appendix A (next).

3. **README.md TOC** — Added Chapter 30 entry under Part VIII.

4. **Chapter 29 navigation** — Updated "Next" link from Appendix A to Chapter 30.

5. **Glossary** — Added "Body Diff" (after "Block") and "Persona" (after "PermanentNote") entries in correct alphabetical position with cross-references to their respective chapters.

## Verification

All task-level and slice-level documentation verification checks pass:
- `grep "30-personas" docs/guide/README.md` → found Chapter 30 in TOC
- `tail -3 docs/guide/29-mental-model-catalog.md` → Next → Chapter 30
- `head -5 docs/guide/30-personas.md` → Chapter 30 title present
- `tail -3 docs/guide/30-personas.md` → Previous → Chapter 29, Next → Appendix A
- `grep -c "Persona\|Body Diff" docs/guide/appendix-d-glossary.md` → 7 (≥2)
- `grep "body.diff" docs/guide/15-event-log.md` → 9 matches across all new sections
- Chapter 15 has all four new section headings: Predicate Labels, Helptext Tooltips, Autocomplete Filters, Body Diff Events

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep "30-personas" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 2 | `tail -3 docs/guide/29-mental-model-catalog.md` | 0 | ✅ pass | <1s |
| 3 | `head -5 docs/guide/30-personas.md` | 0 | ✅ pass | <1s |
| 4 | `tail -3 docs/guide/30-personas.md` | 0 | ✅ pass | <1s |
| 5 | `grep -c "Persona\|Body Diff" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass (7 ≥ 2) | <1s |
| 6 | `grep "body.diff" docs/guide/15-event-log.md` | 0 | ✅ pass (9 matches) | <1s |
| 7 | `grep "^## " docs/guide/15-event-log.md` | 0 | ✅ pass (4 new sections) | <1s |

## Diagnostics

Documentation-only task — no runtime diagnostics. Verify completeness with:
- `grep "^## " docs/guide/15-event-log.md` — lists all section headings in Chapter 15
- `wc -l docs/guide/30-personas.md` — Chapter 30 line count (~130 lines)
- `grep -n "Persona\|Body Diff" docs/guide/appendix-d-glossary.md` — glossary entry locations

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/15-event-log.md` — Updated with 4 new sections (predicate labels, helptext tooltips, autocomplete filters, body diff events) and body.diff in Diff button list
- `docs/guide/30-personas.md` — New chapter covering workspace personas (7 sections + navigation)
- `docs/guide/README.md` — Added Chapter 30 to Part VIII TOC
- `docs/guide/29-mental-model-catalog.md` — Updated navigation footer: Next → Chapter 30
- `docs/guide/appendix-d-glossary.md` — Added "Body Diff" and "Persona" glossary entries
- `.gsd/milestones/M012/slices/S04/tasks/T04-PLAN.md` — Added Observability Impact section (pre-flight fix)
