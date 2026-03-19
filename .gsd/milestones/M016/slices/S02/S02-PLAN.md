# S02: Pull Sync — Linear Issues to bpkm:Task

**Goal:** `poll-tasks` handler fetches Linear issues via paginated GraphQL, maps all fields to `bpkm:Task` properties, creates/updates objects via bulk command API, and stores delta sync cursor — with full unit test coverage of all pure logic and orchestration.
**Demo:** User selects a Linear team, triggers poll, and sees issues appear as correctly-mapped `bpkm:Task` objects with status, priority, assignee, labels, due date, and external link.

## Must-Haves

- Field mapper: `normalize_status()`, `normalize_priority()`, `map_labels_to_tags()`, `build_task_properties()`, `build_issue_query()`, `compute_issue_slug()` — all pure functions
- Person matcher: email-based SPARQL lookup of `foaf:mbox`, create Person via command API on miss, in-memory cache per sync run
- Sync engine: `pull_sync(ctx)` orchestrating LinearClient pagination → field mapping → SPARQL existing-task lookup → create/update via bulk commands → delta cursor storage
- IRI prefix bypass: sync engine posts command payloads directly to `/api/commands/bulk` via `ctx.commands._client` (httpx) to bypass SDK client-side IRI prefix check for `object.patch`/`body.set`/`body.diff` on platform-minted Task IRIs
- Deterministic IRI slugs: `issue-{sha256(workspace_id + issue_id)[:16]}` for predictable Task IRIs
- Delta sync: `updatedAt` filter on GraphQL query, `last_sync_at` cursor stored in StateClient
- Bulk batching: chunk commands into ≤1000-op batches for large syncs
- Skip trashed issues; mark previously-synced trashed issues as cancelled
- Date truncation: Linear `xsd:dateTime` → `xsd:date` for `dueDate`/`completedDate`
- Unit tests: ~55+ tests across three test files covering all mapping, matching, and sync logic

## Proof Level

