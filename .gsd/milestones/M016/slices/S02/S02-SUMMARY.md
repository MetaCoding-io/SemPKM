---
id: S02
parent: M016
milestone: M016
provides:
  - "field_mapper.py: 6 pure functions for Linear→bpkm:Task property conversion (status, priority, labels, slug, properties, GraphQL query)"
  - "person_matcher.py: PersonMatcher class with SPARQL email lookup, command API person creation, and in-memory LRU cache"
  - "sync_engine.py: pull_sync(ctx) orchestrator with paginated GraphQL fetch, field mapping, SPARQL dedup, two-phase bulk create/update, delta cursor"
  - "poll-tasks handler in app.py wired to pull_sync(ctx)"
  - "81 unit tests across 3 test files covering all mapping, matching, and sync logic"
requires:
  - slice: S01
    provides: "LinearClient class with authenticated GraphQL queries, StateClient token storage, app.py skeleton with poll-tasks stub"
affects:
  - S03
key_files:
  - apps/linear-sync/services/field_mapper.py
  - apps/linear-sync/services/person_matcher.py
  - apps/linear-sync/services/sync_engine.py
  - apps/linear-sync/app.py
  - backend/tests/test_field_mapper.py
  - backend/tests/test_person_matcher.py
  - backend/tests/test_sync_engine.py
key_decisions:
  - "D204: Two-phase bulk creation — phase 1 creates tasks (platform mints IRI), phase 2 discovers IRIs via SPARQL then submits body.set/edge.create. All commands bypass SDK CommandClient via direct POST to /api/commands/bulk."
  - "body.set used uniformly for both new and existing task descriptions (no body.diff) — simpler and idempotent for v1"
  - "Case-insensitive PersonMatcher cache keying (email.lower()) to avoid duplicate SPARQL queries for mixed-case emails"
patterns_established:
  - "importlib path resolution in dependency order (field_mapper → person_matcher → linear_client → auth → sync_engine) with sys.modules registration for cross-module imports in test files"
  - "Full IRI keys for bpkm properties (urn:sempkm:model:basic-pkm:taskStatus, etc.) — compact form only for dcterms"
  - "StatefulGraph mock with call-count tracking for testing two-phase lookup patterns"
  - "MockGraphClient / MockCommandClient / MockHttpClient stubs for async SDK client testing"
observability_surfaces:
  - "Logger linear_sync.sync — INFO for sync start/complete with counts (created/updated/unchanged/errors), WARNING for per-issue failures"
  - "Logger linear_sync.person_matcher — DEBUG for cache hits and person creation"
  - "pull_sync() return dict: {status, created, updated, unchanged, errors} — structured result for callers"
  - "StateClient key last_sync_at — ISO timestamp of last successful sync"
drill_down_paths:
  - .gsd/milestones/M016/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M016/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M016/slices/S02/tasks/T03-SUMMARY.md
duration: ~57m (20m T01 + 12m T02 + 25m T03)
verification_result: passed
completed_at: 2026-03-18
---

# S02: Pull Sync — Linear Issues to bpkm:Task

**Built the complete pull sync pipeline — field mapping, person matching, and sync engine orchestrator — with 81 unit tests proving all Linear→bpkm:Task conversion logic, including paginated fetch, delta sync, bulk batching, trashed issue handling, and error isolation.**

## What Happened

Three tasks built the sync pipeline bottom-up:

**T01 (field mapper)** created 6 pure functions handling all Linear→bpkm:Task conversion: `normalize_status()` maps 5 Linear state types to bpkm statuses, `normalize_priority()` maps Linear 0-4 to bpkm priority strings, `map_labels_to_tags()` extracts label names, `compute_issue_slug()` generates deterministic SHA-256 slugs (`issue-{hash16}`), `build_task_properties()` assembles full property dicts with full IRI keys (omitting nulls, truncating datetimes to dates), and `build_issue_query()` produces GraphQL queries with optional updatedAfter filter for delta sync. Two separate query templates (with/without filter) chosen over dynamic string building for clarity. 49 tests.

**T02 (person matcher)** created `PersonMatcher` with a three-step resolution: check in-memory cache → SPARQL lookup by `foaf:mbox` or `crm:email` (case-insensitive) → create Person via `object.create` on miss. Cache keys are lowercased emails. When no display name is provided, the email local part is used for the slug and title. 12 tests.

