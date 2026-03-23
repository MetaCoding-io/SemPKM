---
id: S01
milestone: M040
outcome: success
tasks_completed: 3
tasks_total: 3
duration: ~55m
completed_at: 2026-03-23
---

# S01: M034 Feature Documentation — Summary

**Outcome:** All M034 planning features are now documented in the user guide. Chapter 7 covers all 7 renderers (Table, Cards, Graph, Kanban, Calendar, Timeline, Map). Chapter 28 covers task templates and review workflows. Glossary has 8 new terms. Three-file nav sync verified and two drift issues fixed.

## What Was Delivered

### Chapter 7 — Browsing and Visualizing Data (295 → 478 lines)

Three new `##` sections added, each derived from reading the actual source code:

1. **Calendar View** — type qualification via date field detection heuristics, calendar modes (month/week/day), color coding, drag-to-reschedule with optimistic rollback, resize-to-change-duration, click-to-create with date pre-fill, recurring tasks subsection covering the recurrence editor (RRULE presets, custom mode with frequency/interval/day-selection/end-conditions, EXDATE exception dates), cross-view drag from kanban/explorer, composable planning pattern (calendar + kanban side by side), and scope synchronization.

2. **Timeline / Gantt View** — shared date field detection, zoom levels (Quarter Day → Year), task bars with click-to-open, dependency arrows, drag-to-reschedule, recurring task instances.

3. **Map View** — two-pass geo field detection (well-known IRI match then local-name heuristic), OpenStreetMap tiles, marker clusters with chunked loading, marker popups with click-to-open.

Chapter intro paragraph updated to mention all 7 renderers.

### Chapter 28 — Dashboards & Workflows (301 → 461 lines)

Two new `##` sections:

1. **Task Templates** — what a template contains (title, target class, default properties, subtask definitions), CRUD via REST API with JSON examples, command palette "Create from Template" submenu, batch instantiation pipeline with @slot: cross-command references, atomic commit, override merging. Tip connecting templates to form groups.

2. **Review Workflows** — all 5 seeded workflows (Create & Review, Weekly, Monthly, Quarterly, Yearly) with table showing step counts and purpose, palette launch, stepper UI walkthrough, customization options, PPV model dependency documentation.

### Glossary (Appendix D)

8 new entries added alphabetically with chapter cross-references: Calendar View, Cross-View Drag, Gantt Chart, Recurrence (RRULE), Review Workflow, Scope Propagation, Task Template, Timeline View.

### Three-File Nav Sync

Verified and fixed drift:
- `index.html` — removed duplicate chapter 25/26 entries with malformed labels in Part VIII
- `guide.html` — added missing Mental Model Catalog entry
- After fixes, all three nav files (README.md, index.html, guide.html) list identical chapter sets

## Verification Results

| Check | Result | Threshold |
|-------|--------|-----------|
| Calendar/Timeline/Map mentions in ch7 | 21 | ≥ 3 |
| Task Template/Review Workflow mentions in ch28 | 4 | ≥ 2 |
| Glossary term count (5-term check) | 6 | ≥ 5 |
| Glossary term count (7-term check) | 10 | ≥ 7 |
| Ch7 line count | 478 | ≥ 450 |
| Ch7 H2 section count | 13 | ≥ 10 |
| Ch28 H2 section count | 10 | grew |
| index.html ↔ guide.html diff | 0 lines | identical |

## What S02 Should Know

- S01 did not create any new chapter files — it extended existing chapters 7 and 28. No new entries were needed in the nav files for S01's content.
- The nav sync fixes (duplicate removal in index.html, missing entry in guide.html) are already committed. S02 should not re-fix these.
- Chapter 29 is still shared by two files (29-app-platform.md, 29-mental-model-catalog.md). S02's renumbering work may want to resolve this.
- Documentation sections follow a consistent pattern: Opening → How Types Qualify → Features → Interactions. New sections should match.

## Files Modified

- `docs/guide/07-browsing-and-visualizing.md` — 3 new view sections (Calendar, Timeline, Map)
- `docs/guide/28-dashboards-and-workflows.md` — 2 new sections (Task Templates, Review Workflows)
- `docs/guide/appendix-d-glossary.md` — 8 new glossary entries
- `docs/guide/index.html` — removed duplicate entries
- `backend/app/templates/guide.html` — added missing Mental Model Catalog entry
