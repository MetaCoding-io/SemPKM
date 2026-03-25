---
id: T02
parent: S03
milestone: M043
key_files:
  - backend/app/sparql/router.py
  - backend/app/admin/router.py
  - backend/app/templates/admin/api_tokens.html
  - backend/tests/test_token_scopes.py
key_decisions:
  - Scoped SPARQL endpoints to sparql:read (not separate read/write) since the API only supports read queries — SPARQL UPDATE is not exposed via HTTP
  - Left objects and admin browser endpoints on cookie-only auth — scope enforcement applies only to API endpoints that accept Bearer tokens
  - Used multi-value Form field (list[str]) for scope checkboxes in admin UI rather than a single comma-separated text input
duration: ""
verification_result: passed
completed_at: 2026-03-25T13:49:40.162Z
blocker_discovered: false
---

# T02: Add fine-grained API token scope enforcement to SPARQL, commands, and copilot endpoints with admin UI scope selection

**Add fine-grained API token scope enforcement to SPARQL, commands, and copilot endpoints with admin UI scope selection**

## What Happened

Wired `scope_required()` dependency to the SPARQL router endpoints (GET `/api/sparql`, POST `/api/sparql`, GET `/api/search`) — these now accept Bearer token authentication via `get_current_user_or_api` and enforce `sparql:read` scope. The commands router (`commands:execute`) and copilot router (`copilot:use`) were already wired from T01's infrastructure work.

The scope enforcement model:
- Session-authenticated requests (cookie) bypass scope checks entirely — sessions inherit full role permissions
- Bearer token requests must have at least one matching scope (or wildcard `*`)
- Denied requests return HTTP 403 with a descriptive message and emit a WARNING log with token ID, current scopes, required scope, and endpoint path

Updated the admin API tokens UI (`admin/api_tokens.html`) to show scope checkboxes in a 2-column grid layout with all 8 non-wildcard scopes. When no checkboxes are selected, the token defaults to wildcard (`*`). The token list table now shows a Scopes column, and the creation success banner displays the assigned scopes.

Updated the admin router handler to accept the `scopes` form field (multi-value from checkboxes), validate against `VALID_SCOPES`, and pass the scope string to `AuthService.create_api_token()`.

Wrote 26 tests covering: ApiToken.scopes property parsing (6 tests), VALID_SCOPES constant (2 tests), scope_required dependency unit tests (6 tests), token creation with scopes via JSON API (4 tests), SPARQL endpoint scope enforcement integration (5 tests), commands endpoint scope enforcement integration (2 tests), and scope denial logging (1 test).

## Verification

Ran all auth-related test files — 76 tests pass (26 new + 50 existing), zero regressions. New tests cover: scoped token gets 403 on out-of-scope endpoint, wildcard token passes all scope checks, session auth bypasses scope check, multi-scope tokens pass matching checks, scope denials logged with token ID and endpoint path.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_token_scopes.py -v -x` | 0 | ✅ pass | 1070ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_token_scopes.py tests/test_auth_tokens.py tests/test_commands_bearer_auth.py tests/test_demo_mode.py tests/test_magic_link_hardening.py -v -x` | 0 | ✅ pass | 3420ms |


## Deviations

The task plan mentioned adding scope_required to objects mutation endpoints and admin model endpoints. These routers use cookie-only auth (get_current_user / require_role) for htmx browser interactions — adding Bearer token support would require changing their auth dependency chain. The SPARQL, commands, and copilot endpoints are the natural API surface for external clients. Object mutations via API go through the commands router (already scoped). Admin model endpoints are browser-only and owner-gated. This covers the practical enforcement surface without breaking browser UI flows.

## Known Issues

None.

## Files Created/Modified

- `backend/app/sparql/router.py`
- `backend/app/admin/router.py`
- `backend/app/templates/admin/api_tokens.html`
- `backend/tests/test_token_scopes.py`
