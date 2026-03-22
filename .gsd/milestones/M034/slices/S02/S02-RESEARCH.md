# S02 Research: Timeline / Gantt View

**Slice:** S02 — Timeline / Gantt View
**Milestone:** M034 — Task Planning, Time-Blocking & Calendar UX
**Depth:** Targeted — new library (Frappe Gantt) but well-established codebase view-renderer pattern

## Summary

This slice adds "timeline" as the 7th generic view renderer (joining table, card, graph, kanban, calendar, map). The work follows a well-established pattern: backend service builds SPARQL, endpoint returns JSON, template loads external library from CDN, library renders data. Frappe Gantt v1.2.2 (MIT, zero deps, ~50KB SVG) matches the CDN-loaded library pattern used by FullCalendar, Leaflet, and Cytoscape. The main novelty is the dependency-edge SPARQL query — all other pieces follow existing patterns exactly.

**Requirements owned:** PLAN-04 (Timeline/Gantt view with dependency arrows and zoom), PLAN-10 (Timeline project-scoped filtering via saved queries)

## Recommendation

Use Frappe Gantt v1.2.2 from CDN (`cdn.jsdelivr.net/npm/frappe-gantt@1.2.2/dist/frappe-gantt.umd.js` + CSS). Follow the calendar/map view renderer pattern exactly — IIFE in template, CDN lazy-load, JSON data fetch from `/browser/views/generic/timeline/data`. Scope to `bpkm:Task` type; build a SPARQL query that fetches task IRI, label, scheduledStart, scheduledEnd (with dueDate fallback for end), and `bpkm:dependsOn` edges for dependency arrows.

## Implementation Landscape

### Files to Create

| File | Purpose | Complexity |
|------|---------|------------|
| `backend/app/templates/browser/timeline_view.html` | Jinja2 template: CDN load Frappe Gantt, fetch JSON data, init chart | ~120 lines, follows calendar_view.html pattern |

### Files to Modify

| File | Change | Complexity |
|------|--------|------------|
| `backend/app/views/router.py` | Add `"timeline"` to `_VALID_RENDERERS` set; add `elif renderer == "timeline":` block in `generic_view()` and `generic_view_data()` | Medium — ~80 lines copying calendar/kanban pattern |
| `backend/app/views/service.py` | Add `_build_timeline_select()` and `execute_timeline_query()` methods | Medium — ~100 lines. New SPARQL pattern for dependency edges |
| `frontend/static/js/workspace.js` | Add `timeline: 'Timeline View'` to the `labels` map in `openGenericViewTab()` | 1 line |
| `frontend/static/css/views.css` | Frappe Gantt container sizing + dark mode overrides | ~60 lines |
| `backend/app/templates/browser/views_explorer.html` | Add Timeline View entry (same pattern as Calendar/Map) | ~8 lines |
| `e2e/helpers/selectors.ts` | Add `timeline: '[data-testid="timeline-view"]'` to `SEL.views` | 1 line |

### No Files to Create in `frontend/static/vendor/`

The roadmap says "vendored Frappe Gantt" but the codebase consistently uses CDN loading (FullCalendar from jsdelivr, Leaflet from unpkg, etc.). Follow the established CDN pattern. Pin to `@1.2.2` for reproducibility.

## Key Technical Details

### Frappe Gantt Task Format

Frappe Gantt accepts an array of task objects:

```javascript
{
  id: 'urn:sempkm:...',         // Task IRI
  name: 'Task Label',           // Display name
  start: '2024-01-15',          // YYYY-MM-DD (date only)
  end: '2024-01-20',            // YYYY-MM-DD
  progress: 0,                  // 0-100 (no progress tracking in bpkm, use 0 or derive from status)
  dependencies: ['urn:...'],    // Array of task IDs this depends on
  custom_class: 'priority-high' // Optional CSS class for coloring
}
```

**Date format constraint:** Frappe Gantt expects `YYYY-MM-DD` date strings. `bpkm:scheduledStart` is `xsd:dateTime` (e.g., `2024-01-15T14:00:00`). The backend must strip the time portion, or the frontend must extract `substring(0, 10)`.

**Dependencies:** The `dependencies` array uses task IDs (our IRIs). Frappe Gantt renders arrows automatically.

