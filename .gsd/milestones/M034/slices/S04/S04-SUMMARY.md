# S04: Recurring Tasks & RRULE Expansion — Summary

## Outcome

Delivered end-to-end recurring task support: tasks with RFC 5545 RRULE strings produce virtual calendar instances without creating real objects. A recurrence editor UI provides presets and custom RRULE building. Exception dates (EXDATE) exclude specific occurrences. 24 unit tests + 2 E2E tests pass.

## What Was Built

### Schema (T01)
- Added `bpkm:recurrenceRule` (xsd:string, sh:order 6.4) and `bpkm:exceptionDates` (xsd:string, sh:order 6.5) to TaskShape in `TaskDatesGroup`
- Expanded `bpkm:recurrenceRule` ontology domain to `owl:unionOf [Event, Task]` — both events and tasks share the property
- Added `bpkm:exceptionDates` as `owl:DatatypeProperty` in the ontology
- Added `python-dateutil~=2.9.0` to backend dependencies

### Backend RRULE Expansion (T02)
- `ViewSpecService._expand_rrule()` — static method that parses RFC 5545 RRULE strings via `dateutil.rrule.rrulestr`, applies EXDATE exclusions via `rruleset.exdate()`, and returns occurrences within a ±6 month window (max 52 instances per task)
- `_build_calendar_select()` extended with OPTIONAL SPARQL clauses for `recurrenceRule` and `exceptionDates`
- `execute_calendar_query()` generates virtual events with:
  - Synthetic IDs: `{iri}__recurrence__{isodate}`
  - `extendedProps.isVirtual: true` flag
  - `extendedProps.masterIri` pointing back to the real task
  - Computed start/end preserving original duration
  - Master event's original date skipped to avoid duplicate rendering
- Graceful degradation: malformed RRULE logged as warning, returns empty expansion

### Recurrence Editor UI (T03)
- `recurrence-editor.js` — IIFE exporting `initRecurrenceEditor(inputEl)` and `initExdateEditor(inputEl)`
- Preset radio buttons: Daily, Weekdays, Weekly, Biweekly, Monthly, Custom
- Custom mode: frequency dropdown, interval input, day-of-week checkbox grid (weekly), end condition (never / after N / until date)
- Reverse-parses existing RRULE to pre-select matching preset
- Human-readable summary overlay (e.g., "Every Friday", "Every 2 weeks")
- EXDATE editor: date list with add/remove, "N exceptions" summary
- Popover appended to `document.body` with `position:fixed` to escape dockview stacking context
- Lazy-loaded via `_field.html` conditional — only fetched when a form contains `recurrenceRule` or `exceptionDates` fields
- Guard attributes (`data-rrule-init`, `data-exdate-init`) prevent double-init on htmx re-swap

### Calendar Integration (T04)
- `calendar.js` — `fc-event-recurring` CSS class on virtual events; click handler routes to `masterIri` instead of virtual event's synthetic ID
- CSS: dashed border + `↻` prefix on recurring event titles
- Fixed pre-existing `/static/js/` → `/js/` path bug in `calendar_view.html` and `_field.html` that broke all calendar JS loading
- Fixed htmx script race condition in `calendar_view.html` — replaced `<script src>` with lazy-load pattern (createElement + onload)

### Tests
- 24 unit tests in `test_rrule_expansion.py`: 12 for `_expand_rrule()` (weekly, daily, monthly, EXDATE, COUNT, UNTIL, malformed, max cap, outside window), 2 for SPARQL query structure, 10 for virtual event generation
- 2 E2E tests in `recurring-tasks.spec.ts`: virtual instances rendered on calendar, clicking virtual event opens master task
- 22 existing calendar tests (`test_calendar.py`) continue passing

## Key Files

| File | Change |
|---|---|
| `models/basic-pkm/shapes/basic-pkm.jsonld` | recurrenceRule + exceptionDates on TaskShape |
| `models/basic-pkm/ontology/basic-pkm.jsonld` | exceptionDates property; recurrenceRule domain expanded |
| `backend/pyproject.toml` | python-dateutil~=2.9.0 |
| `backend/app/views/service.py` | `_expand_rrule()`, SPARQL OPTIONAL clauses, virtual event generation |
| `backend/tests/test_rrule_expansion.py` | 24 unit tests |
| `frontend/static/js/recurrence-editor.js` | RRULE preset/custom editor + EXDATE picker |
| `frontend/static/js/calendar.js` | Virtual event CSS class + masterIri click routing |
| `frontend/static/css/views.css` | Recurrence editor styles + `.fc-event-recurring` indicator |
| `backend/app/templates/forms/_field.html` | Lazy-load wiring for recurrence editors |
| `backend/app/templates/browser/calendar_view.html` | JS path fix + lazy-load pattern |
| `e2e/tests/02-views/recurring-tasks.spec.ts` | 2 E2E tests |

## Key Decisions

- **Naive datetimes throughout RRULE expansion** — `dateutil.rruleset.between()` raises TypeError on mixed naive/aware comparison. All expansion uses `datetime.now(timezone.utc).replace(tzinfo=None)` for UTC-based naive datetime.
- **owl:unionOf for recurrenceRule domain** — preserves semantic clarity that both Event and Task can have recurrence rules, rather than dropping the domain entirely.
- **Comma-separated EXDATE string** — simpler parsing than multi-valued RDF property; single `xsd:string` value with comma-delimited ISO dates.
- **Popover to document.body** — follows established pattern (D293) for escaping dockview stacking context.
- **Lazy script loading** — `_field.html` creates `<script>` elements on demand rather than adding to base template; only loads when the form actually has recurrence fields.

## Patterns for Downstream

- Virtual events use `{iri}__recurrence__{isodate}` synthetic IDs — any code processing calendar event IDs should check for `__recurrence__` to identify virtual events
- `extendedProps.isVirtual` and `extendedProps.masterIri` are the canonical signals for frontend code to distinguish virtual from real events
- The lazy-load pattern in `_field.html` (check if function exists → create script → call on load) can be reused for future field-specific JS enhancements
- Recurrence editor functions are on `window` — `window.initRecurrenceEditor(inputEl)` and `window.initExdateEditor(inputEl)` — callable from any context

## What Remains

- S05 (Task Templates & Review Workflows) completes M034
- The recurrence editor has not been exercised against the live Docker stack beyond E2E — visual polish of the summary overlay alignment may need refinement
- FullCalendar's `eventContent` hook could render richer recurring event UI (e.g., "2 of 4" occurrence indicator) — not needed for the current scope

## Verification Results

| Check | Result |
|---|---|
| `cd backend && .venv/bin/python -m pytest tests/test_rrule_expansion.py -v` | ✅ 24/24 passed |
| `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` | ✅ 22/22 passed (no regressions) |
| `npx playwright test e2e/tests/02-views/recurring-tasks.spec.ts` | ✅ 2/2 passed |
| Schema: TaskShape has recurrenceRule (order 6.4) + exceptionDates (order 6.5) | ✅ verified |
| Ontology: exceptionDates exists, recurrenceRule domain covers Event + Task | ✅ verified |
| python-dateutil in pyproject.toml | ✅ verified |
| calendar.js has fc-event-recurring class + masterIri routing | ✅ verified |
| views.css has .fc-event-recurring styles | ✅ verified |
| recurrence-editor.js syntax valid | ✅ verified |
| _field.html has lazy-load wiring for recurrenceRule/exceptionDates | ✅ verified |
