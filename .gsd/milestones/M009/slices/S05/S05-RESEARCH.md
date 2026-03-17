# S05: Scheduler, Permissions, Bulk EventStore & browserVisible — Research

**Date:** 2026-03-16
**Milestone:** M009 — App Platform

## Summary

S05 covers four orthogonal subsystems that share a common dependency (S02's SDK stubs) but are otherwise independent: (1) `AppScheduler` — platform-owned task scheduler with concurrency guard and retry, (2) permission enforcement in SDK clients — command whitelist, IRI prefix, network domain, state graph scoping, (3) `EventStore.commit_bulk()` — summary-only metadata for batch ingestion, and (4) `browserVisible` — filtering hidden types from the object browser.

The codebase is well-prepared. All four subsystems extend existing code with clear seams — no new architectural patterns needed. The SDK client stubs (`CommandClient`, `GraphClient`, `HttpClient`, `StateClient`) are thin wrappers awaiting enforcement logic. The `EventStore.commit()` method has a clean extension point for a summary-only variant. The `ManifestIconDef` in the mental model manifest is the natural home for `browserVisible`. The scheduler is the only genuinely new module (`backend/app/apps/scheduler.py`), but the design doc §8 provides a complete spec.

All four subsystems are unit-testable without Docker. The scheduler's core logic (interval parsing, due-check, concurrency guard, retry backoff) is pure function work. Permission enforcement is input validation. Bulk EventStore builds SPARQL strings. `browserVisible` is a field + filter. Integration testing (scheduler triggering real tasks) deferred to S07.

## Recommendation

Build in this order: **permissions → bulk EventStore → browserVisible → scheduler**. Rationale:

1. **Permissions first** — modifies existing SDK client files (5 files), lowest risk, highest coverage (APP-05). Pure validation logic, easy to test.
2. **Bulk EventStore second** — extends `store.py` with a new method + adds SDK `ctx.commands.bulk()` context manager. Independent of scheduler. Covers APP-11.
3. **browserVisible third** — small scope: one field on `ManifestIconDef`, one filter in `ShapesService.get_types()`. Covers APP-12.
4. **Scheduler last** — the most complex piece. Needs DB interaction (task_config, task_runs), async scheduling loop, proxy integration for task invocation. Admin detail template extension. Covers APP-06. Benefits from permissions being done first (scheduler sends task headers that SDK validates).

## Implementation Landscape

### Key Files

#### Permission Enforcement (APP-05)

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — **Modify.** Currently a thin HTTP wrapper. Add: `allowed_commands: list[str]` constructor param, `app_id: str` for IRI prefix. Reject `command_type not in allowed_commands`. Reject IRIs in params that don't start with `urn:sempkm:app:{app_id}:`. The allowed commands come from `manifest.permissions.commands` — S02's `AppContext` must pass them to `CommandClient`.
- `backend/sdk/sempkm_app_sdk/clients/http.py` — **Modify.** Add `allowed_domains: list[str]` constructor param. Before every GET/POST, parse URL hostname and match against glob patterns (using `fnmatch.fnmatch`). Empty list = no external HTTP allowed.
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — **No change needed.** SPARQL read access is gated at the platform API level (`X-SemPKM-App-Token` claims include `sparql_read`). The SDK client just forwards queries. Platform-side enforcement (if any) is orthogonal.
- `backend/sdk/sempkm_app_sdk/clients/state.py` — **Already scoped.** `StateClient` already hardcodes `graph_iri = f"urn:sempkm:app:{app_id}:state"`. No changes needed — scoping is baked in by construction.
- `backend/sdk/sempkm_app_sdk/context.py` — **Modify.** `AppContext` needs a `permissions` field (the `AppPermissions` object from the manifest, or a simplified dict). Pass it to `CommandClient` and `HttpClient` constructors.

The manifest's permissions object:
```python
class AppPermissions(BaseModel):
    commands: list[str] = []           # e.g. ["object.create", "object.patch"]
    sparql: AppPermissionsSparql = ... # read: bool
    network: list[str] = []            # e.g. ["*", "*.hypothes.is"]
    backgroundTasks: bool = False
    settings: bool = False
```

**SDK runner** (`runner.py`) reads the manifest and constructs `AppContext` — it needs to parse `manifest.permissions` and pass to the context. Currently only passes `app_token`. The manifest is already loaded via `yaml.safe_load(manifest_path)`.

**Design §9 enforcement layers:**
| Layer | Where enforced | How |
|-------|---------------|-----|
| CommandClient | SDK (client-side) | Check `command_type in allowed_commands` before HTTP call |
| IRI prefix | SDK (client-side) | Check all IRIs in params start with `urn:sempkm:app:{app_id}:` |
| HttpClient | SDK (client-side) | Check URL hostname against `permissions.network` globs |
| StateClient | SDK (by construction) | Graph IRI is `urn:sempkm:app:{app_id}:state` — already done |
| Task invocation | SDK (app.py) | `_validate_token()` already checks `X-SemPKM-App-Token` |

Note: D157 decided SDK validates tokens via string comparison, not JWT decode. Permission enforcement is client-side in the SDK, not platform-side JWT claims checking. This is pragmatic for a personal tool — the trust boundary is "apps are locally installed."

#### Bulk EventStore (APP-11)

- `backend/app/events/store.py` — **Modify.** Add `commit_bulk()` method alongside existing `commit()`. The method takes same `operations: list[Operation]` but writes summary-only metadata to the event graph (type `sempkm:BulkEvent`, `sempkm:summary`, `sempkm:source`, `sempkm:operationCount`, `sempkm:affectedCount`). Data triples and materialization are identical. Max batch size enforced (1000 default, configurable).
- `backend/app/events/models.py` — **Modify.** Add `BULK_EVENT_TYPE = SEMPKM.BulkEvent` and summary predicates (`SEMPKM.summary`, `SEMPKM.source`, `SEMPKM.operationCount`, `SEMPKM.affectedCount`).
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — **Modify.** Add `bulk()` context manager method that collects operations, then posts them all at once to a new platform endpoint (or batches them into the existing `/api/commands` endpoint).

The bulk approach from the design doc: summary event graph has ~10 triples (type, timestamp, actor, summary text, source tag, operation count, affected count) vs ~5N triples for standard. Both store the raw data triples identically. Undo granularity differs: bulk = all-or-nothing.

Platform endpoint: need a `POST /api/commands/bulk` endpoint (or extend existing `/api/commands` to accept a `bulk: true` flag + `summary` field). The existing `/api/commands` endpoint dispatches to handlers and calls `EventStore.commit()` — the bulk variant calls `commit_bulk()` instead.

Checking the existing commands endpoint:

- `backend/app/commands/router.py` — houses `POST /api/commands` endpoint
- Commands are dispatched via `dispatch()` → handler → `Operation` → `EventStore.commit()`

For bulk: the SDK's `ctx.commands.bulk()` collects command dicts, posts them to a new `/api/commands/bulk` endpoint that dispatches all, collects `Operation` objects, then calls `EventStore.commit_bulk()`.

#### browserVisible (APP-12)

- `backend/app/models/manifest.py` — **Modify.** Add `browserVisible: bool = True` to `ManifestIconDef`. Types not listed in `icons` default to visible.
- `backend/app/services/shapes.py` — **Modify.** `get_types()` needs to filter out types where the installed model's manifest says `browserVisible: false`. This requires cross-referencing `ShapesService` with `ModelService` (to look up manifests by type IRI).
- `backend/app/services/models.py` — **Extend or expose.** Need a method to query which type IRIs have `browserVisible: false`. Since `ManifestIconDef.type` uses prefixed names (e.g. `bpkm:Note`), the lookup needs prefix expansion.

**Where the filter goes:** The cleanest approach is a new method on `ModelService` or a standalone function: `get_hidden_type_iris() -> set[str]` that iterates installed model manifests, expands prefixed type names against the manifest's `prefixes` dict, and returns IRIs where `browserVisible == False`. Then `ShapesService.get_types()` filters its output against this set.

Alternatively: store `browserVisible` as an RDF triple in the shapes graph at install time. This is cleaner for SPARQL queries but adds install-time complexity. Given that `get_types()` is already in Python (iterating `NodeShapeForm` objects), the Python-side filter is simpler.

**Impact scope:** `get_types()` is called by:
- `_handle_by_type()` in workspace.py (nav tree)
- Type filter pills in generic views
- VFS mount form type multi-select

All three benefit from the same filter.

#### Scheduler (APP-06)

- `backend/app/apps/scheduler.py` — **New file.** The `AppScheduler` class. Core responsibilities:
  - Periodic check loop (every 60s) — which tasks are due
  - Interval parsing: already validated by `AppTask.validate_interval()` in the manifest, but the scheduler needs to convert intervals to seconds for comparison
  - Per-task state: `last_run_at`, `is_running` flag (concurrency guard)
  - Task invocation: `POST /app/{appId}/_tasks/{taskId}` through the proxy (uses `AppProxy.forward()`)
  - Result recording: insert `AppTaskRun` row with status, duration, error
  - Retry: on failure, schedule immediate retry with exponential backoff up to `maxRetries`
  - User-adjustable intervals: check `app_task_config` table for overrides
  - Pause support: skip tasks where `app_task_config.paused == True`

- `backend/app/main.py` — **Modify.** Create `AppScheduler` in `lifespan()`, pass it `AppManager` and `AppProxy` and `session_factory`. Start the scheduler loop as a background task. Stop it on shutdown.

- `backend/app/apps/admin_router.py` — **Modify.** Extend `app_detail()` to query `AppTaskRun` records and `AppTaskConfig` overrides for the task history section. Add endpoints for interval adjustment (`POST /admin/apps/{app_id}/tasks/{task_id}/interval`) and pause/resume (`POST /admin/apps/{app_id}/tasks/{task_id}/pause`).

- `backend/app/templates/admin/apps/detail.html` — **Modify.** Replace the task history placeholder with real content: table of recent task runs (task_id, status, started, duration, error) and per-task interval/pause controls.

**Scheduler internals:**

```python
class AppScheduler:
    def __init__(self, manager, proxy, session_factory):
        self._manager = manager
        self._proxy = proxy
        self._session_factory = session_factory
        self._running_tasks: dict[tuple[str, str], datetime] = {}  # (app_id, task_id) → start_time
        self._task: asyncio.Task | None = None

    async def start(self):
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while True:
            await asyncio.sleep(60)
            await self._check_due_tasks()

    async def _check_due_tasks(self):
        for app_id in self._manager.registry.list_apps():
            manifest = self._manager.registry.get_manifest(app_id)
            status = await self._manager.get_status(app_id)
            if status.get("status") != "running":
                continue
            for task in manifest.tasks:
                if self._is_due(app_id, task):
                    await self._invoke_task(app_id, task)
```

**Interval to seconds conversion:** The manifest validator already accepts shorthand (`5m`, `1h`) and ISO 8601 (`PT5M`). Need a `parse_interval_seconds(interval: str) -> int` function.

### Build Order

1. **Permissions** — Modify SDK clients + context + runner. Unit tests for each enforcement. ~5 files changed, ~15-20 tests.
2. **Bulk EventStore** — Extend `store.py`, add models constants, add platform endpoint, add SDK bulk context manager. ~4 files changed, ~10-15 tests.
3. **browserVisible** — Add field to manifest schema, add filter to shapes service. ~3 files changed, ~5-8 tests.
4. **Scheduler** — New `scheduler.py`, lifespan wiring, admin extensions. ~5 files changed, ~15-20 tests.
5. **Admin detail template** — Replace placeholders with real task history and controls. ~2 files changed.

### Verification Approach

**Unit tests (all run without Docker, <5s):**

- **Permissions:**
  - `CommandClient.execute()` rejects command_type not in allowed list → `PermissionError`
  - `CommandClient.execute()` rejects IRI params not starting with `urn:sempkm:app:{app_id}:` → `PermissionError`
  - `CommandClient.execute()` allows whitelisted commands with valid IRIs
  - `HttpClient.get()` rejects URL with hostname not matching any `network` glob → `PermissionError`
  - `HttpClient.get()` allows URL matching a `network` glob (including `*` wildcard)
  - `HttpClient.get()` allows request when network list is `["*"]`
  - Glob matching: `*.hypothes.is` matches `api.hypothes.is` but not `evil.com`
  - `AppContext` passes permissions to clients correctly

- **Bulk EventStore:**
  - `commit_bulk()` creates event graph with `sempkm:BulkEvent` type
  - `commit_bulk()` records summary, source, operationCount, affectedCount
  - `commit_bulk()` materializes inserts and deletes identically to `commit()`
  - `commit_bulk()` rejects batch over 1000 operations (configurable limit)
  - `commit_bulk()` rolls back on failure (same as `commit()`)

- **browserVisible:**
  - `ManifestIconDef` with `browserVisible: false` parses correctly
  - `ManifestIconDef` defaults `browserVisible: true`
  - `get_types()` excludes types with `browserVisible: false` (mock ShapesService + ModelService)
  - Types not in `icons` list remain visible

- **Scheduler:**
  - `parse_interval_seconds("5m")` → 300
  - `parse_interval_seconds("1h")` → 3600
  - `parse_interval_seconds("PT5M")` → 300
  - Due check: task is due when `now - last_run_at >= interval`
  - Concurrency guard: skip task if previous invocation still running
  - Retry backoff: 1s, 2s, 4s for maxRetries=3, backoffMultiplier=2
  - Task history recording: `AppTaskRun` row created with correct status/duration
  - Config override: `app_task_config.interval_override` takes precedence over manifest default
  - Pause: `app_task_config.paused == True` skips task

- **Admin endpoints:**
  - `GET /admin/apps/{app_id}` includes task history and interval controls
  - `POST /admin/apps/{app_id}/tasks/{task_id}/interval` updates `app_task_config`
  - `POST /admin/apps/{app_id}/tasks/{task_id}/pause` toggles pause state

## Constraints

- **SDK is client-side enforcement (D157):** Permission checks happen in the SDK, not the platform. The platform API doesn't re-validate app permissions on every request — it trusts the JWT token's `sub` claim. This means a malicious app could bypass enforcement by making direct HTTP calls to the platform API. Acceptable for a personal tool with locally-installed apps.
- **Interval minimum is 30 seconds:** Already enforced by `AppTask.validate_interval()` in the manifest schema. The scheduler must honor this floor.
- **Batch size limit 1000:** Design doc default. Should be a constant in `store.py`, not a setting.
- **No new dependencies needed.** `fnmatch` is stdlib. All other libraries already in the project.
- **Admin router is `apps/admin_router.py`** (D150) — task management endpoints go here, not in the main admin router.
- **Scheduler runs in the main asyncio event loop** — no separate thread or process. This is fine for <10 apps with minute-level intervals.

## Common Pitfalls

- **IRI prefix enforcement must handle nested params.** The `object.create` command has `params: {"iri": "urn:..."}` but also `params: {"properties": {"dcterms:references": "urn:..."}}`). The IRI check should scan all string values in the params dict recursively, not just the top-level `iri` key.
- **Network glob matching with ports.** `fnmatch.fnmatch("api.hypothes.is:443", "*.hypothes.is")` returns `False` because the port is part of the string. Strip port before matching.
- **Scheduler startup timing.** The scheduler should wait until `auto_start()` completes before beginning its first check cycle. Otherwise it might check tasks for apps that haven't started yet.
- **Bulk commit + permissions interaction.** The SDK's `ctx.commands.bulk()` context manager should enforce permissions on each `batch.add()` call, not just at commit time. Fail fast on invalid commands.
- **browserVisible filter must not break when no models are installed.** `get_hidden_type_iris()` should return an empty set, not raise.

## Open Risks

- **Scheduler clock drift.** A 60s sleep loop will drift over time. For minute-level intervals this is negligible, but if an app configures a 30s interval, the effective period will be 60-90s (scheduler check granularity). This is acceptable for v1 — the design doc shows 60s check interval.
- **Bulk commit memory.** 1000 operations × ~50 triples each = 50K tuples in memory. With string serialization, this could be 5-10MB per bulk commit. Should be fine for a personal tool.

## Sources

- Design doc §8 (Scheduler): `.gsd/design/APP-PLATFORM-DESIGN.md` lines 939-1007
- Design doc §9 (Permissions): `.gsd/design/APP-PLATFORM-DESIGN.md` lines 1008-1063
- Design doc §12 (Bulk EventStore): `.gsd/design/APP-PLATFORM-DESIGN.md` lines 1321-1424
- S02 summary: Forward Intelligence on token validation and permission enforcement deferral
- S03 summary: Admin detail template placeholders for task history (line 159) and renderer assignments (line 163)
