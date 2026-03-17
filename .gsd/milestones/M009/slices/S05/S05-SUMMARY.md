---
id: S05
parent: M009
milestone: M009
provides:
  - SDK CommandClient with command whitelist + IRI prefix enforcement
  - SDK HttpClient with network domain restriction (fnmatch globs)
  - AppContext permissions wiring from manifest to clients
  - EventStore.commit_bulk() with summary-only metadata (~10 triples per batch)
  - POST /api/commands/bulk platform endpoint
  - SDK CommandClient.bulk() async context manager with per-add permission enforcement
  - ManifestIconDef.browserVisible field (default True)
  - get_hidden_type_iris() for collecting hidden type IRIs from disk manifests
  - ShapesService.get_types(exclude_iris=) filtering parameter
  - Browser routes filter hidden types from nav tree, type picker, lint dashboard, view pills
  - AppScheduler with periodic due-check, concurrency guard, exponential backoff retry
  - parse_interval_seconds() for shorthand and ISO 8601 intervals
  - Admin endpoints for task interval adjustment and pause/resume
  - Admin detail page with real task history, status badges, and controls
requires:
  - slice: S02
    provides: SDK client stubs (CommandClient, HttpClient, GraphClient, StateClient), AppContext, AppProxy, AppManifestSchema with AppPermissions
  - slice: S01
    provides: AppManager, AppRegistry, SQLAlchemy models (AppTaskRun, AppTaskConfig)
  - slice: S03
    provides: admin_router.py and detail.html template
affects:
  - S06
  - S07
key_files:
  - backend/sdk/sempkm_app_sdk/clients/commands.py
  - backend/sdk/sempkm_app_sdk/clients/http.py
  - backend/sdk/sempkm_app_sdk/context.py
  - backend/app/events/store.py
  - backend/app/events/models.py
  - backend/app/commands/router.py
  - backend/app/commands/schemas.py
  - backend/app/models/manifest.py
  - backend/app/services/models.py
  - backend/app/services/shapes.py
  - backend/app/browser/_helpers.py
  - backend/app/apps/scheduler.py
  - backend/app/apps/admin_router.py
  - backend/app/templates/admin/apps/detail.html
  - backend/app/main.py
key_decisions:
  - IRI scanning uses heuristic (starts with urn: or http) — simple, covers all SemPKM IRIs
  - HttpClient allowed_domains=None is permissive; allowed_domains=[] blocks all
  - Bulk event uses BULK_EVENT_TYPE (sempkm:BulkEvent) distinct from EVENT_TYPE for queryability
  - _BulkCollector is a separate class for clean permission delegation
  - get_hidden_type_iris() reads from disk (not async, no triplestore dependency) — mirrors IconService pattern
  - _expand_prefix() duplicated from IconService as module-level function to avoid cross-service coupling
  - Scheduler invokes tasks directly via httpx over UDS rather than fabricating Starlette Request for AppProxy
  - Concurrency guard uses dict[tuple[str,str], datetime] — tracks start time for observability
patterns_established:
  - SDK client permission pattern: __init__ accepts whitelist/prefix, execute() checks before dispatch, PermissionError with diagnostic message
  - Bulk summary metadata pattern: ~10 triples per batch vs ~5N for standard commit
  - SDK context manager pattern for batched operations with fail-fast permission enforcement
  - browserVisible manifest field pattern: static field on ManifestIconDef, read from disk at request time
  - get_hidden_types() helper in _helpers.py centralizes model dir path for browser routes
  - Scheduler due-check pattern: iterate registry → filter running apps → check config → compare elapsed → invoke
  - Admin endpoint upsert pattern for composite-PK config tables
observability_surfaces:
  - PermissionError messages include offending value AND allowed list/prefix
  - sempkm:BulkEvent type distinguishes bulk from standard events in SPARQL queries
  - sempkm:operationCount and sempkm:affectedCount provide batch size introspection
  - app_task_runs table: full execution history with status, duration_ms, error_message
  - app_task_config table: interval_override and paused state per (app_id, task_id)
  - Scheduler logger: INFO (invocations/completions), ERROR (failures), DEBUG (skipped tasks)
  - Admin detail page task history section with status badges and controls
drill_down_paths:
  - .gsd/milestones/M009/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S05/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S05/tasks/T03-SUMMARY.md
  - .gsd/milestones/M009/slices/S05/tasks/T04-SUMMARY.md
duration: ~2h30m
verification_result: passed
completed_at: 2026-03-16
---

# S05: Scheduler, Permissions, Bulk EventStore & browserVisible

