---
id: T04
parent: S05
milestone: M034
provides:
  - 21 unit tests covering full TaskTemplateService CRUD lifecycle and instantiation with @slot: references
key_files:
  - backend/tests/test_task_templates.py
key_decisions: []
patterns_established:
  - SPARQL result helper (_sparql_bindings) for building mock RDF4J JSON responses in tests
observability_surfaces:
  - "pytest tests/test_task_templates.py -v — 21 tests covering create, list, get, update, delete, instantiate, error paths, and edge cases"
duration: 15m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T04: Unit tests for task template CRUD and instantiation

**Wrote 21 pytest unit tests for TaskTemplateService covering all CRUD operations, instantiation with/without subtasks, @slot: reference generation, user overrides, error paths, and JSON parse safety**

## What Happened

Created `backend/tests/test_task_templates.py` with a mocked `TriplestoreClient` (AsyncMock for query/update). The test file includes a `_sparql_bindings()` helper that builds RDF4J-format SPARQL JSON result dicts from simple key-value rows.

Tests cover:
- **Create** (3 tests): basic creation with properties, empty defaults, and SPARQL string escaping for quotes/newlines
- **List** (2 tests): multi-result parsing and empty result handling
- **Get** (3 tests): full field retrieval with parsed JSON blobs, not-found returns None, malformed JSON falls back to defaults
- **Update** (4 tests): title update with DELETE/INSERT SPARQL, not-found returns None, no-op returns existing unchanged, multi-field update
- **Delete** (2 tests): successful delete with DELETE WHERE, not-found returns False
- **Instantiate** (4 tests): single command without subtasks, user override merging, full subtask chain with @slot: references, custom predicate on subtask edges
- **Error case** (1 test): instantiate on nonexistent template raises ValueError
- **Utility** (2 tests): _safe_json_loads with valid and invalid input

All tests verify SPARQL targets the `urn:sempkm:task-templates` named graph, and instantiation tests verify the `@slot:main` / `@slot:subtask_N` reference pattern.

## Verification

All 21 tests pass. All 8 slice-level verification checks pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_task_templates.py -v` | 0 | ✅ pass | 2.7s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_seed_data.py -v` | 0 | ✅ pass | 3.4s |
| 3 | `rg "urn:sempkm:task-templates" backend/app/task_templates/service.py` | 0 | ✅ pass | <1s |
| 4 | `rg "Create from Template" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 5 | `rg "Run Weekly Review" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 6 | `python3 -c "import ast; ast.parse(...)  print('OK')"` | 0 | ✅ pass | <1s |
| 7 | `rg "logger\." backend/app/task_templates/service.py \| head -5` | 0 | ✅ pass | <1s |
| 8 | `rg "status_code=4" backend/app/task_templates/router.py` | 0 | ✅ pass | <1s |

## Diagnostics

- **Run tests:** `cd backend && .venv/bin/python -m pytest tests/test_task_templates.py -v` — full test output with per-test pass/fail
- **Quick check:** `cd backend && .venv/bin/python -m pytest tests/test_task_templates.py -q` — summary only
- **Single test:** `cd backend && .venv/bin/python -m pytest tests/test_task_templates.py::test_instantiate_with_subtasks -v`

## Deviations

Exceeded the planned 8 tests to 21 — added edge cases for empty defaults, SPARQL escaping, malformed JSON fallback, no-op updates, multi-field updates, user override merging, and custom predicates. These improve regression coverage at minimal cost.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_task_templates.py` — 21 unit tests for TaskTemplateService CRUD and instantiation
- `.gsd/milestones/M034/slices/S05/tasks/T04-PLAN.md` — added Observability Impact section per pre-flight
