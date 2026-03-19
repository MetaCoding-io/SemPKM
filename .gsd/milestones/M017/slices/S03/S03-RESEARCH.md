# S03: Push Sync + Settings Polish — Research

**Date:** 2026-03-18

## Summary

This is straightforward work adapting the Linear Sync push_sync pattern (already proven in M016/S03) for GitHub's REST PATCH API. All key infrastructure already exists: `GitHubClient.patch_issue()` is implemented, `build_issue_patch()` reverse mapper is implemented and tested, and the Linear sync_engine.py provides an exact template for `push_sync()` and `_find_changed_tasks()`.

The main gap is that the current GitHub pull_sync does not store `bpkm:lastSyncedAt` per-task, which is required for loop prevention during push sync. This needs to be added to `build_task_properties()` in field_mapper.py and the pull_sync loop prevention check (comparing `updated_at <= lastSyncedAt`) must be added to sync_engine.py.

Settings polish is also straightforward — the Linear sync connect_status.html already has sync direction radios, poll interval dropdown, and push result stats. The GitHub template currently has a placeholder "Pull only — push sync coming in a future update" section that needs replacing with real controls.

## Recommendation

Three tasks: (1) push sync engine + loop prevention plumbing, (2) settings UI + app route polish, (3) unit tests (~40+). Task 1 is the core work; task 2 is template wiring; task 3 validates everything.

## Implementation Landscape

### Key Files

**Modify:**
- `apps/github-sync/services/sync_engine.py` — Add `_find_changed_tasks()` SPARQL query and `push_sync()` function. Add loop prevention to existing `pull_sync()` (check `updated_at <= lastSyncedAt` on existing tasks before updating). Follows linear-sync `sync_engine.py` lines 87-350 almost exactly.
- `apps/github-sync/services/field_mapper.py` — Add `sync_time` parameter to `build_task_properties()` and include `bpkm:lastSyncedAt` in output properties. Also need `_resolve_reverse_state_reason()` helper to map cancelled→not_planned in `build_issue_patch()` (already partially implemented — `REVERSE_STATUS_MAP` exists and `build_issue_patch()` already handles state_reason).
- `apps/github-sync/app.py` — Replace stub `push_changes` task handler with real `push_sync()` call. Add routes: `/_fragments/settings/sync-config` (POST for direction + interval), update `/_fragments/settings/sync-now` to do pull+push when bidirectional. Add `sync_direction`, `poll_interval`, `last_push_result` to `_render_connect_status()` template context.
- `apps/github-sync/frontend/templates/connect_status.html` — Replace placeholder sync direction section with radio buttons (pull-only / bidirectional). Add poll interval dropdown. Add last_push_result stats group. Follow linear-sync template exactly.
- `backend/tests/test_github_sync_engine.py` — Add push_sync tests and loop prevention tests.
- `backend/tests/test_github_field_mapper.py` — Add tests for `lastSyncedAt` in build_task_properties and verify build_issue_patch handles all edge cases.

**Reference (read-only):**
- `apps/linear-sync/services/sync_engine.py` — `push_sync()` (lines 238-350) and `_find_changed_tasks()` (lines 87-128) are the exact templates.
- `apps/linear-sync/app.py` — Route structure for `save_sync_config`, `sync_now` (pull+push), push_changes task handler.
- `apps/linear-sync/frontend/templates/connect_status.html` — Template for sync direction radios, poll interval dropdown, push result stats.

### Detailed Change Map

**sync_engine.py changes:**

1. Add `_find_changed_tasks(graph_client)` — SPARQL query matching tasks with `externalProvider "github"`, `externalUuid` present, `dcterms:modified > bpkm:lastSyncedAt`, `syncDirection != "pull-only"`. Returns list of `{iri, externalUuid, externalId, status, title, lastSyncedAt, tags}`.

2. Add `push_sync(ctx)` — Steps:
   - Check auth status via `get_connection_status()`
   - Check sync_direction setting (skip if "pull-only")
   - Call `_find_changed_tasks()` 
   - For each changed task: call `build_issue_patch(task_props)` → `github_client.patch_issue(owner, repo, number, patch_data)` 
   - Update `lastSyncedAt` on each pushed task via `object.patch` command
   - Store `last_push_result` in state
   - Return structured result dict

3. Key difference from Linear: GitHub needs `owner`, `repo`, and `issue_number` to construct the PATCH URL. These can be derived from `externalId` ("#42") and the repo info. The `externalUrl` (`https://github.com/owner/repo/issues/42`) is the most reliable source — parse it. Or store repo_full_name in a new property. Simpler: store `externalUrl` already, parse it to extract owner/repo/number.

