---
id: T01
parent: S03
milestone: M046
provides: []
requires: []
affects: []
key_files: ["backend/app/apps/scheduler.py", "docker-compose.test.yml"]
key_decisions: []
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "AST parse of scheduler.py passed (no syntax errors). grep confirmed APP_BASE_URL present in docker-compose.test.yml."
completed_at: 2026-03-29T02:12:18.282Z
blocker_discovered: false
---

# T01: Fix naive/aware datetime crash in scheduler and add APP_BASE_URL to test compose for app subprocess startup

> Fix naive/aware datetime crash in scheduler and add APP_BASE_URL to test compose for app subprocess startup

## What Happened
---
id: T01
parent: S03
milestone: M046
key_files:
  - backend/app/apps/scheduler.py
  - docker-compose.test.yml
key_decisions:
  - (none)
duration: ""
verification_result: passed
completed_at: 2026-03-29T02:12:18.282Z
blocker_discovered: false
---

# T01: Fix naive/aware datetime crash in scheduler and add APP_BASE_URL to test compose for app subprocess startup

**Fix naive/aware datetime crash in scheduler and add APP_BASE_URL to test compose for app subprocess startup**

## What Happened

Fixed two bugs blocking app subprocesses in the test container: (1) scheduler.py crashed with TypeError when subtracting timezone-aware `now` from naive SQLite `started_at` — applied the established project pattern of normalizing naive datetimes to UTC before subtraction; (2) docker-compose.test.yml lacked APP_BASE_URL, causing the default http://localhost:4000 to be used when the test API listens on port 8000 — added APP_BASE_URL: http://localhost:8000.

## Verification

AST parse of scheduler.py passed (no syntax errors). grep confirmed APP_BASE_URL present in docker-compose.test.yml.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('app/apps/scheduler.py').read())"` | 0 | ✅ pass | 200ms |
| 2 | `grep -q 'APP_BASE_URL' ../docker-compose.test.yml` | 0 | ✅ pass | 50ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/scheduler.py`
- `docker-compose.test.yml`


## Deviations
None.

## Known Issues
None.
