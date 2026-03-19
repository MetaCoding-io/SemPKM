# S01: GitHub Client + PAT Auth + Issue Pull Sync

**Goal:** Ship a working GitHub sync app that authenticates via PAT, fetches issues from selected repos, and creates/updates bpkm:Task objects with correct field mapping.

**Demo:** User installs github-sync from Admin > Applications, enters a GitHub PAT, selects repositories, clicks Sync Now, and issues appear as browsable Task objects with status, labels, assignee, body, and external link.

## Must-Haves

- GitHubClient with REST GET/PATCH, Link-header pagination, rate-limit header checking
- PAT auth flow (store via StateClient, verify via `/user` endpoint)
- Field mapper: issue → bpkm:Task properties (status, labels→tags, assignee, title, body, externalUrl, externalId, externalUuid)
- PersonMatcher for assignee resolution (reuse M016 pattern)
- pull_sync() with two-phase bulk create (D204 pattern), delta sync via `since` parameter
- App manifest, routes, templates (connect page, settings/status page)
- Repo selection settings (multi-select from `/user/repos`)
- ~80+ unit tests covering client, field mapper, auth, person matcher, sync engine

## Proof Level

- This slice proves: contract (all behavior verified via mocked unit tests; real runtime integration deferred to S04 E2E)
- Real runtime required: no (unit tests load modules via importlib, mock all HTTP/SDK calls)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v` — all pass, ≥80 tests total
- Diagnostic check: `test_github_sync_engine.py` includes at least one test asserting that `last_pull_result` StateClient key contains structured error info (error count, failed issue numbers) when individual issue processing fails — proving a future agent can inspect sync failure state without reading logs

## Observability / Diagnostics

- Runtime signals: Logger `github_sync.client` at DEBUG for REST requests, INFO for rate-limit warnings. Logger `github_sync.sync` at INFO for sync start/complete with counts.
- Inspection surfaces: StateClient keys `last_pull_result` (JSON with status/created/updated/errors/failed_issues), `last_sync_at` (ISO-8601 timestamp)
- Failure visibility: Per-issue error isolation — individual issue failures don't abort sync. `last_pull_result` records error count and list of failed issue numbers. Rate-limit exhaustion raises `GitHubRateLimitError` with `retry_after` seconds.
- Redaction constraints: PAT stored in StateClient, never logged. Only `ghp_****` prefix shown in connection status.

## Integration Closure

- Upstream surfaces consumed: SDK clients (commands, graph, http, state, settings) from `backend/sdk/sempkm_app_sdk/`, `models/basic-pkm/` bpkm:Task shape, app platform manifest loading and proxy routing
- New wiring introduced in this slice: `apps/github-sync/` directory with manifest, app module, service modules, templates, CSS. Mounted by app platform auto-discovery.
- What remains before the milestone is truly usable end-to-end: S02 (PR sync + linking), S03 (push sync + settings polish), S04 (E2E + docs)

## Tasks

- [x] **T01: App scaffold + manifest + GitHub REST client** `est:45m`
  - Why: Foundation — proves GitHub API access with pagination and rate limiting. Establishes the project structure that all subsequent tasks build on.
  - Files: `apps/github-sync/manifest.yaml`, `apps/github-sync/app.py` (stub), `apps/github-sync/services/__init__.py`, `apps/github-sync/services/github_client.py`, `apps/github-sync/requirements.txt`, `backend/tests/test_github_client.py`
  - Do: Clone linear-sync directory structure. Implement `GitHubClient` using SDK `HttpClient` for REST calls. `_paginate()` parses Link headers for `rel="next"` using simple split (D207). `fetch_repos()` for `/user/repos?type=all&sort=updated&per_page=100`. `fetch_issues()` for `/repos/{owner}/{repo}/issues?state=all&since={iso}&per_page=100`. Rate-limit checking via `X-RateLimit-Remaining` header with async sleep when <100 remaining. Exception hierarchy: `GitHubAPIError`, `GitHubAuthError`, `GitHubRateLimitError`. Manifest with permissions for `api.github.com` + `github.com` network access, commands, sparql read, backgroundTasks. Stub `app.py` (just enough for import). Empty `requirements.txt`.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_client.py -v`
  - Done when: GitHubClient pagination, rate-limit checking, fetch_repos, fetch_issues, error hierarchy all unit-tested (~20+ tests)

