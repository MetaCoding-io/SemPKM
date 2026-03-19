---
id: T02
parent: S01
milestone: M017
provides:
  - PAT auth functions (store/get/verify/disconnect/connection_status) via StateClient
  - Pure field mapper (GitHub issue JSON → bpkm:Task properties, reverse mapping for push sync)
  - PersonMatcher with email-first SPARQL lookup, GitHub login fallback, LRU cache
key_files:
  - apps/github-sync/services/auth.py
  - apps/github-sync/services/field_mapper.py
  - apps/github-sync/services/person_matcher.py
  - backend/tests/test_github_field_mapper.py
  - backend/tests/test_github_auth.py
  - backend/tests/test_github_person_matcher.py
key_decisions:
  - GitHub state_reason used to refine closed→done vs closed→cancelled (STATE_REASON_MAP)
  - PersonMatcher uses login as bpkm:externalId for SPARQL fallback when GitHub user email is private
  - build_issue_patch() reverse maps status with state_reason (cancelled→not_planned, done→completed)
patterns_established:
  - PAT masking via _mask_pat(): first 4 + **** + last 4 chars, never raw token in logs or API responses
  - GitHub assignee resolution order: email → login → create new Person (differs from Linear which is email-only)
  - compute_issue_slug uses "gh-" prefix + SHA-256 hash of "repo_full_name#number" (16 hex chars)
observability_surfaces:
  - "Logger github_sync.auth: INFO on PAT store/clear/verify, WARNING on verification failure"
  - "Logger github_sync.person: DEBUG on cache hits and person creation"
  - "get_connection_status() returns structured dict with connected/username/pat_preview/error"
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: PAT auth + field mapper + person matcher

**Implemented PAT auth storage/verification, GitHub→bpkm field mapper with status/label/assignee mapping, and PersonMatcher with email-first + login-fallback SPARQL resolution — 67 tests passing.**

## What Happened

Built three service modules that sit between the T01 REST client and the T03 sync engine:

1. **auth.py** (~110 lines): PAT storage/retrieval via StateClient, verification through `github_client.verify_token()`, connection status with masked PAT preview (`ghp_****ab12`), and disconnect. Follows linear-sync auth pattern but simplified — no OAuth flow, just PAT.

2. **field_mapper.py** (~240 lines): Pure functions mapping GitHub issue JSON to bpkm:Task properties. Two-state model (open→todo, closed→done) refined by `state_reason` (not_planned→cancelled, completed→done, reopened→todo). Handles labels→tags, milestone→project, first assignee IRI passthrough, external ID as "#N". `build_issue_patch()` provides reverse mapping for S03 push sync. `is_pull_request()` detects PRs via `pull_request` key. `compute_issue_slug()` produces deterministic `gh-{hash16}` slugs.

3. **person_matcher.py** (~150 lines): Adapted from linear-sync with GitHub-specific login fallback. Lookup order: email match (foaf:mbox/crm:email), then login match (bpkm:externalId), then create new Person. In-memory cache keyed by email or `login:{username}`. Created persons include both email (when available) and login as externalId.

## Verification

- `pytest tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py -v` — 67/67 passed
- Test count confirmed: 67 (exceeds ≥55 requirement)
- Slice-level partial verification: `pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py -v` — 98/98 passed (T03's sync_engine tests not yet created)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py -v` | 0 | ✅ pass | 0.09s |
| 2 | `pytest --co -q tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py` (67 tests) | 0 | ✅ pass | 0.04s |
| 3 | `pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py -v` (slice partial) | 0 | ✅ pass | 0.11s |

## Diagnostics

- **auth.py**: `get_connection_status()` is the primary inspection surface — returns `{connected, username, pat_preview, error}`. Logger `github_sync.auth` at INFO for store/verify/clear, WARNING on verify failure.
- **field_mapper.py**: Fully pure — no runtime diagnostics. All mappings testable without mocks.
- **person_matcher.py**: Logger `github_sync.person` at DEBUG for cache hits and person creation. Cache is instance-scoped (reset per sync run). SPARQL queries are logged by the graph client at its own level.

## Deviations

- Added `get_assignee_info()` fallback to singular `assignee` field (not just `assignees[]` list) — GitHub API sometimes returns both; needed for robustness.
- Added `test_fallback_to_singular_assignee` test (5 assignee tests instead of planned 4).
- `build_issue_patch()` includes `state_reason` in reverse mapping (not just `state`) — needed for correct GitHub behavior when closing as "not planned".
- Test count is 67 vs planned ~57 (42 field mapper + 15 auth + 10 person matcher) due to additional edge case coverage.

## Known Issues

None.

## Files Created/Modified

- `apps/github-sync/services/auth.py` — PAT auth functions (store, get, verify, disconnect, connection status, masking)
- `apps/github-sync/services/field_mapper.py` — Pure field mapping (GitHub JSON → bpkm properties, reverse mapping, slug computation)
- `apps/github-sync/services/person_matcher.py` — Person resolution with email-first + login-fallback SPARQL lookup and LRU cache
- `backend/tests/test_github_field_mapper.py` — 42 tests covering slug, properties, PR detection, assignee info, reverse mapping, status maps
- `backend/tests/test_github_auth.py` — 15 tests covering PAT storage, verification, connection status, masking, disconnect
- `backend/tests/test_github_person_matcher.py` — 10 tests covering email/login match, cache, creation, edge cases
- `.gsd/milestones/M017/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