### SPARQL Query for Timeline Data

The timeline query must fetch:
1. Task IRI, label, start/end dates (scheduledStart/scheduledEnd preferred, fallback to dueDate)
2. Dependency edges: `?s bpkm:dependsOn ?dep`
3. Optional: priority for color coding, status for progress indication

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX bpkm: <urn:sempkm:model:basic-pkm:>

SELECT ?s ?label ?startDate ?endDate ?dep ?priority ?status
WHERE {
  ?s rdf:type <TYPE_IRI> .
  ?s <START_PATH> ?startDate .
  OPTIONAL { ?s <END_PATH> ?endDate }
  OPTIONAL { ?s bpkm:dependsOn ?dep }
  OPTIONAL { ?s bpkm:taskPriority ?priority }
  OPTIONAL { ?s bpkm:taskStatus ?status }
  OPTIONAL { ?s rdfs:label|dcterms:title ?label }
}
```

**Multi-row handling:** A task with 3 dependencies yields 3 rows. The `execute_timeline_query()` method must group by task IRI and collect dependency IRIs into an array.

### Frappe Gantt Key Configuration Options

```javascript
new Gantt('#timeline-container', tasks, {
  view_mode: 'Week',
  view_mode_select: true,                    // Built-in zoom level selector
  view_modes: ['Day', 'Week', 'Month', 'Year'],
  bar_height: 30,
  column_width: 45,
  move_dependencies: true,                    // Move dependent tasks when parent moves
  readonly_progress: true,                    // No progress drag (we don't track %)
  scroll_to: 'today',                        // Auto-scroll to today
  today_button: true,                        // "Today" button
  popup_on: 'click',                         // Show popup on click
  on_date_change: function(task, start, end) { /* PATCH endpoint */ },
  on_click: function(task) { /* openTab(iri, label) */ },
});
```

### Dark Mode CSS Overrides

Frappe Gantt uses CSS variables. Override with `[data-theme="dark"]` following the FullCalendar/Leaflet pattern:

```css
[data-theme="dark"] .gantt-container { background: var(--color-surface); }
[data-theme="dark"] .gantt .grid-background { fill: var(--color-surface); }
[data-theme="dark"] .gantt .grid-header { fill: var(--color-surface-raised); }
[data-theme="dark"] .gantt .bar-label { fill: var(--color-text); }
[data-theme="dark"] .gantt .lower-text, 
[data-theme="dark"] .gantt .upper-text { fill: var(--color-text-muted); }
[data-theme="dark"] .gantt .arrow { stroke: var(--color-text-muted); }
```

Frappe Gantt also supports CSS variables like `--gv-grid-height`, `--gv-bar-height`, etc.

### Container Sizing

Timeline needs full-height like graph and kanban. Use the existing `.view-flex-column` wrapper with `flex:1; min-height:0` on the container. The container div needs an explicit `height` or Frappe Gantt's `container_height: 'auto'` option.

### Drag-to-Reschedule Persistence

Frappe Gantt's `on_date_change(task, start, end)` fires on drag/resize. Reuse the existing `POST /browser/views/calendar/patch` endpoint — it already handles Task type detection and maps to `bpkm:scheduledStart`/`bpkm:scheduledEnd`. The `start`/`end` from Frappe Gantt are JS Date objects; convert to ISO strings.

### Scope Query Filtering

Follows exact same pattern as calendar/kanban/map — `scope_query` URL param resolves to a SPARQL WHERE body via `extract_scope_where_body()`, injected as a sub-select in the timeline query. The view toolbar already includes the scope dropdown when `user_saved_queries`/`model_saved_queries` are passed.

### Type-Agnostic Design

Like calendar and kanban, timeline should work for any type with date fields. Use the existing `_detect_date_fields()` to find start/end. Dependency detection: scan SHACL properties for `sh:class` pointing to the same type (self-referential object properties). `bpkm:dependsOn` is the primary case, but the detection should generalize.

However, for the initial implementation, hardcoding `bpkm:dependsOn` is simpler and lower-risk. Generalized dependency detection can be a follow-up. The kanban view started with general `sh:in` detection (Knowledge entry: "Kanban status field detection uses SHACL sh:in"), so precedent exists for either approach.

**Recommendation:** Start with hardcoded `bpkm:dependsOn` for dependencies but use `_detect_date_fields()` for start/end fields (already general). This matches the risk profile — date detection is proven, dependency detection is novel.

## Natural Task Seams

1. **Backend data layer** (service + router) — Can be built and unit-tested independently of any frontend. Produces the JSON data contract.
2. **Frontend template + CSS** — Depends on the data contract from T01 but not on E2E infrastructure. Self-contained rendering work.
3. **Integration wiring** (explorer entry, workspace.js label, E2E selectors) — Small additions across multiple files, best done together.
4. **Verification** — E2E tests that prove the whole pipeline.

The natural split: T01 = backend (service methods + router endpoint + unit tests), T02 = frontend (template + CSS + explorer entry + workspace.js), T03 = E2E verification.

## What to Build First

**Backend data endpoint (T01)** is the foundation. Everything else depends on having the `/browser/views/generic/timeline` route working and returning JSON. Unit tests prove the SPARQL construction and result mapping without needing a running stack.

**Riskiest piece:** The SPARQL query for dependencies. A task with N dependencies produces N rows; the grouping logic in `execute_timeline_query()` must handle this correctly. The test for this is straightforward but the query must be right.

## Verification Strategy

**Unit tests** (in `backend/tests/test_timeline.py`):
- `_build_timeline_select()` produces correct SPARQL with and without scope filter
- `execute_timeline_query()` groups multi-row dependency results correctly
- Date fallback: tasks with only `dueDate` (no scheduledStart) still appear with dueDate as start
- Tasks without any dates are excluded
- Empty result returns `{"tasks": [], "dependencies": []}`

**E2E test** (in `e2e/specs/`):
- Navigate to Timeline view via `openGenericViewTab('timeline')`
- Wait for `[data-testid="timeline-view"]` or `.gantt-container` to appear
- Verify task bars rendered (check for `.bar-wrapper` SVG elements)
- Verify dependency arrows present (check for `.arrow` SVG elements)
- Zoom level selector functional (change view mode)

**Manual verification:**
- Open Timeline view, see task bars
- Dependency arrows connect tasks correctly
- Drag a bar to reschedule — calendar PATCH endpoint updates dates
- Dark mode renders correctly
- Scope query filters tasks

## Pitfalls & Constraints

1. **Frappe Gantt requires at least one task** — If the SPARQL query returns empty, render an empty-state message instead of initializing Gantt with `[]` (may error). Same pattern as calendar/kanban empty states.

2. **Date-only vs datetime** — Frappe Gantt expects `YYYY-MM-DD`. scheduledStart is xsd:dateTime (`2024-01-15T14:00:00Z`). Slice the string to 10 chars in the backend transform, or `task.start.substring(0, 10)` in JS.

3. **Dependency IRI matching** — Frappe Gantt's `dependencies` array must contain IDs that match other task `id` fields exactly. Since we use full IRIs as IDs, dependency IRIs must match. Tasks referenced in `dependencies` but not present in the task list will be silently ignored by Frappe Gantt (no error, just no arrow).

4. **`bpkm:dependsOn` is multi-valued** — The SHACL shape has no `sh:maxCount`, so a single task can have multiple dependencies. Each produces an extra row in SPARQL results. The grouping must collect all `?dep` values per task IRI.

5. **`on_date_change` returns JS Date objects** — Need `date.toISOString()` or manual YYYY-MM-DD formatting before sending to the PATCH endpoint. The calendar PATCH endpoint expects ISO 8601 strings.

6. **Container height in dockview panels** — Same issue as graph/kanban views. Use `.view-flex-column` wrapper and `flex:1; min-height:0` on the Gantt container div. Set `container_height: 'auto'` in Frappe Gantt options, or set explicit CSS height.

7. **Frappe Gantt global constructor** — The UMD bundle exposes `window.Gantt`. Calendar uses `window.FullCalendar`. Same CDN lazy-load + `if (typeof Gantt !== 'undefined')` pattern.

## Relevant Skills

None needed — this work uses standard vanilla JS + Python patterns already in the codebase. No React, SwiftUI, or other framework-specific skills apply.
