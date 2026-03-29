---
id: T02
parent: S03
milestone: M046
provides: []
requires: []
affects: []
key_files: ["docker-compose.test.yml"]
key_decisions: []
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "All 5 services present as top-level compose definitions. All 7 env vars present. All 5 depends_on entries present. docker compose config validates YAML. APP_BASE_URL confirmed present from T01."
completed_at: 2026-03-29T02:14:02.232Z
blocker_discovered: false
---

# T02: Added 5 mock API services (todoist, asana, caldav, google-calendar, outlook) with env vars and depends_on entries to docker-compose.test.yml

> Added 5 mock API services (todoist, asana, caldav, google-calendar, outlook) with env vars and depends_on entries to docker-compose.test.yml

## What Happened
---
id: T02
parent: S03
milestone: M046
key_files:
  - docker-compose.test.yml
key_decisions:
  - (none)
duration: ""
verification_result: passed
completed_at: 2026-03-29T02:14:02.232Z
blocker_discovered: false
---

# T02: Added 5 mock API services (todoist, asana, caldav, google-calendar, outlook) with env vars and depends_on entries to docker-compose.test.yml

**Added 5 mock API services (todoist, asana, caldav, google-calendar, outlook) with env vars and depends_on entries to docker-compose.test.yml**

## What Happened

Added 5 new Docker service definitions to docker-compose.test.yml following the exact pattern of existing mock services: python:3.12-slim image, volume mount from e2e/mock-*-api, health check via urllib, sempkm-test network. Added 7 environment variables to the api service (TODOIST_API_URL, ASANA_API_URL, ASANA_TOKEN_URL, GCAL_API_URL, GOOGLE_TOKEN_URL, OUTLOOK_API_URL, OUTLOOK_TOKEN_URL). Added depends_on with service_healthy condition for all 5 new services. The original verification gate failure was a path resolution issue (../docker-compose.test.yml), not a content issue.

## Verification

All 5 services present as top-level compose definitions. All 7 env vars present. All 5 depends_on entries present. docker compose config validates YAML. APP_BASE_URL confirmed present from T01.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose -f docker-compose.test.yml config > /dev/null 2>&1` | 0 | ✅ pass | 500ms |
| 2 | `grep -q 'TODOIST_API_URL' docker-compose.test.yml` | 0 | ✅ pass | 10ms |
| 3 | `grep -q 'GCAL_API_URL' docker-compose.test.yml` | 0 | ✅ pass | 10ms |
| 4 | `grep -q 'OUTLOOK_API_URL' docker-compose.test.yml` | 0 | ✅ pass | 10ms |
| 5 | `grep -q 'APP_BASE_URL' docker-compose.test.yml` | 0 | ✅ pass | 10ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docker-compose.test.yml`


## Deviations
None.

## Known Issues
None.
