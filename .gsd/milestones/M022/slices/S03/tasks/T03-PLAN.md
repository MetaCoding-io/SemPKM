---
estimated_steps: 6
estimated_files: 2
---

# T03: Add settings UI + route wiring in app.py and template

**Slice:** S03 — Push sync + section-based status moves
**Milestone:** M022

## Description

Wire the push sync into the app's user-facing surface: settings route for sync direction/interval, bidirectional sync_now, push_changes task handler, and template updates. This is largely a clone of Linear's settings pattern adapted for Asana, with the Asana-specific field mapping sections already in place from S01.

## Steps

1. **Read** `apps/asana-sync/app.py` and `apps/asana-sync/frontend/templates/connect_status.html` to understand current structure.

2. **Add sync-config route** to `app.py`:
   ```python
   @asana_sync_app.route("/_fragments/settings/sync-config", methods=["POST"])
   ```
   Reads `sync_direction` and `poll_interval` from POST form data, saves to StateClient, returns `_render_connect_status(ctx)`. Clone from Linear's `apps/linear-sync/app.py` lines 282-293.

3. **Update `sync_now` route** — Currently only runs pull_sync. Add: read `sync_direction` from StateClient; if `"bidirectional"`, also run `push_sync(ctx)` and store `last_push_result`. Update `last_sync_at` timestamp. Clone the bidirectional pattern from Linear's sync_now route (`apps/linear-sync/app.py` lines 296-324). The route returns `_render_connect_status(ctx)` (not the inline HTML snippet it currently uses).

4. **Wire `push_changes` task handler** — Replace the current stub (`return {"status": "not_configured"}`) with:
   ```python
   result = await push_sync(ctx)
   return result
   ```
   Add `from .services.sync_engine import push_sync` to imports (pull_sync is already imported).

5. **Update `_render_connect_status()`** — Add these template context variables:
   - `sync_direction` — from `ctx.state.get("sync_direction") or "pull-only"`
   - `poll_interval` — from `ctx.state.get("poll_interval") or "15m"`
   - `last_sync_at` — from `ctx.state.get("last_sync_at")`
   - `last_pull_result` — JSON-parsed from `ctx.state.get("last_pull_result")` (may be None)
   - `last_push_result` — JSON-parsed from `ctx.state.get("last_push_result")` (may be None)

6. **Update `connect_status.html` template** — Add three new sections AFTER the field mapping configuration section and BEFORE the disconnect section. Clone the HTML structure from Linear's `apps/linear-sync/frontend/templates/connect_status.html` (lines 40-170), adapting all htmx URLs to use `/app/asana-sync/` prefix:

   **Section 1: Sync Configuration** — form with `hx-post="/app/asana-sync/_fragments/settings/sync-config"`:
   - Direction radios: "Pull only" (Asana → SemPKM) and "Bidirectional" (Asana ↔ SemPKM)
   - Poll interval select: 5m, 15m, 30m, 1h options
   - Save Config button

   **Section 2: Manual Sync** — form with `hx-post="/app/asana-sync/_fragments/sync-now"`:
   - Sync Now button with htmx indicator

   **Section 3: Sync Stats** — display last_sync_at, last_pull_result, last_push_result:
   - Last sync timestamp
   - Last Pull stat-group (status, created, updated, unchanged, errors)
   - Last Push stat-group (status, pushed, skipped, errors)
   - "No sync data yet" message when all empty

   **Critical**: All `hx-post` URLs must use `/app/asana-sync/` prefix per KNOWLEDGE.md. The `hx-target` should be `#connect-content` and `hx-swap` should be `innerHTML` (same as existing forms in the template).

## Must-Haves

- [ ] `/_fragments/settings/sync-config` POST route saves sync_direction and poll_interval
- [ ] `sync_now` runs push after pull when sync_direction is "bidirectional"
- [ ] `push_changes` task handler calls `push_sync()` (not stub)
- [ ] Template shows sync direction radios, poll interval dropdown, Sync Now button
- [ ] Template shows pull and push result stats with stat-group/stat-row pattern
- [ ] All htmx URLs use `/app/asana-sync/` prefix
- [ ] `app.py` passes `ast.parse()` syntax validation

## Verification

- `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` — no SyntaxError
- `grep -c 'hx-post="/app/asana-sync/' apps/asana-sync/frontend/templates/connect_status.html` — returns 2+ (sync-config + sync-now forms)
- `grep -c 'stat-group\|stat-row' apps/asana-sync/frontend/templates/connect_status.html` — returns 10+ (pull + push stat sections)
- `grep 'push_sync' apps/asana-sync/app.py` — appears in both push_changes handler and sync_now route
- Template contains `sync_direction`, `poll_interval`, `last_pull_result`, `last_push_result` template variables

## Observability Impact

- **New StateClient keys:** `sync_direction` (string: "pull-only" or "bidirectional"), `poll_interval` (string: "5m"/"15m"/"30m"/"1h"), `last_sync_at` (ISO timestamp), `last_pull_result` (JSON), `last_push_result` (JSON)
- **Template signals:** Sync Stats section renders `last_pull_result` and `last_push_result` as stat-group/stat-row blocks — visible in the settings UI as pull/push status, counts, and error counts
- **Logger:** `asana.sync.app` logs sync-config saves, manual sync triggers, and push/pull errors
- **Failure visibility:** If push_sync fails during manual sync, the error is caught, logged, and stored in `last_push_result` with `status: "error"` — visible in the Sync Stats UI section
- **Inspection:** Future agents can check sync direction and interval via StateClient keys; last sync results via `last_pull_result`/`last_push_result` JSON

## Inputs

- `apps/asana-sync/app.py` — Current app routes (~606 lines). push_changes is a stub. sync_now only runs pull.
- `apps/asana-sync/frontend/templates/connect_status.html` — Current template (~371 lines). Has OAuth, project selection, field mapping sections. No sync config or stats sections.
- `apps/linear-sync/app.py` — Reference for sync-config route (lines 282-293), bidirectional sync_now (lines 296-324), and _render_connect_status context (lines 46-78).
- `apps/linear-sync/frontend/templates/connect_status.html` — Reference for sync config + Sync Now + stats HTML (lines 40-170).
- T02 output: `push_sync()` function in `apps/asana-sync/services/sync_engine.py`.

## Expected Output

- `apps/asana-sync/app.py` — Modified with sync-config route, bidirectional sync_now, push_changes wiring, extended _render_connect_status context (~50-60 new lines)
- `apps/asana-sync/frontend/templates/connect_status.html` — Extended with sync config, Sync Now, and stats sections (~80-100 new lines)