- [x] **T02: PAT auth + field mapper + person matcher** `est:45m`
  - Why: Pure-function layer — maps GitHub JSON to bpkm:Task properties and handles auth storage/verification. No orchestration, all side-effect-free (except auth StateClient interaction).
  - Files: `apps/github-sync/services/auth.py`, `apps/github-sync/services/field_mapper.py`, `apps/github-sync/services/person_matcher.py`, `backend/tests/test_github_auth.py`, `backend/tests/test_github_field_mapper.py`, `backend/tests/test_github_person_matcher.py`
  - Do: **Auth:** store PAT via StateClient `github_pat` key, verify via GET `/user`, `get_connection_status()` returns dict with connected/username/pat_preview (masked `ghp_****`). **Field mapper:** `build_task_properties()` — title→dcterms:title, state open→todo/closed→done, state_reason not_planned→cancelled, labels[]→bpkm:tags, first assignee login→bpkm:assignedTo (via PersonMatcher), milestone.title→bpkm:taskProject, number→bpkm:externalId as "#N", html_url→bpkm:externalUrl, node_id→bpkm:externalUuid, externalProvider "github". `compute_issue_slug()` via SHA-256 of `{repo_full_name}#{number}`, first 16 hex chars. **Person matcher:** near-verbatim copy from linear-sync adapted for GitHub `login` + `email` fields.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py -v`
  - Done when: ~55+ tests across three files: field mapper covers all mappings including edge cases (~35), auth covers PAT storage/verify/status (~12), person matcher covers lookup/create/cache (~10)

- [x] **T03: Pull sync engine + app routes + templates** `est:1h`
  - Why: Wires everything together — the user-facing sync flow from PAT entry through issue sync. Also provides the diagnostic `last_pull_result` surface that proves failure visibility.
  - Files: `apps/github-sync/services/sync_engine.py`, `apps/github-sync/app.py`, `apps/github-sync/frontend/templates/connect.html`, `apps/github-sync/frontend/templates/connect_status.html`, `apps/github-sync/frontend/static/styles.css`, `backend/tests/test_github_sync_engine.py`
  - Do: **Sync engine:** `pull_sync()` iterates selected repos from settings, calls `fetch_issues()` with `since` filter from `last_sync_at` StateClient key. Skips issues with `pull_request` key (deferred to S02). Two-phase bulk create per D204: Phase 1 `object.create` commands → Phase 2 SPARQL discover minted IRIs then `body.set` + `edge.create`. Existing tasks (found via SPARQL `STRENDS` on slug) get `object.patch` + conditional `body.diff`. Per-issue error isolation with try/except — failures logged and counted but don't abort sync. After completion, writes `last_pull_result` to StateClient (JSON: status, created_count, updated_count, skipped_count, error_count, failed_issues list, duration_ms). **App routes:** POST `/connect/api-key` stores PAT, GET `/settings` renders status page, POST `/sync-now` triggers `pull_sync`. Task handlers `poll-tasks` and `push-changes` (push-changes is stub for S03). All htmx URLs prefixed with `/app/github-sync/` per knowledge entry. **Templates:** `connect.html` with PAT input + connection status indicator. `connect_status.html` with repo checkboxes, sync now button, last sync stats panel (created/updated/errors, last sync time). **CSS:** clone from linear-sync `styles.css` with github-sync branding.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -v` — includes test for `last_pull_result` error reporting on partial failure
  - Done when: pull_sync creates/updates tasks from mocked repos, partial-failure error state recorded in StateClient, app routes handle connect/settings/sync-now, templates render. ~20+ sync engine tests.

## Files Likely Touched

- `apps/github-sync/manifest.yaml`
- `apps/github-sync/app.py`
- `apps/github-sync/requirements.txt`
- `apps/github-sync/services/__init__.py`
- `apps/github-sync/services/github_client.py`
- `apps/github-sync/services/auth.py`
- `apps/github-sync/services/field_mapper.py`
- `apps/github-sync/services/person_matcher.py`
- `apps/github-sync/services/sync_engine.py`
- `apps/github-sync/frontend/templates/connect.html`
- `apps/github-sync/frontend/templates/connect_status.html`
- `apps/github-sync/frontend/static/styles.css`
- `backend/tests/test_github_client.py`
- `backend/tests/test_github_field_mapper.py`
- `backend/tests/test_github_auth.py`
- `backend/tests/test_github_person_matcher.py`
- `backend/tests/test_github_sync_engine.py`
