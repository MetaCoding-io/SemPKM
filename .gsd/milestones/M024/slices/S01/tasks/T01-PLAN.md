---
estimated_steps: 8
estimated_files: 9
---

# T01: App scaffold, auth module, connect UI, and auth tests

**Slice:** S01 — Auth + GraphQL client + field mapper + person matcher
**Milestone:** M024

## Description

Create the complete `apps/monday-sync/` directory structure following the pattern established by `apps/jira-sync/`. This task builds the app manifest, auth module for API token credential management, the initial app.py with connect/disconnect routes, connect form and status templates, scoped CSS, and comprehensive auth tests.

Monday.com uses a simpler auth model than Jira: a single API token (no email, no site URL). The auth header format is `Authorization: <api_key>` — no Basic encoding, no Bearer prefix.

## Steps

1. **Create `apps/monday-sync/manifest.yaml`** — Copy structure from `apps/jira-sync/manifest.yaml`. Key differences: `appId: "monday-sync"`, `name: "Monday.com Sync"`, icon `"columns"` (Lucide), `network: ["api.monday.com"]`, tasks `poll-tasks` and `push-changes` with 15m interval. No `requirements.txt` needed (SDK provides dependencies, no extra packages).

2. **Create `apps/monday-sync/requirements.txt`** — Empty or minimal (SDK provides core deps). Match pattern of other apps.

3. **Create `apps/monday-sync/services/__init__.py`** — Empty package init.

4. **Create `apps/monday-sync/services/auth.py`** — Follow `apps/jira-sync/services/auth.py` pattern but simplified for single-token auth:
   - State key: `monday_api_token`
   - `_mask_token(token)` — first4 + **** + last4
   - `store_credentials(state_client, api_token)` — store single token
   - `get_credentials(state_client) -> dict | None` — returns `{"api_token": ...}` or None
   - `clear_credentials(state_client)` — set token key to empty
   - `verify_connection(state_client, monday_client) -> dict` — call `monday_client.get_me()`, return user info
   - `get_connection_status(state_client, monday_client) -> dict` — returns `{connected, display_name, email, token_preview, error}`

5. **Create `apps/monday-sync/app.py`** — Follow `apps/jira-sync/app.py` pattern:
   - `monday_sync_app = App("monday-sync")`
   - `_make_client(ctx)` — create MondayClient (imports from services.monday_client)
   - `connect_fragment` route at `/_fragments/connect` — if connected render connect_status.html, else connect.html
   - `connect_credentials` POST route — read `api_token` from form, store, verify, render status
   - `disconnect_handler` POST route — clear credentials, render connect form
   - `save_boards` POST route at `/_fragments/settings/boards` — save selected board IDs to settings
   - `save_sync_config` POST route — save direction/interval
   - `sync_now` POST route — stub that calls pull_sync/push_sync (import deferred)
   - `poll_tasks` and `push_changes` task handlers — stubs
   - `on_startup` / `on_shutdown` lifecycle handlers
   - `_render_connect_status(ctx)` helper — loads boards if connected, passes to template

6. **Create `apps/monday-sync/frontend/templates/connect.html`** — API token input form with single field. Uses `hx-post="/app/monday-sync/_fragments/connect/credentials"`. Links to Monday.com API token page.

7. **Create `apps/monday-sync/frontend/templates/connect_status.html`** — Connected state showing username/email/masked token. Board selection checkboxes section. Sync config section (direction, interval). Sync Now button. Sync stats section. Disconnect button. All htmx URLs prefixed with `/app/monday-sync/`.

8. **Create `apps/monday-sync/frontend/static/styles.css`** — Scoped under `.monday-sync-settings`. Copy from `apps/jira-sync/frontend/static/styles.css` and adapt class prefix. Same visual patterns (connection badge, checkbox lists, form sections).

9. **Write `backend/tests/test_monday_auth.py`** — 20+ tests using importlib loading pattern from `backend/tests/test_jira_auth.py`. Cover: store_credentials, get_credentials (present / missing), clear_credentials, _mask_token (various lengths), get_connection_status (connected, disconnected, error on verify), verify_connection success/failure. Use MockStateClient and MockMondayClient async stubs.

## Must-Haves

- [ ] `apps/monday-sync/manifest.yaml` with correct appId, permissions, tasks, UI page, network domain
- [ ] `apps/monday-sync/services/auth.py` with store/get/clear/verify/status functions using single API token
- [ ] `apps/monday-sync/app.py` with connect/disconnect/board-save routes and task stubs
- [ ] Connect form template with single API token field
- [ ] Connect status template with board selection UI skeleton
- [ ] Scoped CSS under `.monday-sync-settings`
- [ ] 20+ auth tests passing via importlib loading pattern

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_monday_auth.py -v` — 20+ tests pass
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/app.py').read())"` — no syntax errors
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/auth.py').read())"` — no syntax errors
- All files under `apps/monday-sync/` exist and have valid syntax

## Observability Impact

- **New logger:** `monday_sync.auth` — logs INFO on credential store/clear/verify, WARNING on verify failures
- **New logger:** `monday_sync` — logs INFO on app start/stop, connect/disconnect, manual sync trigger; WARNING on render failures; ERROR on sync failures
- **Inspection surface:** `get_connection_status()` returns dict with `connected`, `display_name`, `email`, `token_preview`, `error` — drives the connect_status.html template
- **Redaction:** API tokens never logged raw; `_mask_token()` produces `first4+****+last4` for display; tokens ≤8 chars show only `first4+****`
- **Failure visibility:** Auth errors surface in the connection status dict `error` field; invalid credentials are cleared immediately after failed verification to prevent stale state

## Inputs

- `apps/jira-sync/` — reference implementation for app structure, auth pattern, templates, CSS
- `apps/linear-sync/` — reference for GraphQL-based auth (simpler single-token pattern)
- Knowledge: Monday.com auth uses `Authorization: <api_key>` header (no Bearer, no Basic)
- Knowledge: All htmx URLs in app templates must use `/app/{app_id}/` prefix per KNOWLEDGE.md

## Expected Output

- `apps/monday-sync/manifest.yaml` — complete app manifest
- `apps/monday-sync/requirements.txt` — dependencies file
- `apps/monday-sync/services/__init__.py` — empty package init
- `apps/monday-sync/services/auth.py` — auth helpers with 6 functions
- `apps/monday-sync/app.py` — route handlers and task stubs
- `apps/monday-sync/frontend/templates/connect.html` — API token input form
- `apps/monday-sync/frontend/templates/connect_status.html` — connected state with boards
- `apps/monday-sync/frontend/static/styles.css` — scoped CSS
- `backend/tests/test_monday_auth.py` — 20+ passing tests
