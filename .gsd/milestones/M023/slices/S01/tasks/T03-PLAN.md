---
estimated_steps: 9
estimated_files: 6
---

# T03: Build Jira REST client, auth module, and person matcher with tests

**Slice:** S01 — ADF converter + field mapper + Jira client + auth scaffold
**Milestone:** M023

## Description

Build three service modules that form the Jira API interaction layer:
1. **JiraClient** — REST v3 client with JQL search, offset pagination, error hierarchy
2. **Auth module** — email + API token credential storage via StateClient
3. **PersonMatcher** — resolve Jira accountIds to SemPKM Person IRIs via SPARQL

All three follow established patterns from `apps/github-sync/` and `apps/linear-sync/`. The main Jira-specific differences are: (1) Basic auth uses email+token (not just token), (2) pagination uses `startAt`/`maxResults`/`total` (not Link headers), (3) person lookup uses accountId instead of login.

**Key decisions:**
- D233: API token auth via Basic auth header `base64(email:token)`
- D238: Jira user lookup requires extra API call per unique accountId (cache aggressively)

## Steps

1. Create `apps/jira-sync/services/jira_client.py`:
   - Define error hierarchy: `JiraAPIError(message, status_code, response_body)`, `JiraAuthError(JiraAPIError)`, `JiraRateLimitError(JiraAPIError, retry_after)`
   - `JiraClient.__init__(http_client, state_client)` — stores references
   - `_get_auth_header() -> str` — reads email+token from state, returns `Basic base64(email:token)` header. Raises JiraAuthError if missing.
   - `_request(method, path, **kwargs) -> Response` — builds full URL from site_url + path, adds auth + content-type headers, handles 401→JiraAuthError, 429→JiraRateLimitError (parse Retry-After header), other 4xx/5xx→JiraAPIError
   - `search_issues(jql: str, start_at: int = 0, max_results: int = 100) -> dict` — `POST /rest/api/3/search` with body `{"jql": jql, "startAt": start_at, "maxResults": max_results, "fields": ["*all"], "expand": ["names"]}`. Returns full response dict with `issues`, `startAt`, `maxResults`, `total`
   - `search_all_issues(jql: str) -> list[dict]` — paginated wrapper that calls `search_issues` in a loop until `startAt + len(issues) >= total`. Returns flat list of all issues. Max 50 pages safety limit.
   - `get_issue(issue_key: str) -> dict` — `GET /rest/api/3/issue/{issue_key}`
   - `update_issue(issue_key: str, fields: dict) -> None` — `PUT /rest/api/3/issue/{issue_key}` with body `{"fields": fields}`. Returns None (204 No Content on success)
   - `get_projects() -> list[dict]` — `GET /rest/api/3/project` returns list of project dicts (id, key, name)
   - `get_user(account_id: str) -> dict` — `GET /rest/api/3/user?accountId={account_id}` returns user dict with emailAddress, displayName
   - `get_myself() -> dict` — `GET /rest/api/3/myself` for connection verification
   - Use env var `JIRA_API_URL` override for testing (like `GITHUB_API_URL` pattern)

2. Create `apps/jira-sync/services/auth.py`:
   - State keys: `jira_email`, `jira_token`, `jira_site_url`
   - `store_credentials(state_client, email: str, token: str, site_url: str) -> None` — stores all 3 keys
   - `get_credentials(state_client) -> dict | None` — returns `{"email": ..., "token": ..., "site_url": ...}` or None if any key empty
   - `clear_credentials(state_client) -> None` — sets all 3 keys to empty string
   - `get_connection_status(state_client, jira_client) -> dict` — reads credentials, if present verifies via `jira_client.get_myself()`. Returns `{"connected": bool, "email": str|None, "display_name": str|None, "token_preview": str|None, "site_url": str|None, "error": str|None}`
   - `build_auth_header(email: str, token: str) -> str` — returns base64-encoded Basic auth value
   - `_mask_token(token: str) -> str` — first 4 + **** + last 4 (matching github-sync pattern)
   - Import JiraAuthError for error handling (with try/except ImportError fallback pattern from github-sync auth.py)

