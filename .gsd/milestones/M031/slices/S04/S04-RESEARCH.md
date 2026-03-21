# S04 Research: Kanban Renderer

**Date:** 2026-03-21  
**Depth:** Targeted — known patterns, new renderer type using established codebase conventions  

## Summary

S04 adds a Kanban view renderer that groups objects by a status-like property into draggable columns. The codebase already has a well-established generic view pipeline (table, card, graph) with type filter pills, scope query binding, and view toolbar. The kanban renderer follows the same pattern: a new endpoint in `views/router.py`, a new template, CSS, a small JS module for drag-drop, and registration in the renderer registry + explorer sidebar.

The primary risk is **drag-drop event isolation from dockview's panel drag system**, which is a known problem solved in the canvas module via `capture: true` event listeners + `stopPropagation()`. The secondary concern is **auto-detecting the status field** for a given type — this is solved by the existing SHACL `sh:in` constraint discovery in `ShapesService`.

## Requirement Coverage

| Requirement | Description | How S04 Delivers |
|-------------|-------------|------------------|
| VIEW-12 | Kanban renderer with status-based columns and drag-drop | Full — new kanban endpoint, template, CSS, JS drag-drop, explorer entry |

## Recommendation

Build in 4 tasks:

1. **T01: Backend endpoint + SPARQL query** — Add `kanban` to `_VALID_RENDERERS`, add kanban branch to `generic_view()`, add `execute_kanban_query()` to `service.py`, register in `RENDERER_REGISTRY`. Also add a `_detect_status_field()` helper that finds the first SHACL property with `sh:in` values for the active type.

2. **T02: Jinja2 template** — Create `kanban_view.html` using the same include pattern as cards/table (type filter pills + view toolbar + kanban board). Columns rendered server-side from status values; cards within columns rendered as draggable items.

3. **T03: CSS + JS drag-drop** — Add kanban CSS to `views.css`. Write a small `kanban.js` module for HTML5 drag-drop between columns, with `stopPropagation()` on drag events to isolate from dockview. On drop, submit `object.patch` via `POST /api/commands` to update the status property.

4. **T04: Explorer entry + workspace.js label** — Add "Kanban View" leaf to `views_explorer.html`, add `kanban: 'Kanban View'` to the labels map in `openGenericViewTab()`.

## Implementation Landscape

### Key Files to Change

| File | Change |
|------|--------|
| `backend/app/views/router.py` | Add `"kanban"` to `_VALID_RENDERERS`, add kanban branch in `generic_view()`, add kanban data endpoint |
| `backend/app/views/service.py` | Add `execute_kanban_query()`, add `_detect_status_field()` helper |
| `backend/app/views/registry.py` | Add `"kanban"` entry to `RENDERER_REGISTRY` |
| `backend/app/templates/browser/kanban_view.html` | New — kanban board template |
| `backend/app/templates/browser/views_explorer.html` | Add "Kanban View" tree leaf |
| `frontend/static/css/views.css` | Add kanban board/column/card styles |
| `frontend/static/js/kanban.js` | New — drag-drop logic + status patch |
| `frontend/static/js/workspace.js` | Add `kanban` label to `openGenericViewTab()` labels map |
| `frontend/templates/base.html` or equivalent | Include `kanban.js` script tag |

### Key Files to Read (Reference Only)

| File | Why |
|------|-----|
| `backend/app/templates/browser/cards_view.html` | Closest template pattern to follow |
| `backend/app/templates/browser/view_toolbar.html` | Toolbar include pattern |
| `backend/app/templates/browser/type_filter_pills.html` | Type pills include pattern |
| `frontend/static/js/canvas.js:230-250` | Drag-drop event isolation pattern (capture phase + stopPropagation) |
| `backend/app/services/shapes.py` | `PropertyShape.in_values` for status enum discovery |
| `backend/app/commands/handlers/object_patch.py` | Object patch command structure |
| `frontend/static/js/app.js:174-177` | Client-side object.patch command payload format |

### Existing Patterns to Follow

