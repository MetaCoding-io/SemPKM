# S01: M034 Feature Documentation

**Goal:** Document all M034 planning features in the user guide so users can discover and learn calendar editing, timeline/Gantt, recurring tasks, task templates, and review workflows.
**Demo:** Chapter 7 has Calendar View, Timeline/Gantt View, and Map View sections. Chapter 28 has Task Templates and Review Workflows sections. Glossary has new M034 terms.

## Must-Haves

- Calendar View section in chapter 7 covering: opening, drag-to-reschedule, resize-to-change-duration, click-to-create, cross-view drag from kanban
- Timeline/Gantt View section in chapter 7 covering: opening, zoom levels, dependency arrows, drag-to-reschedule
- Map View section in chapter 7 covering: opening, marker clusters, geo field detection (M033 gap, low marginal cost)
- Recurring tasks and recurrence editor section covering: RRULE presets, custom mode, EXDATE exclusions, virtual instances in calendar/timeline
- Task Templates section in chapter 28 covering: creating, editing, deleting templates, "Create from Template" palette command, batch instantiation
- Review Workflows section in chapter 28 covering: the 4 seeded PPV workflows, launching from palette, step progression
- Cross-view drag and composable planning documented in context with calendar section
- Glossary entries for: Calendar View, Timeline View, Gantt Chart, Recurrence/RRULE, Task Template, Review Workflow, Scope Propagation, Cross-View Drag
- All 3 nav files updated if any new chapter entries are added

## Verification

- `grep -c "Calendar View\|Timeline.*View\|Map View" docs/guide/07-browsing-and-visualizing.md` returns >= 3
- `grep -c "Task Template\|Review Workflow" docs/guide/28-dashboards-and-workflows.md` returns >= 2
- `grep -c "Calendar View\|Timeline View\|Recurrence\|Task Template\|Review Workflow" docs/guide/appendix-d-glossary.md` returns >= 5
- `wc -l docs/guide/07-browsing-and-visualizing.md` shows substantial growth (target: 450+ lines, up from 295)
- Three-file sync: every numbered chapter in README.md has a matching entry in index.html and guide.html

## Tasks

- [ ] **T01: Add Calendar, Timeline, and Map View sections to chapter 7** `est:1h`
  - Why: Chapter 7 covers renderers but is missing the 3 newest ones (Calendar from M034, Timeline from M034, Map from M033)
  - Files: `docs/guide/07-browsing-and-visualizing.md`
  - Do: Add three new sections following the existing pattern (opening, features, interactions). Reference `calendar.js` for calendar interactions, `timeline_view.html` for Gantt config, `map_view.html` for Leaflet/cluster behavior. Include recurring tasks subsection under Calendar covering the recurrence editor presets, custom mode, and how recurring events appear. Include cross-view drag subsection under Calendar. Include composable planning note about side-by-side calendar+kanban.
  - Verify: `grep -c "^## " docs/guide/07-browsing-and-visualizing.md` returns >= 10 (was 7 sections); `grep -q "Calendar View" docs/guide/07-browsing-and-visualizing.md`
  - Done when: Chapter 7 has Calendar View, Timeline/Gantt View, and Map View sections with usage instructions matching actual codebase behavior

- [ ] **T02: Add Task Templates and Review Workflows to chapter 28** `est:45m`
  - Why: Task templates and review workflows are planning tools built on the dashboard/workflow system — they belong in chapter 28
  - Files: `docs/guide/28-dashboards-and-workflows.md`
  - Do: Add "Task Templates" section covering CRUD, the "Create from Template" palette command, batch instantiation with @slot: references. Add "Review Workflows" section covering the 4 seeded PPV workflows, launching from palette, step-by-step progression. Reference `backend/app/task_templates/` and `backend/app/dashboard/seed.py` for accurate details.
  - Verify: `grep -c "^## " docs/guide/28-dashboards-and-workflows.md` shows growth; `grep -q "Task Templates" docs/guide/28-dashboards-and-workflows.md`
  - Done when: Chapter 28 has Task Templates and Review Workflows sections with accurate feature descriptions

- [ ] **T03: Add glossary entries and verify three-file nav sync** `est:30m`
  - Why: Appendix D needs M034 terms; any new chapter entries must appear in all 3 nav files
  - Files: `docs/guide/appendix-d-glossary.md`, `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`
  - Do: Add glossary entries for Calendar View (editable), Timeline View, Gantt Chart, Recurrence/RRULE, Task Template, Review Workflow, Scope Propagation, Cross-View Drag. Since T01-T02 extend existing chapters (7 and 28) rather than creating new ones, nav files may not need new entries — but verify all existing entries are present and consistent across the 3 files. Fix any drift found.
  - Verify: `grep -c "Calendar View\|Timeline View\|Recurrence\|Task Template\|Review Workflow\|Gantt\|Cross-View" docs/guide/appendix-d-glossary.md` returns >= 7
  - Done when: Glossary has all M034 terms; 3 nav files are consistent with each other

## Files Likely Touched

- `docs/guide/07-browsing-and-visualizing.md`
- `docs/guide/28-dashboards-and-workflows.md`
- `docs/guide/appendix-d-glossary.md`
- `docs/guide/README.md` (verification only, possibly fix drift)
- `docs/guide/index.html` (verification only, possibly fix drift)
- `backend/app/templates/guide.html` (verification only, possibly fix drift)
