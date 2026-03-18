# S05: Scheduler, Permissions, Bulk EventStore & browserVisible — UAT

**Milestone:** M009
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All S05 deliverables are backend logic (scheduler, permissions, EventStore, type filtering) proved by 113 contract tests. Live runtime proof deferred to S07 when a real test app exercises these features through the Docker stack.

## Preconditions

- Backend venv exists at `backend/.venv/` with all dependencies installed
- No Docker stack required — all tests run with mocks
- Working directory: worktree root or project root with `cd backend`

## Smoke Test

```bash
cd backend && .venv/bin/pytest tests/test_app_scheduler.py tests/test_sdk_permissions.py tests/test_bulk_eventstore.py tests/test_browser_visible.py -v
```

All 113 tests pass in <2s.

## Test Cases

### 1. Interval Parsing — Shorthand and ISO 8601

1. Run `pytest tests/test_app_scheduler.py::TestParseIntervalSeconds -v`
2. **Expected:** 21 tests pass — covering "30s", "5m", "1h", "1d", "PT5M", "PT1H30M", floor enforcement (29s → ValueError), ceiling enforcement (86401s → ValueError), whitespace stripping, and invalid formats.

### 2. Scheduler Concurrency Guard

1. Run `pytest tests/test_app_scheduler.py::TestConcurrencyGuard -v`
2. **Expected:** 2 tests pass — _running_tasks starts empty; task added during invocation causes skip on re-evaluation.

### 3. Retry with Exponential Backoff

1. Run `pytest tests/test_app_scheduler.py::TestRetryBehavior -v`
2. **Expected:** 4 tests pass — failure triggers retry, exhausted retries records error status, exception triggers retry, zero max_retries means no retry.

### 4. Task Config — Pause and Interval Override

1. Run `pytest tests/test_app_scheduler.py::TestTaskConfig -v`
2. **Expected:** 2 tests pass — paused tasks are skipped entirely; interval overrides change when a task is due.

### 5. Tick Dispatches Due Tasks

1. Run `pytest tests/test_app_scheduler.py::TestTickLogic -v`
2. **Expected:** 3 tests pass — due task dispatched, not-due task skipped, app without tasks skipped.

### 6. Command Whitelist Enforcement

1. Run `pytest tests/test_sdk_permissions.py::TestCommandWhitelist -v`
2. **Expected:** 3 tests pass — allowed command succeeds, rejected command raises PermissionError, empty whitelist blocks all.

### 7. IRI Prefix Enforcement

1. Run `pytest tests/test_sdk_permissions.py::TestIRIPrefix -v`
2. **Expected:** 8 tests pass — object.patch, body.set, edge.create (source + target separately), edge.patch validated against prefix. object.create has no IRI check (platform assigns IRI).

### 8. SPARQL Read Gate

1. Run `pytest tests/test_sdk_permissions.py::TestSparqlReadGate -v`
2. **Expected:** 3 tests pass — sparql_read=True allows query, sparql_read=False blocks query, default is blocked.

### 9. HTTP Domain Enforcement

1. Run `pytest tests/test_sdk_permissions.py::TestDomainEnforcement -v`
2. **Expected:** 9 tests pass — exact domain, glob pattern (*.example.com), wildcard ["*"] allows all, empty list blocks all, enforcement on get/post/request methods, multiple domains.

### 10. AppContext Permissions Threading

1. Run `pytest tests/test_sdk_permissions.py::TestAppContextPermissions -v`
2. **Expected:** 8 tests pass — IRI prefix format, command whitelist received, sparql_read true/false/default, domain list received, empty network, state graph scoped to app.

### 11. Bulk EventStore — Summary Metadata

1. Run `pytest tests/test_bulk_eventstore.py::TestCommitBulkMetadata -v`
2. **Expected:** 5 tests pass — BulkEvent type, bounded triple count (~7-8), summary and source in metadata, performed_by included when provided and omitted when None.

### 12. Bulk Batch Size Limit

1. Run `pytest tests/test_bulk_eventstore.py::TestBulkBatchSizeLimit -v`
2. **Expected:** 2 tests pass — 1000 operations allowed, 1001 raises ValueError.

### 13. SDK Bulk Context Manager

1. Run `pytest tests/test_bulk_eventstore.py::TestSDKBulkContextManager -v`
2. **Expected:** 4 tests pass — accumulates and submits on clean exit, discards on exception, empty batch skips POST, permission check runs on add().

### 14. browserVisible Manifest Parsing

1. Run `pytest tests/test_browser_visible.py::TestManifestIconDefBrowserVisible -v`
2. **Expected:** 4 tests pass — default is true, explicit true, explicit false, schema with hidden icons.

### 15. Hidden Type Resolution from Manifests

