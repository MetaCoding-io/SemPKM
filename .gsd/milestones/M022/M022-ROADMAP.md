# M022: Asana Sync App

**Vision:** Seventh bidirectional sync app on the App Platform — maps Asana tasks to bpkm:Task objects with configurable field mapping for status/priority via custom fields or sections, establishing the "configure before sync" pattern for custom-field-heavy providers.

## Success Criteria

- User installs Asana Sync from Admin > Applications and authenticates via OAuth 2.0 (with PAT fallback)
- User selects workspaces and projects to sync
- User configures status mapping (custom enum field or section names → bpkm:taskStatus)
- User configures priority mapping (custom enum field → bpkm:priority)
- Asana tasks appear as bpkm:Task objects with correct field transforms including subtask nesting up to 5 levels
- Asana tags appear as SemPKM tags, followers mapped to Person objects
- Editing task status/priority in SemPKM pushes back to Asana via reverse field mapping
- 200+ unit tests pass in <2s
- Mock Asana REST API server passes selftest
- Playwright E2E test exercises full install → configure → sync → push lifecycle
- Chapter 40 user guide documents Asana setup, field mapping configuration, and troubleshooting

## Key Risks / Unknowns

- **Configurable field mapping UI** — New UX pattern not present in any prior sync app. User must discover custom fields, map enum values to bpkm status/priority, and persist configuration before sync can run. This is the novel, highest-risk piece.
- **Subtask recursion depth vs rate limits** — 5 levels × many parents could hit Asana's cost-based rate limit (~1500 units/min). Need bounded recursion with backoff.
- **Section-based status mapping** — Moving a task between sections requires `POST /sections/{gid}/addTask` (not a field PATCH), which is a different push pattern than prior sync apps.

## Proof Strategy

- **Configurable field mapping UI** → retire in S01 by building the complete discovery + mapping + persistence flow with unit tests proving round-trip configuration before any sync code runs
- **Subtask recursion** → retire in S02 by implementing depth-bounded recursion with per-level opt_fields and testing with mock nested subtask data
- **Section-based push** → retire in S03 by implementing section move API alongside custom field PATCH for push sync

## Verification Classes

- Contract verification: pytest unit tests (200+ across 5-6 test files) covering auth, client, field mapper, sync engine, person matcher
- Integration verification: Mock Asana REST API server with selftest, Playwright E2E test against Docker stack
- Operational verification: Rate limit backoff on 429, subtask depth limiting, per-task error isolation
- UAT / human verification: none (established sync app pattern)

## Milestone Definition of Done

This milestone is complete only when all are true:

- OAuth 2.0 + PAT auth both work with connection test
- Workspace/project selection persists and drives sync scope
- Custom field discovery returns real field metadata from selected projects
- Status mapping (custom field or section-based) configures and persists correctly
- Priority mapping configures and persists correctly
- Pull sync creates bpkm:Task objects with all mapped fields including subtask nesting
- Push sync reverses field mapping including section-based status moves
- 200+ unit tests pass
- Mock Asana REST API server selftest passes
- Playwright E2E test exercises full lifecycle
- Chapter 40 user guide published with field mapping walkthrough
- README TOC, glossary, appendix A, navigation chain updated
- All ASANA requirements validated

## Requirement Coverage

- Covers: ASANA-01, ASANA-02, ASANA-03, ASANA-04, ASANA-05, ASANA-06, ASANA-07, ASANA-08, ASANA-09, ASANA-10, ASANA-11
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices

- [x] **S01: OAuth + project selection + custom field mapping UI** `risk:high` `depends:[]`
  > After this: User installs Asana Sync, authenticates via OAuth/PAT, selects workspace/projects, discovers custom fields, and configures status/priority mapping with persisted configuration. No sync yet — but the novel "configure before sync" pattern is proven end-to-end with unit tests.

- [x] **S02: Pull sync with configurable field transforms + subtask nesting** `risk:medium` `depends:[S01]`
  > After this: User triggers sync and Asana tasks (including subtasks up to 5 levels, tags, assignees) appear as bpkm:Task objects with status/priority mapped via the S01-configured field mapping.

- [x] **S03: Push sync + section-based status moves** `risk:medium` `depends:[S02]`
  > After this: User edits task status/priority in SemPKM, triggers push, and changes appear in Asana via reverse field mapping — including section moves for section-based status configuration.

- [x] **S04: E2E tests + mock server + user guide** `risk:low` `depends:[S01,S02,S03]`
  > After this: Mock Asana REST API server passes selftest, Playwright E2E test exercises full lifecycle, Chapter 40 user guide documents Asana setup including field mapping walkthrough. README/glossary/nav-chain updated.

## Boundary Map

### S01 → S02

Produces:
- `apps/asana-sync/services/auth.py` — OAuth 2.0 + PAT auth with token storage/refresh/status
- `apps/asana-sync/services/asana_client.py` — REST client with opt_fields, pagination, rate limit backoff
- `apps/asana-sync/app.py` — route handlers for OAuth, workspace/project selection, field mapping config
- `apps/asana-sync/manifest.yaml` — appId "asana-sync", network permissions, OAuth config
- `apps/asana-sync/frontend/templates/connect.html` — OAuth/PAT connect form
- `apps/asana-sync/frontend/templates/connect_status.html` — project selection + field mapping UI
- StateClient persisted configuration: `selected_projects`, `status_source`, `status_field_gid`, `status_mapping`, `priority_field_gid`, `priority_mapping`, `story_points_field_gid`
- `backend/tests/test_asana_auth.py` — auth unit tests
- `backend/tests/test_asana_client.py` — client unit tests with opt_fields/pagination/rate-limit coverage

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `apps/asana-sync/services/field_mapper.py` — configurable status/priority transforms reading from StateClient config, section-based mapping, subtask parent linking, tag/follower mapping, milestone detection
- `apps/asana-sync/services/sync_engine.py` — pull_sync() with two-phase bulk create, subtask recursion (bounded at 5 levels), per-task error isolation
- `apps/asana-sync/services/person_matcher.py` — SPARQL email lookup with create-on-miss and LRU cache
- `backend/tests/test_asana_field_mapper.py` — field mapper unit tests (configurable transforms)
- `backend/tests/test_asana_sync_engine.py` — sync engine pull tests
- `backend/tests/test_asana_person_matcher.py` — person matcher tests

Consumes:
- S01 auth, client, app shell, persisted field mapping configuration

### S03 → S04

Produces:
- Push sync in `sync_engine.py` — SPARQL change detection, reverse mapping, Asana PATCH + section move API
- push_sync tests added to `test_asana_sync_engine.py`
- Settings UI with sync direction, poll interval, Sync Now, sync stats

Consumes:
- S01 auth/client/config, S02 field mapper/sync engine/person matcher

### S04 (final)

Produces:
- `e2e/mocks/asana/server.py` — mock Asana REST API server with selftest
- `e2e/tests/40-asana-sync/asana-sync.spec.ts` — Playwright E2E test
- `docs/guide/40-asana-sync.md` — Chapter 40 user guide
- README TOC, glossary, appendix A, navigation chain updates

Consumes:
- S01-S03 complete app (auth, client, field mapper, sync engine, person matcher, push, settings)
