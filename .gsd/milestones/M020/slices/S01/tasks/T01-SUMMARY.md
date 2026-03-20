---
id: T01
parent: S01
milestone: M020
provides:
  - Outlook Calendar Sync app scaffold with manifest, directory structure, and Microsoft OAuth 2.0 auth module
key_files:
  - apps/outlook-calendar/manifest.yaml
  - apps/outlook-calendar/services/auth.py
  - backend/tests/test_outlook_auth.py
key_decisions:
  - OutlookAuthError defined as local fallback in auth.py so the module loads standalone before outlook_client.py exists (T02 will provide the canonical version)
  - Microsoft refresh token rotation handled in refresh_if_expired — stores new refresh_token only when it differs from the old one
  - token_preview in get_connection_status masks to first 8 chars for diagnostics without exposing secrets
patterns_established:
  - Microsoft Identity Platform OAuth 2.0 flow with scope in both authorize and token requests
  - Env var overrides OUTLOOK_TOKEN_URL, OUTLOOK_AUTH_URL, OUTLOOK_API_URL for testability
observability_surfaces:
  - outlook.sync.auth logger — INFO on token store/clear, WARNING on exchange/refresh failures with status code + body
  - get_connection_status() returns connected, auth_method, microsoft_email, token_expiry, token_preview
  - OutlookAuthError carries status_code and response_body for structured failure diagnosis
duration: 12m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: App scaffold + manifest + auth module

**Built Outlook Calendar Sync app scaffold with manifest, Microsoft OAuth 2.0 auth module, and 41 unit tests**

## What Happened

Created the `apps/outlook-calendar/` directory structure with manifest, services package, and auth module adapted from the Google Calendar app for Microsoft Identity Platform OAuth 2.0.

Key differences from the Google Calendar auth module:
- Microsoft requires `scope` in both token exchange and refresh requests (Google only needs it in authorize)
- Microsoft may rotate refresh tokens on refresh — `refresh_if_expired` detects and stores rotated tokens
- `response_mode: query` replaces Google's `access_type: offline` + `prompt: consent`
- `get_connection_status()` includes a `token_preview` field (first 8 chars + `...`) for diagnostics

The manifest validates against `AppManifestSchema` with correct appId, network permissions for `graph.microsoft.com` and `login.microsoftonline.com`, two background tasks, and `calendar-clock` icon.

## Verification

- 41 unit tests pass covering all auth functions: authorize URL builder, code exchange, token refresh, refresh-if-expired (including rotation), token storage, connection status (including masking), clear state, error class, and constants
- Manifest validates against AppManifestSchema
- No hardcoded htmx URLs (no templates yet)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_outlook_auth.py -v` | 0 | ✅ pass | 0.08s |
| 2 | `python -c "from app.apps.manifest import parse_app_manifest; ..."` | 0 | ✅ pass | <1s |
| 3 | `grep -rn 'hx-...' apps/outlook-calendar/ \| grep -v '/app/outlook-calendar/'` | 1 (no matches) | ✅ pass | <1s |

## Diagnostics

- **Auth state inspection:** Call `get_connection_status(state_client)` to see `connected`, `auth_method`, `microsoft_email`, `token_expiry`, `token_preview` without exposing raw tokens
- **Logger:** `outlook.sync.auth` at INFO for token lifecycle events, WARNING for failures with status code + response body
- **Error diagnosis:** Catch `OutlookAuthError` and inspect `.status_code` and `.response_body` for structured failure info
- **Test isolation:** Set `OUTLOOK_TOKEN_URL` and `OUTLOOK_AUTH_URL` env vars to point at mock servers

## Deviations

None — followed the plan as written.

## Known Issues

- `OutlookAuthError` is defined as a local fallback in `auth.py` since `outlook_client.py` doesn't exist yet. T02 will create the canonical error classes in the client module, and the import chain will resolve correctly at that point.

## Files Created/Modified

- `apps/outlook-calendar/manifest.yaml` — App manifest with identity, permissions, tasks, UI page
- `apps/outlook-calendar/services/__init__.py` — Empty package init
- `apps/outlook-calendar/services/auth.py` — Microsoft OAuth 2.0 auth helpers (authorize URL, code exchange, refresh, store/clear, connection status)
- `backend/tests/test_outlook_auth.py` — 41 unit tests for the auth module
