---
depends_on: [M033]
---

# M034: Task Planning, Time-Blocking & Calendar UX

**Gathered:** 2026-03-21
**Status:** Queued — pending auto-mode execution

## Project Description

Transform SemPKM from a knowledge store into a daily operational hub by adding time-blocking to tasks, making the calendar view editable and interactive, building an open-source timeline/Gantt renderer, and enabling composable planning workflows that leverage PPV's existing review hierarchy.

## Why This Milestone

SemPKM has tasks (bpkm:Task with status/priority/dueDate), events (bpkm:Event with startDate/endDate), a kanban view (M031), and a basic calendar renderer (M033/S02 — read-only FullCalendar month/week/day). But there's no way to **plan** — to take a task from the backlog and assign it to a specific time slot on Tuesday afternoon. The calendar is read-only. Tasks have a dueDate (when it's due) but no concept of "when I intend to do it" — what PPV calls the "doDate" (ppv:doDate already exists on ActionItem).

Users who want weekly/daily planning currently leave SemPKM entirely. Sunsama, Todoist Upcoming, and Notion calendar views all solve this by letting users drag tasks onto time slots. SemPKM has all the building blocks (calendar renderer, kanban, dockview composability, SHACL forms, saved queries, dashboards) but they're not connected into a planning workflow.

PPV already models the full review hierarchy — ppv:WeeklyReview, ppv:MonthlyReview, ppv:QuarterlyReview, ppv:YearlyReview — with linking predicates between levels. These types exist in the ontology and shapes but have no dedicated UX beyond standard SHACL forms.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Add a scheduled start/end time to any task (time-blocking), distinct from the due date
- Drag tasks from the kanban or explorer onto the calendar to schedule them at specific time slots
- See tasks and events together on the calendar — tasks as colored blocks, events alongside
- Resize events/tasks on the calendar to change duration
- Click an empty time slot to create a new task scheduled at that time
- Open a timeline/Gantt view with horizontal bars and dependency arrows
- See project-scoped Gantt charts filtered by saved query
- Create recurring tasks with RRULE support
- Save task templates for common task patterns
- Run PPV weekly/monthly/quarterly/yearly review workflows
- Compose planning surfaces by opening calendar + kanban side by side in dockview

### Entry point / environment

- Entry point: http://localhost:3000/browser/ — calendar, kanban, timeline views, command palette
- Environment: Docker Compose (api + triplestore + frontend/nginx)
- Live dependencies involved: RDF4J triplestore, FullCalendar (vendored in M033)

## Completion Class

- Contract complete means: Task schema extended with scheduledStart/scheduledEnd, calendar accepts drops/resize, timeline renderer displays bars, recurring task RRULE stored and expanded, task templates work, review workflows create PPV objects
- Integration complete means: time-blocked tasks on calendar alongside synced Events, drag from kanban creates schedule, timeline shows real dependency graphs, review workflow uses real task data
- Operational complete means: scheduling data persists across restart, RRULE expansion without phantom objects, review workflows create properly-linked PPV objects

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User drags a task from kanban to Wednesday 2pm on the calendar. It shows as a 1-hour block.
- User opens timeline filtered to a project. Sees tasks as bars with dependency arrows. Dragging reschedules.
- Recurring task with FREQ=WEEKLY;BYDAY=FR shows next 4 Fridays without creating 4 objects.
- Calendar + kanban side by side share scope. Status change on kanban triggers calendar re-fetch.
- PPV weekly review workflow shows completed tasks, creates ppv:WeeklyReview linked to month.

## Risks and Unknowns

- **FullCalendar interaction plugin in htmx** — MIT-licensed @fullcalendar/interaction needs testing within htmx swap lifecycle. Current initCalendar() with tryInit polling suggests re-init is handled.
- **Custom timeline renderer** — Most code-heavy feature. vis-timeline (MIT) vs custom SVG — research needed.
- **Recurring task expansion** — Calendar endpoint generates virtual events from RRULE without creating objects. Same pattern as Google Calendar.
- **Cross-view drag-and-drop** — Kanban→calendar crosses dockview panels. stopPropagation() proven in kanban (M031) and canvas (M008).
- **FullCalendar Premium timeline licensed ($480)** — Building custom timeline instead. Free plugins cover calendar needs.
- **PPV doDate vs scheduledStart** — ppv:doDate (xsd:date, day only) on ActionItem. bpkm:scheduledStart/End (xsd:dateTime, hour level) on Task. Complementary: doDate is "which day", scheduledStart is "which hour".

