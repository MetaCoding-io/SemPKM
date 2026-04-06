---
estimated_steps: 30
estimated_files: 3
skills_used: []
---

# T01: Extend kanban backend to detect and fetch enrichment fields

## Description

Extend the kanban backend to detect priority-like and date-like fields from SHACL shapes, include them in the SPARQL query, and pass enrichment data through to the template context.

**Current state:** `execute_kanban_query()` fetches only `?s`, `?label`, `?statusValue`. Items are `{iri, label}` dicts.

**Target state:** A new `_detect_enrichment_fields()` method scans SHACL PropertyShapes for:
- **Priority field**: first property with `sh:in` values whose path contains 'priority' (case-insensitive). Falls back to any `sh:in` property that isn't the status field.
- **Due date field**: first property with `sh:datatype` in `{xsd:date, xsd:dateTime}` or whose path local-name matches well-known date paths (`duedate`, `deadline`, `targetdate`, `enddate`). Uses existing `_detect_date_fields()` logic but only needs the start field.

`_build_kanban_select()` adds OPTIONAL clauses for detected fields. `execute_kanban_query()` populates item dicts with `priority` and `due_date` keys (both nullable). The router passes the enrichment metadata (field names) alongside column data.

## Steps

1. Add `_detect_enrichment_fields(type_iri)` method to `ViewSpecService` that returns `{priority_field: PropertyShape|None, date_field: PropertyShape|None}`. Scan the form properties from `get_form_for_type()`. For priority: find first `sh:in` property with 'priority' in path (case-insensitive), or first non-status `sh:in` property. For date: reuse the start-field detection from `_detect_date_fields()` (call it and take the first result).

2. Update `_build_kanban_select()` signature to accept optional `priority_path` and `date_path` strings. When non-None, add `OPTIONAL { ?s <priority_path> ?priorityValue }` and `OPTIONAL { ?s <date_path> ?dateValue }` to the WHERE clause.

3. Update `execute_kanban_query()` to:
   - Call `_detect_enrichment_fields()` for the type
   - Pass priority_path/date_path to `_build_kanban_select()`
   - Extract `priorityValue` and `dateValue` from bindings into each item dict
   - Include enrichment metadata in the return dict: `enrichment: {priority_field: {path, name, values}|null, date_field: {path, name}|null}`

4. Update the kanban branch in `generic_view()` in `router.py` to pass `enrichment` to the template context.

5. Add unit tests in `test_kanban.py`:
   - `test_detect_enrichment_priority_field` — type with priority sh:in property
   - `test_detect_enrichment_date_field` — type with xsd:date property
   - `test_detect_enrichment_no_fields` — type with no enrichment fields returns nulls
   - `test_build_kanban_select_with_enrichment` — SPARQL contains OPTIONAL clauses
   - `test_execute_kanban_query_enriched_items` — items include priority/due_date keys

6. Run existing tests to confirm no regressions.

## Must-Haves

- [ ] `_detect_enrichment_fields()` returns priority and date fields correctly
- [ ] `_build_kanban_select()` adds OPTIONAL SPARQL clauses when enrichment paths provided
- [ ] Items in `execute_kanban_query()` output include `priority` and `due_date` keys (nullable)
- [ ] Router passes `enrichment` metadata to template context
- [ ] All existing kanban tests pass
- [ ] New enrichment tests pass

## Inputs

- ``backend/app/views/service.py` — existing _detect_status_field, _build_kanban_select, execute_kanban_query`
- ``backend/app/views/router.py` — kanban branch in generic_view() at line ~1189`
- ``backend/tests/test_kanban.py` — existing test structure and helpers`
- ``backend/app/services/shapes.py` — PropertyShape dataclass definition`

## Expected Output

- ``backend/app/views/service.py` — new _detect_enrichment_fields() method, updated _build_kanban_select() and execute_kanban_query()`
- ``backend/app/views/router.py` — enrichment passed in kanban template context`
- ``backend/tests/test_kanban.py` — 5+ new enrichment test cases`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_kanban.py -v
