---
estimated_steps: 5
estimated_files: 3
---

# T03: Wire settings UI, sync routes, and poll-events task handler

**Slice:** S03 — Pull sync + field mapping + settings
**Milestone:** M018

## Description

Connect the sync engine (T02) to the user-facing settings UI and the platform's task scheduler. This task adds the Sync Configuration section (direction, poll interval), Manual Sync section (Sync Now button), and Sync Stats section to the existing connect_status.html template. It wires the `poll-events` task handler to call real `pull_sync()`, and adds the routes that save settings and trigger manual syncs.

Follow the linear-sync connect_status.html and app.py patterns exactly — the template structure, htmx URLs, form field names, and route handler shapes should mirror what linear-sync established.

**Knowledge rule:** All htmx URLs in app templates must use `/app/google-calendar/` prefix so requests route through the app proxy (see KNOWLEDGE.md: "App template htmx URLs must use proxy prefix").

## Steps

1. **Extend `apps/google-calendar/frontend/templates/connect_status.html`** — add three new sections after the existing Calendar Selection section and before the Disconnect section. Copy the structure directly from `apps/linear-sync/frontend/templates/connect_status.html`:

   a. **Sync Configuration section** — a form with `hx-post="/app/google-calendar/_fragments/settings/sync-config"` containing:
      - Direction fieldset with two radio buttons: "Pull only" (value `"pull-only"`, hint "Google Calendar → SemPKM") and "Bidirectional" (value `"bidirectional"`, hint "Google Calendar ↔ SemPKM"). Default to pull-only checked unless `sync_direction == 'bidirectional'`.
      - Poll Interval fieldset with a `<select>`: 5m/15m/30m/1h options, selected based on `poll_interval` template var.
      - Save Config button.

   b. **Manual Sync section** — a form with `hx-post="/app/google-calendar/_fragments/sync-now"` containing:
      - "Sync Now" button with htmx indicator "Syncing…".

   c. **Sync Stats section** — displays sync status data:
      - Last sync timestamp from `last_sync_at` var
      - Last Pull result group (status, created, updated, unchanged, errors count) from `last_pull_result` var
      - Last Push result group (status, pushed, skipped, errors count) from `last_push_result` var — this will show "No sync data yet" until S04 implements push
      - "No sync data yet" message when no sync has run

   Template variables needed (provided by `_render_connect_status`): `sync_direction`, `poll_interval`, `last_sync_at`, `last_pull_result`, `last_push_result` (in addition to existing vars).

2. **Add settings routes to `apps/google-calendar/app.py`**:

   a. `POST /_fragments/settings/sync-config` — read `sync_direction` and `poll_interval` from form, store via `ctx.state.set()`, re-render connect_status.
   b. `POST /_fragments/sync-now` — import and call `pull_sync(ctx)`, then if `sync_direction == "bidirectional"` also call push (skip for now — S04). Store result, re-render connect_status.

3. **Wire `poll-events` task handler** — replace the skeleton in `app.py` with a real implementation that:
   - Imports `pull_sync` from `services.sync_engine`
   - Calls `await pull_sync(ctx)`
   - If sync_direction is bidirectional, also calls push (placeholder for S04)
   - Returns the sync result dict

4. **Extend `_render_connect_status()`** in app.py to pass the new template variables:
   - `sync_direction` ← `await ctx.state.get("sync_direction") or "pull-only"`
   - `poll_interval` ← `await ctx.state.get("poll_interval") or "15m"`
   - `last_sync_at` ← `await ctx.state.get("last_sync_at")`
   - `last_pull_result` ← JSON-parsed from `await ctx.state.get("last_pull_result")`
   - `last_push_result` ← JSON-parsed from `await ctx.state.get("last_push_result")`

5. **Add styles to `apps/google-calendar/frontend/static/styles.css`** — copy the sync-config, sync-now, sync-stats CSS sections from `apps/linear-sync/frontend/static/styles.css` and adapt class names to use `gcal-` prefix where needed (or reuse the same class names since they're scoped to the app's template).

## Must-Haves

- [ ] Sync Configuration section with direction radios and poll interval dropdown
- [ ] Sync Now button triggers `pull_sync()` and re-renders with results
- [ ] Sync Stats section shows last sync time, pull results (created/updated/unchanged/errors)
- [ ] `poll-events` task handler calls real `pull_sync(ctx)`
- [ ] All htmx URLs use `/app/google-calendar/` prefix
- [ ] Template syntax valid (no Jinja2 parse errors)
- [ ] `push-changes` handler remains skeleton (S04 scope)

## Verification

- Jinja2 template syntax check: `cd backend && python3 -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('../apps/google-calendar/frontend/templates')); env.get_template('connect_status.html'); print('OK')"`
- All htmx URL prefix check: `grep -n 'hx-post\|hx-get\|hx-put\|hx-delete' apps/google-calendar/frontend/templates/connect_status.html` — every URL starts with `/app/google-calendar/`
- `cd backend && .venv/bin/python -m pytest -x` — full suite passes (no regressions from route/handler changes)

## Inputs

- `apps/google-calendar/services/sync_engine.py` — T02 output (pull_sync function)
- `apps/google-calendar/app.py` — S02 output (existing routes, _render_connect_status, _make_client_with_creds)
- `apps/google-calendar/frontend/templates/connect_status.html` — S02 output (existing calendar list + disconnect)
- `apps/linear-sync/frontend/templates/connect_status.html` — reference for sync config/stats template structure
- `apps/linear-sync/app.py` — reference for sync-config, sync-now route handlers
- `apps/linear-sync/frontend/static/styles.css` — reference for sync section CSS

## Observability Impact

- **Sync stats UI:** The Sync Stats section surfaces `last_sync_at`, `last_pull_result` (status/created/updated/unchanged/errors), and `last_push_result` directly in the settings page — a future agent or user can inspect sync health visually without touching logs.
- **State keys:** `sync_direction`, `poll_interval`, `last_sync_at`, `last_pull_result`, `last_push_result` are all persisted in app state and can be queried via `ctx.state.get()` for debugging.
- **poll-events handler:** Now calls real `pull_sync(ctx)` — the `google_calendar.sync` logger emits INFO for per-calendar stats and WARNING for per-event failures. The task handler returns the full sync result dict, which the scheduler can log.
- **Failure visibility:** Manual Sync catches and persists error results; the UI shows error status and count. The poll-events handler logs and returns errors without crashing.

## Expected Output

- `apps/google-calendar/frontend/templates/connect_status.html` — extended with sync config, sync now, sync stats sections
- `apps/google-calendar/app.py` — sync-config route, sync-now route, real poll-events handler, extended _render_connect_status
- `apps/google-calendar/frontend/static/styles.css` — extended with sync section styles
