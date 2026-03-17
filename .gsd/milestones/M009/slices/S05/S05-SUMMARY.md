---
id: S05
parent: M009
milestone: M009
provides:
  - AppScheduler with periodic tick loop, concurrency guard, exponential backoff retry, and DB recording
  - parse_interval_seconds() for shorthand and ISO 8601 interval conversion
  - Admin task history section with interval adjustment and pause/resume controls
  - SDK CommandClient permission enforcement (command whitelist + recursive IRI prefix scanning)
  - SDK GraphClient sparql_read gating
  - SDK HttpClient domain enforcement (fnmatch glob matching with port stripping)
  - AppContext manifest-to-client permissions wiring
  - EventStore.commit_bulk() with summary-only metadata (~10 triples per batch)
  - POST /api/commands/bulk endpoint for batch command execution
  - SDK CommandClient.bulk() async context manager
  - browserVisible field on ManifestIconDef with get_hidden_types() and object browser filtering
requires:
  - slice: S02
    provides: SDK client stubs (CommandClient, GraphClient, HttpClient, StateClient, AppContext), AppProxy, JWT tokens
affects:
  - S06
  - S07
key_files:
  - backend/app/apps/scheduler.py
  - backend/app/apps/admin_router.py
  - backend/app/templates/admin/apps/detail.html
  - backend/app/main.py
  - backend/sdk/sempkm_app_sdk/clients/commands.py
  - backend/sdk/sempkm_app_sdk/clients/graph.py
  - backend/sdk/sempkm_app_sdk/clients/http.py
  - backend/sdk/sempkm_app_sdk/context.py
  - backend/app/events/store.py
  - backend/app/events/models.py
  - backend/app/commands/router.py
  - backend/app/models/manifest.py
  - backend/app/browser/_helpers.py
  - backend/app/browser/workspace.py
  - backend/tests/test_app_scheduler.py
  - backend/tests/test_app_permissions.py
  - backend/tests/test_bulk_eventstore.py
  - backend/tests/test_browser_visible.py
