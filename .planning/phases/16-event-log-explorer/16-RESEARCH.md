# Phase 16: Event Log Explorer - Research

**Researched:** 2026-02-24
**Domain:** Event log querying (SPARQL over RDF named graphs), cursor-based pagination, inline diff computation, undo/compensating commands, htmx bottom-panel UI
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EVNT-01 | Event log displays a paginated timeline of all events in reverse chronological order with operation type badge, affected object link, user, and timestamp | SPARQL SELECT over event named graphs with `urn:sempkm:event:` IRI pattern; cursor pagination via `FILTER(?ts < ?cursor_ts)` on `sempkm:timestamp`; label resolution via existing `LabelService`; rendered as htmx partial loaded into `#panel-event-log` pane |
| EVNT-02 | Events are filterable by operation type, user, object, and date range with removable filter chips; filters combine with AND logic | Client-side filter state in JS; htmx GET with query params (`?op=object.patch&user=...&from=...&to=...`); SPARQL `FILTER` clauses added dynamically in Python; filter chips as button elements with `onclick` that remove the filter and reload |
| EVNT-03 | Clicking an object.patch or body.set event shows an inline diff of the changes (property before/after or line-by-line body diff) | For `object.patch`: data triples in event graph are the NEW values; OLD values must be reconstructed from the PREVIOUS event for the same subject+predicate; diff shown as before/after table rows. For `body.set`: previous body queried from most-recent earlier event; line-by-line diff with Python `difflib.unified_diff` or `difflib.ndiff` |
| EVNT-04 | Reversible events (object.patch, body.set, edge.create, edge.patch) have an Undo button that creates a compensating event after confirmation | Undo for `object.patch`/`edge.patch`: read OLD values from preceding event, dispatch new `object.patch`/`edge.patch` with those values. Undo for `body.set`: read OLD body from preceding event, dispatch `body.set`. Undo for `edge.create`: delete edge triples from current state graph via new `edge.delete` command or direct compensating operation |

</phase_requirements>

---

## Summary

