---
id: T01
parent: S01
milestone: M019
provides:
  - todoist-sync app scaffold with manifest, auth module, routes, and templates
key_files:
  - apps/todoist-sync/manifest.yaml
  - apps/todoist-sync/app.py
  - apps/todoist-sync/services/auth.py
  - apps/todoist-sync/frontend/templates/connect.html
  - apps/todoist-sync/frontend/templates/connect_status.html
  - backend/tests/test_todoist_auth.py
key_decisions:
  - "Auth verifies via GET /rest/v2/projects (returns project count) rather than a user endpoint — Todoist REST v2 has no /user endpoint"
  - "Exception classes (TodoistAuthError, TodoistAPIError) co-located in auth.py — keeps the module self-contained"
patterns_established:
  - "Todoist auth follows github-sync pattern: store_token/get_stored_token/verify_token/get_connection_status/clear_credentials/_mask_token"
  - "Auth uses http_client (SDK HttpClient) directly instead of a separate client class — verify_token takes http_client + token args"
observability_surfaces:
  - "todoist.sync.auth logger — INFO on token store/verify/clear, WARNING on verification failures"
  - "todoist.sync logger — INFO on route handler outcomes"
  - "get_connection_status() returns {connected, auth_method, projects_count, token_preview}"
duration: 12m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: App scaffold + manifest + auth

**Created todoist-sync app with manifest, auth module (store/verify/status/disconnect), route handlers, connect/status templates, and 25 passing unit tests.**

## What Happened

Cloned the github-sync app structure and adapted it for Todoist. Key differences from github-sync:

1. **Auth verification** uses `GET /rest/v2/projects` with a `Bearer` token header (Todoist REST v2 pattern) instead of GitHub's `GET /user`. Returns project count as the verification signal.
2. **Connection status** returns `auth_method`, `projects_count`, and `token_preview` — richer than github-sync's `username`-based status since Todoist doesn't have a user profile endpoint in REST v2.
3. **Route naming** uses `api-token` instead of `api-key` to match Todoist's terminology.
4. **Templates** include placeholder sections for project selection and sync settings (wired in T04).

## Verification

- Manifest validates against `AppManifestSchema` — confirmed by loading it with `parse_app_manifest()`.
- All htmx URLs use `/app/todoist-sync/` prefix — confirmed by grep.
- 25 auth unit tests pass (exceeds the 15+ minimum).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_todoist_auth.py -v` | 0 | ✅ pass | 0.04s |
| 2 | `python -c "from backend.app.apps.manifest import parse_app_manifest; parse_app_manifest('apps/todoist-sync/manifest.yaml')"` | 0 | ✅ pass | — |
| 3 | `rg "hx-post\|hx-get" apps/todoist-sync/frontend/templates/` (all use /app/todoist-sync/ prefix) | 0 | ✅ pass | — |

## Diagnostics

- **Auth state:** Call `get_connection_status(state_client, http_client)` — returns `{connected, auth_method, projects_count, token_preview}`
- **Logger:** `todoist.sync.auth` at INFO/WARNING
- **Errors:** `TodoistAuthError` (401/403 from Todoist) and `TodoistAPIError` (other HTTP codes) — both carry `.status_code`

## Deviations

- Auth `verify_token` takes `http_client` + `token` as explicit args instead of using a separate client class. This differs from github-sync where `verify_pat` takes a `github_client` that internally reads the PAT. The Todoist pattern is simpler since there's no separate client yet (comes in T02).

## Known Issues

None.

## Files Created/Modified

- `apps/todoist-sync/manifest.yaml` — App manifest with todoist-sync identity, permissions, two background tasks
- `apps/todoist-sync/app.py` — Route handlers for connect/disconnect, placeholder task handlers
- `apps/todoist-sync/services/__init__.py` — Empty package init
- `apps/todoist-sync/services/auth.py` — Token storage, verification, connection status, masking, error classes
- `apps/todoist-sync/frontend/templates/connect.html` — PAT input form with htmx
- `apps/todoist-sync/frontend/templates/connect_status.html` — Connected status display with disconnect button
- `apps/todoist-sync/frontend/static/styles.css` — Minimal app-specific styles
- `backend/tests/test_todoist_auth.py` — 25 unit tests covering all auth functions
