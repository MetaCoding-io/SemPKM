# S03 Research: Cross-View Drag & Composable Planning

## Summary

S03 adds two capabilities: (1) dragging tasks from kanban cards or explorer tree onto the calendar to schedule them, and (2) shared scope context between views so a filter change in one propagates to sibling views. Both are medium-complexity integration work using established patterns. The key technical challenge is FullCalendar's external drop API requiring coordination with HTML5 native drag-and-drop across dockview panel boundaries — but both the drag source (kanban) and the drag infrastructure (canvas `text/iri` + `stopPropagation()`) are proven.

## Requirements Targeted

From M034 Roadmap:
- **PLAN-03** — External drag to calendar (kanban/explorer → calendar drop scheduling)
- **PLAN-08** — Composable planning (calendar + kanban side by side, shared scope, cross-view events)
- **PLAN-09** — Calendar shows tasks and events together with color coding (S01 delivered this; S03 extends with external drops)

## Recommendation

**Targeted research** depth was appropriate. All patterns exist in the codebase. The primary integration risk (cross-dockview-panel HTML5 drag → FullCalendar drop) has two well-documented approaches (FullCalendar `Draggable` wrapper vs raw `drop` with `dataTransfer`). The raw `drop` approach is simpler and aligns with existing kanban/canvas patterns.

## Implementation Landscape

### What Exists

**Kanban drag source** (`frontend/static/js/kanban.js`, 144 lines):
- HTML5 `dragstart` sets `e.dataTransfer.setData('text/plain', card.dataset.iri)` and `effectAllowed = 'move'`
- `e.stopPropagation()` on `dragstart`, `dragover`, `drop` prevents dockview interference
- Cards have `draggable="true"` and `data-iri="{{ item.iri }}"` — but NO `data-title` or `data-duration` attributes
- Drop handler patches status via `POST /api/commands` with `object.patch`

**Explorer tree drag source** (`backend/app/templates/browser/tree_children.html`):
- Inline `ondragstart` sets `text/iri`, `text/label` MIME types AND `window.__canvasDragPayload` side-channel
- Supports multi-select bulk drag via `window.getSelectedIris()`
- More data available than kanban cards (IRI + label)

**Calendar view** (`backend/app/templates/browser/calendar_view.html`):
- Inline `<script>` IIFE — no separate `calendar.js` file yet
- `editable: true`, `selectable: true` from S01, with `eventDrop` and `eventResize` handlers
- **Missing**: `droppable: true` and `drop` callback
- **Missing**: No `window` reference to the FullCalendar instance — can't call `refetchEvents()` externally
- Patch helper: `patchCalendarEvent(info, actionLabel)` POSTs to `/browser/views/calendar/patch`

**Calendar PATCH backend** (`backend/app/views/router.py:954`):
- `POST /browser/views/calendar/patch` accepts `{iri, start?, end?}`
- Auto-detects object type → maps to correct date predicates (Task→scheduledStart/scheduledEnd, Event→startDate/endDate)
- Dispatches `object.patch` command + event store commit + validation queue + webhook

**Canvas drop pattern** (`frontend/static/js/canvas.js:465-545`):
- Reads `text/iri` + `text/label` from `dataTransfer`
- Falls back to `window.__canvasDragPayload` side-channel for complex payloads
- `stopPropagation()` on `dragover` and `drop`
- Handles spurious `dragleave` from dockview overlays

**Cross-view events**:
- `sempkm:command-executed` — dispatched by kanban, calendar, apps, timeline after mutations. Event log listens and refreshes.
- `sempkm:tab-activated` — dispatched by workspace-layout on panel focus change
- `sempkm:tabs-empty` — dispatched when no object panels remain
- **No `sempkm:scope-changed` event exists yet** — scope changes currently trigger full htmx re-swap of the view content via `applyScopeQuery()`

**View toolbar scope UI** (`backend/app/templates/browser/view_toolbar.html`):
- `<select class="view-scope-select">` with saved queries grouped by user/model
- `onchange` calls `applyScopeQuery(queryId, renderer, selectedType)` which does `htmx.ajax('GET', ...)` to re-swap the view
- The scope select targets `.group-editor-area` — this replaces the ACTIVE panel content only, not sibling panels

