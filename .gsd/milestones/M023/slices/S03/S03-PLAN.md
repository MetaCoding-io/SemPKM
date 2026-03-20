# S03: Push sync + issue links

**Goal:** User edits task title/description/priority in SemPKM and changes push back to Jira via REST API. Issue links of type "blocks" create bpkm:dependsOn edges between tasks during pull sync. Full bidirectional sync loop works with loop prevention.
**Demo:** Run `pytest backend/tests/test_jira_sync_engine.py -v` — all existing tests pass (regression) plus ~50 new tests covering push sync pipeline and issue link processing.

## Must-Haves

- `_find_changed_tasks()` SPARQL query finds Jira-provider tasks where `dcterms:modified > bpkm:lastSyncedAt` (or no lastSyncedAt)
- Real `push_sync()` replaces stub — finds changed tasks, builds reverse field mapping (title/priority via `build_issue_patch()` + description via `markdown_to_adf()`), calls `JiraClient.update_issue()`, updates `lastSyncedAt` after push
- `build_issue_patch()` extended to include description as ADF dict (via `markdown_to_adf()`)
- Push sync reads task body text via SPARQL query (`urn:sempkm:body` predicate)
- Loop prevention: `lastSyncedAt` updated after push so next pull_sync skips re-import
- Per-task error isolation — one failed push doesn't kill the run
- Issue link processing in pull_sync: "Blocks" type links → `bpkm:dependsOn` edges between Task objects
- Issue link deduplication — process only outward "blocks" direction to avoid duplicate edges
- Result dict uses `status: "success"` (not `"ok"`) for consistency with pull_sync

## Proof Level

- This slice proves: contract
- Real runtime required: no (all verification via mocked clients)
- Human/UAT required: no

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_jira_sync_engine.py -v` — all ~145 tests pass (95 existing + ~50 new)
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_jira_*.py -v` — combined suite (~380+ tests) passes
- `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read())"` — valid Python
- `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/field_mapper.py').read())"` — valid Python
- `grep -c "push_sync\|_find_changed_tasks\|_process_issue_links" apps/jira-sync/services/sync_engine.py` — all three functions present
- `grep -c "dependsOn\|issue.*link\|blocks" backend/tests/test_jira_sync_engine.py` — issue link tests present
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_jira_sync_engine.py -k "error" -v` — error isolation and failure-path tests pass (push errors list, per-task isolation, partial status)

## Observability / Diagnostics

- Runtime signals: `ctx.state "last_push_result"` — JSON with status/pushed/skipped/errors/timestamp. Structured logging at INFO for push phases, WARNING for per-task errors.
- Inspection surfaces: `ctx.state.get("last_push_result")` rendered in connect_status.html. `ctx.state.get("last_pull_result")` now includes issue link edge counts.
- Failure visibility: `errors` list in push result with per-task `{iri, error}` dicts. `failed_issues` in pull result for issue link processing failures.
- Redaction constraints: none (no secrets in sync state)

## Integration Closure

- Upstream surfaces consumed: `sync_engine.py` (S02 pull_sync + push_sync stub), `field_mapper.py` (S01 build_issue_patch, reverse_priority), `adf_converter.py` (S01 markdown_to_adf), `jira_client.py` (S01 JiraClient.update_issue), `auth.py` (S01 get_connection_status), `app.py` (S02 handler wiring for push-changes)
- New wiring introduced in this slice: none — `push-changes` handler already calls `push_sync()` from app.py (S02 wired it). Issue links processed inline in existing `pull_sync()` flow.
- What remains before the milestone is truly usable end-to-end: S04 (E2E tests + user guide)

## Tasks

- [x] **T01: Implement real push sync with SPARQL change detection and ADF description conversion** `est:45m`
  - Why: Replaces the push_sync stub with a real implementation enabling bidirectional sync. This is the higher-risk piece — integrates SPARQL change detection, reverse field mapping, ADF conversion, and Jira API update.
  - Files: `apps/jira-sync/services/sync_engine.py`, `apps/jira-sync/services/field_mapper.py`, `backend/tests/test_jira_sync_engine.py`
  - Do: (1) Add `_find_changed_tasks()` SPARQL function querying tasks with `externalProvider="jira"` where `dcterms:modified > bpkm:lastSyncedAt` — also OPTIONAL-bind `urn:sempkm:body` to get description text. (2) Add `_get_task_body()` SPARQL helper to read body text by IRI. (3) Extend `build_issue_patch()` in field_mapper.py to accept optional `description_adf` dict param and include it in the `fields` result. (4) Replace `push_sync()` stub with real implementation: auth check → direction check → find changed tasks → for each: read body via SPARQL, convert body to ADF via `markdown_to_adf()`, build issue patch with title/priority/description, call `JiraClient.update_issue(externalId, fields)`, update `lastSyncedAt`. (5) Use `status: "success"` (not `"ok"`) for result dict consistency. (6) Write ~30 unit tests covering: _find_changed_tasks (no tasks, one changed, one unchanged, pull-only filter), _get_task_body (found, not found), push_sync happy path with description ADF, push_sync error isolation, push_sync skip conditions, loop prevention, lastSyncedAt update, build_issue_patch with description.
  - Verify: `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_jira_sync_engine.py -v` — all existing + new tests pass
  - Done when: push_sync replaces stub, _find_changed_tasks exists, description push via markdown_to_adf works, ~125 total tests pass

- [x] **T02: Add issue link processing to pull sync with dependsOn edge creation** `est:30m`
  - Why: Closes the issue link requirement (JIRA-07). During pull sync, Jira issue links of type "Blocks" must create `bpkm:dependsOn` edges between the corresponding Task objects. This is a pull-side addition — no new API calls needed since issuelinks are already in the search response.
  - Files: `apps/jira-sync/services/sync_engine.py`, `backend/tests/test_jira_sync_engine.py`
  - Do: (1) Add `_process_issue_links()` helper that takes a list of issues and graph_client, iterates each issue's `fields.issuelinks` array, filters for link type name containing "block" (case-insensitive), processes only the `outwardIssue` entries (current issue is the blocker → outward is the blocked task) to avoid duplicate edges, looks up both Task IRIs via `_find_existing_task()`, and returns a list of `edge.create` commands with `bpkm:dependsOn` predicate. (2) Integrate `_process_issue_links()` into pull_sync as Phase 4 — after Phase 3 (epic→child linking) and before the final follow-up submission. Include edge commands in the combined follow-up batch. (3) Write ~20 unit tests covering: "Blocks" type → dependsOn edge, other link types ignored, inward links ignored (dedup), linked issue not synced → skip, empty issuelinks, multiple links on one issue, case-insensitive "blocks" matching, integration with full pull_sync.
  - Verify: `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_jira_sync_engine.py -v` — all ~145 tests pass
  - Done when: _process_issue_links exists, pull_sync creates dependsOn edges for "Blocks" links, ~145 total tests pass

## Files Likely Touched

- `apps/jira-sync/services/sync_engine.py` — push_sync real implementation, _find_changed_tasks, _get_task_body, _process_issue_links
- `apps/jira-sync/services/field_mapper.py` — build_issue_patch extension for description ADF
- `backend/tests/test_jira_sync_engine.py` — ~50 new tests for push sync and issue links
