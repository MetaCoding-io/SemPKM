# S03 Research: Calendar View

## Summary

Calendar view is a well-understood extension of the existing view renderer system. The pattern is proven by four prior renderers (table, card, graph, kanban). FullCalendar 6 global bundle is a single CDN script, no separate CSS needed. The only non-trivial piece is date field detection from SHACL shapes — `bpkm:Event`'s `schema:startDate`/`schema:endDate` have **no `sh:datatype`** in the shapes file, requiring a fallback heuristic.

## Requirement Coverage

| Requirement | Description | How this slice addresses it |
|-------------|-------------|----------------------------|
| CAL-01 | Calendar view renders objects with date properties on FullCalendar grid | Core deliverable — template + JS init + SPARQL data endpoint |
| CAL-02 | Month/week/day view switching | FullCalendar `headerToolbar` right buttons: `dayGridMonth,timeGridWeek,timeGridDay` |
| CAL-03 | Event click opens object tab | `eventClick` handler calls `openTab(iri, label)` |

## Recommendation

**Targeted depth.** Follow the kanban view pattern exactly. Five changes:

1. **Backend**: Add `"calendar"` to `_VALID_RENDERERS`, add `_detect_date_fields()` method, add `execute_calendar_query()` method, add `elif renderer == "calendar":` branch in `generic_view()`
2. **Template**: Create `calendar_view.html` following graph/kanban pattern (view-flex-column, type_filter_pills, view_toolbar, lazy-load FullCalendar CDN, init script)
3. **CSS**: Calendar container styles in `views.css` — full-height flex child + FullCalendar theme overrides for dark mode
4. **Frontend JS**: Add `calendar: 'Calendar View'` to labels dict in `openGenericViewTab`, add Calendar View entry in `views_explorer.html`
5. **Calendar data endpoint**: `/browser/views/generic/calendar/data` returning JSON `{events: [{id, title, start, end, allDay, extendedProps: {iri}}]}` — fetched by the template's init script

## Implementation Landscape

### Files to create
| File | Purpose |
|------|---------|
| `backend/app/templates/browser/calendar_view.html` | Template: flex-column + type pills + toolbar + calendar container + lazy-load FullCalendar + init script |

### Files to modify
| File | Change | Size |
|------|--------|------|
| `backend/app/views/router.py` | Add `"calendar"` to `_VALID_RENDERERS`; add `elif renderer == "calendar":` in `generic_view()`; add `/generic/calendar/data` JSON endpoint | ~80 lines |
| `backend/app/views/service.py` | Add `_detect_date_fields()` and `execute_calendar_query()` methods | ~80 lines |
| `frontend/static/css/views.css` | Calendar container `.calendar-container` flex child + dark-mode FullCalendar overrides | ~40 lines |
| `frontend/static/js/workspace.js` | Add `calendar: 'Calendar View'` to labels dict (line ~3474) | 1 line |
| `frontend/static/js/workspace-layout.js` | No change needed — `generic-view` handler is renderer-agnostic already | 0 lines |
| `backend/app/templates/browser/views_explorer.html` | Add Calendar View tree-leaf entry following Kanban View pattern | ~7 lines |
| `e2e/helpers/dockview.ts` | Add `'calendar'` to `renderer` union type | 1 line |
| `e2e/helpers/selectors.ts` | Add `calendar: '[data-testid="calendar-view"]'` to `SEL.views` | 1 line |

### Key patterns to follow

**Date field detection (`_detect_date_fields`)** — analogous to `_detect_status_field`:
- Iterate `form.properties` from `ShapesService.get_form_for_type(type_iri)`
- Match `prop.datatype` in `{xsd:date, xsd:dateTime}` (covers Project, Task, Milestone)
- **Also** match well-known path IRIs: `schema:startDate`, `schema:endDate`, `bpkm:dueDate`, `bpkm:completedDate`, `bpkm:targetDate` — even when `sh:datatype` is absent (covers Event)
- Return `(start_field: PropertyShape, end_field: PropertyShape | None)` — prefer `startDate`/`endDate` pairs, fall back to single date field
- Priority: `schema:startDate` > paths containing "start" > `bpkm:dueDate` > `dcterms:created`

**SPARQL calendar query:**
```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?s ?label ?startDate ?endDate ?allDay
WHERE {
  ?s rdf:type <{type_iri}> .
  ?s <{start_path}> ?startDate .
  {scope_clause}
  OPTIONAL { ?s rdfs:label|dcterms:title ?label }
  OPTIONAL { ?s <{end_path}> ?endDate }
  OPTIONAL { ?s <bpkm:allDay> ?allDay }
}
```

**JSON response format** (maps directly to FullCalendar event objects):
```json
{
  "events": [
    {
      "id": "urn:sempkm:...",
      "title": "Team Meeting",
      "start": "2026-03-15T10:00:00",
      "end": "2026-03-15T11:00:00",
      "allDay": false,
      "extendedProps": { "iri": "urn:sempkm:..." }
    }
  ],
  "date_fields": {
    "start": { "path": "schema:startDate", "name": "Start Date" },
    "end": { "path": "schema:endDate", "name": "End Date" }
  }
}
```

