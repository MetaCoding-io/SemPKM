---
id: T01
parent: S04
milestone: M031
provides:
  - _detect_status_field() method for SHACL sh:in property detection
  - _build_kanban_select() static method for kanban SPARQL query generation
  - execute_kanban_query() method for server-side grouping into columns
  - kanban branch in generic_view() endpoint
  - kanban entry in RENDERER_REGISTRY
  - 18 unit tests covering detection, query building, and grouping logic
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/app/views/registry.py
  - backend/tests/test_kanban.py
key_decisions:
  - Column labels derived from title-casing the status value with dash/underscore-to-space conversion
  - Unset column uses sentinel value "__unset__" to distinguish from real status values
  - Status field detection prefers properties with "status" in path (case-insensitive), falls back to first sh:in property
patterns_established:
  - Kanban grouping via sh:in values follows same scope_filter sub-select pattern as table/card/graph
observability_surfaces:
  - logger.info on every kanban request with type and scope_query
  - logger.warning when status field detection fails
  - Graceful error templates for missing type or missing status property
duration: 25m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Backend kanban endpoint, status detection, and unit tests

**Add kanban renderer backend with SHACL-driven status field detection, SPARQL grouping query, router branch, registry entry, and 18 unit tests.**

## What Happened

Added three new methods to `ViewSpecService` in `service.py`:

1. `_detect_status_field(type_iri)` — queries SHACL shapes for the first PropertyShape with non-empty `in_values`, preferring properties with "status" in the path (case-insensitive). Returns `(None, [])` gracefully when shapes service is unavailable, form is missing, or no property has `in_values`.

2. `_build_kanban_select(type_iri, status_path, scope_filter)` — static method that generates a SPARQL SELECT query fetching `?s ?label ?statusValue` with optional scope sub-select, following the same pattern as `_build_default_select`.

3. `execute_kanban_query(type_iri, status_field, status_values, scope_filter)` — executes the kanban query, deduplicates subjects, and groups results into ordered columns matching the `sh:in` values. Objects with unrecognized status values go into an "Unset" column appended at the end.

In `router.py`, added `"kanban"` to `_VALID_RENDERERS` and restructured the if/elif chain in `generic_view()` to include a kanban branch. The branch handles three cases: no type selected (error message), type with no status property (error message), and normal kanban rendering with full context.

In `registry.py`, added the `"kanban"` entry pointing to `browser/kanban_view.html`.

Created `test_kanban.py` with 18 tests across three test classes covering detection, query building, and execution/grouping logic.

## Verification

- `python -m pytest backend/tests/test_kanban.py -v` — all 18 tests pass
- `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` — no syntax errors
- `python3 -c "import ast; ast.parse(open('backend/app/views/service.py').read())"` — no syntax errors
- `grep -q '"kanban"' backend/app/views/registry.py` — registry entry present

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_kanban.py -v` | 0 | ✅ pass | 0.44s |
| 2 | `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import ast; ast.parse(open('backend/app/views/service.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `grep -q '"kanban"' backend/app/views/registry.py` | 0 | ✅ pass | <1s |
| 5 | `grep -q 'kanban' backend/app/views/router.py` | 0 | ✅ pass | <1s |

### Slice-level verification (partial — T02 items expected to fail)

| # | Command | Exit Code | Verdict | Notes |
|---|---------|-----------|---------|-------|
| 1 | `python -m pytest backend/tests/test_kanban.py -v` | 0 | ✅ pass | 18/18 |
| 2 | `grep -q '"kanban"' backend/app/views/registry.py` | 0 | ✅ pass | |
| 3 | `grep -q 'kanban' backend/app/views/router.py` | 0 | ✅ pass | |
| 4 | `test -f backend/app/templates/browser/kanban_view.html` | 1 | ⏳ T02 | Template created in T02 |
| 5 | `test -f frontend/static/js/kanban.js` | 1 | ⏳ T02 | JS created in T02 |
| 6 | `grep -q 'Kanban View' backend/app/templates/browser/views_explorer.html` | 1 | ⏳ T02 | Explorer entry in T02 |
| 7 | `grep -q 'kanban' frontend/static/js/workspace.js` | 1 | ⏳ T02 | Label registration in T02 |

## Diagnostics

- **Request monitoring:** `grep "generic_view: renderer=kanban" <log>` shows all kanban requests with type and scope info.
- **Status detection failures:** `grep "_detect_status_field" <log>` surfaces shapes lookup failures.
- **Inspect endpoint:** `GET /browser/views/generic/kanban?type=<iri>` returns kanban HTML or user-facing error message.
- **Unit test regression:** `cd backend && .venv/bin/python -m pytest tests/test_kanban.py -v` (must run from `backend/` dir to avoid root `.env` loading issue).

## Deviations

- Tests must be run from `backend/` directory (not project root) because the root `.env` file contains `LINEAR_API_KEY` which is rejected as an extra field by the Pydantic Settings model. This is a pre-existing environment issue, not specific to this task.
- Added 18 tests (plan said 8+) — extra tests cover edge cases like case-insensitive status path matching, deduplication, empty results, query failures, and label fallback.

## Known Issues

- The kanban template (`kanban_view.html`) does not exist yet — the router references it but rendering will fail until T02 creates it. This is by design (T02 handles template + JS + wiring).

## Files Created/Modified

- `backend/app/views/service.py` — Added `_detect_status_field()`, `_build_kanban_select()`, `execute_kanban_query()` methods to ViewSpecService
- `backend/app/views/router.py` — Added `"kanban"` to `_VALID_RENDERERS`, restructured if/elif chain, added kanban branch in `generic_view()`
- `backend/app/views/registry.py` — Added `"kanban"` entry to `RENDERER_REGISTRY`
- `backend/tests/test_kanban.py` — New test file with 18 unit tests across 3 test classes
- `.gsd/milestones/M031/slices/S04/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
