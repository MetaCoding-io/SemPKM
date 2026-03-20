---
estimated_steps: 8
estimated_files: 7
---

# T03: App shell with manifest, OAuth/PAT routes, project selection, and connect templates

**Slice:** S01 — OAuth + project selection + custom field mapping UI
**Milestone:** M022

## Description

Wire the T01 auth module and T02 client into the App Platform as a running app. Create the manifest, app.py with route handlers, and frontend templates. This task proves the OAuth redirect flow, PAT entry, workspace/project selection with persistence, and disconnect.

The connect.html template handles the initial authentication (OAuth credentials + PAT entry). The connect_status.html template shows connection status and project selection — T04 will extend it with the field mapping UI sections.

All htmx URLs must use the `/app/asana-sync/` prefix per KNOWLEDGE.md ("App template htmx URLs must use proxy prefix").

## Steps

1. Create `apps/asana-sync/manifest.yaml`:
   ```yaml
   appId: "asana-sync"
   name: "Asana Sync"
   version: "0.1.0"
   description: "Sync Asana tasks with SemPKM objects"
   author:
     name: "SemPKM"
   license: "MIT"
   dependencies:
     platform: ">=0.1.0"
   permissions:
     commands:
       - "object.create"
       - "object.patch"
       - "body.set"
       - "edge.create"
     sparql:
       read: true
     backgroundTasks: true
     network:
       - "app.asana.com"
   backend:
     entrypoint: "app:asana_sync_app"
   tasks:
     - id: "poll-tasks"
       description: "Poll Asana for updated tasks and sync to SemPKM"
       interval: "15m"
       retryPolicy:
         maxRetries: 3
         maxBackoff: "60s"
     - id: "push-changes"
       description: "Push local changes back to Asana"
       interval: "15m"
       retryPolicy:
         maxRetries: 3
         maxBackoff: "60s"
   frontend:
     staticDir: "frontend/static"
     css:
       - "styles.css"
   ui:
     pages:
       - id: "settings"
         path: "/settings"
         label: "Asana"
         icon: "check-square"
         nav: "apps"
         fragment: "connect"
   ```

2. Create `apps/asana-sync/requirements.txt` with `markdownify` (needed for S02 HTML→Markdown on task notes).

3. Create `apps/asana-sync/app.py` with route handlers. Follow the Google Calendar app.py structure:
   - Import from `services.auth` and `services.asana_client`.
   - `REDIRECT_URI = "http://localhost:3000/app/asana-sync/_fragments/oauth-callback"`
   - `asana_sync_app = App("asana-sync")`
   - Helper: `_make_client(ctx)` → `AsanaClient(ctx.http, ctx.state)`.
   - Helper: `_make_client_with_creds(ctx)` → `AsanaClient(ctx.http, ctx.state, client_id, client_secret)`.
   - Helper: `_render_connect_status(ctx)` → renders connect_status.html with connection status, workspace/project data, selected projects, and (placeholder for T04) field mapping config.
   - Route `/_fragments/connect` (GET) — if connected, render connect_status.html via `_render_connect_status()`; else render connect.html.
   - Route `/_fragments/connect/credentials` (POST) — save OAuth client_id/client_secret via StateClient. Re-render connect.html with success message.
   - Route `/_fragments/connect/asana` (POST) — generate CSRF state, build authorize URL via `build_asana_authorize_url()`, return RedirectResponse.
   - Route `/_fragments/oauth-callback` (GET) — verify CSRF state, exchange code via `exchange_code()`, fetch user identity via `client.get_user_me()`, store tokens via `store_auth_tokens()`, render success/error HTML page.
   - Route `/_fragments/connect/pat` (POST) — read `api_key` from form, verify via `verify_pat()`, store as access_token with auth_method="pat", render connect_status.
   - Route `/_fragments/connect/disconnect` (POST) — clear auth state, clear selected_projects, render connect.html.
   - Route `/_fragments/settings/projects` (POST) — save selected project GIDs as JSON via StateClient, re-render connect_status.
   - Skeleton task handlers: `@asana_sync_app.task("poll-tasks")` and `@asana_sync_app.task("push-changes")` — stub implementations that log and return `{"status": "not_configured"}`.
   - Startup/shutdown handlers with logging.

4. Create `apps/asana-sync/frontend/templates/connect.html`:
   - Two-section layout matching `apps/google-calendar/frontend/templates/connect.html`:
     - Section 1: "Asana OAuth Credentials" — client_id text input, client_secret password input, Save button. POST to `/app/asana-sync/_fragments/connect/credentials`.
     - Divider with "then"
     - Section 2: "Connect with Asana" — button POST to `/app/asana-sync/_fragments/connect/asana`. Disabled if no credentials saved.
     - Divider with "or"
     - Section 3: "Personal Access Token" — api_key password input with placeholder "0/...", Connect button. POST to `/app/asana-sync/_fragments/connect/pat`.
   - Error/success alert divs.
   - CSS class: `asana-sync-settings`.

