---
id: T01
parent: S02
milestone: M045
provides: []
requires: []
affects: []
key_files: ["backend/Dockerfile", "docker-compose.yml", "docker-compose.test.yml", "docker-compose.demo.yml", "docker-compose.cloud.yml", "docker-compose.federation-test.yml", "docker-compose.test-ollama.yml"]
key_decisions: ["Cloud compose overlay inherits security_opt/cap_drop from base — no duplication to avoid compose validation error"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Dockerfile builds successfully. Container runs as uid=1000(sempkm). /app/data owned by sempkm:sempkm. All 6 compose files validate cleanly. no-new-privileges present in all standalone compose files. Cloud overlay merged config confirmed with security directives on both services."
completed_at: 2026-03-29T00:01:11.373Z
blocker_discovered: false
---

# T01: Hardened backend Dockerfile to run as non-root UID 1000 (sempkm) and added security_opt/cap_drop to all 6 compose files

> Hardened backend Dockerfile to run as non-root UID 1000 (sempkm) and added security_opt/cap_drop to all 6 compose files

## What Happened
---
id: T01
parent: S02
milestone: M045
key_files:
  - backend/Dockerfile
  - docker-compose.yml
  - docker-compose.test.yml
  - docker-compose.demo.yml
  - docker-compose.cloud.yml
  - docker-compose.federation-test.yml
  - docker-compose.test-ollama.yml
key_decisions:
  - Cloud compose overlay inherits security_opt/cap_drop from base — no duplication to avoid compose validation error
duration: ""
verification_result: passed
completed_at: 2026-03-29T00:01:11.374Z
blocker_discovered: false
---

# T01: Hardened backend Dockerfile to run as non-root UID 1000 (sempkm) and added security_opt/cap_drop to all 6 compose files

**Hardened backend Dockerfile to run as non-root UID 1000 (sempkm) and added security_opt/cap_drop to all 6 compose files**

## What Happened

Added a sempkm system user (UID 1000) to the backend Dockerfile with USER directive after all root-requiring build steps. Removed --reload from production CMD. Added security_opt: no-new-privileges:true and cap_drop: ALL to every api and frontend service across all compose files. Dev compose restores hot-reload via command override. Cloud overlay inherits security directives from base compose.

## Verification

Dockerfile builds successfully. Container runs as uid=1000(sempkm). /app/data owned by sempkm:sempkm. All 6 compose files validate cleanly. no-new-privileges present in all standalone compose files. Cloud overlay merged config confirmed with security directives on both services.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q 'USER sempkm' backend/Dockerfile` | 0 | ✅ pass | 100ms |
| 2 | `! grep '\-\-reload' backend/Dockerfile` | 0 | ✅ pass | 100ms |
| 3 | `grep -c 'no-new-privileges' docker-compose*.yml` | 0 | ✅ pass | 100ms |
| 4 | `docker compose config --quiet (all 6 files)` | 0 | ✅ pass | 2000ms |
| 5 | `docker build backend/ --no-cache` | 0 | ✅ pass | 45000ms |
| 6 | `docker run --rm sempkm-test-build id` | 0 | ✅ pass | 1000ms |
| 7 | `docker run --rm sempkm-test-build stat /app/data` | 0 | ✅ pass | 1000ms |


## Deviations

Cloud compose overlay does not duplicate security_opt/cap_drop — it inherits from base compose. Adding duplicates caused validation error.

## Known Issues

None.

## Files Created/Modified

- `backend/Dockerfile`
- `docker-compose.yml`
- `docker-compose.test.yml`
- `docker-compose.demo.yml`
- `docker-compose.cloud.yml`
- `docker-compose.federation-test.yml`
- `docker-compose.test-ollama.yml`


## Deviations
Cloud compose overlay does not duplicate security_opt/cap_drop — it inherits from base compose. Adding duplicates caused validation error.

## Known Issues
None.
