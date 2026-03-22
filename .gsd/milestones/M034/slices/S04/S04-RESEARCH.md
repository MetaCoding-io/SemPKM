# S04 Research: Recurring Tasks & RRULE Expansion

**Slice:** Recurring Tasks & RRULE Expansion
**Depth:** Targeted — known technology (RFC 5545 RRULE), new to this codebase, moderate integration surface

## Summary

This slice adds RRULE-based recurrence support to Tasks: schema properties (`bpkm:recurrenceRule`, `bpkm:exceptionDates`), backend expansion of RRULE strings into virtual calendar events via `python-dateutil`, and a recurrence editor UI. The pattern mirrors how Google Calendar synced events already use `bpkm:recurrenceRule` on EventShape — we're extending the same concept to Tasks.

The work divides into four natural seams:
1. **Schema** — 2 new properties on TaskShape + ontology declarations
2. **Backend** — `python-dateutil` dependency + RRULE expansion in calendar query pipeline
3. **Frontend editor** — Recurrence editor popover/modal with presets
4. **Integration** — Virtual recurring events rendered on calendar, E2E test

## Recommendation

Build bottom-up: schema first (trivial, enables everything), then backend RRULE expansion with unit tests (riskiest — must handle edge cases), then frontend recurrence editor, then E2E integration test.

## Implementation Landscape

### 1. Schema Changes (basic-pkm shapes + ontology)

**What exists:**
- `bpkm:recurrenceRule` already exists in the ontology (`owl:DatatypeProperty`, domain `bpkm:Event`, range `xsd:string`)
- EventShape has `bpkm:recurrenceRule` at `sh:order 13` in `bpkm:EventScheduleGroup`
- TaskShape has `bpkm:TaskDatesGroup` (order 2) with scheduling properties at orders 6.1–6.3

**What to add:**
- `bpkm:recurrenceRule` property on TaskShape — `xsd:string`, `sh:maxCount 1`, `sh:order 6.4`, `bpkm:TaskDatesGroup`
- `bpkm:exceptionDates` property on TaskShape — `xsd:string`, `sh:maxCount 1`, `sh:order 6.5`, `bpkm:TaskDatesGroup`
- Ontology: `bpkm:exceptionDates` as new `owl:DatatypeProperty` (domain: `bpkm:Task`, range: `xsd:string`)
- Ontology: Update `bpkm:recurrenceRule` domain — either remove domain restriction (OWL open world) or add `bpkm:Task` as additional domain via `owl:unionOf`

