---
id: T02
parent: S01
milestone: M016
provides:
  - LinearClient class with authenticated GraphQL queries, cursor-based pagination, automatic OAuth token refresh on 401, typed exceptions
  - 22 unit tests covering all client behaviors (query construction, auth, errors, refresh, pagination, convenience methods)
key_files:
  - apps/linear-sync/services/linear_client.py
  - backend/tests/test_linear_client.py
key_decisions:
  - Copy variables dict on each query execution to prevent mutation during pagination loops
  - Return LinearAuthError (not generic LinearAPIError) on 401 retry path — callers can distinguish auth failures from other HTTP errors
patterns_established:
  - importlib.util.spec_from_file_location to load app modules from apps/ directory into backend test suite
  - MockHttpClient/MockStateClient pattern for testing SDK-dependent app code without platform runtime
observability_surfaces:
  - Logger linear_sync.client: DEBUG for every GraphQL request, INFO for token refresh events, WARNING for rate limits
  - Typed exceptions carry status_code, message, response_body — callers get structured error info
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: LinearClient with GraphQL queries, pagination, token refresh, and unit tests

**Implemented LinearClient with authenticated GraphQL queries, cursor-based pagination, OAuth token refresh on 401, typed exceptions, and 22 passing unit tests**

## What Happened

Built `LinearClient` in `apps/linear-sync/services/linear_client.py` (~270 lines) with:

1. **Exception hierarchy:** `LinearAPIError` base with `status_code`/`message`/`response_body`, plus `LinearAuthError` (401/403), `LinearRateLimitError` (429 with `retry_after`), `LinearQueryError` (GraphQL-level errors in 200 responses).

2. **Auth header resolution:** Checks `access_token` first (OAuth), falls back to `api_key` (API key auth), raises `LinearAuthError` if neither exists.

3. **Query execution:** POSTs to `https://api.linear.app/graphql` with JSON payload and Bearer auth. Handles 401 (token refresh + single retry), 429 (rate limit with Retry-After parsing), 403, other 4xx/5xx, and GraphQL-level errors.

4. **Token refresh:** Acquires asyncio.Lock to prevent concurrent refreshes. Exchanges refresh_token at Linear's OAuth token endpoint. Stores new access_token and refresh_token via StateClient. Logs refresh events at INFO level (no token values).

5. **Cursor-based pagination:** `query_paginated()` with dot-delimited paths to nodes array and pageInfo. Safety limit of 50 pages (5000 items).

6. **Convenience methods:** `get_viewer()`, `get_teams()`, `get_organization()`.

During testing, found and fixed two bugs: (1) pagination mutated the shared variables dict in-place, causing cursor values to bleed across recorded mock calls — fixed by copying variables on each query execution; (2) retry-path 401s fell through to the generic `status >= 400` handler, raising `LinearAPIError` instead of `LinearAuthError` — fixed by handling 401 before the generic check regardless of refresh eligibility.

## Verification

- `cd backend && .venv/bin/python3 -m pytest tests/test_linear_client.py -v` — 22/22 tests pass
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/linear_client.py').read()); print('OK')"` — valid Python

Slice-level verification:
- ✅ LinearClient unit tests pass
- ⏳ Docker stack install — applies at T03 completion
- ⏳ Settings page load — applies at T03 completion

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python3 -m pytest tests/test_linear_client.py -v` | 0 | ✅ pass | 0.03s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/linear_client.py').read()); print('OK')"` | 0 | ✅ pass | <1s |

## Diagnostics

- **Run tests:** `cd backend && .venv/bin/python3 -m pytest tests/test_linear_client.py -v`
- **Logger:** `logging.getLogger("linear_sync.client")` — DEBUG for requests, INFO for token refresh
- **Exception inspection:** All exceptions carry `.status_code`, `.message`, `.response_body`; `LinearRateLimitError` adds `.retry_after`
- **Module import for debugging:** `importlib.util.spec_from_file_location("linear_client", "apps/linear-sync/services/linear_client.py")` to load outside the app runtime

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/linear-sync/services/linear_client.py` — LinearClient class with authenticated GraphQL queries, pagination, token refresh, typed exceptions (~270 lines)
- `backend/tests/test_linear_client.py` — 22 unit tests covering query construction, auth header, error handling, token refresh, pagination, and convenience methods
- `.gsd/milestones/M016/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section per pre-flight requirement
