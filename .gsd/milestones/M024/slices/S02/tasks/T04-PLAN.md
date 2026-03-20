---
estimated_steps: 6
estimated_files: 1
---

# T04: Sync engine unit tests

**Slice:** S02 — Column mapping configuration UI + pull sync
**Milestone:** M024

## Description

Create `test_monday_sync_engine.py` with 100+ unit tests proving the sync engine handles all cases — SPARQL lookups, create/update classification, two-phase bulk, group→taskGroup, subitem→parentTask edges, per-item error isolation, push stub, and all helper functions. Uses the same importlib + mock client pattern as the Jira sync engine tests.

**Relevant skills:** Load the `test` skill for test generation patterns.

## Steps

1. **Create file with importlib module loading.** Path: `backend/tests/test_monday_sync_engine.py`. Load modules in dependency order:
   ```python
   _SERVICES_DIR = Path(__file__).resolve().parent.parent.parent / "apps" / "monday-sync" / "services"
   ```
   Load in order: `monday_client.py` → `auth.py` → `field_mapper.py` → `person_matcher.py` → `sync_engine.py`. This order matters because sync_engine imports from the others.

   Import key functions: `pull_sync`, `push_sync`, `_find_existing_task`, `_build_create_command`, `_build_update_commands`, `_submit_commands_batched`, `_make_result`, `_compute_status`, `BATCH_SIZE`. Also `BPKM` and `compute_slug` from field_mapper.

2. **Build mock clients.** Follow the Jira test pattern exactly:

   ```python
   class MockStateClient:
       """In-memory key-value store mirroring SDK StateClient."""
       def __init__(self, data=None):
           self._data = dict(data or {})
       async def get(self, key): return self._data.get(key)
       async def set(self, key, value): self._data[key] = value

   class MockSettingsClient:
       """In-memory settings store — separate from state."""
       def __init__(self, data=None):
           self._data = dict(data or {})
       async def get(self, key): return self._data.get(key)
       async def set(self, key, value): self._data[key] = value

   class MockGraphClient:
       """Stub for GraphClient — returns SPARQL results by slug pattern matching."""
       def __init__(self, slug_map=None, email_to_iri=None, body_map=None):
           self.slug_map = slug_map or {}
           self.email_to_iri = email_to_iri or {}
           self.body_map = body_map or {}
           self.queries = []
       
       async def query(self, sparql):
           self.queries.append(sparql)
           # Task lookup: STRENDS + /Task/ + "monday"
           if "STRENDS" in sparql and "/Task/" in sparql:
               for slug, info in self.slug_map.items():
                   if slug in sparql:
                       binding = {"task": {"type": "uri", "value": info["iri"]}}
                       if info.get("status"):
                           binding["status"] = {"type": "literal", "value": info["status"]}
                       if info.get("externalId"):
                           binding["extId"] = {"type": "literal", "value": info["externalId"]}
                       if info.get("lastSyncedAt"):
                           binding["lastSynced"] = {"type": "literal", "value": info["lastSyncedAt"]}
                       return {"results": {"bindings": [binding]}}
           # PersonMatcher email lookup
           if "foaf" in sparql.lower() or "crm:email" in sparql.lower():
               for email, iri in self.email_to_iri.items():
                   if email.lower() in sparql.lower():
                       return {"results": {"bindings": [
                           {"person": {"type": "uri", "value": iri}}
                       ]}}
           return {"results": {"bindings": []}}
   
   class MockHttpClient:
       """Records bulk command POST requests."""
       def __init__(self, responses=None):
           self.requests = []
           self.responses = responses or []
           self._call_count = 0
       
       async def post(self, url, json=None):
           self.requests.append({"url": url, "json": json})
           if self._call_count < len(self.responses):
               resp = self.responses[self._call_count]
               self._call_count += 1
               return resp
           return MockResponse(200, {"results": []})
       
       async def request(self, method, url, **kwargs):
           # For MondayClient._execute_query
           self.requests.append({"method": method, "url": url, **kwargs})
           return MockResponse(200, {"data": {}})
   
   class MockResponse:
       def __init__(self, status_code, data=None):
           self.status_code = status_code
           self._data = data if data is not None else {}
       def json(self): return self._data
       def raise_for_status(self):
           if self.status_code >= 400:
               raise Exception(f"HTTP {self.status_code}")
   
   class MockCommandsClient:
       """Exposes _client for bulk bypass."""
       def __init__(self, http_client):
           self._client = http_client
   ```

   **Critical:** Use `data if data is not None else {}` (not `data or {}`) for MockResponse — per KNOWLEDGE.md Pattern #2, empty list `[]` is falsy in Python and would silently become `{}`.

   Build a `MockContext` dataclass:
   ```python
   class MockContext:
       def __init__(self, state=None, settings=None, graph=None, http=None, commands=None):
           self.state = state or MockStateClient()
           self.settings = settings or MockSettingsClient()
           self.graph = graph or MockGraphClient()
           self.http = http or MockHttpClient()
           self.commands = commands or MockCommandsClient(MockHttpClient())
   ```

3. **Test SPARQL lookup helpers.** 10+ tests:
   - `_find_existing_task` — returns task info when slug matches
   - `_find_existing_task` — returns None when no match
   - `_find_existing_task` — includes status, externalId, lastSyncedAt when present
   - `_find_existing_task` — omits optional fields when absent
   - SPARQL query contains `"monday"` as externalProvider

