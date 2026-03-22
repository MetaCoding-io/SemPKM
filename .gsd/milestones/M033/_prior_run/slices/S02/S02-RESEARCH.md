# S02 Research: Calendar View Renderer

**Depth:** Targeted — known technology (FullCalendar), established codebase patterns (renderer registry, lazy-load, generic view endpoint)

---

## Summary

Calendar view follows the exact same integration pattern as kanban: register in `RENDERER_REGISTRY`, add to `_VALID_RENDERERS`, add an `elif renderer == "calendar"` branch in `generic_view()`, create a template, write a JS init function, add a CSS section. FullCalendar 6.x is ideal — single global bundle (`index.global.min.js`), CSS is self-injected (no separate stylesheet needed), and the `FullCalendar.Calendar` constructor + `calendar.render()` API is straightforward. The main novel work is date property auto-detection from SHACL shapes and the SPARQL calendar query builder.

---

## Recommendation

**Approach:** Follow the kanban pattern exactly. Five tasks matching the roadmap decomposition.

**FullCalendar vendoring:** Use the `fullcalendar` npm package (v6.1.20) which bundles core + interaction + daygrid + timegrid + list + multimonth. It provides `index.global.min.js` (~180KB minified) that registers the `FullCalendar` global. Unlike Yasgui, FullCalendar v6 self-injects its CSS from the JS bundle — **no separate CSS file needed in the build pipeline**. This simplifies the build.js addition (one JS bundle, no CSS bundle).

**Date detection:** Scan SHACL `PropertyShape.datatype` for `xsd:date` and `xsd:dateTime`. Also match well-known date paths (`schema:startDate`, `schema:endDate`) even without explicit datatype (Event shape omits datatype on these). Prefer `schema:startDate` > `bpkm:dueDate` > `dcterms:created` as the default start-date property. Allow user override via query param.

---

## Implementation Landscape

### Files to Create
| File | Purpose |
|------|---------|
| `backend/app/templates/browser/calendar_view.html` | Jinja2 template — FullCalendar container, init script, month/week/day toolbar |
| `frontend/static/js/calendar.js` | `initCalendar(containerId, dataUrl, options)` function — FullCalendar init, event click → `openTab()`, dark mode CSS variable overrides |
| `frontend/static/css/views.css` (append) | `.calendar-container` styles, `.calendar-toolbar` for view switcher |

### Files to Modify
| File | Change |
|------|--------|
| `backend/app/views/registry.py` | Add `"calendar"` entry to `RENDERER_REGISTRY` with template `browser/calendar_view.html` |
| `backend/app/views/router.py` | Add `"calendar"` to `_VALID_RENDERERS` set; add `elif renderer == "calendar"` branch in `generic_view()`; add calendar data JSON endpoint |
| `backend/app/views/service.py` | Add `_detect_date_fields()` method (parallel to `_detect_status_field()`); add `execute_calendar_query()` method; add `_build_calendar_select()` static method |
| `backend/app/templates/browser/views_explorer.html` | Add Calendar View entry (tree-leaf with onclick `openGenericViewTab('calendar')`) |
| `frontend/static/js/workspace.js` | Add `'calendar'` to the `labels` dict in `openGenericViewTab()` |
| `frontend/package.json` | Add `"fullcalendar": "6.1.20"` dependency |
| `frontend/build.js` | Add section for FullCalendar bundle (copy `index.global.min.js`, content-hash, add to manifest as `fullcalendar.js`) — **no CSS section needed** |

### Key Integration Points

**Renderer Registry** (`registry.py`):
```python
"calendar": {
    "type": "calendar",
    "template": "browser/calendar_view.html",
}
```

**Generic View Branch** (`router.py` `generic_view()`): The calendar branch needs to:
1. Call `_detect_date_fields(type_iri)` to find start/end date properties
2. Build a SPARQL SELECT query fetching `?s ?label ?startDate ?endDate ?type`
3. Execute and transform results into FullCalendar event JSON format
4. Pass events + date field metadata to the template

**Calendar Data Endpoint**: New `GET /browser/views/generic/calendar/data` returning JSON array of FullCalendar events:
```json
[{"id": "<iri>", "title": "Event Name", "start": "2025-03-15", "end": "2025-03-16", "extendedProps": {"iri": "<iri>", "type": "bpkm:Event"}}]
```

**FullCalendar Lazy Load** (same D272 pattern as Yasgui/Chart.js):
- `build.js`: Read `fullcalendar/index.global.min.js` from node_modules, content-hash it, write to dist, add `fullcalendar.js` manifest entry
- Template loads via `{{ 'fullcalendar.js' | asset_url }}` with CDN fallback `https://cdn.jsdelivr.net/npm/fullcalendar@6.1.20/index.global.min.js`
- **Critical v6 difference**: No CSS file needed. FullCalendar v6 self-injects its styles from the JS bundle.