## Existing Codebase / Prior Art

- `backend/app/views/service.py` — execute_calendar_query() on milestone/M033 branch. Returns FullCalendar JSON. Verified.
- `frontend/static/js/calendar.js` — M033/S02 read-only calendar (76 lines on M033 branch). No editable/droppable. Verified.
- `frontend/static/js/kanban.js` — HTML5 drag-drop with stopPropagation(). Verified on main.
- `models/basic-pkm/shapes/basic-pkm.jsonld` — TaskShape: 21 properties, bpkm:dueDate but no start/end time. Verified.
- `models/ppv/ontology/ppv.jsonld` — ppv:doDate ("When to DO the action"), 4 Review classes with linking predicates. Verified.
- `models/ppv/shapes/ppv.jsonld` — WeeklyReviewShape (startDate/endDate, cycle, focusObjective), MonthlyReviewShape (hasWeeklyReviews). Verified.
- `models/ppv/views/ppv.jsonld` — 19 ViewSpecs including "Review Calendar". Verified.
- `backend/app/workflow/` — WorkflowSpec stepper runner (M006). Review workflow reference.
- `backend/app/dashboard/registry.py` — BlockRegistry (M032). Planning dashboards composable.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions.

## Relevant Requirements

- New: PLAN-01 through PLAN-10+ covering time-blocking, editable calendar, timeline/Gantt, recurring tasks, templates, review workflows
- Existing deferred advanced: "Timeline/calendar renderers — v2+"
- PPV review types gain workflow UX

## Scope

### In Scope

**Data Model — Time-Blocking:**
- bpkm:scheduledStart/scheduledEnd (xsd:dateTime) on Task
- bpkm:estimatedDuration on Task
- TaskShape scheduling property group, basic-pkm v2.2.0
- Calendar data endpoint includes Tasks with scheduledStart
- ppv:doDate surfaced for date-only scheduling

**Editable Calendar:**
- @fullcalendar/interaction (MIT): editable, droppable, selectable
- Drag to reschedule, resize for duration, click-to-create
- External drag from kanban/explorer
- Tasks colored by priority, Events by source

**Timeline/Gantt Renderer:**
- New "Timeline" generic view (8th renderer, open-source)
- Horizontal bars, dependency arrows (bpkm:dependsOn)
- Project-scoped, day/week/month/quarter zoom
- Drag to reschedule, resize for duration
- Milestone markers as diamonds

**Recurring Tasks:**
- bpkm:recurrenceRule (RRULE string), virtual calendar instances
- Recurrence editor UI, EXDATE exception tracking
- Sync app RRULE preservation

**Task Templates:**
- Named templates in urn:sempkm:task-templates graph
- Title pattern, defaults, subtask structure
- "Create from Template" in command palette

**Planning Workflows (PPV Review):**
- Weekly/monthly/quarterly/yearly review workflows on WorkflowSpec runner
- Seed sample review workflows

**Composable Planning:**
- Calendar + kanban side by side, shared scope, cross-view events

### Out of Scope / Non-Goals

- Dedicated "My Day" view — compose from existing
- FullCalendar Premium timeline — custom instead
- Natural language scheduling — M035 AI copilot scope
- Pomodoro, focus mode, team scheduling
- Calendar sync write-back of scheduled times
- Mobile-specific layouts

## Technical Constraints

- htmx + vanilla JS. FullCalendar interaction is vanilla-compatible.
- Timeline must be MIT/Apache. No FullCalendar Premium.
- RRULE expansion at query time, not stored objects.
- Cross-dockview drag with stopPropagation() (proven pattern).
- basic-pkm changes additive only.

## Integration Points

- **FullCalendar (M033/S02)** — interaction upgrade
- **Kanban (M031/S04)** — drag source, shared patterns
- **ViewSpecService** — timeline as 8th renderer
- **Command API** — object.patch for scheduling
- **WorkflowSpec (M006)** — review workflows
- **PPV model** — review types, doDate
- **Saved queries** — shared scope
- **Dashboard system (M032)** — planning dashboards
- **Sync apps (M016-M024)** — RRULE preservation

## Open Questions

- **Timeline library** — vis-timeline vs custom SVG. Research during planning.
- **Recurring task exceptions** — EXDATE list (iCalendar) vs separate objects.
- **Cross-panel drag data** — IRI + title + estimatedDuration minimum.
- **Review week boundaries** — Monday–Sunday or configurable?
- **Calendar coloring** — By type or by priority?
