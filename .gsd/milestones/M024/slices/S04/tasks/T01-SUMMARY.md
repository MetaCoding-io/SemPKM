---
id: T01
parent: S04
milestone: M024
provides:
  - Mock Monday.com GraphQL server with 10 query shapes and selftest
  - Docker compose mock-monday service with MONDAY_API_URL env var
key_files:
  - e2e/mock-monday-api/server.py
  - docker-compose.test.yml
key_decisions:
  - Used "{ me " (with space) as substring matcher instead of bare "me" to avoid false matches on queries containing "me" as a substring (e.g. "somethingUnknown")
patterns_established:
  - Monday.com mock uses POST / (root path) unlike Linear's POST /graphql — matches Monday.com's single-endpoint GraphQL API
observability_surfaces:
  - python e2e/mock-monday-api/server.py --selftest — 12 checks, exits 0/1
  - GET /health on mock-monday:8080 — Docker healthcheck
  - [mock-monday] prefixed stderr logs for query dispatch visibility
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Mock Monday.com GraphQL server + Docker integration

**Created mock Monday.com GraphQL API server with 12-check selftest and wired mock-monday service into Docker test stack with MONDAY_API_URL env var**

## What Happened

Built `e2e/mock-monday-api/server.py` following the Linear mock's substring-dispatch pattern and the Jira mock's selftest infrastructure (`_FakeRequestFile`/`_FakeWFile`/`_make_fake_handler`). The mock handles all 10 query shapes from `monday_client.py`: `me`, `boards(limit`, `boards(ids:` with `columns`, `boards(ids:` with `items_page`, `boards(ids:` with `groups`, `items(ids:` with `subitems`, `users(ids:`, `tags(ids:`, `change_multiple_column_values` mutation, and `create_item` mutation.

Key implementation details:
- POST endpoint is at `/` (root path), not `/graphql` — matches Monday.com's single-endpoint API
- All responses wrapped in `{"data": {...}}`
- `settings_str` values are JSON strings (double-encoded) containing `{"labels": {...}}` for status/priority columns
- Items include realistic `column_values` covering status, priority, date, people, tags, dependency, and numbers types
- Items include `group { id title }` metadata (Sprint 5 and Backlog groups)
- Subitems response includes one subitem with parent augmentation support
- The `me` matcher uses `"{ me "` (with space) to avoid false-matching queries that contain "me" as a substring

Updated `docker-compose.test.yml` with `mock-monday` service block (python:3.12-slim, healthcheck on `/health`), `MONDAY_API_URL: http://mock-monday:8080` in api environment, and `mock-monday` in api `depends_on` with `condition: service_healthy`.

## Verification

- `python3 e2e/mock-monday-api/server.py --selftest` — 12 passed, 0 failed
- `docker compose -f docker-compose.test.yml config --quiet` — exits 0 (valid YAML)
- `python3 -c "import ast; ast.parse(open('e2e/mock-monday-api/server.py').read())"` — syntax valid
- `grep -c "MONDAY_API_URL" docker-compose.test.yml` — 1 match
- `grep -c "mock-monday" docker-compose.test.yml` — 4 matches (service block, depends_on, env var reference)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 e2e/mock-monday-api/server.py --selftest` | 0 | ✅ pass | <1s |
| 2 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import ast; ast.parse(open('e2e/mock-monday-api/server.py').read())"` | 0 | ✅ pass | <1s |

### Slice-level verification (partial — T01 scope only)

| # | Command | Exit Code | Verdict | Notes |
|---|---------|-----------|---------|-------|
| 1 | `python3 e2e/mock-monday-api/server.py --selftest` | 0 | ✅ pass | 12 passed, 0 failed |
| 2 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass | Valid YAML |
| 3 | `cd backend && uv run python -m pytest tests/test_monday_*.py -v` | — | ⏳ not run | Regression check deferred (not modified by this task) |
| 4 | `test -f docs/guide/37-monday-sync.md` | — | ⏳ T03 | Not yet created |
| 5 | Navigation file updates | — | ⏳ T03 | Not yet created |
| 6 | E2E test | — | ⏳ T02 | Not yet created |

## Diagnostics

- **Selftest**: `python3 e2e/mock-monday-api/server.py --selftest` — runs all 12 checks in-process, no Docker required
- **Request logs**: In Docker, `docker compose -f docker-compose.test.yml logs mock-monday` shows `[mock-monday] Matched query type: X` for each dispatched query
- **Unmatched queries**: Logged with `[mock-monday] Unmatched query (fallback): <first 120 chars>` — useful for debugging if E2E tests get unexpected empty responses
- **Health**: `curl http://localhost:8080/health` → `{"status": "ok"}` when running

## Deviations

- Changed `me` matcher from bare `"me"` to `"{ me "` (with surrounding syntax chars) because `somethingUnknown` contains the substring `me`, causing the fallback test to match the wrong response. This is more robust and still matches the actual query `{ me { id name email } }`.

## Known Issues

None.

## Files Created/Modified

- `e2e/mock-monday-api/server.py` — New mock Monday.com GraphQL server (~450 lines) with 10 query shape handlers and 12-check selftest
- `docker-compose.test.yml` — Added mock-monday service, MONDAY_API_URL env var, and depends_on entry
- `.gsd/milestones/M024/slices/S04/S04-PLAN.md` — Added Observability/Diagnostics section, marked T01 done
- `.gsd/milestones/M024/slices/S04/tasks/T01-PLAN.md` — Added Observability Impact section
