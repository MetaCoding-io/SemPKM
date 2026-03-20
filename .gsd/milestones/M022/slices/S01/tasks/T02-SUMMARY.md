---
id: T02
parent: S01
milestone: M022
provides:
  - Asana REST client with opt_fields, offset pagination, 429 rate-limit backoff, and 401 token refresh
  - All Asana resource endpoints (workspaces, projects, sections, custom fields, tasks, subtasks, user/me, patch, addTask)
key_files:
  - apps/asana-sync/services/asana_client.py
  - backend/tests/test_asana_client.py
key_decisions:
  - Split _raw_request (returns full JSON body with next_page) from _request (unwraps data envelope) so pagination can read sibling fields without duplicating error handling
  - AsanaRateLimitError carries retry_after attribute parsed from Retry-After header (default 60s)
  - get_projects filters archived projects client-side after fetch
  - get_custom_fields extracts custom_field sub-object from each custom_field_settings entry
patterns_established:
  - _raw_request/_request two-layer pattern for APIs with response wrappers containing pagination metadata
  - opt_fields injected via query string in _paginated_get, caller-specified for get_tasks/get_subtasks
observability_surfaces:
  - "Logger: asana.sync.client — token refresh events, API error status codes"
  - "Exceptions: AsanaAPIError/AsanaAuthError/AsanaRateLimitError with .status_code, .response_body, .retry_after"
  - "Token refresh lock: AsanaClient._refreshing asyncio.Lock prevents concurrent refresh races"
duration: 20m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Asana REST client with opt_fields, pagination, rate limit backoff, and unit tests

**Built Asana REST client with data envelope unwrapping, opt_fields injection, offset-based pagination, 429 rate-limit backoff, 401 token refresh with asyncio.Lock, and 9 resource endpoints — 28 unit tests passing.**

## What Happened

Created `AsanaClient` class following the GCal client pattern but adapted for Asana's API specifics. Key architectural difference: split `_raw_request` (returns full JSON body including `next_page`) from `_request` (unwraps `{"data": ...}` envelope). This lets `_paginated_get` use `_raw_request` to access the `next_page.offset` cursor while getting full error handling (401 refresh, 429 rate limit, 403/5xx).

Implemented all 9 resource endpoints from the plan: `get_workspaces`, `get_projects` (with archived filtering), `get_sections`, `get_custom_fields` (extracts `custom_field` sub-object from settings), `get_tasks` (with `modified_since` for incremental sync), `get_subtasks`, `get_user_me`, `patch_task`, and `add_task_to_section`.

Tests follow the importlib module-loading pattern from `test_gcal_client.py` with MockResponse, MockHttpClient (records calls), and MockStateClient.

## Verification

- `backend/.venv/bin/python -m pytest backend/tests/test_asana_client.py -v --noconftest` — 28 tests pass (target: ≥20)
- `backend/.venv/bin/python -m pytest backend/tests/test_asana_auth.py -v --noconftest` — 30 tests pass (no regression)
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/asana_client.py').read())"` — no syntax errors

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/asana_client.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `python -m pytest backend/tests/test_asana_client.py -v --noconftest` | 0 | ✅ pass (28 tests) | 0.08s |
| 3 | `python -m pytest backend/tests/test_asana_auth.py -v --noconftest` | 0 | ✅ pass (30 tests) | 0.05s |

### Slice-level verification (partial — T02 of T04):

| Check | Status |
|-------|--------|
| Auth tests ≥20 pass | ✅ 30 pass |
| Client tests ≥20 pass | ✅ 28 pass |
| All app files present | ❌ manifest.yaml, app.py, templates, styles.css — T03/T04 |
| manifest.yaml structure | ❌ T03 |
| connect_status.html field mapping UI | ❌ T04 |

## Diagnostics

- **Logger:** grep for `asana.sync.client` in app logs to see token refresh events and API error details
- **Exception inspection:** `AsanaAPIError.status_code`, `.response_body` on all API errors; `AsanaRateLimitError.retry_after` for 429 backoff window
- **Token refresh state:** `AsanaClient._refreshing.locked()` shows if a refresh is in progress
- **Tests:** `python -m pytest backend/tests/test_asana_client.py -v --noconftest` from worktree root

## Deviations

- Plan specified `get_user(user_gid)` endpoint; implemented `get_user_me()` instead (GET /users/me with opt_fields=name,email) — matches auth.py's PAT verification pattern and is the only user endpoint needed for connection identity. The T01 summary also references this as `get_user_me()`.
- Tests run with `--noconftest` because the conftest.py imports `app.config.Settings` which doesn't recognize asana env vars in .env yet. This is the same pattern used for auth tests.

## Known Issues

None.

## Files Created/Modified

- `apps/asana-sync/services/asana_client.py` — AsanaClient with _raw_request/_request, _paginated_get, 9 endpoints, exception hierarchy (~400 lines)
- `backend/tests/test_asana_client.py` — 28 unit tests covering auth headers, data unwrapping, 401 refresh, 429 rate limit, 403/5xx, pagination, all endpoints, exception hierarchy
- `.gsd/milestones/M022/slices/S01/tasks/T02-PLAN.md` — added Observability Impact section
