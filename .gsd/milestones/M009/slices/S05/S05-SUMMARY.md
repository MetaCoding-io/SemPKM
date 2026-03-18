---
id: S05
parent: M009
milestone: M009
provides:
  - AppScheduler with 60s tick loop, concurrency guard, exponential backoff retry, DB recording
  - parse_interval_seconds for shorthand (30s/5m/1h/1d) and ISO 8601 (PT5M/PT1H30M)
  - SDK permission enforcement on CommandClient (command whitelist + IRI prefix), GraphClient (sparql_read gate), HttpClient (domain glob via fnmatch)
  - EventStore.commit_bulk() with BulkEvent summary metadata (~7-8 triples per batch vs ~5N)
  - POST /api/commands/bulk endpoint for batch command execution
  - SDK CommandClient.bulk() async context manager
  - browserVisible field on ManifestIconDef (default true), get_hidden_type_iris(), object browser + type pill filtering
  - Admin task history section with interval override and pause UI
requires:
  - slice: S02
    provides: SDK client stubs (CommandClient, GraphClient, HttpClient, StateClient), AppProxy UDS transport, JWT tokens
affects:
  - S06 (permissions enforced, scheduler running, registry metadata available)
  - S07 (all SDK features exercisable in test app)
key_files:
  - backend/app/apps/scheduler.py
  - backend/app/apps/proxy.py
  - backend/app/apps/admin_router.py
  - backend/app/templates/admin/apps/detail.html
  - backend/app/main.py
  - backend/app/events/store.py
  - backend/app/events/models.py
  - backend/app/commands/router.py
  - backend/sdk/sempkm_app_sdk/clients/commands.py
  - backend/sdk/sempkm_app_sdk/clients/graph.py
  - backend/sdk/sempkm_app_sdk/clients/http.py
  - backend/sdk/sempkm_app_sdk/context.py
  - backend/sdk/sempkm_app_sdk/runner.py
  - backend/app/models/manifest.py
  - backend/app/services/models.py
  - backend/app/services/icons.py
  - backend/app/browser/_helpers.py
  - backend/app/browser/workspace.py
  - backend/app/views/router.py
  - backend/tests/test_app_scheduler.py
  - backend/tests/test_sdk_permissions.py
  - backend/tests/test_bulk_eventstore.py
  - backend/tests/test_browser_visible.py
key_decisions:
  - D141 — Platform owns scheduling; apps declare tasks, platform runs them via HTTP
  - D144 — browserVisible field hides internal types from browser without losing SPARQL queryability
  - D145 — Bulk EventStore with summary metadata (~10 triples) instead of per-operation (~5N)
  - D177 — SDK default-deny permissions with manifest-driven allowlists, IRI prefix scoping, fnmatch domain globs
patterns_established:
  - parse_interval_seconds as a public function reused by scheduler and admin config validation
  - Concurrency guard via _running_tasks set keyed by (app_id, task_id) tuple
  - Permission enforcement is stateless and synchronous — PermissionError with self-documenting messages
  - BulkAccumulator pattern separates permission checking (sync, on add()) from network submission (async, on context exit)
  - get_hidden_types() in browser._helpers wraps get_hidden_type_iris() — single import for all browser/view routers
  - ShapesService.get_types(exclude_iris=set) pattern for filtering types at the query layer
observability_surfaces:
  - app.apps.scheduler logger — INFO for dispatches/completions, WARNING for retries, ERROR for exhausted retries
  - app_task_runs table — full execution history with status/duration_ms/error_message
  - app_task_config table — user overrides for interval and pause state
  - Admin detail page task history <details> section with interval adjustment form
  - app.events.store logger at INFO on bulk commit with operation count, affected count, source
  - POST /api/commands/bulk response includes operation_count and affected_count
  - BulkEvent typed events queryable via SPARQL: SELECT ?e WHERE { GRAPH ?g { ?e a <urn:sempkm:BulkEvent> } }
  - PermissionError exceptions include offending value and allowed list/prefix in message
