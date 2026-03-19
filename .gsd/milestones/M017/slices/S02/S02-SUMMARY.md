---
id: S02
parent: M017
milestone: M017
provides:
  - PR sync as bpkm:Task objects with externalProvider "github-pr"
  - Phase 3 link-discovery in pull_sync() creating bpkm:dependsOn edges from PR tasks to issue tasks via timeline API
  - fetch_timeline() method on GitHubClient for /repos/{owner}/{repo}/issues/{number}/timeline
  - extract_linked_issue_numbers() pure function filtering cross-referenced timeline events
  - _find_existing_task() extended with optional provider parameter for slug-only lookups
  - edges_created count in last_pull_result diagnostic surface
requires:
  - slice: S01
    provides: GitHubClient._paginate(), field_mapper.compute_issue_slug(), field_mapper.is_pull_request(), field_mapper.build_task_properties(), sync_engine._find_existing_task(), sync_engine._submit_commands_batched()
affects:
  - S04
key_files:
  - apps/github-sync/services/github_client.py
  - apps/github-sync/services/field_mapper.py
  - apps/github-sync/services/sync_engine.py
  - backend/tests/test_github_client.py
  - backend/tests/test_github_field_mapper.py
  - backend/tests/test_github_sync_engine.py
key_decisions:
  - Phase 3 iterates synced issues only (not PRs) for timeline queries — PRs don't have meaningful timeline cross-refs back to issues
  - provider=None in _find_existing_task omits the externalProvider SPARQL filter entirely — slug uniqueness via SHA-256 is sufficient
patterns_established:
  - Timeline event filtering uses try/except with silent skip for malformed events — consistent with the existing graceful-degradation pattern in the sync engine
  - Per-issue timeline error isolation with (timeline) suffix in failed_issues list for distinguishable failure tracking
  - _make_github_responses() test helper auto-generates empty timeline responses for non-PR issues to keep existing tests working
observability_surfaces:
  - last_pull_result StateClient key includes edges_created count alongside created/updated/errors
  - failed_issues entries with (timeline) suffix distinguish timeline API failures from issue processing failures
  - Log line at INFO includes edges count in pull sync completion message
drill_down_paths:
  - .gsd/milestones/M017/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M017/slices/S02/tasks/T02-SUMMARY.md
duration: 40m
verification_result: passed
completed_at: 2026-03-18
---

# S02: PR Pull Sync + PR-to-Issue Edge Linking

**GitHub PRs sync as bpkm:Task objects with `externalProvider: "github-pr"`, and cross-referenced PRs are linked to their target issues via `bpkm:dependsOn` edges through the GitHub Timeline API**

## What Happened

Two tasks built the PR sync and edge-linking pipeline on top of S01's issue sync infrastructure.

**T01** added two building blocks: `fetch_timeline()` on `GitHubClient` (thin convenience method delegating to the existing `_paginate()` for the `/repos/{owner}/{repo}/issues/{number}/timeline` endpoint), and `extract_linked_issue_numbers()` on `field_mapper` — a pure function that filters timeline events for `cross-referenced` type where the source is a PR (`pull_request` key present), restricts to same-repo matches, deduplicates, and returns sorted `(repo_full_name, pr_number)` tuples. Malformed events are silently skipped. 15 new tests (6 client, 9 field mapper).

**T02** integrated these into the sync pipeline with four changes: (1) removed the PR skip filter so all items (issues and PRs) are processed in the same loop — `build_task_properties()` already sets the correct `externalProvider` based on the `pull_request` key; (2) extended `_find_existing_task()` with an optional `provider` parameter (default `"github"`, `None` omits the filter) for slug-only lookups needed during edge resolution; (3) added phase 3 link-discovery after phases 1+2 — iterates synced issues, fetches timeline, extracts linked PR numbers, resolves both task IRIs, builds `edge.create` commands with `bpkm:dependsOn` predicate; (4) extended `_make_result()` with `edges_created` count. Timeline errors are per-issue isolated with `(timeline)` suffix in `failed_issues`. 17 new sync engine tests.

## Verification

