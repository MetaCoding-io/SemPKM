---
id: T03
parent: S01
milestone: M023
provides:
  - "JiraClient REST v3 client with JQL search, offset pagination, error hierarchy (JiraAPIError, JiraAuthError, JiraRateLimitError)"
  - "Auth module: store_credentials, get_credentials, clear_credentials, get_connection_status, build_auth_header, _mask_token"
  - "PersonMatcher.resolve(account_id, display_name, email) with SPARQL lookup, Jira API fallback, create-on-miss, LRU cache"
key_files:
  - apps/jira-sync/services/jira_client.py
  - apps/jira-sync/services/auth.py
  - apps/jira-sync/services/person_matcher.py
  - backend/tests/test_jira_client.py
  - backend/tests/test_jira_auth.py
  - backend/tests/test_jira_person_matcher.py
key_decisions:
  - "Used asyncio.run() wrapper pattern in tests instead of @pytest.mark.asyncio — pytest-asyncio is not installed in the venv (only anyio)"
patterns_established:
  - "Jira Basic auth via base64(email:token) — different from GitHub PAT token auth"
  - "Offset pagination (startAt/maxResults/total) loop with MAX_PAGINATION_PAGES=50 safety limit"
  - "PersonMatcher takes jira_client as 3rd dependency for accountId→email lookup (Jira only provides accountId in issue payloads)"
observability_surfaces:
  - "get_connection_status() returns full state dict (connected, email, display_name, token_preview, site_url, error)"
  - "JiraAuthError (401), JiraRateLimitError (429 with retry_after), JiraAPIError (4xx/5xx with status_code + response_body)"
  - "Structured logging in auth (credential stored/cleared), client (request method+URL), person_matcher (cache hit/miss/create)"
duration: 25m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: Build Jira REST client, auth module, and person matcher with tests

**Implemented Jira REST client (JQL search, offset pagination, error hierarchy), auth module (email+token+site_url credential management), and person matcher (SPARQL lookup with Jira API fallback) — 68 passing tests across 3 test files.**

## What Happened

Built three service modules following the established github-sync patterns:

1. **JiraClient** (`jira_client.py`, ~250 lines): REST v3 client with Basic auth (base64 email:token), `_request()` with error hierarchy (401→JiraAuthError, 429→JiraRateLimitError with Retry-After parsing, 4xx/5xx→JiraAPIError), `search_issues()` via POST with JQL body, `search_all_issues()` paginated wrapper using startAt/total offset pagination (50-page safety limit), plus `get_issue`, `update_issue`, `get_projects`, `get_user`, `get_myself`. Uses `JIRA_API_URL` env var override for testing.

2. **Auth module** (`auth.py`, ~130 lines): `store_credentials`/`get_credentials`/`clear_credentials` for email+token+site_url via StateClient, `build_auth_header` for base64 Basic auth, `_mask_token` (first 4 + **** + last 4), `get_connection_status` verifying via `get_myself()`.

3. **PersonMatcher** (`person_matcher.py`, ~200 lines): `resolve(account_id, display_name, email)` with 5-step lookup: cache check → SPARQL by email (if provided) → Jira API `get_user` for email (if not provided) → SPARQL by externalId → create-on-miss. Cache keyed by account_id. Handles Jira API failures gracefully (falls through to externalId lookup).

## Verification

All 68 tests pass (34 client + 20 auth + 14 person matcher). All 237 tests across 5 slice test files pass together.

- `test_jira_client.py`: 34 tests — auth header construction (6), request building (3), error handling (7), JQL search (3), pagination (4), get_issue (2), update_issue (2), get_projects (2), get_user (2), get_myself (2)
- `test_jira_auth.py`: 20 tests — store_credentials (2), get_credentials (5), clear_credentials (2), mask_token (5), build_auth_header (3), connection_status (4)
- `test_jira_person_matcher.py`: 14 tests — None returns None, email SPARQL hit, Jira API fallback, externalId hit, creation on miss, cache hit, API failure graceful, display_name-only creation, account_id-only creation, email skips Jira API, full miss path, API provides displayName, cache by account_id, different IDs not cached

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_jira_client.py -v` | 0 | ✅ pass | 0.1s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_jira_auth.py -v` | 0 | ✅ pass | 0.1s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_jira_person_matcher.py -v` | 0 | ✅ pass | 0.1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_jira_adf_converter.py tests/test_jira_field_mapper.py tests/test_jira_client.py tests/test_jira_auth.py tests/test_jira_person_matcher.py -v` | 0 | ✅ pass (237 total) | 0.2s |

## Diagnostics

- **JiraClient**: Call `get_myself()` to verify credentials. Error objects carry `status_code` and `response_body` for debugging. `search_all_issues(jql)` logs page progress.
- **Auth**: `get_connection_status()` returns full state dict — check `connected`, `error`, `token_preview` fields. Token never exposed raw.
- **PersonMatcher**: Cache hit/miss logged at DEBUG level. Failed Jira API calls logged at WARNING. Check `_cache` dict for resolved mappings.

## Deviations

- Used `asyncio.run()` wrapper pattern instead of `@pytest.mark.asyncio` decorator because `pytest-asyncio` is not installed in the backend venv (only `anyio` plugin is available). The existing github-sync tests use `@pytest.mark.asyncio` but they also fail in this venv — this is a pre-existing gap, not introduced by this task.

## Known Issues

- `pytest-asyncio` is not installed in the backend venv despite being listed in `pyproject.toml` dependencies. The existing github-sync test files (`test_github_client.py`, `test_github_auth.py`, `test_github_person_matcher.py`) also fail with "async def functions are not natively supported" for the same reason.

## Files Created/Modified

- `apps/jira-sync/services/jira_client.py` — REST v3 client with JQL search, offset pagination, Basic auth, error hierarchy (~250 lines)
- `apps/jira-sync/services/auth.py` — credential storage/retrieval/clearing, connection status, token masking (~130 lines)
- `apps/jira-sync/services/person_matcher.py` — accountId→Person IRI resolver with SPARQL + Jira API + create-on-miss + LRU cache (~200 lines)
- `backend/tests/test_jira_client.py` — 34 tests covering all client methods and error paths
- `backend/tests/test_jira_auth.py` — 20 tests covering all auth helpers
- `backend/tests/test_jira_person_matcher.py` — 14 tests covering all resolution paths
