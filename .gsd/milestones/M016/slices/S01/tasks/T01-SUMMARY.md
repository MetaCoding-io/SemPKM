---
id: T01
parent: S01
milestone: M016
provides:
  - Installable Linear Sync app skeleton with manifest, entrypoint, templates, and CSS
  - Placeholder routes for connect, API key auth, OAuth callback, and disconnect
key_files:
  - apps/linear-sync/manifest.yaml
  - apps/linear-sync/app.py
  - apps/linear-sync/requirements.txt
  - apps/linear-sync/services/__init__.py
  - apps/linear-sync/frontend/templates/connect.html
  - apps/linear-sync/frontend/templates/connect_status.html
  - apps/linear-sync/frontend/static/styles.css
key_decisions:
  - Scoped all CSS under `.linear-sync-settings` class to avoid conflicts with workspace styles
  - Used `password` input type for API key field to avoid accidental exposure
  - Registered all four fragment routes (connect, api-key, oauth-callback, disconnect) as 501 placeholders — T03 will implement real logic
patterns_established:
  - App route pattern: `/_fragments/connect` for settings page, `/_fragments/connect/{action}` for sub-actions
  - Two-template pattern: connect.html (disconnected state) and connect_status.html (connected state), swapped via htmx
observability_surfaces:
  - Lifecycle logging via `logging.getLogger("linear_sync")` at INFO level for startup/shutdown
  - Poll-tasks handler logs execution at INFO level (returns noop until sync is implemented)
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: App manifest, skeleton, and settings page shell

**Created Linear Sync app skeleton with manifest, Python entrypoint, placeholder routes, settings page templates, and scoped CSS — ready for install via App Platform.**

## What Happened

Created all 7 files for the linear-sync app following the test-app patterns exactly. The manifest declares all permissions needed by downstream slices (object.create, object.patch, body.set, body.diff, edge.create, sparql read, backgroundTasks, network access to api.linear.app and linear.app). The app.py exports `linear_sync_app` matching the manifest entrypoint and registers four fragment routes (connect GET, api-key POST, oauth-callback GET, disconnect POST) plus a poll-tasks background task and startup/shutdown lifecycle hooks. The connect.html template provides a two-section auth form (API key input + OAuth button) with htmx attributes for dynamic swapping. The connect_status.html template shows connected state with workspace info and team list (Jinja loop). CSS is fully scoped under `.linear-sync-settings`.

## Verification

- Manifest parses as valid YAML — confirmed
- All 5 required permission types present in manifest.commands
- `app.py` compiles via `ast.parse` — confirmed
- `linear_sync_app` is a top-level module assignment — confirmed
- All 4 route paths registered in source — confirmed
- Template syntax balanced (Jinja braces and HTML tags) — confirmed
- All 7 files exist at expected paths — confirmed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import yaml; yaml.safe_load(open('apps/linear-sync/manifest.yaml')); print('manifest OK')"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read()); print('app.py OK')"` | 0 | ✅ pass | <1s |
| 3 | Template Jinja/HTML balance check (custom script) | 0 | ✅ pass | <1s |
| 4 | All 7 files exist check | 0 | ✅ pass | <1s |
| 5 | Manifest permissions deep check (all 5 commands, sparql, network, entrypoint, task, ui page) | 0 | ✅ pass | <1s |
| 6 | app.py route registration check (4 routes + module-level export) | 0 | ✅ pass | <1s |

### Slice-Level Verification (Partial)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | `cd backend && python -m pytest tests/test_linear_client.py -v` | ⏳ not yet | Test file created in T02 |
| 2 | App installs successfully in Docker stack | ⏳ not yet | Requires running stack; can test after T03 |
| 3 | Settings page loads at `/_fragments/connect` | ⏳ not yet | Route registered but needs running app to test |

## Diagnostics

- **Lifecycle logs:** `docker compose logs api | grep linear_sync` — should show startup/shutdown messages once installed
- **Route availability:** `curl http://localhost:8000/app/linear-sync/_fragments/connect` once the Docker stack is running with the app installed
- **Manifest inspection:** `python3 -c "import yaml; print(yaml.safe_load(open('apps/linear-sync/manifest.yaml')))"` for quick manifest review

## Deviations

None — followed the task plan exactly.

## Known Issues

- Jinja2 template parsing could not be verified via `jinja2` import (not installed in system Python). Verified via custom balanced-brace and HTML tag check instead. Full Jinja2 parsing will be confirmed when the app runs in Docker.

## Files Created/Modified

- `apps/linear-sync/manifest.yaml` — App manifest with full permissions, task, and UI page config
- `apps/linear-sync/app.py` — App entrypoint with placeholder routes and lifecycle hooks
- `apps/linear-sync/requirements.txt` — Empty dependency file (SDK provides httpx)
- `apps/linear-sync/services/__init__.py` — Empty package init for services module
- `apps/linear-sync/frontend/templates/connect.html` — Disconnected state: API key form + OAuth button
- `apps/linear-sync/frontend/templates/connect_status.html` — Connected state: status badge, teams table, disconnect
- `apps/linear-sync/frontend/static/styles.css` — Scoped CSS for settings page components
- `.gsd/milestones/M016/slices/S01/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
