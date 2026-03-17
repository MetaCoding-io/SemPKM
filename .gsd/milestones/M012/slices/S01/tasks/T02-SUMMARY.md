---
id: T02
parent: S01
milestone: M012
provides:
  - GET /browser/events/suggest-types endpoint
  - GET /browser/events/suggest-predicates?q= endpoint
  - GET /browser/events/suggest-objects?q= endpoint
  - predicate_iri filter parameter on EventQueryService.list_events()
  - pred query parameter on event_log() route with filter chip
  - Autocomplete UI for operation type, predicate, and object filters in event log
  - Fix for ShapesService to iterate inline blank-node property shapes (sh:property objects)
key_files:
  - backend/app/browser/events.py
  - backend/app/events/query.py
  - backend/app/templates/browser/event_log.html
  - backend/app/templates/browser/_event_suggestions.html
  - frontend/static/css/workspace.css
  - backend/app/services/shapes.py
  - backend/tests/test_event_suggestions.py
key_decisions:
  - D161: Iterate both rdf:type sh:PropertyShape subjects AND sh:property objects to capture inline blank-node property shapes
patterns_established:
  - htmx-driven autocomplete pattern: text input + hx-trigger="focus" or "keyup changed delay:300ms" → suggestion template fragment → JS click handler applies filter via htmx.ajax
  - Suggestion template fragment (_event_suggestions.html) is reusable for any filter-type autocomplete dropdown
observability_surfaces:
  - logger.warning in each suggestion endpoint on SPARQL query failure
  - Predicate filter chip shows resolved human-readable label (e.g. "property: Title") — visual indicator of shapes service health
  - Suggestion items include data-value attributes for DOM inspection
  - Empty suggestions show "No matches" message
duration: 50min
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Add suggestion endpoints and autocomplete UI for event log filters

**Added three suggestion endpoints (types, predicates, objects) with htmx-driven autocomplete dropdowns and predicate filter support in the event log**

## What Happened

1. **Added `predicate_iri` filter to `EventQueryService.list_events()`** in `query.py`:
   - New optional parameter `predicate_iri: str | None = None`
   - When set, adds `FILTER EXISTS { GRAPH ?event { ?s <pred_iri> ?o . FILTER(?s != ?event) } }` to the SPARQL query
   - Wired through from `event_log()` route via `pred: str | None = Query(default=None)`

2. **Added three suggestion endpoints** in `events.py`:
   - `GET /browser/events/suggest-types` — queries distinct `sempkm:operationType` values from event graphs, returns HTML fragment
   - `GET /browser/events/suggest-predicates?q=` — queries distinct predicates from event data triples, resolves labels via ShapesService, filters by `q` parameter
   - `GET /browser/events/suggest-objects?q=` — queries distinct `sempkm:affectedIRI` values with optional SPARQL text filter, resolves labels via LabelService, filters by `q` parameter
   - All return the shared `_event_suggestions.html` template fragment

3. **Created `_event_suggestions.html` template** — shared suggestion dropdown fragment with `data-value` and `data-filter-param` attributes on each suggestion button

4. **Updated `event_log.html`** — replaced static `<select>` dropdown with three autocomplete text inputs (`#event-op-filter`, `#event-pred-filter`, `#event-obj-filter`), added JS click handler for suggestion selection, close-on-outside-click and Escape key behavior

5. **Added CSS in `workspace.css`** — `.event-autocomplete-wrapper` (relative positioning), `.event-autocomplete-target/.event-autocomplete-dropdown` (absolute dropdown), `.event-suggestion-item` (hover highlight), `.event-suggestion-empty` (no-match state)

6. **Added predicate filter chip** — when `pred` parameter is active, resolves human-readable label via ShapesService and shows "property: Title ×" chip

7. **Fixed ShapesService `get_labels_for_predicates()` and `get_helptext_for_predicates()`** — discovered that installed model shapes use inline blank nodes via `sh:property` (not explicitly typed `sh:PropertyShape`). Added iteration over `sh:property` objects in addition to typed PropertyShape subjects. This fix was essential for real-data label resolution.

## Verification

- **Unit tests:** 13/13 passed in `test_event_suggestions.py` — covers predicate filter SPARQL generation, type/predicate/object suggestion logic, label display format, local name extraction
- **T01 regression tests:** 14/14 passed in `test_event_log_labels.py` — label and helptext resolution unchanged by ShapesService fix
- **Browser testing (live Docker stack):**
  - Clicked operation filter → dropdown appeared with 9 operation types from real events (body.set, comment.create, edge.create, inference.run, model.install, object.create, object.patch, etc.)
  - Clicked "object.patch" suggestion → event log filtered to only object.patch events, "op: object.patch ×" filter chip appeared
  - Dismissed chip → all events returned
  - Typed "tit" in predicate filter → "Title (title)" and "Job Title (jobTitle)" suggestions appeared with human-readable SHACL labels
  - Clicked "Title (title)" → "property: Title ×" filter chip appeared, events filtered
  - Typed "sempkm" in object filter → 20+ suggestions with resolved labels ("Carol Singh", "Bobby Martinez", "SemPKM Development", etc.)
  - All browser assertions passed: 3 filter inputs visible, date inputs visible, no console errors

## Diagnostics

- Check `#op-suggestions`, `#pred-suggestions`, `#obj-suggestions` divs in DOM — they contain the suggestion dropdown HTML after focus/keyup
- Each `.event-suggestion-item` has `data-value` (the IRI/value) and `data-filter-param` (the query param name) for inspection
- Backend logs show `logger.warning` if any suggestion SPARQL query fails
- Predicate filter chip shows "property: {label}" — if label is a raw IRI local name instead of capitalized sh:name, shapes service resolution may have failed

## Deviations

- **ShapesService blank-node fix:** The plan assumed `get_labels_for_predicates()` worked with real data. In practice, it returned empty results because the installed model shapes use inline blank nodes (via `sh:property`) without explicit `rdf:type sh:PropertyShape`. Fixed by adding `sh:property` object iteration. This fix improves T01's event detail label resolution too.
- **Suggestion template:** Used a shared `_event_suggestions.html` fragment instead of inline HTML generation in each endpoint — cleaner separation of concerns

## Known Issues

- The operation filter input shows the raw value (e.g. "object.patch") from previous filter — but since it's now a text input instead of a select, the operation type is displayed but doesn't auto-populate the dropdown selection state
- Object suggestion display truncates long IRIs with "..." prefix — acceptable for readability but may hide distinguishing prefixes on similar IRIs

## Files Created/Modified

- `backend/app/browser/events.py` — added 3 suggestion endpoints (`suggest-types`, `suggest-predicates`, `suggest-objects`), `pred` parameter + ShapesService dependency on `event_log()`, predicate filter chip
- `backend/app/events/query.py` — added `predicate_iri` parameter to `list_events()` with FILTER EXISTS clause
- `backend/app/templates/browser/event_log.html` — replaced static select with 3 autocomplete inputs, added JS click handler/close behavior
- `backend/app/templates/browser/_event_suggestions.html` — new shared suggestion dropdown template fragment
- `frontend/static/css/workspace.css` — added autocomplete dropdown styling (wrapper, dropdown, suggestion items, empty state)
- `backend/app/services/shapes.py` — fixed `get_labels_for_predicates()` and `get_helptext_for_predicates()` to also iterate `sh:property` blank-node objects
- `backend/tests/test_event_suggestions.py` — new test file with 13 tests for predicate filter and suggestion logic
- `.gsd/milestones/M012/slices/S01/tasks/T02-PLAN.md` — added Observability Impact section
