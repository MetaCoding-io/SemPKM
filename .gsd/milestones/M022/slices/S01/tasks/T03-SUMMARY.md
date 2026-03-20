---
id: T03
parent: S01
milestone: M022
provides:
  - Asana Sync app shell with manifest, OAuth/PAT route handlers, project selection, and frontend templates
key_files:
  - apps/asana-sync/manifest.yaml
  - apps/asana-sync/app.py
  - apps/asana-sync/requirements.txt
  - apps/asana-sync/frontend/templates/connect.html
  - apps/asana-sync/frontend/templates/connect_status.html
  - apps/asana-sync/frontend/static/styles.css
key_decisions:
  - OAuth callback result page auto-redirects to /browser/ after 2s on success, matching Google Calendar pattern
  - Workspace/project data fetched eagerly in _render_connect_status — errors caught gracefully so status page still renders without project data
patterns_established:
  - Dual-auth connect template pattern (OAuth credentials section → "then" divider → OAuth connect button → "or" divider → PAT section) reused from Google Calendar/Linear Sync
  - Workspace-grouped project checkboxes in connect_status.html — each workspace is a heading with its projects indented below
observability_surfaces:
  - Logger asana.sync.app covers all route handler events (credential save, OAuth redirect, callback, PAT verify, disconnect, project selection)
  - get_connection_status(ctx.state) returns {connected, auth_method, asana_email, token_expiry}
  - selected_projects key in StateClient stores JSON array of project GIDs
  - _oauth_result_page renders success/error directly in browser; errors also logged at WARNING level
duration: 25m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: App shell with manifest, OAuth/PAT routes, project selection, and connect templates

**Built Asana Sync app shell with manifest, 8 route handlers (OAuth credentials/redirect/callback, PAT, disconnect, project selection), dual-auth connect template, workspace-grouped project selection UI, and scoped CSS — wiring T01 auth module and T02 client into the App Platform.**

## What Happened

Created the full Asana Sync app shell following the Google Calendar and Linear Sync patterns:

1. **manifest.yaml** — appId "asana-sync", network permission for app.asana.com, commands (object.create/patch, body.set, edge.create), SPARQL read, background tasks, two scheduled tasks (poll-tasks, push-changes at 15m intervals), UI page with check-square icon in apps nav.

2. **app.py** (~300 lines) — 8 routes covering the complete auth and project selection flow:
   - `/_fragments/connect` GET — renders connect form or status based on connection state
   - `/_fragments/connect/credentials` POST — saves OAuth client_id/secret
   - `/_fragments/connect/asana` POST — generates CSRF state, builds authorize URL, redirects to Asana
   - `/_fragments/oauth-callback` GET — verifies CSRF state, exchanges code, fetches user identity, stores tokens
   - `/_fragments/connect/pat` POST — verifies PAT via /users/me, stores with auth_method="pat"
   - `/_fragments/connect/disconnect` POST — clears auth state and selected projects
   - `/_fragments/settings/projects` POST — saves selected project GIDs as JSON
   - Skeleton task handlers for poll-tasks and push-changes returning `{"status": "not_configured"}`

3. **connect.html** — Three-section layout: OAuth credentials form, "then" → OAuth connect button (disabled until credentials saved), "or" → PAT entry form. All htmx URLs prefixed with `/app/asana-sync/`.

4. **connect_status.html** — Connection badge with auth method, user email, workspace-grouped project checkboxes, field mapping placeholder section for T04, disconnect button.

5. **styles.css** — Scoped under `.asana-sync-settings`, cloned from Linear Sync with additions for workspace headings, project checkbox lists, redirect URI code blocks, and dashed-border field mapping placeholder.

6. **requirements.txt** — markdownify dependency for S02's HTML→Markdown conversion.

## Verification

- All 9 required files exist at expected paths
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` — syntax valid
- `python3 -c "import yaml; yaml.safe_load(open('apps/asana-sync/manifest.yaml'))"` — YAML valid
- All htmx URLs in templates use `/app/asana-sync/` prefix (6 total, 0 missing prefix)
- manifest.yaml appId is "asana-sync"
- 30 auth tests pass, 28 client tests pass (slice-level checks)
- connect_status.html has project selection checkboxes grouped by workspace (T04 will add field mapping sections)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `ls apps/asana-sync/{manifest.yaml,app.py,...}` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import yaml; yaml.safe_load(open('apps/asana-sync/manifest.yaml'))"` | 0 | ✅ pass | <1s |
| 4 | `grep '/app/asana-sync/' ...connect.html ...connect_status.html` — 4+2 matches | 0 | ✅ pass | <1s |
| 5 | `grep 'hx-post\|hx-get' ... \| grep -v '/app/asana-sync/'` — no unmatched | 0 | ✅ pass | <1s |
| 6 | `grep 'appId' apps/asana-sync/manifest.yaml` — shows "asana-sync" | 0 | ✅ pass | <1s |
| 7 | `pytest backend/tests/test_asana_auth.py -v --noconftest` — 30 passed | 0 | ✅ pass | 0.05s |
| 8 | `pytest backend/tests/test_asana_client.py -v --noconftest` — 28 passed | 0 | ✅ pass | 0.04s |

## Diagnostics

- **App logger:** `grep "asana.sync.app"` in container logs covers credential saves, OAuth redirects, callbacks, PAT verification, disconnect, and project selection events
- **Auth logger:** `grep "asana.sync.auth"` covers token exchange, refresh, PAT verification details
- **Client logger:** `grep "asana.sync.client"` covers API errors and token refresh events
- **Connection state:** `get_connection_status(ctx.state)` returns `{connected, auth_method, asana_email, token_expiry}`
- **Project selection:** `ctx.state.get("selected_projects")` returns JSON array of project GIDs
- **OAuth errors:** `AsanaAuthError` includes `.status_code` and `.response_body`; callback errors rendered in browser and logged at WARNING

## Deviations

None.

## Known Issues

- connect_status.html field mapping section is a placeholder — T04 will add status/priority/story-points mapping UI
- Skeleton task handlers return `{"status": "not_configured"}` — S02/S03 will implement actual sync logic
- Slice verification check "connect_status.html has status source radio buttons, status mapping table, priority mapping table, story points field selector" will not pass until T04 completes — this is expected for an intermediate task

## Files Created/Modified

- `apps/asana-sync/manifest.yaml` — App manifest with permissions, tasks, UI config
- `apps/asana-sync/requirements.txt` — markdownify dependency
- `apps/asana-sync/app.py` — Route handlers for OAuth, PAT, project selection, disconnect
- `apps/asana-sync/frontend/templates/connect.html` — Dual-auth connect form (OAuth + PAT)
- `apps/asana-sync/frontend/templates/connect_status.html` — Connection status + workspace-grouped project checkboxes
- `apps/asana-sync/frontend/static/styles.css` — Scoped CSS for asana-sync UI
- `.gsd/milestones/M022/slices/S01/tasks/T03-PLAN.md` — Added Observability Impact section
