# S02: PR Pull Sync + PR-to-Issue Edge Linking

**Goal:** Extend pull sync to handle GitHub PRs as separate bpkm:Task objects with `externalProvider: "github-pr"`, and create edges between PRs and the issues they reference using the timeline API.

**Demo:** After sync, PRs appear as Task objects distinguishable from issues. A PR that "Closes #42" has an edge linking it to issue #42's Task object. Both are browsable in the workspace with correct relationships panel.

## Must-Haves

- PR detection: issues with `pull_request` key handled separately with `externalProvider: "github-pr"`
- Timeline API integration: `fetch_timeline_events()` on GitHubClient for `/repos/{owner}/{repo}/issues/{number}/timeline`
- Parse `cross-referenced` events to find PR→issue links
- Edge creation between PR task IRI and issue task IRI via `bpkm:dependsOn`
- Graceful skip when target issue's repo is not synced (cross-repo edge target doesn't exist)
- ~30+ unit tests for PR detection, timeline parsing, edge creation

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py -v` — all pass including new PR-related tests
- PR tasks have `externalProvider: "github-pr"` in unit test assertions
- Timeline cross-reference parsing produces correct edge commands

## Observability / Diagnostics

- Runtime signals: Logger `github_sync.sync` at INFO for PR count, edge count. WARNING for skipped cross-repo edges.
- Inspection surfaces: `last_pull_result` extended with `prs_created`, `prs_updated`, `edges_created`, `edges_skipped`
- Failure visibility: Per-PR and per-edge error isolation

## Tasks

- [ ] **T01: PR detection + provider distinction in field mapper and sync engine** `est:30m`
  - Why: PRs are issues with a `pull_request` key — need separate handling in the sync pipeline
  - Files: `apps/github-sync/services/field_mapper.py`, `apps/github-sync/services/sync_engine.py`, `backend/tests/test_github_field_mapper.py`, `backend/tests/test_github_sync_engine.py`
  - Do: In field_mapper, add `is_pull_request(issue_data)` check for `pull_request` key presence. `build_task_properties()` sets `externalProvider: "github-pr"` when `is_pull_request()` is true, otherwise "github". In sync_engine, `pull_sync()` processes both issues and PRs from the same `/repos/{owner}/{repo}/issues` response (GitHub returns both), using the detection to set the correct provider. Ensure `compute_issue_slug()` works identically for issues and PRs (same repo+number scheme).
  - Verify: Unit tests assert PR detection logic and provider field distinction (~10 tests)
  - Done when: PRs create tasks with `externalProvider: "github-pr"`, issues create tasks with `externalProvider: "github"`

- [ ] **T02: Timeline API client + cross-reference parsing + edge creation** `est:45m`
  - Why: Novel feature — PR-to-issue linking via GitHub's timeline events API
  - Files: `apps/github-sync/services/github_client.py`, `apps/github-sync/services/sync_engine.py`, `backend/tests/test_github_client.py`, `backend/tests/test_github_sync_engine.py`
  - Do: Add `fetch_timeline_events(owner, repo, issue_number)` to GitHubClient — GET `/repos/{owner}/{repo}/issues/{number}/timeline`, paginate, filter for `event == "cross-referenced"` where `source.issue.pull_request` exists (meaning a PR referenced this issue). Add `sync_pr_links()` in sync_engine: for each synced issue, fetch timeline events, find cross-referencing PRs, compute both IRIs via `compute_issue_slug()`, check target exists via SPARQL, create `bpkm:dependsOn` edge from PR task → issue task. Skip gracefully with warning when target IRI doesn't exist (cross-repo or PR not synced). Rate-limit awareness — timeline API is heavier, so only call for issues that have had recent PR activity (or just call for all and let rate limiting handle it).
  - Verify: Unit tests cover timeline event parsing, edge command generation, cross-repo skip (~20 tests)
  - Done when: `sync_pr_links()` produces correct edge commands for cross-referenced PRs and gracefully skips missing targets

## Files Likely Touched

- `apps/github-sync/services/github_client.py`
- `apps/github-sync/services/field_mapper.py`
- `apps/github-sync/services/sync_engine.py`
- `backend/tests/test_github_client.py`
- `backend/tests/test_github_field_mapper.py`
- `backend/tests/test_github_sync_engine.py`
