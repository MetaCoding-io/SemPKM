# M017: GitHub Issues Sync App

**Vision:** Bidirectional sync between GitHub Issues/PRs and bpkm:Task objects on the App Platform — mapping issues to tasks, PRs to tasks with provider distinction, PR-to-issue edges, label-based tags, assignee resolution, and push-back for status/title changes.

## Success Criteria

- User installs the GitHub sync app from Admin > Applications and configures a Personal Access Token
- User selects repositories to sync and triggers a poll
- GitHub issues appear as bpkm:Task objects with correct status (open→todo, closed→done), labels as tags, first assignee mapped to Person, external URL and ID preserved
- GitHub PRs appear as separate bpkm:Task objects with `externalProvider: "github-pr"` distinction
- PRs that reference issues (via "Closes #42" etc.) have edges linking PR task → Issue task
- User edits a task title/status in SemPKM, triggers push, and the change appears in GitHub
- Pushed changes are not re-imported on next pull (loop prevention)
- E2E Playwright test covers the full install → configure → sync → verify → push → cleanup lifecycle
- User guide Chapter 35 documents the GitHub sync workflow

## Key Risks / Unknowns

- **PR-to-issue linking via timeline API** — The timeline events endpoint (`GET /repos/{owner}/{repo}/issues/{number}/timeline`) returns `cross-referenced` events, but this is a less commonly used GitHub API. Pagination, event filtering, and rate-limit impact on large repos are unknowns.
- **REST pagination via Link headers** — Different from Linear's cursor-based GraphQL pagination. Need to parse RFC 8288 Link headers correctly for all paginated endpoints.

## Proof Strategy

- PR-to-issue linking → retire in S02 by proving timeline API returns cross-referenced events and edges are created between PR tasks and issue tasks
- REST pagination → retire in S01 by proving paginated issue fetch works for repos with >30 issues (default page size)

## Verification Classes

- Contract verification: Unit tests for field mapping, client pagination, person matching, sync logic, push sync — targeting ~150+ tests following M016 pattern
- Integration verification: E2E Playwright test against mock GitHub REST API server in Docker
- Operational verification: Rate-limit header checking with backoff, delta sync via `since` parameter
- UAT / human verification: none required — E2E test covers the user-visible flow

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 4 slices marked `[x]` in this roadmap
- All 4 slice summaries exist
- GitHub issues sync as bpkm:Task objects with correct field mapping (status, labels, assignee, URL, body)
- GitHub PRs sync as bpkm:Task objects with `externalProvider: "github-pr"`
- PR-to-issue edges exist for cross-referenced PRs
- Push sync writes status/title changes back to GitHub
- Loop prevention prevents re-import of pushed changes
- Mock GitHub REST API server passes selftest
- E2E Playwright test passes against Docker test stack
- User guide Chapter 35 committed with field mapping tables
- Unit test count ≥150, all passing
- GH-01 through GH-07 requirements validated or documented

## Requirement Coverage

New requirements (registered during this milestone):

- **GH-01** (GitHub PAT auth) → S01
- **GH-02** (Pull sync: issues → bpkm:Task) → S01
- **GH-03** (Pull sync: PRs + issue linking) → S02
- **GH-04** (Push sync: SemPKM → GitHub) → S03
- **GH-05** (Settings UI: repo selection, sync direction, poll interval) → S03
- **GH-06** (Person matching: assignee resolution) → S01
- **GH-07** (E2E tests + user guide) → S04

Reuses validated patterns from M016: SYNC-01 through SYNC-07 patterns (OAuth/API key pattern, pull/push sync, field mapping, person matching, settings UI, admin history, provider attribution).

Leaves for later: GitHub OAuth App flow (PAT-only for v1, same as M016's API key path), webhook endpoint (polling-only per D200 rationale), GitHub milestone → bpkm:Milestone mapping (deferred to keep scope focused on issues/PRs).

## Slices

- [x] **S01: GitHub Client + PAT Auth + Issue Pull Sync** `risk:high` `depends:[]`
  > After this: User installs the GitHub sync app, enters a PAT, selects repos, clicks Sync Now, and GitHub issues appear as bpkm:Task objects with correct status, labels, assignee, and external link. Verified by unit tests (~80+) covering client, field mapping, auth, person matching, and sync engine.

- [ ] **S02: PR Pull Sync + PR-to-Issue Edge Linking** `risk:medium` `depends:[S01]`
  > After this: GitHub PRs appear as bpkm:Task objects with `externalProvider: "github-pr"`. PRs that reference issues have edges linking them. Timeline API cross-referenced events are parsed and edge-created. Verified by unit tests (~30+) covering PR detection, timeline parsing, and edge creation.

- [ ] **S03: Push Sync + Settings Polish** `risk:low` `depends:[S01]`
  > After this: User edits task status/title in SemPKM, triggers push, and changes appear in GitHub via PATCH API. Loop prevention via `lastSyncedAt` comparison. Settings page has repo selection, sync direction, poll interval, Sync Now, and sync stats. Verified by unit tests (~40+) covering reverse mapping, push logic, and loop prevention.

- [ ] **S04: E2E Tests + User Guide** `risk:low` `depends:[S01,S02,S03]`
  > After this: Mock GitHub REST API server runs in Docker alongside test stack. Playwright E2E test covers full install → configure → sync → verify → push → cleanup lifecycle (~12 phases). Chapter 35 user guide documents GitHub sync with field mapping tables and troubleshooting.

## Boundary Map

### S01 → S02

Produces:
- `apps/github-sync/services/github_client.py` — `GitHubClient` class with REST GET/PATCH, Link-header pagination, rate-limit checking, `fetch_issues()`, `fetch_repos()`
- `apps/github-sync/services/field_mapper.py` — `build_task_properties()`, `compute_issue_slug()`, status/label/assignee mapping functions
- `apps/github-sync/services/person_matcher.py` — `PersonMatcher` class (near-verbatim from Linear sync)
- `apps/github-sync/services/sync_engine.py` — `pull_sync()` with two-phase bulk create, delta sync via `since` parameter
- `apps/github-sync/services/auth.py` — PAT storage/verification via StateClient
- `apps/github-sync/app.py` — App routes: connect, settings, sync handler
- `apps/github-sync/manifest.yaml` — App manifest with permissions, tasks, UI pages

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- Same as S01 → S02 (GitHubClient, field_mapper, sync_engine, auth, app routes)
- `build_task_properties()` forward mapping functions reusable for reverse mapping reference

Consumes:
- nothing (first slice)

### S02 → S04

Produces:
- `pull_sync()` extended with PR detection (via `pull_request` key) and `sync_pr_links()` using timeline API
- Edge creation between PR tasks and issue tasks via `bpkm:closesIssue` or `bpkm:dependsOn`

### S03 → S04

Produces:
- `push_sync()` with SPARQL change detection, reverse field mapping, GitHub PATCH mutations, loop prevention
- Settings POST routes for repo selection, sync direction, poll interval
- `connect_status.html` template with full settings control panel and sync stats

### S04 (terminal)

Produces:
- `e2e/mock-github-api/server.py` — Mock GitHub REST API server with canned responses
- `e2e/tests/32-github-sync/github-sync.spec.ts` — Playwright E2E spec (~12 phases)
- `docs/guide/35-github-sync.md` — Chapter 35 user guide
- `docker-compose.test.yml` updates for mock-github service