- This slice proves: contract (all sync logic unit-tested with mocked clients)
- Real runtime required: no (runtime integration deferred to S04 E2E test)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_field_mapper.py -v` — all field mapper tests pass (~30 tests)
- `cd backend && python -m pytest tests/test_person_matcher.py -v` — all person matcher tests pass (~10 tests)
- `cd backend && python -m pytest tests/test_sync_engine.py -v` — all sync engine tests pass (~20 tests)
- `cd backend && python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py -v` — full suite passes
- All three new source files pass `python3 -c "import ast; ast.parse(open(f).read())"`
- `apps/linear-sync/app.py` poll-tasks handler calls `pull_sync(ctx)` instead of noop

## Observability / Diagnostics

- Runtime signals: Logger `linear_sync.sync` — INFO for sync start/complete with counts (created/updated/unchanged/errors), WARNING on partial failures, DEBUG for per-issue processing
- Inspection surfaces: StateClient keys `last_sync_at` (ISO datetime of last successful sync), `sync_teams` (JSON list of team IDs); sync result dict returned from `pull_sync()` with counts
- Failure visibility: `pull_sync()` returns `{"status": "error", "message": ...}` on auth failure or API errors; per-issue errors accumulated in result `errors` list with issue ID and exception message
- Redaction constraints: No Linear API tokens in logs (they stay in StateClient); issue titles may contain user content but are only logged at DEBUG level

## Integration Closure

- Upstream surfaces consumed: `LinearClient` from `services/linear_client.py` (S01) for GraphQL queries; `StateClient` for token storage and sync cursor; `GraphClient` for SPARQL task lookups; `CommandClient._client` (httpx.AsyncClient) for direct bulk command posting
- New wiring introduced in this slice: `poll_tasks()` in `app.py` calls `pull_sync(ctx)` — the real sync entry point
- What remains before the milestone is truly usable end-to-end: S03 (push sync + settings UI for team selection + admin detail), S04 (E2E test + user guide)

## Tasks

- [ ] **T01: Build field mapper with full unit tests** `est:1h`
  - Why: Pure mapping functions are the foundation — everything else depends on correct status/priority normalization, property building, slug computation, and GraphQL query construction. Zero external dependencies, fully testable in isolation.
  - Files: `apps/linear-sync/services/field_mapper.py`, `backend/tests/test_field_mapper.py`
  - Do: Implement all six pure functions: `normalize_status()` (5 Linear state types → bpkm statuses), `normalize_priority()` (Linear 0-4 → bpkm enum or None), `map_labels_to_tags()` (extract label names), `build_task_properties()` (full properties dict with full IRIs as keys), `build_issue_query()` (GraphQL query + variables for paginated issue fetch with team/date filter), `compute_issue_slug()` (deterministic SHA-256 based slug). All property keys must use full IRIs (e.g. `urn:sempkm:model:basic-pkm:taskStatus`) not compact form. Date fields must truncate datetime to date-only. Empty/null values must be omitted from properties dict. Linear `estimate` maps to `effort` string.
  - Verify: `cd backend && python -m pytest tests/test_field_mapper.py -v` — ~30 tests pass
  - Done when: All 6 functions implemented, all normalization paths covered by tests, property dict uses full IRIs, dates truncated correctly

- [ ] **T02: Build person matcher with unit tests** `est:30m`
  - Why: Sync engine needs to resolve Linear assignees (email + display name) to Person IRIs. Person matcher encapsulates SPARQL lookup + command API creation + in-memory caching, keeping the sync engine focused on orchestration.
  - Files: `apps/linear-sync/services/person_matcher.py`, `backend/tests/test_person_matcher.py`
  - Do: Implement `PersonMatcher` class with `match_or_create(email, display_name) -> str | None` method. SPARQL query checks both `foaf:mbox` and `urn:sempkm:model:crm:email`. On miss: create `bpkm:Person` via command API with `dcterms:title` (display name) and `foaf:mbox` (email). Cache results in `_cache: dict[str, str]` (email → IRI) to avoid repeated queries in a single sync run. Return None if email is None/empty. The `object.create` command for Person goes through the SDK's `CommandClient` normally (no IRI prefix issue since `object.create` has no IRI field to check). Constructor takes `graph_client` and `command_client`.
  - Verify: `cd backend && python -m pytest tests/test_person_matcher.py -v` — ~10 tests pass
  - Done when: Person lookup works for both foaf:mbox and crm:email, creation on miss returns platform-minted IRI, cache prevents duplicate SPARQL queries, None email returns None

- [ ] **T03: Build sync engine, wire poll-tasks, and add unit tests** `est:1h30m`
  - Why: The sync engine is the core orchestrator that ties LinearClient, field mapper, person matcher, and bulk commands together. It must handle the IRI prefix bypass for patch/body commands on platform-minted IRIs, chunk bulk batches at 1000 ops, and manage the delta sync cursor. Wiring into poll-tasks completes the slice demo.
  - Files: `apps/linear-sync/services/sync_engine.py`, `backend/tests/test_sync_engine.py`, `apps/linear-sync/app.py`
  - Do: Implement `pull_sync(ctx)` that: (1) checks auth via `get_connection_status()`, (2) reads `last_sync_at` and `sync_teams` from StateClient, (3) builds GraphQL query via field mapper, (4) paginates via `LinearClient.query_paginated()`, (5) for each issue: compute slug → SPARQL check if task exists → build properties → create new or patch existing, (6) accumulate all commands and submit in ≤1000-op bulk batches directly via `ctx.commands._client.post("/api/commands/bulk", json=payload)` to bypass IRI prefix checking, (7) update `last_sync_at` on success. Handle assignee via `PersonMatcher` → `edge.create` for `bpkm:assignedTo`. Handle description as `body.set` (new) or `body.diff` (existing with changed description). Skip trashed issues on initial sync; update previously-synced trashed issues to status=cancelled. Modify `app.py` to import and call `pull_sync(ctx)` from the poll-tasks handler.
  - Verify: `cd backend && python -m pytest tests/test_sync_engine.py -v` — ~20 tests pass; `cd backend && python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py -v` — full suite passes
  - Done when: pull_sync creates tasks for new issues, patches changed tasks, skips unchanged, handles trashed issues, batches commands correctly, stores sync cursor, poll-tasks handler calls pull_sync

## Files Likely Touched

- `apps/linear-sync/services/field_mapper.py` (new)
- `apps/linear-sync/services/person_matcher.py` (new)
- `apps/linear-sync/services/sync_engine.py` (new)
- `apps/linear-sync/app.py` (modified — wire poll-tasks)
- `backend/tests/test_field_mapper.py` (new)
- `backend/tests/test_person_matcher.py` (new)
- `backend/tests/test_sync_engine.py` (new)
