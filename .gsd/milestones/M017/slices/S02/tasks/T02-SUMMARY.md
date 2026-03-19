---
id: T02
parent: S02
milestone: M017
provides:
  - PR sync as bpkm:Task objects with externalProvider "github-pr"
  - Phase 3 link-discovery loop creating bpkm:dependsOn edge commands from PR tasks to issue tasks
  - _find_existing_task() with optional provider parameter for slug-only lookups
  - edges_created count in last_pull_result diagnostic surface
key_files:
  - apps/github-sync/services/sync_engine.py
  - backend/tests/test_github_sync_engine.py
key_decisions:
  - Phase 3 iterates synced issues only (not PRs) for timeline queries — PRs don't have meaningful timeline cross-refs back to issues
  - provider=None in _find_existing_task omits the externalProvider SPARQL filter entirely — slug uniqueness via SHA-256 is sufficient
patterns_established:
  - Timeline errors use per-issue isolation with (timeline) suffix in failed_issues for distinguishable failure tracking
  - _make_github_responses() test helper auto-generates empty timeline responses for non-PR issues to keep existing tests working
observability_surfaces:
  - last_pull_result StateClient key now includes edges_created count
  - failed_issues entries with (timeline) suffix distinguish timeline API failures from issue processing failures
  - Log line at INFO includes edges count in pull sync completion message
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Wire PR sync and edge creation into pull_sync() with tests

**Removed PR skip filter, added phase 3 link-discovery loop that creates bpkm:dependsOn edges from PR tasks to issue tasks via timeline API, with 17 new tests (156 total passing)**

## What Happened

Modified `sync_engine.py` with four changes:

1. **`_find_existing_task()` extended** with optional `provider` parameter (default `"github"`). When `provider=None`, the SPARQL query omits the `externalProvider` filter — enabling slug-only lookups needed for phase 3 edge resolution where we need to find tasks regardless of whether they're issues or PRs.

2. **PR skip filter removed** — the `real_issues = [i for i in issues if not is_pull_request(i)]` line and skipped count increment were deleted. All items (issues and PRs) are now processed in the same loop. `build_task_properties()` already sets the correct `externalProvider` based on the `pull_request` key presence. Non-PR items are tracked in a `synced_issues` list for phase 3 timeline queries.

3. **Phase 3 link-discovery added** after phases 1+2. For each synced issue: fetches timeline via `github_client.fetch_timeline()`, extracts linked PR numbers via `extract_linked_issue_numbers()`, resolves both PR and issue task IRIs via `_find_existing_task(provider=None)`, and builds `edge.create` commands with `source=PR_IRI, target=Issue_IRI, predicate=bpkm:dependsOn`. Timeline errors are per-issue isolated with `(timeline)` suffix in `failed_issues`.

4. **`_make_result()` extended** with `edges_created` parameter, included in the result dict for diagnostic inspection.

Updated `_make_github_responses()` test helper to auto-generate empty timeline responses for each non-PR issue in the fixture list, keeping all existing tests working without manual response queue changes.

## Verification

All 156 tests pass across 5 test files:
- 37 in test_github_client.py (unchanged)
- 86 in test_github_field_mapper.py (unchanged)  
- 13 in test_github_auth.py (unchanged)
- 10 in test_github_person_matcher.py (unchanged)
- 43 in test_github_sync_engine.py (was 26, +17 new)

New test classes: `TestPRSync` (5 tests), `TestTimelineEdgeCreation` (8 tests), `TestFindExistingTaskProvider` (4 tests). Existing `TestPRFiltering` tests renamed to verify PRs are now *created* instead of *skipped*.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v` | 0 | ✅ pass | 0.22s |

## Diagnostics

- **edges_created**: Read `last_pull_result` from StateClient — JSON includes `edges_created` integer alongside `created`/`updated`/`errors`
- **Timeline failures**: `failed_issues` list entries with `(timeline)` suffix indicate timeline API failures separate from issue processing failures
- **Test inspection**: `TestTimelineEdgeCreation::test_edges_created_in_result` confirms the diagnostic surface; `test_timeline_api_error_isolated` confirms failure-path isolation

## Deviations

- Task plan step 7 specified `test_pr_properties_include_correct_provider` should assert `externalSource` in properties — the actual field name is `externalUrl` per the field_mapper implementation. Fixed to match reality.

## Known Issues

None.

## Files Created/Modified

- `apps/github-sync/services/sync_engine.py` — removed PR skip filter, added phase 3 link-discovery loop, extended `_find_existing_task()` with provider param, extended `_make_result()` with `edges_created`
- `backend/tests/test_github_sync_engine.py` — renamed PR filtering tests, added 17 new tests in TestPRSync/TestTimelineEdgeCreation/TestFindExistingTaskProvider, updated `_make_github_responses()` to auto-generate timeline responses
