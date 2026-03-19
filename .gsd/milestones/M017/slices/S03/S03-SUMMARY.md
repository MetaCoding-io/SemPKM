---
id: S03
parent: M017
milestone: M017
provides:
  - push_sync() engine with SPARQL change detection, reverse field mapping, GitHub PATCH, loop prevention
  - parse_external_url() for issue/PR URL decomposition into (owner, repo, number)
  - _find_changed_tasks() SPARQL query (dcterms:modified > bpkm:lastSyncedAt)
  - Loop prevention in pull_sync() via lastSyncedAt timestamp comparison
  - lastSyncedAt field in build_task_properties() and _find_existing_task()
  - sync-config POST route saving sync_direction and poll_interval via ctx.settings
  - Bidirectional sync_now (pull + push when direction=bidirectional)
  - Real push_changes task handler wired to push_sync()
  - connect_status.html with direction radios, poll interval dropdown, push result stats
requires:
  - slice: S01
    provides: GitHubClient.patch_issue(), build_issue_patch(), _find_existing_task(), _submit_commands_batched(), get_connection_status(), pull_sync()
affects:
  - S04
key_files:
  - apps/github-sync/services/sync_engine.py
  - apps/github-sync/services/field_mapper.py
  - apps/github-sync/app.py
  - apps/github-sync/frontend/templates/connect_status.html
  - backend/tests/test_github_sync_engine.py
  - backend/tests/test_github_field_mapper.py
key_decisions:
  - sync_direction and poll_interval stored in ctx.settings (not ctx.state), matching github-sync's existing settings pattern (selected_repos uses ctx.settings)
  - Push sync import deferred inside sync_now and push_changes handlers to avoid circular imports at module load (same as linear-sync pattern)
  - Tags from SPARQL come as single strings; push_sync wraps in list for build_issue_patch
  - parse_external_url accepts both github.com and www.github.com hostnames
patterns_established:
  - Push sync follows linear-sync pattern exactly: auth check → direction check → find changed → per-task push → update lastSyncedAt → store result
  - Loop prevention via string comparison of ISO timestamps (updated_at <= lastSyncedAt) — lexicographic ordering equals temporal ordering for ISO-8601
  - _StubApp test helper for loading app.py via importlib — passthrough decorators let tests call route handlers directly as async functions
  - _RenderableAppContext captures template render calls for assertion without needing real Jinja2
observability_surfaces:
  - last_push_result StateClient key — JSON with status/pushed/skipped/errors/timestamp
  - Per-task errors in errors list with IRI and error message
  - sync_direction in SettingsClient — default "pull-only"
  - poll_interval in SettingsClient — default "15m"
  - Logger github_sync.sync at INFO for push start/complete, WARNING for per-task errors
drill_down_paths:
  - .gsd/milestones/M017/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M017/slices/S03/tasks/T02-SUMMARY.md
duration: 35m
verification_result: passed
completed_at: 2026-03-18
---

# S03: Push Sync + Settings Polish

**Push sync engine writes local task edits back to GitHub via PATCH API with loop prevention, and the settings UI exposes sync direction, poll interval, and push result diagnostics — 48 new tests (204 total), all passing.**

## What Happened

T01 built the core push sync pipeline. `push_sync()` in sync_engine.py detects locally-changed tasks via `_find_changed_tasks()` — a SPARQL query matching tasks with `externalProvider "github"` where `dcterms:modified > bpkm:lastSyncedAt` (or no lastSyncedAt). For each changed task, it builds a PATCH payload via `build_issue_patch()`, extracts the GitHub coordinates via `parse_external_url()` (handling both `/issues/` and `/pull/` paths), calls `github_client.patch_issue()`, and then updates `lastSyncedAt` via a bulk command. The structured `last_push_result` is stored in StateClient as JSON with status, pushed/skipped counts, errors list, and timestamp.

Loop prevention was added to `pull_sync()`: after finding an existing task, it compares `issue["updated_at"] <= existing["lastSyncedAt"]` and skips the update if true, preventing re-import of changes we just pushed. `build_task_properties()` now includes `bpkm:lastSyncedAt` in its output when a `sync_time` is provided, and `_find_existing_task()` returns lastSyncedAt via an OPTIONAL SPARQL clause.

