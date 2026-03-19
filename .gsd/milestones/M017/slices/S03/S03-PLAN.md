# S03: Push Sync + Settings Polish

**Goal:** Complete bidirectional sync — detect local task changes, push status/title updates to GitHub via PATCH API, and polish settings UI with repo selection, sync direction, poll interval, and sync stats.

**Demo:** User changes a task's status from "todo" to "done" in SemPKM, clicks Sync Now (or waits for poll), and the corresponding GitHub issue is closed. The next pull does not re-import the pushed change.

## Must-Haves

- `push_sync()`: SPARQL change detection for tasks with `externalProvider: "github"`, reverse field mapping (bpkm→GitHub), PATCH `/repos/{owner}/{repo}/issues/{number}`
- Loop prevention: `bpkm:lastSyncedAt` comparison in pull_sync (D205 pattern)
- `build_issue_patch()` reverse mapper: status done→closed/todo→open, title
- Settings POST routes: repo selection, sync direction (pull-only/bidirectional), poll interval
- Settings template: repo checkboxes, direction radios, interval dropdown, Sync Now button, sync stats
- ~40+ unit tests covering reverse mapping, push logic, loop prevention

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_push_sync.py tests/test_github_field_mapper.py tests/test_github_sync_engine.py -v` — all pass
- Loop prevention unit tests prove pull_sync skips issues where `updated_at ≤ lastSyncedAt`

## Observability / Diagnostics

- Runtime signals: Logger `github_sync.sync` at INFO for push start/complete with counts
- Inspection surfaces: StateClient keys `last_push_result` (JSON with status/pushed/skipped/errors), `sync_repos`, `sync_direction`, `poll_interval`
- Failure visibility: Per-issue push error isolation with warning log

## Tasks

- [ ] **T01: Reverse field mapping + GitHub PATCH client method** `est:30m`
  - Why: Pure functions for converting bpkm properties back to GitHub issue fields
  - Files: `apps/github-sync/services/field_mapper.py`, `apps/github-sync/services/github_client.py`, `backend/tests/test_github_field_mapper.py`, `backend/tests/test_github_client.py`
  - Do: `build_issue_patch(task_properties)` → dict with `title`, `state` (todo→open, done→closed), `labels` (tags→label names). V1 pushes status and title only, not labels (per research: creating labels via API may surprise users). `update_issue(owner, repo, number, patch_data)` on GitHubClient — PATCH `/repos/{owner}/{repo}/issues/{number}`. Unit tests for all reverse mapping cases.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_field_mapper.py tests/test_github_client.py -v`
  - Done when: Reverse mapping covers status and title (~15 tests), PATCH method tested (~5 tests)

- [ ] **T02: push_sync() + loop prevention + settings routes** `est:45m`
  - Why: Completes bidirectional sync and user-facing settings
  - Files: `apps/github-sync/services/sync_engine.py`, `apps/github-sync/app.py`, `apps/github-sync/frontend/templates/connect_status.html`, `backend/tests/test_github_push_sync.py`
  - Do: `push_sync()`: SPARQL query for tasks with `externalProvider: "github"` and `dcterms:modified > lastSyncedAt`, reverse-map properties, call `update_issue()` for each, update `lastSyncedAt` after success. Loop prevention in `pull_sync()`: skip issues where `updated_at ≤ task's bpkm:lastSyncedAt` (D205). Settings routes: POST `/settings/repos` (checkbox list), POST `/settings/direction` (pull-only/bidirectional), POST `/settings/interval` (dropdown). Update connect_status.html with repo checkboxes (fetched via `fetch_repos()`), direction radios, interval dropdown, Sync Now button, sync stats section showing last_pull_result/last_push_result. Register `push-changes` scheduled task in manifest (runs if sync_direction == "bidirectional").
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_push_sync.py -v` — push sync + loop prevention tests pass (~20 tests)
  - Done when: push_sync writes changes back, loop prevention proven, settings routes persist state

## Files Likely Touched

- `apps/github-sync/services/field_mapper.py`
- `apps/github-sync/services/github_client.py`
- `apps/github-sync/services/sync_engine.py`
- `apps/github-sync/app.py`
- `apps/github-sync/manifest.yaml`
- `apps/github-sync/frontend/templates/connect_status.html`
- `backend/tests/test_github_field_mapper.py`
- `backend/tests/test_github_client.py`
- `backend/tests/test_github_push_sync.py`
