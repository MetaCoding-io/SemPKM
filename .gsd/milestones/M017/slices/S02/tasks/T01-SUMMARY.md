---
id: T01
parent: S02
milestone: M017
provides:
  - fetch_timeline() method on GitHubClient
  - extract_linked_issue_numbers() pure function on field_mapper
key_files:
  - apps/github-sync/services/github_client.py
  - apps/github-sync/services/field_mapper.py
  - backend/tests/test_github_client.py
  - backend/tests/test_github_field_mapper.py
key_decisions: []
patterns_established:
  - Timeline event filtering uses try/except with silent skip for malformed events — consistent with the existing graceful-degradation pattern in the sync engine
observability_surfaces:
  - fetch_timeline() inherits existing _request() DEBUG logging and error hierarchy
  - extract_linked_issue_numbers() is pure — no runtime signals, tested via unit tests only
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Add fetch_timeline() and extract_linked_issue_numbers() with tests

**Added fetch_timeline() to GitHubClient and extract_linked_issue_numbers() to field_mapper with 15 new unit tests**

## What Happened

Added two building blocks that T02's sync engine changes will consume:

1. `fetch_timeline(owner, repo, issue_number)` — thin convenience method on `GitHubClient` that delegates to `_paginate()` for the `/repos/{owner}/{repo}/issues/{number}/timeline` endpoint. No special headers needed since the timeline API graduated from preview.

2. `extract_linked_issue_numbers(timeline_events, repo_full_name)` — pure function that filters timeline events for `cross-referenced` events where the source is a PR (has `pull_request` key), restricts to same-repo matches, deduplicates, and returns sorted `(repo_full_name, pr_number)` tuples. Malformed events are silently skipped via try/except.

## Verification

- 88 tests pass across `test_github_client.py` (39) and `test_github_field_mapper.py` (49)
- 15 new tests: 6 client + 9 field mapper (exceeds ≥13 requirement)
- Full slice suite: 139 tests pass across all 5 test files

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py -v` | 0 | ✅ pass | 0.14s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v` | 0 | ✅ pass | 0.16s |

## Diagnostics

- `fetch_timeline()` inherits the existing error hierarchy — 401→GitHubAuthError, 403/429→GitHubRateLimitError, 4xx/5xx→GitHubAPIError
- `extract_linked_issue_numbers()` is pure, no runtime signals — test via the unit test suite
- Both functions are importable directly from their modules for REPL inspection

## Deviations

- Added 6 client tests instead of 5 (added separate `test_fetch_timeline_server_error` for 500 status)
- Added 9 field mapper tests instead of 8 (added `test_mixed_same_and_cross_repo` for coverage of mixed-repo filtering)
- Both deviations are additive — more coverage than planned

## Known Issues

None.

## Files Created/Modified

- `apps/github-sync/services/github_client.py` — added `fetch_timeline()` method (~20 lines)
- `apps/github-sync/services/field_mapper.py` — added `extract_linked_issue_numbers()` function (~40 lines)
- `backend/tests/test_github_client.py` — added `TestFetchTimeline` class with 6 tests
- `backend/tests/test_github_field_mapper.py` — added `TestExtractLinkedIssueNumbers` class with 9 tests, plus `_make_cross_ref_event` helper
- `.gsd/milestones/M017/slices/S02/tasks/T01-PLAN.md` — added Observability Impact section (pre-flight fix)
