---
verdict: needs-attention
remediation_round: 0
---

# Milestone Validation: M034

## Success Criteria Checklist

- [x] **Tasks have scheduledStart/scheduledEnd/estimatedDuration properties; setting them places the task on the calendar as a colored block** — `models/basic-pkm/shapes/basic-pkm.jsonld` contains all 3 properties on TaskShape (sh:order 6.1–6.3). `manifest.yaml` version is 2.2.0. S01 summary confirms color-coded calendar rendering with merged Events + Tasks query. 23 unit tests pass in `test_calendar_editable.py`.

- [x] **Users drag tasks onto calendar time slots (or from kanban) to schedule them; resize to change duration; click empty slots to create tasks** — S01 delivered `eventDrop`, `eventResize`, and `select` handlers in `calendar_view.html` with FullCalendar `editable: true` and `selectable: true`. Calendar PATCH endpoint persists via `object.patch` through command dispatch pipeline. S01 summary and test suite confirm.

- [x] **A timeline/Gantt view shows tasks as horizontal bars with dependency arrows, filterable by project or saved query** — S02 delivered Frappe Gantt integration as the 7th generic view renderer. `_build_timeline_select()` and `execute_timeline_query()` with dependency grouping. 15 unit tests pass in `test_timeline.py`. E2E tests pass for rendering, dependency arrows (state:'attached' for SVG), and zoom switching. `timeline_view.html` template exists with drag-to-reschedule and zoom level support.

- [x] **Recurring tasks with RRULE strings show virtual instances on the calendar without creating real objects** — S04 delivered `_expand_rrule()` using `python-dateutil~=2.9.0` (added to `pyproject.toml`). Virtual events use synthetic IDs (`{iri}__recurrence__{isodate}`) with `extendedProps.isVirtual` and `masterIri`. 24 unit tests pass in `test_rrule_expansion.py`. 2 E2E tests in `recurring-tasks.spec.ts`. CSS dashed-border + ↻ indicator on virtual events.

- [x] **Task templates exist as named reusable patterns with default properties and subtask structures** — S05 delivered `TaskTemplateService` in `backend/app/task_templates/` with full CRUD against `urn:sempkm:task-templates` named graph. Batch instantiation with `@slot:` references. REST API endpoints. 21 unit tests pass in `test_task_templates.py`. Command palette "Create from Template" parent with dynamic API children confirmed in `workspace.js`.

- [x] **PPV weekly/monthly/quarterly/yearly review workflows run via the existing WorkflowSpec stepper** — S05 delivered 4 seed workflow definitions in `backend/app/dashboard/seed.py` (Weekly, Monthly, Quarterly, Yearly Review) with per-name idempotency. 10 seed tests pass in `test_seed_data.py`. 4 review workflow launcher commands in command palette confirmed in `workspace.js`.

- [x] **Calendar + kanban side by side share scope context — status change on kanban triggers calendar re-fetch** — S03 delivered `sempkm:scope-changed` custom event in `workspace.js`, with listeners in `calendar.js` and `kanban.js` that re-fetch data. Self-trigger prevention via panel ID comparison. E2E tests pass for cross-view drag and scope propagation.

- [x] **Recurrence editor UI exists** — `frontend/static/js/recurrence-editor.js` exports `window.initRecurrenceEditor()` and `window.initExdateEditor()`. Presets (Daily, Weekdays, Weekly, Biweekly, Monthly, Custom), custom RRULE builder, EXDATE picker. Lazy-loaded via `_field.html` conditional.

- [x] **External drag from kanban or explorer to calendar schedules a task at the drop time** — S03 delivered `__calendarDragPayload` side-channel in `calendar.js`, kanban dragstart enrichment with IRI/label/duration in `kanban.js`. FullCalendar `droppable: true` with external drop handler. E2E test and backend unit tests confirm.

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | Editable calendar + task time-blocking schema + merged Events+Tasks query | scheduledStart/scheduledEnd/estimatedDuration on TaskShape v2.2.0; merged calendar query; PATCH endpoint; FullCalendar editable mode; 23 unit tests | **pass** |
| S02 | Timeline/Gantt view with Frappe Gantt, dependency arrows, drag-to-reschedule, zoom | 7th generic renderer; `_build_timeline_select()` + `execute_timeline_query()`; Frappe Gantt CDN template; dark mode CSS; 15 unit + 3 E2E tests | **pass** |
| S03 | Cross-view drag (kanban→calendar) + scope-changed propagation | `__calendarDragPayload` side-channel; `sempkm:scope-changed` event; self-trigger prevention; E2E + backend unit tests | **pass** |
| S04 | Recurring tasks with RRULE expansion, recurrence editor UI, EXDATE support | `_expand_rrule()` with python-dateutil; virtual events; recurrence-editor.js; lazy-load wiring; 24 unit + 2 E2E tests | **pass** |
| S05 | Task templates with CRUD + instantiation; PPV review workflow seeds + command palette | TaskTemplateService package; REST API; 4 seed workflows; command palette entries; template picker partial; 21 unit + 10 seed tests | **pass** |

