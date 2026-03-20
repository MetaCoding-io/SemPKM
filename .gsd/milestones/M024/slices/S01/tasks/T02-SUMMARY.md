---
id: T02
parent: S01
milestone: M024
provides:
  - MondayClient GraphQL client with 10 convenience methods, cursor-based pagination, complexity budget tracking, and 4-class error hierarchy
key_files:
  - apps/monday-sync/services/monday_client.py
  - backend/tests/test_monday_client.py
key_decisions:
  - Monday.com GraphQL queries use inline string interpolation (not GraphQL variables) for board_id/item_id since Monday.com's API expects integer board IDs directly in the query, not as typed variables
  - Complexity error detection uses dual check — extensions.code == "COMPLEXITY" OR message contains "complexity" — to handle both documented and undocumented Monday.com error formats
patterns_established:
  - MondayClient._execute_query() is the single HTTP gateway — all convenience methods build query strings and delegate to it, following the LinearClient pattern
  - MockHttpClient.request() matches the SDK HttpClient interface with method+url+kwargs — same pattern as test_jira_client.py
observability_surfaces:
  - monday_sync.client logger at DEBUG level — logs complexity budget (after, reset_in_x_seconds) from every query response
  - MondayApiError hierarchy carries status_code + response_body for all API failures
  - MondayComplexityError.reset_in_seconds tells callers exactly when to retry
  - MondayRateLimitError.retry_after parsed from Retry-After header (default 60s)
duration: 20m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Monday.com GraphQL client with complexity tracking and error hierarchy

**Built MondayClient with 10 convenience methods, cursor-based pagination, complexity budget tracking, 4-class error hierarchy, and 64 passing unit tests.**

## What Happened

Created `apps/monday-sync/services/monday_client.py` with a complete GraphQL client following the LinearClient pattern but adapted for Monday.com specifics:

1. **Error hierarchy** — 4 exception classes: `MondayApiError` (base with message/status_code/response_body), `MondayAuthError` (401), `MondayRateLimitError` (429 with retry_after), `MondayComplexityError` (200 with complexity error body, carries reset_in_seconds).

2. **Core `_execute_query()`** — single HTTP gateway that POSTs to MONDAY_API_URL, handles HTTP errors (401→auth, 429→rate limit, 4xx/5xx→generic), detects complexity errors in 200 responses (via extensions.code or message keyword), logs complexity budget at DEBUG level, and returns the `data` dict.

3. **10 convenience methods** — `get_me()`, `get_boards()`, `get_board_columns()`, `get_board_groups()`, `get_board_items()` (cursor pagination), `get_users()`, `get_tags()`, `change_multiple_column_values()`, `create_item()`, plus `get_all_board_items()` paginated wrapper with MAX_PAGINATION_PAGES=50 safety limit.

4. **Auth** — raw token Authorization header (no Bearer prefix) read from `monday_api_token` state key established in T01.

5. **64 unit tests** covering error hierarchy structure, auth header (raw token, no Bearer, missing/empty token), HTTP errors (401/403/429/500 with retry_after parsing), GraphQL errors (generic, complexity by extensions code, complexity by message keyword, reset_in_seconds sourcing), all 10 convenience methods (success/empty/edge cases), pagination (single page, multi-page, safety limit), mutations, API URL env override, complexity DEBUG logging, request payload structure, and K002 mock correctness.

## Verification

- 64 tests pass in `test_monday_client.py`
- 31 tests pass in `test_monday_auth.py` (T01, still passing)
- Python syntax validation passes on `monday_client.py`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python3 -m pytest tests/test_monday_client.py -v` | 0 | ✅ pass | 0.12s |
| 2 | `cd backend && .venv/bin/python3 -m pytest tests/test_monday_auth.py -v` | 0 | ✅ pass | 0.04s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/monday_client.py').read())"` | 0 | ✅ pass | <0.1s |

### Slice-level verification (intermediate — 2/7 checks available)

| # | Command | Exit Code | Verdict | Notes |
|---|---------|-----------|---------|-------|
| 1 | `pytest tests/test_monday_auth.py -v` | 0 | ✅ 31 pass | T01 |
| 2 | `pytest tests/test_monday_client.py -v` | 0 | ✅ 64 pass | T02 — this task |
| 3 | `pytest tests/test_monday_field_mapper.py -v` | — | ⏳ pending | T03 |
| 4 | `pytest tests/test_monday_person_matcher.py -v` | — | ⏳ pending | T04 |

## Diagnostics

- **Complexity budget inspection:** Set log level to DEBUG on `monday_sync.client` to see per-query complexity tracking (`after` remaining, `reset_in_x_seconds`)
- **Error diagnosis:** All `MondayApiError` subclasses carry `status_code` and `response_body` for debugging. `MondayComplexityError.reset_in_seconds` tells you when to retry. `MondayRateLimitError.retry_after` parsed from HTTP headers.
- **Test runner:** `cd backend && .venv/bin/python3 -m pytest tests/test_monday_client.py -v` — must run from backend/ directory with its venv
- **API URL override:** Set `MONDAY_API_URL` env var to redirect all queries to a local mock server for integration testing

## Deviations

None — implemented exactly as planned.

## Known Issues

None.

## Files Created/Modified

- `apps/monday-sync/services/monday_client.py` — Complete GraphQL client with error hierarchy, complexity tracking, 10 convenience methods, cursor pagination (~330 lines)
- `backend/tests/test_monday_client.py` — 64 unit tests covering all methods and error paths (~600 lines)
- `.gsd/milestones/M024/slices/S01/tasks/T02-PLAN.md` — Added missing Observability Impact section
