---
estimated_steps: 7
estimated_files: 3
---

# T02: LinearClient with GraphQL queries, pagination, token refresh, and unit tests

**Slice:** S01 — OAuth + App Skeleton + Linear Client
**Milestone:** M016

## Description

Implements the core Linear API client that all subsequent slices depend on. `LinearClient` wraps the SDK's `HttpClient` for authenticated GraphQL requests to `https://api.linear.app/graphql`, with cursor-based pagination, automatic token refresh on 401, rate limit handling, and typed exceptions. This is pure logic with no platform runtime dependencies — ideal for thorough unit testing via pytest.

The client reads auth tokens from `StateClient` (set by T03's auth flow) and handles the full lifecycle: initial request → 401 detection → refresh token exchange → retry with new token → store updated tokens.

## Steps

1. Create `apps/linear-sync/services/linear_client.py` with exception classes:
   - `LinearAPIError(Exception)` — base with `status_code`, `message`, `response_body` attrs
   - `LinearAuthError(LinearAPIError)` — 401/403 responses
   - `LinearRateLimitError(LinearAPIError)` — 429 responses, with `retry_after` attr (from header or default 60s)
   - `LinearQueryError(LinearAPIError)` — GraphQL-level errors (200 response but `errors` array in body)

2. Implement `LinearClient.__init__(self, http_client, state_client, client_id=None, client_secret=None)`:
   - `http_client`: SDK `HttpClient` instance (domain-enforced to api.linear.app)
   - `state_client`: SDK `StateClient` for reading/writing tokens
   - `client_id` / `client_secret`: optional, needed for OAuth token refresh (not needed for API key auth)
   - Internal `_refreshing` lock (asyncio.Lock) to prevent concurrent refresh attempts

3. Implement `async _get_auth_header(self) -> dict`:
   - Read `access_token` from state_client
   - If not found, read `api_key` from state_client (API key auth fallback)
   - If neither found, raise `LinearAuthError("Not authenticated")`
   - Return `{"Authorization": f"Bearer {token}"}`

4. Implement `async query(self, graphql: str, variables: dict | None = None) -> dict`:
   - Build JSON payload: `{"query": graphql, "variables": variables or {}}`
   - Get auth headers via `_get_auth_header()`
   - POST to `https://api.linear.app/graphql` via `http_client.post(url, json=payload, headers=headers)`
   - Handle response status:
     - **200 with `errors` key**: raise `LinearQueryError` with first error message
     - **401**: attempt token refresh via `_handle_token_refresh()`, retry once
     - **429**: raise `LinearRateLimitError` with `Retry-After` header value
     - **Other 4xx/5xx**: raise `LinearAPIError`
   - Return `response.json()["data"]`

5. Implement `async _handle_token_refresh(self)`:
   - Acquire `_refreshing` lock to prevent concurrent refreshes
   - Read `refresh_token` from state_client — if missing (API key auth), raise `LinearAuthError("Token refresh not available with API key auth")`
   - POST to `https://api.linear.app/oauth/token` with `grant_type=refresh_token`, `client_id`, `client_secret`, `refresh_token`
   - Parse response for new `access_token` and `refresh_token`
   - Store both via state_client.set()
   - Log token refresh at INFO level (log event, NOT the token values)

6. Implement `async query_paginated(self, graphql: str, variables: dict | None, path_to_nodes: str, path_to_pageinfo: str) -> list`:
   - `path_to_nodes` is a dot-delimited path to the nodes array in the response (e.g. `"issues.nodes"`)
   - `path_to_pageinfo` is a dot-delimited path to pageInfo (e.g. `"issues.pageInfo"`)
   - Loop: query with `$after` cursor variable → extract nodes → check `pageInfo.hasNextPage` → set `$after = pageInfo.endCursor` → continue
   - Return aggregated list of all nodes
   - Safety limit: max 50 pages (5000 items at 100/page) to prevent runaway pagination

7. Implement convenience methods:
   - `async get_viewer(self) -> dict`: `{ viewer { id name email } }` — returns viewer dict
   - `async get_teams(self) -> list[dict]`: `{ teams { nodes { id name key description } } }` — returns team list
   - `async get_organization(self) -> dict`: `{ organization { id name urlKey } }` — returns org info

8. Write `backend/tests/test_linear_client.py` with comprehensive unit tests:
   - Use `importlib.util.spec_from_file_location` to load `linear_client` module from `apps/linear-sync/services/linear_client.py`
   - Mock `HttpClient` and `StateClient` — create simple async mock classes that record calls and return preset responses
   - **Test groups:**
     - Query construction: correct URL, JSON body with query+variables, Authorization header
     - Auth header: API key fallback when no access_token, error when no credentials
     - Error handling: 401 → LinearAuthError, 429 → LinearRateLimitError with retry_after, 5xx → LinearAPIError, GraphQL errors → LinearQueryError
     - Token refresh: 401 → refresh → retry succeeds, refresh failure propagates, refresh skipped for API key auth
     - Pagination: single page (hasNextPage=false), multi-page cursor chaining, safety limit at 50 pages
     - Convenience methods: get_viewer returns parsed data, get_teams returns node list, get_organization returns org dict
   - Target: ≥18 unit tests

## Must-Haves

- [ ] `LinearClient` sends authenticated GraphQL POST to `https://api.linear.app/graphql`
- [ ] Automatic token refresh on 401 with single-retry (no infinite loops)
- [ ] Cursor-based pagination with configurable paths and safety limit
- [ ] Typed exceptions: `LinearAuthError`, `LinearRateLimitError`, `LinearAPIError`, `LinearQueryError`
- [ ] API key fallback when no OAuth tokens present
- [ ] Convenience methods: `get_viewer()`, `get_teams()`, `get_organization()`
- [ ] ≥18 unit tests passing

## Verification

- `cd backend && python -m pytest tests/test_linear_client.py -v` — all tests pass
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/linear_client.py').read()); print('OK')"` — valid Python

## Inputs

- `apps/linear-sync/services/__init__.py` — empty package from T01
- `backend/sdk/sempkm_app_sdk/clients/http.py` — `HttpClient` API: `async get(url, **kwargs)`, `async post(url, **kwargs)` returning `httpx.Response`
- `backend/sdk/sempkm_app_sdk/clients/state.py` — `StateClient` API: `async get(key) -> str | None`, `async set(key, value)`
- Linear GraphQL API: single endpoint `https://api.linear.app/graphql`, auth via `Authorization: Bearer <token>`, cursor pagination via `after` variable and `pageInfo { hasNextPage endCursor }`
- Linear OAuth token endpoint: `https://api.linear.app/oauth/token` with `grant_type=refresh_token`

## Expected Output

- `apps/linear-sync/services/linear_client.py` — complete LinearClient class (~200-250 lines)
- `backend/tests/test_linear_client.py` — ≥18 unit tests covering all client behaviors