key_decisions:
  - D147 — IRI prefix validation uses heuristic string matching (urn:/http:// prefixes), not full IRI parsing
  - D148 — Scheduler invokes tasks via direct httpx-over-UDS, not AppProxy.forward() (avoids Request fabrication)
  - Concurrency guard tracks start time (datetime) not just presence (bool) — enables stuck-task detection
  - Task runs recorded as "running" immediately, updated on completion — enables stuck-task observability
  - GraphClient sparql_read defaults to True when no permissions configured (permissive), False when permissions dict exists but sparql_read key missing (restrictive)
  - HttpClient allowed_domains=None is permissive; allowed_domains=[] blocks all
  - Bulk EventStore batch size hard limit: 1000 operations
patterns_established:
  - SDK permission pattern: __init__ accepts whitelist/prefix/flag, method checks before dispatch, PermissionError with diagnostic message including offending value AND allowed set
  - Recursive IRI scanning: _check_iri_prefix() walks dict/list/tuple structures, matches strings starting with urn:/http(s)://
  - Scheduler due-check: iterate registry → filter running apps → check config (pause/override) → compare elapsed → invoke as separate asyncio task
  - Admin config upsert pattern: GET existing row by composite PK, create if None, update if exists
  - Bulk event pattern: single event graph with BulkEvent type, summary/source/operation_count/affected_count metadata, accumulated data triples from all operations
observability_surfaces:
  - app_task_runs table with status, duration_ms, error_message per execution
  - app_task_config table with interval_override and paused state per (app_id, task_id)
  - Scheduler logger (app.apps.scheduler) at INFO/ERROR/DEBUG
  - Admin detail page task history section with status badges and controls
  - PermissionError messages include offending value + allowed set for all 3 client types
  - BulkEvent metadata in triplestore (operationCount, affectedCount, summary, source)
drill_down_paths:
  - .gsd/milestones/M009/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S05/tasks/T04-SUMMARY.md
duration: ~2h
verification_result: passed
completed_at: 2026-03-17
---

# S05: Scheduler, Permissions, Bulk EventStore & browserVisible

**Platform scheduler fires app tasks with concurrency guard and retry; SDK clients enforce command whitelist, IRI prefix, SPARQL gate, and network domain restrictions; bulk EventStore records summary metadata; browserVisible hides internal types from object browser.**

## What Happened

This slice built four independent capability layers that complete the app platform's runtime enforcement and background task infrastructure.

**Scheduler (T04).** Created `AppScheduler` class running in the main asyncio event loop with a 60-second tick cycle. Each tick iterates the app registry, filters for running apps, checks each task against its config (user-overridden interval, pause state, concurrency guard), and invokes due tasks via direct httpx POST over UDS to `/_tasks/{task_id}`. Task invocation respects the manifest's `retryPolicy` — exponential backoff with configurable maxRetries and maxBackoff. Every invocation records an `AppTaskRun` row (status: running → success/error, duration_ms, error_message). The scheduler starts after `auto_start()` in main.py lifespan and stops before manager shutdown. Admin router gained two new endpoints: interval update and pause toggle, both using a composite-PK upsert pattern on `AppTaskConfig`. The admin detail template was extended with a full task management section showing each task's description, current interval, pause/resume toggle, interval form, retry policy, and recent run history with color-coded status badges.

**Permissions (T01 + closer fix).** Added real enforcement to three SDK clients. `CommandClient` validates command types against an `allowed_commands` whitelist and recursively scans all params for IRI strings (urn:/http(s):// prefixes) that don't match the app's `urn:sempkm:app:{app_id}:` prefix. `HttpClient` validates outbound URLs against `allowed_domains` glob patterns via `fnmatch.fnmatch` with port stripping. `GraphClient` gates all queries on a `sparql_read` boolean — when False, PermissionError is raised before any HTTP call. `AppContext` threads manifest permissions to all client constructors: `permissions.commands` → CommandClient whitelist, `permissions.network` → HttpClient domains, `permissions.sparql_read` → GraphClient gate. When `permissions` is None (no manifest enforcement), all clients default to permissive.

**Bulk EventStore (T03).** Extended `EventStore` with `commit_bulk()` — same transactional pattern as `commit()` but creates a single summary event graph with `sempkm:BulkEvent` type and ~10 metadata triples (summary, source, operationCount, affectedCount) instead of ~5N per-operation metadata. Data triples accumulate from all operations and materialize identically. Batch size hard-limited to 1000 operations. Added `POST /api/commands/bulk` endpoint and SDK `CommandClient.bulk()` async context manager that accumulates operations and sends on exit.

**browserVisible (T04 work, originally T03).** Added `browserVisible: bool = True` field to `ManifestIconDef` in the Mental Model manifest schema. `get_hidden_type_iris()` reads on-disk manifests and returns type IRIs where `browserVisible` is False. Object browser's `_handle_by_type()` and generic view type filter pills call `get_hidden_types()` to exclude hidden types from the user-facing list. Hidden types remain fully queryable via SPARQL and linkable via edges.

## Verification

- `pytest tests/test_app_scheduler.py -v` — **31 passed** (interval parsing, concurrency guard, retry backoff, admin interval/pause endpoints, task run recording, detail rendering, loop resilience, config override, pause skip)
- `pytest tests/test_app_permissions.py -v` — **33 passed** (command whitelist, IRI prefix recursive scanning, domain glob matching, sparql_read gate, AppContext wiring for all 4 client types)
- `pytest tests/test_bulk_eventstore.py -v` — **16 passed** (summary metadata structure, operation/affected counts, batch size limit, all-or-nothing semantics, bulk API endpoint, SDK context manager)
- `pytest tests/test_browser_visible.py -v` — **22 passed** (manifest parsing, hidden type set, multiple models, bad manifest resilience, type exclusion filtering)
- `pytest tests/test_app_admin.py -v` — **26 passed** (existing admin tests pass with new session factory mock)
- `pytest tests/test_app_browser.py -v` — **11 passed** (explorer and page rendering)
- **Full suite: 1196 passed, 5 pre-existing failures** (test_renderer_overrides.py — Python 3.14 asyncio.get_event_loop() deprecation in S06-staged tests, not S05 regression)

## Requirements Advanced

- APP-05 (permission enforcement) — CommandClient rejects unpermitted command types and IRI prefix violations; GraphClient gates on sparql_read; HttpClient enforces domain globs; StateClient scoped to app state graph. All 4 SDK client types covered with 33 unit tests.
- APP-06 (platform-owned task scheduler) — AppScheduler triggers tasks at configured intervals, concurrency guard prevents double-fire, retry with exponential backoff, task history in SQLite, admin has full control (pause, adjust interval, view history). 31 unit tests.
- APP-11 (bulk EventStore) — commit_bulk() records ~10 summary triples per batch, 1000-op limit enforced, SDK bulk() context manager works. 16 unit tests.
- APP-12 (browserVisible) — ManifestIconDef.browserVisible field parsed, hidden types excluded from object browser and generic view pills, still SPARQL-queryable. 22 unit tests.
- APP-10 (admin monitoring portal) — Admin detail page extended with task history section, interval adjustment, pause/resume controls.

## Requirements Validated

- APP-05 — Permission enforcement: 33 tests prove command whitelist, IRI prefix scanning, SPARQL gate, domain restriction, and AppContext wiring for all 5 SDK clients
- APP-06 — Task scheduler: 31 tests prove interval parsing, concurrency guard, retry backoff, DB recording, admin CRUD, and loop resilience
- APP-11 — Bulk EventStore: 16 tests prove summary metadata, batch limit, operation counts, and SDK context manager
- APP-12 — browserVisible: 22 tests prove manifest parsing, hidden type collection, and browser filtering

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **Task renumbering during execution.** The plan defined T01=Scheduler, T02=Permissions, T03=Bulk EventStore, T04=browserVisible. Executor agents implemented them in a different order: T01 became permissions, T03 became bulk+browserVisible, T04 became scheduler. All must-haves were delivered.
- **GraphClient sparql_read enforcement was missing after task execution.** The T01 summary covered CommandClient and HttpClient but not GraphClient. The closer added sparql_read enforcement to GraphClient, wired it through AppContext, and added 7 tests (3 GraphClient + 4 AppContext wiring). This completed the APP-05 requirement.
- **Scheduler uses direct httpx instead of AppProxy.invoke_task().** Plan called for adding invoke_task() to AppProxy. Implementation uses direct httpx-over-UDS instead — simpler and avoids fabricating a Starlette Request object.

## Known Limitations

- **Scheduler not tested with real Docker stack.** All verification is contract-level (unit tests with mocks). Real subprocess invocation deferred to S07 integration tests.
- **Bulk endpoint has no per-command permission enforcement.** The `POST /api/commands/bulk` platform endpoint accepts command arrays but doesn't validate individual command permissions — that's the SDK client's responsibility (enforced per-add in _BulkCollector).
- **5 pre-existing test failures in test_renderer_overrides.py.** Python 3.14's asyncio.get_event_loop() deprecation breaks TestGetRendererOverride — these tests use synchronous `run_until_complete` instead of `@pytest.mark.asyncio`. Not an S05 regression; will be fixed in S06.

## Follow-ups

- S06 should consume `AppScheduler` running state and `AppRegistry` renderer/contribution metadata
- S07 should exercise scheduler + permissions + bulk in the Docker stack with the test app
- test_renderer_overrides.py needs `@pytest.mark.asyncio` migration to fix Python 3.14 compatibility

## Files Created/Modified

- `backend/app/apps/scheduler.py` — new: AppScheduler class, parse_interval_seconds(), CHECK_INTERVAL
- `backend/app/main.py` — scheduler lifespan wiring (start after auto_start, stop before manager)
- `backend/app/apps/admin_router.py` — task history endpoints, interval/pause CRUD, enriched detail query
- `backend/app/templates/admin/apps/detail.html` — full task management section with history, controls, status badges
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — command whitelist, IRI prefix scanning, bulk context manager
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — sparql_read gate
- `backend/sdk/sempkm_app_sdk/clients/http.py` — domain enforcement via fnmatch
- `backend/sdk/sempkm_app_sdk/context.py` — permissions dict wired to all client constructors
- `backend/sdk/sempkm_app_sdk/runner.py` — manifest permissions parsing
- `backend/app/events/store.py` — commit_bulk() method
- `backend/app/events/models.py` — BULK_EVENT_TYPE, BULK_SUMMARY, BULK_SOURCE, BULK_OP_COUNT, BULK_AFFECTED_COUNT
- `backend/app/commands/router.py` — POST /api/commands/bulk endpoint
- `backend/app/models/manifest.py` — browserVisible field on ManifestIconDef
- `backend/app/browser/_helpers.py` — get_hidden_types() and get_hidden_type_iris()
- `backend/app/browser/workspace.py` — type filtering via get_hidden_types() in _handle_by_type() and generic views
- `backend/tests/test_app_scheduler.py` — new: 31 tests
- `backend/tests/test_app_permissions.py` — new: 33 tests (26 original + 7 GraphClient additions)
- `backend/tests/test_bulk_eventstore.py` — new: 16 tests
- `backend/tests/test_browser_visible.py` — new: 22 tests
- `backend/tests/test_app_admin.py` — updated: mock async_session_factory for detail endpoint

## Forward Intelligence

### What the next slice should know
- All 5 SDK clients now enforce permissions when a permissions dict is provided. The pattern is consistent: `__init__` accepts enforcement config, method checks before dispatch, `PermissionError` with diagnostic message. S06's renderer override dispatch should check `AppRegistry` for manifests (already consuming `get_manifest()`).
- The scheduler is wired into lifespan and will invoke tasks on any running app with manifest tasks. S07's test app needs manifest tasks to exercise this.
- `get_hidden_types()` reads on-disk manifests and is called by `_handle_by_type()` and the views router. S06's frontend contributions should not re-add hidden types when building view lists.
- Bulk EventStore expects `Operation` objects — same as `commit()`. The SDK's `CommandClient.bulk()` context manager handles the HTTP call. S07 should test bulk through the SDK.

### What's fragile
- **AppScheduler._post_task() creates a new httpx client per invocation** — this is fine for <10 apps with minute-level intervals but would need connection pooling for high-frequency scenarios. S07 should verify with the real Docker stack.
- **get_hidden_type_iris() reads manifests from disk on every call** — no caching. Fine for the current call pattern (once per explorer load) but would need caching if called in hot paths.

### Authoritative diagnostics
- `SELECT * FROM app_task_runs WHERE app_id = ? ORDER BY started_at DESC` — full scheduler execution history
- `SELECT * FROM app_task_config` — interval overrides and pause states
- `pytest tests/test_app_permissions.py tests/test_app_scheduler.py tests/test_bulk_eventstore.py tests/test_browser_visible.py -v` — 102 tests covering all S05 deliverables

### What assumptions changed
- **Plan assumed T02 would be a separate GraphClient-focused task** — in practice, GraphClient enforcement was a small addition to the permissions task and was completed during slice closure rather than as a standalone task.
- **Plan assumed AppProxy.invoke_task() would be needed** — direct httpx-over-UDS is simpler and avoids Request fabrication complexity.