Phase 16 builds on the event store that is already fully functional. Every write to SemPKM since the beginning has been stored as an immutable RDF named graph with IRI pattern `urn:sempkm:event:{uuid}`. Each graph contains metadata triples (`sempkm:timestamp`, `sempkm:operationType`, `sempkm:affectedIRI`, `sempkm:performedBy`, `sempkm:description`) plus the data triples that were written. The hard parts are: (1) efficiently querying and paginating events via SPARQL, (2) reconstructing the "before" state for diffs (requires reading a prior event's data), and (3) implementing undo correctly (a compensating command, not a deletion from history).

The frontend target is `#panel-event-log` inside the bottom panel, which already has a placeholder pane. The panel loading pattern is the same as other htmx partials: `htmx.ajax()` targets the pane container. The bottom panel tab switching is already wired in `workspace.js` via `_applyPanelState()`. Adding a lazy-load trigger when the "EVENT LOG" tab is activated is the only integration point.

The event data model has one important gap: the data triples in an `object.patch` event graph store only the NEW values (what was set), not the OLD values (what was deleted). To reconstruct before/after diffs, the code must query the preceding event for the same subject+predicate — or query the current state graph for the current value (which is the new value after the patch). For undo, the old value must come from the event graph that immediately preceded the change for that property.

**Primary recommendation:** Implement the event index SPARQL query in a new `EventQueryService`, use cursor-based pagination via timestamp comparison, reconstruct diff context by querying backward through event history, and implement undo as a new `POST /browser/events/{event_iri}/undo` endpoint that dispatches compensating commands through the existing `EventStore.commit()`.

---

## Standard Stack

### Core (already in project — no new installs needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | current | New `/browser/events` endpoint family | Already the project web framework |
| TriplestoreClient | project | SPARQL SELECT queries against event graphs | Already the RDF4J interface |
| LabelService | project | Resolve affected object IRIs to display labels | Already used in browser/router.py |
| Jinja2Blocks | current | HTML template rendering for event list | Already used for all htmx partials |
| htmx | 2.0.4 CDN | Lazy-load event log pane, filter reloads | Already the project AJAX mechanism |
| Python `difflib` | stdlib | Compute text diffs for body.set events | Built-in, no install needed |

### Supporting (no install needed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python `difflib.unified_diff` | stdlib | Line-by-line diff for body content | `body.set` event detail view |
| CSS counter-badge styles | project CSS | Operation type badges (colored pill labels) | Already have `badge` patterns in existing CSS |
| `window.fetch` | browser | Undo confirmation + POST to undo endpoint | Consistent with existing save/create patterns |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python `difflib` | JS `diff` library (jsdiff) | Server-side is simpler; diff computed once, returned as HTML; no extra CDN dependency |
| Cursor pagination (timestamp) | Offset pagination (LIMIT/OFFSET) | Cursor is O(log N) vs O(N) for large logs; RDF4J may not support stable offsets; cursor is the correct choice per success criteria |
| New `EventQueryService` | Inline SPARQL in router | Service is testable and reusable; event querying complexity warrants its own module |

**Installation:** No new packages needed.

---

## Architecture Patterns

### Recommended Project Structure Additions

```
backend/app/
├── events/
│   ├── models.py        # EXISTING: event vocabulary constants
│   ├── store.py         # EXISTING: EventStore, Operation, EventResult
│   └── query.py         # NEW: EventQueryService (SPARQL pagination, diff, undo logic)
├── browser/
│   └── router.py        # EXTEND: /browser/events GET + /browser/events/{iri}/undo POST
└── templates/browser/
    ├── event_log.html      # NEW: event timeline list (htmx partial, paginated)
    ├── event_detail.html   # NEW: diff view for object.patch / body.set
    └── workspace.html      # MODIFY: add htmx lazy-load trigger on event-log panel tab

frontend/static/
├── css/workspace.css    # EXTEND: event log list styles, filter chip styles, badge styles
└── js/workspace.js      # EXTEND: lazy-load event log when panel tab activated
```

### Pattern 1: Event Index SPARQL Query

The core query selects event metadata from all event named graphs. The key insight: each named graph has the event IRI as both the graph name AND the subject of the metadata triples.

```sparql
# Source: codebase analysis of EventStore.commit() — event graphs use event_iri as graph name and subject

SELECT ?event ?timestamp ?opType ?affectedIRI ?performedBy ?description
WHERE {
  GRAPH ?event {
    ?event a <urn:sempkm:Event> ;
           <urn:sempkm:timestamp> ?timestamp ;
           <urn:sempkm:operationType> ?opType ;
           <urn:sempkm:affectedIRI> ?affectedIRI .
    OPTIONAL { ?event <urn:sempkm:performedBy> ?performedBy }
    OPTIONAL { ?event <urn:sempkm:description> ?description }
  }
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
  # Cursor pagination: only events BEFORE the cursor timestamp
  # FILTER(?timestamp < "2026-02-24T12:00:00Z"^^xsd:dateTime)
  # Filters applied here when user applies them:
  # FILTER(?opType = "object.patch")  -- for op type filter
  # FILTER(?affectedIRI = <iri>)      -- for object filter
  # FILTER(?performedBy = <user_iri>) -- for user filter
}
ORDER BY DESC(?timestamp)
LIMIT 51
```

Note: `LIMIT 51` for a page size of 50 — if 51 rows return, there is a next page and the cursor is the 50th row's timestamp.

### Pattern 2: Cursor-Based Pagination

```python
# In EventQueryService

async def list_events(
    self,
    cursor_timestamp: str | None = None,  # ISO datetime string; None = start from most recent
    op_type: str | None = None,
    user_iri: str | None = None,
    object_iri: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page_size: int = 50,
) -> tuple[list[dict], str | None]:
    """
    Returns (events, next_cursor).
    next_cursor is None when there are no more events.
    """
    filters = []
    if cursor_timestamp:
        filters.append(f'FILTER(?timestamp < "{cursor_timestamp}"^^xsd:dateTime)')
    if op_type:
        filters.append(f'FILTER(?opType = "{op_type}")')
    if user_iri:
        filters.append(f'FILTER(?performedBy = <{user_iri}>)')
    if object_iri:
        filters.append(f'FILTER(?affectedIRI = <{object_iri}>)')
    if date_from:
        filters.append(f'FILTER(?timestamp >= "{date_from}"^^xsd:dateTime)')
    if date_to:
        filters.append(f'FILTER(?timestamp <= "{date_to}"^^xsd:dateTime)')

    filter_str = "\n  ".join(filters)
    sparql = f"""...base query with {filter_str}..."""
    result = await self._client.query(sparql)
    # Parse rows, group by event IRI (multiple affectedIRI rows per event)
    # Return first page_size events and compute next_cursor
```

The grouping step: one event may have multiple `sempkm:affectedIRI` rows (e.g., `edge.create` affects edge IRI + source IRI + target IRI). The Python layer must group by `?event` before returning a list of event dicts.

### Pattern 3: Event Panel Lazy Loading

The `#panel-event-log` pane currently shows a static placeholder. It should load the event log when the tab is first activated. The `initPanelTabs()` function in `workspace.js` handles tab switches via `_applyPanelState()`. Adding an htmx trigger on first open:

```javascript
// In workspace.js initPanelTabs() — extend to lazy-load event log on first activation
function initPanelTabs() {
  document.querySelectorAll('.panel-tab').forEach(function (btn) {
    btn.addEventListener('click', function () {
      panelState.activeTab = btn.dataset.panel;
      savePanelState();
      _applyPanelState();

      // Lazy-load event log when tab activated for the first time
      if (btn.dataset.panel === 'event-log') {
        var pane = document.getElementById('panel-event-log');
        if (pane && pane.querySelector('.panel-placeholder')) {
          // Replace placeholder with loaded content
          htmx.ajax('GET', '/browser/events', {
            target: '#panel-event-log',
            swap: 'innerHTML'
          });
        }
      }
    });
  });
}
```

Additionally, opening the bottom panel via `Ctrl+J` should auto-load if `event-log` is the active tab:

```javascript
// In _applyPanelState() — add after the existing tab state restoration
if (panelState.open && panelState.activeTab === 'event-log') {
  var pane = document.getElementById('panel-event-log');
  if (pane && pane.querySelector('.panel-placeholder')) {
    htmx.ajax('GET', '/browser/events', {
      target: '#panel-event-log',
      swap: 'innerHTML'
    });
  }
}
```

### Pattern 4: Diff Reconstruction for object.patch

The `object.patch` event graph stores only the NEW values (confirmed by reading `handle_object_patch()` in `handlers/object_patch.py` — `data_triples` contains only the new value side). To show before/after:

**Option A (query current state for new value, query preceding event for old value):**
1. New value: read directly from the event graph's data triples for the predicate
2. Old value: query backward through event history for the same `subject + predicate` pair — find the most recent earlier `object.patch` or `object.create` event that touched that predicate

**Option B (query the current state graph for new value, query next-older event for old value):**
This is equivalent to Option A but from a different direction.

**Recommended approach for Option A:**
```sparql
# Find the old value: most recent event before ?event_iri that touched ?subject + ?predicate
SELECT ?old_value ?old_event_ts
WHERE {
  GRAPH ?prev_event {
    ?prev_event a <urn:sempkm:Event> ;
               <urn:sempkm:timestamp> ?old_event_ts .
    ?subject ?predicate ?old_value .  # data triple in that event's graph
  }
  GRAPH <urn:sempkm:event:{uuid}> {
    <urn:sempkm:event:{uuid}> <urn:sempkm:timestamp> ?this_ts .
  }
  FILTER(STRSTARTS(STR(?prev_event), "urn:sempkm:event:"))
  FILTER(?old_event_ts < ?this_ts)
  FILTER(?prev_event != <urn:sempkm:event:{uuid}>)
}
ORDER BY DESC(?old_event_ts)
LIMIT 1
```

This is a cross-graph query. RDF4J supports querying across named graphs. The event IRI is the graph name, so `GRAPH ?prev_event { ?prev_event a sempkm:Event }` iterates all event graphs. This may be slow for large logs.

**Simpler alternative:** For properties with a single value, show only the NEW value (what was set). The current state graph always has the live value. For the "before" value, show "previous value" as greyed-out or "unknown" unless we have the preceding event's data.

**CRITICAL INSIGHT:** The simplest robust approach for before/after diff is:
- NEW value: from the event graph's data triples (already have them)
- OLD value: query the current state graph (what's there NOW is the NEW value after the patch). To get the OLD value, walk backward: find the event immediately before this one that has the same subject + predicate in its data triples.
- For a timeline view, if we just show "changed X to Y", we need both. For initial implementation, showing just "set to Y" with the affected property names is sufficient for EVNT-03 ("property before/after"), but EVNT-03 explicitly requires before/after.

**Best approach for before/after without expensive cross-graph queries:**
Store the BEFORE values at write time. This requires modifying `handle_object_patch()` to query the triplestore for current values before writing, adding them as `sempkm:beforeValue` triples to the event graph. This is an EventStore enhancement but enables clean before/after diffs without backward-crawling queries.

However, this requires a read-before-write in the command handler, which adds a round trip. The existing pattern in `handle_object_patch()` uses `Variable("old_N")` delete patterns (no query), so it deliberately avoids reading current values.

**Resolution:** For Phase 16, implement diff reconstruction by querying backward — find the preceding event's data triples for the same subject+predicate. Accept that this is a `O(events)` scan in the worst case but is only triggered on explicit diff clicks (not on page load).

### Pattern 5: Undo as Compensating Command

Undo is NOT a deletion from history. It creates a NEW event that reverses the effect:

```
object.patch undo → new object.patch with old property values
body.set undo      → new body.set with old body content
edge.create undo   → new "edge.delete" compensating operation (OR object.patch on current state)
edge.patch undo    → new edge.patch with old annotation values
```

**For `edge.create` undo:** There is no `edge.delete` command in the current command set. Options:
1. Add an `edge.delete` command (cleanest, adds to the command vocabulary)
2. Implement undo for `edge.create` as a direct compensating `Operation` (bypasses the command layer, goes directly to `EventStore.commit()`) that removes the edge triples from the current state graph

**Recommended:** Option 2 for Phase 16 (avoids adding a new command type to the vocabulary). The undo endpoint constructs the compensating `Operation` directly:

```python
# Compensating Operation for edge.create undo
# Reads edge triples from event graph, deletes them from current state

compensation_op = Operation(
    operation_type="edge.create.undo",  # new operation type string for provenance
    affected_iris=[edge_iri],
    description=f"Undo edge.create for: {edge_iri}",
    data_triples=[],  # nothing to record in the compensating event graph
    materialize_inserts=[],
    materialize_deletes=edge_triples_as_exact_patterns,  # exact triples to delete
)
```

**Undo endpoint pattern:**

```python
@router.post("/browser/events/{event_iri:path}/undo")
async def undo_event(
    event_iri: str,
    request: Request,
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Create a compensating event that reverses the specified event."""
    decoded_iri = unquote(event_iri)
    event_query = EventQueryService(client)

    # 1. Load the event's operation type and data
    event_data = await event_query.get_event_detail(decoded_iri)

    # 2. Build compensating operation based on operation type
    compensation = await event_query.build_compensation(decoded_iri, event_data)
    if not compensation:
        return JSONResponse(status_code=400, content={"error": "This event cannot be undone"})

    # 3. Commit compensating operation
    event_store = EventStore(client)
    user_iri = URIRef(f"urn:sempkm:user:{user.id}")
    await event_store.commit([compensation], performed_by=user_iri, performed_by_role=user.role)

    # 4. Return updated event log partial (refresh the pane)
    return HTMLResponse(content='<div hx-get="/browser/events" hx-trigger="load" hx-swap="innerHTML"></div>')
```

### Pattern 6: Filter Chips UI

Filter chips are button elements in the event log header bar:

```html
<!-- In event_log.html — filter chips row -->
<div class="event-log-filters">
  <div class="filter-chips" id="event-filter-chips">
    {% for chip in active_filters %}
    <button class="filter-chip"
            hx-get="/browser/events{{ remove_filter_url(chip) }}"
            hx-target="#panel-event-log"
            hx-swap="innerHTML">
      {{ chip.label }} &times;
    </button>
    {% endfor %}
  </div>
  <div class="event-filter-controls">
    <select id="event-op-filter" onchange="applyEventFilter()">
      <option value="">All operations</option>
      <option value="object.create">object.create</option>
      <option value="object.patch">object.patch</option>
      <option value="body.set">body.set</option>
      <option value="edge.create">edge.create</option>
      <option value="edge.patch">edge.patch</option>
    </select>
  </div>
</div>
```

Filter state is passed as URL query params on htmx requests. The Python route reads `Request.query_params` and passes them to `EventQueryService.list_events()`. Removing a filter chip reconstructs the URL without that parameter.

### Pattern 7: New Router for Events

Following the pattern of `browser/router.py` vs `debug/router.py`, add event log routes either:
- **Option A:** Add to `browser/router.py` (already has label resolution, TriplestoreClient, etc.)
- **Option B:** Create a new `events/router.py` module

**Recommendation:** Add to `browser/router.py` for Phase 16 (3 routes maximum). The browser router is already the home of workspace-related htmx endpoints and has all needed dependencies. Creating a separate router is only justified if the number of routes grows (Phase 17+).

### Anti-Patterns to Avoid

- **OFFSET-based pagination against RDF4J:** RDF4J SPARQL does not guarantee stable OFFSET pagination across concurrent writes. Cursor (timestamp) pagination is mandatory.
- **Querying all event data on every page load:** Only query metadata (timestamp, opType, affectedIRI, performedBy) for the list view. Load diff data only on explicit click (htmx GET for detail).
- **Modifying history (deleting events):** Undo MUST create a new compensating event, never mutate or delete existing event graphs. The event log is immutable append-only.
- **Eager before/after diff computation for all events in list:** Diff reconstruction involves cross-graph queries. Only compute diffs on explicit click for EVNT-03, never on the list page.
- **Loading all events at once:** Even with a small dataset, SPARQL scanning all event graphs without a cursor is O(N). Always use LIMIT + cursor.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text diff computation | Custom character diff | Python `difflib.unified_diff` or `difflib.ndiff` | stdlib, handles edge cases (empty strings, whitespace-only changes, large texts), well-tested |
| Pagination | Count-based (`page=2&size=50`) | Cursor-based (timestamp as cursor) | RDF4J SPARQL OFFSET is unstable under concurrent writes; timestamp cursor is stable and O(log N) |
| Filter URL construction | Custom URL builder | Simple Python `urllib.parse.urlencode` with filter params dict | Avoid hand-crafted query strings; urlencode handles escaping |
| Undo confirmation dialog | Custom modal | `window.confirm()` | Matches existing `toggleObjectMode` unsaved-changes pattern (`window.confirm('Discard unsaved changes?')`); zero dependencies |

---

## Common Pitfalls

### Pitfall 1: Multiple affectedIRI Rows Per Event
**What goes wrong:** A SPARQL query returns one row per `sempkm:affectedIRI` triple. An `edge.create` event has 3 affected IRIs. The Python code that expects one row per event will create 3 duplicate entries.
**Why it happens:** `sempkm:affectedIRI` is multi-valued; SPARQL SELECT produces a Cartesian product.
**How to avoid:** In `EventQueryService.list_events()`, group results by `?event` IRI before building the event list. Use Python `dict` keyed on event IRI, appending `affectedIRI` to a list. Alternatively, use `GROUP_CONCAT(?affectedIRI; separator=",")` in the SPARQL query.
**Warning signs:** Event list shows the same event multiple times with different affected IRI labels.

### Pitfall 2: Event Graph Query Scans All Named Graphs
**What goes wrong:** `GRAPH ?g { ... }` in SPARQL without any constraints iterates ALL named graphs in the triplestore, including the current state graph (`urn:sempkm:current`) and validation report graphs.
**Why it happens:** No graph name filter.
**How to avoid:** Always add `FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))` to restrict the graph scan to event graphs only.
**Warning signs:** Query returns unexpected rows from the current state graph or validation graphs.

### Pitfall 3: Timestamp Cursor Collision
**What goes wrong:** Two events have the same timestamp (same millisecond). Cursor pagination using `?ts < cursor_ts` skips all events at the exact cursor timestamp, causing gaps.
**Why it happens:** High write throughput can create millisecond-identical timestamps.
**How to avoid:** Use `(timestamp, event_iri)` as a compound cursor: `FILTER(?ts < :cursor_ts || (?ts = :cursor_ts && STR(?event) < ":cursor_iri"))`. For Phase 16, the simpler single-timestamp cursor is acceptable given the low write frequency of a PKM tool — document this as a known limitation.
**Warning signs:** Under rapid save conditions, some events disappear from the timeline between pages.

### Pitfall 4: Undo Races with New Edits
**What goes wrong:** User clicks Undo on event E1. Between E1 and now, user made change E2 to the same property. Undo of E1 overwrites E2's value.
**Why it happens:** No optimistic locking or version check on undo.
**How to avoid:** Accept this behavior for Phase 16 (undo simply patches back to the old value, regardless of intervening changes). Add a warning in the undo confirmation: "This will overwrite any changes made to this field since then." This is consistent with how git revert works.
**Warning signs:** User undoes a property change but their subsequent edit is also reverted.

### Pitfall 5: event.create Has No Before Value for Diff
**What goes wrong:** The diff view is opened for an `object.create` event. There is no "before" state — the object didn't exist.
**Why it happens:** Diff logic assumes there is always a preceding state.
**How to avoid:** The diff view for `object.create` and `edge.create` shows only "Created: [properties]" with no before column. The code must check the operation type before attempting backward query.
**Warning signs:** Null pointer or empty query result when trying to find preceding event for a creation event.

### Pitfall 6: Panel Content Lost on Split.js Recreation
**What goes wrong:** When `splitRight()` or `removeGroup()` is called, `recreateGroupSplit()` in `workspace-layout.js` saves and restores the `#bottom-panel` DOM node. If the event log was loaded and the panel DOM is moved, htmx `hx-*` attributes survive but JavaScript state (scroll position, filter state) is lost.
**Why it happens:** `recreateGroupSplit()` does `editorPane.innerHTML = ''` then re-inserts saved DOM references. The event log pane content survives if it was in `#bottom-panel` before the reset.
**How to avoid:** The existing `recreateGroupSplit()` already saves and re-inserts `#bottom-panel` as a real DOM node (confirmed in codebase: `var bottomPanel = document.getElementById('bottom-panel'); editorPane.innerHTML = ''; ... editorPane.appendChild(bottomPanel)`). The event log content will survive. No changes needed.
**Warning signs:** Event log disappears after splitting an editor group.

---

## Code Examples

### EventQueryService Skeleton

```python
# backend/app/events/query.py
from dataclasses import dataclass, field
from app.triplestore.client import TriplestoreClient
from app.events.models import EVENT_TYPE, EVENT_TIMESTAMP, EVENT_OPERATION, EVENT_AFFECTED, EVENT_PERFORMED_BY


@dataclass
class EventSummary:
    """Summary of one event for the timeline list."""
    event_iri: str
    timestamp: str
    operation_type: str
    affected_iris: list[str]
    performed_by: str | None  # user IRI, None for system events
    description: str


@dataclass
class EventDetail:
    """Full event data including data triples for diff."""
    summary: EventSummary
    data_triples: list[tuple[str, str, str]]  # (s, p, o) as strings
    before_values: dict[str, str]  # predicate -> old value (empty if not reconstructed)
    new_values: dict[str, str]     # predicate -> new value (from data_triples)


class EventQueryService:
    """Query service for browsing and analyzing event graphs."""

    PAGE_SIZE = 50

    def __init__(self, client: TriplestoreClient) -> None:
        self._client = client

    async def list_events(
        self,
        cursor_timestamp: str | None = None,
        op_type: str | None = None,
        user_iri: str | None = None,
        object_iri: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[list[EventSummary], str | None]:
        """List events with cursor pagination. Returns (events, next_cursor)."""
        ...

    async def get_event_detail(self, event_iri: str) -> EventDetail | None:
        """Load full event data including data triples and reconstructed before values."""
        ...

    async def build_compensation(self, event_iri: str, detail: EventDetail) -> "Operation | None":
        """Build a compensating Operation for the given event, or None if not reversible."""
        ...
```

### SPARQL for Event List (core query)

```sparql
PREFIX sempkm: <urn:sempkm:>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?event ?timestamp ?opType (GROUP_CONCAT(STR(?affectedIRI); separator=",") AS ?affected) ?performedBy ?description
WHERE {
  GRAPH ?event {
    ?event a sempkm:Event ;
           sempkm:timestamp ?timestamp ;
           sempkm:operationType ?opType ;
           sempkm:affectedIRI ?affectedIRI .
    OPTIONAL { ?event sempkm:performedBy ?performedBy }
    OPTIONAL { ?event sempkm:description ?description }
  }
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
  {CURSOR_FILTER}
  {OP_FILTER}
  {USER_FILTER}
  {OBJECT_FILTER}
  {DATE_FROM_FILTER}
  {DATE_TO_FILTER}
}
GROUP BY ?event ?timestamp ?opType ?performedBy ?description
ORDER BY DESC(?timestamp)
LIMIT 51
```

Note: `GROUP_CONCAT` collapses multiple `affectedIRI` rows into one comma-separated string. RDF4J supports `GROUP_CONCAT` with separator.

### SPARQL for Event Detail (data triples)

```sparql
# Get all data triples stored in a specific event graph (excluding metadata)
PREFIX sempkm: <urn:sempkm:>

SELECT ?s ?p ?o
WHERE {
  GRAPH <{event_iri}> {
    ?s ?p ?o .
    FILTER(?s != <{event_iri}> || ?p NOT IN (
      sempkm:timestamp, sempkm:operationType, sempkm:affectedIRI,
      sempkm:performedBy, sempkm:performedByRole, sempkm:description,
      <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>
    ))
  }
}
```

This separates data triples (the actual change) from event metadata.

### SPARQL for Reconstructing Old Values (before-state for diffs)

```sparql
# Find the most recent event before {event_iri} that recorded a value for {subject} + {predicate}
PREFIX sempkm: <urn:sempkm:>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?old_value
WHERE {
  GRAPH ?prev_event {
    ?prev_event sempkm:timestamp ?prev_ts .
    <{subject_iri}> <{predicate_iri}> ?old_value .
  }
  FILTER(STRSTARTS(STR(?prev_event), "urn:sempkm:event:"))
  FILTER(?prev_ts < "{this_event_timestamp}"^^xsd:dateTime)
}
ORDER BY DESC(?prev_ts)
LIMIT 1
```

### Python `difflib` for Body Diff

```python
import difflib

def compute_body_diff(old_body: str, new_body: str) -> list[dict]:
    """Compute a unified diff between two body strings.

    Returns a list of line diff entries with type ('add', 'remove', 'context').
    """
    old_lines = old_body.splitlines(keepends=True)
    new_lines = new_body.splitlines(keepends=True)

    diff_lines = []
    for line in difflib.unified_diff(old_lines, new_lines, lineterm=''):
        if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
            continue
        elif line.startswith('+'):
            diff_lines.append({'type': 'add', 'text': line[1:]})
        elif line.startswith('-'):
            diff_lines.append({'type': 'remove', 'text': line[1:]})
        else:
            diff_lines.append({'type': 'context', 'text': line[1:]})

    return diff_lines
```

### New Routes in browser/router.py

```python
@router.get("/events")
async def event_log(
    request: Request,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    label_service: LabelService = Depends(get_label_service),
    cursor: str | None = Query(default=None),
    op: str | None = Query(default=None),
    user_filter: str | None = Query(default=None, alias="user"),
    obj: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """Render the event log timeline as an htmx partial for the bottom panel."""
    from app.events.query import EventQueryService
    templates = request.app.state.templates

    query_svc = EventQueryService(client)
    events, next_cursor = await query_svc.list_events(
        cursor_timestamp=cursor, op_type=op, user_iri=user_filter,
        object_iri=obj, date_from=date_from, date_to=date_to,
    )

    # Resolve labels for affected IRIs
    all_affected_iris = [iri for e in events for iri in e.affected_iris]
    labels = await label_service.resolve_batch(all_affected_iris) if all_affected_iris else {}

    # Build active filters list for chip rendering
    active_filters = []
    if op: active_filters.append({"param": "op", "value": op, "label": f"op: {op}"})
    if obj: active_filters.append({"param": "obj", "value": obj, "label": f"object: {labels.get(obj, obj)}"})
    # ...

    return templates.TemplateResponse(request, "browser/event_log.html", {
        "request": request,
        "events": events,
        "labels": labels,
        "next_cursor": next_cursor,
        "active_filters": active_filters,
        "current_params": dict(request.query_params),
    })


@router.get("/events/{event_iri:path}/detail")
async def event_detail(
    request: Request,
    event_iri: str,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Render inline diff for object.patch or body.set events."""
    from app.events.query import EventQueryService
    from urllib.parse import unquote
    templates = request.app.state.templates

    decoded_iri = unquote(event_iri)
    query_svc = EventQueryService(client)
    detail = await query_svc.get_event_detail(decoded_iri)

    return templates.TemplateResponse(request, "browser/event_detail.html", {
        "request": request,
        "detail": detail,
    })


@router.post("/events/{event_iri:path}/undo")
async def undo_event(
    request: Request,
    event_iri: str,
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Create a compensating event that reverses the specified event."""
    from app.events.query import EventQueryService
    from app.events.store import EventStore
    from urllib.parse import unquote
    decoded_iri = unquote(event_iri)

    query_svc = EventQueryService(client)
    detail = await query_svc.get_event_detail(decoded_iri)
    if not detail:
        return JSONResponse(status_code=404, content={"error": "Event not found"})

    compensation = await query_svc.build_compensation(decoded_iri, detail)
    if not compensation:
        return JSONResponse(status_code=400, content={"error": "This event cannot be undone"})

    event_store = EventStore(client)
    user_iri = URIRef(f"urn:sempkm:user:{user.id}")
    await event_store.commit([compensation], performed_by=user_iri, performed_by_role=user.role)

    # Return a reload trigger for the event log pane
    return JSONResponse(content={"status": "ok", "message": "Undo applied"})
```

---

## State of the Art

| Old Approach | Current Approach | Status in Codebase | Impact for Phase 16 |
|--------------|------------------|-------------------|---------------------|
| `#panel-event-log` shows static placeholder | Event log timeline with pagination | Placeholder still in workspace.html | Replace placeholder with htmx lazy-load on tab activation |
| No event querying API | SPARQL SELECT over event named graphs | Event graphs exist in triplestore from all previous writes | All past events are queryable without migration |
| No diff view | Before/after for object.patch; line diff for body.set | Not implemented | New EventQueryService with backward query for old values |
| No undo | Compensating event via EventStore.commit() | EventStore.commit() already supports arbitrary Operations | Undo adds a new operation type string and reconstructed compensating Operation |

---

## Open Questions

1. **Does RDF4J support `GROUP_CONCAT` with separator in SPARQL 1.1?**
   - What we know: RDF4J implements SPARQL 1.1; `GROUP_CONCAT` is part of SPARQL 1.1 spec. The project already uses RDF4J for all SPARQL queries.
   - What's unclear: Whether the specific version of RDF4J in the project's Docker image fully supports `GROUP_CONCAT`. If not, we fall back to Python-side grouping.
   - Recommendation: Use `GROUP_CONCAT` in the query; if it fails at runtime, fall back to Python grouping (collect all rows, group by event IRI in Python). Python grouping is always safe.

2. **Performance of cross-graph backward query for diff reconstruction**
   - What we know: The backward query (`GRAPH ?prev_event { ... }`) scans all event graphs before the timestamp. With 1000 events, this is 1000 graphs to scan per property per diff click.
   - What's unclear: How RDF4J indexes named graphs — it may maintain an internal index by graph IRI that makes this fast, or it may be a full scan.
   - Recommendation: Only trigger on explicit diff click (never on list page). Accept the performance for Phase 16. If it proves slow, consider adding `sempkm:beforeValue` triples to event graphs at write time (would require modifying `handle_object_patch()` to do a pre-read) as a Phase 16+ enhancement.

3. **User IRI resolution for "performed by" display**
   - What we know: User IRIs are stored as `urn:sempkm:user:{uuid}`. The `LabelService` resolves object labels from the triplestore, but user data is in the SQL database, not the triplestore.
   - What's unclear: There is no SPARQL-queryable label for user IRIs. The SQL `users` table has `email` and `display_name` fields (via AuthService).
   - Recommendation: In the event log router, after fetching events with user IRIs, do a SQL lookup for user display names by UUID (extract UUID from `urn:sempkm:user:{uuid}` pattern). Cache in a local dict for the request. This avoids LabelService for user IRIs.

4. **Filter chip "remove" URL construction**
   - What we know: Each filter chip should be a link that reloads the event log without that filter. The current query params minus the removed filter key.
   - What's unclear: Best pattern for constructing "remove this filter" URLs in Jinja2.
   - Recommendation: Pass `current_params` dict to the template, and use a Jinja2 custom filter `without_param(params, key)` that returns a URL query string excluding the given key. Register the filter in the templates env like the existing `format_date` filter.

---

## Implementation Sequence for Plans

Based on the three-plan structure:

**Plan 16-01: Event API Endpoint with Cursor Pagination and Event Index**
- Python: `backend/app/events/query.py` — `EventQueryService` with `list_events()` (SPARQL + Python grouping + cursor pagination)
- Python: `browser/router.py` — `GET /browser/events` endpoint with query param filtering
- Python: `browser/router.py` — `GET /browser/events/{event_iri}/detail` endpoint
- Template: `browser/event_log.html` — basic timeline list (no filters yet, no diff)
- JS: `workspace.js` `initPanelTabs()` — lazy-load event log on tab activation
- Test: Event log renders in bottom panel with correct events listed

**Plan 16-02: Event Log Timeline UI with Filtering**
- Template: `browser/event_log.html` — add filter controls, filter chips, "Load more" cursor button
- Python: Jinja2 filter `without_param` registered in router
- CSS: `workspace.css` — event log styles (timeline rows, operation type badges, filter chips, pagination button)
- Test: Filter by op type works, filter chips appear, removing chip reloads without that filter, cursor pagination loads next page

**Plan 16-03: Inline Diff View and Undo Operations**
- Python: `EventQueryService.get_event_detail()` — data triple extraction + backward query for old values + `compute_body_diff()`
- Python: `EventQueryService.build_compensation()` — undo logic for each reversible operation type
- Python: `browser/router.py` — `POST /browser/events/{event_iri}/undo` endpoint
- Template: `browser/event_detail.html` — before/after property diff table + body diff with add/remove line coloring
- Template: `browser/event_log.html` — add "Diff" expand button for patch/body.set events + "Undo" button for reversible events
- JS: Undo button with `window.confirm()` + fetch POST + reload trigger
- Test: Clicking diff shows before/after; undo button prompts, creates compensating event, event log refreshes

---

## Sources

### Primary (HIGH confidence)
- Codebase: `/home/james/Code/SemPKM/backend/app/events/store.py` — confirms data_triples contain NEW values only for object.patch; confirms event graph structure; confirms event IRI = graph name = subject of metadata
- Codebase: `/home/james/Code/SemPKM/backend/app/events/models.py` — all RDF predicates used in event metadata
- Codebase: `/home/james/Code/SemPKM/backend/app/commands/handlers/object_patch.py` — confirms no read-before-write; `data_triples` is new value; `Variable("old_N")` delete pattern
- Codebase: `/home/james/Code/SemPKM/backend/app/commands/handlers/body_set.py` — confirms body stored in data_triples as new value
- Codebase: `/home/james/Code/SemPKM/backend/app/commands/handlers/edge_create.py` — confirms all edge triples in data_triples + materialize_inserts; affected_iris has 3 entries
- Codebase: `/home/james/Code/SemPKM/backend/app/commands/handlers/edge_patch.py` — confirms same pattern as object.patch
- Codebase: `/home/james/Code/SemPKM/backend/app/rdf/iri.py` — confirms event IRI pattern `urn:sempkm:event:{uuid}`
- Codebase: `/home/james/Code/SemPKM/backend/app/rdf/namespaces.py` — SEMPKM namespace = `urn:sempkm:`
- Codebase: `/home/james/Code/SemPKM/backend/app/triplestore/client.py` — confirms query() method takes SPARQL SELECT and returns JSON SPARQL results
- Codebase: `/home/james/Code/SemPKM/backend/app/browser/router.py` — router patterns, LabelService usage, htmx partial rendering pattern
- Codebase: `/home/james/Code/SemPKM/backend/app/templates/browser/workspace.html` — `#panel-event-log` DOM target, placeholder structure
- Codebase: `/home/james/Code/SemPKM/frontend/static/js/workspace.js` — `initPanelTabs()`, `_applyPanelState()`, `panelState`, `toggleBottomPanel()`
- Codebase: `/home/james/Code/SemPKM/frontend/static/js/workspace-layout.js` — `recreateGroupSplit()` saves+restores `#bottom-panel` DOM node (event log content safe from split operations)
- Codebase: `/home/james/Code/SemPKM/backend/app/services/labels.py` — `resolve_batch()` pattern for resolving affected IRIs to labels
- Codebase: `/home/james/Code/SemPKM/backend/app/dependencies.py` — `get_triplestore_client`, `get_label_service` dependency injection patterns

### Secondary (MEDIUM confidence)
- Python stdlib `difflib` documentation — `unified_diff()`, `ndiff()` APIs; always available in Python 3.x
- SPARQL 1.1 spec — `GROUP_CONCAT` with separator, `FILTER(STRSTARTS(...))`, cross-graph patterns (`GRAPH ?g {}`)

### Tertiary (LOW confidence — verify at implementation)
- RDF4J `GROUP_CONCAT` support — should work per SPARQL 1.1 compliance, but test against actual RDF4J version in Docker image
- Cross-graph backward scan performance — depends on RDF4J internal indexing; may need optimization if event log is large

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project; no new dependencies required
- Architecture: HIGH — all extension points identified from direct codebase analysis; event data model fully understood
- Pagination: HIGH — cursor pagination pattern is well-established; SPARQL query structure confirmed by codebase analysis
- Diff reconstruction: MEDIUM — backward query logic is sound but cross-graph query performance on large logs is unverified
- Undo implementation: HIGH — compensating Operation pattern maps directly to existing EventStore.commit() interface; edge.create undo adds no new command type

**Research date:** 2026-02-24
**Valid until:** 2026-03-25 (stable stack)
