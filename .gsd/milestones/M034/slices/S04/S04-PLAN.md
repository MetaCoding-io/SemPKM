# S04: Recurring Tasks & RRULE Expansion

**Goal:** Tasks with RRULE recurrence rules produce virtual calendar instances without creating real objects. A recurrence editor UI lets users set presets or custom rules. Exception dates (EXDATE) exclude specific occurrences.
**Demo:** Create task "Weekly Review" with FREQ=WEEKLY;BYDAY=FR. Calendar shows next 4+ Fridays as task blocks. Click one — opens the master task. Edit recurrence to add EXDATE for next Friday — that instance disappears.

## Must-Haves

- `bpkm:recurrenceRule` and `bpkm:exceptionDates` properties on TaskShape with ontology declarations
- `python-dateutil` dependency added to backend
- `_expand_rrule()` function generating virtual occurrences from RRULE string within a date window
- `execute_calendar_query()` expanded to produce virtual events for recurring tasks
- Virtual events have synthetic IDs, point back to master task IRI, and are visually distinguished
- Recurrence editor UI with presets (daily, weekdays, weekly, biweekly, monthly, custom) and EXDATE picker
- Clicking a virtual calendar event opens the master task
- Unit tests for RRULE expansion (happy path, EXDATE, COUNT, UNTIL, malformed, max cap)
- E2E test verifying recurring task shows multiple calendar instances

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (Docker stack with triplestore for calendar data query)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rrule_expansion.py -v` — all pass
- `npx playwright test e2e/tests/02-views/recurring-tasks.spec.ts` — all pass
- Virtual events rendered on calendar with recurring indicator CSS class
- Recurrence editor popover builds valid RRULE strings from UI selections
- Malformed RRULE in test returns empty expansion with logged warning (graceful degradation check)

## Observability / Diagnostics

- Runtime signals: `[calendar]` console.log for RRULE expansion count; `logger.info` in `execute_calendar_query` reporting virtual event count
- Inspection surfaces: Calendar data JSON endpoint (`/browser/views/generic/calendar/data?merged=true`) returns virtual events with `isVirtual: true` in extendedProps
- Failure visibility: Malformed RRULE logged as warning, returns empty expansion (graceful degradation)
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: S01's `scheduledStart`/`scheduledEnd` on TaskShape, `calendar.js` editable calendar, `execute_calendar_query()`/`execute_merged_calendar_query()` in view service, SHACL form renderer `_field.html`
- New wiring introduced in this slice: `python-dateutil` dependency, `_expand_rrule()` in service, recurrence editor JS + template, virtual event class in calendar.js
- What remains before the milestone is truly usable end-to-end: S05 (task templates + review workflows)

## Tasks

- [x] **T01: Add recurrence schema properties and python-dateutil dependency** `est:30m`
  - Why: All other tasks need the schema properties and the dateutil library. Docker rebuild required for the new dependency.
  - Files: `models/basic-pkm/shapes/basic-pkm.jsonld`, `models/basic-pkm/ontology/basic-pkm.jsonld`, `backend/pyproject.toml`
  - Do: Add `bpkm:recurrenceRule` (xsd:string, sh:order 6.4, TaskDatesGroup) and `bpkm:exceptionDates` (xsd:string, sh:order 6.5, TaskDatesGroup) to TaskShape. Add `bpkm:exceptionDates` owl:DatatypeProperty to ontology. Update `bpkm:recurrenceRule` domain to cover both Event and Task. Add `python-dateutil~=2.9.0` to pyproject.toml dependencies.
  - Verify: `python3 -c "import json; d=json.load(open('models/basic-pkm/shapes/basic-pkm.jsonld')); [print(p.get('sh:path',{}).get('@id','')) for item in d['@graph'] if item.get('@id')=='bpkm:TaskShape' for p in item.get('sh:property',[])]" | grep -q recurrenceRule && grep -q python-dateutil backend/pyproject.toml`
  - Done when: TaskShape has both recurrence properties at correct orders; ontology has exceptionDates declaration and recurrenceRule domain covers Task; pyproject.toml lists python-dateutil

- [x] **T02: Implement backend RRULE expansion and unit tests** `est:1.5h`
  - Why: Core slice logic — expands RRULE strings into virtual calendar events. Must handle edge cases (malformed, EXDATE, COUNT, UNTIL, max cap).
  - Files: `backend/app/views/service.py`, `backend/tests/test_rrule_expansion.py`
  - Do: Add `_expand_rrule()` method to ViewSpecService. Extend `_build_calendar_select()` to OPTIONAL-fetch `?recurrenceRule` and `?exceptionDates`. Extend `execute_calendar_query()` to detect recurrenceRule bindings and generate virtual events with synthetic IDs (`{iri}__recurrence__{isodate}`), `isVirtual: true`, and `masterIri` in extendedProps. Use ±6 month default window, max 52 instances per task. Write comprehensive unit tests.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_rrule_expansion.py -v` — all pass
  - Done when: `_expand_rrule()` correctly handles FREQ=WEEKLY, EXDATE, COUNT, UNTIL, malformed input; `execute_calendar_query()` returns virtual events for recurring items; all tests green