**Dockview panel system** (`frontend/static/js/workspace-layout.js`):
- `window._dockview` exposes the DockviewComponent instance
- `dv.panels` array with `.id`, `.params`, `.group`, `.api`
- Panel params include `{ specialType, renderer, scopeQuery, selectedType }` for generic views
- No built-in inter-panel communication — all cross-panel coordination is via `document` events

### What Needs to Be Built

#### 1. External Drag → Calendar Drop

**Approach: Raw HTML5 dataTransfer + FullCalendar `drop` callback**

FullCalendar's `Draggable` class wraps a DOM container and watches for drag events from child elements. It works when source elements are in a predictable container. But kanban cards live in a different dockview panel — the DOM subtree is mounted/destroyed independently, and `Draggable` can't observe it.

Instead, use FullCalendar's `droppable: true` + `drop` callback, which fires for ANY native HTML5 drag event that lands on the calendar. The `drop` callback receives `{ date, dateStr, allDay, draggedEl, jsEvent, view }`. We read the IRI from `jsEvent.dataTransfer.getData('text/plain')` (kanban) or `jsEvent.dataTransfer.getData('text/iri')` (tree), then call the existing `/browser/views/calendar/patch` endpoint to set scheduledStart.

**Key detail**: The `drop` callback's `info.date` is a JavaScript Date object representing the drop target's time slot. On day/month views it's a date only (`allDay: true`); on week/day time views it's a datetime. This directly gives us the scheduledStart value.

**For scheduledEnd**: Default to 1 hour duration (scheduledStart + 60min). If the kanban card carries `data-duration` (ISO 8601), parse it to compute the real end time.

**Flow**:
1. User drags kanban card (or tree item) — existing `dragstart` fires, sets `text/plain`/`text/iri`
2. Drag crosses dockview panel boundary — HTML5 DnD handles this natively
3. FullCalendar intercepts `dragover` on calendar cells (via `droppable: true`)
4. User drops on a time slot — FullCalendar `drop(info)` fires
5. Read IRI from `info.jsEvent.dataTransfer`
6. Compute start/end from `info.date` + default duration
7. POST to `/browser/views/calendar/patch` with `{iri, start, end}`
8. On success: add event to calendar via `calendar.addEvent(...)` + dispatch `sempkm:command-executed`
9. On success: show toast "Task scheduled"

#### 2. Kanban Card Data Enrichment

Kanban cards currently have only `data-iri`. For the calendar drop to show a meaningful event, we need the task title. Options:
- **Option A**: Add `data-title` and `data-duration` attributes to kanban card template + set `text/iri` and `text/label` MIME types in `dragstart` (matches tree pattern)
- **Option B**: Fetch title from the IRI via API after drop

Option A is better — no extra round-trip, and it aligns kanban drag data with the tree drag pattern. Requires changes to:
- `kanban_view.html`: add `data-title="{{ item.label }}"` to `.kanban-card`
- `kanban.js`: set `text/iri` (in addition to `text/plain`) and `text/label` in `dragstart`

#### 3. Calendar JS Extraction

The calendar template has ~120 lines of inline `<script>`. S03 needs to:
- Extract to `frontend/static/js/calendar.js`
- Expose the FullCalendar instance as `window._sempkmCalendar` for external control (refetchEvents)
- Add `droppable: true` and `drop` callback
- Add `eventReceive` callback (fires after FullCalendar creates an event from external drop)
- Add `sempkm:command-executed` listener that calls `calendar.refetchEvents()`

The template keeps a minimal `<script>` that calls `initCalendar(el, dataUrl)`.

#### 4. Scope Change Propagation

**New custom event**: `sempkm:scope-changed` dispatched on `document` with `detail: { scopeQuery, scopeLabel, renderer, sourcePanel }`.

