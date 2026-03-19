---
estimated_steps: 8
estimated_files: 4
---

# T03: Settings page polish + push-changes wiring + sync stats

**Slice:** S03 — Push Sync + Settings Polish + Admin Detail
**Milestone:** M016

## Description

Transform the read-only settings page into a full sync control panel with team selection, sync direction, poll interval, immediate sync trigger, and sync result display. Wire the `push-changes` task handler in app.py and register it in the manifest. This is the user-facing completion of bidirectional sync — without it, push sync is unreachable dead code.

The admin detail page already shows task run history with status/duration/error from the platform's `AppTaskRun` records (visible in `detail.html`'s Task History section). Rather than modifying the platform template, sync-specific metadata (last sync results, total synced tasks) goes in the app's own settings page, which admins can also reach.

## Steps

1. **Add `push-changes` task to `manifest.yaml`:**
   ```yaml
   - id: "push-changes"
     description: "Push local task changes back to Linear"
     interval: "15m"
     retryPolicy:
       maxRetries: 3
       maxBackoff: "60s"
   ```

2. **Add `push_changes` task handler to `app.py`:**
   ```python
   @linear_sync_app.task("push-changes")
   async def push_changes(ctx: AppContext):
       from services.sync_engine import push_sync
       logger.info("push-changes: starting push sync")
       try:
           result = await push_sync(ctx)
           logger.info("push-changes: completed — %s", result)
           return result
       except Exception as exc:
           logger.error("push-changes: push failed — %s", exc, exc_info=True)
           return {"status": "error", "message": str(exc)}
   ```

3. **Add settings form POST routes to `app.py`:**
   - `POST /_fragments/settings/teams` — reads `team_ids` multi-value from form, JSON-serializes and stores in `sync_teams` state key. Returns updated connect_status.html fragment.
   - `POST /_fragments/settings/sync-config` — reads `sync_direction` (string: "pull-only" or "bidirectional") and `poll_interval` (string: "5m", "15m", "30m", "1h") from form. Stores both in state. Returns updated connect_status.html fragment.
   - `POST /_fragments/sync-now` — immediately calls `pull_sync(ctx)` then `push_sync(ctx)` (if sync_direction is bidirectional). Stores results in state. Returns updated connect_status.html fragment with fresh stats.

4. **Rewrite `connect_status.html` with full sync controls:**
   - **Connection header**: keep existing status badge + auth method badge + workspace name.
   - **Teams section**: Replace read-only table with a `<form>` containing checkboxes per team. Each checkbox has `name="team_ids"` and `value="{{ team.id }}"`. Teams already in `sync_teams` state key are pre-checked. Form posts to `/_fragments/settings/teams` via htmx.
   - **Sync configuration section**: Radio buttons for sync direction (`pull-only` checked by default, `bidirectional`). Select dropdown for poll interval (5m, 15m (default), 30m, 1h). Form posts to `/_fragments/settings/sync-config` via htmx.
   - **Sync Now section**: Button that POSTs to `/_fragments/sync-now` via htmx. Shows htmx loading indicator during execution.
   - **Sync stats section**: Shows last sync time (from `last_sync_at` state), last pull result counts (from `last_pull_result` state — need to store this in pull_sync too), last push result counts (from `last_push_result` state), and total synced tasks count. Data passed as template variables from the connect_fragment route.
   - **Disconnect section**: keep existing disconnect button.

5. **Update `connect_fragment` route in `app.py`:**
   - When connected, read additional state keys: `sync_teams`, `sync_direction`, `poll_interval`, `last_sync_at`, `last_pull_result`, `last_push_result`.
   - Pass all as template variables to connect_status.html.
   - Parse `sync_teams` JSON to get list of selected team IDs for checkbox pre-checking.
   - Parse result JSONs for stats display.

6. **Add CSS for new settings controls to `styles.css`:**
   - Team checkbox list styling (`.team-checkbox-list`)
   - Sync config form layout (`.sync-config-form`)
   - Sync Now button styling (reuse `.btn-primary`)
   - Sync stats card styling (`.sync-stats`)
   - Radio button and select styling

7. **Verify the complete wiring:**
   - `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read())"` — syntax valid
   - Confirm manifest.yaml has both `poll-tasks` and `push-changes` tasks
   - Confirm connect_status.html renders with all sections (team checkboxes, config form, sync now, stats, disconnect)
   - Run existing test suite to ensure no regressions: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py tests/test_sync_engine.py -v`

## Must-Haves

- [ ] `push-changes` task in manifest.yaml with 15m interval
- [ ] `push_changes` task handler in app.py calling push_sync(ctx)
- [ ] `POST /_fragments/settings/teams` route saves selected team IDs to sync_teams state
- [ ] `POST /_fragments/settings/sync-config` route saves sync_direction and poll_interval
- [ ] `POST /_fragments/sync-now` route runs pull + push sync immediately
- [ ] connect_status.html has team checkboxes with pre-check for selected teams
- [ ] connect_status.html has sync direction radios and poll interval select
- [ ] connect_status.html has Sync Now button with htmx loading indicator
- [ ] connect_status.html has sync stats section (last sync time, pull/push results)
- [ ] connect_fragment route passes all sync state as template variables

## Verification

- `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read())"` — syntax valid
- `grep -c "push-changes" apps/linear-sync/manifest.yaml` — at least 1 match
- `grep -c "team_ids" apps/linear-sync/frontend/templates/connect_status.html` — at least 1 match (team checkboxes)
- `grep -c "sync-direction" apps/linear-sync/frontend/templates/connect_status.html` — at least 1 match
- `grep -c "sync-now" apps/linear-sync/frontend/templates/connect_status.html` — at least 1 match
- `grep -c "sync-stats" apps/linear-sync/frontend/templates/connect_status.html` — at least 1 match
- `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py tests/test_sync_engine.py -v` — no regressions

## Inputs

- `apps/linear-sync/app.py` — existing routes (connect_fragment, connect_api_key, oauth_callback, disconnect, poll_tasks)
- `apps/linear-sync/manifest.yaml` — existing manifest with poll-tasks task
- `apps/linear-sync/frontend/templates/connect_status.html` — current read-only template with teams table and disconnect
- `apps/linear-sync/frontend/static/styles.css` — existing CSS with button, table, status badge styles
- `apps/linear-sync/services/sync_engine.py` — T02's push_sync() and modified pull_sync()
- `apps/linear-sync/services/auth.py` — get_connection_status() for template data
- S02 Summary: StateClient key `sync_teams` (JSON list of team IDs) already used by pull_sync

## Expected Output

- `apps/linear-sync/manifest.yaml` — extended with push-changes task
- `apps/linear-sync/app.py` — extended with push_changes handler, 3 settings routes, updated connect_fragment
- `apps/linear-sync/frontend/templates/connect_status.html` — full sync control panel
- `apps/linear-sync/frontend/static/styles.css` — extended with sync control styles