156 tests pass across 5 test files in 0.17s:
- 37 in test_github_client.py (6 new for fetch_timeline)
- 86 in test_github_field_mapper.py (9 new for extract_linked_issue_numbers)
- 13 in test_github_auth.py (unchanged)
- 10 in test_github_person_matcher.py (unchanged)
- 43 in test_github_sync_engine.py (17 new: 5 PR sync + 8 timeline edge creation + 4 provider param)

All existing 124 S01 tests continue to pass — PR-filtering tests were renamed to verify PRs are now *created* instead of *skipped*. Test helper `_make_github_responses()` auto-generates empty timeline responses for non-PR issues so existing tests work without modification.

Observability verified: `edges_created` field present in `_make_result()` output, `(timeline)` suffix in `failed_issues` entries for timeline API errors.

## Requirements Advanced

- GH-03 — PR sync and edge linking fully implemented and unit-tested. PRs create tasks with `github-pr` provider. Timeline API cross-referenced events parsed and edges created. Runtime validation deferred to S04 E2E.

## Requirements Validated

- None — GH-03 requires S04 E2E runtime verification to move to validated status.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- T01 added 15 tests instead of planned ≥13 (6 client + 9 field mapper vs. planned ~13 total) — more coverage than planned.
- T02 plan step 7 referenced `externalSource` but the actual field name is `externalUrl` per the field_mapper implementation — test fixed to match reality.

## Known Limitations

- Edge creation is same-repo only — cross-repo PR references (e.g., a PR in `org/repo-a` closing an issue in `org/repo-b`) are filtered out by `extract_linked_issue_numbers()`. This is intentional for v1 simplicity.
- Timeline API is called per-issue sequentially — no parallelism. For repos with thousands of issues this could be slow. Acceptable for v1; batching/concurrency can be added if needed.
- Edge predicate is `bpkm:dependsOn` rather than a more specific `bpkm:closesIssue` — chosen for consistency with existing edge vocabulary.

## Follow-ups

- S04 E2E test needs to verify PR sync and edge creation against the mock GitHub API server in Docker.
- Mock GitHub API server needs timeline endpoint responses for cross-referenced events.

## Files Created/Modified

- `apps/github-sync/services/github_client.py` — added `fetch_timeline()` method (~20 lines)
- `apps/github-sync/services/field_mapper.py` — added `extract_linked_issue_numbers()` function (~40 lines)
- `apps/github-sync/services/sync_engine.py` — removed PR skip filter, added phase 3 link-discovery loop, extended `_find_existing_task()` with provider param, extended `_make_result()` with `edges_created`
- `backend/tests/test_github_client.py` — added `TestFetchTimeline` class with 6 tests
- `backend/tests/test_github_field_mapper.py` — added `TestExtractLinkedIssueNumbers` class with 9 tests
- `backend/tests/test_github_sync_engine.py` — renamed PR filtering tests, added 17 new tests (TestPRSync, TestTimelineEdgeCreation, TestFindExistingTaskProvider), updated `_make_github_responses()` helper

## Forward Intelligence

### What the next slice should know
- `pull_sync()` now has three phases: phase 1 (create/update tasks for all items including PRs), phase 2 (body.set for items with body content), phase 3 (timeline link-discovery for issues only). Push sync (S03) only needs to care about phases 1+2 for reverse mapping — phase 3 is read-only edge creation.
- The `_find_existing_task(provider=None)` variant is available for slug-only lookups if push sync needs to resolve tasks regardless of provider type.

### What's fragile
- `_make_github_responses()` test helper auto-generates empty timeline responses for each non-PR issue — if the sync engine changes to fetch timelines for PRs too, existing tests will silently get empty timelines instead of failing visibly.
- Phase 3 timeline fetch uses the same `github_client` instance as phases 1+2 — rate limit consumption is cumulative across all three phases.

### Authoritative diagnostics
- `last_pull_result` StateClient key — JSON includes `edges_created` integer. If edges aren't appearing, check this field first.
- `failed_issues` list entries with `(timeline)` suffix — these are timeline-specific failures separate from issue processing failures. Any entry here means the timeline API returned an error for that issue.

### What assumptions changed
- Original plan assumed PR-to-issue edges would use `bpkm:closesIssue` predicate — actual implementation uses `bpkm:dependsOn` for consistency with existing edge vocabulary. The predicate choice is easily changeable if needed.
