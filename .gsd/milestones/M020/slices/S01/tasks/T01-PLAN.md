---
estimated_steps: 8
estimated_files: 4
---

# T01: App scaffold + manifest + auth module

**Slice:** S01 — Microsoft OAuth + Graph API Client
**Milestone:** M020

## Description

Create the Outlook Calendar Sync app scaffold by cloning from google-calendar and adapting for Microsoft Identity Platform OAuth 2.0. Build the auth module with authorize URL builder, code exchange, token refresh, token storage, connection status, and disconnect.

## Steps

1. Create `apps/outlook-calendar/` directory structure (services/, frontend/templates/, frontend/static/)
2. Write `manifest.yaml` — appId "outlook-calendar", name "Outlook Calendar Sync", icon "calendar-clock", network permissions for graph.microsoft.com and login.microsoftonline.com, two background tasks (poll-events, push-changes)
3. Create `services/__init__.py`
4. Build `services/auth.py` with Microsoft OAuth helpers: authorize URL, code exchange, refresh, store/clear tokens, connection status, OUTLOOK_API_URL + OUTLOOK_AUTH_URL env var overrides
5. Write `backend/tests/test_outlook_auth.py` with 20+ tests

## Must-Haves

- [ ] Manifest validates against AppManifestSchema
- [ ] Auth module has env var overrides for testability
- [ ] 20+ unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_outlook_auth.py -v` — all pass

## Observability Impact

- **Logger:** `outlook.sync.auth` — INFO on token store/verify/clear, WARNING on exchange/refresh failures with status code + response body
- **Inspection surface:** `get_connection_status()` returns `{connected, auth_method, microsoft_email, token_expiry, token_preview}` — agents/UI can call this to inspect auth state without reading raw tokens
- **Error class:** `OutlookAuthError` carries `status_code` and `response_body` for structured failure diagnosis
- **Env overrides:** `OUTLOOK_TOKEN_URL` and `OUTLOOK_AUTH_URL` allow pointing auth to mock servers in tests

## Inputs

- `apps/google-calendar/manifest.yaml` — reference manifest structure
- `apps/google-calendar/services/auth.py` — reference auth module to adapt

## Expected Output

- `apps/outlook-calendar/manifest.yaml`
- `apps/outlook-calendar/services/__init__.py`
- `apps/outlook-calendar/services/auth.py`
- `backend/tests/test_outlook_auth.py`
