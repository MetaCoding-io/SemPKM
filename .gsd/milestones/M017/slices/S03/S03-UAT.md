# S03: Push Sync + Settings Polish — UAT

**Milestone:** M017
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: Push sync is contract-tested with 48 mocked unit tests. Runtime validation against live Docker stack is explicitly deferred to S04 E2E test. This UAT verifies the artifacts (code, templates, tests) are correct and complete.

## Preconditions

- Backend virtual environment available at `backend/.venv`
- All source files from T01 and T02 committed to working tree
- No Docker stack required (all tests are mocked)

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py tests/test_github_client.py tests/test_github_auth.py tests/test_github_person_matcher.py -v --tb=short
```

Expected: 204 tests pass, 0 failures, 0 errors.

## Test Cases

### 1. Push sync detects changed tasks and pushes to GitHub

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -k "test_push_sync_happy_path" -v`
2. **Expected:** Test passes — push_sync finds changed tasks, calls patch_issue for each, stores result with `status: "ok"` and `pushed: 2`.

### 2. Push sync skips when direction is pull-only

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -k "test_push_sync_skips_pull_only" -v`
2. **Expected:** Test passes — push_sync returns early with `status: "skipped"` when sync_direction is "pull-only".

### 3. Loop prevention skips unchanged tasks during pull

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -k "TestLoopPrevention" -v`
2. **Expected:** 4 tests pass — existing tasks with `updated_at <= lastSyncedAt` are skipped, newer tasks are updated, tasks without lastSyncedAt are always updated, new tasks are created normally.

### 4. parse_external_url handles issue and PR URLs

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_field_mapper.py -k "TestParseExternalUrl" -v`
2. **Expected:** 10 tests pass — correct (owner, repo, number) extraction for issue URLs, PR URLs, www.github.com, invalid URLs return None, missing path segments return None.

### 5. build_task_properties includes lastSyncedAt

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_field_mapper.py -k "TestBuildTaskPropertiesLastSyncedAt" -v`
2. **Expected:** 3 tests pass — sync_time parameter adds `bpkm:lastSyncedAt` to output, default (no sync_time) still works, lastSyncedAt survives the None/empty stripping.

### 6. Sync config route saves settings

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -k "TestSyncConfigRoute" -v`
2. **Expected:** 3 tests pass — POST to sync-config saves sync_direction and poll_interval to ctx.settings, template is re-rendered after save.

### 7. Bidirectional sync_now runs push after pull

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -k "test_sync_now_bidirectional" -v`
2. **Expected:** Test passes — sync_now calls both pull_sync and push_sync when direction is "bidirectional", stores both results.

### 8. Push errors don't break sync_now

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -k "test_sync_now_push_error" -v`
2. **Expected:** Test passes — push_sync failure is caught, last_sync_at is still updated, error is logged but doesn't propagate.

### 9. push_changes task handler calls real push_sync

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -k "TestPushChangesHandler" -v`
2. **Expected:** 2 tests pass — push_changes handler invokes push_sync and stores result in state.

### 10. Template has direction radios and poll interval dropdown

1. Run: `rg 'name="sync_direction"' apps/github-sync/frontend/templates/connect_status.html`
2. **Expected:** 2 matches (pull-only and bidirectional radio inputs).
3. Run: `rg 'name="poll_interval"' apps/github-sync/frontend/templates/connect_status.html`
4. **Expected:** 1 match (select element).
5. Run: `rg 'last_push_result' apps/github-sync/frontend/templates/connect_status.html`
6. **Expected:** Multiple matches showing status, pushed count, skipped count, and error count display.

### 11. Push result diagnostics structure

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -k "test_last_push_result_structure" -v`
2. **Expected:** Test passes — last_push_result contains status, pushed, errors list, and timestamp fields.

## Edge Cases

### Push sync with partial failures

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -k "test_push_sync_partial_failure" -v`
2. **Expected:** Test passes — successful tasks get lastSyncedAt updated, failed tasks are recorded in errors list with IRI and error message. Overall status is "partial_error".

### No changed tasks to push

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -k "test_push_sync_no_changed_tasks" -v`
2. **Expected:** Test passes — push_sync returns result with `status: "ok"` and `pushed: 0`.

### Not connected (no PAT)

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -k "test_push_sync_not_connected" -v`
2. **Expected:** Test passes — push_sync returns early with `status: "not_connected"`.

## Failure Signals

- Any test failure in the 204-test suite indicates a regression
- `rg '"push sync not implemented yet"' apps/github-sync/app.py` returning matches means the stub was not replaced
- Missing `last_push_result` in StateClient after push_sync completes means diagnostic surface is broken
- htmx URLs in connect_status.html without `/app/github-sync/` prefix will fail at runtime through the app proxy

## Requirements Proved By This UAT

- GH-04 — Push sync engine contract: SPARQL change detection, reverse mapping, PATCH mutation, lastSyncedAt update, loop prevention, error isolation, diagnostic surface
- GH-05 — Settings UI contract: sync direction radios, poll interval dropdown, save persistence, push result stats display

## Not Proven By This UAT

- Runtime push sync against live GitHub API (deferred to S04 mock server)
- Template rendering in browser with real Jinja2 context (deferred to S04 E2E)
- Bidirectional sync-now end-to-end through Docker stack (deferred to S04)
- Interaction between push sync and PR tasks (externalProvider "github-pr") — push applies to both issue and PR URLs via parse_external_url

## Notes for Tester

- All tests are mocked — no network calls, no Docker, no GitHub API access needed
- The 204-test count includes all 5 GitHub sync test files (sync_engine, field_mapper, client, auth, person_matcher)
- The _StubApp pattern in T02 tests loads app.py via importlib with passthrough decorators — this is intentional and avoids needing the real SDK
- If adding new push sync tests, use the MockGraphClient with dict slug_map values (includes optional lastSyncedAt field)