1. Run `pytest tests/test_browser_visible.py::TestGetHiddenTypeIris -v`
2. **Expected:** 7 tests pass — None models_dir returns empty, nonexistent dir returns empty, all-visible returns empty, hidden types resolved with correct prefix expansion, multiple models aggregated, bad manifests silently skipped.

### 16. ShapesService Type Filtering

1. Run `pytest tests/test_browser_visible.py::TestGetTypesFiltering -v`
2. **Expected:** 6 tests pass — no exclude, None, empty set all return all types; exclude_iris filters hidden; multiple exclusions work; nonexistent IRI is harmless.

## Edge Cases

### Interval Floor Boundary

1. Run `pytest tests/test_app_scheduler.py::TestParseIntervalSeconds::test_floor_at_boundary -v`
2. **Expected:** "30s" parses to 30 (at the floor), but "29s" raises ValueError.

### Bulk Rollback on Transaction Failure

1. Run `pytest tests/test_bulk_eventstore.py::TestBulkRollback -v`
2. **Expected:** 2 tests pass — both transaction failure and commit failure trigger full rollback with no partial state.

### Bad Manifest Files Skipped During browserVisible Scan

1. Run `pytest tests/test_browser_visible.py::TestGetHiddenTypeIris::test_bad_manifest_skipped -v`
2. **Expected:** Malformed manifest.yaml files are silently skipped — get_hidden_type_iris() returns types from valid manifests only.

### PermissionError Message Quality

1. In a Python shell:
   ```python
   from sempkm_app_sdk.clients.commands import CommandClient
   c = CommandClient(base_url="http://x", token="t", allowed_commands={"body.set"}, iri_prefix="urn:sempkm:app:test:")
   try:
       import asyncio; asyncio.run(c.execute("edge.create", source="urn:x", target="urn:y"))
   except PermissionError as e:
       print(str(e))
   ```
2. **Expected:** Error message includes the rejected command type ("edge.create") and the allowed set ("{'body.set'}").

## Failure Signals

- Any of the 113 tests failing indicates a regression in scheduler logic, permission enforcement, bulk EventStore, or browserVisible filtering.
- `test_app_scheduler.py` failures: check `scheduler.py` for interval parsing regex, backoff calculation, or concurrency guard set management.
- `test_sdk_permissions.py` failures: check `commands.py` `_IRI_PARAMS` dict, `graph.py` `sparql_read` flag, or `http.py` `_check_domain` method.
- `test_bulk_eventstore.py` failures: check `store.py` `commit_bulk()` for metadata triple generation or transaction handling.
- `test_browser_visible.py` failures: check `manifest.py` for `browserVisible` field, `services/models.py` for `get_hidden_type_iris()`, or `shapes.py` for `exclude_iris` filtering.
- Full suite regression (1344 total): check `test_app_admin.py` fixture (async_session_factory) and `test_sdk_app.py` (permission constructor args).

## Requirements Proved By This UAT

- APP-05 — Permission enforcement proved by 33 tests covering command whitelist, IRI prefix, SPARQL gate, domain globs, and AppContext threading (contract level)
- APP-06 — Task scheduler proved by 40 tests covering interval parsing, concurrency guard, retry backoff, task config, tick logic, and lifecycle (contract level)
- APP-11 — Bulk EventStore proved by 18 tests covering summary metadata, batch limits, materialization, rollback, and SDK context manager (contract level)
- APP-12 — browserVisible proved by 22 tests covering manifest parsing, prefix expansion, hidden type resolution, and ShapesService filtering (contract level)
- APP-03 — SDK extended (permission enforcement + bulk context manager)
- APP-10 — Admin task history section (template + endpoints)
- APP-13 — app_task_runs and app_task_config table usage

## Not Proven By This UAT

- Live scheduler firing against a real app subprocess (requires Docker stack + real test app — S07)
- Permission enforcement through the full IPC proxy chain (requires running app via UDS — S07)
- Bulk EventStore through HTTP API with real triplestore materialization (requires Docker stack — S07)
- browserVisible filtering in a live object browser with real installed models (requires Docker stack — S07)
- Admin task history UI rendering with real data (requires running scheduler with apps — S07)

## Notes for Tester

- All tests are pure contract tests with mocks — no Docker, no network, no filesystem side effects. They run in <2s total.
- The 4 SDK bulk context manager tests in `test_bulk_eventstore.py` require `sempkm_app_sdk` to be importable. If running from a fresh venv without the SDK installed, these 4 tests will fail with ImportError — install the SDK first: `pip install -e sdk/`.
- The `test_app_scheduler.py::TestTickLogic::test_tick_skips_not_due_task` test produces a RuntimeWarning about an unawaited coroutine — this is a mock artifact, not a real issue.
