# M019: Todoist Sync App

**Vision:** Fourth bidirectional sync app on the App Platform — Todoist tasks sync to bpkm:Task objects with correct priority mapping, labels-as-tags, project selection, and completion state via close/reopen endpoints.

## Success Criteria

- User installs Todoist Sync app, enters their API token, and connects successfully
- User selects Todoist projects, triggers sync, and sees tasks as bpkm:Task objects with correct titles, priorities (inverted 1→low, 4→critical), due dates, labels as tags, and external links
- User completes a task in SemPKM, and the corresponding Todoist task is closed via the close endpoint
- User reopens a task in SemPKM, and the corresponding Todoist task is reopened
- Settings UI allows project selection, sync direction toggle, poll interval, and Sync Now
- 150+ unit tests covering auth, client, field mapper, sync engine, and person matcher
- Mock Todoist API server passes self-test
- E2E Playwright test proves full lifecycle (structurally complete — may hit pre-existing subprocess issue)
- User guide Chapter 37 documents Todoist sync with field mapping tables

## Key Risks / Unknowns

- **Near-zero technical risk.** Todoist REST API v2 is simpler than all prior sync targets. No pagination, no complex auth, no GraphQL. The architecture is proven across three prior apps. The only novelty is the close/reopen endpoint pattern for completion state.
- **Pre-existing subprocess startup issue.** E2E tests for M016, M017, and M018 all hit the same subprocess 500 error. This is not a Todoist-specific risk — the E2E test will be structurally complete but may fail at the same point.

## Proof Strategy

- close/reopen endpoint pattern → retire in S02 by proving push_sync correctly branches on status change direction and calls POST /tasks/{id}/close or /tasks/{id}/reopen
- Priority inversion correctness → retire in S01 with explicit unit tests for all 4 levels mapping both directions

## Verification Classes

- Contract verification: pytest unit tests (auth, client, field_mapper, person_matcher, sync_engine) — 150+ tests, importlib loading from apps/todoist-sync/
- Integration verification: Mock Todoist API server with selftest, E2E Playwright test through Docker stack
- Operational verification: sync logger (INFO per pull/push, WARNING on errors), last_pull_result/last_push_result state keys, get_connection_status()
- UAT / human verification: none required — pattern is proven

## Milestone Definition of Done

This milestone is complete only when all are true:

- All three slices complete: auth+client+pull, push+settings, E2E+docs
- Todoist app installable from Admin > Applications
- PAT auth connects and verifies via GET /rest/v2/projects
- Pull sync creates bpkm:Task objects with all mapped fields
- Push sync closes/reopens tasks and updates fields
- Settings UI with project selection, direction, interval, Sync Now
- 150+ pytest unit tests pass in <3s
- Mock Todoist API server passes selftest
- Playwright E2E test structurally complete
- Chapter 37 user guide published with field mapping tables
- All TD requirements validated or documented with evidence

## Requirement Coverage

- Covers: TD-01 (PAT auth), TD-02 (pull sync), TD-03 (push sync), TD-04 (project selection), TD-05 (priority mapping), TD-06 (label→tag mapping), TD-07 (settings UI), TD-08 (E2E + user guide)
- Partially covers: none
- Leaves for later: none
- Orphan risks: Pre-existing app subprocess E2E issue (tracked across M016-M018, not Todoist-specific)

## Slices

- [x] **S01: Auth + Client + Pull Sync** `risk:medium` `depends:[]`
  > After this: user enters Todoist API token, connects, selects projects, triggers sync, and sees Todoist tasks as bpkm:Task objects with correct priorities, due dates, labels, and external links — proven by 100+ unit tests

- [x] **S02: Push Sync + Settings UI** `risk:low` `depends:[S01]`
  > After this: user can complete/reopen tasks bidirectionally, configure sync direction and poll interval, and trigger manual sync — proven by 50+ additional unit tests

- [x] **S03: E2E Tests + User Guide** `risk:low` `depends:[S01,S02]`
  > After this: mock Todoist API server passes selftest, Playwright E2E test covers full lifecycle, Chapter 37 user guide documents everything with field mapping tables

## Boundary Map

### S01 → S02

Produces:
- `apps/todoist-sync/services/auth.py` — store_token(), verify_token(), get_connection_status(), clear_credentials()
- `apps/todoist-sync/services/todoist_client.py` — TodoistClient with get_tasks(), get_projects(), get_labels()
- `apps/todoist-sync/services/field_mapper.py` — build_task_properties(), map_priority(), map_status() with bidirectional mapping dicts
- `apps/todoist-sync/services/person_matcher.py` — PersonMatcher with email-based SPARQL lookup
- `apps/todoist-sync/services/sync_engine.py` — pull_sync() function creating bpkm:Task objects
- `apps/todoist-sync/app.py` — route handlers for connect, disconnect, sync_now, project selection
- `apps/todoist-sync/frontend/templates/connect.html` — PAT input form
- `apps/todoist-sync/frontend/templates/connect_status.html` — connection status + project selection UI

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- push_sync() in sync_engine.py — detect changes, reverse map, close/reopen/update via TodoistClient
- TodoistClient.close_task(), reopen_task(), update_task(), create_task() methods
- Settings UI controls (sync direction, poll interval, push result stats) in connect_status.html
- push-changes task handler in app.py

Consumes:
- All S01 outputs (auth, client, field mapper, pull sync, route handlers, templates)

### S03 consumes all

Produces:
- `e2e/mock-todoist-api/server.py` — canned task/project/label responses, selftest
- `e2e/tests/37-todoist-sync/todoist-sync.spec.ts` — full lifecycle E2E test
- `docs/guide/37-todoist-sync.md` — Chapter 37 user guide
- Docker service wiring in docker-compose.test.yml

Consumes:
- All S01 + S02 outputs
