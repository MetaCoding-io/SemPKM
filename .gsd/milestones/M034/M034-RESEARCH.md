# M034 Research: Task Planning, Time-Blocking & Calendar UX

Research completed 2026-03-22. Key findings:

- FullCalendar standard CDN bundle already includes @fullcalendar/interaction — no new script needed, just enable `editable: true`, `droppable: true`, `selectable: true`
- Frappe Gantt (MIT, zero deps, ~50KB, SVG) recommended over vis-timeline for timeline/Gantt renderer — built-in dependency arrows, drag/resize, zoom levels
- bpkm:Task needs scheduledStart/scheduledEnd/estimatedDuration added to TaskShape (basic-pkm v2.2.0, additive only)
- bpkm:Event already has recurrenceRule (RFC 5545 RRULE) + recurringEventId from calendar sync apps
- Cross-panel drag proven in kanban (stopPropagation) and canvas (text/iri dataTransfer) — same pattern for calendar drops
- python-dateutil needed for backend RRULE expansion; rrule.js available for frontend recurrence editor
- WorkflowSpec stepper runner supports PPV review workflows via existing step types (view, form, dashboard)

Risk ordering: Schema+EditableCalendar → Timeline/Gantt → RecurringTasks → CrossViewIntegration → Templates+Workflows
