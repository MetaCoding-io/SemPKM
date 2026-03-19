---
id: S01
parent: M017
milestone: M017
provides:
  - GitHubClient REST client with Link-header pagination, rate-limit checking, and typed exception hierarchy
  - PAT auth flow (store/verify/disconnect/connection_status) via StateClient
  - Pure field mapper (GitHub issue JSON → bpkm:Task properties, reverse mapping for push sync)
  - PersonMatcher with email-first + login-fallback SPARQL resolution and LRU cache
  - pull_sync() engine with two-phase bulk create (D204 pattern), delta sync, per-issue error isolation
  - App routes for connect/settings/sync-now/disconnect + task handlers (poll-tasks, push-changes stub)
  - Frontend templates (connect.html + connect_status.html) with repo selection and sync stats
  - last_pull_result structured diagnostic surface in StateClient
requires:
  - slice: none
    provides: first slice in M017
affects:
  - S02 (consumes GitHubClient, field_mapper, person_matcher, sync_engine, auth, app routes)
  - S03 (consumes build_issue_patch reverse mapping, sync_engine, app routes)
key_files:
  - apps/github-sync/manifest.yaml
  - apps/github-sync/app.py
  - apps/github-sync/services/github_client.py
  - apps/github-sync/services/auth.py
  - apps/github-sync/services/field_mapper.py
  - apps/github-sync/services/person_matcher.py
  - apps/github-sync/services/sync_engine.py
  - apps/github-sync/frontend/templates/connect.html
  - apps/github-sync/frontend/templates/connect_status.html
  - apps/github-sync/frontend/static/styles.css
  - backend/tests/test_github_client.py
  - backend/tests/test_github_field_mapper.py
  - backend/tests/test_github_auth.py
  - backend/tests/test_github_person_matcher.py
  - backend/tests/test_github_sync_engine.py
key_decisions:
  - D206 PAT-only auth (no OAuth App flow for v1)
  - D207 Manual Link header parsing (regex, no library)
  - GitHub state_reason used to refine closed→done vs closed→cancelled
  - ctx-based pull_sync API matching linear-sync pattern
  - MockResponse default data uses `data if data is not None else {}` (knowledge entry)
