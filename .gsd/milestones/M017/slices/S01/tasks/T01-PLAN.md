---
estimated_steps: 6
estimated_files: 6
---

# T01: App scaffold + manifest + GitHub REST client

**Slice:** S01 — GitHub Client + PAT Auth + Issue Pull Sync
**Milestone:** M017

## Description

Create the `apps/github-sync/` directory structure, manifest, and the core `GitHubClient` class. The client wraps the SDK `HttpClient` for authenticated REST calls to `api.github.com`, implementing Link-header pagination (D207), rate-limit header checking with sleep, and typed exception hierarchy. This proves GitHub API access patterns work and provides the foundation for all subsequent tasks.

The reference implementation is `apps/linear-sync/services/linear_client.py` (395 lines). The GitHub equivalent is simpler (REST instead of GraphQL) but adds Link-header pagination instead of cursor-based.

## Steps

1. **Create directory structure:**
   - `apps/github-sync/services/__init__.py` (empty)
   - `apps/github-sync/requirements.txt` (empty — SDK provides httpx)
   - Copy `apps/linear-sync/manifest.yaml` → adapt for github-sync

2. **Write `apps/github-sync/manifest.yaml`:**
   - `appId: "github-sync"`, name "GitHub Sync", version "0.1.0"
   - `permissions.commands`: `["object.create", "object.patch", "body.set", "body.diff", "edge.create"]`
   - `permissions.sparql.read: true`, `permissions.backgroundTasks: true`
   - `permissions.network`: `["api.github.com", "github.com"]`
   - `backend.entrypoint: "app:github_sync_app"`
   - Tasks: `poll-tasks` (15m) and `push-changes` (15m), same retry policy as linear
   - Frontend: `staticDir: "frontend/static"`, css: `["styles.css"]`
   - UI pages: settings page at `/settings`, label "GitHub Sync", icon "github", nav "apps", fragment "connect"

3. **Write `apps/github-sync/services/github_client.py`:**
   - Read `apps/linear-sync/services/linear_client.py` for structure reference
   - Constants: `GITHUB_API_URL = os.environ.get("GITHUB_API_URL", "https://api.github.com")`, `MAX_PAGINATION_PAGES = 50`
   - Exception hierarchy: `GitHubAPIError(message, status_code, response_body)`, `GitHubAuthError(GitHubAPIError)`, `GitHubRateLimitError(GitHubAPIError)` with `retry_after` attribute parsed from `X-RateLimit-Reset` (convert epoch → seconds until reset)
   - `GitHubClient.__init__(self, http_client, state_client)` — stores references
   - `async def _get_token(self)` — reads PAT from `state_client.get("github_pat")`
   - `async def _request(self, method, url, **kwargs)` — builds headers (`Authorization: token {pat}`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`), executes request via `http_client.request()`, handles 401→GitHubAuthError, 403/429→GitHubRateLimitError (parse `Retry-After` or `X-RateLimit-Reset`), other 4xx/5xx→GitHubAPIError
   - `async def _check_rate_limit(self, response_headers)` — reads `X-RateLimit-Remaining`, if < 100, calculates sleep time from `X-RateLimit-Reset` epoch, logs warning, `await asyncio.sleep()`
   - `async def _paginate(self, url, params=None)` — yields pages by following `Link: <url>; rel="next"` header. Parse via splitting on `,` then matching `rel="next"`. Max `MAX_PAGINATION_PAGES` iterations. Calls `_check_rate_limit()` after each page.
   - `async def fetch_repos(self)` — `_paginate("/user/repos", params={"type": "all", "sort": "updated", "per_page": 100})`, returns flat list of repo dicts
   - `async def fetch_issues(self, owner, repo, since=None)` — `_paginate(f"/repos/{owner}/{repo}/issues", params={"state": "all", "sort": "updated", "direction": "asc", "per_page": 100, **({"since": since} if since else {})})`, returns flat list of issue dicts
   - `async def verify_token(self)` — GET `/user`, returns user dict or raises GitHubAuthError
   - `async def patch_issue(self, owner, repo, issue_number, data)` — PATCH `/repos/{owner}/{repo}/issues/{issue_number}` with JSON body, for push sync (S03)

4. **Write stub `apps/github-sync/app.py`:**
   - Minimal file that imports App from SDK, creates `github_sync_app = App()`, registers empty routes. Just enough for the manifest `entrypoint` to resolve. Full routes come in T03.

5. **Write `backend/tests/test_github_client.py`:**
   - Use importlib pattern from `backend/tests/test_linear_client.py` (load module from apps dir)
   - Mock `http_client.request()` returning httpx-like response objects (status_code, json(), headers, text)
   - Test groups:
     - **Link-header pagination** (~5 tests): single page (no Link header), multi-page (3 pages), max pages guard, empty results, malformed Link header
     - **Rate-limit checking** (~4 tests): remaining > 100 (no sleep), remaining < 100 (sleep called), zero remaining, missing headers (no error)
     - **fetch_repos** (~3 tests): returns flat list, pagination works, auth error
     - **fetch_issues** (~4 tests): basic fetch, `since` parameter passed, empty repo, skips PR filter (client returns all — filtering is sync engine's job)
     - **Error handling** (~5 tests): 401→GitHubAuthError, 403→GitHubRateLimitError, 429→GitHubRateLimitError with retry_after, 500→GitHubAPIError, verify_token success/failure
     - **patch_issue** (~2 tests): success, error

6. **Verify:**
   - `cd backend && .venv/bin/python -m pytest tests/test_github_client.py -v` — all pass

## Must-Haves

- [ ] `apps/github-sync/manifest.yaml` exists with correct permissions, tasks, UI pages
- [ ] `GitHubClient` implements `_paginate()` with Link-header parsing (not cursor-based)
- [ ] Rate-limit checking reads `X-RateLimit-Remaining` and sleeps when low
- [ ] Exception hierarchy: `GitHubAPIError`, `GitHubAuthError`, `GitHubRateLimitError`
- [ ] `fetch_repos()`, `fetch_issues()`, `verify_token()`, `patch_issue()` methods exist
- [ ] ~20+ unit tests pass covering pagination, rate limiting, error handling

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_client.py -v` — all tests pass
- `python3 -c "import yaml; yaml.safe_load(open('apps/github-sync/manifest.yaml'))"` — manifest parses

## Inputs

- `apps/linear-sync/manifest.yaml` — reference manifest structure (adapt for github)
- `apps/linear-sync/services/linear_client.py` — reference client (adapt GraphQL→REST, cursor→Link-header)
- `backend/tests/test_linear_client.py` — reference test structure (importlib loading, mock patterns)
- `.gsd/milestones/M017/M017-RESEARCH.md` — GitHub API specifics (endpoints, headers, pagination format)

## Expected Output

- `apps/github-sync/manifest.yaml` — complete app manifest
- `apps/github-sync/services/github_client.py` — REST client with pagination and rate limiting (~250 lines)
- `apps/github-sync/services/__init__.py` — empty init
- `apps/github-sync/requirements.txt` — empty (SDK provides deps)
- `apps/github-sync/app.py` — minimal stub
- `backend/tests/test_github_client.py` — 20+ passing tests