**Who dispatches**: The view toolbar's scope `<select>` `onchange` — instead of (or in addition to) calling `applyScopeQuery()`, it dispatches this event.

**Who listens**: Each view's init function registers a `sempkm:scope-changed` listener. When fired:
- Calendar: re-fetch data with new scope query param → `calendar.removeAllEvents()` + fetch + `calendar.addEvent()` for each
- Kanban: htmx re-swap with new scope_query param
- Timeline: re-fetch data with new scope query param

**Panel identity**: The `sourcePanel` in the event detail lets a view skip self-triggered scope changes. Use the dockview panel ID from the closest `.dv-panel` ancestor.

**Simpler alternative**: Since `applyScopeQuery` already does a full htmx re-swap, the scope change for the active panel already works. For sibling panels, the `sempkm:scope-changed` event is the new piece — siblings listen and re-fetch independently.

### Natural Task Decomposition

**T01 — Kanban drag enrichment + calendar.js extraction** (~30 min)
- Extract calendar inline script to `frontend/static/js/calendar.js`
- Add `droppable: true`, `drop` callback, `eventReceive` callback
- Expose `window._sempkmCalendar` for external access
- Enrich kanban cards: `data-title`, `data-duration` attrs, `text/iri`+`text/label` MIME types in dragstart
- Calendar `<script>` tag becomes `<script src="/static/js/calendar.js"></script>` + minimal init call
- Add `sempkm:command-executed` listener → `calendar.refetchEvents()`
- CSS: external drop hover state on calendar (`.fc-highlight` already exists from `selectable`)

**T02 — Scope change propagation** (~20 min)
- New `sempkm:scope-changed` custom event
- View toolbar scope select dispatches event on change
- Calendar listens: re-fetches with new scope query, rebuilds events
- Kanban listens: htmx re-swap with updated scope_query param
- Panel identity via dockview panel ID to prevent self-trigger loops

**T03 — E2E test: cross-view drag + scope sync** (~25 min)
- Playwright test: open kanban + calendar side by side
- Seed a task, verify it appears on kanban
- Drag task from kanban to calendar time slot (simulate via JS since HTML5 DnD across panels is tricky in Playwright)
- Verify scheduledStart persisted via SPARQL API
- Verify scope change in one view propagates to sibling

### File Change Map

| File | Action | What |
|------|--------|------|
| `frontend/static/js/calendar.js` | **Create** | Extracted from calendar_view.html inline script; add droppable, drop, eventReceive, refetchEvents listener, window._sempkmCalendar |
| `frontend/static/js/kanban.js` | **Modify** | dragstart: add `text/iri`, `text/label` MIME types; read `data-title` from card |
| `backend/app/templates/browser/kanban_view.html` | **Modify** | Add `data-title="{{ item.label }}"` to `.kanban-card` div |
| `backend/app/templates/browser/calendar_view.html` | **Modify** | Replace inline script with `<script src>` + minimal init; add `droppable: true` via params |
| `frontend/static/js/workspace.js` | **Modify** | Add `sempkm:scope-changed` event dispatch in scope select handler; add listener wiring |
| `backend/app/templates/browser/view_toolbar.html` | **Modify** | scope select onchange dispatches `sempkm:scope-changed` in addition to applyScopeQuery |
| `frontend/static/css/views.css` | **Modify** | External drop highlight states, drag ghost styling |
| `e2e/tests/02-views/cross-view-drag.spec.ts` | **Create** | E2E test for kanban→calendar drag + scope propagation |
| `e2e/helpers/selectors.ts` | **Modify** | Add calendar drop zone selectors if needed |

### Risks and Mitigations

**Risk 1: FullCalendar `drop` callback may not receive `dataTransfer` data**
FullCalendar's `droppable: true` uses its internal drag detection which may not pass through the raw HTML5 `dataTransfer` in the `drop` callback's `jsEvent`. The v6 docs show `info.draggedEl` and `info.date` but don't document `info.jsEvent.dataTransfer` explicitly.