**T03 (sync engine)** created `pull_sync(ctx)` orchestrating the full pipeline: auth check → read sync state (last_sync_at, sync_teams) → paginated GraphQL fetch via LinearClient → per-issue processing (slug computation, SPARQL dedup, property building, assignee resolution) → two-phase bulk submission → cursor update. New issues use a two-phase approach: phase 1 submits `object.create` commands (platform assigns IRI), phase 2 re-queries SPARQL to discover the minted IRIs and submits `body.set`/`edge.create`. Existing issues get all commands in a single batch. All commands bypass the SDK's `CommandClient` by posting directly to `/api/commands/bulk` via `ctx.commands._client` to avoid IRI prefix checking on platform-minted Task IRIs. Trashed issues are skipped on initial sync; previously-synced trashed issues get status set to cancelled. Commands batch at ≤1000 ops. Per-issue errors are isolated (don't abort the sync). 20 tests. The poll-tasks handler in `app.py` was wired to call `pull_sync(ctx)`.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py -v` — 49/49 passed
- `cd backend && .venv/bin/python -m pytest tests/test_person_matcher.py -v` — 12/12 passed
- `cd backend && .venv/bin/python -m pytest tests/test_sync_engine.py -v` — 20/20 passed
- `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py -v` — 81/81 passed (0.09s)
- `cd backend && .venv/bin/python -m pytest tests/test_sync_engine.py -v -k "error"` — 2/2 passed (error path coverage confirmed)
- All 3 source files pass `python3 -c "import ast; ast.parse(open(f).read())"` — syntax valid
- `app.py` confirmed wired: `from services.sync_engine import pull_sync` called in `poll_tasks` handler

## Requirements Advanced

- SYNC-02 (pull sync) — pull_sync() creates/updates bpkm:Task objects with correct field mapping for all mappable fields (status, priority, assignee, labels, due date, external link, effort, description). Contract-verified via 81 unit tests. Runtime integration deferred to S04 E2E test.

## Requirements Validated

- None — SYNC-02 needs runtime E2E proof (S04) to move from advanced to validated.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- **body.set instead of body.diff for existing tasks**: Plan mentioned `body.diff` for existing tasks with changed descriptions; implemented `body.set` uniformly. Fetching the old body from SPARQL to compute a diff would add complexity for marginal benefit in v1.
- **Simplified new_issue_assignees storage**: Plan suggested storing `{email, name}` dict for phase 2 assignee edge creation; simplified to storing the resolved Person IRI directly since PersonMatcher is already called during issue processing.
- **Test count exceeded target**: Plan estimated ~55+ tests; delivered 81 (49 + 12 + 20) due to thorough edge case coverage.

## Known Limitations

- **No runtime integration test**: All tests use mocked clients. Real GraphQL pagination, bulk command posting, and SPARQL dedup are proven structurally but not against the running platform. Deferred to S04 E2E test.
- **body.set only (no body.diff)**: Existing task descriptions are overwritten on every sync rather than diffed. Acceptable for v1 but wastes event store space for unchanged descriptions.
- **No push sync loop prevention**: pull_sync doesn't filter out changes that originated from a SemPKM push. S03 adds lastSyncedAt comparison for this.

## Follow-ups

- S03 needs `field_mapper.py` reverse mapping functions (bpkm→Linear) for push sync — the forward mapping constants established here can be inverted.
- S04 E2E test should verify real pagination against mocked Linear API with 50+ issues to retire the bulk batching risk.

## Files Created/Modified

- `apps/linear-sync/services/field_mapper.py` — 6 pure functions + constants for Linear→bpkm field mapping (~180 lines)
- `apps/linear-sync/services/person_matcher.py` — PersonMatcher class with SPARQL lookup, command creation, slugify, caching (~120 lines)
- `apps/linear-sync/services/sync_engine.py` — pull_sync() orchestrator with two-phase bulk, delta cursor, error isolation (~250 lines)
- `apps/linear-sync/app.py` — Modified poll-tasks handler to async, now calls pull_sync(ctx)
- `backend/tests/test_field_mapper.py` — 49 unit tests across 6 test classes (~250 lines)
- `backend/tests/test_person_matcher.py` — 12 unit tests with MockGraphClient and MockCommandClient
- `backend/tests/test_sync_engine.py` — 20 unit tests with MockStateClient, MockGraphClient, MockCommandClient, MockHttpClient, MockAppContext, StatefulGraph

## Forward Intelligence

### What the next slice should know
- The field mapper uses full IRI keys (`urn:sempkm:model:basic-pkm:taskStatus`) not compact form — reverse mapping for push sync must use the same convention.
- `compute_issue_slug(workspace_id, issue_id)` produces deterministic slugs — push sync can use the same function to find the Linear issue ID from a task's slug (though it's a one-way hash, so the issue_id should be stored as a property or in StateClient).
- The `_submit_commands_batched()` function in sync_engine.py can be reused for push sync bulk mutations.
- The importlib test loading pattern requires dependency-order loading with sys.modules registration — follow the chain in test_sync_engine.py.

### What's fragile
- The SDK bypass (`ctx.commands._client.post("/api/commands/bulk", ...)`) accesses a private attribute — if the SDK changes its internal httpx client structure, this breaks. Monitor SDK changes.
- The two-phase approach (create → SPARQL lookup → body/edge) has a timing assumption: the platform must have processed and materialized the created objects before the SPARQL lookup in phase 2. In tests this is mocked, but in production there could be a race if materialization is async.

### Authoritative diagnostics
- `pull_sync()` return dict `{status, created, updated, unchanged, errors}` — the most reliable signal for sync health. Check `status` first, then `errors` list for per-issue failures.
- `StateClient.get("last_sync_at")` — confirms when the last successful sync completed.
- Logger `linear_sync.sync` at INFO — logs fetch count and final result dict.

### What assumptions changed
- Plan assumed `body.diff` for existing tasks — changed to `body.set` for simplicity (no need to fetch old body content from SPARQL).
- Plan assumed storing assignee email+name for phase 2 — simplified to storing resolved Person IRI directly from PersonMatcher.
