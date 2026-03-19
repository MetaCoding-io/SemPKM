# S03: Push Sync + Settings Polish + Admin Detail — UAT

**Milestone:** M016
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S03's proof level is contract verification (unit tests for all pure logic + engine orchestration with mocked clients). Real runtime verification is explicitly deferred to S04 E2E test. UAT validates the artifacts exist and the logic is correct.

## Preconditions

- Backend venv exists at `backend/.venv/` with pytest installed
- Source files at `apps/linear-sync/services/` are present and syntactically valid
- `backend/tests/test_push_sync.py` exists with test classes

## Smoke Test

Run the full Linear sync test suite:
```
cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v
```
Expected: 69 tests pass, 0 failures, <1s execution.

## Test Cases

### 1. Reverse status mapping covers all bpkm statuses

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "TestReverseStatus"`
2. **Expected:** All tests pass. Covers: todo→backlog, in-progress→started, done→completed, cancelled→canceled, unknown→backlog (default).

### 2. Reverse priority mapping covers all bpkm priorities

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "TestReversePriority"`
2. **Expected:** All tests pass. Covers: none→0, low→4, medium→3, high→2, urgent→1, unknown→None.

### 3. build_issue_update_input constructs correct mutation payload

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "TestBuildIssueUpdateInput"`
2. **Expected:** All tests pass. Covers: stateId resolution from workflow states, priority mapping, title passthrough, dueDate passthrough, unknown status skips stateId, empty dict for no changes, None team_id handled gracefully.

### 4. LinearClient mutation methods are well-formed

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "TestLinearClientMutations"`
2. **Expected:** All tests pass. Covers: get_workflow_states sends correct GraphQL query and parses response, update_issue sends issueUpdate mutation with correct variables.

### 5. Pull sync stores externalUuid

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "TestExternalUuid"`
2. **Expected:** All tests pass. Covers: externalUuid extracted from issue "id" field, missing "id" field omits property.

### 6. Push sync orchestrator finds and processes changed tasks

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "TestPushSyncExecution"`
2. **Expected:** All tests pass. Covers: skips when not connected, skips pull-only direction, calls issueUpdate per changed task, isolates per-task errors, stores last_push_result in state, result contains correct counts.

### 7. SPARQL change detection query shape

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "TestFindChangedTasks"`
2. **Expected:** All tests pass. Covers: correct dict shape returned, empty list for no results, optional fields handled as None.

### 8. Workflow state resolution

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "TestResolveWorkflowStates"`
2. **Expected:** All tests pass. Covers: correct (team_id, state_type)→state_id lookup, first-match-wins for duplicate types, empty team list returns empty dict.

### 9. Loop prevention in pull sync

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "TestLoopPrevention"`
2. **Expected:** 4 tests pass. Covers: skips when updatedAt < lastSyncedAt, skips when updatedAt == lastSyncedAt, processes when updatedAt > lastSyncedAt, processes when no lastSyncedAt exists.

### 10. Full suite regression check

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py tests/test_push_sync.py -v`
2. **Expected:** 150 tests pass, 0 failures, <0.5s execution. No regressions in existing S01/S02 tests.

### 11. Failure-path tests

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "error or unknown or missing"`
2. **Expected:** 6 tests pass covering unknown status defaults, missing workflow states, unknown priority returns None, and per-task error isolation.

### 12. Manifest has push-changes task

1. Run: `grep "push-changes" apps/linear-sync/manifest.yaml`
2. **Expected:** At least one line containing `push-changes` task definition.

### 13. Settings template has all sync controls

1. Run: `grep -c "team_ids\|sync_direction\|sync-now\|sync-stats\|poll_interval" apps/linear-sync/frontend/templates/connect_status.html`
2. **Expected:** Count ≥ 10 (team checkboxes, direction radios, interval select, sync now button, stats section all present).

### 14. All source files syntactically valid

1. Run each:
   - `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/field_mapper.py').read())"`
   - `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/sync_engine.py').read())"`
   - `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/linear_client.py').read())"`
   - `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read())"`
2. **Expected:** All 4 exit with code 0, no output.

## Edge Cases

### Unknown status maps safely

1. Call `reverse_status("nonexistent-status")`
2. **Expected:** Returns `"backlog"` (safe default, not an exception).

### Unknown priority returns None (not a default integer)

1. Call `reverse_priority("nonexistent-priority")`
2. **Expected:** Returns `None`, not 0 or any integer. Callers decide to omit the field.

### Empty update input for unchanged task

1. Call `build_issue_update_input({}, {}, {})` with empty properties
2. **Expected:** Returns `{}` (empty dict). push_sync skips the mutation.

### Loop prevention with equal timestamps

1. Issue has `updatedAt = "2026-03-18T10:00:00Z"`, task has `lastSyncedAt = "2026-03-18T10:00:00Z"`
2. **Expected:** Issue is SKIPPED (equal means the update was our push, not an external change).

## Failure Signals

- Any of the 69 `test_push_sync.py` tests fail → push sync logic is broken
- Syntax check fails on any source file → file has been corrupted
- `manifest.yaml` missing `push-changes` → scheduled push sync won't run
- `connect_status.html` missing sync control references → settings page will be incomplete
- Full 150-test suite shows regressions → S01/S02 code was accidentally broken

## Requirements Proved By This UAT

- SYNC-03 — push_sync detects changed tasks, reverse-maps, executes mutations, prevents loops (contract verification)
- SYNC-04 — settings page has team selection, direction, interval, Sync Now, stats (template verification)
- SYNC-05 — push-changes task registered in manifest for platform scheduler visibility

## Not Proven By This UAT

- Real runtime behavior against Linear API (deferred to S04 E2E test with mocked API)
- Settings page rendering in browser (deferred to S04 E2E test)
- Actual scheduled task execution (requires running Docker stack with app platform)
- Admin detail page Task History display (platform feature, not app code)

## Notes for Tester

- All tests run in <0.5s with no Docker dependency — they mock all external interactions
- The "Sync Now" template button uses htmx `hx-indicator` for loading state but this can't be verified without a browser
- Push sync's single-team limitation (first team from sync_teams) is by design for v1 — don't test multi-team scenarios
- Loop prevention test case #4 (equal timestamps = skip) is intentional — the rationale is that our push sets lastSyncedAt after the mutation, so the next poll's updatedAt will be ≤ lastSyncedAt