**Mitigation**: Use the same `window.__canvasDragPayload` side-channel pattern from canvas.js. Set `window.__calendarDragPayload = { iri, title, duration }` in kanban's `dragstart`, read it in the calendar's `drop` callback, clear after use. This bypasses any dataTransfer limitations.

**Fallback**: If FullCalendar's `droppable` doesn't intercept native HTML5 drops at all (because `Draggable` wasn't used), add a native `drop` event listener on `#calendar-container` that computes the target time from mouse position + FullCalendar's `getDate()` API.

**Risk 2: Cross-dockview drag blocked by dockview's own drag handlers**
dockview intercepts drag events for panel reordering. kanban already proves `stopPropagation()` prevents this for intra-panel drag. But the `dragover`/`drop` events on the calendar's panel haven't been tested with external drags.

**Mitigation**: The calendar container sits inside a `.dv-content-container` div. FullCalendar's interaction plugin registers its own `dragover`/`drop` handlers on the calendar element. Since these are deeper in the DOM than dockview's panel chrome, they should fire first. If dockview interferes, add `stopPropagation()` on the calendar container's `dragover` handler (same pattern as kanban).

**Risk 3: Playwright can't simulate cross-panel HTML5 DnD**
Native HTML5 drag-and-drop is notoriously hard to simulate in Playwright. `page.dragAndDrop()` works for elements in the same frame but may not work across dockview panels.

**Mitigation**: Use `page.evaluate()` to directly call the calendar's drop handler with synthetic data, bypassing actual drag simulation. Test the individual pieces: (1) kanban dragstart sets correct data, (2) calendar drop handler creates correct PATCH request, (3) scope change event propagates. This is more reliable than end-to-end drag simulation.

### Prior Art in Codebase

| Pattern | Where | Relevance |
|---------|-------|-----------|
| HTML5 DnD with stopPropagation in dockview | `kanban.js` | Exact pattern for drag source |
| `text/iri` + `text/label` MIME types | `tree_children.html` | Data format standard for drag payloads |
| `window.__canvasDragPayload` side-channel | `canvas.js` | Backup data channel for complex payloads |
| `patchCalendarEvent()` helper | `calendar_view.html` | Backend PATCH reusable for drop handler |
| `sempkm:command-executed` event | kanban, calendar, timeline, apps | Cross-view mutation notification |
| `applyScopeQuery()` | `workspace.js` | Existing scope change handler (re-swaps active panel) |
| CDN lazy-load + IIFE pattern | `calendar_view.html`, `timeline_view.html` | JS file structure pattern |

### Don't Hand-Roll

- **FullCalendar Draggable class for kanban cards**: Don't try to instantiate `new FullCalendar.Draggable()` on the kanban container. The kanban is in a separate dockview panel — the Draggable instance can't observe drag events across panel boundaries. Use native HTML5 DnD with the `drop` callback instead.
- **Custom date-from-mouse-position calculation**: FullCalendar's `drop` callback provides `info.date` directly. Don't compute the target time from pixel coordinates.
- **Per-panel iframe isolation for scope**: Don't try to isolate panel scope with iframes. Use document-level custom events — they're the proven pattern in this codebase.

## Sources

- FullCalendar v6 docs: `drop` callback receives `{ date, dateStr, allDay, draggedEl, jsEvent, view }` — date is a JS Date for the target slot
- FullCalendar v6 docs: `Draggable` wraps a container element; `ThirdPartyDraggable` wraps third-party drag libraries
- FullCalendar v6 docs: `droppable: true` required alongside Draggable for external drops; `eventReceive` fires after event creation from external drop
- Codebase: kanban `stopPropagation()` pattern proven for dockview panel isolation
- Codebase: canvas uses `text/iri` + `window.__canvasDragPayload` as dual data channels
- KNOWLEDGE.md: HTML5 drag-drop inside dockview panels needs `stopPropagation()` (M031/S04/T02)
- KNOWLEDGE.md: `dragleave` flicker prevention with `contains(relatedTarget)` (M031/S04/T02)
- KNOWLEDGE.md: Popovers inside dockview panels must escape stacking context (M031/S05/T04)
