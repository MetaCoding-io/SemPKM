# S05: Scheduler, Permissions, Bulk EventStore & browserVisible — Research

**Date:** 2026-03-16
**Researcher:** GSD auto-mode

## Summary

S05 has four independent deliverables: (1) `AppScheduler` — platform-owned task triggering with concurrency guard and retry, (2) SDK permission enforcement on all 5 clients, (3) `EventStore.commit_bulk()` with summary metadata + SDK `bulk()` context manager, and (4) `browserVisible` field on Mental Model ManifestSchema filtering types from the object browser.

All four are well-defined by the design doc and use patterns already established in the codebase. The scheduler is the most complex — it's a new asyncio background loop managing timers, DB writes, and HTTP calls. But it doesn't touch the critical path (subprocess lifecycle, IPC) that S01/S02 already proved. Permission enforcement is mechanical: add validation logic to existing SDK client stubs. Bulk EventStore extends a well-understood 365-line module. `browserVisible` is ~20 lines of manifest schema change plus a SPARQL filter.

The admin detail page needs a task history section and interval adjustment UI (D148 — admin grows across slices). This is the S05-specific admin work.

## Recommendation

**4 tasks, one per deliverable, parallel-safe except that admin UI touches from task 1 (scheduler) overlap with the detail template.**

Build order:
1. **Scheduler** first — it's the largest piece and has the most surface area (new file, DB writes, proxy calls, admin UI extension). No dependencies on the other 3 deliverables.
2. **SDK permission enforcement** — modifies 3 SDK clients (CommandClient, GraphClient, HttpClient) plus the AppContext to thread manifest permissions through. Independent of scheduler.
3. **Bulk EventStore** — extends `backend/app/events/store.py` with `commit_bulk()` and adds SDK `bulk()` context manager. Independent of scheduler and permissions.
4. **browserVisible** — smallest piece. Adds field to `ManifestIconDef`, exposes via `IconService`, filters in `_handle_by_type`. Independent of everything else.

All 4 can be verified with unit tests without Docker.

## Implementation Landscape

### Key Files

**Scheduler (new):**
- `backend/app/apps/scheduler.py` — **new file.** `AppScheduler` class with:
  - `start()` / `stop()` lifecycle
  - `_tick()` — periodic loop checking which tasks are due
  - `_invoke_task()` — POST to app UDS via proxy, record result in `app_task_runs`
  - `_parse_interval_seconds()` — convert manifest interval strings to seconds (reuse regex from `AppTask.validate_interval`)
  - Concurrency guard: track `_running_tasks: dict[tuple[str, str], bool]` (app_id, task_id)
  - Retry: exponential backoff per manifest `retryPolicy`
  - `get_task_config()` / `update_task_config()` — read/write `app_task_config` overrides

**Scheduler (modify):**
- `backend/app/main.py` — add `AppScheduler` init in lifespan, start after `auto_start()`, stop in shutdown before proxy/manager cleanup
- `backend/app/apps/admin_router.py` — add task history endpoint (`GET /admin/apps/{app_id}/tasks`), interval adjustment endpoint (`POST /admin/apps/{app_id}/tasks/{task_id}/config`)
- `backend/app/templates/admin/apps/detail.html` — add task history table and interval controls

**SDK Permission enforcement (modify):**
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — add `_allowed_commands: set[str]` and `_iri_prefix: str` params; validate before forwarding
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — add `_sparql_read: bool` param; reject if not permitted
- `backend/sdk/sempkm_app_sdk/clients/http.py` — add `_allowed_domains: list[str]` param; validate URL hostname against glob patterns via `fnmatch`
- `backend/sdk/sempkm_app_sdk/context.py` — accept `permissions` dict in constructor, thread through to client constructors. Currently clients are created with no permission info; need to pass manifest.permissions.

**Bulk EventStore (modify + new):**
- `backend/app/events/store.py` — add `commit_bulk()` method. Same transaction pattern as `commit()` but: (a) event type is `SEMPKM.BulkEvent`, (b) metadata is summary-only (~10 triples: type, timestamp, actor, summary, source, operation count, affected count), (c) data triples still stored in event graph, (d) materialization still happens identically
- `backend/app/events/models.py` — add `BULK_EVENT_TYPE`, `EVENT_SUMMARY`, `EVENT_SOURCE`, `EVENT_OPERATION_COUNT`, `EVENT_AFFECTED_COUNT` constants
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — add `bulk()` async context manager that batches operations and calls a platform bulk endpoint
- `backend/app/commands/router.py` or a new `/api/commands/bulk` endpoint — accept bulk command batch and dispatch through EventStore.commit_bulk()

