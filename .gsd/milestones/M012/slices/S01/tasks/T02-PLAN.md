---
estimated_steps: 7
estimated_files: 4
---

# T02: Add suggestion endpoints and autocomplete UI for event log filters

**Slice:** S01 — Event Log Polish — Labels, Helptext & Autocomplete
**Milestone:** M012

## Description

The event log currently has a static `<select>` dropdown for operation type filtering and date range inputs — but no way to filter by predicate or object, and no autocomplete. This task adds three suggestion endpoints that query real event data, and wires them into the event log filter area with htmx-driven autocomplete dropdowns.

## Steps

1. **Add `GET /browser/events/suggest-types` endpoint** in `backend/app/browser/events.py`:
   - Query distinct `sempkm:operationType` values from event graphs:
     ```sparql
     PREFIX sempkm: <urn:sempkm:>
     SELECT DISTINCT ?opType WHERE {
       GRAPH ?event {
         ?event sempkm:operationType ?opType .
       }
       FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
     }
     ORDER BY ?opType
     ```
   - Return HTML fragment: `<div class="autocomplete-suggestions">` with one `<button>` per type, each with `hx-get="/browser/events?op=..."` to apply the filter
   - No `q` parameter needed — operation types are a small finite set

2. **Add `GET /browser/events/suggest-predicates?q=` endpoint** in `backend/app/browser/events.py`:
   - Accept `q: str = Query(default="")` parameter
   - Query distinct predicates from event data triples (exclude event metadata predicates like `prov:startedAtTime`, `sempkm:operationType`, etc.):
     ```sparql
     PREFIX sempkm: <urn:sempkm:>
     PREFIX prov: <http://www.w3.org/ns/prov#>
     PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
     SELECT DISTINCT ?pred WHERE {
       GRAPH ?event {
         ?event a sempkm:Event .
         ?s ?pred ?o .
         FILTER(?s != ?event)
       }
       FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
     }
     LIMIT 100
     ```
   - Resolve labels for predicates using `ShapesService.get_labels_for_predicates()` (from T01)
   - Filter results: if `q` is provided, match against label or IRI local name (case-insensitive Python-side filter)
   - Return HTML fragment with suggestions showing label + IRI, limit 20
   - Each suggestion is a clickable element that applies a predicate filter (note: predicate filtering isn't in the current event_log query — add an optional `pred` query parameter to `event_log()` and `list_events()`)

3. **Add `GET /browser/events/suggest-objects?q=` endpoint** in `backend/app/browser/events.py`:
   - Accept `q: str = Query(default="")` parameter
   - Query distinct `sempkm:affectedIRI` values with optional text match:
     ```sparql
     PREFIX sempkm: <urn:sempkm:>
     SELECT DISTINCT ?iri WHERE {
       GRAPH ?event {
         ?event sempkm:affectedIRI ?iri .
       }
       FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
       FILTER(CONTAINS(LCASE(STR(?iri)), LCASE("...")))
     }
     LIMIT 20
     ```
   - Resolve labels via `LabelService.resolve_batch()`
   - If `q` is provided, also filter by label text (Python-side after resolution)
   - Return HTML fragment with suggestions showing label, IRI truncated in parentheses

4. **Add optional `pred` filter to `EventQueryService.list_events()`** in `backend/app/events/query.py`:
   - Add `predicate_iri: str | None = None` parameter
   - When provided, add a FILTER clause that checks for data triples matching the predicate:
     ```sparql
     FILTER EXISTS { GRAPH ?event { ?s <{predicate_iri}> ?o . FILTER(?s != ?event) } }
     ```
   - Wire through from `event_log()` route: add `pred: str | None = Query(default=None)` parameter

5. **Update `event_log.html` filter UI** in `backend/app/templates/browser/event_log.html`:
   - Replace the static `<select id="event-op-filter">` with a text input + dropdown combo:
     - `<input type="text" id="event-op-filter" placeholder="Filter by operation...">`
     - `<div class="event-autocomplete-dropdown" id="op-suggestions">` positioned below
     - `hx-get="/browser/events/suggest-types"` on the input with `hx-trigger="focus"` (load all types on focus)
     - Clicking a suggestion sets the input value and triggers filter
   - Add a predicate filter input:
     - `<input type="text" id="event-pred-filter" name="pred" placeholder="Filter by property...">`
     - `hx-get="/browser/events/suggest-predicates"` with `hx-trigger="keyup changed delay:300ms"` and `hx-include="this"` (sends `q` param)
     - Target: `#pred-suggestions` dropdown
   - Add an object filter input:
     - `<input type="text" id="event-obj-filter" placeholder="Filter by object...">`
     - `hx-get="/browser/events/suggest-objects"` with `hx-trigger="keyup changed delay:300ms"` and `hx-include="this"` (sends `q` param)
     - Target: `#obj-suggestions` dropdown
   - Each suggestion click should navigate: `hx-get="/browser/events?op=X&pred=Y&obj=Z"` with the selected value, targeting `#panel-event-log`
   - Update `hx-include` on date filters to include new filter inputs

6. **Add CSS for autocomplete dropdowns** in `frontend/static/css/workspace.css`:
   - `.event-filter-controls` becomes a flex-wrap container to accommodate more inputs
   - `.event-autocomplete-wrapper` — `position: relative` container for each input+dropdown pair
   - `.event-autocomplete-dropdown` — `position: absolute; top: 100%; left: 0; z-index: 100;` dropdown panel
   - Style similar to existing `.tag-autocomplete-dropdown` if present (check tag autocomplete CSS for reference)
   - Suggestion items: hover highlight, padding, clickable
   - Add `display: none` default, show via htmx swap

7. **Add `pred` filter chip** to `event_log()` route:
   - In the `active_filters` list construction, add a chip for `pred` when present
   - Display the human-readable predicate label in the chip (resolve via shapes service or label service)

## Must-Haves

- [ ] `GET /browser/events/suggest-types` returns distinct operation types as HTML suggestions
- [ ] `GET /browser/events/suggest-predicates?q=` returns predicate suggestions with human-readable labels
- [ ] `GET /browser/events/suggest-objects?q=` returns object suggestions with resolved labels
- [ ] Event log filter area has autocomplete inputs for operation type, predicate, and object
- [ ] Clicking a suggestion applies the filter and refreshes the event log
- [ ] Predicate filter is wired through `EventQueryService.list_events()` with FILTER EXISTS clause

## Verification

- Start Docker stack → open event log → click on operation type input → suggestion dropdown appears with operation types from actual events
- Type "tit" in predicate filter → "Title (dcterms:title)" suggestion appears
- Type a partial object name in object filter → matching objects appear as suggestions
- Select a suggestion → event log filters to matching events
- Active filter chips appear and can be dismissed

## Inputs

- `backend/app/browser/events.py` — from T01 with `get_shapes_service` import already added
- `backend/app/services/shapes.py` — from T01 with `get_labels_for_predicates()` method
- `backend/app/events/query.py` — existing `EventQueryService.list_events()`
- `backend/app/templates/browser/event_log.html` — existing filter UI
- `frontend/static/css/workspace.css` — existing event log styles

## Expected Output

- `backend/app/browser/events.py` — 3 new suggestion endpoints, `pred` filter parameter on `event_log()`
- `backend/app/events/query.py` — `predicate_iri` filter parameter on `list_events()`
- `backend/app/templates/browser/event_log.html` — autocomplete inputs with htmx-driven dropdowns
- `frontend/static/css/workspace.css` — autocomplete dropdown styling

## Observability Impact

- **New endpoints visible in server logs:** `GET /browser/events/suggest-types`, `suggest-predicates`, `suggest-objects` — each hit shows as a standard FastAPI access log entry. 404 or 500 responses indicate SPARQL or service failures.
- **SPARQL query failures:** `logger.warning` in each suggestion endpoint logs the failing query context (graceful degradation to empty suggestions list).
- **Predicate filter SPARQL:** When `pred` filter is active, `EventQueryService.list_events()` includes a `FILTER EXISTS` clause — if the filter produces no results, the event log shows "No events recorded yet." which is the expected empty-state indicator.
- **Inspection surfaces:** Each autocomplete suggestion HTML fragment includes `data-value` attributes on suggestion items for DOM inspection. The predicate filter chip shows the resolved human-readable label (or raw IRI if resolution fails) — visual indicator of shapes service health.
- **Failure visibility:** If shapes service is unavailable, predicate suggestions fall back to IRI local names (same graceful degradation as T01). Object suggestions fall back to truncated IRIs if LabelService fails.