**1. Generic View Endpoint Pattern (router.py)**

The `generic_view()` function dispatches by renderer type. Currently:
```python
_VALID_RENDERERS = {"table", "card", "graph"}
```
After S04: `{"table", "card", "graph", "kanban"}`. Add an `elif renderer == "kanban":` branch that:
- Calls `_detect_status_field()` to find the status property for the active type
- Calls `execute_kanban_query()` to fetch objects grouped by status
- Renders `kanban_view.html` with the same context variables as other renderers

**2. Status Field Detection via SHACL**

The `ShapesService.get_form_for_type(type_iri)` returns a `NodeShapeForm` with `properties: list[PropertyShape]`. Each `PropertyShape` has `in_values: list[str]` populated from `sh:in`. The kanban status field is the first property whose:
- `in_values` is non-empty (has enumerated allowed values)
- Name/path contains "status" (heuristic preference) OR just the first property with `in_values`

For `bpkm:Task`: `sh:path bpkm:taskStatus`, `sh:in ["todo", "in-progress", "done", "blocked", "cancelled"]`
For `bpkm:Project`: `sh:path bpkm:status`, `sh:in` not declared (uses free-text) — would need fallback
For `res:ResearchQuestion`: `sh:path res:status`, values from ontology comment: "open, in-progress, answered, abandoned"

The SHACL `sh:in` on `bpkm:taskStatus` gives us `["todo", "in-progress", "done", "blocked", "cancelled"]` — these become the kanban column headers.

**Fallback when no type is selected or type has no sh:in property:** Show a message like "Select a type with status values to use Kanban View" or default to generic status columns.

**3. Drag-Drop Isolation from Dockview (canvas.js pattern)**

```javascript
// canvas.js line 237 — capture phase prevents dockview from intercepting
document.addEventListener('dragover', onDragOver, true);
document.addEventListener('drop', onDrop, true);
```

The kanban drag-drop should:
- Use HTML5 Drag and Drop API (native, no library needed)
- Listen on the kanban container element (not document) to scope events
- Call `event.stopPropagation()` on `dragstart`, `dragover`, `drop` to prevent dockview from intercepting
- Set `draggable="true"` on kanban cards, NOT on column containers

**4. Object Status Update via Command API**

```javascript
// POST /api/commands with object.patch
fetch('/api/commands', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    command: 'object.patch',
    params: {
      iri: objectIri,
      properties: {
        '<status_predicate_iri>': newStatusValue
      }
    }
  })
})
```

After successful patch, dispatch `sempkm:command-executed` custom event so other open views refresh.

**5. Renderer Registry**

```python
# registry.py — add:
"kanban": {
    "type": "kanban",
    "template": "browser/kanban_view.html",
},
```

**6. Explorer Sidebar Entry**

Add to `views_explorer.html` following the exact pattern of the Table/Cards/Graph entries:
```html
<a class="tree-leaf view-leaf" href="#"
   onclick="openGenericViewTab('kanban'); return false;">
    <span class="tree-leaf-icon">&#9707;</span>
    <span class="tree-leaf-label">Kanban View</span>
</a>
```

### SPARQL Query Structure for Kanban

The kanban query needs to fetch objects with their status value and label, grouped by status. Two approaches:

**Approach A: Server-side grouping (recommended)**
- Single SELECT query fetching `?s ?label ?statusValue` + any extra columns
- Python groups results into `{status_value: [objects]}` dict
- Template iterates over status columns, then objects within each

```sparql
SELECT ?s ?label ?statusValue WHERE {
  ?s rdf:type <type_iri> .
  ?s <status_predicate> ?statusValue .
  OPTIONAL { ?s rdfs:label|dcterms:title ?label }
}
```

This is simpler and follows the existing two-phase query pattern (count, then fetch).

**Approach B: Client-side grouping** — Fetch all objects and group in JS. Unnecessary complexity.

