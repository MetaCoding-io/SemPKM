---
id: M040
provides:
  - User guide documentation for all M034 planning features (Calendar, Timeline, Map, Task Templates, Review Workflows)
  - Integration of 9 orphaned guide chapters into nav with unique chapter numbers 39–47
  - Zero broken cross-references across 47 guide chapters
  - Three-file nav sync (README.md, index.html, guide.html) fully verified
key_decisions: []
patterns_established:
  - Documentation sections follow consistent pattern: Opening → How Types Qualify → Features → Interactions
  - Cross-reference audit command: grep -rnoP '\]\(\K[^)]+\.md[^)]*' docs/guide/ for per-match link extraction
observability_surfaces:
  - none
requirement_outcomes: []
duration: ~2h
verification_result: passed
completed_at: 2026-03-23
---

# M040: Cleanup - Documentation, UI Fixes & Bug Squashing

**All M034 planning features documented in the user guide; 9 orphaned chapters renumbered and integrated into navigation — 47 chapters, zero collisions, zero broken cross-references.**

## What Happened

Two independent documentation slices ran in sequence. S01 extended existing chapters with M034 feature documentation; S02 resolved chapter numbering collisions for files that had been created by earlier milestones but never linked into navigation.

**S01 (M034 Feature Documentation)** added three new sections to Chapter 7 (Browsing and Visualizing Data) — Calendar View, Timeline/Gantt View, and Map View — bringing the renderer count from 4 to all 7. Each section was derived from reading source code and documents the type qualification heuristics, UI interactions, and integration points. The Calendar section includes recurring tasks (RRULE editor, EXDATE exceptions), cross-view drag from kanban/explorer, and the composable planning pattern. Two new sections were added to Chapter 28 (Dashboards & Workflows) — Task Templates and Review Workflows — documenting the REST API, command palette integration, batch instantiation pipeline, and all 5 seeded review workflows. Eight new glossary entries were added to Appendix D. Two nav drift issues were fixed during the three-file sync verification (duplicate entries in index.html, missing Mental Model Catalog in guide.html).

**S02 (Orphan Chapter Integration)** renamed 9 files that had duplicate chapter numbers (collisions at 29, 32, 36–40) to sequential chapters 39–47. All three navigation files were updated with the new entries, grouped topically. 27 internal cross-references broken by the renumbering were fixed across 9 files.

## Cross-Slice Verification

| Success Criterion | Evidence | Status |
|---|---|---|
| Calendar editing, timeline/Gantt, recurring tasks, task templates, review workflows documented | Chapter 7 has `## Calendar View`, `## Timeline / Gantt View`, `## Map View`; Chapter 28 has `## Task Templates`, `## Review Workflows` | ✅ |
| Chapter 7 covers all 7 renderers | H2 headings: Table View, Card View, Graph View, Kanban View, Calendar View, Timeline/Gantt View, Map View | ✅ |
| Chapter 28 covers task templates and review workflows | 4 mentions of "Task Template" or "Review Workflow" in chapter 28 | ✅ |
| All .md files linked from README.md, index.html, guide.html | Zero files missing from any nav file (verified by per-file grep across all 47 chapters) | ✅ |
| Zero chapter number collisions | `ls [0-9]*.md \| sed 's/-.*//' \| sort -n \| uniq -d` returns empty | ✅ |
| Glossary includes Calendar View, Timeline View, Recurrence, Task Template, Review Workflow | All 5 terms found in appendix-d-glossary.md | ✅ |
| No broken cross-references | `grep -rnoP` link extraction + file existence check returns zero broken refs | ✅ |
| 16 non-.gsd/ files changed, 500 insertions | `git diff --stat` confirms real documentation work | ✅ |

## Requirement Changes

No project-level requirement status changes. The DOC-01 through DOC-09 requirements referenced in the roadmap were milestone-internal scope items, not tracked in REQUIREMENTS.md.

## Forward Intelligence

### What the next milestone should know
- The user guide now has **47 numbered chapters** (01–47) plus 6 appendices (A–F). Next available chapter number is **48**.
- All three navigation files (README.md, index.html, guide.html) must be updated together — see Knowledge entry "User guide has THREE files that must stay in sync."
- The documentation gap flagged in M039's summary ("⚠️ User guide docs gap: no docs/guide chapters written for M034 features") is now resolved.

### What's fragile
- Three-file nav sync remains manual — there is no automated check that README.md, index.html, and guide.html stay in sync. A pre-commit hook or CI check would prevent future drift.
- Cross-reference audit depends on regex extraction (`grep -rnoP '\]\(\K[^)]+\.md[^)]*'`). A prior version of this regex only extracted the first link per line — always use the per-match (`-o`) variant.

### Authoritative diagnostics
- `ls docs/guide/[0-9]*.md | wc -l` → 47 (chapter count)
- `ls docs/guide/[0-9]*.md | sed 's/.*\///' | sed 's/-.*//' | sort -n | uniq -d` → empty (no duplicates)
- `grep -rnoP '\]\(\K[^)]+\.md' docs/guide/ | while read ...` → zero broken refs

### What assumptions changed
- The roadmap assumed 8 orphan files; S02 found 9 (two separate files both numbered 39 and two both numbered 40). All 9 were resolved.

## Files Created/Modified

- `docs/guide/07-browsing-and-visualizing.md` — 3 new view sections (Calendar, Timeline/Gantt, Map), +183 lines
- `docs/guide/28-dashboards-and-workflows.md` — 2 new sections (Task Templates, Review Workflows), +160 lines
- `docs/guide/appendix-d-glossary.md` — 8 new glossary entries + 15 cross-reference updates
- `docs/guide/README.md` — 9 orphan entries added, 1 stale removed
- `docs/guide/index.html` — 9 orphan entries added, duplicate entries removed
- `backend/app/templates/guide.html` — 9 orphan entries added, missing entry added
- `docs/guide/30-personas.md` — 1 cross-reference updated
- `docs/guide/39-mental-model-catalog.md` through `docs/guide/47-asana-sync.md` — 9 files renamed from old chapter numbers, headings updated, cross-references fixed
