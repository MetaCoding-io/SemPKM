# S01: GitHub Client + PAT Auth + Issue Pull Sync — UAT

**Milestone:** M017
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 is contract-verified via 124 mocked unit tests. Real runtime integration is deferred to S04's E2E Playwright test against Docker stack with mock GitHub API server. All behavior is tested through importlib-loaded modules with mocked SDK clients.

## Preconditions

- Backend virtualenv exists at `backend/.venv/` with pytest installed
- Working directory is the project root (`/home/james/Code/SemPKM`)
- No Docker stack needed — all tests use mocked HTTP/SDK clients

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v
```

Expected: 124 tests pass in <1s.

## Test Cases

### 1. GitHub REST Client Pagination

1. Run `pytest tests/test_github_client.py::TestPagination -v`
2. **Expected:** 6 tests pass — single page, multi-page Link header following, max pages guard (50), empty results, malformed Link header stops, first request uses params.

### 2. Rate-Limit Checking and Error Handling

1. Run `pytest tests/test_github_client.py::TestRateLimitChecking tests/test_github_client.py::TestErrorHandling -v`
2. **Expected:** 11 tests pass — sleep when remaining < 100, no sleep above threshold, missing headers safe, 401→AuthError, 403→RateLimitError, 429→RateLimitError with retry_after, 500→APIError, no-PAT→AuthError.

### 3. PAT Auth Storage and Verification

1. Run `pytest tests/test_github_auth.py -v`
2. **Expected:** 15 tests pass — store/get/verify/disconnect, masked preview (standard PAT, short PAT, fine-grained PAT), connected/disconnected/error status states.

### 4. Field Mapper: GitHub Issue → bpkm:Task Properties

1. Run `pytest tests/test_github_field_mapper.py::TestBuildTaskProperties -v`
2. **Expected:** 18 tests pass covering: basic issue (all fields), missing optional fields, open→todo, closed→done, closed+not_planned→cancelled, closed+completed→done, reopened→todo, labels→tags, assignee IRI passthrough, no-person→omit, milestone→project, external ID "#N", external URL, external UUID, externalProvider "github" for issues, "github-pr" for PRs, due date from milestone, no due date when milestone lacks due_on.

### 5. Field Mapper: Reverse Mapping (for Push Sync)

1. Run `pytest tests/test_github_field_mapper.py::TestBuildIssuePatch -v`
2. **Expected:** 7 tests pass — title mapping, todo→open, done→closed, cancelled→closed+not_planned, labels reverse, empty properties, in_progress/blocked→open.

### 6. PR Detection

1. Run `pytest tests/test_github_field_mapper.py::TestIsPullRequest -v`
2. **Expected:** 3 tests pass — issue without PR key (False), issue with PR key (True), PR-as-issue (True).

### 7. Person Matcher: Email-First + Login-Fallback Resolution

1. Run `pytest tests/test_github_person_matcher.py -v`
2. **Expected:** 10 tests pass — match by email, match by login, miss creates person, cache hit skips SPARQL, email preferred over login, null email falls back to login, None/empty assignee returns None, created person has correct properties, created person with email.

### 8. Pull Sync: Full Pipeline

1. Run `pytest tests/test_github_sync_engine.py::TestPullSyncBasic -v`
2. **Expected:** 7 tests pass — skips when not connected, skips when no repos selected, creates task for new issue, updates existing task, empty repo, multiple repos, delta sync uses `since` parameter.

### 9. Pull Sync: PR Filtering

1. Run `pytest tests/test_github_sync_engine.py::TestPRFiltering -v`
2. **Expected:** 2 tests pass — PRs skipped with increment to skipped count, all-PRs repo yields zero created.

### 10. Error Isolation and Diagnostics

1. Run `pytest tests/test_github_sync_engine.py::TestErrorIsolation tests/test_github_sync_engine.py::TestLastPullResultDiagnostics -v`
2. **Expected:** 6 tests pass — single issue failure doesn't abort sync, partial failure records failed_issues, all issues fail gives "error" status, success result has correct structure (status/created/updated/skipped/errors/duration_ms/timestamp), partial failure diagnostics include error count + failed_issues list, skipped result persisted.

### 11. Manifest Validity

1. Run `python3 -c "import yaml; m = yaml.safe_load(open('apps/github-sync/manifest.yaml')); assert m['id'] == 'github-sync'; assert 'api.github.com' in m['permissions']['network']"`
2. **Expected:** No error — manifest has correct ID and network permissions.

### 12. Template Proxy Prefix

1. Run `grep -c '/app/github-sync/' apps/github-sync/frontend/templates/*.html`
2. **Expected:** All htmx URLs use `/app/github-sync/` prefix (4 occurrences across 2 files).

## Edge Cases

### Rate-limit with missing reset header

1. Run `pytest tests/test_github_client.py::TestRateLimitChecking::test_remaining_below_threshold_no_reset_header_defaults_60s -v`
2. **Expected:** When `X-RateLimit-Remaining` is below threshold but `X-RateLimit-Reset` header is absent, defaults to 60s sleep.

### PAT masking for very short tokens

1. Run `pytest tests/test_github_auth.py::TestPatMasking::test_very_short_pat -v`
2. **Expected:** Tokens shorter than 8 chars get full masking (all asterisks).

### Assignee fallback to singular field

1. Run `pytest tests/test_github_field_mapper.py::TestGetAssigneeInfo::test_fallback_to_singular_assignee -v`
2. **Expected:** When `assignees` array is empty but `assignee` object exists, falls back to singular field.

### Slug determinism and uniqueness

1. Run `pytest tests/test_github_field_mapper.py::TestComputeIssueSlug -v`
2. **Expected:** 4 tests — same input produces same slug, different repos produce different slugs, different numbers produce different slugs, format is `gh-{16 hex chars}`.

## Failure Signals

- Any test failure in the 124-test suite indicates a broken contract
- `test_partial_failure_diagnostics` failure means the diagnostic surface (last_pull_result) is broken — S04 E2E won't be able to verify sync outcomes
- `test_creates_task_for_new_issue` failure means the two-phase bulk create pattern is broken
- `test_delta_sync_uses_since` failure means incremental sync won't work (full re-fetch every time)

## Requirements Proved By This UAT

- GH-01 (GitHub PAT auth) — PAT storage, verification via /user endpoint, masked preview, disconnect
- GH-02 (Pull sync: issues → bpkm:Task) — field mapping, two-phase bulk create, delta sync, PR filtering
- GH-06 (Person matching) — email-first + login-fallback resolution with LRU cache

## Not Proven By This UAT

- GH-03 (PR sync + issue linking) — deferred to S02
- GH-04 (Push sync) — deferred to S03
- GH-05 (Settings UI polish) — deferred to S03
- GH-07 (E2E tests + user guide) — deferred to S04
- Real runtime integration — all tests use mocked SDK clients. Docker + app platform integration verified by S04 E2E.

## Notes for Tester

- Tests load app modules via `importlib.util.spec_from_file_location` since `apps/` is outside `backend/`'s Python path. If import errors occur, check that `apps/github-sync/services/` files exist.
- The `_AsyncNoopMock` + `patch.object(gc.asyncio, "sleep")` pattern in test_github_client.py is needed because standard `patch("asyncio.sleep")` doesn't work with importlib-loaded modules.
- MockResponse uses `data if data is not None else {}` (not `data or {}`) — see knowledge entry about empty list falsy evaluation.
