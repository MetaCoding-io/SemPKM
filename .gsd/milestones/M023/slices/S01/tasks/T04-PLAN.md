---
estimated_steps: 7
estimated_files: 7
---

# T04: Wire app scaffold with manifest, routes, templates, and CSS

**Slice:** S01 — ADF converter + field mapper + Jira client + auth scaffold
**Milestone:** M023

## Description

Wire all service modules from T01-T03 into an installable Jira Sync app with manifest, route handlers, HTML templates, and scoped CSS. This follows the exact structure of `apps/github-sync/` — same route patterns, template naming, and CSS approach. The Jira-specific differences are: (1) auth requires email + token + site_url (not just token), (2) project list comes from `get_projects()` instead of repo fetch, (3) settings will later include a JQL filter field (prepared here as placeholder).

**Key constraint from KNOWLEDGE.md:** All htmx URLs in app templates must use `/app/jira-sync/` proxy prefix so requests route through the `app_proxy_router`.

## Steps

1. Create `apps/jira-sync/manifest.yaml`:
   ```yaml
   appId: "jira-sync"
   name: "Jira Sync"
   version: "0.1.0"
   description: "Two-way sync between SemPKM objects and Jira issues"
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
       - "body.diff"
       - "edge.create"
     sparql:
       read: true
     backgroundTasks: true
     network:
       - "*.atlassian.net"
   backend:
     entrypoint: "app:jira_sync_app"
   tasks:
     - id: "poll-tasks"
       description: "Poll Jira for updated issues and sync to SemPKM"
       interval: "15m"
       retryPolicy:
         maxRetries: 3
         maxBackoff: "60s"
     - id: "push-changes"
       description: "Push local task changes back to Jira"
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
         label: "Jira Sync"
         icon: "ticket"
         nav: "apps"
         fragment: "connect"
   ```

2. Create `apps/jira-sync/app.py`:
   - Import App, AppContext from sempkm_app_sdk
   - Import services: auth (store_credentials, get_credentials, get_connection_status, clear_credentials), jira_client (JiraClient, JiraAuthError, JiraAPIError)
   - `jira_sync_app = App("jira-sync")`
   - `_make_client(ctx) -> JiraClient` helper
   - Route `/_fragments/connect` GET: check connection status, render connect.html (disconnected) or connect_status.html (connected with projects list)
   - Route `/_fragments/connect/credentials` POST: read email, token, site_url from form, store via auth.store_credentials, verify via client.get_myself(), render connect_status.html on success or connect.html with error on failure
   - Route `/_fragments/connect/disconnect` POST: clear credentials, render connect.html
   - Route `/_fragments/settings/projects` POST: save selected project keys as JSON in settings
   - Route `/_fragments/settings/sync-config` POST: save sync_direction and poll_interval
   - Route `/_fragments/settings/sync-now` POST: placeholder — renders connect_status with "Sync not yet implemented" message (S02 will wire real sync)
   - `_render_connect_status(ctx)` helper: fetch projects, read settings (selected_projects, sync_direction, poll_interval, jql_filter, last_sync_at, last_pull_result, last_push_result), render connect_status.html
   - Task handlers `poll-tasks` and `push-changes`: placeholder stubs logging "not yet implemented" (S02/S03 will wire real sync)
   - on_startup/on_shutdown lifecycle hooks with logging
   - **Critical:** All htmx URLs in route handlers that generate HTML must use `/app/jira-sync/` prefix

3. Create `apps/jira-sync/requirements.txt`:
   ```
   # SDK is injected by the platform — httpx available via SDK.
   # No additional dependencies.
   ```

4. Create `apps/jira-sync/frontend/templates/connect.html`:
   - Scoped wrapper `<div id="connect-content" class="jira-sync-settings">`
   - Title "Connect to Jira Cloud"
   - Description text about linking Jira account
   - Error alert (conditional on `error` var)
   - Form section with 3 fields:
     - Email input (text, `name="email"`, placeholder "you@company.com")
     - API Token input (password, `name="token"`, placeholder, link to `https://id.atlassian.com/manage-profile/security/api-tokens`)
     - Site URL input (text, `name="site_url"`, placeholder "mycompany.atlassian.net", hint about Cloud-only)
   - Form action: `hx-post="/app/jira-sync/_fragments/connect/credentials"` hx-target="#connect-content" hx-swap="innerHTML"
   - Connect button with loading indicator

5. Create `apps/jira-sync/frontend/templates/connect_status.html`:
   - Connected badge, email display, masked token, site URL
   - Project selection section: checkboxes for each project with key + name, `hx-post="/app/jira-sync/_fragments/settings/projects"`
   - JQL filter text input (placeholder "e.g., project = PROJ AND issuetype != Epic", saved via settings — this is just UI, S02 uses it)
   - Sync configuration: direction radios (pull-only / bidirectional), poll interval dropdown (5m/15m/30m/1h)
   - Sync Now button: `hx-post="/app/jira-sync/_fragments/settings/sync-now"`
   - Sync stats section (last sync time, pull result, push result) — follows github-sync pattern exactly
   - Disconnect button with confirmation: `hx-post="/app/jira-sync/_fragments/connect/disconnect"`

