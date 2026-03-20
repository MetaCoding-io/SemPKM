# T02: TodoistClient + field mapper

**Slice:** S01 — Auth + Client + Pull Sync
**Milestone:** M019

## Description

REST client wrapping SDK HttpClient for Todoist API v2, and field mapper with all property transforms including priority inversion.

## Steps

1. Write `services/todoist_client.py` — TodoistClient with get_tasks(project_id=None), get_projects(), get_labels(). Simple GET to /rest/v2/tasks, /rest/v2/projects, /rest/v2/labels. Auth header from stored token.
2. Write `services/field_mapper.py`:
   - TODOIST_TO_BPKM_PRIORITY = {1:"low", 2:"medium", 3:"high", 4:"critical"} and BPKM_TO_TODOIST_PRIORITY reverse
   - TODOIST_TO_BPKM_STATUS / BPKM_TO_TODOIST_STATUS for is_completed ↔ taskStatus
   - build_task_properties(task, labels_lookup, project_lookup) — full property dict
   - Due date: extract due.date (YYYY-MM-DD) as xsd:date. Handle missing due, date-only, datetime cases.
   - Labels: direct array to bpkm:tags
   - URL, external ID, project name
3. Write `backend/tests/test_todoist_client.py` — 15+ tests: get_tasks, get_projects, get_labels, auth header, error handling, project_id filter
4. Write `backend/tests/test_todoist_field_mapper.py` — 40+ tests: all 4 priority levels both directions, status mapping, due date edge cases, label mapping, URL/ID, full build_task_properties

## Must-Haves

- [ ] All 4 priority levels tested bidirectionally
- [ ] Due date extraction handles None, date-only, and datetime
- [ ] 55+ combined tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_todoist_client.py tests/test_todoist_field_mapper.py -v`

## Observability Impact

- **Logger:** `todoist.sync.client` — DEBUG for each request (method + URL), WARNING on API errors with status code and response body excerpt
- **Exceptions:** `TodoistAuthError` (401/403) and `TodoistAPIError` (other HTTP errors) carry `.status_code` and `.response_body` for structured error inspection
- **Inspection:** `TodoistClient.get_projects()` doubles as a health check — if it returns data, the client and token are working. Field mapper is pure (no runtime signals — all side-effect-free transforms).
- **Failure visibility:** Client methods propagate typed exceptions rather than returning None/empty on failure — callers always see the error class and status code

## Inputs

- `apps/github-sync/services/github_client.py` — client pattern
- `apps/github-sync/services/field_mapper.py` — mapper pattern
- M019-RESEARCH.md field mapping table

## Expected Output

- `apps/todoist-sync/services/todoist_client.py`, `services/field_mapper.py`
- `backend/tests/test_todoist_client.py`, `test_todoist_field_mapper.py` — 55+ passing tests