- [x] **T03: Build recurrence editor UI with presets and EXDATE picker** `est:1.5h`
  - Why: Users need a friendly way to create RRULE strings instead of typing raw RFC 5545. The editor hooks into the SHACL form's text input for recurrenceRule.
  - Files: `frontend/static/js/recurrence-editor.js`, `backend/app/templates/browser/recurrence_editor.html`, `frontend/static/css/views.css`, `backend/app/templates/forms/_field.html`
  - Do: Create `recurrence-editor.js` with `window.initRecurrenceEditor(inputEl)` — adds a button next to the input that opens a popover. Popover has preset radio buttons (Daily, Weekdays, Weekly, Biweekly, Monthly, Custom). Custom mode: frequency selector, interval, day-of-week checkboxes, end condition (never/after N/until date). Display human-readable summary on the input. Add EXDATE section with date inputs and add/remove. Create Jinja2 partial `recurrence_editor.html` included from `_field.html` when property path contains `recurrenceRule`. Add CSS for popover, presets, day checkboxes, EXDATE list.
  - Verify: Form field for recurrenceRule renders with editor button; selecting "Weekly" preset produces `FREQ=WEEKLY`; custom mode with BYDAY produces correct RRULE string
  - Done when: Recurrence editor popover opens from form field, presets generate correct RRULE strings, EXDATE editor adds/removes dates, human-readable summary shown on input

- [x] **T04: Wire virtual event rendering in calendar and write E2E test** `est:1h`
  - Why: Connects backend expansion to frontend rendering. Virtual recurring events need visual distinction and click-to-open-master behavior. E2E test proves the full stack.
  - Files: `frontend/static/js/calendar.js`, `frontend/static/css/views.css`, `e2e/tests/02-views/recurring-tasks.spec.ts`
  - Do: In `calendar.js` `eventClassNames`, add `fc-event-recurring` class when `extendedProps.isVirtual` is true. In `eventClick`, if `extendedProps.masterIri` exists, open that instead of `extendedProps.iri`. Add CSS for recurring indicator (↻ icon or dashed border). Write E2E test: create task with scheduledStart + recurrenceRule via API, open calendar, verify multiple events for single task, verify clicking virtual event opens master.
  - Verify: `npx playwright test e2e/tests/02-views/recurring-tasks.spec.ts` — all pass
  - Done when: Virtual recurring events show recurring indicator on calendar; clicking opens master task; E2E test passes end-to-end

## Files Likely Touched

- `models/basic-pkm/shapes/basic-pkm.jsonld`
- `models/basic-pkm/ontology/basic-pkm.jsonld`
- `backend/pyproject.toml`
- `backend/app/views/service.py`
- `backend/tests/test_rrule_expansion.py`
- `frontend/static/js/recurrence-editor.js`
- `frontend/static/js/calendar.js`
- `frontend/static/css/views.css`
- `backend/app/templates/browser/recurrence_editor.html`
- `backend/app/templates/forms/_field.html`
- `e2e/tests/02-views/recurring-tasks.spec.ts`