drill_down_paths:
  - .gsd/milestones/M009/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S05/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S05/tasks/T03-SUMMARY.md
  - .gsd/milestones/M009/slices/S05/tasks/T04-SUMMARY.md
duration: 1h20m
verification_result: passed
completed_at: 2026-03-18
---

# S05: Scheduler, Permissions, Bulk EventStore & browserVisible

**Platform scheduler fires app tasks on interval with concurrency guard and retry, SDK clients enforce permission sandbox (command whitelist, IRI prefix, domain globs, SPARQL gate), bulk EventStore records summary-only metadata for batch operations, and browserVisible hides internal types from the object browser.**

## What Happened

Four tasks delivered the four subsystems this slice covers.

**T01 — AppScheduler** built the platform-owned scheduler with a 60s tick loop. Each tick queries running apps from the DB, evaluates manifest tasks against configured intervals and last-run timestamps, and dispatches due tasks via `AppProxy.invoke_task()` (POST to app UDS). A `_running_tasks` set prevents double-firing. Retry uses exponential backoff clamped to manifest `maxBackoff`. Every invocation is recorded as an `AppTaskRun` row with status, duration, and error message. `parse_interval_seconds()` handles both shorthand ("30s", "5m", "1h", "1d") and ISO 8601 ("PT5M", "PT1H30M") with floor 30s / ceiling 86400s. The scheduler is wired into `main.py` lifespan — started after `auto_start()`, stopped before manager teardown. Admin gets task history and config endpoints with interval override and pause controls.

**T02 — SDK Permissions** added real enforcement to all three SDK clients. `CommandClient` rejects commands not in the manifest whitelist and validates IRI params against the app's `urn:sempkm:app:{appId}:` prefix (using a `_IRI_PARAMS` dict mapping command types to their IRI-carrying fields). `GraphClient` gates on `sparql_read` boolean (default False). `HttpClient` validates request hostnames against allowed domains using `fnmatch.fnmatch` — empty list blocks all, `["*"]` allows all. `AppContext` threads permissions from the manifest dict to each client constructor. All enforcement is stateless and synchronous, raising `PermissionError` with self-documenting messages.

**T03 — Bulk EventStore** added `commit_bulk()` with the same transactional pattern as `commit()` but writing ~7-8 summary triples per batch (type, timestamp, actor, summary, source, operationCount, affectedCount) instead of ~5N per-operation metadata. `POST /api/commands/bulk` accepts batched commands and routes through `commit_bulk()`. SDK `CommandClient.bulk()` is an async context manager yielding a `BulkAccumulator` that checks permissions synchronously on `add()` and submits the batch on clean exit. Batch size capped at 1000.

**T04 — browserVisible** added `browserVisible: bool = True` to `ManifestIconDef`. `get_hidden_type_iris()` scans on-disk manifests and returns type IRIs where `browserVisible` is False. Both `_handle_by_type()` in workspace.py and `generic_view()`/`type_pills()` in views/router.py pass the hidden set to `ShapesService.get_types(exclude_iris=...)`. Hidden types remain fully queryable via SPARQL and linkable via edges.

## Verification

All four task-specific test suites pass:

| Suite | Tests | Status |
|-------|-------|--------|
| `test_app_scheduler.py` | 40 | ✅ pass |
| `test_sdk_permissions.py` | 33 | ✅ pass |
| `test_bulk_eventstore.py` | 18 | ✅ pass |
| `test_browser_visible.py` | 22 | ✅ pass |
| **Full suite** | **1344** | **✅ pass, 0 failures** |