**FullCalendar initialization** (in template `<script>` block):
```javascript
function loadCalendar(dataUrl) {
  var script = document.createElement('script');
  script.src = 'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.17/index.global.min.js';
  script.onload = function() {
    fetch(dataUrl, { credentials: 'include' })
      .then(r => r.json())
      .then(function(data) {
        var calEl = document.getElementById('calendar-container');
        var cal = new FullCalendar.Calendar(calEl, {
          initialView: 'dayGridMonth',
          headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
          },
          events: data.events,
          eventClick: function(info) {
            info.jsEvent.preventDefault();
            var iri = info.event.extendedProps.iri;
            var title = info.event.title;
            if (typeof openTab === 'function') openTab(iri, title);
          }
        });
        cal.render();
      });
  };
  document.head.appendChild(script);
}
```

**Template structure:**
```html
<div class="view-flex-column">
{% if is_generic | default(false) %}
{% include "browser/type_filter_pills.html" %}
{% endif %}
{% include "browser/view_toolbar.html" %}

{# Calendar-specific: no-type or no-date-fields empty states #}
{% if error_message %}
<div class="view-empty-state">
    <p>{{ error_message }}</p>
</div>
{% else %}
<div id="calendar-container" class="calendar-container" data-testid="calendar-view"></div>
{% endif %}
</div>

<script>
(function() {
  var dataUrl = {{ calendar_data_url | tojson }};
  // lazy-load FullCalendar then fetch events
  loadCalendar(dataUrl);
})();
</script>
```

### FullCalendar dark mode

FullCalendar 6 uses CSS variables with `.fc` prefix. Override for dark mode:
```css
[data-theme="dark"] .fc {
  --fc-border-color: var(--color-border);
  --fc-page-bg-color: var(--color-bg);
  --fc-neutral-bg-color: var(--color-bg-secondary);
  --fc-list-event-hover-bg-color: var(--color-bg-hover);
  --fc-today-bg-color: rgba(var(--accent-rgb), 0.08);
  --fc-event-bg-color: var(--color-accent);
  --fc-event-border-color: var(--color-accent);
  --fc-event-text-color: #fff;
}
```

### Empty states

Two empty states, same as kanban:
1. **No type selected**: "Select a type to use Calendar View" — when `type_iri` is empty
2. **No date fields**: "This type has no date properties for Calendar display" — when `_detect_date_fields` returns None
3. **No events**: FullCalendar handles this natively — shows empty grid, no special handling needed

### Event type data availability

`bpkm:Event` is the best candidate — has `schema:startDate`, `schema:endDate`, `bpkm:allDay`. Also viable:
- `bpkm:Project` — `schema:startDate`, `schema:endDate` (xsd:date)
- `bpkm:Task` — `bpkm:dueDate` (xsd:date, single date, no end)
- `bpkm:Milestone` — `bpkm:targetDate` (xsd:date, single date)

### Critical detail: Event shape dates have no sh:datatype

The Event shape's `schema:startDate` and `schema:endDate` properties have **no `sh:datatype`** declaration in `basic-pkm.jsonld`. The shapes parser sets `PropertyShape.datatype = None` for these. In contrast, Project's same properties have `sh:datatype: xsd:date`.

The `_detect_date_fields()` method MUST check both:
1. `prop.datatype in {"http://www.w3.org/2001/XMLSchema#date", "http://www.w3.org/2001/XMLSchema#dateTime"}`
2. Well-known date path IRIs: `schema:startDate`, `schema:endDate`, `bpkm:dueDate`, etc.

Without the path heuristic, Event — the primary calendar use case — would show "no date properties."

## Task Boundaries

### T01: Backend — date detection + calendar query + router
- Add `_detect_date_fields()` to `ViewSpecService`
- Add `execute_calendar_query()` to `ViewSpecService`
- Add `"calendar"` to `_VALID_RENDERERS`
- Add `elif renderer == "calendar":` branch in `generic_view()`
- Add `/generic/calendar/data` JSON data endpoint
- **Verify:** pytest unit test for `_detect_date_fields` against Event, Project, Task, Note (no dates)

### T02: Frontend — template, CSS, explorer, workspace integration
- Create `calendar_view.html` template
- Add calendar CSS to `views.css` (container + dark mode overrides)
- Add `calendar: 'Calendar View'` to workspace.js labels
- Add Calendar View entry in `views_explorer.html`
- **Verify:** Start dev stack, open Calendar View from sidebar, see FullCalendar render with Event data. Month/week/day switching works. Click event → opens object tab.

### T03: E2E test
- Add `'calendar'` to dockview helper renderer union
- Add `calendar` selector to `SEL.views`
- Write E2E spec: open calendar view → verify FullCalendar rendered → switch views → click event → verify object tab opens
- **Verify:** `npx playwright test calendar` passes

### Dependency chain
T01 is independent. T02 depends on T01 (needs the endpoint). T03 depends on T02.
