---
estimated_steps: 7
estimated_files: 4
---

# T02: Settings UI routes, template polish, and route tests

**Slice:** S03 — Push Sync + Settings Polish
**Milestone:** M017

## Description

Wire the push sync engine (from T01) into app routes and build the settings UI. This replaces the placeholder sync direction section with real controls, adds the sync-config POST route, makes sync_now bidirectional-aware, and replaces the stub push-changes task handler with the real push_sync call. The connect_status.html template gets sync direction radios, poll interval dropdown, and push result stats — matching the linear-sync template pattern exactly.

## Steps

1. **Add `/_fragments/settings/sync-config` POST route to `apps/github-sync/app.py`:**
   - Read `sync_direction` and `poll_interval` from form data
   - Store via `ctx.settings.set("sync_direction", ...)` and `ctx.settings.set("poll_interval", ...)`
   - Log the config change
   - Return `await _render_connect_status(ctx)`
   - Reference: `apps/linear-sync/app.py` `save_sync_config` route

2. **Update `sync_now` route in app.py:**
   - After pull_sync, read `sync_direction` from `ctx.settings`
   - If "bidirectional": import and call `push_sync(ctx)`, store result in state
   - Wrap push in its own try/except (same pattern as linear-sync)
   - Update `last_sync_at` after both pull and push complete
   - Reference: `apps/linear-sync/app.py` `sync_now` route

3. **Replace stub `push_changes` task handler in app.py:**
   - Import `push_sync` from `services.sync_engine`
   - Call `push_sync(ctx)` and return result
   - Wrap in try/except, log errors
   - Match the linear-sync `push_changes` pattern

4. **Update `_render_connect_status()` in app.py:**
   - Read `sync_direction` from `ctx.settings.get("sync_direction")` (default "pull-only")
   - Read `poll_interval` from `ctx.settings.get("poll_interval")` (default "15m")
   - Read `last_push_result` from `ctx.state.get("last_push_result")` and JSON parse
   - Pass all three as template variables alongside existing ones

5. **Update `apps/github-sync/frontend/templates/connect_status.html`:**
   - Replace the placeholder sync direction section with a real form:
     - `hx-post="/app/github-sync/_fragments/settings/sync-config"` (use proxy prefix)
     - Radio buttons: "Pull only" (GitHub → SemPKM) and "Bidirectional" (GitHub ↔ SemPKM)
     - Default checked based on `sync_direction` template var
   - Add poll interval `<select>` dropdown inside the same form (5m, 15m, 30m, 1h)
   - Add "Save Config" submit button
   - Add Last Push stats group in the sync stats section (matching linear-sync):
     - Status, pushed count, skipped count, errors count
     - Only shown when `last_push_result` is truthy
   - All htmx URLs must use `/app/github-sync/` proxy prefix
   - Reference: `apps/linear-sync/frontend/templates/connect_status.html` for exact structure

6. **Update imports in app.py:**
   - Add `push_sync` to the deferred imports inside `sync_now` and `push_changes`
   - Ensure the import path matches: `from services.sync_engine import pull_sync, push_sync`

7. **Write ≥15 new tests in `backend/tests/test_github_sync_engine.py`:**
   - Note: These are behavioral tests for the route/handler logic, not HTTP integration tests. Test via direct function calls to the handler logic and mock verification.
   - `TestSyncNowBidirectional`: mock ctx with direction="bidirectional", verify push_sync is called after pull_sync
   - `TestSyncNowPullOnly`: mock ctx with direction="pull-only", verify push_sync is NOT called
   - `TestPushChangesHandler`: verify the task handler calls push_sync and returns result
   - `TestRenderConnectStatus`: verify _render_connect_status reads sync_direction, poll_interval, last_push_result from settings/state
   - `TestSyncConfigRoute`: verify sync-config saves sync_direction and poll_interval to settings
   - Additional edge cases: default values when no settings exist, error handling in sync_now

## Must-Haves

- [ ] `sync-config` POST route saves sync_direction and poll_interval via ctx.settings
- [ ] `sync_now` calls push_sync after pull_sync when direction is "bidirectional"
- [ ] `push-changes` task handler calls real push_sync (not stub)
- [ ] `_render_connect_status` passes sync_direction, poll_interval, last_push_result to template
- [ ] connect_status.html has sync direction radios, poll interval dropdown, and push result stats
- [ ] All htmx URLs use `/app/github-sync/` proxy prefix
- [ ] ≥15 new tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py tests/test_github_client.py tests/test_github_auth.py tests/test_github_person_matcher.py -v` — full suite passes with ≥196 total tests
- Template contains radio inputs for sync_direction, select for poll_interval, and last_push_result stats section
- No `"push sync not implemented yet"` stub text remains in app.py
- All htmx URLs in connect_status.html use `/app/github-sync/` prefix (grep verify)

## Inputs

- `apps/github-sync/app.py` — current routes with stub push_changes handler
- `apps/github-sync/frontend/templates/connect_status.html` — current template with placeholder sync direction
- `apps/github-sync/services/sync_engine.py` — T01's `push_sync()` function (must be complete)
- `apps/linear-sync/app.py` — reference for save_sync_config, sync_now pull+push, push_changes handler
- `apps/linear-sync/frontend/templates/connect_status.html` — reference for radio/dropdown/stats HTML structure
- T01 summary — confirms push_sync signature, return format, state keys used
- `backend/tests/test_github_sync_engine.py` — existing mock infrastructure

## Expected Output

- `apps/github-sync/app.py` — sync-config route added, sync_now updated with push, push_changes wired, _render_connect_status extended
- `apps/github-sync/frontend/templates/connect_status.html` — real sync direction radios, poll interval dropdown, push stats section
- `backend/tests/test_github_sync_engine.py` — ≥15 new tests for route/handler behavior
