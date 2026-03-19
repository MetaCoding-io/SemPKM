# S03: Push Sync + Settings Polish

**Goal:** Push local task edits (title, status, labels) back to GitHub via PATCH API, with loop prevention and a complete settings UI for sync direction and poll interval.
**Demo:** User edits a task's status/title in SemPKM, triggers push, change appears in GitHub. Settings page has sync direction radios, poll interval dropdown, Sync Now does pull+push when bidirectional, and push result stats display alongside pull stats.

## Must-Haves

- `push_sync()` function in sync_engine.py detects changed tasks via SPARQL, reverse-maps via `build_issue_patch()`, calls `github_client.patch_issue()`, updates `lastSyncedAt`
- `_find_changed_tasks()` SPARQL query finds tasks where `dcterms:modified > bpkm:lastSyncedAt`
- `parse_external_url()` extracts (owner, repo, number) from `bpkm:externalUrl` for both `/issues/` and `/pull/` paths
- `build_task_properties()` includes `bpkm:lastSyncedAt` so pull-synced tasks get timestamps
- Loop prevention in `pull_sync()`: skip update when `updated_at <= lastSyncedAt`
- `_find_existing_task()` returns `lastSyncedAt` for loop prevention checks
- Settings POST route for sync direction + poll interval (stored via `ctx.settings`)
- `sync_now` runs push after pull when direction is "bidirectional"
- `push-changes` task handler calls real `push_sync()`
- connect_status.html has sync direction radios, poll interval dropdown, and push result stats
- `_render_connect_status()` reads and passes sync_direction, poll_interval, last_push_result to template
- `last_push_result` stored in StateClient as structured JSON diagnostic surface
- ≥40 new unit tests

## Proof Level

- This slice proves: contract (mocked unit tests, no live runtime)
- Real runtime required: no (deferred to S04 E2E)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py tests/test_github_client.py tests/test_github_auth.py tests/test_github_person_matcher.py -v` — all tests pass (existing 156 + ≥40 new)
- New push sync tests: `_find_changed_tasks` happy path, empty results, pull-only skip, direction filter, `push_sync` happy path, not-connected skip, pull-only skip, no-changed skip, partial failure with error recording, `lastSyncedAt` update after push
- New field mapper tests: `parse_external_url` for issue URL, PR URL, invalid URL, missing path segments; `build_task_properties` includes `lastSyncedAt`
- Loop prevention test: `pull_sync` skips update when `updated_at <= lastSyncedAt` on existing task
- Failure diagnostic test: `last_push_result` contains status, pushed count, errors list, and timestamp — proving inspectable failure state

## Observability / Diagnostics

- Runtime signals: `last_push_result` StateClient key — JSON with status/pushed/skipped/errors/timestamp. Logger `github_sync.sync` at INFO for push start/complete with counts, WARNING for per-task push errors.
- Inspection surfaces: `last_push_result` in StateClient, displayed in connect_status.html push stats section. `get_connection_status()` for auth check.
- Failure visibility: `errors` list in `last_push_result` with per-task IRI + error message. `failed_tasks` list distinguishes which tasks failed to push.
- Redaction constraints: PAT never included in push result or error messages.

## Integration Closure

- Upstream surfaces consumed: `GitHubClient.patch_issue()` (S01), `build_issue_patch()` (S01), `_find_existing_task()` (S01/S02), `_submit_commands_batched()` (S01), `get_connection_status()` (S01)
- New wiring introduced: `push_sync()` in sync_engine.py, `sync-config` POST route in app.py, push-changes task handler wired to real push_sync, bidirectional sync-now
- What remains: S04 (E2E test + user guide) for runtime validation

## Tasks

- [ ] **T01: Push sync engine with loop prevention and field mapper extensions** `est:45m`
  - Why: Core push sync logic — detects locally changed tasks, reverse-maps properties, pushes via PATCH API, updates lastSyncedAt, and adds loop prevention to pull_sync. This is the engine that GH-04 depends on.
  - Files: `apps/github-sync/services/sync_engine.py`, `apps/github-sync/services/field_mapper.py`, `backend/tests/test_github_sync_engine.py`, `backend/tests/test_github_field_mapper.py`
  - Do: (1) Add `parse_external_url()` to field_mapper.py — parse `https://github.com/owner/repo/issues/42` and `/pull/42` into `(owner, repo, 42)`. (2) Add `sync_time` param to `build_task_properties()`, include `bpkm:lastSyncedAt` in output. (3) Extend `_find_existing_task()` to also return `lastSyncedAt` via OPTIONAL clause. (4) Add `_find_changed_tasks(graph_client)` SPARQL query matching `externalProvider "github"`, `externalUuid` present, `dcterms:modified > bpkm:lastSyncedAt` (or no lastSyncedAt). (5) Add `push_sync(ctx)` — auth check → direction check → find changed → for each: build_issue_patch → parse_external_url → github_client.patch_issue → update lastSyncedAt → store last_push_result. (6) Add loop prevention to `pull_sync()`: after finding existing task, compare `issue["updated_at"] <= existing["lastSyncedAt"]` and skip if true. (7) Write ≥25 new tests. Follow the linear-sync sync_engine.py push_sync pattern closely.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py -v` — all pass including new push/loop tests
  - Done when: push_sync returns structured result, _find_changed_tasks works, loop prevention skips unchanged tasks, parse_external_url handles both URL patterns, ≥25 new tests pass

- [ ] **T02: Settings UI routes, template polish, and route tests** `est:30m`
  - Why: Wires push sync into app routes and provides the user-facing settings controls — completing GH-05 (settings UI) and making push sync triggerable from the UI.
  - Files: `apps/github-sync/app.py`, `apps/github-sync/frontend/templates/connect_status.html`, `backend/tests/test_github_sync_engine.py`
  - Do: (1) Add `/_fragments/settings/sync-config` POST route — reads sync_direction + poll_interval from form, stores via `ctx.settings.set()`. (2) Update `sync_now` to import and call `push_sync()` after `pull_sync()` when direction is "bidirectional", store `last_push_result` in state. (3) Replace stub `push_changes` task handler with real `push_sync()` call. (4) Update `_render_connect_status()` to read sync_direction, poll_interval, last_push_result from settings/state and pass to template. (5) Replace placeholder sync direction section in connect_status.html with radio buttons (pull-only / bidirectional), add poll interval dropdown, add push result stats group — matching linear-sync template pattern exactly. (6) Update last_sync_at to be set after sync_now completes. (7) Write ≥15 new tests for route behavior: sync-config saves settings, sync-now does pull+push when bidirectional, sync-now does pull-only when pull-only, push-changes calls push_sync, _render_connect_status includes new fields.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py tests/test_github_client.py tests/test_github_auth.py tests/test_github_person_matcher.py -v` — full suite passes with ≥196 total tests
  - Done when: sync-config route saves settings, sync_now does push when bidirectional, template shows direction radios + poll interval + push stats, push-changes task handler works, ≥15 new tests pass

## Files Likely Touched

- `apps/github-sync/services/sync_engine.py`
- `apps/github-sync/services/field_mapper.py`
- `apps/github-sync/app.py`
- `apps/github-sync/frontend/templates/connect_status.html`
- `backend/tests/test_github_sync_engine.py`
- `backend/tests/test_github_field_mapper.py`
