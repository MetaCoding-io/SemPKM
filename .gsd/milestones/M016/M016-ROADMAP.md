# M016: Linear Sync App

**Vision:** First bidirectional task provider sync app on the SemPKM App Platform — connecting Linear issues to `bpkm:Task` objects with full field mapping, delta sync, change detection, and push-back.

## Success Criteria

- User authenticates with Linear (OAuth or API key), and the connection is verified in the app's settings page
- User selects a Linear team/project to sync, triggers poll, and issues appear as `bpkm:Task` objects in the workspace object browser within one poll cycle
- Synced tasks have correct status (Linear "In Progress" → bpkm:taskStatus "in-progress"), priority, assignee, labels, due dates, and external link
- User changes a task's status in SemPKM, triggers push, and the change appears in Linear
- Admin detail page shows sync run history with success/failure, object counts, and last sync time
- Unit tests cover all field mapping, normalization, IRI minting, change detection, and conflict resolution logic
- E2E Playwright test exercises install → configure → poll → verify against mocked Linear API
- User guide documents the Linear sync app setup, configuration, and sync behavior

## Key Risks / Unknowns

- **OAuth callback routing through app proxy** — The App Platform proxies `/app/{appId}/_fragments/*` to app processes. OAuth callbacks need a URL that Linear can redirect to and that the app can handle. API key auth is the fallback.
- **Token refresh lifecycle** — Linear access tokens expire after 24 hours with mandatory refresh tokens. The app must handle transparent token refresh without losing sync state.
- **Push-back loop prevention** — When the app pushes a change to Linear, the next poll sees that change as "updated." Without loop detection, the app re-imports its own changes.
- **Bulk EventStore for large initial sync** — Workspaces with thousands of issues need paginated queries and multi-batch bulk commits (1000-ops-per-batch limit).

## Proof Strategy

- OAuth callback routing → retire in S01 by proving OAuth code exchange through the app proxy returns a valid access token and `{ viewer { id name } }` query succeeds
- Token refresh lifecycle → retire in S01 by implementing refresh logic and proving 401 → refresh → retry flow works
- Push-back loop prevention → retire in S03 by implementing `lastSyncedAt` comparison and proving a pushed change is not re-imported on next poll
- Bulk EventStore for large sync → retire in S02 by syncing 50+ issues in a single poll with paginated GraphQL and bulk commits

## Verification Classes

- Contract verification: pytest unit tests for field mapping, IRI minting, status/priority normalization, change detection, conflict resolution, GraphQL query construction, pagination
- Integration verification: Playwright E2E test against Docker stack with mocked Linear API
- Operational verification: scheduled poll-tasks runs on interval, handles API errors gracefully, sync state persists across app restart
- UAT / human verification: manual OAuth flow with a real Linear workspace

## Milestone Definition of Done

This milestone is complete only when all are true:

- OAuth and API key auth both work end-to-end
- Pull sync creates/updates bpkm:Task objects with correct field mapping for all mappable fields
- Push sync detects changes to synced tasks and writes them back to Linear
- Settings page allows team/project selection, sync direction toggle, and poll interval configuration
- Admin detail page shows sync run history with counts and status
- Loop prevention verified: pushed changes are not re-imported
- Unit tests cover all pure logic (field mapping, normalization, IRI minting, change detection)
- E2E Playwright test covers install → configure → poll → verify task properties
- User guide Chapter 34 documents the full Linear sync workflow
- All SYNC requirements are validated or have documented gaps

## Requirement Coverage

- Covers: SYNC-01 (auth), SYNC-02 (pull sync), SYNC-03 (push sync), SYNC-04 (settings UI), SYNC-05 (admin sync history), SYNC-06 (person matching), SYNC-07 (provider icon/link)
- Partially covers: none
- Leaves for later: Linear comments sync, Linear webhooks (no platform external webhook routing), multiple workspace support
- Orphan risks: none

## Slices

- [x] **S01: OAuth + App Skeleton + Linear Client** `risk:high` `depends:[]`
  > After this: user installs Linear Sync app, authenticates via OAuth or API key, sees their Linear workspace name and team list on the settings page — proving the full auth flow and API connection through the App Platform
- [x] **S02: Pull Sync — Linear Issues to bpkm:Task** `risk:high` `depends:[S01]`
  > After this: user selects a Linear team/project, triggers poll, and sees issues appear as correctly-mapped bpkm:Task objects in the workspace object browser with status, priority, assignee, labels, due date, and external link
- [x] **S03: Push Sync + Settings Polish + Admin Detail** `risk:medium` `depends:[S02]`
  > After this: user edits a synced task's status in SemPKM and sees the change reflected in Linear; settings page has full sync controls; admin detail shows sync run history
- [x] **S04: E2E Tests + User Guide** `risk:low` `depends:[S03]`
  > After this: Playwright E2E test proves the install → configure → poll → verify flow against mocked Linear API; Chapter 34 documents the full Linear sync workflow with setup instructions

## Boundary Map

### S01 → S02

Produces:
- `apps/linear-sync/services/linear_client.py` — `LinearClient` class with authenticated GraphQL query execution, pagination, error handling, token refresh
- `apps/linear-sync/app.py` — App skeleton with OAuth callback route, connect settings fragment showing workspace info
- StateClient keys: `access_token`, `refresh_token`, `workspace_id`, `workspace_name`
- `apps/linear-sync/manifest.yaml` — manifest with `api.linear.app` network permission, command permissions for object.create/object.patch/body.set/edge.create

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `apps/linear-sync/services/field_mapper.py` — pure functions for Linear↔bpkm field mapping, status normalization, priority normalization
- `apps/linear-sync/services/sync_engine.py` — `pull_sync()` with IRI minting, delta sync cursor, bulk EventStore pipeline
- StateClient keys: `last_sync_at`, `sync_teams` (JSON list of selected team IDs)
- IRI mapping: Linear issue ID → SemPKM task IRI via deterministic `urn:sempkm:app:linear-sync:issue-{hash16}` pattern
- `apps/linear-sync/services/person_matcher.py` — email-based Person lookup/creation

Consumes:
- `LinearClient` from S01 for GraphQL queries
- StateClient token storage from S01 for authenticated API calls

### S03 → S04

Produces:
- `push_sync()` function in `sync_engine.py` — change detection, reverse field mapping, Linear mutation, loop prevention
- Settings page fragment with team/project multi-select, sync direction toggle, poll interval selector
- Admin detail fragment showing sync run history (timestamp, direction, counts, status)
- `poll-tasks` and `push-changes` scheduled task handlers in `app.py`

Consumes:
- `field_mapper.py` reverse mapping functions from S02
- `LinearClient` mutation methods from S01
- IRI mapping infrastructure from S02

### S04 (terminal)

Produces:
- `e2e/tests/26-linear-sync/linear-sync.spec.ts` — Playwright E2E test
- `docs/guide/34-linear-sync.md` — user guide chapter
- Updated `docs/guide/README.md` TOC and navigation chain

Consumes:
- All slices (S01–S03)
