---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T01: Backend timeline data layer — service methods, router endpoints, unit tests

**Slice:** S02 — Timeline / Gantt View
**Milestone:** M034

## Description

Build the backend data layer for the timeline view. This adds two new methods to `ViewSpecService` (`_build_timeline_select()` and `execute_timeline_query()`), registers `"timeline"` as a valid renderer in the router, and adds the `elif renderer == "timeline":` blocks to both `generic_view()` and `generic_view_data()`. The key novelty is the dependency-edge SPARQL query — a task with N `bpkm:dependsOn` edges produces N rows that must be grouped into a single task object with a dependency array. Unit tests prove the SPARQL construction and result grouping independently of any frontend.

## Steps

1. **Add `_build_timeline_select()` to `ViewSpecService`** in `backend/app/views/service.py`. Pattern follows `_build_calendar_select()` exactly. SELECT query fetches `?s ?label ?startDate ?endDate ?dep ?priority ?status` from tasks of the given type. Use the start/end paths from `_detect_date_fields()`. Wrap `?endDate`, `?dep`, `?priority`, and `?status` in OPTIONAL clauses (not all tasks have all fields). Include scope_filter sub-select when provided. Use the `bpkm:dependsOn` predicate IRI directly: `urn:sempkm:model:basic-pkm:dependsOn`. Use the standard label pattern: `OPTIONAL { ?s rdfs:label|dcterms:title ?label }`.

2. **Add `execute_timeline_query()` to `ViewSpecService`**. Execute the SPARQL, then group results by task IRI (`?s`). For each unique `?s`, collect: IRI, label, startDate (strip to YYYY-MM-DD if xsd:dateTime), endDate (strip to YYYY-MM-DD, fallback: startDate + 1 day if absent), list of dependency IRIs from `?dep`. Build and return `{"tasks": [...], "dependency_count": N}` where each task dict has `{id, name, start, end, progress, dependencies, custom_class}`. Progress defaults to 0. `custom_class` maps from `?status` if present (e.g., "done" → "bar-done", "in-progress" → "bar-active"). Tasks with no valid startDate are excluded.

3. **Register timeline in the router** (`backend/app/views/router.py`):
   - Add `"timeline"` to `_VALID_RENDERERS` set.
   - Add `elif renderer == "timeline":` block in `generic_view()`. Pattern: detect date fields, build `timeline_data_url`, pass context to `timeline_view.html` template. Handle no-type-selected (error message "Select a type to use Timeline View") and no-date-fields (error message "This type has no date properties for Timeline display"). Context dict matches the calendar/map pattern: `request`, `timeline_data_url`, `type_label`, `type_iri`, `selected_type`, `types`, `model_view_specs`, `scope_query`, `user_saved_queries`, `model_saved_queries`, `is_generic`, `renderer`, `pagination_base_url`, `pag_extra`, `spec`, `date_fields`, `error_message`.
   - Add `elif renderer == "timeline":` block in `generic_view_data()`. Update the guard `if renderer not in ("graph", "calendar", "map", "timeline"):`. Detect date fields, call `execute_timeline_query()`, return JSON.

4. **Write unit tests** in `backend/tests/test_timeline.py`:
   - `test_build_timeline_select_basic` — correct SPARQL structure with start+end fields, no scope
   - `test_build_timeline_select_with_scope` — scope_filter injected as sub-select
   - `test_build_timeline_select_no_end` — only start field, endDate still OPTIONAL
   - `test_execute_timeline_query_groups_deps` — 3 rows for 1 task with 2 deps → single task with `dependencies: [dep1, dep2]`
   - `test_execute_timeline_query_date_fallback` — dueDate used when scheduledStart absent (via `_detect_date_fields` priority)
   - `test_execute_timeline_query_strips_time` — `2024-01-15T14:00:00Z` → `2024-01-15`
   - `test_execute_timeline_query_empty` — no results → `{"tasks": []}`
   - `test_execute_timeline_query_no_date_excluded` — tasks without startDate not in result

5. **Run tests and fix** — `cd backend && .venv/bin/python -m pytest tests/test_timeline.py -v`. Iterate until all pass.

## Must-Haves

- [ ] `_build_timeline_select()` produces valid SPARQL with dependency, priority, status optionals
- [ ] `execute_timeline_query()` groups multi-row dependency results correctly
- [ ] `"timeline"` in `_VALID_RENDERERS`
- [ ] `generic_view()` handles timeline with type, no-type, and no-date-fields cases
- [ ] `generic_view_data()` handles timeline renderer and returns JSON
- [ ] Date strings stripped to YYYY-MM-DD format for Frappe Gantt compatibility
- [ ] Unit tests pass covering grouping, date fallback, date stripping, empty results

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_timeline.py -v` — all tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_timeline.py tests/test_calendar.py -v` — no regressions in calendar tests

## Observability Impact

- Signals added: `logger.info("generic_view: renderer=timeline ...")` and `logger.info("execute_timeline_query: type=%s tasks=%d deps=%d")` structured log lines
- How a future agent inspects: Check backend logs for `renderer=timeline` entries; hit `/browser/views/generic/timeline/data?type=<iri>` directly for raw JSON
- Failure state exposed: error_message in template context when no dates detected; empty `{"tasks": []}` response when no data

## Inputs

- `backend/app/views/service.py` — existing `_detect_date_fields()`, `_build_calendar_select()` as pattern reference
- `backend/app/views/router.py` — existing `generic_view()` and `generic_view_data()` with calendar/map blocks as pattern reference
- `backend/tests/test_calendar.py` — unit test pattern with `_make_property()`, `_build_service()` helpers
- `models/basic-pkm/shapes/basic-pkm.jsonld` — bpkm:scheduledStart, bpkm:scheduledEnd, bpkm:dependsOn property shapes
- `models/basic-pkm/ontology/basic-pkm.jsonld` — bpkm:dependsOn OWL declaration

## Expected Output

- `backend/app/views/service.py` — `_build_timeline_select()` and `execute_timeline_query()` added
- `backend/app/views/router.py` — timeline renderer registered in `_VALID_RENDERERS`, `generic_view()`, and `generic_view_data()`
- `backend/tests/test_timeline.py` — comprehensive unit test suite (8+ tests)
