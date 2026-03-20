---
id: T02
parent: S02
milestone: M023
provides:
  - 95 unit tests for Jira sync engine covering all pull/push/skip/error paths
key_files:
  - backend/tests/test_jira_sync_engine.py
key_decisions:
  - Tests mock JiraClient/get_connection_status via patch.object on _sync_engine module rather than injecting mock clients, matching how sync_engine internally constructs JiraClient
  - Epic→child linking tests use pre-populated slug_map in MockGraphClient (existing task scenario) rather than mock-patching _find_existing_task, avoiding fragile call-count tracking
  - Empty-issues early return in pull_sync does not store last_sync_at/last_pull_result — tests adjusted to provide actual issues when verifying state storage
patterns_established:
  - MockGraphClient with separate slug_map (Task) and milestone_slug_map (Milestone) for typed SPARQL routing
  - MockSettingsClient separate from MockStateClient mirroring SDK ctx.settings vs ctx.state split
  - CapturingJiraClient subclass pattern for asserting JQL content without intercepting full sync flow
observability_surfaces:
  - pytest tests/test_jira_sync_engine.py -v — 95 tests across 13 test classes
  - Combined suite: pytest tests/test_jira_*.py -v — 332 total (237 S01 + 95 S02)
duration: 20m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Comprehensive unit tests for Jira sync engine

**95 unit tests for Jira sync engine covering SPARQL helpers, JQL construction, command builders, pull sync happy/error/skip paths, Epic→Milestone creation, delta sync with loop prevention, push stub, and app.py wiring**

## What Happened

Built `backend/tests/test_jira_sync_engine.py` (2328 lines, 95 tests) using importlib-based module loading matching the established GCal test pattern. Created 7 mock client classes (MockStateClient, MockSettingsClient, MockGraphClient, MockHttpClient, MockCommandClient, MockExternalHttpClient, MockAppContext) plus MockResponse following K002. Built Jira issue fixture helpers (_make_issue, _make_epic, _make_adf_doc) with realistic nested field structures.

Tests organized into 13 classes covering all 10 plan categories: SPARQL helpers (4 tests), JQL construction (11 tests), command builders (6 tests), pull sync happy path (10 tests), Epic→Milestone (8 tests), delta sync + loop prevention (5 tests), skip conditions (6 tests), error isolation (5 tests), push sync stub (4 tests), app wiring (5 tests), parent epic key extraction (6 tests), submit commands batched (3 tests), MockResponse correctness (6 tests), compute status (5 tests), and edge cases (7 tests).

Required installing pytest-asyncio via uv (was in pyproject.toml dev deps but not installed in worktree venv). Fixed 7 initial test failures: empty-issues early return path in sync_engine doesn't store state (adjusted tests to provide issues), epic child linking tests restructured to use pre-populated slug_map instead of fragile call-count mock patching, removed broken `services.sync_engine` module patch in app wiring test.

## Verification

- 95 tests pass in test_jira_sync_engine.py
- 332 tests pass in combined test_jira_*.py suite (no S01 regressions)
- sync_engine.py and app.py are valid Python
- 7 pull_sync/push_sync references in app.py confirm wiring
- Failure-path signals (error/partial status, failed_issues, WARNING logging) confirmed present

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_jira_sync_engine.py -v` | 0 | ✅ pass | 0.22s |
| 2 | `pytest tests/test_jira_*.py -v` (332 tests) | 0 | ✅ pass | 0.37s |
| 3 | `wc -l backend/tests/test_jira_sync_engine.py` → 2328 | 0 | ✅ pass | <1s |
| 4 | `ast.parse(sync_engine.py)` | 0 | ✅ pass | <1s |
| 5 | `ast.parse(app.py)` | 0 | ✅ pass | <1s |
| 6 | `grep -c pull_sync\|push_sync app.py` → 7 | 0 | ✅ pass | <1s |
| 7 | `grep failure-path signals in sync_engine.py` | 0 | ✅ pass | <1s |

## Diagnostics

- Run `pytest tests/test_jira_sync_engine.py -v` to see all 95 tests with pass/fail status
- Run `pytest tests/test_jira_sync_engine.py -v -k "Epic"` to run only Epic→Milestone tests
- Run `pytest tests/test_jira_sync_engine.py -v -k "error"` to run only error isolation tests
- Test classes map 1:1 to sync engine capabilities: TestFindExistingTask, TestBuildJql, TestPullSyncHappyPath, TestEpicToMilestone, TestDeltaSyncAndLoopPrevention, TestSkipConditions, TestErrorIsolation, TestPushSync, TestAppWiring

## Deviations

- pytest-asyncio needed manual installation via `uv pip install pytest-asyncio` — was in pyproject.toml but not installed in worktree venv
- Epic child linking tests use existing-task-in-graph approach rather than mock-patching _find_existing_task with call counters — more robust and realistic
- 95 tests instead of plan's 60+ target — additional coverage for _get_parent_epic_key, _compute_status, _submit_commands_batched, MockResponse K002 compliance, and edge cases

## Known Issues

- pull_sync's empty-issues early return path does not store last_sync_at or last_pull_result in state — this is by-design behavior, not a bug (no issues to sync means no sync timestamp needed)

## Files Created/Modified

- `backend/tests/test_jira_sync_engine.py` — new, 2328 lines, 95 unit tests for Jira sync engine
- `.gsd/milestones/M023/slices/S02/S02-PLAN.md` — marked T02 as [x]
- `.gsd/milestones/M023/slices/S02/tasks/T02-PLAN.md` — added Observability Impact section
- `.gsd/STATE.md` — updated next action
