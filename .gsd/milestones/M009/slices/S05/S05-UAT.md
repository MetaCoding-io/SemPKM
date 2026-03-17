# S05: Scheduler, Permissions, Bulk EventStore & browserVisible — UAT

**Milestone:** M009
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All S05 deliverables are contract-level (scheduler logic, permission enforcement, EventStore extension, manifest parsing) testable with mocks and unit tests. Live runtime proof deferred to S07 integration tests.

## Preconditions

- Backend venv active: `cd backend && source .venv/bin/activate`
- All S05 test files present: `test_app_scheduler.py`, `test_app_permissions.py`, `test_bulk_eventstore.py`, `test_browser_visible.py`
- No Docker required — all tests use mocks

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_app_scheduler.py tests/test_app_permissions.py tests/test_bulk_eventstore.py tests/test_browser_visible.py -v --tb=short
```
Expected: 102 tests pass, 0 failures.

## Test Cases

### 1. Interval Parsing Covers All Formats

1. Run: `pytest tests/test_app_scheduler.py -k "parse_interval" -v`
2. **Expected:** Tests pass for shorthand formats (30s, 5m, 1h, 1d) and ISO 8601 formats (PT5M, PT1H30M, PT30S). Invalid strings raise ValueError.

### 2. Scheduler Concurrency Guard Prevents Double-Fire

1. Run: `pytest tests/test_app_scheduler.py -k "concurrency" -v`
2. **Expected:** When a task is already in `_running_tasks`, scheduler skips it and logs at DEBUG level.

### 3. Retry Backoff Computes Correctly

1. Run: `pytest tests/test_app_scheduler.py -k "retry" -v`
2. **Expected:** Backoff delay = `backoffMultiplier ** (attempt - 1)`, capped at maxBackoff. After maxRetries exceeded, task recorded as "error".

### 4. Task Runs Recorded in DB

1. Run: `pytest tests/test_app_scheduler.py -k "task_run" -v`
2. **Expected:** AppTaskRun row created with status="running" at invocation start, updated to "success" or "error" with duration_ms and error_message on completion.

### 5. Admin Task Config CRUD

1. Run: `pytest tests/test_app_scheduler.py -k "admin" -v`
2. **Expected:** POST interval endpoint validates format and upserts AppTaskConfig. POST pause endpoint toggles paused boolean. Admin detail shows task section with history and controls.

### 6. CommandClient Rejects Unpermitted Commands

1. Run: `pytest tests/test_app_permissions.py -k "TestCommandWhitelist" -v`
2. **Expected:** Allowed commands pass through. Disallowed commands raise PermissionError with the command type and allowed list in the message. Empty whitelist blocks all.

### 7. IRI Prefix Enforcement Is Recursive

1. Run: `pytest tests/test_app_permissions.py -k "TestIRIPrefixEnforcement" -v`
2. **Expected:** IRIs matching `urn:sempkm:app:{app_id}:*` pass. IRIs with other prefixes (including http://) are caught even when nested multiple levels deep in dicts/lists. Non-IRI strings (no urn:/http prefix) are ignored.

### 8. HttpClient Domain Enforcement

1. Run: `pytest tests/test_app_permissions.py -k "TestDomainEnforcement" -v`
2. **Expected:** Matching domains pass. Non-matching domains raise PermissionError. Wildcard `["*"]` allows all. Glob `*.hypothes.is` matches `api.hypothes.is` but not `hypothes.is`. Port numbers stripped before matching. Empty list blocks all. None (unconfigured) allows all.

### 9. GraphClient SPARQL Gate

1. Run: `pytest tests/test_app_permissions.py -k "TestSparqlReadGate" -v`
2. **Expected:** `sparql_read=True` allows queries. `sparql_read=False` raises PermissionError. Default is True (permissive).

### 10. AppContext Threads Permissions to All Clients

1. Run: `pytest tests/test_app_permissions.py -k "TestAppContextPermissions" -v`
2. **Expected:** `permissions.commands` → CommandClient._allowed_commands. `permissions.network` → HttpClient._allowed_domains. `permissions.sparql_read` → GraphClient._sparql_read. No permissions → all clients permissive. Missing keys → restrictive defaults.

### 11. Bulk EventStore Summary Metadata

1. Run: `pytest tests/test_bulk_eventstore.py -v`
2. **Expected:** commit_bulk() produces BulkEvent type with summary, source, operationCount, affectedCount. Batch size >1000 raises ValueError. Data triples accumulate correctly.

### 12. browserVisible Filtering

1. Run: `pytest tests/test_browser_visible.py -v`
2. **Expected:** Types with `browserVisible: false` returned by get_hidden_type_iris(). ShapesService.get_types() respects exclude_iris parameter. Multiple models and bad manifests handled gracefully.

### 13. Full Suite Regression Check

1. Run: `pytest tests/ -v --tb=short`
2. **Expected:** 1196+ passed. Only allowed failures: 5 in test_renderer_overrides.py (pre-existing Python 3.14 asyncio deprecation, S06 staging).

## Edge Cases

### Scheduler With No Running Apps

1. Start scheduler with no apps in registry or all apps stopped.
2. **Expected:** _check_due_tasks() exits early with no errors. No task invocations.

### Scheduler With Paused Tasks

1. Set AppTaskConfig.paused=True for a task.
2. **Expected:** Scheduler skips the task and logs "paused" at DEBUG level. No invocation.

### IRI Prefix With HTTP URLs

1. Execute `object.create` with `{"source": "http://external.com/article"}` through a CommandClient with IRI prefix enforcement.
2. **Expected:** PermissionError raised because `http://external.com/article` doesn't start with `urn:sempkm:app:{app_id}:`.

