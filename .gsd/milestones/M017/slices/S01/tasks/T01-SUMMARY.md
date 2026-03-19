---
id: T01
parent: S01
milestone: M017
provides:
  - GitHubClient REST client with Link-header pagination and rate-limit checking
  - GitHub-sync app scaffold (manifest, stub app.py, directory structure)
  - Exception hierarchy (GitHubAPIError, GitHubAuthError, GitHubRateLimitError)
key_files:
  - apps/github-sync/services/github_client.py
  - apps/github-sync/manifest.yaml
  - apps/github-sync/app.py
  - backend/tests/test_github_client.py
key_decisions: []
patterns_established:
  - Link-header pagination via regex on `Link` response header (not cursor-based)
  - SDK HttpClient.request() for REST calls (vs linear-sync's direct .post() for GraphQL)
  - _AsyncNoopMock + patch.object(gc.asyncio, "sleep") for testing async sleep calls in importlib-loaded modules
observability_surfaces:
  - Logger github_sync.client at DEBUG for REST requests, WARNING for rate-limit threshold
  - GitHubRateLimitError.retry_after exposes computed wait time for callers
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: App scaffold + manifest + GitHub REST client

**Created github-sync app directory structure, manifest, and GitHubClient REST client with Link-header pagination, rate-limit checking, and typed exception hierarchy — 31 unit tests passing.**

## What Happened

Built the `apps/github-sync/` directory structure mirroring linear-sync. The manifest declares permissions for `api.github.com` + `github.com` network access, commands (object.create/patch, body.set/diff, edge.create), SPARQL read, backgroundTasks, and two polling tasks (poll-tasks, push-changes at 15m intervals).

`GitHubClient` wraps the SDK `HttpClient` for authenticated REST calls. Key differences from the Linear client: REST (GET/PATCH) instead of GraphQL, `Authorization: token {pat}` header format, Link-header pagination instead of cursor-based, and proactive rate-limit checking via `X-RateLimit-Remaining` header with async sleep when remaining < 100.

The `_paginate()` method follows `Link: <url>; rel="next"` headers using a precompiled regex, up to 50 pages max. The `_parse_retry_after()` static method handles both `Retry-After` (seconds) and `X-RateLimit-Reset` (epoch timestamp) headers for computing wait times.

Stub `app.py` registers the app with SDK and provides startup/shutdown logging hooks. Full routes deferred to T03.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_client.py -v` — 31 tests pass
- `python3 -c "import yaml; yaml.safe_load(open('apps/github-sync/manifest.yaml'))"` — manifest parses successfully

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_github_client.py -v` | 0 | ✅ pass | 0.06s |
| 2 | `python3 -c "import yaml; yaml.safe_load(open('apps/github-sync/manifest.yaml'))"` | 0 | ✅ pass | <1s |

Slice-level partial: only `test_github_client.py` exists so far (31/80+ target). Other test files created in T02 and T03.

## Diagnostics

- **Logger `github_sync.client`**: DEBUG for each REST request (method + URL), WARNING for rate-limit threshold (remaining count + sleep duration).
- **Exception inspection**: `GitHubAPIError.status_code`, `.response_body`; `GitHubRateLimitError.retry_after` (seconds).
- **Test mock pattern**: `_AsyncNoopMock` class + `patch.object(gc.asyncio, "sleep", mock_sleep)` for testing async sleep in importlib-loaded modules — standard `patch("asyncio.sleep")` doesn't work because the module holds its own reference to the `asyncio` module.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/github-sync/manifest.yaml` — app manifest with permissions, tasks, frontend, UI pages
- `apps/github-sync/services/github_client.py` — REST client (~300 lines) with pagination, rate-limit, error hierarchy
- `apps/github-sync/services/__init__.py` — empty init
- `apps/github-sync/requirements.txt` — empty (SDK provides deps)
- `apps/github-sync/app.py` — minimal stub with startup/shutdown hooks
- `backend/tests/test_github_client.py` — 31 unit tests covering pagination, rate-limit, errors, convenience methods
- `.gsd/milestones/M017/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section