Coverage:
- Interval parsing: shorthand, ISO 8601, floor/ceiling, edge cases (21 tests)
- Backoff calculation: multiple attempts, capped at max (5 tests)
- Concurrency guard: skip when running (2 tests)
- Retry: success/failure/exception/zero-retries (4 tests)
- Task config: pause, override (2 tests)
- Tick logic: due/not-due/no-tasks (3 tests)
- Scheduler lifecycle: start/stop (2 tests)
- Command whitelist: allow/reject/empty (3 tests)
- IRI prefix: 7 command types (8 tests)
- SPARQL gate: allow/block/default (3 tests)
- Domain enforcement: exact/glob/wildcard/empty/multiple, all HTTP methods (9 tests)
- AppContext threading: 8 tests
- Bulk metadata: type, triple count, summary, source, performed_by (5 tests)
- Bulk counts: operation and affected deduplication (3 tests)
- Batch size limit: 1000 allowed, 1001 rejected (2 tests)
- Bulk materialization: inserts and deletes (2 tests)
- Bulk rollback: transaction and commit failure (2 tests)
- SDK bulk context manager: accumulate/discard/empty/permission (4 tests)
- Manifest parsing: default true, explicit true/false, schema integration (4 tests)
- Prefix expansion: known/unknown/HTTP/URN/no-colon (5 tests)
- Hidden type resolution: none/empty/all-visible/hidden/multiple/bad-manifest (7 tests)
- ShapesService filtering: no exclude/none/empty/filters/multiple/nonexistent (6 tests)

## Requirements Advanced

- APP-05 — Permission enforcement implemented in SDK clients (command whitelist, IRI prefix, SPARQL gate, domain globs). Contract tests prove enforcement. Live runtime proof deferred to S07.
- APP-06 — Platform-owned task scheduler with interval parsing, concurrency guard, retry, and DB recording. Contract tests prove all scheduler logic. Live runtime proof deferred to S07.
- APP-11 — Bulk EventStore with commit_bulk(), summary metadata, batch size limit, bulk API endpoint, SDK context manager. Contract tests prove metadata shape and rollback. Live runtime proof deferred to S07.
- APP-12 — browserVisible field on ManifestIconDef, get_hidden_type_iris(), object browser and type pill filtering. Contract tests prove parsing and filtering.
- APP-03 — App SDK extended with permission enforcement on all clients and bulk context manager.
- APP-10 — Admin detail page extended with task history section (interval display, pause toggle, runs table).
- APP-13 — app_task_runs and app_task_config tables populated by scheduler and admin config endpoints.

## Requirements Validated

- None moved to validated — all S05 requirements proved by contract tests only. Full validation requires S07 integration proof with real Docker stack.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- T02 used `source` and `target` field names for edge.create IRI validation instead of `subject` and `object` (plan spec). The actual `EdgeCreateParams` schema uses source/target.
- T02 added `body.diff` to the IRI param map — not in the plan but exists in the command registry alongside `body.set`.
- T03 refactored CommandClient to extract `_check_permissions()` as a shared method for both `execute()` and `BulkAccumulator.add()`. Plan didn't mention this refactoring but it's the right deduplication.
- T04 placed hidden-type resolution in `app.services.models.get_hidden_type_iris()` instead of as an `IconService` method — avoids coupling to IconService lifecycle. `_expand_prefix()` duplicated in models.py to keep the function self-contained.

## Known Limitations

- All S05 work is proved by contract tests (mocks, no Docker). Live scheduler firing, real permission enforcement through the proxy chain, and bulk commits through the API are deferred to S07 integration proof.
- Scheduler tick interval is 60s — tasks with intervals below 60s still fire at the next tick. The 30s floor is a manifest validation constraint, not a scheduler precision guarantee.
- `invoke_task` uses a 300s timeout — long-running tasks beyond this will be marked as failed.
- Bulk batch size limit is 1000 — this is enforced at both the API and EventStore layers but is not configurable.

## Follow-ups

- S06 needs the scheduler running and permissions enforced to wire workspace contributions and renderer overrides.
- S07 will exercise all S05 features through the Docker stack with a real test app — that's where APP-05, APP-06, APP-11, and APP-12 should move to validated.