### Bulk Batch Size Exactly 1000

1. Call commit_bulk() with exactly 1000 operations.
2. **Expected:** Succeeds. At 1001, raises ValueError.

### browserVisible Default True

1. Parse a ManifestIconDef without the browserVisible field.
2. **Expected:** `browserVisible` defaults to True. Type not hidden.

### HttpClient With No Permissions

1. Create AppContext with permissions=None.
2. **Expected:** HttpClient._allowed_domains is None — all domains allowed (permissive default).

### GraphClient With Permissions But No sparql_read Key

1. Create AppContext with permissions={"commands": ["object.create"]}.
2. **Expected:** GraphClient._sparql_read is False — defaults to restrictive when permissions dict exists.

## Failure Signals

- Any of the 102 S05-specific tests failing
- PermissionError not raised when expected (permission bypass)
- PermissionError raised with missing diagnostic info (offending value not in message)
- AppTaskRun rows not created or missing error_message on failure
- get_hidden_type_iris() returning wrong set or crashing on bad manifest
- Full suite regression count > 5 (only test_renderer_overrides.py allowed)

## Requirements Proved By This UAT

- APP-05 — Permission enforcement across all 5 SDK client types (33 tests)
- APP-06 — Platform-owned task scheduler with concurrency, retry, admin controls (31 tests)
- APP-11 — Bulk EventStore with summary metadata and batch limits (16 tests)
- APP-12 — browserVisible field with object browser filtering (22 tests)
- APP-10 — Admin monitoring portal extended with task history section

## Not Proven By This UAT

- Real scheduler invocation through Docker stack (deferred to S07)
- Real subprocess UDS communication for task invocation (mocked in tests)
- Admin UI visual rendering of task history section (template tested via string matching, not browser)
- Bulk EventStore interaction with real RDF4J triplestore (commit_bulk uses mock client)
- browserVisible filtering with real models installed in Docker stack

## Notes for Tester

- The 5 failures in test_renderer_overrides.py are pre-existing (Python 3.14 asyncio.get_event_loop() deprecation) and not related to S05. They exist in S06-staged code.
- The scheduler CHECK_INTERVAL is 60 seconds — tests mock this, so they run instantly.
- Permission tests use mock httpx clients — no network calls are made.
- The browserVisible tests create temporary model directories with manifest.yaml files.
