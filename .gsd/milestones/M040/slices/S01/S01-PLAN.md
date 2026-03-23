# S01: M034 User Guide Documentation

**Goal:** Every user-visible feature from M034 (Task Planning, Time-Blocking & Calendar UX) has guide documentation that a new user can follow.
**Demo:** Open the user guide → find sections on calendar editing, timeline view, recurring tasks, templates, and review workflows with usage instructions and screenshots.

## Background

M034 shipped these features with zero documentation:

1. **Editable calendar** — drag-to-reschedule, resize-to-change-duration, click-to-create tasks on calendar
2. **Timeline/Gantt view** — horizontal task bars with dependency arrows, zoom levels (day/week/month/quarter)
3. **Recurring tasks** — RRULE-based recurrence with virtual calendar instances, dashed-border visual treatment
4. **Recurrence editor** — presets (daily/weekdays/weekly/biweekly/monthly/custom) + EXDATE management
5. **Task templates** — named reusable patterns with "Create from Template" in command palette
6. **PPV review workflows** — Weekly/Monthly/Quarterly/Yearly review workflows launchable from command palette
7. **Cross-view drag** — drag tasks from kanban onto calendar to schedule them at the drop time
8. **Composable planning** — calendar + kanban side-by-side with shared scope context

## Existing Guide Structure

- `07-browsing-and-visualizing.md` — covers table/card/graph/kanban. Calendar and timeline are renderers of the same kind → extend this chapter.
- `28-dashboards-and-workflows.md` — covers dashboards and workflow stepper. Review workflows are workflows → extend this chapter.
- Task templates and recurrence editor are new concepts → may need new sections in chapter 5 (Working with Objects) or a new chapter.

## Must-Haves

- Calendar editing interactions documented (drag, resize, click-to-create) with keyboard/mouse instructions
- Timeline/Gantt view documented (opening it, reading dependency arrows, zoom controls, drag-to-reschedule)
- Recurring tasks documented (how to set recurrence on a task, what virtual instances look like, how to edit the master)
- Task templates documented (creating templates, using "Create from Template", what @slot: references do)
- Review workflows documented (launching from command palette, stepping through, what gets created)
- Cross-view drag documented (how to drag from kanban to calendar, what happens on drop)
- Composable planning documented (opening calendar + kanban side-by-side, scope synchronization)

## Tasks

- [ ] **T01: Write calendar and timeline guide sections** `est:45m`
  - Why: These are new renderers in chapter 7's scope — table/card/graph/kanban are documented but calendar and timeline are not
  - Files: `docs/guide/07-browsing-and-visualizing.md`
  - Do: Add ## Calendar View and ## Timeline View sections following the existing pattern (opening the view, toolbar, interactions, tips). Cover drag/resize/click-to-create for calendar, dependency arrows and zoom for timeline, and cross-view drag from kanban to calendar.
  - Verify: New sections exist with usage instructions for all calendar and timeline interactions
  - Done when: `grep -c "## Calendar View\|## Timeline View" docs/guide/07-browsing-and-visualizing.md` returns 2

- [ ] **T02: Write recurring tasks and recurrence editor guide sections** `est:30m`
  - Why: Recurrence is a task property — fits in chapter 5 (Working with Objects) or as a new subsection in calendar docs
  - Files: `docs/guide/07-browsing-and-visualizing.md` or `docs/guide/05-working-with-objects.md`
  - Do: Document how to set recurrence on a task (recurrence editor presets, custom RRULE, EXDATE), how virtual instances appear on the calendar (dashed borders, ↻ prefix), and how clicking a virtual instance navigates to the master task.
  - Verify: Recurrence documentation covers editor usage, visual treatment, and master task navigation
  - Done when: Guide contains recurrence documentation with editor presets listed

- [ ] **T03: Write task templates and review workflows guide sections** `est:30m`
  - Why: Templates are a new concept; review workflows extend chapter 28's workflow coverage
  - Files: `docs/guide/28-dashboards-and-workflows.md` and/or new section in `docs/guide/05-working-with-objects.md`
  - Do: Document task templates (what they are, creating from command palette, @slot: references, batch instantiation). Document PPV review workflows (launching Weekly/Monthly/Quarterly/Yearly from command palette, stepping through, what review objects are created).
  - Verify: Template and review workflow sections exist with step-by-step usage instructions
  - Done when: Guide contains template and review workflow documentation

## Files Likely Touched

- `docs/guide/07-browsing-and-visualizing.md` — new Calendar View and Timeline View sections
- `docs/guide/05-working-with-objects.md` — recurring tasks, possibly task templates
- `docs/guide/28-dashboards-and-workflows.md` — review workflows section
