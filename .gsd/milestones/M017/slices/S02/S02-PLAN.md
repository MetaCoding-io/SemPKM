# S02: PR Pull Sync + PR-to-Issue Edge Linking

**Goal:** GitHub PRs sync as `bpkm:Task` objects with `externalProvider: "github-pr"`, and PRs that reference issues have `bpkm:dependsOn` edges linking the PR task to the issue task.
**Demo:** After pull sync, PRs appear as tasks alongside issues. A PR that "Closes #42" has an edge from the PR task to the issue #42 task, discoverable via SPARQL and visible in the Relations panel.

## Must-Haves

- `fetch_timeline()` on `GitHubClient` using existing `_paginate()` for `GET /repos/{owner}/{repo}/issues/{number}/timeline`
- `extract_linked_issue_numbers()` pure function on `field_mapper.py` that filters timeline events for `cross-referenced` type where `source.issue.pull_request` exists, with deduplication
- PR skip filter removed from `pull_sync()` — PRs processed as tasks with `externalProvider: "github-pr"`
- Phase 3 link-discovery in `pull_sync()`: iterate synced issues, call timeline API, resolve linked PR task IRIs, submit `edge.create` commands with predicate `bpkm:dependsOn`
- `_find_existing_task()` supports provider-agnostic lookup by slug (for resolving PR task IRIs from issue slugs)
- Cross-repo and missing-task edge creation skipped gracefully with debug logging
- All 124 existing tests still pass (with PR-filtering tests modified)
- ~30 new tests covering timeline parsing, PR sync, and edge creation

## Proof Level

- This slice proves: contract (mocked unit tests, no live runtime)
- Real runtime required: no (deferred to S04 E2E)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v` — all tests pass, total ≥150
- Existing 124 tests still pass (PR-filtering tests modified to verify PRs are now *created* instead of *skipped*)
- `extract_linked_issue_numbers()` tests cover: cross-referenced with PR, without PR, cross-repo same-repo only, empty timeline, duplicate deduplication, malformed events
- Sync engine tests verify: PR creates task with `github-pr` provider, timeline edge creation produces `edge.create` commands, edge skipped when issue task not found, edge skipped when no cross-references, multiple PRs referencing same issue, `last_pull_result` includes `edges_created` count for diagnostic inspection

## Observability / Diagnostics

- Runtime signals: `last_pull_result` extended with `edges_created` count; logger `github_sync.sync` at DEBUG for timeline fetches, INFO for edge creation count
- Inspection surfaces: `last_pull_result` StateClient key — JSON now includes `edges_created` field alongside existing `created`/`updated`/`errors`
- Failure visibility: timeline API errors are per-issue isolated (caught and logged, don't abort sync); `failed_issues` list includes timeline failures with `(timeline)` suffix
- Redaction constraints: none (no secrets in timeline data)

## Integration Closure

- Upstream surfaces consumed: `GitHubClient._paginate()`, `field_mapper.compute_issue_slug()`, `field_mapper.is_pull_request()`, `field_mapper.build_task_properties()`, `sync_engine._find_existing_task()`, `sync_engine._submit_commands_batched()`
- New wiring introduced in this slice: `fetch_timeline()` method on client, `extract_linked_issue_numbers()` pure function, phase 3 link-discovery loop in `pull_sync()`
- What remains before the milestone is truly usable end-to-end: S03 (push sync + settings polish), S04 (E2E test + user guide)

## Tasks

- [ ] **T01: Add fetch_timeline() and extract_linked_issue_numbers() with tests** `est:30m`
  - Why: Pure functions that the sync engine consumes — testable in isolation, zero coupling to sync pipeline
  - Files: `apps/github-sync/services/github_client.py`, `apps/github-sync/services/field_mapper.py`, `backend/tests/test_github_client.py`, `backend/tests/test_github_field_mapper.py`
  - Do: Add `fetch_timeline(owner, repo, issue_number)` convenience method to GitHubClient (delegates to `_paginate()`). Add `extract_linked_issue_numbers(timeline_events, repo_full_name)` to field_mapper that filters for `event == "cross-referenced"` where `source.issue.pull_request` exists, extracts `(repo_full_name, issue_number)` tuples, deduplicates, and returns only same-repo matches. Add ~13 unit tests.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py -v` — all existing + new tests pass
  - Done when: `fetch_timeline()` and `extract_linked_issue_numbers()` exist with ≥13 new tests passing

- [ ] **T02: Wire PR sync and edge creation into pull_sync() with tests** `est:40m`
  - Why: Integrates the pure functions into the sync pipeline — removes PR skip filter, adds phase 3 link-discovery, creates `edge.create` commands
  - Files: `apps/github-sync/services/sync_engine.py`, `backend/tests/test_github_sync_engine.py`
  - Do: (1) Remove the PR skip filter from `pull_sync()`. (2) Track synced issues separately from PRs during the loop (need issue list for timeline queries). (3) After phases 1+2, add phase 3: iterate synced issues, call `fetch_timeline()` per issue, call `extract_linked_issue_numbers()`, resolve PR task IRIs via `_find_existing_task()`, build `edge.create` commands with predicate `bpkm:dependsOn`. (4) Modify `_find_existing_task()` to accept optional `provider` param (default `"github"`) so it can find both issue and PR tasks by slug. (5) Extend `_make_result()` with `edges_created` field. (6) Wrap timeline errors in per-issue isolation. (7) Update PR-filtering tests to verify PRs are now created. (8) Add ~17 new sync engine tests.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v` — all ≥150 tests pass
  - Done when: PRs create tasks, timeline edges produce `edge.create` commands, `last_pull_result` includes `edges_created`, total test count ≥150

## Files Likely Touched

- `apps/github-sync/services/github_client.py`
- `apps/github-sync/services/field_mapper.py`
- `apps/github-sync/services/sync_engine.py`
- `backend/tests/test_github_client.py`
- `backend/tests/test_github_field_mapper.py`
- `backend/tests/test_github_sync_engine.py`
