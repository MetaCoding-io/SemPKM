# S02: Pull Sync — Linear Issues to bpkm:Task — UAT

**Milestone:** M016
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All sync logic is tested via mocked clients (81 unit tests). No runtime platform is needed to verify the pure mapping, matching, and orchestration logic. Runtime integration is explicitly deferred to S04 E2E test.

## Preconditions

- Backend Python venv exists at `backend/.venv/`
- Source files exist: `apps/linear-sync/services/field_mapper.py`, `person_matcher.py`, `sync_engine.py`
- Test files exist: `backend/tests/test_field_mapper.py`, `test_person_matcher.py`, `test_sync_engine.py`
- No Docker stack required

## Smoke Test

Run the full test suite:
```
cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py -v
```
Expected: 81 tests pass in <1s.

## Test Cases

### 1. Field mapper: Status normalization covers all Linear state types

1. Run `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py -v -k "TestNormalizeStatus"`
2. **Expected:** 7 tests pass covering backlog→todo, unstarted→todo, started→in-progress, completed→done, cancelled→cancelled, unknown→todo, empty→todo

### 2. Field mapper: Priority normalization covers Linear 0-4 scale

1. Run `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py -v -k "TestNormalizePriority"`
2. **Expected:** 6 tests pass. Priority 0 and unknown values return None (omitted from properties).

### 3. Field mapper: Property dict uses full IRIs and truncates dates

1. Run `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py -v -k "TestBuildTaskProperties"`
2. **Expected:** 13 tests pass. All bpkm property keys use `urn:sempkm:model:basic-pkm:` prefix. DateTime values truncated to date-only. Null/empty values omitted.

### 4. Field mapper: GraphQL query construction with delta filter

1. Run `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py -v -k "TestBuildIssueQuery"`
2. **Expected:** 6 tests pass. Query includes team filter, optional updatedAfter, pagination with `$after` cursor, and requests all required fields (title, description, state, priority, labels, assignee, dueDate, completedAt, estimate, trashed, updatedAt).

### 5. Field mapper: Deterministic slug computation

1. Run `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py -v -k "TestComputeIssueSlug"`
2. **Expected:** 4 tests pass. Same inputs always produce same slug. Different workspace IDs produce different slugs. Format is `issue-{16 hex chars}`.

### 6. Person matcher: SPARQL lookup finds existing persons

1. Run `cd backend && .venv/bin/python -m pytest tests/test_person_matcher.py -v -k "existing_person"`
2. **Expected:** 2 tests pass — finds persons via both `foaf:mbox` and `crm:email` predicates.

### 7. Person matcher: Creates new person on miss

1. Run `cd backend && .venv/bin/python -m pytest tests/test_person_matcher.py -v -k "new_person_created"`
2. **Expected:** Test passes. Command submitted is `object.create` with type `bpkm:Person`, `dcterms:title` set to display name, `foaf:mbox` set to email URI.

### 8. Person matcher: Cache prevents duplicate queries

1. Run `cd backend && .venv/bin/python -m pytest tests/test_person_matcher.py -v -k "cache"`
2. **Expected:** 2 tests pass. Second call with same email skips SPARQL. Mixed-case emails (Bob@Co.com vs bob@co.com) share cache entry.

### 9. Sync engine: Skips when not connected or no teams selected

1. Run `cd backend && .venv/bin/python -m pytest tests/test_sync_engine.py -v -k "skips"`
2. **Expected:** 2 tests pass. pull_sync returns `{"status": "skipped", ...}` without making any API calls.

### 10. Sync engine: Creates tasks for new issues

1. Run `cd backend && .venv/bin/python -m pytest tests/test_sync_engine.py -v -k "creates_task"`
2. **Expected:** Test passes. Bulk payload includes `object.create` command with type `bpkm:Task`, correct slug prefix, and all mapped properties.

### 11. Sync engine: Patches existing tasks

1. Run `cd backend && .venv/bin/python -m pytest tests/test_sync_engine.py -v -k "patches_existing"`
2. **Expected:** Test passes. Bulk payload includes `object.patch` command with the existing task IRI and updated properties.

### 12. Sync engine: Handles trashed issues correctly

