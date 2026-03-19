---
estimated_steps: 8
estimated_files: 4
---

# T01: Reverse field mapper + LinearClient mutations + store issue UUID

**Slice:** S03 — Push Sync + Settings Polish + Admin Detail
**Milestone:** M016

## Description

Add the reverse mapping functions needed for push sync (bpkm→Linear field conversion), add mutation support to LinearClient, and modify pull sync to store the Linear issue UUID. These are the foundational building blocks that T02's push sync engine depends on.

The forward mapping constants in `field_mapper.py` (STATUS_MAP, PRIORITY_MAP) can be inverted for reverse mapping. The key complexity is status reverse mapping — bpkm `taskStatus` maps to a Linear `state.type` string, but the actual `issueUpdate` mutation needs a `stateId` UUID, which requires looking up the team's workflow states.

The Linear issue UUID (`issue["id"]`) is available in the GraphQL response but not currently stored as a property. Push sync needs it because `issueUpdate(id: ...)` takes the UUID, not the human-readable identifier like "ENG-123". Store it as `bpkm:externalUuid` during pull sync.

## Steps

1. **Add reverse mapping constants to `field_mapper.py`:**
   - `REVERSE_STATUS_MAP: dict[str, str]` — `{"todo": "backlog", "in-progress": "started", "done": "completed", "blocked": "unstarted", "cancelled": "cancelled"}` (inverts STATUS_MAP, choosing one Linear state.type per bpkm status)
   - `REVERSE_PRIORITY_MAP: dict[str, int]` — `{"critical": 1, "high": 2, "medium": 3, "low": 4}` (inverts PRIORITY_MAP)

2. **Add reverse mapping functions to `field_mapper.py`:**
   - `reverse_status(bpkm_status: str) -> str` — returns Linear `state.type` string. Unknown inputs default to `"backlog"`.
   - `reverse_priority(bpkm_priority: str) -> int | None` — returns Linear priority int or None for unknown.
   - `build_issue_update_input(task_properties: dict, workflow_states: dict) -> dict` — builds a dict of `IssueUpdateInput` fields from bpkm task properties. `workflow_states` is `{(team_id, state_type): state_id}` lookup. Handles: title (from `dcterms:title`), stateId (from taskStatus → reverse_status → workflow_states lookup), priority (from priority → reverse_priority), dueDate (pass through). Skips fields that have no Linear equivalent (completedDate, externalUrl, externalProvider, tags for v1 — tag push requires fetching current labels). Returns only fields that changed (non-None values).

3. **Add `get_workflow_states(team_id)` to `LinearClient`:**
   - Query: `query($teamId: String!) { team(id: $teamId) { states { nodes { id name type } } } }`
   - Returns `list[dict]` of `{id, name, type}` workflow state dicts.

4. **Add `update_issue(issue_id, input_dict)` to `LinearClient`:**
   - Builds and executes `mutation($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) { success issue { id updatedAt } } }` 
   - Returns the response data dict.
   - Uses existing `self.query()` method (which handles mutations fine — same GraphQL transport).

5. **Modify `build_task_properties()` in `field_mapper.py`:**
   - Add `f"{BPKM}externalUuid": issue.get("id", "")` to the properties dict. The `id` field is the Linear issue UUID (available in the GraphQL `_ISSUE_FIELDS` which already includes `id`).
   - Ensure it's stripped if empty (the existing empty-value filter handles this).

6. **Create `backend/tests/test_push_sync.py` with ~25 unit tests:**
   - Load modules via importlib in dependency order (same pattern as test_sync_engine.py).
   - Test `reverse_status()`: all 5 bpkm statuses map correctly, unknown defaults to "backlog".
   - Test `reverse_priority()`: all 4 priorities map correctly, unknown returns None.
   - Test `build_issue_update_input()`: correct title extraction, stateId resolution from workflow_states, priority mapping, dueDate pass-through, skipped fields (no tags, no completedDate, no externalUrl), missing workflow state gracefully skipped, empty properties produce empty dict.
   - Test `LinearClient.get_workflow_states()`: correct GraphQL query, correct response parsing.
   - Test `LinearClient.update_issue()`: correct mutation string, correct variables.
   - Test that `build_task_properties()` now includes `bpkm:externalUuid`.

7. **Run existing tests to confirm no regressions:**
   - `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_sync_engine.py -v`

8. **Syntax-check all modified files.**

## Must-Haves

- [ ] `REVERSE_STATUS_MAP` and `REVERSE_PRIORITY_MAP` constants in field_mapper.py
- [ ] `reverse_status()` and `reverse_priority()` pure functions with unknown-input defaults
- [ ] `build_issue_update_input()` resolves stateId from workflow_states lookup, handles missing states gracefully
- [ ] `LinearClient.get_workflow_states(team_id)` queries team workflow states
- [ ] `LinearClient.update_issue(issue_id, input_dict)` executes issueUpdate mutation
- [ ] `build_task_properties()` stores `bpkm:externalUuid` from `issue["id"]`
- [ ] ~25 unit tests in `test_push_sync.py` covering all new functions
- [ ] Existing 81 tests still pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v` — all new tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_sync_engine.py -v` — existing tests still pass
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/field_mapper.py').read())"` — syntax valid
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/linear_client.py').read())"` — syntax valid

## Inputs

- `apps/linear-sync/services/field_mapper.py` — existing forward mapping constants (STATUS_MAP, PRIORITY_MAP, BPKM prefix, build_task_properties, _ISSUE_FIELDS)
- `apps/linear-sync/services/linear_client.py` — existing LinearClient class with query(), query_paginated(), typed exceptions
- `backend/tests/test_sync_engine.py` — importlib loading pattern and mock client classes (MockHttpClient, MockResponse, MockStateClient)
- S02 Summary: full IRI keys for bpkm properties (`urn:sempkm:model:basic-pkm:taskStatus`), not compact form

## Expected Output

- `apps/linear-sync/services/field_mapper.py` — extended with REVERSE_STATUS_MAP, REVERSE_PRIORITY_MAP, reverse_status(), reverse_priority(), build_issue_update_input(), and externalUuid in build_task_properties()
- `apps/linear-sync/services/linear_client.py` — extended with get_workflow_states(), update_issue()
- `backend/tests/test_push_sync.py` — ~25 unit tests for all new functions
