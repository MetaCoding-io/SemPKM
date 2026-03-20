---
id: T01
parent: S04
milestone: M022
provides:
  - Mock Asana REST API server with 14-check selftest
key_files:
  - e2e/mock-asana-api/server.py
key_decisions:
  - Added /api/1.0/projects/{gid}/custom_field_settings as a separate endpoint since the AsanaClient calls it independently from the single-project GET
patterns_established:
  - Asana envelope pattern: {"data": obj} for single items, {"data": [...], "next_page": null} for lists
observability_surfaces:
  - "[mock-asana] METHOD /path → STATUS" stderr logs on every request
  - GET /health returns {"status": "ok"} for Docker healthcheck
  - --selftest mode exercises all 14 checks with per-check pass/fail output
duration: 20m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Build mock Asana REST API server with selftest

**Mock Asana REST API server with 14 endpoints, Bearer auth, Asana envelope format, and selftest — all 14 checks pass.**

## What Happened

Built `e2e/mock-asana-api/server.py` (~550 lines) following the established mock server pattern from `e2e/mock-todoist-api/server.py`. The server provides canned responses for all endpoints the `AsanaClient` calls:

- `/health` (no auth), `/api/1.0/users/me`, `/api/1.0/workspaces`, `/api/1.0/workspaces/{gid}/projects`
- `/api/1.0/projects/{gid}` (single project with custom_field_settings), `/api/1.0/projects/{gid}/custom_field_settings` (separate endpoint)
- `/api/1.0/projects/{gid}/sections`, `/api/1.0/projects/{gid}/tasks`
- `/api/1.0/tasks/{gid}/subtasks`, `PATCH /api/1.0/tasks/{gid}`, `POST /api/1.0/sections/{gid}/addTask`

Canned data: 1 user, 1 workspace, 2 projects, 3 sections per project, 3 custom fields (Status enum, Priority enum, Story Points number), 3 tasks with full custom_fields/memberships/tags/assignee, 1 subtask.

Task data includes all fields the sync engine requests via `TASK_OPT_FIELDS`: custom_fields with enum_value GIDs matching project custom_field_settings, memberships with section {gid, name}, tags, assignee with email, followers, parent, permalink_url, resource_subtype, dates, and timestamps.

## Verification

- `python3 e2e/mock-asana-api/server.py --selftest` — 14/14 checks pass
- `python3 -c "import ast; ast.parse(open('e2e/mock-asana-api/server.py').read())"` — syntax OK
- Slice-level selftest check passes; remaining slice checks (docker-compose, selectors, E2E spec, docs) are T02/T03 work

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 e2e/mock-asana-api/server.py --selftest` | 0 | ✅ pass | 2.6s |
| 2 | `python3 -c "import ast; ast.parse(open('e2e/mock-asana-api/server.py').read())"` | 0 | ✅ pass | 2.6s |
| 3 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass (pre-existing) | <1s |
| 4 | `grep -c "asanaSync" e2e/helpers/selectors.ts` | 1 | ⏳ expected 0 (T02) | <1s |
| 5 | `test -f e2e/tests/40-asana-sync/asana-sync.spec.ts` | 1 | ⏳ expected (T02) | <1s |
| 6 | `test -f docs/guide/40-asana-sync.md` | 1 | ⏳ expected (T03) | <1s |

## Diagnostics

- **Selftest:** `python3 e2e/mock-asana-api/server.py --selftest` — exercises all endpoints with pass/fail per check
- **Request logging:** Every request logged to stderr as `[mock-asana] METHOD /path → STATUS`
- **Health:** `GET /health` returns `{"status": "ok"}` — use for Docker healthcheck
- **Auth failure shape:** `401 {"errors": [{"message": "Not Authorized"}]}`
- **Not found shape:** `404 {"errors": [{"message": "Not Found"}]}`

## Deviations

- Added `/api/1.0/projects/{gid}/custom_field_settings` as a separate list endpoint (not in original plan) because the `AsanaClient.get_custom_fields()` method calls this path directly rather than extracting custom_field_settings from the single-project response. Both endpoints are now covered.
- Selftest has 14 checks instead of the planned ~12 — added custom_field_settings endpoint check and 404-for-unknown-project check.

## Known Issues

None.

## Files Created/Modified

- `e2e/mock-asana-api/server.py` — Mock Asana REST API server (~550 lines), 14 endpoints, Bearer auth, Asana envelope format, selftest
- `.gsd/milestones/M022/slices/S04/S04-PLAN.md` — Added Observability / Diagnostics section
- `.gsd/milestones/M022/slices/S04/tasks/T01-PLAN.md` — Added Observability Impact section