6. Create `apps/jira-sync/frontend/static/styles.css`:
   - Clone from `apps/github-sync/frontend/static/styles.css`
   - Change root scope class from `.github-sync-settings` to `.jira-sync-settings`
   - Add styles for site_url input field
   - Add styles for JQL filter input
   - Keep all shared styles (buttons, connection status, repo/project checkboxes, sync config, sync stats, alerts, disconnect)

7. Verify all files: manifest YAML valid, app.py parses, templates have correct htmx URLs

## Must-Haves

- [ ] manifest.yaml has correct appId, permissions, tasks, and UI page
- [ ] app.py has all 6 routes with `/app/jira-sync/` proxy prefix in htmx URLs
- [ ] connect.html has email + token + site_url form fields
- [ ] connect_status.html has project selection, JQL filter, sync config, sync stats sections
- [ ] styles.css scoped under `.jira-sync-settings`
- [ ] requirements.txt present
- [ ] All service imports in app.py reference correct module paths

## Verification

- `python -c "import yaml; yaml.safe_load(open('apps/jira-sync/manifest.yaml'))"` — valid YAML
- `python -c "import ast; ast.parse(open('apps/jira-sync/app.py').read())"` — valid Python
- `grep -c 'hx-post=\|hx-get=' apps/jira-sync/frontend/templates/*.html` — all htmx URLs present
- `grep '/app/jira-sync/' apps/jira-sync/frontend/templates/*.html | wc -l` — every htmx URL uses proxy prefix (should match total htmx attribute count)
- `grep 'jira-sync-settings' apps/jira-sync/frontend/static/styles.css | head -1` — scoped CSS class present

## Inputs

- `apps/jira-sync/services/auth.py` — from T03 (store_credentials, get_connection_status, etc.)
- `apps/jira-sync/services/jira_client.py` — from T03 (JiraClient, error classes)
- `apps/jira-sync/services/adf_converter.py` — from T01 (imported but not used in routes until S02)
- `apps/jira-sync/services/field_mapper.py` — from T02 (imported but not used in routes until S02)
- `apps/jira-sync/services/person_matcher.py` — from T03 (imported but not used in routes until S02)
- `apps/github-sync/manifest.yaml` — reference manifest structure
- `apps/github-sync/app.py` — reference route pattern
- `apps/github-sync/frontend/templates/connect.html` — reference template (adapt for email+token+site_url)
- `apps/github-sync/frontend/templates/connect_status.html` — reference template (adapt project list for Jira)
- `apps/github-sync/frontend/static/styles.css` — clone and rebrand
- KNOWLEDGE.md: "App template htmx URLs must use proxy prefix" — all hx-post/hx-get must use `/app/jira-sync/` prefix

## Observability Impact

- **Structured logging:** `logger.getLogger("jira_sync")` emits INFO on connect/disconnect, credential verification, project save, sync config save, manual sync trigger, and app lifecycle (startup/shutdown). WARNING on failed project fetch, failed status render, failed credential verification.
- **Connection status:** `get_connection_status(state, client)` returns a dict with `connected`, `email`, `display_name`, `token_preview` (masked), `site_url`, and optional `error` — the primary diagnostic surface for auth issues.
- **Settings state:** All sync config (selected_projects, sync_direction, poll_interval, jql_filter) is persisted via `ctx.settings` and readable via the SDK state API.
- **Sync state:** `last_sync_at`, `last_pull_result`, `last_push_result` are persisted in `ctx.state` and displayed in the sync stats UI section.
- **Task handler stubs:** `poll-tasks` and `push-changes` return `{"status": "skipped", "message": "..."}` — the platform task runner will log these as skipped runs until S02/S03 wire real sync.
- **HX-Trigger header:** On successful connect, response includes `HX-Trigger: jiraConnected` for frontend event handling.
- **Failure visibility:** JiraAuthError and JiraAPIError exceptions surface as user-facing error messages in the connect form. Invalid credentials are cleared immediately on failed verification.

## Expected Output

- `apps/jira-sync/manifest.yaml` — complete app manifest
- `apps/jira-sync/app.py` — ~200-line route handler module
- `apps/jira-sync/requirements.txt` — SDK-only comment
- `apps/jira-sync/frontend/templates/connect.html` — auth form with email+token+site_url
- `apps/jira-sync/frontend/templates/connect_status.html` — connected state with project selection, JQL filter, sync config
- `apps/jira-sync/frontend/static/styles.css` — scoped CSS (~250 lines)