4. **Test `pull_sync()` full pipeline.** 50+ tests:
   - **Skip conditions:** returns skipped when not connected; returns skipped when no boards selected; returns skipped when board has no column mapping
   - **Single board, create new items:** items not in graph → Phase 1 create commands generated with correct type, slug, properties
   - **Single board, update existing items:** items found in graph → update commands generated with object.patch
   - **Multiple boards:** iterates all selected boards, each with own column mapping
   - **Column mapping applied:** build_task_properties called with correct column_mapping, status_label_mapping, priority_label_mapping from settings
   - **Group → taskGroup:** item.group.title set as `bpkm:taskGroup` property
   - **Group missing:** items without group data don't crash
   - **Subitem → parentTask:** subitems create edge.create commands with `bpkm:parentTask` predicate
   - **Subitem processing:** subitems created as separate Task objects
   - **Per-item error isolation:** one item failing doesn't stop others; error_count incremented; failed_items list populated
   - **Phase 1 → Phase 2:** create commands submitted first, then body.set + edge.create commands
   - **Assignee resolution:** PersonMatcher.resolve called with user_id; result used in edge.create
   - **Assignee resolution failure:** caught and logged, doesn't fail the item
   - **Description handling:** description extracted from properties and deferred to Phase 2 body.set
   - **Bulk bypass:** commands POSTed to /api/commands/bulk via ctx.commands._client
   - **Source string:** bulk commands use source "monday-sync"
   - **Sync timestamp stored:** last_sync_at set in state after sync
   - **Result stored:** last_pull_result set in state as JSON
   - **Empty results:** no items → returns success with 0 counts
   - **All items fail:** returns "error" status
   - **Mixed success/failure:** returns "partial" status

5. **Test `push_sync()` stub.** 3+ tests:
   - Returns `{"status": "skipped", "reason": "not implemented"}`
   - Is async function
   - Doesn't interact with any clients

6. **Test result helpers.** 10+ tests:
   - `_compute_status(1, 0, 0, 0)` → "success"
   - `_compute_status(0, 1, 0, 0)` → "success"
   - `_compute_status(1, 0, 0, 1)` → "partial"
   - `_compute_status(0, 0, 0, 1)` → "error"
   - `_compute_status(0, 0, 0, 0)` → "success" (empty is success)
   - `_make_result` includes duration_ms, created, updated, skipped, errors, failed_items
   - `_make_result` with reason includes reason field
   - `_build_create_command` returns correct structure
   - `_build_update_commands` returns patch + body + edge commands
   - `_build_update_commands` skips body/edge when None

## Must-Haves

- [ ] Test file at `backend/tests/test_monday_sync_engine.py`
- [ ] Uses importlib loading pattern (no package installation required)
- [ ] 100+ tests total
- [ ] MockResponse uses `data if data is not None else {}` (not `data or {}`)
- [ ] SPARQL lookup tests
- [ ] Pull sync full pipeline tests (skip conditions, create, update, multiple boards)
- [ ] Group→taskGroup tests
- [ ] Subitem→parentTask tests
- [ ] Per-item error isolation tests
- [ ] Phase 1 → Phase 2 command sequencing tests
- [ ] Push sync stub tests
- [ ] Result helper tests
- [ ] All tests pass: `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py -v`
- [ ] Combined Monday tests pass: `cd backend && .venv/bin/python3 -m pytest tests/test_monday_*.py -v` — 427+ total

## Verification

- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py -v` — 100+ tests pass
- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_*.py -v` — 427+ total tests pass (277 S01 + 50+ T03 + 100+ T04)
- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_*.py -v --tb=short 2>&1 | tail -5` — "X passed" with 0 failures
- `wc -l backend/tests/test_monday_sync_engine.py` — substantial file (1000+ lines)

## Inputs

- `apps/monday-sync/services/sync_engine.py` — T02 output with pull_sync, push_sync, and all helpers
- `apps/monday-sync/services/field_mapper.py` — S01: build_task_properties, compute_slug, BPKM
- `apps/monday-sync/services/person_matcher.py` — S01: PersonMatcher with resolve()
- `apps/monday-sync/services/auth.py` — S01: get_connection_status
- `apps/monday-sync/services/monday_client.py` — T01 output: MondayClient with get_all_board_items, get_subitems
- `backend/tests/test_jira_sync_engine.py` — reference for mock client pattern and test structure (~3600 lines, 95 tests)
- `backend/tests/test_monday_field_mapper.py` — reference for importlib loading pattern
- KNOWLEDGE.md Pattern #2: MockResponse `data if data is not None else {}` (not `data or {}`)

## Observability Impact

- **Test run command:** `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py -v` — displays per-test pass/fail status. A future agent inspects sync engine correctness by running this.
- **Failure visibility:** Pytest verbose output names the exact test class and method that failed, with short traceback. Error-path tests (`TestPullSyncAllItemsFail`, `TestPullSyncAssigneeResolution`) validate that runtime failures are surfaced correctly in `failed_items` and `error_count`.
- **MockResponse correctness signal:** `TestMockResponseFalsyData` catches regressions in KNOWLEDGE.md Pattern #2 — if someone changes `data if data is not None else {}` to `data or {}`, these tests fail immediately.
- **No runtime signals changed** — this task only adds tests, no production code modified.

## Expected Output

- `backend/tests/test_monday_sync_engine.py` — NEW: 100+ tests, 1000+ lines