patterns_established:
  - REST client using SDK HttpClient.request() (vs linear-sync's direct .post() for GraphQL)
  - Link-header pagination via precompiled regex on response headers
  - PAT masking via _mask_pat() — first 4 + **** + last 4 chars
  - GitHub assignee resolution order — email → login → create new Person (differs from Linear email-only)
  - compute_issue_slug with "gh-" prefix + SHA-256 hash of "repo_full_name#number"
  - MockExternalHttpClient with ordered response queue for multi-step API flow testing
observability_surfaces:
  - StateClient key `last_pull_result` — JSON with status/created/updated/skipped/errors/failed_issues/duration_ms/timestamp
  - StateClient key `last_sync_at` — ISO-8601 timestamp for delta sync
  - Logger `github_sync.client` at DEBUG for REST requests, WARNING for rate-limit threshold
  - Logger `github_sync.auth` at INFO for store/verify/clear, WARNING on verification failure
  - Logger `github_sync.sync` at INFO for sync start/complete with counts
  - get_connection_status() returns structured dict with connected/username/pat_preview/error
  - GitHubRateLimitError.retry_after exposes computed wait time
drill_down_paths:
  - .gsd/milestones/M017/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M017/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M017/slices/S01/tasks/T03-SUMMARY.md
duration: 70m
verification_result: passed
completed_at: 2026-03-18
---

# S01: GitHub Client + PAT Auth + Issue Pull Sync

**Complete GitHub sync app foundation — REST client with Link-header pagination, PAT auth, field mapper (GitHub issues → bpkm:Task with status/labels/assignee/body), person matcher, and pull sync engine with two-phase bulk create and per-issue error isolation — 124 unit tests passing.**

## What Happened

Built the `apps/github-sync/` app in three tasks following the linear-sync reference pattern, adapted for GitHub's REST API.

**T01 (GitHubClient + scaffold):** Created the app directory structure mirroring linear-sync. `GitHubClient` wraps the SDK `HttpClient` for authenticated REST GET/PATCH calls. Key differentiator from Linear: REST instead of GraphQL, `Authorization: token {pat}` header, Link-header pagination via precompiled regex (up to 50 pages max), and proactive rate-limit checking via `X-RateLimit-Remaining` header with async sleep when remaining < 100. Exception hierarchy provides `GitHubAPIError`, `GitHubAuthError`, and `GitHubRateLimitError` with typed `retry_after` and `status_code` fields. Manifest declares permissions for `api.github.com` + `github.com` network, commands, SPARQL read, and two scheduled tasks.

**T02 (auth + field mapper + person matcher):** Three pure-ish service modules. Auth stores PAT via StateClient with masked preview (`ghp_****ab12`). Field mapper maps GitHub issue JSON to bpkm:Task properties: two-state model (open→todo, closed→done) refined by `state_reason` (not_planned→cancelled, completed→done, reopened→todo), labels→tags, first assignee IRI, milestone→project, external ID as "#N", node_id as externalUuid. Includes `build_issue_patch()` reverse mapping for S03 push sync and `is_pull_request()` for PR detection. Person matcher adapted from linear-sync with GitHub-specific login fallback: email match → login match (via bpkm:externalId) → create new Person.

**T03 (sync engine + app routes + templates):** Wired everything together. `pull_sync()` iterates selected repos from settings, fetches issues per-repo with delta sync `since` parameter, filters PRs, resolves assignees, maps properties, then does two-phase bulk create (object.create → SPARQL discover IRI → body.set). Existing tasks get object.patch + body.set for idempotent updates. Per-issue error isolation wraps each issue in try/except, recording failures in `failed_issues` list. Status degrades from "success" → "partial" → "error". All htmx URLs in templates use `/app/github-sync/` proxy prefix per knowledge entry.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v` — **124/124 passed in 0.15s**
- Test breakdown: 31 client + 42 field mapper + 15 auth + 10 person matcher + 26 sync engine
- Exceeds plan target of ≥80 tests (124 total)
- `test_partial_failure_diagnostics` confirms `last_pull_result` contains error count, failed_issues list, duration_ms, and timestamp — proving a future agent can inspect sync failure state without reading logs
- All htmx template URLs verified using `/app/github-sync/` prefix
- Manifest parses successfully via PyYAML

## Requirements Advanced

- GH-01 (GitHub PAT auth) — PAT store/verify/disconnect via StateClient, masked preview in connection status, verified by 15 auth tests
- GH-02 (Pull sync: issues → bpkm:Task) — Full pipeline from fetch through two-phase bulk create with delta sync, verified by 26 sync engine tests + 42 field mapper tests
- GH-06 (Person matching: assignee resolution) — Email-first + login-fallback SPARQL lookup with LRU cache, verified by 10 person matcher tests

## Requirements Validated

- None yet — runtime integration deferred to S04 E2E test. All S01 verification is contract-level (mocked unit tests).

## New Requirements Surfaced

- GH-01 (GitHub PAT auth) — active, covered by S01
- GH-02 (Pull sync: issues → bpkm:Task) — active, covered by S01
- GH-03 (Pull sync: PRs + issue linking) — active, covered by S02
- GH-04 (Push sync: SemPKM → GitHub) — active, covered by S03
- GH-05 (Settings UI: repo selection, sync direction, poll interval) — active, covered by S03
- GH-06 (Person matching: assignee resolution) — active, covered by S01
- GH-07 (E2E tests + user guide) — active, covered by S04

## Requirements Invalidated or Re-scoped

- None

## Deviations

- T03 used `pull_sync(ctx)` instead of explicit params — matches linear-sync AppContext convention and simplifies route/task handler integration.
- T03 used `body.set` instead of `body.diff` for existing issues — body.diff requires previous body content which isn't tracked. Simpler and correct for idempotent updates.
- T02 added `get_assignee_info()` fallback to singular `assignee` field (not just `assignees[]` list) for GitHub API robustness.
- Test count is 124 (vs planned ≥80) due to thorough edge case coverage.

## Known Limitations

- PR filtering skips all issues with `pull_request` key — PR sync deferred to S02.
- push-changes task handler is a stub — real push sync deferred to S03.
- No E2E runtime verification — all tests are mocked unit tests. Real runtime integration verified in S04.
- body.set used for all updates (no incremental diff) — simplification from plan.

## Follow-ups

- S02 needs to extend `pull_sync()` to handle PRs (remove the skip filter, add PR-specific field mapping and timeline API cross-reference link creation).
- S03 needs to implement `push_sync()` using `build_issue_patch()` reverse mapping already provided by field_mapper.py.
- S04 needs to build mock GitHub REST API server and E2E Playwright test.

## Files Created/Modified

- `apps/github-sync/manifest.yaml` — App manifest with permissions, tasks, frontend, UI pages
- `apps/github-sync/app.py` — Complete app routes (connect, repos, sync-now, disconnect) + task handlers
- `apps/github-sync/requirements.txt` — Empty (SDK provides deps)
- `apps/github-sync/services/__init__.py` — Empty init
- `apps/github-sync/services/github_client.py` — REST client (~300 lines) with pagination, rate-limit, error hierarchy
- `apps/github-sync/services/auth.py` — PAT auth functions (store, get, verify, disconnect, connection status, masking)
- `apps/github-sync/services/field_mapper.py` — Pure field mapping (~240 lines) with forward and reverse mapping, slug computation
- `apps/github-sync/services/person_matcher.py` — Person resolution (~150 lines) with email/login SPARQL lookup and LRU cache
- `apps/github-sync/services/sync_engine.py` — Pull sync engine (~280 lines) with two-phase bulk, delta sync, error isolation
- `apps/github-sync/frontend/templates/connect.html` — PAT input form with fine-grained token instructions
- `apps/github-sync/frontend/templates/connect_status.html` — Connected status with repo checkboxes, sync stats, disconnect
- `apps/github-sync/frontend/static/styles.css` — Scoped styles for github-sync settings UI
- `backend/tests/test_github_client.py` — 31 tests covering pagination, rate-limit, errors, convenience methods
- `backend/tests/test_github_field_mapper.py` — 42 tests covering slug, properties, PR detection, assignee, reverse mapping
- `backend/tests/test_github_auth.py` — 15 tests covering PAT storage, verification, status, masking, disconnect
- `backend/tests/test_github_person_matcher.py` — 10 tests covering email/login match, cache, creation, edge cases
- `backend/tests/test_github_sync_engine.py` — 26 tests covering find_existing, batching, pull_sync, PR filtering, error isolation, diagnostics

## Forward Intelligence

### What the next slice should know
- `pull_sync()` explicitly skips issues with `pull_request` key (line: `if is_pull_request(issue): skipped += 1; continue`). S02 needs to either remove this filter and add PR handling inline, or add a separate `pull_sync_prs()` function.
- `build_issue_patch()` reverse mapping already exists in field_mapper.py — S03 can use it directly for push sync.
- The `compute_issue_slug()` function uses "gh-" prefix to avoid collisions with linear-sync's slug format. S02 PR slugs should use a different prefix or the same "gh-" prefix (since repo_full_name#number is unique for both issues and PRs).
- Templates use hardcoded `/app/github-sync/` prefix in htmx URLs — this works but is fragile. S03 settings polish should consider a template variable.

### What's fragile
- `MockExternalHttpClient` response queue ordering — tests depend on exact request sequence. Adding a new API call in the middle of pull_sync will break existing test setups.
- `_submit_commands_batched()` uses direct HTTP POST to `/api/commands/bulk` bypassing SDK IRI prefix check (same pattern as D204 from linear-sync). If the SDK changes the prefix enforcement mechanism, this bypass needs updating.

### Authoritative diagnostics
- `StateClient key last_pull_result` — the single source of truth for sync outcomes. Contains status, counts, failed_issues list, duration_ms, and timestamp. This is what S04's E2E test should assert against.
- `get_connection_status()` — returns structured dict that templates render. Verify PAT connection by checking `connected: true` and `username` field.

### What assumptions changed
- Plan estimated ~400 lines for sync_engine.py — actual is ~280 lines because GitHub REST is simpler than Linear GraphQL pagination.
- Plan specified body.diff for existing issues — simplified to body.set because tracking previous body content adds complexity for marginal benefit.
- Test count significantly exceeded target (124 vs 80+) due to thorough edge case coverage.
