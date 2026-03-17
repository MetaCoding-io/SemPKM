# S05: Scheduler, Permissions, Bulk EventStore & browserVisible — UAT

**Milestone:** M009
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All S05 deliverables are contract-level (SDK clients, EventStore, scheduler logic, manifest fields). 121 unit tests verify behavior without Docker. Integration testing deferred to S07.

## Preconditions

- Backend venv available at `backend/.venv`
- Working directory is the M009 worktree (or main project with M009 changes merged)
- No Docker stack required — all tests are unit/contract level

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_app_permissions.py tests/test_bulk_eventstore.py tests/test_browser_visible.py tests/test_app_scheduler.py tests/test_app_admin.py -v
```
Expected: 121 tests pass, 0 failures.

## Test Cases

### 1. Permission Enforcement — Command Whitelist

1. Create a `CommandClient` with `allowed_commands=["object.create"]`
2. Call `execute("object.create", {...})` — should succeed
3. Call `execute("object.delete", {...})` — should raise `PermissionError`
4. **Expected:** PermissionError message includes `"object.delete"` and the allowed list `["object.create"]`

### 2. Permission Enforcement — IRI Prefix

1. Create a `CommandClient` with `app_id="rss-reader"`
2. Call `execute("object.create", {"iri": "urn:sempkm:app:rss-reader:article-1"})` — should succeed
3. Call `execute("object.create", {"iri": "urn:sempkm:model:basic-pkm:note-1"})` — should raise `PermissionError`
4. **Expected:** PermissionError message includes the offending IRI and the required prefix `urn:sempkm:app:rss-reader:`

### 3. Permission Enforcement — Network Domains

1. Create an `HttpClient` with `allowed_domains=["*.hypothes.is", "api.example.com"]`
2. Call `get("https://api.hypothes.is/annotations")` — should succeed (matches `*.hypothes.is`)
3. Call `get("https://evil.com/steal")` — should raise `PermissionError`
4. Call `get("https://api.example.com:443/data")` — should succeed (port stripped)
5. **Expected:** PermissionError includes hostname `evil.com` and the allowed patterns

### 4. AppContext Permissions Wiring

1. Create `AppContext` with `permissions={"commands": ["object.create"], "network": ["*.example.com"]}`
2. Access `ctx.commands` — should have `_allowed_commands == ["object.create"]`
3. Access `ctx.http` — should have `_allowed_domains == ["*.example.com"]`
4. **Expected:** Permissions flow from AppContext to SDK clients correctly

### 5. Bulk EventStore — Summary Metadata

1. Create 5 `Operation` objects with inserts
2. Call `commit_bulk(operations, summary="Test batch", source="test")`
3. Query the event graph for the created event
4. **Expected:** Event has type `sempkm:BulkEvent`, `sempkm:summary` = "Test batch", `sempkm:operationCount` = 5. No per-operation metadata triples.

### 6. Bulk EventStore — Size Limit

1. Create 1001 `Operation` objects
2. Call `commit_bulk(operations, ...)`
3. **Expected:** `ValueError` raised with message including "1000" and "1001"

### 7. SDK Bulk Context Manager

1. Create `CommandClient` with `allowed_commands=["object.create"]`
2. Use `async with client.bulk("Test", "test") as batch:`
3. Call `batch.add("object.create", {"iri": "urn:sempkm:app:test:obj-1"})`
4. Call `batch.add("object.delete", {...})` — should raise `PermissionError` immediately
5. **Expected:** Permission check happens on `add()`, not on context exit

### 8. browserVisible — Field Default

1. Parse a manifest icon def without `browserVisible` field
2. **Expected:** `icon_def.browserVisible` is `True`

### 9. browserVisible — Hidden Type Collection

1. Create a temp directory with a model manifest containing `browserVisible: false` on one type
2. Call `get_hidden_type_iris(temp_dir)`
3. **Expected:** Returns set containing the expanded IRI of the hidden type

### 10. browserVisible — Type Filtering

1. Mock `ShapesService.get_node_shapes()` to return 3 types
2. Call `get_types(exclude_iris={"urn:type:Hidden"})`
3. **Expected:** Returns 2 types, excluding the hidden one

### 11. Scheduler — Interval Parsing

1. Call `parse_interval_seconds("5m")` — **Expected:** 300
2. Call `parse_interval_seconds("1h")` — **Expected:** 3600
3. Call `parse_interval_seconds("PT5M")` — **Expected:** 300
4. Call `parse_interval_seconds("PT1H30M")` — **Expected:** 5400
5. Call `parse_interval_seconds("invalid")` — **Expected:** `ValueError`

### 12. Scheduler — Concurrency Guard

1. Start a task invocation for `(app_id, task_id)`
2. Before it completes, check if the same task is due
3. **Expected:** Task skipped due to concurrency guard
4. After completion, check again — **Expected:** Task is eligible

### 13. Scheduler — Admin Interval Adjustment

1. POST to `/admin/apps/{app_id}/tasks/{task_id}/interval` with `interval=10m`
2. Query `app_task_config` table
3. **Expected:** Row exists with `interval_override = "10m"`

### 14. Scheduler — Admin Pause Toggle

1. POST to `/admin/apps/{app_id}/tasks/{task_id}/pause`
2. Query `app_task_config` table
3. **Expected:** Row exists with `paused = True`
4. POST again
5. **Expected:** `paused` toggled to `False`

### 15. Admin Detail — Task History Display

1. Create `AppTaskRun` rows with various statuses (success, error, running)
2. Render admin detail page for the app
3. **Expected:** HTML contains task IDs, status badges, duration, error messages

## Edge Cases

### Empty allowed_commands list blocks all commands

1. Create `CommandClient` with `allowed_commands=[]`
2. Call any `execute()` — **Expected:** `PermissionError`

### None allowed_domains permits all

1. Create `HttpClient` with `allowed_domains=None`
2. Call `get("https://anything.com")` — **Expected:** No PermissionError

### Empty bulk batch skips HTTP

1. Use `async with client.bulk(...) as batch:` without calling `add()`
2. **Expected:** No HTTP POST to `/api/commands/bulk`

### Bad manifest skipped in hidden type collection

1. Directory with invalid YAML manifest alongside valid one
2. Call `get_hidden_type_iris(dir)`
3. **Expected:** Returns hidden types from valid manifest, skips bad one without error

### Scheduler loop survives exceptions

1. Scheduler `_check_due_tasks()` raises an exception
2. **Expected:** Loop continues, exception logged, next check runs normally

## Failure Signals

- Any of the 121 tests failing indicates a regression
- `PermissionError` not raised on unpermitted operations = security hole
- `app_task_runs` table empty after scheduler runs = scheduler not recording history
- Hidden types appearing in nav tree = `get_hidden_types()` not called at route
- `ValueError` not raised for >1000 bulk ops = size limit broken

## Requirements Proved By This UAT

- APP-05 — Permission enforcement (test cases 1-4, edge cases 1-2)
- APP-06 — Task scheduler (test cases 11-15, edge case 5)
- APP-11 — Bulk EventStore (test cases 5-7, edge case 3)
- APP-12 — browserVisible (test cases 8-10, edge case 4)
- APP-10 — Admin task history (test cases 13-15)

## Not Proven By This UAT

- Live Docker integration — scheduled task actually fires against a running app subprocess (deferred to S07)
- nginx proxy behavior for task invocation endpoints
- Real manifest permissions loaded from an installed app's YAML
- Browser UI rendering of hidden types (visual verification deferred to S07 E2E)
- Bulk commit undo (all-or-nothing rollback in real triplestore)

## Notes for Tester

- All test cases map directly to existing pytest tests — run the smoke test command to verify everything at once
- The scheduler's 60-second loop makes live testing slow; unit tests mock the timing
- `get_hidden_type_iris()` uses `/app/models` as the default path (Docker mount) — tests use temp directories
