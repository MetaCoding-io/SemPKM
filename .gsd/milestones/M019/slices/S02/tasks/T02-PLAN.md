---
estimated_steps: 5
estimated_files: 4
---

# T02: Wire settings route, update app.py handlers, and add settings UI controls

**Slice:** S02 — Push Sync + Settings UI
**Milestone:** M019

## Description

Connect T01's push_sync engine to the app's HTTP route handlers and add the settings UI. This adds the sync config POST route (direction + poll interval), updates sync_now to be bidirectional-aware, replaces the push_changes placeholder with the real push_sync call, and extends connect_status.html with direction radios, poll interval dropdown, and push result stats.

All htmx URLs must use the `/app/todoist-sync/` prefix per the project knowledge base rule.

## Steps

1. **Add `/_fragments/settings/sync-config` POST route to `app.py`** — Reads `sync_direction` and `poll_interval` from form data, saves via `ctx.settings.set()` (not `ctx.state` — settings are user-configurable, state is internal sync bookkeeping). Returns `_render_connect_status(ctx)`. Pattern: identical to `apps/github-sync/app.py` save_sync_config route.

2. **Update `_render_connect_status()` in `app.py`** — Read additional template variables:
   - `sync_direction` from `ctx.settings.get("sync_direction")` (default "pull-only")
   - `poll_interval` from `ctx.settings.get("poll_interval")` (default "15m")
   - `last_push_result` from `ctx.state.get("last_push_result")` (JSON parse, default None)
   - `last_sync_at` from `ctx.state.get("last_sync_at")` (default "")
   - Pass all to `ctx.render_template("connect_status.html", ...)`

3. **Update `sync_now` handler in `app.py`** — After the existing pull_sync call, check `sync_direction = await ctx.settings.get("sync_direction")`. If `"bidirectional"`, import and call `push_sync(ctx)`, store result in `last_push_result` state key (with try/except for error isolation). Update `last_sync_at` state key. Pattern: identical to github-sync's sync_now handler.

4. **Replace `push_changes` task handler** — Remove the placeholder body, import and call `push_sync(ctx)` with proper logging and error handling. Pattern: identical to github-sync's push_changes handler.

5. **Update `connect_status.html` template** — Add three sections after the existing project selection section and before the disconnect button. Copy structure from `apps/github-sync/frontend/templates/connect_status.html`:
   
   a. **Sync Configuration section** — Form with `hx-post="/app/todoist-sync/_fragments/settings/sync-config"` and `hx-target="#connect-content"`. Contains:
      - Direction fieldset: two radio buttons (pull-only checked when `sync_direction != 'bidirectional'`, bidirectional checked when equal). Labels: "Pull only" with hint "Todoist → SemPKM", "Bidirectional" with hint "Todoist ↔ SemPKM".
      - Poll interval fieldset: `<select>` with options 5m/15m/30m/1h, pre-selected from `poll_interval` variable.
      - Save Config button.
   
   b. **Update Sync Now section** — Change the existing sync-now form's `hx-post` target to `/app/todoist-sync/_fragments/settings/sync-now` (note: under `/settings/` path to match github-sync pattern). Keep pull stats display.
   
   c. **Push stats section** — Display `last_push_result` if present. Show status, pushed count, skipped count, closed/reopened counts if available, and errors count. Pattern: similar to github-sync's push stats section.
   
   d. **Verify all htmx attributes** use `/app/todoist-sync/` prefix — check every `hx-post`, `hx-get` attribute in the template.

6. **Write additional tests in `test_todoist_push_sync.py`** — Add test classes for route/handler behavior:
   - `TestSyncConfigRoute`: saves direction and interval via settings, returns status fragment
   - `TestSyncNowBidirectional`: sync_now calls push_sync when direction is bidirectional, doesn't call push when pull-only, isolates push errors
   - `TestPushChangesHandler`: push_changes task calls push_sync, logs result
   - `TestRenderConnectStatus`: template context includes sync_direction, poll_interval, last_push_result, last_sync_at
   - htmx prefix check: scan connect_status.html for any hx-post/hx-get without /app/todoist-sync/ prefix

## Must-Haves

- [ ] `/_fragments/settings/sync-config` POST route saves direction and interval via ctx.settings
- [ ] `_render_connect_status` passes sync_direction, poll_interval, last_push_result to template
- [ ] `sync_now` calls push_sync after pull when direction is bidirectional
- [ ] `push_changes` task handler calls real push_sync (not placeholder)
- [ ] connect_status.html has direction radios, poll interval dropdown, push stats section
- [ ] All htmx URLs use `/app/todoist-sync/` prefix
- [ ] 15+ additional unit tests for routes, handlers, and template context

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018 && python -m pytest backend/tests/test_todoist_push_sync.py -v` — 50+ total tests pass (T01's 35+ plus T02's 15+)
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018 && python -m pytest backend/tests/test_todoist_*.py -v` — all Todoist tests (218+) pass in <3s
- `rg "hx-" apps/todoist-sync/frontend/templates/ | grep -v "/app/todoist-sync/"` — returns empty

## Observability Impact

- **Settings state keys:** `sync_direction` and `poll_interval` stored via `ctx.settings.set()` — inspectable via app settings API
- **Push result in UI:** `last_push_result` state key rendered in connect_status.html push stats section — shows status, pushed/skipped/closed/reopened counts, error count
- **Bidirectional sync_now:** When direction is bidirectional, `sync_now` handler stores both `last_pull_result` and `last_push_result` in state, plus updates `last_sync_at` timestamp
- **push_changes task handler:** Logs push result via `todoist.sync` logger at INFO level with aggregate counts, WARNING on failure
- **Failure visibility:** Push errors surfaced in both the `last_push_result.errors` array (per-task IRI + error message) and in the settings UI push stats section

## Inputs

- `apps/todoist-sync/services/sync_engine.py` — T01's push_sync() function
- `apps/todoist-sync/app.py` — existing route handlers, _render_connect_status, sync_now, push_changes placeholder
- `apps/todoist-sync/frontend/templates/connect_status.html` — existing template with project selection, sync stats, disconnect
- `apps/github-sync/app.py` — reference: save_sync_config route (line 160), sync_now bidirectional logic (line 176), push_changes handler (line 240)
- `apps/github-sync/frontend/templates/connect_status.html` — reference: sync config form, push stats section HTML structure
- `backend/tests/test_todoist_push_sync.py` — T01's test file to extend with route/handler tests

## Expected Output

- `apps/todoist-sync/app.py` — updated with sync-config route, bidirectional sync_now, real push_changes handler, enriched _render_connect_status
- `apps/todoist-sync/frontend/templates/connect_status.html` — extended with sync config form, updated sync-now path, push stats section
- `backend/tests/test_todoist_push_sync.py` — extended with 15+ route/handler/template tests (50+ total)
