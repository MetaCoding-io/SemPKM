---
estimated_steps: 5
estimated_files: 4
---

# T01: Add fetch_timeline() and extract_linked_issue_numbers() with tests

**Slice:** S02 — PR Pull Sync + PR-to-Issue Edge Linking
**Milestone:** M017

## Description

Add the two pure building blocks that T02's sync engine changes consume. `fetch_timeline()` is a thin convenience method on `GitHubClient` that delegates to the existing `_paginate()`. `extract_linked_issue_numbers()` is a pure function on `field_mapper.py` that filters timeline events for cross-referenced PRs and returns deduplicated `(repo_full_name, issue_number)` tuples for same-repo matches only. Both are testable in isolation with zero dependency on the sync pipeline.

## Steps

1. **Add `fetch_timeline()` to `GitHubClient`** in `apps/github-sync/services/github_client.py`:
   - Method signature: `async def fetch_timeline(self, owner: str, repo: str, issue_number: int) -> list[dict[str, Any]]`
   - Delegates to `self._paginate(f"/repos/{owner}/{repo}/issues/{issue_number}/timeline")`
   - No extra params needed — timeline endpoint doesn't support `since`/`state` filtering
   - Add the Accept header `application/vnd.github.mockingbird-preview+json` for timeline API (required for `cross-referenced` events) — override in the params or add a note that the existing Accept header `application/vnd.github+json` may work but `mockingbird-preview` is safer. Actually, the timeline events API graduated from preview — the standard `application/vnd.github+json` header works. Just use `_paginate()` directly.

2. **Add `extract_linked_issue_numbers()` to `field_mapper.py`** in `apps/github-sync/services/field_mapper.py`:
   - Signature: `def extract_linked_issue_numbers(timeline_events: list[dict], repo_full_name: str) -> list[tuple[str, int]]`
   - Iterate `timeline_events`, filter for events where:
     - `event.get("event") == "cross-referenced"`
     - `event.get("source", {}).get("issue", {}).get("pull_request")` is truthy (confirms source is a PR)
   - From each matching event, extract:
     - `source_repo = event["source"]["issue"]["repository"]["full_name"]`
     - `pr_number = event["source"]["issue"]["number"]`
   - Filter to same-repo only: `source_repo == repo_full_name`
   - Deduplicate by `(source_repo, pr_number)` tuples (use a `set` internally, return as sorted list)
   - Return `list[tuple[str, int]]` — each tuple is `(repo_full_name, pr_number)`
   - Handle malformed events gracefully: missing keys → skip with no error

3. **Add ~5 `fetch_timeline()` tests** to `backend/tests/test_github_client.py`:
   - `test_fetch_timeline_basic` — returns timeline events list
   - `test_fetch_timeline_pagination` — follows Link header for multi-page timelines
   - `test_fetch_timeline_empty` — returns empty list for issue with no timeline events
   - `test_fetch_timeline_auth_error` — raises `GitHubAuthError` on 401
   - `test_fetch_timeline_api_error` — raises `GitHubAPIError` on 404/500

4. **Add ~8 `extract_linked_issue_numbers()` tests** to `backend/tests/test_github_field_mapper.py`:
   - `test_cross_referenced_with_pr` — returns `(repo, number)` for a cross-referenced PR event
   - `test_cross_referenced_without_pr` — skips event where `source.issue` has no `pull_request` key (issue-to-issue cross-ref)
   - `test_cross_repo_filtered_out` — skips event from different repo
   - `test_same_repo_included` — includes event from same repo
   - `test_empty_timeline` — returns empty list
   - `test_duplicate_dedup` — two events with same PR number deduplicated to one
   - `test_malformed_event_skipped` — event missing `source` or `source.issue` is skipped without error
   - `test_multiple_prs_referencing_issue` — returns all unique PR numbers

5. **Run full test suite** to verify no regressions: `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py -v`

## Must-Haves

- [ ] `fetch_timeline(owner, repo, issue_number)` method on `GitHubClient` using `_paginate()`
- [ ] `extract_linked_issue_numbers(timeline_events, repo_full_name)` pure function returns deduplicated same-repo `(repo, pr_number)` tuples
- [ ] Malformed timeline events handled gracefully (no exceptions)
- [ ] ≥5 new client tests + ≥8 new field mapper tests, all passing
- [ ] All existing tests still pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py -v` — all existing + new tests pass
- New test count ≥13 (≥5 client + ≥8 field mapper)

## Inputs

- `apps/github-sync/services/github_client.py` — existing `GitHubClient` with `_paginate()` method and `MockExternalHttpClient` test pattern
- `apps/github-sync/services/field_mapper.py` — existing pure functions, `is_pull_request()` reference for PR detection pattern
- `backend/tests/test_github_client.py` — existing test structure with `MockExternalHttpClient` and async test fixtures
- `backend/tests/test_github_field_mapper.py` — existing 42 tests, module loading pattern via importlib

## Observability Impact

- **No runtime signals added.** Both functions are pure building blocks — `fetch_timeline()` delegates to `_paginate()` which already logs via `logger.debug()` in `_request()`, and `extract_linked_issue_numbers()` is a pure function with no side effects.
- **Inspection:** A future agent can verify these exist by running the test suites. The functions appear in `field_mapper.py` exports and `GitHubClient` method list.
- **Failure visibility:** `fetch_timeline()` inherits the existing error hierarchy (`GitHubAuthError`, `GitHubRateLimitError`, `GitHubAPIError`). `extract_linked_issue_numbers()` silently skips malformed events — no exceptions surface from bad input, which is intentional.

## Expected Output

- `apps/github-sync/services/github_client.py` — `fetch_timeline()` method added (~10 lines)
- `apps/github-sync/services/field_mapper.py` — `extract_linked_issue_numbers()` function added (~25 lines)
- `backend/tests/test_github_client.py` — ~5 new tests in a `TestFetchTimeline` class
- `backend/tests/test_github_field_mapper.py` — ~8 new tests in a `TestExtractLinkedIssueNumbers` class
