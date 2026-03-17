---
id: S01
parent: M012
milestone: M012
provides:
  - ShapesService.get_labels_for_predicates(iris) method returning {predicate_iri: human_label}
  - ShapesService.get_helptext_for_predicates(iris) method returning {predicate_iri: helptext}
  - Predicate label and helptext resolution in event_detail() route via ShapesService
  - Human-readable predicate labels in event detail template (e.g. "Title" not "dcterms:title")
  - Helptext tooltips on predicate labels from SHACL sh:name / sempkm:editHelpText / sh:description
  - GET /browser/events/suggest-types endpoint (distinct operation types from event graphs)
  - GET /browser/events/suggest-predicates?q= endpoint (predicate labels from SHACL shapes, filtered)
  - GET /browser/events/suggest-objects?q= endpoint (affected IRIs with resolved labels, filtered)
  - predicate_iri filter parameter on EventQueryService.list_events()
  - htmx-driven autocomplete UI for operation type, predicate, and object filters in event log
  - Shared _event_suggestions.html template fragment for autocomplete dropdowns
  - Fix for ShapesService to iterate inline blank-node property shapes (sh:property objects)
requires: []
affects:
  - S04
key_files:
  - backend/app/services/shapes.py
  - backend/app/browser/events.py
  - backend/app/events/query.py
  - backend/app/templates/browser/event_detail.html
  - backend/app/templates/browser/event_log.html
  - backend/app/templates/browser/_event_suggestions.html
  - frontend/static/css/workspace.css
  - backend/tests/test_event_log_labels.py
  - backend/tests/test_event_suggestions.py
key_decisions:
  - D161: Iterate both rdf:type sh:PropertyShape subjects AND sh:property objects for inline blank-node property shapes
  - Used ShapesService (not LabelService) for predicate labels — vocabulary terms live in shapes/ontology graphs, not urn:sempkm:current
patterns_established:
  - SHACL property shape iteration pattern for predicate metadata extraction — reusable for any future predicate-level UI enrichment
  - htmx autocomplete pattern: text input + hx-trigger="focus" or "keyup changed delay:300ms" → suggestion template fragment → JS click handler applies filter via htmx.ajax
  - Shared suggestion template fragment (_event_suggestions.html) reusable for any filter-type autocomplete dropdown
observability_surfaces:
  - logger.warning on shapes graph query failure in get_labels_for_predicates() and get_helptext_for_predicates()
  - logger.warning in each suggestion endpoint on SPARQL query failure
  - HTML title attribute on .diff-pred-label shows helptext or full IRI for debugging
  - Predicate filter chip shows resolved label (e.g. "property: Title") — visual indicator of shapes service health
  - Resolved labels use capitalized sh:name (e.g. "Title") vs fallback lowercase local name (e.g. "title")
drill_down_paths:
  - .gsd/milestones/M012/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M012/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M012/slices/S01/tasks/T03-SUMMARY.md
duration: ~2h30m
verification_result: passed
completed_at: 2026-03-17
---

# S01: Event Log Polish — Labels, Helptext & Autocomplete

**Event log detail now shows human-readable predicate labels from SHACL shapes, helptext tooltips on hover, and autocomplete-driven filters for operation type, predicate, and object**

## What Happened

Three tasks delivered the full event log polish feature:

**T01 — Predicate labels and helptext in event detail.** Added `get_labels_for_predicates()` and `get_helptext_for_predicates()` to `ShapesService`. These iterate SHACL PropertyShapes, matching `sh:path` to requested predicate IRIs, and extract `sh:name` (label) and `sempkm:editHelpText` / `sh:description` (helptext). The `event_detail()` route now injects ShapesService and LabelService dependencies, collects all predicate IRIs from event diff data, resolves labels and helptext, and passes them to the template. The event detail template renders human-readable labels (e.g. "Title" instead of "dcterms:title") with HTML `title` attributes showing helptext or the full IRI. CSS adds a dotted underline and help cursor on predicates with helptext.

**T02 — Suggestion endpoints and autocomplete UI.** Added three suggestion endpoints (`suggest-types`, `suggest-predicates`, `suggest-objects`) that query real event data via SPARQL and return HTML fragments through a shared `_event_suggestions.html` template. The event log filter area was upgraded from a static `<select>` to three text inputs with htmx-driven autocomplete dropdowns (focus/keyup triggers). Added a `predicate_iri` filter parameter to `EventQueryService.list_events()` with a FILTER EXISTS clause. Filter chips display the resolved human-readable label with a dismiss button. During implementation, discovered that `get_labels_for_predicates()` returned empty on real data because installed model shapes use inline blank nodes (via `sh:property`) without explicit `rdf:type sh:PropertyShape`. Fixed by adding `sh:property` object iteration — this also improved T01's label resolution.

**T03 — Unit tests.** Added 37 tests across two files: 20 tests in `test_event_log_labels.py` covering label resolution (sh:name, rdfs:label fallback, inline blank-node shapes, empty/error cases) and helptext extraction (editHelpText preference, sh:description fallback, graceful degradation); 17 tests in `test_event_suggestions.py` covering predicate filter SPARQL generation, suggestion endpoint logic, label display format, and local name extraction.

## Verification

- **Unit tests:** 37/37 passed (20 label/helptext + 17 suggestion/filter tests)
- **Full suite regression:** 909/909 passed, no regressions
- **Browser verification (live Docker stack, T02):**
  - Operation filter: clicked → dropdown showed 9 operation types; clicked "object.patch" → filtered correctly with chip
  - Predicate filter: typed "tit" → "Title (title)" and "Job Title (jobTitle)" appeared with SHACL labels
  - Object filter: typed "sempkm" → 20+ suggestions with resolved human-readable labels
  - All 3 filter inputs visible, date inputs visible, no console errors