1. Run `cd backend && .venv/bin/python -m pytest tests/test_sync_engine.py -v -k "trashed"`
2. **Expected:** 2 tests pass. New trashed issues are skipped entirely. Existing tasks for trashed issues get status patched to "cancelled".

### 13. Sync engine: Batches commands at 1000-op limit

1. Run `cd backend && .venv/bin/python -m pytest tests/test_sync_engine.py -v -k "batches"`
2. **Expected:** Test passes. When command count exceeds 1000, multiple HTTP POSTs are made with ≤1000 ops each.

### 14. Sync engine: Per-issue errors don't abort sync

1. Run `cd backend && .venv/bin/python -m pytest tests/test_sync_engine.py -v -k "error"`
2. **Expected:** 2 tests pass. A failing issue is recorded in the `errors` list with `issue_id` and `error` message. Other issues still process successfully.

### 15. Sync engine: Commands bypass SDK client

1. Run `cd backend && .venv/bin/python -m pytest tests/test_sync_engine.py -v -k "commands_posted_directly"`
2. **Expected:** Test passes. Commands are posted via `ctx.commands._client.post()` (httpx direct), not via `ctx.commands.execute()`.

### 16. Sync engine: Stores delta cursor on success

1. Run `cd backend && .venv/bin/python -m pytest tests/test_sync_engine.py -v -k "stores_last_sync"`
2. **Expected:** Test passes. After successful sync, `last_sync_at` is set in StateClient with an ISO timestamp.

### 17. poll-tasks handler wiring

1. Run `grep -n 'pull_sync' apps/linear-sync/app.py`
2. **Expected:** Output shows `from services.sync_engine import pull_sync` import and `result = await pull_sync(ctx)` call in the poll_tasks handler.

### 18. Source files are syntactically valid Python

1. Run:
   ```
   python3 -c "import ast; ast.parse(open('apps/linear-sync/services/field_mapper.py').read())"
   python3 -c "import ast; ast.parse(open('apps/linear-sync/services/person_matcher.py').read())"
   python3 -c "import ast; ast.parse(open('apps/linear-sync/services/sync_engine.py').read())"
   ```
2. **Expected:** All three complete with exit code 0.

## Edge Cases

### None/empty email for assignee

1. Run `cd backend && .venv/bin/python -m pytest tests/test_person_matcher.py -v -k "none_email or empty_email"`
2. **Expected:** Both return None without making SPARQL queries or creating persons.

### Issue with no description

1. Run `cd backend && .venv/bin/python -m pytest tests/test_sync_engine.py -v -k "without_description"`
2. **Expected:** No body.set command is emitted for that issue.

### Effort mapping for unknown values

1. Run `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py -v -k "TestEffortMapping"`
2. **Expected:** 8 tests pass. Known estimates (1,2,3,5,8) map to strings. Unknown values are stringified as-is. Zero and None are omitted.

### Labels with missing name field

1. Run `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py -v -k "label_without_name"`
2. **Expected:** Label entries without a `name` key are silently skipped.

## Failure Signals

- Any test failure in the 81-test suite indicates a broken mapping, matching, or sync logic path
- `pull_sync()` returning `{"status": "error"}` indicates auth or API failure
- Non-empty `errors` list in the result dict indicates per-issue processing failures
- Missing `pull_sync` import in `app.py` means the handler is still a noop stub

## Requirements Proved By This UAT

- SYNC-02 (pull sync) — contract-level proof that field mapping, person matching, IRI minting, delta sync, bulk batching, and error isolation all work correctly via 81 unit tests with mocked clients

## Not Proven By This UAT

- Runtime integration against the actual SemPKM platform (deferred to S04 E2E test)
- Real Linear GraphQL API pagination behavior
- Actual bulk command processing and materialization by the platform
- Push sync (S03) and loop prevention (S03)

## Notes for Tester

- All tests run in <1s with zero external dependencies (no Docker, no network, no triplestore)
- The importlib loading pattern in test files is intentional — app code lives in `apps/linear-sync/` which isn't on the Python path, so tests load modules dynamically
- The `StatefulGraph` mock in test_sync_engine.py returns different results on subsequent calls to simulate the two-phase create→discover pattern