**browserVisible (modify):**
- `backend/app/models/manifest.py` — add `browserVisible: bool = True` field to `ManifestIconDef`
- `backend/app/services/icons.py` — expose hidden types set: `get_hidden_types() -> set[str]` computed from manifest icons where `browserVisible=False`
- `backend/app/browser/workspace.py` — in `_handle_by_type()`, filter out hidden types from `shapes_service.get_types()` results

### Build Order

**Task 1: AppScheduler + admin task history**
- Create `scheduler.py` with the timer loop, concurrency guard, retry logic
- Add `_parse_interval_seconds()` utility (shorthand + ISO 8601 → int)
- Wire into `main.py` lifespan
- Add admin task history endpoint + template section
- Unit tests: interval parsing, concurrency guard logic, retry backoff calculation, task config CRUD

**Task 2: SDK permission enforcement**
- Modify `CommandClient` — add whitelist + IRI prefix check
- Modify `GraphClient` — add sparql_read gate
- Modify `HttpClient` — add domain glob enforcement via `fnmatch`
- Modify `AppContext` — accept and thread permissions
- Modify `runner.py` — read manifest permissions, pass to AppContext
- Unit tests: each enforcement layer, edge cases (empty whitelist, wildcard domain, mixed case)

**Task 3: Bulk EventStore + SDK bulk context manager**
- Add vocabulary constants for BulkEvent
- Implement `commit_bulk()` on EventStore
- Add `/api/commands/bulk` platform endpoint (or extend existing)
- Add `BulkCommandClient` or `bulk()` context manager on SDK CommandClient
- Unit tests: summary metadata structure, batch size enforcement, undo semantics

**Task 4: browserVisible**
- Add field to `ManifestIconDef`
- Add `get_hidden_types()` to `IconService`
- Filter in `_handle_by_type()` (and potentially in type filter pills for generic views)
- Unit tests: manifest parsing with browserVisible, icon service hidden types, filtering

### Verification Approach

All verification is unit tests — no Docker needed:

```bash
cd backend && .venv/bin/pytest tests/test_app_scheduler.py -v
cd backend && .venv/bin/pytest tests/test_sdk_permissions.py -v
cd backend && .venv/bin/pytest tests/test_bulk_eventstore.py -v
cd backend && .venv/bin/pytest tests/test_browser_visible.py -v
```

Plus run existing test suite to confirm no regressions:
```bash
cd backend && .venv/bin/pytest tests/ -v
```

**Scheduler tests** should cover:
- `_parse_interval_seconds()` — "30s"→30, "5m"→300, "1h"→3600, "1d"→86400, "PT5M"→300
- Concurrency guard — task not re-invoked if already running
- Retry backoff — correct delay calculation per attempt
- Task config CRUD — override interval, pause/resume
- `_tick()` — identifies due tasks based on last run + interval

**Permission tests** should cover:
- CommandClient rejects `edge.patch` when only `["object.create", "body.set"]` allowed
- CommandClient rejects IRIs not matching `urn:sempkm:app:{appId}:`
- GraphClient rejects query when `sparql_read=False`
- HttpClient rejects URL to `evil.com` when only `["*.hypothes.is"]` allowed
- HttpClient allows wildcard `["*"]` pattern
- StateClient already scoped — just verify graph_iri matches `urn:sempkm:app:{appId}:state`

**Bulk EventStore tests** should cover:
- `commit_bulk()` produces BulkEvent type with summary metadata
- Operation count and affected count correct
- Batch size limit enforcement (>1000 raises)
- Data triples still materialize correctly
- All-or-nothing semantics (mock transaction failure → rollback)

**browserVisible tests** should cover:
- ManifestIconDef with `browserVisible: false` parsed correctly
- `get_hidden_types()` returns correct set
- Types with `browserVisible: false` excluded from `_handle_by_type()` output

## Constraints