5. Create `apps/asana-sync/frontend/templates/connect_status.html`:
   - Connection status badge (Connected ●) with auth method badge.
   - User email display.
   - **Workspace/Project Selection section**: For each workspace, show workspace name as heading with project checkboxes below. Form POSTs to `/app/asana-sync/_fragments/settings/projects`. Pre-check already-selected projects. Save button.
   - Placeholder section for field mapping (T04 will add).
   - Disconnect button.
   - CSS class: `asana-sync-settings`.

6. Create `apps/asana-sync/frontend/static/styles.css`:
   - Clone from `apps/linear-sync/frontend/static/styles.css`, replace `.linear-sync-settings` with `.asana-sync-settings`.
   - Add styles for workspace-project grouping (workspace headings, indented project checkboxes).

7. Verify files exist and are syntactically valid:
   - `python -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"`
   - `python -c "import yaml; yaml.safe_load(open('apps/asana-sync/manifest.yaml'))"` (or just check YAML structure manually)
   - All template files exist at expected paths.

8. Commit: `feat(asana-sync): add app shell with manifest, OAuth/PAT routes, project selection`

## Must-Haves

- [ ] manifest.yaml with appId "asana-sync", correct network/command permissions, tasks, UI config
- [ ] app.py with OAuth redirect flow, PAT auth, project selection, disconnect
- [ ] connect.html with OAuth credentials + PAT dual-auth layout
- [ ] connect_status.html with project selection checkboxes grouped by workspace
- [ ] All htmx URLs prefixed with `/app/asana-sync/`
- [ ] styles.css with asana-sync-settings class
- [ ] requirements.txt with markdownify
- [ ] CSRF state verification on OAuth callback
- [ ] Skeleton task handlers for poll-tasks and push-changes

## Verification

- `ls apps/asana-sync/manifest.yaml apps/asana-sync/app.py apps/asana-sync/requirements.txt apps/asana-sync/services/__init__.py apps/asana-sync/services/auth.py apps/asana-sync/services/asana_client.py apps/asana-sync/frontend/templates/connect.html apps/asana-sync/frontend/templates/connect_status.html apps/asana-sync/frontend/static/styles.css` — all exist
- `python -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` — no syntax errors
- `grep -c '/app/asana-sync/' apps/asana-sync/frontend/templates/connect.html apps/asana-sync/frontend/templates/connect_status.html` — all htmx URLs use app prefix
- `grep 'appId' apps/asana-sync/manifest.yaml` — shows "asana-sync"

## Inputs

- `apps/asana-sync/services/auth.py` (from T01) — OAuth helpers (build URL, exchange code, store tokens, etc.)
- `apps/asana-sync/services/asana_client.py` (from T02) — REST client (get_workspaces, get_projects, get_user_me, etc.)
- `apps/google-calendar/app.py` — OAuth route handler pattern to follow
- `apps/google-calendar/manifest.yaml` — manifest structure pattern
- `apps/linear-sync/frontend/templates/connect.html` — dual-auth template pattern (OAuth + API key)
- `apps/linear-sync/frontend/templates/connect_status.html` — status page template pattern
- `apps/linear-sync/frontend/static/styles.css` — CSS pattern to clone

## Observability Impact

- **Logger `asana.sync.app`**: All route handlers log auth events (OAuth redirect, callback success/error, PAT verify, disconnect, project selection save). Grep for `asana.sync.app` in container logs.
- **Connection status**: `get_connection_status(ctx.state)` returns `{connected, auth_method, asana_email, token_expiry}` — inspectable from any route handler or task.
- **OAuth errors**: The `_oauth_result_page` renders success/error in the browser; error details also logged at WARNING level.
- **CSRF state**: `oauth_state` key in StateClient — cleared after successful exchange. Mismatch logged at WARNING.
- **Project selection**: `selected_projects` key in StateClient stores JSON array of project GIDs.

## Expected Output

- `apps/asana-sync/manifest.yaml` — complete manifest with correct appId, permissions, tasks, UI
- `apps/asana-sync/requirements.txt` — markdownify dependency
- `apps/asana-sync/app.py` — route handlers for OAuth flow, PAT auth, project selection, disconnect (~300 lines)
- `apps/asana-sync/frontend/templates/connect.html` — dual-auth connect form
- `apps/asana-sync/frontend/templates/connect_status.html` — connection status + project selection (field mapping placeholder for T04)
- `apps/asana-sync/frontend/static/styles.css` — styles for asana-sync UI
