# S02: Pull sync + settings UI — UAT

**Milestone:** M023
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All sync logic runs through mocked clients — no live Jira API needed. E2E with mock server is S04's responsibility. Unit tests with realistic mock data prove the pipeline correctness.

## Preconditions

- Worktree venv has pytest-asyncio installed: `cd backend && .venv/bin/python -c "import pytest_asyncio"`
- All S01 Jira test files exist: `ls backend/tests/test_jira_*.py` shows test_jira_adf_converter.py, test_jira_auth.py, test_jira_client.py, test_jira_field_mapper.py, test_jira_person_matcher.py, test_jira_sync_engine.py

## Smoke Test

```bash
cd /home/james/Code/SemPKM/.gsd/worktrees/M023/backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py -v --tb=short
```
Expected: 95 tests pass in under 1 second.

## Test Cases

### 1. Sync engine module is valid Python

1. Run: `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read())"`
2. **Expected:** Exit code 0, no output (valid Python AST)

### 2. App.py handlers wired to sync functions

1. Run: `grep -n "from services.sync_engine import" apps/jira-sync/app.py`
2. **Expected:** 3 lines — one each in sync_now, poll-tasks, push-changes handlers
3. Run: `grep -c "pull_sync\|push_sync" apps/jira-sync/app.py`
4. **Expected:** Output is `7` (3 imports + 4 function calls)

### 3. Pull sync happy path — basic task creation

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestPullSyncHappyPath::test_basic_pull_creates_task -v`
2. **Expected:** Test passes — verifies pull_sync creates object.create command with correct slug and type

### 4. Epic→Milestone creation and child linking

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py -k "Epic" -v`
2. **Expected:** 8 tests pass covering Epic detection, Milestone object creation, next-gen parent.key linking, classic customfield_10014 linking, and parent-not-found graceful handling

### 5. JQL construction variants

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestBuildJql -v`
2. **Expected:** 11 tests pass covering single project, multiple projects, user JQL filter, delta sync timestamp, combined filters, empty project list

### 6. Delta sync and loop prevention

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestDeltaSyncAndLoopPrevention -v`
2. **Expected:** 5 tests pass — verifies issues with updatedAt ≤ lastSyncedAt are skipped, delta timestamp appended to JQL

### 7. Error isolation — one bad issue doesn't kill sync

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestErrorIsolation -v`
2. **Expected:** 5 tests pass — verifies partial status when some issues fail, failed_issues list populated, other issues still processed

### 8. Skip conditions

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestSkipConditions -v`
2. **Expected:** 6 tests pass — not connected returns error, no projects selected returns error, empty issue results returns success with zero counts

### 9. Push sync stub returns correct status

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestPushSync -v`
2. **Expected:** 4 tests pass — push not connected skips, pull-only direction skips, bidirectional returns "not implemented", result stored in state

### 10. App.py wiring — sync_now calls pull_sync

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestAppWiring -v`
2. **Expected:** 5 tests pass — sync_now calls pull_sync, poll-tasks calls pull_sync, push-changes calls push_sync, bidirectional runs both, last_sync_at stored

### 11. Full combined Jira test suite — no regressions

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_*.py -v`
2. **Expected:** 332 tests pass (237 from S01 + 95 from S02), no failures, under 1 second

### 12. Failure-path signals present in sync engine

1. Run: `grep -n "status.*error\|status.*partial\|failed_issues\|WARNING" apps/jira-sync/services/sync_engine.py | head -20`
2. **Expected:** At least 8 matches showing error status, partial status, failed_issues list, and WARNING-level logging

## Edge Cases

### ADF description is None

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestEdgeCases::test_issue_with_none_description_no_body_set -v`
2. **Expected:** Pass — no body.set command generated when description is None

### Assignee is None

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestEdgeCases::test_issue_with_none_assignee_no_person_resolution -v`
2. **Expected:** Pass — no PersonMatcher.resolve call and no assignedTo edge when assignee is None

### Update existing milestone (not just create)

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestEdgeCases::test_update_existing_milestone -v`
2. **Expected:** Pass — existing milestone found via SPARQL produces object.patch instead of object.create

### Parent epic key extraction — next-gen vs classic

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestGetParentEpicKey -v`
2. **Expected:** 6 tests pass — next-gen parent Epic detected, non-Epic parent ignored, classic customfield_10014 used as fallback, next-gen preferred over classic when both present

### Empty issues list — early return

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py::TestSkipConditions::test_empty_issues_returns_success -v`
2. **Expected:** Pass — returns success with zero counts, does NOT store last_sync_at in state

## Failure Signals

- Any test in `test_jira_sync_engine.py` failing indicates a broken sync path
- `ast.parse` failure on sync_engine.py or app.py means syntax error introduced
- Fewer than 7 `pull_sync`/`push_sync` references in app.py means a handler was disconnected
- Any S01 test regression (combined suite < 332) means sync_engine.py broke an upstream module

## Requirements Proved By This UAT

- JIRA-03 (Pull sync) — partially proven by unit tests with mocked clients; full validation needs E2E in S04
- JIRA-04 (Epic → Milestone) — partially proven by 8 Epic-specific tests; full validation needs E2E in S04
- JIRA-05 (JQL-based filtered sync) — partially proven by 11 JQL tests; full validation needs E2E in S04

## Not Proven By This UAT

- Live Jira API interaction (mocked clients only)
- Real ADF document conversion end-to-end through pull pipeline (tested individually in S01)
- Settings UI rendering (built in S01, tested visually in S04 E2E)
- Full bidirectional sync loop (push not yet implemented — S03)
- Issue link "blocks" → bpkm:dependsOn edges (S03)
- E2E lifecycle test (S04)

## Notes for Tester

- All tests use mocked clients — no Jira credentials or network access needed
- The 332 combined test count (237 + 95) is the key regression signal — if it drops, something broke
- push_sync is intentionally a stub — don't expect real push behavior
- Empty-issues early return deliberately skips state storage — this is by design, not a bug
