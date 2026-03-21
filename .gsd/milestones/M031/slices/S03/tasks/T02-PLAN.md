---
estimated_steps: 3
estimated_files: 2
skills_used:
  - test
---

# T02: Unit test for explorer endpoint + SQ-03 VFS verification

**Slice:** S03 — Saved Queries Everywhere
**Milestone:** M031

## Description

Write unit tests for the new `GET /browser/saved-queries/explorer` endpoint to verify it returns correct HTML with tree-leaf entries, drag attributes, and click handlers. Also verify that SQ-03 (saved queries as VFS mount scope) is already implemented — the VFS `build_scope_filter()` already resolves `scope_query` IRIs and the mount settings form already populates the scope dropdown from `/api/sparql/saved`.

## Steps

1. **Create `test_saved_queries_explorer.py`** — New test file at `backend/tests/test_saved_queries_explorer.py`. Use the same testing patterns as `backend/tests/test_view_scope.py`:
   - Mock `QueryService.list_all_queries()` returning a mix of user and model queries (use `SavedQueryData` dataclass from `app.sparql.query_service`)
   - Mock the Jinja2 templates and request objects
   - Test cases:
     - Endpoint returns HTML containing `.tree-leaf` class for each query
     - Each entry has `__canvasDragPayload` with correct `type:'query'` format
     - Each entry has `openGenericViewTab` onclick handler
     - Empty query list renders "No saved queries" empty state
     - Model queries are present alongside user queries
   - Use `from app.sparql.query_service import SavedQueryData` to build test data

2. **Verify SQ-03 already implemented** — Read `backend/app/vfs/strategies.py` `build_scope_filter()` and `_resolve_scope_query_sync()`. Confirm they resolve `scope_query` IRI to SPARQL text and inject it as a scope filter. Add a docstring/comment block in the test file documenting that SQ-03 is satisfied by existing code: VFS `build_scope_filter()` resolves scope queries, mount settings form populates `#mount-scope` dropdown from `/api/sparql/saved?include_shared=true` (see `workspace.js` line ~3460).

3. **Run tests** — Execute `python3 -m pytest backend/tests/test_saved_queries_explorer.py -v` and confirm all pass.

## Must-Haves

- [ ] Test file exists at `backend/tests/test_saved_queries_explorer.py`
- [ ] Tests cover: non-empty query list rendering, drag attributes, click handlers, empty state
- [ ] SQ-03 documented as already-implemented with file references
- [ ] All tests pass

## Verification

- `python3 -m pytest backend/tests/test_saved_queries_explorer.py -v` — all tests pass
- `grep -q 'SQ-03' backend/tests/test_saved_queries_explorer.py` — SQ-03 verification documented

## Inputs

- `backend/app/views/router.py` — the endpoint under test (modified in T01)
- `backend/app/templates/browser/saved_queries_explorer.html` — the template rendered by the endpoint (created in T01)
- `backend/app/sparql/query_service.py` — `SavedQueryData` dataclass and `list_all_queries()` to mock
- `backend/app/vfs/strategies.py` — `build_scope_filter()` to verify for SQ-03
- `backend/tests/test_view_scope.py` — reference for testing patterns

## Observability Impact

- **Test failure signals:** Pytest output surfaces which template rendering assertions fail (tree-leaf count, drag attributes, click handlers, empty state) — enabling fast regression detection when the template or endpoint changes.
- **Endpoint error handling coverage:** Tests verify that `logger.exception()` is called on `list_all_queries()` failure, confirming the error logging path works. A future agent can check server logs for `saved_queries_explorer: failed to load queries` when debugging.
- **SQ-03 scope resolution tests:** `test_build_scope_filter_accepts_scope_query` verifies the VFS scope filter sub-select is generated — if this test breaks, scope_query resolution in mounts is broken.

## Expected Output

- `backend/tests/test_saved_queries_explorer.py` — new test file with endpoint tests and SQ-03 documentation