4. Add loop prevention to `pull_sync()`: After the `existing = await _find_existing_task(...)` check, if `existing` has `lastSyncedAt`, compare `issue["updated_at"] <= existing["lastSyncedAt"]` and skip if true (change originated from our push).

**field_mapper.py changes:**

1. Add `sync_time: str | None = None` parameter to `build_task_properties()`. If None, use `datetime.now(timezone.utc).isoformat()`. Include `bpkm:lastSyncedAt: sync_time` in output dict.

2. Add `parse_external_url(url: str) -> tuple[str, str, int] | None` — parse `https://github.com/owner/repo/issues/42` into `(owner, repo, 42)`. Needed by push_sync to construct the PATCH request.

**app.py changes:**

1. Add `/_fragments/settings/sync-config` POST route — reads `sync_direction` and `poll_interval` from form, stores via `ctx.settings.set()`.

2. Update `sync_now` to run push_sync after pull_sync when direction is "bidirectional" (matches linear-sync pattern).

3. Replace stub `push_changes` task handler with real `push_sync()` call.

4. Update `_render_connect_status()` to read/pass `sync_direction`, `poll_interval`, and `last_push_result` to template.

**connect_status.html changes:**

1. Replace the placeholder sync direction section with real radio buttons matching linear-sync template.
2. Add poll interval dropdown.
3. Add `last_push_result` stats group.
4. Update "Sync Now" form to use the same pattern as linear-sync (which does pull+push).

### _find_existing_task needs extending

The current `_find_existing_task()` returns `{iri, title, status}`. For push sync loop prevention, it needs to also return `lastSyncedAt`. Add an OPTIONAL clause for `bpkm:lastSyncedAt` and include it in the return dict.

### Parsing externalUrl for push_sync

`push_sync` needs to call `github_client.patch_issue(owner, repo, number, data)`. The task's `bpkm:externalUrl` contains `https://github.com/owner/repo/issues/42` (or `.../pull/42` for PRs). A simple URL parse extracts owner, repo, and number. This is cleaner than storing repo_full_name in a separate property.

The `_find_changed_tasks` SPARQL query must also fetch `externalUrl` and `externalId` to support this parsing.

### Build Order

1. **field_mapper.py** — Add `sync_time`/`lastSyncedAt` to `build_task_properties()`, add `parse_external_url()`. Small, testable, unblocks everything.
2. **sync_engine.py** — Add `_find_changed_tasks()`, `push_sync()`, loop prevention in `pull_sync()`, extend `_find_existing_task()` with lastSyncedAt.
3. **app.py + template** — Wire routes and UI. Depends on sync_engine changes.
4. **Tests** — Can start in parallel with implementation or after.

### Verification Approach

- `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py -v` — all tests pass
- New tests target ~40+: push_sync happy path, skip when not connected, skip when pull-only, empty changed tasks, partial failure, loop prevention (task skipped when updated_at <= lastSyncedAt), lastSyncedAt updated after push, build_issue_patch edge cases, parse_external_url parsing
- Template changes verified by reading the template and confirming it matches linear-sync pattern (no runtime verification needed — deferred to S04 E2E)

## Constraints

- App template htmx URLs must use `/app/github-sync/` proxy prefix (knowledge entry).
- `_submit_commands_batched()` bypasses SDK IRI prefix check via `ctx.commands._client` (D204 pattern).
- MockExternalHttpClient response queue ordering — tests depend on exact request sequence. Adding a new API call in pull_sync (for lastSyncedAt storage) won't break existing tests because the property is added to the existing object.create/object.patch commands, not as a separate API call.
- `build_issue_patch()` already handles title, status→state, state_reason, and labels→tags. No additional fields needed for v1 push.

## Common Pitfalls

- **Parsing externalUrl for PR vs issue paths** — GitHub URLs use `/issues/42` for issues and `/pull/42` for PRs, but both are patched via the same `PATCH /repos/{owner}/{repo}/issues/{number}` endpoint. The URL parser must handle both path patterns.
- **Loop prevention requires lastSyncedAt on ALL pull-synced tasks** — If existing tasks from S01/S02 don't have `lastSyncedAt`, `_find_changed_tasks` will treat them all as changed on first push sync run. The SPARQL query should handle missing `lastSyncedAt` gracefully (treat as changed, which is the safe default for the first push after upgrade).
- **sync_direction stored via ctx.settings vs ctx.state** — Linear sync uses `ctx.state.set("sync_direction", ...)`. Settings that are user-configurable UI controls should use `ctx.settings` for consistency. Check which the existing GitHub routes use (currently settings uses `ctx.settings.set("selected_repos", ...)`). Keep consistent — use `ctx.settings` for user preferences, `ctx.state` for runtime state.