3. Create `apps/jira-sync/services/person_matcher.py`:
   - `PersonMatcher.__init__(graph_client, command_client, jira_client)` — note: jira_client is needed for accountId→email lookup
   - `_cache: dict[str, str]` — accountId→Person IRI LRU cache
   - `resolve(account_id: str | None, display_name: str | None, email: str | None) -> str | None`:
     - If account_id is None: return None
     - Check cache by account_id
     - If email provided: SPARQL lookup by email (foaf:mbox, crm:email UNION query)
     - If no email: call `jira_client.get_user(account_id)` to get email, then SPARQL lookup
     - Fallback: SPARQL lookup by account_id (bpkm:externalId)
     - Create person on miss via command_client (slug from display_name or email)
     - Cache result

4. Create `backend/tests/test_jira_client.py` with MockResponse/MockHttpClient/MockStateClient helpers:
   - Tests: JQL search (single page response), paginated search (multi-page), get_issue, update_issue (204), get_projects, get_user, get_myself
   - Error handling: 401→JiraAuthError, 429→JiraRateLimitError with Retry-After, 404→JiraAPIError, 500→JiraAPIError
   - Auth header: verify base64 encoding of email:token
   - Missing credentials: JiraAuthError raised
   - Pagination: startAt/total logic, max pages safety limit
   - Use `data if data is not None else {}` pattern per KNOWLEDGE.md K002

5. Create `backend/tests/test_jira_auth.py`:
   - Tests: store_credentials writes all 3 keys, get_credentials returns dict, get_credentials returns None when empty, clear_credentials sets to empty, _mask_token short/long tokens, get_connection_status connected (mock get_myself success), get_connection_status disconnected (no creds), get_connection_status error (mock get_myself failure), build_auth_header correct base64

6. Create `backend/tests/test_jira_person_matcher.py`:
   - Tests: email match found in SPARQL, account_id fallback (email lookup via jira_client), account_id match in SPARQL (bpkm:externalId), person creation on miss, cache hit on repeat resolve, None account_id returns None, jira_client.get_user failure handled gracefully

7. Run all tests: `cd backend && python -m pytest tests/test_jira_client.py tests/test_jira_auth.py tests/test_jira_person_matcher.py -v`

## Must-Haves

- [ ] JiraClient handles JQL search with offset pagination
- [ ] Error hierarchy: JiraAuthError (401), JiraRateLimitError (429), JiraAPIError (4xx/5xx)
- [ ] Auth stores/retrieves/clears email + token + site_url credentials
- [ ] build_auth_header produces correct base64 Basic auth
- [ ] PersonMatcher resolves by email, falls back to accountId lookup via Jira API, creates on miss
- [ ] LRU cache prevents duplicate lookups within a sync run
- [ ] 50+ total tests pass across 3 test files

## Verification

- `cd backend && python -m pytest tests/test_jira_client.py tests/test_jira_auth.py tests/test_jira_person_matcher.py -v` — all 50+ tests pass
- Each test file loads its module via importlib and runs independently

## Observability Impact

- Signals added/changed: structured logging in auth (credentials stored/cleared), client (request method+URL, error status codes), person_matcher (cache hit/miss/create)
- How a future agent inspects this: `get_connection_status()` returns full state dict; error objects carry status_code + response_body
- Failure state exposed: JiraAuthError for bad credentials, JiraRateLimitError with retry_after seconds, JiraAPIError with response body

## Inputs

- `apps/jira-sync/services/__init__.py` — created in T01
- `apps/github-sync/services/github_client.py` — reference for REST client pattern (error hierarchy, MockResponse, _request, pagination)
- `apps/github-sync/services/auth.py` — reference for auth module pattern (store/get/clear, connection status, mask)
- `apps/github-sync/services/person_matcher.py` — reference for PersonMatcher pattern (SPARQL lookup, create-on-miss, LRU cache)
- `backend/tests/test_github_client.py` — reference for MockResponse/MockHttpClient patterns
- `backend/tests/test_github_auth.py` — reference for auth test patterns
- `backend/tests/test_github_person_matcher.py` — reference for person matcher test patterns
- D233: API token auth with Basic auth header
- D238: accountId requires extra API call per unique user

## Expected Output

- `apps/jira-sync/services/jira_client.py` — ~300-line REST client with JQL search, pagination, error hierarchy
- `apps/jira-sync/services/auth.py` — ~120-line auth module with credential management
- `apps/jira-sync/services/person_matcher.py` — ~150-line person matcher with SPARQL lookup + Jira API fallback
- `backend/tests/test_jira_client.py` — 25+ tests covering all client methods and error paths
- `backend/tests/test_jira_auth.py` — 15+ tests covering all auth helpers
- `backend/tests/test_jira_person_matcher.py` — 12+ tests covering all resolution paths
