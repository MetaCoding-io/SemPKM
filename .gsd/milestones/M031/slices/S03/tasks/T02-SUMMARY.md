---
id: T02
parent: S03
milestone: M031
provides:
  - Unit tests for saved queries explorer endpoint (28 tests)
  - SQ-03 VFS scope query verification with code references
key_files:
  - backend/tests/test_saved_queries_explorer.py
key_decisions:
  - Tests render real Jinja2 templates (not mocked output) for template rendering tests, while using mocked dependencies for endpoint behavior tests
patterns_established:
  - Template rendering tests via standalone Jinja2 Environment with FileSystemLoader pointed at app/templates
  - Endpoint behavior tests calling the async handler directly with mocked request/templates/query_service
observability_surfaces:
  - Test failure output surfaces which template assertions fail (tree-leaf count, drag attributes, click handlers, empty state)
  - Error handling test confirms logger.exception is called on list_all_queries failure
duration: 10m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Unit test for explorer endpoint + SQ-03 VFS verification

**Added 28 unit tests covering saved queries explorer template rendering, endpoint behavior, error handling, and SQ-03 VFS scope query verification**

## What Happened

Created `backend/tests/test_saved_queries_explorer.py` with three test classes:

1. **TestSavedQueriesExplorerTemplate** (18 tests) — Renders `saved_queries_explorer.html` with a real Jinja2 environment and verifies: tree-leaf entries for each query, Lucide icons (database for user, book-open for model), `__canvasDragPayload` drag attributes with query IDs and embed URLs, `openGenericViewTab` click handlers, empty-state "No saved queries" message, group headers ("My Queries" / "Model Queries"), and mixed query rendering.

2. **TestSavedQueriesExplorerEndpoint** (5 tests) — Calls the `saved_queries_explorer` async handler directly with mocked dependencies and verifies: `list_all_queries(user.id)` is called, queries list is passed in template context, correct template name is used, graceful degradation to empty list on exception, and `logger.exception` is called on error.

3. **TestSQ03VFSScopeQueryVerification** (5 tests) — Confirms SQ-03 (saved queries as VFS mount scope) is already implemented by exercising the real VFS code: `build_scope_filter()` generates a sub-select from resolved query text, returns empty string when no scope is set, `_extract_where_body()` extracts and renames variables, `_resolve_scope_query_sync` is importable, and `MountDefinition` has a `scope_query` field.

## Verification

All 28 tests pass. All slice-level verification checks pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('backend/app/sparql/router.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_saved_queries_explorer.py -v` | 0 | ✅ pass (28/28) | 0.68s |
| 4 | `grep -q 'section-queries' backend/app/templates/browser/workspace.html` | 0 | ✅ pass | <1s |
| 5 | `test -f backend/app/templates/browser/saved_queries_explorer.html` | 0 | ✅ pass | <1s |
| 6 | `grep -q '__canvasDragPayload' backend/app/templates/browser/saved_queries_explorer.html` | 0 | ✅ pass | <1s |
| 7 | `grep -q 'openGenericViewTab' backend/app/templates/browser/saved_queries_explorer.html` | 0 | ✅ pass | <1s |
| 8 | `grep -q 'logger.exception' backend/app/views/router.py` | 0 | ✅ pass | <1s |
| 9 | `grep -q 'SQ-03' backend/tests/test_saved_queries_explorer.py` | 0 | ✅ pass | <1s |

## Diagnostics

- **Test failures:** Run `cd backend && .venv/bin/python -m pytest tests/test_saved_queries_explorer.py -v` — each test name describes exactly what it checks.
- **SQ-03 evidence:** The test file header docstring documents the full SQ-03 verification with file references to `strategies.py`, `mount_router.py`, and `workspace.js`.

## Deviations

- **MountDefinition constructor:** Plan referenced `iri`/`label`/`root_path` fields; actual dataclass uses `id`/`name`/`path`. Fixed in SQ-03 tests to match reality.
- **Test execution command:** Tests must run from `backend/` directory using `.venv/bin/python -m pytest` (not `python3 -m pytest` from root) due to virtualenv and Pydantic settings configuration.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_saved_queries_explorer.py` — New test file with 28 tests covering template rendering, endpoint behavior, and SQ-03 verification
- `.gsd/milestones/M031/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M031/slices/S03/S03-PLAN.md` — Marked T02 as done
