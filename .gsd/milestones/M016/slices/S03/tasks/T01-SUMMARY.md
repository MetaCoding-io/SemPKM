---
id: T01
parent: S03
milestone: M016
provides:
  - Reverse field mapping constants and functions (bpkm→Linear)
  - build_issue_update_input() for constructing issueUpdate mutation inputs
  - LinearClient.get_workflow_states() and update_issue() methods
  - bpkm:externalUuid stored during pull sync
key_files:
  - apps/linear-sync/services/field_mapper.py
  - apps/linear-sync/services/linear_client.py
  - backend/tests/test_push_sync.py
key_decisions:
  - "REVERSE_STATUS_MAP maps 'todo'→'backlog' (not 'unstarted') since backlog is the most common default state in Linear"
  - "build_issue_update_input takes team_id as parameter for workflow state lookup, gracefully skips stateId when team_id is None or state not found"
patterns_established:
  - "Reverse mapping functions follow same convention as forward: unknown inputs get safe defaults (backlog for status, None for priority)"
observability_surfaces:
  - "build_issue_update_input returns only non-None fields — empty dict means no pushable changes"
  - "reverse_status defaults unknown to backlog; reverse_priority returns None for unknown — callers decide behavior"
  - "LinearClient mutations use existing query() transport — errors surface via LinearAPIError/LinearQueryError with status_code and response_body"
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Reverse field mapper + LinearClient mutations + store issue UUID

**Added reverse mapping (bpkm→Linear), LinearClient mutation methods, and externalUuid storage in pull sync with 44 unit tests**

## What Happened

Extended `field_mapper.py` with reverse mapping constants (`REVERSE_STATUS_MAP`, `REVERSE_PRIORITY_MAP`) and three new functions: `reverse_status()`, `reverse_priority()`, and `build_issue_update_input()`. The update input builder resolves stateId from a workflow states lookup, maps priority to Linear integers, passes through title and dueDate, and silently skips fields that have no Linear equivalent (tags, completedDate, externalUrl).

Extended `LinearClient` with `get_workflow_states(team_id)` for querying a team's workflow state definitions and `update_issue(issue_id, input_dict)` for executing the `issueUpdate` GraphQL mutation. Both use the existing `query()` transport which handles auth, refresh, rate limiting, and error typing.

Modified `build_task_properties()` to store `bpkm:externalUuid` from the Linear issue's `id` field. This UUID is needed by push sync because Linear's `issueUpdate` mutation takes the UUID, not the human-readable identifier.

## Verification

- 44 new tests in `test_push_sync.py` — all pass
- 69 existing tests in `test_field_mapper.py` + `test_sync_engine.py` — all pass (zero regressions)
- 125 total tests across the full Linear sync suite — all pass
- Both modified source files pass `ast.parse()` syntax validation
- Failure-path tests pass: unknown status defaults, missing workflow states, unknown priority returns None

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v` | 0 | ✅ pass | 0.06s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_sync_engine.py -v` | 0 | ✅ pass | 0.07s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/field_mapper.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/linear_client.py').read())"` | 0 | ✅ pass | <1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "error or unknown or missing"` | 0 | ✅ pass | 0.02s |
| 6 | `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py tests/test_push_sync.py -v` | 0 | ✅ pass | 0.12s |

## Diagnostics

- `reverse_status()` and `reverse_priority()` are pure functions — test directly with any input string
- `build_issue_update_input()` returns a dict of only the fields that will be mutated — inspect the dict to verify what would be pushed
- Empty return dict from `build_issue_update_input()` means no pushable changes
- `bpkm:externalUuid` presence on a task IRI can be verified via SPARQL: `?task bpkm:externalUuid ?uuid`
- LinearClient mutation errors surface through the existing exception hierarchy with `status_code` and `response_body`

## Deviations

- Plan specified ~25 tests; delivered 44 (more thorough coverage of constant values and edge cases). No structural deviation.

## Known Issues

None.

## Files Created/Modified

- `apps/linear-sync/services/field_mapper.py` — Added REVERSE_STATUS_MAP, REVERSE_PRIORITY_MAP, reverse_status(), reverse_priority(), build_issue_update_input(), and bpkm:externalUuid in build_task_properties()
- `apps/linear-sync/services/linear_client.py` — Added get_workflow_states(team_id) and update_issue(issue_id, input_dict) methods
- `backend/tests/test_push_sync.py` — Created with 44 unit tests covering all reverse mapping, LinearClient mutations, and externalUuid storage
- `.gsd/milestones/M016/slices/S03/S03-PLAN.md` — T01 marked done, added failure-path verification step
- `.gsd/milestones/M016/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section
