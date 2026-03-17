# S01: Event Log Polish — Labels, Helptext & Autocomplete — UAT

**Milestone:** M012
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven for unit tests + live-runtime for browser verification)
- Why this mode is sufficient: Unit tests cover ShapesService label/helptext contracts and suggestion logic. Browser tests confirm the UI renders correctly with real triplestore data. Human-experience check validates label readability.

## Preconditions

- Docker stack running (`docker compose up -d`) with at least one Mental Model installed (basic-pkm recommended)
- At least 5-10 events in the event log (create some objects, edit properties, add edges to generate events)
- At least one `object.patch` event exists (edit an existing object's property to generate a diff-viewable event)

## Smoke Test

Open the event log (sidebar → Event Log or `/browser/events`). Click "Diff" on any `object.patch` event. The Property column should show human-readable labels (e.g. "Title", "Description") instead of raw IRIs (e.g. "dcterms:title").

## Test Cases

### 1. Predicate labels in event detail diff view

1. Open the event log
2. Find an `object.patch` event (any property edit)
3. Click the "Diff" button to expand the event detail
4. Look at the "Property" column in the diff table
5. **Expected:** Properties show human-readable labels like "Title", "Description", "Status" — not raw IRIs like "dcterms:title" or "http://purl.org/dc/terms/title"

### 2. Helptext tooltips on predicate labels

1. In the expanded event detail diff view from Test 1
2. Hover the mouse over a predicate label (e.g. "Title")
3. Wait for the browser tooltip to appear
4. **Expected:** Tooltip shows either SHACL helptext (descriptive text from the model shapes, e.g. "The name of this object") or the full predicate IRI if no helptext is defined
5. **Expected:** Labels with helptext have a dotted underline and a help cursor icon

### 3. Operation type autocomplete filter

1. Open the event log list view
2. Click or focus on the "Operation type" filter input
3. **Expected:** A dropdown appears listing all distinct operation types from the event data (e.g. "object.create", "object.patch", "body.set", "edge.create", etc.)
4. Click on "object.patch" in the dropdown
5. **Expected:** The event log filters to show only `object.patch` events. A filter chip appears showing "op: object.patch ×"
6. Click the × on the filter chip
7. **Expected:** All events reappear

### 4. Predicate autocomplete filter

1. Open the event log list view
2. Click or focus on the "Predicate" filter input
3. Type "tit" slowly
4. **Expected:** A dropdown appears showing predicates matching the prefix, with human-readable labels (e.g. "Title (title)"). These labels come from SHACL shapes.
5. Click on "Title (title)" in the dropdown
6. **Expected:** Events filter to show only events that modified the title predicate. A filter chip shows "property: Title ×"
7. Click the × to dismiss
8. **Expected:** All events reappear

### 5. Object autocomplete filter

1. Open the event log list view
2. Click or focus on the "Object" filter input
3. Type part of a known object's name (e.g. if you have a project named "SemPKM", type "sem")
4. **Expected:** A dropdown appears showing matching objects with their human-readable labels (e.g. "SemPKM Development")
5. Click on one of the suggested objects
6. **Expected:** Events filter to show only events related to that object. A filter chip appears with the object label.

### 6. Object.create event detail shows labels

1. Open the event log
2. Find an `object.create` event
3. Click "Diff" to expand the event detail
4. **Expected:** The creation detail view shows property labels (not IRIs) for all initial property values set during creation

### 7. Unit tests pass

1. Run: `cd backend && python -m pytest tests/test_event_log_labels.py tests/test_event_suggestions.py -v`
2. **Expected:** 37/37 tests pass (20 label/helptext + 17 suggestion/filter)

## Edge Cases

### Empty event log

1. On a fresh install with no events, open the event log
2. Click on each filter input
3. **Expected:** Suggestion dropdowns show "No matches" or an empty state — no errors, no crash

### Unknown predicates (not in SHACL shapes)

1. Create an event with a predicate not defined in any installed SHACL shape (e.g. via raw SPARQL or a custom property)
2. Open the event detail diff view
3. **Expected:** The predicate falls back to displaying the local name (e.g. "customProp" from "http://example.com/customProp") — not a raw full IRI, and no error

### Multiple filters combined

1. Apply an operation type filter (e.g. "object.patch")
2. Then apply a predicate filter (e.g. "Title")
3. **Expected:** Only events that are both `object.patch` AND involve the title predicate are shown. Both filter chips are visible.
4. Remove one chip
5. **Expected:** The remaining filter still applies

### Rapid typing in autocomplete

1. Type quickly in the predicate filter input (faster than the 300ms debounce)
2. **Expected:** Only one suggestion request fires after typing stops. No duplicate dropdowns or visual glitches.

## Failure Signals

- **Predicate labels show raw IRIs** (e.g. "http://purl.org/dc/terms/title" or "dcterms:title") in event detail → ShapesService label resolution failed. Check backend logs for `"Failed to resolve predicate labels from shapes graph"`.
- **No autocomplete dropdown appears** when clicking/typing in filter inputs → Suggestion endpoints may be broken. Check browser DevTools network tab for 500 errors on `/browser/events/suggest-*`.
- **"No matches" shown when matches should exist** → SPARQL queries against event graphs may be returning empty. Check that events exist and the triplestore is healthy.
- **Filter chips show raw IRIs instead of labels** → ShapesService or LabelService resolution failed for the filter display.
- **Console JS errors on filter interaction** → Check browser console for htmx or JS handler errors in the autocomplete code.

## Requirements Proved By This UAT

- EVTLOG-01 — Tests 1, 5, and 6 prove predicate/type/object labels resolve to human-readable text
- EVTLOG-02 — Test 2 proves helptext tooltips appear from SHACL annotations
- EVTLOG-03 — Tests 3, 4, and 5 prove autocomplete works for all three filter fields

## Not Proven By This UAT

- E2E Playwright automated test coverage — deferred to S04
- Performance under very large event logs (10,000+ events) — suggestion SPARQL queries may slow down
- Event log list view label resolution (only event detail diff view is covered in S01)

## Notes for Tester

- The quality of predicate labels depends on the installed Mental Model's SHACL shapes. With basic-pkm installed, expect labels like "Title", "Description", "Status", "Due Date" for common properties. Types without SHACL `sh:name` annotations will fall back to the local name portion of the IRI.
- Helptext availability depends on `sempkm:editHelpText` or `sh:description` annotations in the shapes. Not all properties have helptext — some will show just the full IRI in the tooltip.
- The predicate filter is new functionality that didn't exist before S01. The operation type and object filters existed as static controls — they now use autocomplete instead.
- Labels that appear capitalized (e.g. "Title") come from SHACL `sh:name`. Labels that appear lowercase (e.g. "title") are fallback local name extraction — this is a visual indicator of whether shapes-based resolution succeeded.