- **SDK clients are in a separate package** (`backend/sdk/`) — they can't import platform code. Permission enforcement must use data passed at construction time (the permissions dict from the manifest), not direct access to `AppManifestSchema`.
- **Scheduler runs in the main event loop** — all DB operations must use the async session factory pattern already established in `AppManager`. No blocking I/O.
- **`app_task_runs` table uses auto-incrementing PK** — scheduler writes must handle concurrent access (unlikely in single-process but defensive). Use the existing `async_sessionmaker` pattern.
- **Existing `commit()` signature must not change** — `commit_bulk()` is a new method, not a modification of the existing one. D145 is explicit about this.
- **`fnmatch.fnmatch` is stdlib** — no new dependency for domain glob matching. Patterns like `*.hypothes.is` match `api.hypothes.is` correctly.
- **ISO 8601 duration parsing** — manifest already validates format (`PT(\d+[HMS])+`) but the scheduler needs to convert to seconds. Simple regex extraction is sufficient (no need for `isodate` library): `H`→3600, `M`→60, `S`→1.
- **Admin detail template already exists** (168 lines) — task history section is additive. Follow existing pattern of `<details>` sections with htmx lazy-loading.

## Common Pitfalls

- **Scheduler tick drift** — Using `asyncio.sleep(60)` for the tick loop means each tick includes the execution time of the previous tick. Use `asyncio.wait_for` with a deadline computed from the last tick start time, or accept 60s±execution_time granularity (acceptable for v1 since minimum interval is 30s).
- **Proxy reuse for task invocation** — The scheduler should call the proxy's `forward()` method directly (same process), not make an HTTP request to itself. But `forward()` expects a `Request` object. Simpler approach: use the proxy's pooled httpx client directly via `proxy._get_or_create_client()`, or create a dedicated method on AppProxy for internal task invocation that doesn't need a Request.
- **Permission enforcement in SDK vs platform** — The design says enforcement happens in SDK clients (not platform-side). This means an app that doesn't use the SDK (raw HTTP) could bypass enforcement. Acceptable for v1 because apps are first-party and installed from the apps/ directory. Platform-side enforcement is future work.
- **IRI prefix enforcement scope** — `CommandClient` must check all IRIs in the command params, not just the top-level subject. For `object.create`, check `iri`; for `edge.create`, check `subject` and `object` params against the prefix. The exact param names come from the command schemas.
- **Bulk EventStore transaction size** — 1000 operations × ~3 triples each = ~3000 triples in one SPARQL INSERT DATA. RDF4J's request body limit is ~2MB. At ~100 bytes/triple, this is ~300KB — well within limits.

## Open Risks

- **Scheduler-proxy interaction** — The scheduler needs to POST to app UDS sockets. It can use AppProxy's connection pool, but `AppProxy.forward()` expects a Starlette `Request` object. A simpler internal method `invoke_task(app_id, task_id, run_id, token)` on AppProxy would be cleaner. This is a minor design decision to make during implementation.
- **Bulk command routing** — The existing `/api/commands` endpoint dispatches single commands via `dispatch()`. Bulk needs either a new endpoint or extension of the existing one. The cleanest approach is a new `POST /api/commands/bulk` endpoint that accepts `{commands: [...], summary: str, source: str}` and routes through `EventStore.commit_bulk()`.

## Sources

- `.gsd/design/APP-PLATFORM-DESIGN.md` §8 (Scheduler), §9 (Permissions), §12 (Bulk EventStore)
- `backend/app/apps/manifest.py` — existing `AppTask.validate_interval` with shorthand + ISO 8601 regex
- `backend/app/events/store.py` — existing `commit()` method (365 lines) — base for `commit_bulk()`
- `backend/sdk/sempkm_app_sdk/clients/` — all 5 client stubs, currently without enforcement
- `backend/app/apps/models.py` — `AppTaskRun`, `AppTaskConfig` tables already defined in S01
- `backend/app/apps/proxy.py` — `AppProxy.forward()` and connection pool pattern
- `backend/app/apps/admin_router.py` — existing admin routes (197 lines), extension point for task history
- `backend/app/services/icons.py` — `IconService._build_cache()` reads manifest icons, extension point for browserVisible
- `backend/app/models/manifest.py` — `ManifestIconDef` model, extension point for browserVisible field
- `backend/app/browser/workspace.py` — `_handle_by_type()` at line 110, filter point for hidden types