**Format conventions:**
- `recurrenceRule` stores the RFC 5545 RRULE string, e.g. `FREQ=WEEKLY;BYDAY=FR` (without `RRULE:` prefix — consistent with EventShape's existing help text)
- `exceptionDates` stores comma-separated ISO 8601 date strings, e.g. `2026-04-03,2026-04-10` — simpler than RFC 5545 EXDATE format, parseable with basic string splitting
- No version bump needed — manifest already at 2.2.0 from S01

### 2. Backend: python-dateutil + RRULE Expansion

**Dependency addition:**
- Add `python-dateutil~=2.9.0` to `backend/pyproject.toml` dependencies
- Docker rebuild required for this change (see CLAUDE.md: "Rebuild needed: pyproject.toml (deps)")

**RRULE expansion function — `_expand_rrule()`:**
```python
from dateutil.rrule import rrulestr, rruleset
from datetime import datetime, date

def _expand_rrule(
    rrule_str: str,
    dtstart: datetime,
    range_start: datetime,
    range_end: datetime,
    exdates: list[str] | None = None,
    max_instances: int = 52,
) -> list[datetime]:
```

Key API from python-dateutil:
- `rrulestr(rule_string, dtstart=dtstart)` — parses RRULE string into rrule object
- `rruleset()` — container for rrule + exdate
- `set.rrule(rule)` — add recurrence rule
- `set.exdate(dt)` — add exception date
- `set.between(after, before, inc=True)` — get occurrences in range
- Falls back gracefully for malformed RRULE (log warning, return empty list)

**Integration point — `execute_calendar_query()` and `execute_merged_calendar_query()`:**

Current flow:
1. `_build_calendar_select()` builds SPARQL → fetches `?s ?label ?startDate ?endDate`
2. `execute_calendar_query()` maps bindings to FullCalendar events
3. `execute_merged_calendar_query()` iterates Event + Task types, merges results

RRULE expansion hooks into step 1–2:
1. Extend `_build_calendar_select()` to also fetch `?recurrenceRule` and `?exceptionDates` (OPTIONAL clauses)
2. In `execute_calendar_query()`, after mapping bindings to events:
   - For any event with a non-empty `recurrenceRule`, generate virtual instances
   - Virtual events get a synthetic ID like `{original_iri}__recurrence__{iso_date}` — FullCalendar needs unique IDs
   - Virtual events share the original's title, color, extendedProps (including `iri` pointing to the master task)
   - Virtual events get `start`/`end` computed from the RRULE occurrence + original duration
   - The original master event is included too (if it falls in the range — which it does since it has `startDate`)
   - Mark virtual events with `extendedProps.isVirtual: true` and `extendedProps.masterIri: originalIri`

**Calendar data endpoint** already accepts implicit date range from FullCalendar fetch. Currently no `start`/`end` query params are used — all events are returned. For RRULE expansion, we need a date window:
- Option A: Accept `start` and `end` query params from FullCalendar's `events` function (it sends these automatically when using a URL source)
- Option B: Default to ±6 months from today for expansion window
- **Recommendation: Option A** — FullCalendar automatically sends `start` and `end` params when the event source is a URL. The current implementation uses a one-shot fetch instead of a URL source, so this may need adjustment in `calendar.js` to use FullCalendar's built-in refetch mechanism.

**Actually — reviewing calendar.js more carefully:** The current implementation does a one-shot `fetch(dataUrl)` and passes `data.events` as a static array. For RRULE expansion to work with date ranges, either:
- (a) Switch to FullCalendar's URL event source (`events: dataUrl`) — FullCalendar will auto-append `start` and `end` params, OR
- (b) Keep the one-shot fetch but expand RRULE with a generous default window (±6 months)

Option (b) is simpler and doesn't break the existing fetch pattern. Max 52 instances per recurring task is plenty.

**Edge cases to handle:**
- Malformed RRULE string → log warning, skip expansion, return master event only
- No `scheduledStart` on recurring task → can't expand (RRULE needs a dtstart)
- `exceptionDates` with dates that don't match any occurrence → silently ignored
- COUNT-limited rules (e.g., `FREQ=WEEKLY;COUNT=10`) → respect COUNT
- UNTIL-limited rules → respect UNTIL date
- Infinite rules without COUNT/UNTIL → clamp to `max_instances`

### 3. Frontend: Recurrence Editor

**Purpose:** A UI for building RRULE strings from user-friendly presets, attached to the `bpkm:recurrenceRule` form field.

**Approach — standalone JS module (`recurrence-editor.js`):**
- Export `window.initRecurrenceEditor(inputEl)` — enhances a text input with a button that opens a popover
- The popover contains preset radio buttons (Daily, Weekdays, Weekly, Biweekly, Monthly, Custom)
- Custom mode shows: frequency selector (daily/weekly/monthly/yearly), interval number, day-of-week checkboxes (for weekly), end condition (never/after N/until date)
- On confirm, writes the RRULE string to the input's value
- On the input, display a human-readable summary instead of raw RRULE (e.g., "Every Friday" instead of "FREQ=WEEKLY;BYDAY=FR")

**EXDATE editor:** Below the RRULE section, show a list of exception dates with add/remove. Each date is an `<input type="date">`. Values stored as comma-separated ISO dates in the `exceptionDates` input.

**Integration with SHACL form:**
- The SHACL form renderer generates a plain `<input type="text">` for `bpkm:recurrenceRule` (it's xsd:string)
- `recurrence-editor.js` can use `MutationObserver` or be called from the object tab's init code to find inputs with `data-property-path` containing `recurrenceRule` and enhance them
- Alternative: add a Jinja2 template check for the property path and render the recurrence editor widget directly

**No external JS library needed.** RRULE strings are simple enough to construct from presets:
```javascript
// Presets map
const PRESETS = {
  'daily':     'FREQ=DAILY',
  'weekdays':  'FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR',
  'weekly':    'FREQ=WEEKLY',
  'biweekly':  'FREQ=WEEKLY;INTERVAL=2',
  'monthly':   'FREQ=MONTHLY',
};
```

**Calendar recurring event indicators:**
- Virtual recurring events on the calendar should show a small repeat icon (↻) in the title or a CSS class for visual distinction
- FullCalendar `eventClassNames` already checks `extendedProps.sourceType` — extend to also check `extendedProps.isVirtual`
- Clicking a virtual event should open the master task (the `iri` in extendedProps points to the master)

### 4. Verification

**Unit tests (`backend/tests/test_rrule_expansion.py`):**
- `_expand_rrule()` with FREQ=WEEKLY;BYDAY=FR → correct Friday dates
- `_expand_rrule()` with EXDATE → excluded date missing from results
- `_expand_rrule()` with COUNT=5 → exactly 5 results
- `_expand_rrule()` with UNTIL=date → no results past that date
- `_expand_rrule()` with malformed string → empty list, no exception
- `_expand_rrule()` with max_instances cap → respects limit
- `execute_calendar_query()` with recurrenceRule in bindings → virtual events in output
- Virtual event IDs follow `{iri}__recurrence__{date}` pattern
- Virtual events have `isVirtual: true` and `masterIri` in extendedProps

**E2E test (`e2e/tests/02-views/recurring-tasks.spec.ts`):**
- Create a task with `scheduledStart` and `recurrenceRule` via API
- Open calendar view
- Verify multiple instances appear on calendar (more than 1 event for the single task)
- Verify clicking a virtual instance opens the master task

## File Inventory

### Files to Create
| File | Purpose |
|------|---------|
| `frontend/static/js/recurrence-editor.js` | RRULE builder UI with presets, EXDATE editor |
| `backend/app/templates/browser/recurrence_editor.html` | Jinja2 partial for recurrence editor popover markup |
| `backend/tests/test_rrule_expansion.py` | Unit tests for `_expand_rrule()` and calendar query integration |
| `e2e/tests/02-views/recurring-tasks.spec.ts` | E2E test for recurring task calendar rendering |

### Files to Modify
| File | Change |
|------|--------|
| `backend/pyproject.toml` | Add `python-dateutil~=2.9.0` to dependencies |
| `models/basic-pkm/shapes/basic-pkm.jsonld` | Add `bpkm:recurrenceRule` and `bpkm:exceptionDates` to TaskShape |
| `models/basic-pkm/ontology/basic-pkm.jsonld` | Add `bpkm:exceptionDates` declaration; update `bpkm:recurrenceRule` domain |
| `backend/app/views/service.py` | Add `_expand_rrule()` method; extend `_build_calendar_select()` to fetch recurrenceRule/exceptionDates; extend `execute_calendar_query()` to generate virtual events |
| `frontend/static/js/calendar.js` | Add `fc-event-recurring` class for virtual events; handle click on virtual event to open master task |
| `frontend/static/css/views.css` | Recurring event indicator styles; recurrence editor popover styles |

### Files to NOT Touch
| File | Reason |
|------|--------|
| `models/basic-pkm/manifest.yaml` | Already at 2.2.0 from S01 — no version bump needed |
| `backend/app/views/router.py` | No router changes needed — expansion happens inside service layer |
| `frontend/static/js/kanban.js` | Kanban doesn't show recurring instances |

## Key Risks

1. **python-dateutil requires Docker rebuild** — The dependency addition is the only change requiring `docker compose build`. All other changes are hot-reloadable via volume mounts.

2. **RRULE parsing edge cases** — Malformed strings from manual editing or broken sync data. The `_expand_rrule()` function must wrap `rrulestr()` in try/except and return empty list on failure.

3. **Performance of expansion in merged calendar query** — If many tasks have recurrence rules, expanding all of them adds latency. The `max_instances=52` cap per task and the ±6 month window prevent runaway expansion. For a typical user with 5-10 recurring tasks, this adds <50ms.

4. **Virtual event click routing** — FullCalendar's `eventClick` handler must distinguish virtual events (open master) from real events (open self). The `extendedProps.masterIri || extendedProps.iri` pattern handles this.

## Task Decomposition Suggestion

| Task | Scope | Est |
|------|-------|-----|
| T01: Schema + dependency | Add properties to shapes/ontology, add python-dateutil to pyproject.toml | small |
| T02: Backend RRULE expansion | `_expand_rrule()`, extend calendar SPARQL + event mapping, unit tests | medium |
| T03: Recurrence editor UI | `recurrence-editor.js`, editor template, CSS, integration with SHACL form | medium |
| T04: Calendar integration + E2E | Virtual event rendering, click routing, recurring indicators, E2E test | small |

T01 must come first (Docker rebuild). T02 depends on T01. T03 is independent of T02 (pure frontend). T04 depends on T02+T03.