## Cross-Slice Integration

| Boundary | Expected | Actual | Status |
|----------|----------|--------|--------|
| S01 → S02: scheduledStart/scheduledEnd for timeline bar positioning | S02 consumes S01's scheduling properties | `_detect_date_fields()` priority puts scheduledStart first; timeline SPARQL uses it | ✅ |
| S01 → S03: Editable calendar as drop target | S03 uses S01's FullCalendar with `droppable: true` | `calendar.js` reads `__calendarDragPayload` and calls PATCH endpoint | ✅ |
| S01 → S04: Calendar rendering merges virtual events | S04's `_expand_rrule()` produces events consumed by S01's calendar | `execute_calendar_query()` calls expansion, returns merged list | ✅ |
| S01 → S05: Task type with scheduling properties for templates | S05 templates target bpkm:Task class | Templates create Tasks via dispatch pipeline with scheduling fields | ✅ |
| S02 → S01: Calendar PATCH endpoint reuse | S02 timeline reuses S01's PATCH endpoint for drag-to-reschedule | Confirmed: timeline calls `/browser/views/calendar/patch` | ✅ |
| S03 → S01: scope-changed triggers calendar re-fetch | S03 dispatches `sempkm:scope-changed` | `calendar.js` listener re-fetches with updated scope_query param | ✅ |

No boundary mismatches found.

## Requirement Coverage

| ID | Requirement | Addressed By | Evidence | Status |
|---|---|---|---|---|
| PLAN-01 | Task time-blocking | S01 | 3 properties on TaskShape, 23 unit tests | ✅ validated |
| PLAN-02 | Editable calendar | S01 | FullCalendar editable mode, PATCH endpoint | ✅ validated |
| PLAN-03 | External drag to calendar | S03 | kanban→calendar drag, E2E test | ✅ validated |
| PLAN-04 | Timeline/Gantt view | S02 | Frappe Gantt, 15 unit + 3 E2E tests | ✅ validated |
| PLAN-05 | Recurring tasks (RRULE) | S04 | _expand_rrule(), recurrence editor, 24 unit + 2 E2E | ✅ validated |
| PLAN-06 | Task templates | S05 | TaskTemplateService, REST API, 21 unit tests | ✅ validated |
| PLAN-07 | PPV review workflows | S05 | 4 seed workflows, 10 seed tests, palette entries | ✅ validated |
| PLAN-08 | Composable planning | S03 | scope-changed event, cross-view listeners | ✅ validated |
| PLAN-09 | Calendar shows tasks+events with color coding | S01 | merged query, color CSS classes | ✅ validated |
| PLAN-10 | Timeline project-scoped filtering | S02 | scope_query parameter in timeline data endpoint | ✅ validated |

All 10 requirements addressed. No orphaned or unaddressed requirements.

## Attention Items

These are minor observations that do not block completion:

1. **UAT placeholders** — S01, S02, S03, and S05 have auto-generated placeholder UAT scripts ("Doctor created this placeholder"). S04 has a real UAT script. This is a process gap — the slices were verified through contract testing (99 passing unit tests + E2E tests) and summary attestation, but human-oriented UAT scripts were not written for 4 of 5 slices.

2. **CDN dependencies** — Both FullCalendar (S01) and Frappe Gantt (S02) are loaded from CDN at runtime. CDN outage breaks both views. The M029 vendor pipeline exists but wasn't used for these libraries. This is documented as a known limitation in both slice summaries.

3. **Template management UI** — S05 delivers API-only template CRUD (no create/edit/delete UI). Templates are created and managed via API calls. The command palette "Create from Template" provides the consumption UI but not the authoring UI. This is noted in S05's known limitations.

4. **Vendored Frappe Gantt** — The boundary map planned `frontend/static/vendor/frappe-gantt.min.js` but S02 used CDN instead. The file was not vendored. This is a minor deviation from the plan but functionally equivalent.

## Verdict Rationale

**Verdict: needs-attention**

All 9 success criteria are met. All 5 slices delivered their planned outputs with verification. All 10 requirements are addressed. Cross-slice integration points align correctly. 99 unit tests and multiple E2E tests pass on the current codebase.

The "needs-attention" (rather than "pass") is due to:
- 4 of 5 UAT scripts are placeholders — the human verification surface was not prepared, though automated contract tests cover the same ground
- CDN dependencies create a runtime fragility not present in other views

These are documentation and infrastructure hygiene items, not functional gaps. No remediation slices are needed — the milestone's definition of done is substantively met.

## Remediation Plan

None required. The attention items are process improvements for future milestones, not blocking issues for M034.
