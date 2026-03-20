# S03: Push sync + issue links — UAT

**Milestone:** M023
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All verification is via mocked clients in unit tests — no live Jira instance needed. Push sync pipeline, issue link edge creation, and error isolation are fully testable through mock graph/Jira clients.

## Preconditions

- Working directory: `/home/james/Code/SemPKM/.gsd/worktrees/M023`
- Python venv available at `./backend/.venv/bin/python`
- No Docker stack or live server required

## Smoke Test

```bash
cd /home/james/Code/SemPKM/.gsd/worktrees/M023
./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -v --noconftest 2>&1 | tail -5
```
Expected: `148 passed` with exit code 0.

## Test Cases

### 1. Push sync replaces stub with real implementation

1. Run: `grep -A 5 "def push_sync" apps/jira-sync/services/sync_engine.py | head -10`
2. **Expected:** Function signature includes `ctx`, `state`, `jira` parameters. Body is NOT a stub returning `{"status": "skipped"}` — it has real logic with `_find_changed_tasks()` call.

### 2. Push sync happy path creates Jira API update

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_push_happy_path" -v --noconftest`
2. **Expected:** Test passes. Push sync finds changed task, converts body to ADF, calls update_issue with title/priority/description fields, updates lastSyncedAt.

### 3. Push sync includes ADF description from markdown body

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_push_with_description_adf" -v --noconftest`
2. **Expected:** Test passes. The issue patch sent to Jira includes a `description` field containing an ADF document (dict with `version`, `type`, `content` keys).

### 4. Push sync error isolation — one failed task doesn't kill the run

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_push_error_isolation" -v --noconftest`
2. **Expected:** Test passes. When one task's update_issue call raises an exception, the remaining tasks still get processed. Result has `errors` list with the failed task's IRI.

### 5. Push sync loop prevention via lastSyncedAt

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_push_updates_last_synced" -v --noconftest`
2. **Expected:** Test passes. After a successful push, the task's `bpkm:lastSyncedAt` is updated so next pull_sync won't re-import the pushed changes.

### 6. Push sync skipped when direction is pull-only

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_push_pull_only" -v --noconftest`
2. **Expected:** Test passes. Push sync returns `{"status": "skipped"}` when sync_direction is "pull".

### 7. Push result uses "success" status (not "ok")

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_push_result_uses_success_not_ok" -v --noconftest`
2. **Expected:** Test passes. Result dict has `"status": "success"`, matching the convention used by pull_sync and the connect_status.html template.

### 8. _find_changed_tasks SPARQL detects modified tasks

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "TestFindChangedTasks" -v --noconftest`
2. **Expected:** All 6 tests pass — no tasks, one changed, one unchanged (skipped), pull-only filter, multiple changed, and tasks without lastSyncedAt (treated as changed).

### 9. _get_task_body reads body text via SPARQL

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "TestGetTaskBody" -v --noconftest`
2. **Expected:** All 4 tests pass — body found, body not found (returns None), empty body, and body with special characters.

### 10. build_issue_patch includes description ADF when provided

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "TestBuildIssuePatchWithDescription" -v --noconftest`
2. **Expected:** All 5 tests pass — with ADF dict, without ADF (omitted from patch), empty ADF (omitted), ADF plus title+priority, and None description_adf.

### 11. Issue links: "Blocks" type creates dependsOn edge

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_inward_blocks_link_creates_depends_on_edge" -v --noconftest`
2. **Expected:** Test passes. An inward "Blocks" link creates an edge.create command with `bpkm:dependsOn` predicate between the two task IRIs.

### 12. Issue links: outward links ignored for deduplication

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_outward_blocks_link_ignored" -v --noconftest`
2. **Expected:** Test passes. Outward "Blocks" links produce zero edge commands — only inward links are processed.

### 13. Issue links: non-blocks link types ignored

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_non_blocks_link_type_ignored" -v --noconftest`
2. **Expected:** Test passes. Link types like "Relates" or "Duplicates" produce zero edge commands.

### 14. Issue links: case-insensitive matching

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_case_insensitive" -v --noconftest`
2. **Expected:** Both tests pass. "blocks" (lowercase) and "BLOCKS" (uppercase) both match as blocking link types.

### 15. Issue links integrated into pull_sync Phase 4

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "TestPullSyncWithIssueLinks" -v --noconftest`
2. **Expected:** All 5 integration tests pass — pull sync with blocking links creates edges, without links still works, result includes issue_links count, commands in follow-up batch, and issue links processed after epic linking.

### 16. Pull result includes issue_links count

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_pull_result_includes_issue_links_count" -v --noconftest`
2. **Expected:** Test passes. The pull result dict contains an `issue_links` key with the count of dependsOn edges created.

## Edge Cases

### Per-link error isolation

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_error_in_one_link_doesnt_stop_others" -v --noconftest`
2. **Expected:** Test passes. When one issue link processing fails (e.g., linked issue not synced), remaining links are still processed.

### Linked issue not synced — skip gracefully

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_linked_issue_not_synced_skips" -v --noconftest`
2. **Expected:** Test passes. When the linked issue hasn't been synced (no corresponding Task IRI in graph), the link is skipped without error.

### None issuelinks field

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_none_issuelinks_treated_as_empty" -v --noconftest`
2. **Expected:** Test passes. Issues with `issuelinks: None` are treated as having no links (no crash).

### Push sync with unknown priority

1. Run: `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "test_push_task_with_unknown_priority_omits_it" -v --noconftest`
2. **Expected:** Test passes. Tasks with priority values not in REVERSE_PRIORITY_MAP are pushed without a priority field (other fields still pushed).

## Failure Signals

- Any test failure in `test_jira_sync_engine.py` — indicates regression in sync engine
- `push_sync` returning `{"status": "skipped"}` for all cases — stub not replaced
- `_process_issue_links` not found in sync_engine.py — T02 not integrated
- `grep -c "dependsOn" apps/jira-sync/services/sync_engine.py` returns 0 — issue links not implemented
- Combined suite (`test_jira_*.py`) failing — cross-module regression

## Requirements Proved By This UAT

- JIRA-07 (issue links → dependsOn edges) — Tests 11-16 and edge cases prove "Blocks" links create correct edges with deduplication
- JIRA-08 (push sync title/description/priority) — Tests 1-10 prove push pipeline with SPARQL detection, ADF conversion, API update, error isolation
- JIRA-09 (bidirectional loop prevention) — Test 5 proves lastSyncedAt update prevents re-import

## Not Proven By This UAT

- End-to-end lifecycle through Docker stack with mock Jira API (S04 scope)
- Real Jira Cloud API interaction (out of scope for v1 automated testing)
- Push sync for status transitions (deferred per D237)
- UI rendering of push results in connect_status.html (S04 E2E will cover)

## Notes for Tester

- All tests must use `--noconftest` flag due to a pre-existing conftest.py Settings validation error unrelated to Jira sync
- The combined suite (`test_jira_*.py --noconftest`) should show 385 tests passing — this confirms no cross-module regression from the sync engine changes
- Error isolation tests (`-k "error"`) are particularly important — they prove the per-task and per-link error isolation that prevents one bad issue from killing a sync run
