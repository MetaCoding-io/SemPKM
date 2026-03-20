# T01: App scaffold + manifest + auth

**Slice:** S01 — Auth + Client + Pull Sync
**Milestone:** M019

## Description

Create the todoist-sync app directory structure by cloning github-sync. Write the manifest, auth module with PAT storage/verification, route handlers for connect/disconnect, and frontend templates.

## Steps

1. Create `apps/todoist-sync/` directory structure mirroring github-sync: `services/`, `frontend/templates/`, `frontend/static/`
2. Write `manifest.yaml` — appId "todoist-sync", name "Todoist Sync", network domain "api.todoist.com", same permissions as github-sync, tasks: poll-tasks (5m) and push-changes (5m)
3. Write `services/__init__.py` and `services/auth.py` — clone github-sync auth: store_token, verify_token (GET /rest/v2/projects), get_connection_status, clear_credentials, mask_token, get_stored_token
4. Write `app.py` — route handlers: GET /_fragments/connect, POST /_fragments/connect/api-token, POST /_fragments/disconnect. Placeholder task handlers.
5. Write `frontend/templates/connect.html` — PAT input form. All htmx URLs use `/app/todoist-sync/` prefix.
6. Write `frontend/templates/connect_status.html` — status display, masked token, disconnect. Placeholder sections for project selection and settings.
7. Write `backend/tests/test_todoist_auth.py` — 15+ tests using importlib pattern

## Must-Haves

- [ ] Manifest validates against AppManifestSchema
- [ ] Auth module matches github-sync pattern with all functions
- [ ] All htmx URLs use `/app/todoist-sync/` prefix
- [ ] 15+ auth unit tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_todoist_auth.py -v` — all pass

## Inputs

- `apps/github-sync/` — primary template to clone from
- `apps/github-sync/services/auth.py` — auth module pattern

## Expected Output

- `apps/todoist-sync/manifest.yaml`, `app.py`, `services/auth.py`, `services/__init__.py`
- `apps/todoist-sync/frontend/templates/connect.html`, `connect_status.html`
- `backend/tests/test_todoist_auth.py` — 15+ passing tests

## Observability Impact

- **Logger:** `todoist.sync.auth` — INFO on token store/verify/clear, WARNING on verification failures
- **Logger:** `todoist.sync` — INFO on route handler outcomes (connect, disconnect), WARNING on render failures
- **Inspection:** `get_connection_status()` returns `{connected, auth_method, projects_count, token_preview}` — agents can call this to check Todoist connection state
- **Failure visibility:** Auth errors surface as `TodoistAuthError` (401/403) or `TodoistAPIError` (other HTTP codes) with `status_code` attribute for programmatic handling
