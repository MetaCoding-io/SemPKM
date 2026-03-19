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

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v` — all pass
- All test files exist with ≥80 tests total

## Observability / Diagnostics

- Runtime signals: Logger `github_sync.client` at DEBUG for REST requests, INFO for rate-limit warnings. Logger `github_sync.sync` at INFO for sync start/complete with counts.
- Inspection surfaces: StateClient keys `last_pull_result` (JSON with status/created/updated/errors), `last_sync_at`
- Failure visibility: Per-issue error isolation with warning log + error count in last_pull_result
- Redaction constraints: PAT stored in StateClient, never logged

## Tasks

- [ ] **T01: App scaffold + manifest + GitHub REST client** `est:45m`
  - Why: Foundation — proves GitHub API access with pagination and rate limiting
  - Files: `apps/github-sync/manifest.yaml`, `apps/github-sync/app.py`, `apps/github-sync/services/__init__.py`, `apps/github-sync/services/github_client.py`, `apps/github-sync/requirements.txt`
  - Do: Clone linear-sync structure. GitHubClient using SDK HttpClient for REST calls. Implement `_paginate()` parsing Link headers for `rel="next"`. `fetch_repos()` for `/user/repos?type=all&sort=updated`. `fetch_issues()` for `/repos/{owner}/{repo}/issues?state=all&since={iso}&per_page=100`. Rate-limit checking via `X-RateLimit-Remaining` header with sleep when <100 remaining. Manifest with permissions for `api.github.com` network access, commands, sparql read, backgroundTasks. Empty requirements.txt (SDK provides httpx).
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_client.py -v`
  - Done when: GitHubClient pagination, rate-limit checking, and repo/issue fetch all unit-tested (~20 tests)

- [ ] **T02: PAT auth + field mapper + person matcher** `est:45m`
  - Why: Pure-function layer — maps GitHub JSON to bpkm:Task properties
  - Files: `apps/github-sync/services/auth.py`, `apps/github-sync/services/field_mapper.py`, `apps/github-sync/services/person_matcher.py`, `backend/tests/test_github_auth.py`, `backend/tests/test_github_field_mapper.py`, `backend/tests/test_github_person_matcher.py`
  - Do: Auth: store PAT via StateClient, verify via GET `/user`, connection status. Field mapper: `build_task_properties()` mapping title→dcterms:title, body passthrough, state open→todo/closed→done, state_reason not_planned→cancelled, labels→bpkm:tags, first assignee→bpkm:assignedTo, milestone.title→bpkm:taskProject, number→bpkm:externalId (as "#N"), html_url→bpkm:externalUrl, node_id→bpkm:externalUuid, externalProvider "github" (not "github-pr" — that's S02). `compute_issue_slug()`: SHA-256 of `repo_full_name + issue_number`, first 16 chars. PersonMatcher: copy from linear sync, adapt for GitHub username + email. No `build_issue_query()` needed (REST, not GraphQL) — instead `build_issue_patch()` for push sync (S03).
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py -v`
  - Done when: Field mapper covers all mappings (~35 tests), auth covers PAT storage/verify (~12 tests), person matcher covers lookup/create (~10 tests)

- [ ] **T03: Pull sync engine + app routes + templates** `est:45m`
  - Why: Wires everything together — user-facing sync flow
  - Files: `apps/github-sync/services/sync_engine.py`, `apps/github-sync/app.py`, `apps/github-sync/frontend/templates/connect.html`, `apps/github-sync/frontend/templates/connect_status.html`, `apps/github-sync/frontend/static/styles.css`, `backend/tests/test_github_sync_engine.py`
  - Do: pull_sync(): iterate selected repos, fetch_issues with since filter, skip PRs (issues with `pull_request` key — handled in S02), two-phase bulk create (D204: object.create → SPARQL discover IRI → body.set), update existing tasks via object.patch. Delta sync: use `since` param from last_sync_at StateClient key. App routes: POST connect/api-key, GET settings page, POST sync-now handler triggering pull_sync. Templates: connect.html with PAT input form, connect_status.html with repo selection checkboxes, sync now button, last sync stats. All htmx URLs prefixed with `/app/github-sync/` per knowledge entry.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -v` — sync engine tests pass (~20 tests)
  - Done when: pull_sync creates/updates tasks for a mocked repo, app routes handle connect and sync-now, templates render

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
