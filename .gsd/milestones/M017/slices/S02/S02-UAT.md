# S02: PR Pull Sync + PR-to-Issue Edge Linking — UAT

**Milestone:** M017
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All S02 work is unit-tested pure functions and sync logic with mocked dependencies. No runtime, UI, or Docker needed. S04 will provide live runtime E2E verification.

## Preconditions

- Backend venv exists at `backend/.venv/` with all dependencies installed
- All source files in `apps/github-sync/services/` and `backend/tests/` are up to date

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py::TestPRSync::test_pr_creates_task_with_github_pr_provider tests/test_github_sync_engine.py::TestTimelineEdgeCreation::test_edge_created_for_cross_referenced_pr -v
```

Both tests pass — confirms PRs create tasks and cross-referenced PRs produce edge commands.

## Test Cases

### 1. Full test suite passes with ≥150 tests

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v`
2. **Expected:** All 156 tests pass. Zero failures. Duration < 1s.

### 2. PR creates task with github-pr provider

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py::TestPRSync -v`
2. **Expected:** All 5 tests pass:
   - `test_pr_creates_task_with_github_pr_provider` — PR item produces `object.create` command with `externalProvider: "github-pr"`
   - `test_mixed_issues_and_prs_all_created` — both issues and PRs create tasks (no skip filter)
   - `test_pr_body_set` — PR with body produces `body.set` command
   - `test_pr_update_existing` — existing PR task produces `object.patch` instead of `object.create`
   - `test_pr_properties_include_correct_provider` — PR task properties include `externalUrl` pointing to PR HTML URL

### 3. Timeline edge creation works

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py::TestTimelineEdgeCreation -v`
2. **Expected:** All 8 tests pass:
   - `test_edge_created_for_cross_referenced_pr` — cross-referenced event produces `edge.create` command with `bpkm:dependsOn` predicate, source=PR task IRI, target=issue task IRI
   - `test_no_edges_when_no_cross_references` — empty timeline produces 0 edges
   - `test_edge_skipped_when_pr_task_not_found` — if PR task doesn't exist in graph, edge is silently skipped (no crash)
   - `test_edge_skipped_when_issue_task_not_found` — if issue task doesn't exist in graph, edge is silently skipped
   - `test_multiple_prs_referencing_same_issue` — multiple PRs referencing one issue produce multiple edges
   - `test_timeline_api_error_isolated` — timeline API error for one issue doesn't abort other issues; failed issue logged with `(timeline)` suffix
   - `test_edges_created_in_result` — `last_pull_result` includes `edges_created` count
   - `test_timeline_not_called_for_prs` — timeline fetch is only called for issues, not for PRs

### 4. fetch_timeline() client method works

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_client.py::TestFetchTimeline -v`
2. **Expected:** All 6 tests pass:
   - Basic fetch returns timeline events list
   - Pagination works (follows Link header)
   - Empty timeline returns `[]`
   - Auth error raises `GitHubAuthError`
   - API error raises `GitHubAPIError`
   - Server error (500) raises `GitHubAPIError`

### 5. extract_linked_issue_numbers() pure function works

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_field_mapper.py::TestExtractLinkedIssueNumbers -v`
2. **Expected:** All 9 tests pass:
   - Cross-referenced event with PR returns `(repo, pr_number)` tuple
   - Cross-referenced event without PR is filtered out
   - Cross-repo references are filtered out (only same-repo kept)
   - Same-repo references are included
   - Empty timeline returns `[]`
   - Duplicate events are deduplicated
   - Malformed events are silently skipped
   - Multiple PRs referencing one issue returns all PR numbers
   - Mixed same-repo and cross-repo events correctly filtered

### 6. _find_existing_task provider parameter works

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py::TestFindExistingTaskProvider -v`
2. **Expected:** All 4 tests pass:
   - Default provider (`"github"`) includes `externalProvider` filter in SPARQL
   - PR provider (`"github-pr"`) includes PR-specific filter
   - `provider=None` omits the `externalProvider` filter entirely
   - `provider=None` can find PR tasks by slug alone

### 7. Existing S01 tests unbroken

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py::TestPRFiltering -v`
2. **Expected:** Both PR filtering tests pass — now verify PRs are *created* (not skipped):
   - `test_prs_are_created_as_tasks` — mixed issues+PRs all produce commands
   - `test_all_prs_creates_pr_tasks` — all-PR input creates tasks for all items

## Edge Cases

### Timeline API returns 500 for one issue among many

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py::TestTimelineEdgeCreation::test_timeline_api_error_isolated -v`
2. **Expected:** Test passes — error isolated to one issue, other issues processed successfully. Failed issue appears in `failed_issues` with `(timeline)` suffix.

### PR task not found during edge resolution

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py::TestTimelineEdgeCreation::test_edge_skipped_when_pr_task_not_found -v`
2. **Expected:** Test passes — edge silently skipped, no crash, sync continues.

### Malformed timeline event

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_field_mapper.py::TestExtractLinkedIssueNumbers::test_malformed_event_skipped -v`
2. **Expected:** Test passes — malformed event silently skipped, valid events still extracted.

## Failure Signals

- Any test failure in the 156-test suite indicates a regression
- `edges_created` missing from `_make_result()` output would indicate the diagnostic surface is broken
- `(timeline)` suffix absent from failed_issues entries would indicate timeline error isolation is broken
- Tests in `TestPRFiltering` checking that PRs are *skipped* would indicate the PR skip filter was re-introduced

## Requirements Proved By This UAT

- GH-03 (PR sync + issue linking) — contract-level proof via 32 new unit tests covering PR task creation, timeline parsing, edge creation, error isolation, and diagnostic surfaces

## Not Proven By This UAT

- Runtime PR sync against actual GitHub API responses — deferred to S04 E2E with mock GitHub API server
- Edge visibility in the UI Relations panel — deferred to S04 E2E
- Rate limit behavior during timeline fetch phase — tested at client level (S01) but not at sync pipeline level under load

## Notes for Tester

- All tests are pure unit tests with mocked HTTP responses — no Docker, no network, no triplestore needed.
- The `_make_github_responses()` helper auto-generates empty timeline responses for non-PR issues. If a test adds new issue fixtures without updating the helper, timeline-related tests may get unexpected empty results.
- The edge predicate is `bpkm:dependsOn` (not `bpkm:closesIssue`). This is intentional per the implementation — check the sync_engine.py phase 3 code if this seems wrong.
