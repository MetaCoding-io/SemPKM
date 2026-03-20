---
estimated_steps: 8
estimated_files: 2
---

# T02: Monday.com GraphQL client with complexity tracking and error hierarchy

**Slice:** S01 — Auth + GraphQL client + field mapper + person matcher
**Milestone:** M024

## Description

Build the `MondayClient` GraphQL client — the central API integration for the Monday.com Sync app. Monday.com's API has two unique features compared to Linear's GraphQL: a **complexity budget** system (each query has a "cost" and you get ~10M points per minute; exceeding it returns a special error), and **column value format asymmetry** (reads vs writes use different JSON shapes).

The client follows the `LinearClient` pattern (from `apps/linear-sync/services/linear_client.py`) but with Monday.com-specific adaptations for auth headers, complexity tracking, and Monday.com's GraphQL API structure.

## Steps

1. **Create error hierarchy** at the top of `apps/monday-sync/services/monday_client.py`:
   - `MondayApiError(Exception)` — base, with `message`, `status_code`, `response_body`
   - `MondayAuthError(MondayApiError)` — 401 Unauthorized
   - `MondayRateLimitError(MondayApiError)` — 429, with `retry_after: int` attribute
   - `MondayComplexityError(MondayApiError)` — complexity budget exceeded (comes as 200 with error in body), with `reset_in_seconds: int` attribute

2. **Build the `MondayClient` class** with constructor `__init__(self, http_client, state_client)`:
   - `MONDAY_API_URL = os.environ.get("MONDAY_API_URL", "https://api.monday.com/v2")` — env override for testing
   - `MAX_PAGINATION_PAGES = 50` — safety limit

3. **Implement `_get_auth_header()`** — reads `monday_api_token` from state, returns `{"Authorization": api_token}`. Raises `MondayAuthError` if no token stored. Note: Monday.com uses the raw token as the Authorization value (no "Bearer" prefix).

4. **Implement `_execute_query(query, variables)`** — the core GraphQL request method:
   - POST to `MONDAY_API_URL` with JSON body `{"query": query, "variables": variables}`
   - Add auth header + `Content-Type: application/json`
   - Handle HTTP errors: 401 → `MondayAuthError`, 429 → `MondayRateLimitError` (parse `Retry-After` header, default 60s)
   - Handle GraphQL errors: Monday.com returns `{"errors": [...], "data": null}` on errors. Check `errors[0].message` — if it contains "Complexity" or the error has `extensions.code == "COMPLEXITY"`, raise `MondayComplexityError` with `reset_in_x_seconds` from the response. Otherwise raise `MondayApiError`.
   - Track complexity: if response has `"complexity"` key, log the `after` and `reset_in_x_seconds` values at DEBUG level
   - Return `data` dict from response

5. **Implement convenience methods** — each method builds a GraphQL query string and calls `_execute_query()`:
   - `get_me()` — `{ me { id name email } }` → returns user dict
   - `get_boards()` — `{ boards(limit: 100) { id name state } }` → returns list of board dicts (filter to `state: "active"` in query or after)
   - `get_board_columns(board_id)` — `{ boards(ids: [$id]) { columns { id title type settings_str } } }` → returns list of column dicts
   - `get_board_groups(board_id)` — `{ boards(ids: [$id]) { groups { id title } } }` → returns list of group dicts
   - `get_board_items(board_id, limit=100, cursor=None)` — uses `items_page(limit, cursor)` nested query within `boards(ids: [$id])`. Returns `{"items": [...], "cursor": "..."}` dict. The cursor is `null` when no more pages.
   - `get_users(user_ids: list[int])` — `{ users(ids: $ids) { id name email } }` → returns list of user dicts
   - `get_tags(tag_ids: list[int])` — `{ tags(ids: $ids) { id name } }` → returns list of tag dicts
   - `change_multiple_column_values(board_id, item_id, column_values_json)` — mutation `change_multiple_column_values(board_id: $boardId, item_id: $itemId, column_values: $columnValues)` where `column_values` is a JSON string
   - `create_item(board_id, group_id, name, column_values_json)` — mutation `create_item(board_id: $boardId, group_id: $groupId, item_name: $name, column_values: $columnValues)`

6. **Implement `get_all_board_items(board_id)`** — paginated wrapper that calls `get_board_items()` in a loop following cursors until `cursor` is `null`. Safety limit of `MAX_PAGINATION_PAGES`.

7. **Write comprehensive tests** in `backend/tests/test_monday_client.py` using importlib loading pattern. Use `MockHttpClient` that returns canned GraphQL responses and `MockStateClient` for auth. Test categories:
   - Auth: token read, missing token → MondayAuthError
   - get_me: success response parsing
   - get_boards: success, empty boards
   - get_board_columns: column type/title/settings parsing
   - get_board_groups: group id/title parsing
   - get_board_items: single page, pagination (multiple cursors), empty items
   - get_all_board_items: multi-page aggregation, safety limit
   - get_users: single/multiple users, empty
   - get_tags: single/multiple tags
   - change_multiple_column_values: success mutation
   - create_item: success mutation
   - Error handling: 401 → MondayAuthError, 429 → MondayRateLimitError with retry_after, complexity error → MondayComplexityError with reset_in_seconds, generic GraphQL error → MondayApiError
   - MONDAY_API_URL env override

8. **Ensure MockHttpClient/MockResponse uses `data if data is not None else {}`** pattern per KNOWLEDGE.md K002 to avoid falsy empty list bug.

## Must-Haves

- [ ] 4-class error hierarchy: MondayApiError, MondayAuthError, MondayRateLimitError, MondayComplexityError
- [ ] MondayClient with 10 convenience methods + paginated wrapper
- [ ] Auth header is raw token (no Bearer prefix) per Monday.com API requirements
- [ ] Complexity tracking from GraphQL response `complexity` field
- [ ] ComplexityError detection from 200 responses with error body
- [ ] Cursor-based pagination for items_page queries
- [ ] MONDAY_API_URL env override for testing
- [ ] 50+ unit tests covering all methods and error paths

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_monday_client.py -v` — 50+ tests pass
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/monday_client.py').read())"` — no syntax errors

## Inputs

- `apps/monday-sync/services/auth.py` — from T01, provides state key name `monday_api_token`
- `apps/linear-sync/services/linear_client.py` — reference GraphQL client implementation (cursor pagination, error hierarchy, env URL override)
- `apps/jira-sync/services/jira_client.py` — reference REST client for error patterns
- `backend/tests/test_jira_client.py` — reference test file for importlib loading + MockHttpClient pattern

## Observability Impact

- **Logger:** `monday_sync.client` — DEBUG-level complexity budget tracking (`after` and `reset_in_x_seconds` per response), WARNING on GraphQL errors
- **Error hierarchy:** `MondayApiError` base carries `message`, `status_code`, `response_body`; `MondayComplexityError` adds `reset_in_seconds`; `MondayRateLimitError` adds `retry_after`
- **Inspection:** Call `get_me()` to verify token validity; complexity budget visible in DEBUG logs after every query
- **Failure signals:** `MondayAuthError` on missing/invalid token, `MondayRateLimitError` with retry guidance, `MondayComplexityError` with reset countdown

## Expected Output

- `apps/monday-sync/services/monday_client.py` — complete GraphQL client (~300-400 lines)
- `backend/tests/test_monday_client.py` — 50+ passing tests (~400-500 lines)