**Date Property Auto-Detection** (new `_detect_date_fields()` on ViewSpecService):
- Uses `ShapesService.get_form_for_type(type_iri)` — same pattern as `_detect_status_field()`
- Scans `PropertyShape.datatype` for `http://www.w3.org/2001/XMLSchema#date` and `http://www.w3.org/2001/XMLSchema#dateTime`
- Also matches well-known paths: `schema:startDate`, `schema:endDate`, `bpkm:dueDate`, `bpkm:targetDate`
- Priority for start date: path containing "start" > "due" > "target" > "created"
- Priority for end date: path containing "end" > "completed" > "modified"
- Returns `(start_property: PropertyShape, end_property: PropertyShape | None)`

**Types with date data** (from SHACL shapes scan):
| Type | Start-like | End-like |
|------|-----------|----------|
| bpkm:Event | schema:startDate | schema:endDate |
| bpkm:Project | schema:startDate (xsd:date) | schema:endDate (xsd:date) |
| bpkm:Task | bpkm:dueDate (xsd:date) | bpkm:completedDate (xsd:date) |
| bpkm:Milestone | bpkm:targetDate (xsd:date) | bpkm:completedDate (xsd:date) |
| All types | dcterms:created (xsd:dateTime) | dcterms:modified (xsd:dateTime) |

**Note on Event shape**: `schema:startDate` and `schema:endDate` on EventShape have **no explicit sh:datatype** — they accept both xsd:date and xsd:dateTime. The detection logic must also match by path name, not just datatype.

**Seed data**: basic-pkm has 4+ Event seed objects with `schema:startDate`/`schema:endDate` values. Projects also have date ranges. Calendar view will have data immediately on a fresh install with basic-pkm.

### Dark Mode

FullCalendar v6 uses CSS custom properties (prefixed `--fc-*`). Override these in the `.dark` theme scope:
```css
.dark .calendar-container {
    --fc-border-color: var(--color-border);
    --fc-page-bg-color: var(--color-bg);
    --fc-neutral-bg-color: var(--color-bg-elevated);
    --fc-today-bg-color: var(--color-bg-accent-subtle);
    --fc-event-bg-color: var(--color-accent);
    --fc-event-text-color: var(--color-text-on-accent);
}
```

### Saved View Support

The existing save view mechanism (`saveCurrentView()` in view_toolbar.html) already captures `renderer_type` from the toolbar's `data-renderer` attribute. Adding `"calendar"` to `_VALID_RENDERERS` and including the toolbar in the calendar template automatically enables save/restore for calendar views. The `openGenericViewTab('calendar')` path in `workspace-layout.js` is also automatic once `labels` dict is extended.

---

## Constraints & Risks

1. **Bundle size**: `fullcalendar` global bundle is ~180KB minified. Acceptable for lazy-load (same order as Yasgui). Pre-compression (.gz) will reduce to ~45KB transfer.

2. **Container visibility**: FullCalendar, like Cytoscape, requires a visible container at `render()` time. The dockview panel may not be visible when the htmx swap occurs. Use the same `tryInit()` polling pattern from `graph_view.html` — retry until container has non-zero dimensions.

3. **Date format normalization**: SPARQL returns dates as typed literals. `xsd:date` values are `"2025-03-15"` and `xsd:dateTime` values are `"2025-03-15T10:00:00"`. FullCalendar accepts both ISO formats natively — no conversion needed.

4. **"All types" calendar**: When no type filter is selected, the calendar must query across all types that have date properties. This requires a UNION query or multiple OPTIONAL patterns. Recommend: if no type selected, default to types with `schema:startDate` (Events + Projects), falling back to `dcterms:created` for everything else.

5. **Event shape startDate has no datatype**: Detection must not rely solely on `sh:datatype`. Path-based matching (`schema:startDate`, `schema:endDate`) is necessary as a fallback.

---

## Task Decomposition Guidance

The roadmap's 5-task decomposition is well-structured. Recommended execution order:

1. **T01 — Vendor FullCalendar**: `npm install fullcalendar@6.1.20`, add build.js section, verify `fullcalendar.js` appears in manifest. No CSS section needed (v6 self-injects). Quick verification: `node build.js` succeeds.

2. **T02 — Registry + Router + Service**: Register renderer, add to valid set, add `_detect_date_fields()` + `execute_calendar_query()` + `_build_calendar_select()` to service, add `elif renderer == "calendar"` branch + data endpoint to router. This is the core backend work.

3. **T03 — Calendar SPARQL query builder**: Already part of T02's service methods. Could merge with T02 or keep separate if the date detection logic proves complex. The `_detect_date_fields()` follows `_detect_status_field()` pattern exactly.

4. **T04 — Template + JS + CSS**: `calendar_view.html` template, `calendar.js` init function, CSS additions to `views.css`. Template loads FullCalendar via `asset_url` with CDN fallback, renders a container div, inline script calls `initCalendar()`. The JS function creates `new FullCalendar.Calendar()` with `eventClick` wired to `openTab()`.

5. **T05 — Explorer entry + saved view**: Add tree-leaf to `views_explorer.html`, extend `labels` dict in `workspace.js`. Saved view support is mostly automatic from the toolbar include.

**Verification**: Open calendar view in browser, confirm events render on date grid, click event → object tab opens, type filter narrows results, month/week/day toggle works, dark mode renders correctly.