Server-side grouping is correct. The `execute_kanban_query()` method returns:
```python
{
    "columns": [{"value": "todo", "label": "Todo", "items": [...]}, ...],
    "status_field": {"path": "urn:sempkm:model:basic-pkm:taskStatus", "name": "Task Status"},
    "total": 42,
    "type_label": "Task",
}
```

### Template Structure (kanban_view.html)

```
{% include "browser/type_filter_pills.html" %}
{% include "browser/view_toolbar.html" %}

<div class="kanban-board" data-status-predicate="{{ status_field.path }}">
  {% for col in columns %}
  <div class="kanban-column" data-status="{{ col.value }}">
    <div class="kanban-column-header">
      <span class="kanban-column-title">{{ col.label }}</span>
      <span class="kanban-column-count">{{ col.items | length }}</span>
    </div>
    <div class="kanban-column-body" data-drop-zone="kanban">
      {% for item in col.items %}
      <div class="kanban-card" draggable="true" data-iri="{{ item.iri }}">
        <span class="kanban-card-title" onclick="openTab('{{ item.iri }}', ...)">{{ item.label }}</span>
        {% for prop in item.properties %}
        <span class="kanban-card-prop">{{ prop.value }}</span>
        {% endfor %}
      </div>
      {% endfor %}
    </div>
  </div>
  {% endfor %}
</div>
```

### CSS Layout

```css
.kanban-board {
  display: flex;
  gap: 12px;
  padding: 12px;
  overflow-x: auto;
  height: 100%;
  align-items: flex-start;
}

.kanban-column {
  min-width: 250px;
  max-width: 300px;
  flex-shrink: 0;
  background: var(--color-surface-raised);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  max-height: 100%;
}

.kanban-column-body {
  overflow-y: auto;
  flex: 1;
  padding: 8px;
}

.kanban-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 10px;
  margin-bottom: 8px;
  cursor: grab;
}
```

### Drag-Drop JS Module (kanban.js)

Small self-contained module (~80-100 lines):
1. `initKanban(boardEl)` — attach event listeners with `stopPropagation()`
2. `onDragStart(e)` — set `dataTransfer` with object IRI
3. `onDragOver(e)` — `preventDefault()` + visual drop indicator
4. `onDrop(e)` — read IRI from dataTransfer, read target column's `data-status`, call `patchStatus()`
5. `patchStatus(iri, predicate, newStatus)` — POST to `/api/commands`, dispatch `sempkm:command-executed` on success, move DOM card to target column optimistically

### Script Loading

Check how other view-specific JS is loaded. The graph view loads `graph.js` via a `<script>` tag in `graph_view.html`. The kanban template should similarly include:
```html
<script src="/static/js/kanban.js"></script>
```

### Edge Cases

1. **No type selected** — Kanban without a type makes no sense (no status field). Show a prompt: "Select a type with status values to use Kanban View."
2. **Type has no sh:in property** — Show message: "This type has no status-like properties for Kanban grouping."
3. **Objects with no status value** — Put them in an "Unset" column at the end.
4. **Scope query active** — Filter kanban items by scope query (same `scope_filter` injection pattern as other renderers).
5. **Drag-drop on touch devices** — HTML5 drag-drop doesn't work on mobile. Acceptable for MVP — kanban is a desktop pattern.

### How to Verify

1. **Endpoint works:** `curl http://localhost:8000/browser/views/generic/kanban?type=urn:sempkm:model:basic-pkm:Task` returns HTML with kanban columns
2. **Status detection:** With Task type selected, columns should be: todo, in-progress, done, blocked, cancelled
3. **Drag-drop isolation:** Drag a kanban card — dockview should NOT start a panel drag
4. **Status update:** Drop a card in a different column → verify the object's status changed in triplestore
5. **Explorer entry:** "Kanban View" appears in the views explorer sidebar
6. **Type pills work:** Clicking a type pill re-renders the kanban with that type's status columns
7. **Scope query:** Selecting a saved query scope filters kanban items
8. **Python tests:** `pytest tests/test_kanban.py` — test `_detect_status_field()`, `execute_kanban_query()` grouping logic