**Platform scheduler, SDK permission enforcement, bulk event commits, and browserVisible type filtering — all contract-verified with 121 tests.**

## What Happened

**T01 — SDK Permission Enforcement:** Added real enforcement to the SDK client stubs that were built in S02 with enforcement deferred. `CommandClient` now rejects commands not in the manifest's `permissions.commands` whitelist and recursively scans all params for IRI strings that don't match the app's prefix (`urn:sempkm:app:{app_id}:`). `HttpClient` matches outbound URL hostnames against `permissions.network` glob patterns via `fnmatch`, stripping ports before matching. `AppContext` wires manifest permissions to both clients at construction. 26 tests.

**T02 — Bulk EventStore:** Added `commit_bulk()` to `EventStore` — creates a single `sempkm:BulkEvent` with ~10 metadata triples (summary, source, operation count, affected count) instead of per-operation metadata. Data triples and materializations are identical to `commit()`. Added `POST /api/commands/bulk` platform endpoint and SDK `CommandClient.bulk()` async context manager with per-add permission enforcement (fail fast). 1000-operation batch limit enforced. 16 tests.

**T03 — browserVisible:** Added `browserVisible: bool = True` field to `ManifestIconDef`. Added `get_hidden_type_iris()` standalone function that reads on-disk manifests, finds icons with `browserVisible=False`, expands prefixed type names, and returns the set of hidden IRIs. Added `exclude_iris` parameter to `ShapesService.get_types()`. Updated 6 browser-facing call sites (nav tree, workspace main, type picker, lint dashboard, 2 view pill endpoints) to pass hidden types. The obsidian import mapper was intentionally left unfiltered. 22 tests. Note: T03's code was missing from the worktree despite the task summary claiming completion — implemented during slice completion.

**T04 — AppScheduler:** Created `AppScheduler` class running in the main asyncio event loop, checking due tasks every 60 seconds. Each task's due state considers user config overrides, pause state, concurrency guard, and elapsed time. Task invocation via direct httpx POST over UDS. Retry with exponential backoff per task's retryPolicy. Every invocation records an `AppTaskRun` row. Wired into `main.py` lifespan (starts after `auto_start()`, stops before shutdown). Extended admin router with interval update and pause toggle endpoints. Replaced detail template task placeholder with full task management section. 31 scheduler tests + 26 admin tests.

## Verification

All 5 slice-level test suites pass:

- `tests/test_app_permissions.py` — **26 passed** (command whitelist, IRI prefix, domain enforcement, AppContext wiring)
- `tests/test_bulk_eventstore.py` — **16 passed** (bulk event type, metadata, materialization, size limits, SDK context manager, permissions)
- `tests/test_browser_visible.py` — **22 passed** (field defaults, prefix expansion, hidden IRI collection, type filtering)
- `tests/test_app_scheduler.py` — **31 passed** (interval parsing, concurrency guard, retry backoff, admin endpoints, task recording, config overrides, pause, loop resilience)
- `tests/test_app_admin.py` — **26 passed** (existing admin tests still pass with new task management)

**Total: 121 tests, 0 failures, 0 regressions.**

All modified Python files pass `ast.parse()` syntax verification.

## Requirements Advanced

- APP-05 — SDK clients now enforce command whitelist, IRI prefix, and network domain restrictions per manifest permissions
- APP-06 — AppScheduler triggers tasks at configured intervals with concurrency guard, retry, and admin visibility
- APP-11 — `EventStore.commit_bulk()` records summary-only metadata; SDK exposes `ctx.commands.bulk()` context manager; batch limit enforced
- APP-12 — `browserVisible: false` types hidden from object browser nav tree, type picker, and view filter pills
- APP-03 — SDK clients gained real enforcement (advanced from stub state)
- APP-10 — Admin detail page extended with task history, interval adjustment, and pause controls
- APP-13 — `app_task_config` and `app_task_runs` tables populated correctly during scheduler operations

## Requirements Validated

