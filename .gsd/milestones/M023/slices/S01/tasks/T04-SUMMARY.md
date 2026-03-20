---
id: T04
parent: S01
milestone: M023
provides:
  - "Jira Sync installable app scaffold: manifest.yaml, 6 route handlers, connect/status templates, scoped CSS"
  - "Route handlers: connect (GET), credentials (POST), disconnect (POST), projects (POST), sync-config (POST), sync-now (POST)"
  - "Task handler stubs: poll-tasks, push-changes (placeholder for S02/S03)"
key_files:
  - apps/jira-sync/manifest.yaml
  - apps/jira-sync/app.py
  - apps/jira-sync/requirements.txt
  - apps/jira-sync/frontend/templates/connect.html
  - apps/jira-sync/frontend/templates/connect_status.html
  - apps/jira-sync/frontend/static/styles.css
key_decisions:
  - "JQL filter field included as persistent UI+settings but not consumed by routes until S02"
  - "site_url auto-prepends https:// if no protocol given, matching Jira Cloud-only target"
  - "Sync Now route is a placeholder re-render (no error message) — S02 wires real sync"
patterns_established:
  - "Jira app scaffold mirrors github-sync structure: same route prefix pattern, template naming, CSS scoping"
  - "All htmx URLs use /app/jira-sync/ proxy prefix per KNOWLEDGE.md constraint"
  - "connect_status.html uses project.key (not full_name) for checkbox values — matches Jira project model"
observability_surfaces:
  - "jira_sync logger: INFO on connect/disconnect, credential verify, project/config save, lifecycle"
  - "get_connection_status() returns diagnostic dict with masked token, site_url, error field"
  - "Task stubs return {status: skipped, message: ...} for platform task runner visibility"
duration: "15min"
verification_result: passed
completed_at: "2026-03-19"
blocker_discovered: false
---

# T04: Wire app scaffold with manifest, routes, templates, and CSS

**Wired Jira Sync app scaffold with manifest.yaml, 6 route handlers, email+token+site_url connect form, project selection/JQL/sync-config templates, and scoped CSS — all htmx URLs use /app/jira-sync/ proxy prefix.**

## What Happened

Created 6 files following the exact github-sync app structure. The manifest defines the app with `ticket` icon, `*.atlassian.net` network permission, two background tasks, and a settings UI page. The app module (`app.py`) provides 6 route handlers — connect fragment, credential auth, disconnect, project selection, sync config, and sync-now placeholder — plus two task handler stubs that return `skipped` status until S02/S03 wire real sync engines.

The connect form (`connect.html`) has three fields (email, API token, site URL) instead of github-sync's single PAT field, with a link to Atlassian's token management page. The connected status page (`connect_status.html`) shows project selection checkboxes (using `project.key` values), a JQL filter text input, sync direction radios, poll interval dropdown, sync stats section, and disconnect button.

CSS is scoped under `.jira-sync-settings` with additional styles for site_url display, JQL filter input, and project key/name columns.

## Verification

- manifest.yaml: valid YAML, correct appId/permissions/tasks/UI page
- app.py: valid Python AST, 6 routes, correct service imports
- Templates: 5 htmx attributes across 2 templates, all 5 use `/app/jira-sync/` proxy prefix (100% match)
- CSS: scoped under `.jira-sync-settings` class
- All 237 slice tests pass (95 ADF + 74 field mapper + 68 client/auth/person)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import yaml; yaml.safe_load(open('apps/jira-sync/manifest.yaml'))"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/jira-sync/app.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `grep -c 'hx-post=\|hx-get=' apps/jira-sync/frontend/templates/*.html` (5 total) | 0 | ✅ pass | <1s |
| 4 | `grep '/app/jira-sync/' templates/*.html \| wc -l` (5 lines, matches htmx count) | 0 | ✅ pass | <1s |
| 5 | `grep 'jira-sync-settings' apps/jira-sync/frontend/static/styles.css \| head -1` | 0 | ✅ pass | <1s |
| 6 | `pytest tests/test_jira_adf_converter.py ... test_jira_person_matcher.py -q` (237 passed) | 0 | ✅ pass | 0.18s |

## Diagnostics

- **Connection state:** Call `get_connection_status(state_client, jira_client)` to inspect auth state — returns `connected`, `email`, `display_name`, `token_preview` (masked), `site_url`, optional `error`.
- **Route logging:** All route handlers log at INFO level to `jira_sync` logger. Credential failures log at WARNING.
- **Settings inspection:** Sync config stored as: `selected_projects` (JSON list of keys), `sync_direction`, `poll_interval`, `jql_filter` — all readable via `ctx.settings.get()`.
- **Task stubs:** `poll-tasks` and `push-changes` return `{"status": "skipped", "message": "..."}` — platform task runner logs these.

## Deviations

- JQL filter input uses `form="sync-config-form"` attribute to associate with the sync config form, rather than being in a separate standalone form. This keeps the JQL filter value submitted alongside sync direction and poll interval in a single POST.

## Known Issues

None.

## Files Created/Modified

- `apps/jira-sync/manifest.yaml` — App manifest with appId, permissions, tasks, UI page
- `apps/jira-sync/app.py` — 6 route handlers + 2 task stubs + lifecycle hooks (~210 lines)
- `apps/jira-sync/requirements.txt` — SDK-only comment (no extra deps)
- `apps/jira-sync/frontend/templates/connect.html` — Auth form with email + token + site_url
- `apps/jira-sync/frontend/templates/connect_status.html` — Connected state with project list, JQL, sync config, stats
- `apps/jira-sync/frontend/static/styles.css` — Scoped CSS under .jira-sync-settings (~310 lines)
- `.gsd/milestones/M023/slices/S01/tasks/T04-PLAN.md` — Added Observability Impact section