- **LSP diagnostics:** Clean (no real code errors)

## Requirements Advanced

- EVTLOG-01 — Predicate/type/object labels resolve to human-readable text in event log. Event detail diff view shows ShapesService-resolved labels for all predicate columns.
- EVTLOG-02 — Helptext tooltips on event log predicates from SHACL annotations. HTML title attributes populated from sempkm:editHelpText / sh:description, with dotted underline visual indicator.
- EVTLOG-03 — Autocomplete for event log filter fields. Three suggestion endpoints serve real event data; htmx dropdowns on all three filter fields.

## Requirements Validated

- None yet — browser E2E tests (S04) are the final validation step for EVTLOG-01/02/03.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- **ShapesService blank-node fix (D161):** The plan assumed `get_labels_for_predicates()` would work with real data from installation. In practice, installed model shapes use inline blank nodes via `sh:property` without explicit `rdf:type sh:PropertyShape` — the original implementation found zero shapes. Fixed by adding `sh:property` object iteration alongside typed node iteration. This was the critical discovery of this slice, now documented in KNOWLEDGE.md.
- **Shared suggestion template:** Used a shared `_event_suggestions.html` fragment instead of inline HTML in each endpoint — cleaner separation of concerns than the plan specified.

## Known Limitations

- Event log list view labels are not yet resolved (only event detail diff view) — the list view still shows raw operation type strings. Could be enhanced in a follow-up.
- Operation type filter shows raw value in the input after selection (e.g. "object.patch") — no human-readable display for operation types since they don't have SHACL labels.
- Object suggestion display truncates long IRIs with "..." prefix — acceptable but may hide distinguishing prefixes on similar IRIs.

## Follow-ups

- S04 will provide E2E Playwright tests that validate the full browser experience (EVTLOG-01/02/03 final validation).
- Event log list view could benefit from the same label resolution applied to its predicate/object columns (not in current scope).

## Files Created/Modified

- `backend/app/services/shapes.py` — added `get_labels_for_predicates()` and `get_helptext_for_predicates()` methods; fixed to iterate both typed and inline (sh:property) PropertyShapes
- `backend/app/browser/events.py` — added ShapesService/LabelService deps to `event_detail()`, 3 suggestion endpoints, `pred` filter parameter + filter chip on `event_log()`
- `backend/app/events/query.py` — added `predicate_iri` parameter to `list_events()` with FILTER EXISTS clause
- `backend/app/templates/browser/event_detail.html` — uses `predicate_labels` and `predicate_helptext` dicts, adds title attributes and has-helptext CSS class
- `backend/app/templates/browser/event_log.html` — replaced static select with 3 autocomplete inputs, JS suggestion handler, close-on-outside-click
- `backend/app/templates/browser/_event_suggestions.html` — new shared suggestion dropdown template fragment
- `frontend/static/css/workspace.css` — added `.diff-pred-label` tooltip styling, `.event-autocomplete-*` dropdown styling
- `backend/tests/test_event_log_labels.py` — 20 tests for label/helptext resolution
- `backend/tests/test_event_suggestions.py` — 17 tests for suggestion endpoints and predicate filter

## Forward Intelligence

### What the next slice should know
- `ShapesService.get_labels_for_predicates()` and `get_helptext_for_predicates()` are the canonical way to resolve predicate-level metadata from SHACL shapes. They handle both typed `sh:PropertyShape` nodes and inline blank nodes linked via `sh:property`. Any future code needing predicate labels should use these methods, not re-query shapes directly.
- The htmx autocomplete pattern (`text input → hx-trigger → _event_suggestions.html fragment → JS click handler`) is established and reusable. The shared template accepts `suggestions` (list of dicts with `value`, `label`, `filter_param` keys).
- The `predicate_iri` filter on `EventQueryService.list_events()` uses `FILTER EXISTS` with a subgraph pattern — this could be extended to other filter dimensions (e.g. object IRI filter) using the same approach.

### What's fragile
- **ShapesService shapes graph caching** — `_fetch_shapes_graph()` is called per-request for label/helptext resolution. If this becomes a performance concern under high event log traffic, the shapes graph should be cached (it changes only on model install/refresh). Currently acceptable for the low-traffic event log use case.
- **Suggestion SPARQL queries scan all event graphs** — the `suggest-types`, `suggest-predicates`, and `suggest-objects` endpoints issue `SELECT DISTINCT` across all event named graphs. On repositories with many thousands of events, these queries may become slow. Consider adding time-window constraints or caching if this happens.

### Authoritative diagnostics
- `pytest tests/test_event_log_labels.py tests/test_event_suggestions.py -v` — 37 tests cover the contract for all new ShapesService methods and suggestion endpoint logic. Run after any change to shapes.py or events.py.
- In the browser, hover any `.diff-pred-label` element — the `title` attribute shows either SHACL helptext or the full predicate IRI. If it shows a raw IRI for a predicate that should have a label (like dcterms:title), the ShapesService label resolution failed.
- Backend logs: look for `"Failed to resolve predicate labels from shapes graph"` or `"Failed to resolve predicate helptext from shapes graph"` warnings.

### What assumptions changed
- **Assumption:** `rdf:type sh:PropertyShape` iteration would find all property shapes → **Reality:** Installed models use inline blank nodes via `sh:property` that don't carry explicit type triples. Both iteration paths are required (D161). This is documented in KNOWLEDGE.md.