- APP-05 — 26 permission tests prove: whitelisted commands succeed, non-whitelisted rejected, IRI prefix enforced recursively, network globs matched with port stripping
- APP-06 — 31 scheduler tests prove: interval parsing handles all formats, due-check logic correct, concurrency guard prevents duplicates, retry backoff capped, task runs recorded, config overrides respected, pause skips execution
- APP-11 — 16 bulk tests prove: summary metadata created (~10 triples), no per-operation metadata leakage, materialization identical to commit(), >1000 ops fails, SDK context manager collects and posts
- APP-12 — 22 browserVisible tests prove: field defaults True, hidden types collected from manifests, get_types() excludes hidden IRIs, edge cases handled

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T03 code changes were missing from the worktree despite the task summary claiming completion — all T03 code (manifest field, get_hidden_type_iris, ShapesService filtering, browser route updates, 22 tests) was implemented during slice completion.
- T04 used direct httpx-over-UDS for task invocation instead of AppProxy.forward() — simpler, avoids Starlette Request fabrication.
- T02 added `BulkCommandRequest`/`BulkCommandResponse` Pydantic models to `schemas.py` (not in plan but needed for proper FastAPI integration).

## Known Limitations

- Scheduler loop interval is fixed at 60 seconds — not configurable without code change. Sufficient for expected task intervals (5m+).
- `get_hidden_type_iris()` reads from disk on every request — no caching. Acceptable since model manifests change rarely and reads are fast.
- Obsidian import mapper does not filter hidden types — intentional, users may need to map to internal types during import.

## Follow-ups

- S06 needs `AppRegistry` renderer/contribution metadata, scheduler running, permissions enforced — all now available.
- S07 test app should exercise: scheduled task firing, permission rejection, bulk commit, browserVisible hiding.

## Files Created/Modified

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — command whitelist, IRI prefix scanning, bulk context manager
- `backend/sdk/sempkm_app_sdk/clients/http.py` — domain enforcement via fnmatch
- `backend/sdk/sempkm_app_sdk/context.py` — permissions wiring to clients
- `backend/sdk/sempkm_app_sdk/runner.py` — manifest permissions parsing
- `backend/app/events/models.py` — 5 bulk event vocabulary constants
- `backend/app/events/store.py` — commit_bulk() method
- `backend/app/commands/schemas.py` — BulkCommandRequest/Response models
- `backend/app/commands/router.py` — POST /api/commands/bulk endpoint
- `backend/app/models/manifest.py` — browserVisible field on ManifestIconDef
- `backend/app/services/models.py` — _expand_prefix(), get_hidden_type_iris()
- `backend/app/services/shapes.py` — exclude_iris parameter on get_types()
- `backend/app/browser/_helpers.py` — get_hidden_types() helper
- `backend/app/browser/workspace.py` — 2 get_types() calls updated with hidden filtering
- `backend/app/browser/objects.py` — type picker call site updated
- `backend/app/browser/pages.py` — lint dashboard call site updated
- `backend/app/views/router.py` — 2 view filter pill call sites updated
- `backend/app/apps/scheduler.py` — new: AppScheduler, parse_interval_seconds()
- `backend/app/apps/admin_router.py` — interval/pause endpoints, enriched detail
- `backend/app/templates/admin/apps/detail.html` — task management section
- `backend/app/main.py` — scheduler lifecycle wiring
- `backend/tests/test_app_permissions.py` — 26 tests
- `backend/tests/test_bulk_eventstore.py` — 16 tests
- `backend/tests/test_browser_visible.py` — 22 tests
- `backend/tests/test_app_scheduler.py` — 31 tests
- `backend/tests/test_app_admin.py` — updated for new session factory mock

## Forward Intelligence

### What the next slice should know
- SDK clients now have real permission enforcement — S06 workspace contributions and renderer overrides can rely on permissions being enforced at the SDK layer, not the platform proxy.
- `AppRegistry` renderer/contribution metadata is available via manifests. S06 should query `registry.get_manifest(app_id)` for frontend declarations.
- The scheduler is wired into lifespan and auto-starts after `auto_start()` — S07 can verify scheduled task execution by checking `app_task_runs` table.

### What's fragile
- `get_hidden_type_iris()` does disk I/O on every browser request — if models directory has many entries, could add latency. Consider caching if it becomes measurable.
- Scheduler concurrency guard is in-memory (`_running_tasks` dict) — if the platform process crashes mid-task, the guard won't detect the orphaned run. The `app_task_runs` row with `status='running'` would need manual cleanup.

### Authoritative diagnostics
- `SELECT * FROM app_task_runs ORDER BY started_at DESC` — definitive task execution history
- `SELECT * FROM app_task_config` — user overrides for intervals and pause state
- `SELECT ?e ?s ?c WHERE { ?e a <urn:sempkm:BulkEvent> ; <urn:sempkm:summary> ?s ; <urn:sempkm:operationCount> ?c }` — all bulk events

### What assumptions changed
- T03 task summary claimed code was written but it wasn't in the worktree — never trust task summaries without file-level verification in the closer step.
