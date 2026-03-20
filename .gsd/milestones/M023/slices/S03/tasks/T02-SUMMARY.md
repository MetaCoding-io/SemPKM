---
id: T02
parent: S03
milestone: M023
provides:
  - _process_issue_links() function for creating bpkm:dependsOn edges from Jira "Blocks" issue links
  - Phase 4 integration in pull_sync pipeline — runs after epic linking, before final follow-up submission
  - Pull result enrichment with issue_links count in result dict and state
key_files:
  - apps/jira-sync/services/sync_engine.py
  - backend/tests/test_jira_sync_engine.py
key_decisions:
  - Process only inwardIssue links (not outwardIssue) for deduplication — each blocking relationship appears once
  - Link type matching uses case-insensitive "block" substring (handles Blocks, blocks, BLOCKS, localized variants)
  - Issue link edge errors are isolated per-link (try/except) and logged at WARNING, not counted in pull result errors
patterns_established:
  - _make_issue_with_links() and _make_blocks_link() test helpers for creating issue dicts with link arrays
  - Integration test pattern using ctx.commands._client.recorded_calls to inspect submitted bulk commands
observability_surfaces:
  - ctx.state "last_pull_result" now includes "issue_links" count
  - Structured logging at INFO for Phase 4 edge count, WARNING for per-link errors
  - Follow-up summary string includes issue link count alongside epic link count
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Add issue link processing to pull sync with dependsOn edge creation

**Added _process_issue_links() Phase 4 to pull_sync: Jira "Blocks" issue links create bpkm:dependsOn edges between Task objects with inward-only deduplication**

## What Happened

1. Added `_process_issue_links(issues, graph_client)` function (~90 lines including docstring) to sync_engine.py. For each issue, iterates `fields.issuelinks`, filters for link type name containing "block" (case-insensitive), processes only `inwardIssue` entries (the current issue "is blocked by" the inward issue). Looks up both Task IRIs via `_find_existing_task()`, creates `edge.create` commands with `bpkm:dependsOn` predicate. Per-link error isolation via try/except.

2. Integrated into pull_sync as Phase 4 — after Phase 3 (epic→child linking) and before final follow-up command submission. Passes ALL issues (tasks + epics) since epics can have blocking relationships too. Issue link commands are included in the `all_follow_up` batch alongside update, phase2, and epic link commands.

3. Updated pull result dict to include `"issue_links": len(issue_link_commands)`. Extended `_make_result()` with `issue_links` parameter. Updated follow-up log message to include issue link count.

4. Wrote 21 new tests across two test classes: TestIssueLinks (16 unit tests for `_process_issue_links()`) and TestPullSyncWithIssueLinks (5 integration tests for full pull_sync with issue links).

## Verification

- All 148 tests pass (127 existing + 21 new): `backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py --noconftest -v`
- Combined suite (385 tests) passes: `backend/.venv/bin/pytest backend/tests/test_jira_*.py --noconftest -v`
- Python syntax valid for sync_engine.py and field_mapper.py
- `grep -c "dependsOn"` → 4 occurrences in sync_engine.py
- `grep -c "_process_issue_links"` → 2 occurrences (def + call)
- Error isolation tests all pass (12 selected via `-k "error"`)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py --noconftest -v` | 0 | ✅ pass | 0.40s |
| 2 | `backend/.venv/bin/pytest backend/tests/test_jira_*.py --noconftest -v` | 0 | ✅ pass | 0.60s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read()); print('VALID')"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/field_mapper.py').read()); print('VALID')"` | 0 | ✅ pass | <1s |
| 5 | `grep -c "dependsOn" apps/jira-sync/services/sync_engine.py` → 4 | 0 | ✅ pass | <1s |
| 6 | `grep -c "_process_issue_links" apps/jira-sync/services/sync_engine.py` → 2 | 0 | ✅ pass | <1s |
| 7 | `grep -c "push_sync\|_find_changed_tasks\|_process_issue_links" apps/jira-sync/services/sync_engine.py` → 8 | 0 | ✅ pass | <1s |
| 8 | `grep -c "dependsOn\|issue.*link\|blocks" backend/tests/test_jira_sync_engine.py` → 100 | 0 | ✅ pass | <1s |
| 9 | `backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "error" -v --noconftest` → 12 passed | 0 | ✅ pass | 0.09s |

## Diagnostics

- **Pull result inspection:** `ctx.state.get("last_pull_result")` returns JSON with `{status, created, updated, skipped, errors, failed_issues, duration_ms, issue_links}` — `issue_links` is the count of dependsOn edges created from Jira "Blocks" links.
- **Phase 4 logging:** INFO-level log `"pull_sync: Phase 4 — N issue link (dependsOn) edges"` when edges are created. WARNING-level logs for per-link processing errors with the issue key.
- **Follow-up summary:** Bulk command summary includes issue link count: `"Jira sync: N updates, N follow-ups, N epic links, N issue links"`.

## Deviations

- Wrote 21 tests instead of the planned ~20 — added test for `None` issuelinks field and cross-project links.
- sync_engine.py grew to 946 lines (vs planned ~860) because the function docstring is more thorough and the Phase 4 integration includes more detailed logging.

## Known Issues

- None

## Files Created/Modified

- `apps/jira-sync/services/sync_engine.py` — Added `_process_issue_links()` function (~90 lines), Phase 4 integration in pull_sync, `_make_result()` extended with `issue_links` param, updated follow-up log messages
- `backend/tests/test_jira_sync_engine.py` — Added 21 new tests in TestIssueLinks (16) and TestPullSyncWithIssueLinks (5) classes, plus `_make_issue_with_links()` and `_make_blocks_link()` test helpers