T02 wired everything into the app routes. The `/_fragments/settings/sync-config` POST route saves sync_direction and poll_interval via `ctx.settings.set()`. `sync_now` was updated to call `push_sync()` after `pull_sync()` when direction is "bidirectional", with error isolation so push failures don't prevent the sync timestamp from updating. The stub `push_changes` task handler was replaced with a real implementation calling `push_sync()`. The connect_status.html template gained direction radio buttons (pull-only / bidirectional), a poll interval dropdown, and a push result stats section showing status, pushed count, skipped count, and error count.

## Verification

- **204 tests pass** across 5 test files in 0.24s: `test_github_sync_engine.py` (78), `test_github_field_mapper.py` (55), `test_github_client.py` (41), `test_github_auth.py` (20), `test_github_person_matcher.py` (10)
- 48 new tests: 33 from T01 (push sync, find changed tasks, loop prevention, parse_external_url, lastSyncedAt) + 15 from T02 (route behavior, bidirectional sync, handler wiring, settings persistence)
- Template verified: radio inputs for sync_direction, select for poll_interval, last_push_result stats display
- No stub text remains in app.py — all push-related handlers are fully wired
- All htmx URLs in connect_status.html use `/app/github-sync/` proxy prefix

## Requirements Advanced

- GH-04 — Push sync engine implemented with SPARQL change detection, reverse field mapping, GitHub PATCH mutations, lastSyncedAt update, and loop prevention. Contract-level proof via 33 unit tests covering happy path, error isolation, direction filtering, and diagnostics.
- GH-05 — Settings UI completed with sync direction radios, poll interval dropdown, Save Config button, push result stats section. 15 unit tests verify route behavior and template rendering.

## Requirements Validated

- None yet — GH-04 and GH-05 have contract proof (mocked unit tests) but require S04 E2E runtime validation before moving to validated status.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

None.

## Known Limitations

- Push sync and settings UI are contract-tested only (mocked unit tests). Runtime validation against Docker stack is deferred to S04 E2E test.
- Tags retrieved from SPARQL arrive as single strings and must be wrapped in lists for `build_issue_patch` — this works but is a subtle type coercion that could surface bugs if tag storage changes.

## Follow-ups

- S04 will provide E2E runtime validation (mock GitHub REST API server + Playwright test covering full install → configure → sync → verify → push → cleanup)
- S04 should test the bidirectional sync-now flow end-to-end to confirm push errors don't break pull results

## Files Created/Modified

- `apps/github-sync/services/sync_engine.py` — Added `_find_changed_tasks()`, `push_sync()`, extended `_find_existing_task()` with lastSyncedAt, loop prevention in `pull_sync()`
- `apps/github-sync/services/field_mapper.py` — Added `parse_external_url()`, extended `build_task_properties()` with sync_time/lastSyncedAt
- `apps/github-sync/app.py` — Added sync-config route, updated sync_now with bidirectional push, replaced push_changes stub, extended _render_connect_status
- `apps/github-sync/frontend/templates/connect_status.html` — Direction radios, poll interval dropdown, push result stats section
- `backend/tests/test_github_sync_engine.py` — 35 new tests (20 from T01 + 15 from T02), _StubApp and _RenderableAppContext helpers
- `backend/tests/test_github_field_mapper.py` — 13 new tests for parse_external_url and lastSyncedAt in build_task_properties

## Forward Intelligence

### What the next slice should know
- The push sync pipeline follows the exact same pattern as linear-sync: auth → direction → find changed → per-task push → update lastSyncedAt → store result. The mock GitHub API server in S04 needs to handle `PATCH /repos/{owner}/{repo}/issues/{number}` for push verification.
- `sync_now` runs pull first, then push (when bidirectional). The E2E test should verify both directions in sequence.
- The `last_push_result` diagnostic surface is the primary way to verify push outcomes — check `ctx.state.get("last_push_result")`.

### What's fragile
- Tags from SPARQL are single strings wrapped in lists before passing to `build_issue_patch` — the mock API server should return labels in the expected GitHub format (list of objects with `name` field).
- `parse_external_url` only handles `github.com` and `www.github.com` hostnames — GitHub Enterprise Server URLs would need extending.

### Authoritative diagnostics
- `last_push_result` in StateClient — JSON with `{status, pushed, skipped, errors, timestamp}`. This is the definitive push outcome surface.
- `last_pull_result` in StateClient — already existed from S01, now with loop prevention skipping unchanged tasks.
- Template renders both pull and push stats when available, showing "No sync data yet" when neither exists.

### What assumptions changed
- No assumptions changed. The push sync pattern mapped cleanly from linear-sync to github-sync.
