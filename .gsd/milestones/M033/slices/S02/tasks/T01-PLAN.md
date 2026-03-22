---
estimated_steps: 7
estimated_files: 3
skills_used: []
---

# T01: Backend — register calendar renderer, date detection, data endpoint

**Slice:** S02 — Calendar View Renderer
**Milestone:** M033

## Description

Register the calendar renderer in the existing registry/router system, add date property auto-detection from SHACL shapes, build the calendar SPARQL query, and create a JSON data endpoint that returns FullCalendar-compatible events. This follows the exact pattern established by the kanban renderer (D291, M031/S04).

## Steps

1. **Register in `RENDERER_REGISTRY`** (`registry.py`): Add `"calendar": {"type": "calendar", "template": "browser/calendar_view.html"}` entry, same pattern as table/card/graph/kanban.

2. **Add to `_VALID_RENDERERS`** (`router.py`): Add `"calendar"` to the set `{"table", "card", "graph", "kanban"}`. Update the docstring on `generic_view()` to mention calendar.

3. **Add `_detect_date_fields()` to ViewSpecService** (`service.py`): New async method parallel to `_detect_status_field()`. Uses `self._shapes_service.get_form_for_type(type_iri)` to get SHACL properties. Scans for:
   - Properties with `datatype` matching `http://www.w3.org/2001/XMLSchema#date` or `http://www.w3.org/2001/XMLSchema#dateTime`
   - Properties with well-known date path names: `schema:startDate`, `schema:endDate`, `bpkm:dueDate`, `bpkm:targetDate`, `bpkm:completedDate`, `dcterms:created`, `dcterms:modified`
   - **Important**: The Event shape's `schema:startDate`/`schema:endDate` have NO explicit `sh:datatype`, so detection must also match by path name, not just datatype.
   - Start-date priority: path containing "startDate" > "dueDate" > "targetDate" > "created"
   - End-date priority: path containing "endDate" > "completedDate" > "modified"
   - Returns `tuple[PropertyShape | None, PropertyShape | None]` — `(start_property, end_property)`

4. **Add `_build_calendar_select()` static method** (`service.py`): Builds SPARQL SELECT query:
   ```sparql
   PREFIX rdf: <...>
   PREFIX rdfs: <...>
   PREFIX dcterms: <...>
   SELECT ?s ?label ?startDate ?endDate ?type WHERE {
     ?s rdf:type <TYPE_IRI> .
     ?s <START_PATH> ?startDate .
     OPTIONAL { ?s <END_PATH> ?endDate }
     OPTIONAL { ?s rdfs:label|dcterms:title ?label }
     OPTIONAL { ?s rdf:type ?type }
     <scope_clause if present>
   }
   ```
   When no type is selected, query types that have date properties (build a UNION or VALUES clause). The `end_date` path is always OPTIONAL since not all types have it.

5. **Add `execute_calendar_query()` async method** (`service.py`): Runs `_build_calendar_select()`, passes through `scope_to_current_graph()`, executes via `self._client.query()`. Transforms SPARQL bindings into FullCalendar JSON format:
   ```json
   [{"id": "<iri>", "title": "Event Label", "start": "2025-03-15", "end": "2025-03-16", "extendedProps": {"iri": "<iri>", "type": "<type_iri>"}}]
   ```
   Deduplicates by IRI (`?s`). Falls back to IRI local name when label is missing.

6. **Add `elif renderer == "calendar"` branch in `generic_view()`** (`router.py`): After the graph branch and before the kanban branch. Calls `_detect_date_fields(type_iri)` to find start/end properties. When no type is selected, renders the calendar template with no pre-detected fields — the data endpoint handles multi-type queries. Pass `date_fields`, `types_list`, `type_label`, `selected_type`, `scope_query`, `user_saved_queries`, `model_saved_queries`, `model_view_specs`, `renderer`, `is_generic`, `pagination_base_url`, `pag_extra`, `spec` to the template. Include `embed` support.

7. **Extend the `/browser/views/generic/{renderer}/data` endpoint** (`router.py`): Currently only handles `renderer == "graph"`. Add `elif renderer == "calendar"` that calls `execute_calendar_query()` with `type_iri` and `scope_filter_text`, returns JSON array directly.

## Must-Haves

- [ ] `"calendar"` registered in `RENDERER_REGISTRY` with correct template path
- [ ] `"calendar"` in `_VALID_RENDERERS` set
- [ ] `_detect_date_fields()` finds `schema:startDate`/`schema:endDate` on Event shape (even without explicit `sh:datatype`)
- [ ] `_detect_date_fields()` finds `bpkm:dueDate` on Task shape
- [ ] `_detect_date_fields()` falls back to `dcterms:created` when no explicit date properties exist
- [ ] `_detect_date_fields()` returns `(None, None)` for types with no date properties
- [ ] `_build_calendar_select()` produces valid SPARQL with scope filter support
- [ ] `execute_calendar_query()` returns FullCalendar-compatible JSON with `{id, title, start, end, extendedProps}`
- [ ] Calendar data endpoint at `/browser/views/generic/calendar/data` returns JSON array
- [ ] `generic_view()` has a working `elif renderer == "calendar"` branch

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` — passes (T03 creates this file, but the backend code must be correct)
- `python -c "from app.views.registry import RENDERER_REGISTRY; assert 'calendar' in RENDERER_REGISTRY"` works from `backend/` dir
- Import check: `python -c "from app.views.service import ViewSpecService; assert hasattr(ViewSpecService, '_detect_date_fields')"` works

## Inputs

- `backend/app/views/registry.py` — existing renderer registry to extend
- `backend/app/views/router.py` — existing generic_view() and data endpoint to extend
- `backend/app/views/service.py` — existing ViewSpecService with kanban methods as pattern reference
- `backend/app/services/shapes.py` — PropertyShape dataclass (has `path`, `name`, `datatype`, `in_values` fields)

## Expected Output

- `backend/app/views/registry.py` — calendar entry added to RENDERER_REGISTRY
- `backend/app/views/router.py` — calendar branch in generic_view() + calendar data in generic_graph_data()
- `backend/app/views/service.py` — _detect_date_fields(), _build_calendar_select(), execute_calendar_query() methods added

## Observability Impact

- **New log lines:** `execute_calendar_query: type=... start_path=... end_path=... scope=...` at INFO level on every calendar data request. `execute_calendar_query: returned N events` on completion. `generic_view: renderer=calendar type=... scope_query=...` on view render.
- **Failure signals:** `execute_calendar_query: query failed for type=...` at WARNING with traceback on SPARQL failure (returns empty array). `_detect_date_fields: shapes lookup failed for ...` at WARNING when ShapesService errors.
- **Inspection surface:** `GET /browser/views/generic/calendar/data?type=<iri>` returns JSON array of FullCalendar events — usable for debugging data issues.