## Files Created/Modified

- `backend/app/apps/scheduler.py` — new: AppScheduler class, parse_interval_seconds, calculate_backoff
- `backend/app/apps/proxy.py` — added invoke_task() method for scheduler-initiated task calls
- `backend/app/apps/admin_router.py` — added task history and config endpoints
- `backend/app/templates/admin/apps/detail.html` — replaced placeholder with task history details section
- `backend/app/main.py` — wired AppScheduler into lifespan (create/start/stop)
- `backend/app/events/models.py` — added 5 bulk vocabulary constants
- `backend/app/events/store.py` — added commit_bulk() method
- `backend/app/commands/router.py` — added BulkCommandRequest model, POST /api/commands/bulk endpoint
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — permission enforcement + bulk context manager + _check_permissions refactor
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — sparql_read gate
- `backend/sdk/sempkm_app_sdk/clients/http.py` — domain enforcement via fnmatch
- `backend/sdk/sempkm_app_sdk/context.py` — permissions dict threading to all clients
- `backend/sdk/sempkm_app_sdk/runner.py` — reads manifest.permissions, passes to AppContext
- `backend/app/models/manifest.py` — browserVisible: bool = True on ManifestIconDef
- `backend/app/services/models.py` — get_hidden_type_iris() and _expand_prefix()
- `backend/app/browser/_helpers.py` — get_hidden_types() wrapper
- `backend/app/browser/workspace.py` — _handle_by_type() and workspace() pass exclude_iris
- `backend/app/views/router.py` — generic_view() and type_pills() pass exclude_iris
- `backend/app/services/shapes.py` — get_types() accepts exclude_iris parameter
- `backend/tests/test_app_scheduler.py` — new: 40 tests
- `backend/tests/test_sdk_permissions.py` — new: 33 tests
- `backend/tests/test_bulk_eventstore.py` — new: 18 tests
- `backend/tests/test_browser_visible.py` — new: 22 tests
- `backend/tests/test_sdk_app.py` — updated 2 tests for new permission args
- `backend/tests/test_app_admin.py` — fixed fixture, updated assertion

## Forward Intelligence

### What the next slice should know
- AppScheduler is wired into lifespan and will tick every 60s once apps are running. S06 doesn't interact with the scheduler directly — it reads manifest data for renderer/contribution metadata.
- Permission enforcement is fully implemented in the SDK clients. S06 app contributions will go through the proxied SDK — permissions are transparent to the frontend integration layer.
- `commit_bulk()` is available but no existing code path uses it yet. S07's test app should exercise it.
- `get_hidden_types()` is called on every object browser and type pill render — models with `browserVisible: false` types will have those types silently excluded.

### What's fragile
- `invoke_task` assumes the app subprocess has a `/_tasks/{task_id}` route registered by the SDK runner. If the SDK task decorator changes the route pattern, the scheduler will 404.
- `_IRI_PARAMS` dict in CommandClient must be kept in sync with any new command types that carry IRI parameters.
- `_expand_prefix()` is duplicated in `services/models.py` (identical to IconService version). If prefix expansion logic changes, both must be updated.

### Authoritative diagnostics
- `app_task_runs` table: SELECT * FROM app_task_runs ORDER BY started_at DESC — shows all scheduler history
- `app_task_config` table: SELECT * FROM app_task_config — shows interval overrides and pause states
- Admin detail page at `/admin/apps/{app_id}` — task history section visible when app has scheduled tasks
- `GET /admin/apps/{app_id}/tasks` — JSON API for task run history

### What assumptions changed
- Task plan for T02 assumed edge.create uses `subject`/`object` fields — actual schema uses `source`/`target`. The implementation uses the real field names.
- T04 planned to put hidden-type resolution on IconService — moved to standalone function in services/models.py to avoid lifecycle coupling. Works the same, different location.
