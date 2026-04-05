---
estimated_steps: 14
estimated_files: 2
skills_used: []
---

# T01: Create backend Docker entrypoint and update Dockerfile

Create a `backend/docker-entrypoint.sh` script that ensures data subdirectories exist before handing off to the CMD. Update `backend/Dockerfile` to COPY and ENTRYPOINT the script.

**Context:** The backend currently has no entrypoint — it jumps straight to `CMD ["uvicorn", ...]`. The frontend already has an entrypoint pattern at `frontend/docker-entrypoint.sh` that can be referenced. The backend runs as user `sempkm` (uid 1000) with `security_opt: no-new-privileges:true` and `cap_drop: ALL`, so gosu/su-exec are NOT viable. The entrypoint must run as `sempkm`.

**Important:** Alembic migrations are already run inside the app's lifespan startup in `backend/app/main.py` (line ~328: `alembic_command.upgrade(alembic_cfg, "head")`). Do NOT add `alembic upgrade head` to the entrypoint — it would conflict with the async migration logic.

Steps:
1. Create `backend/docker-entrypoint.sh`:
   - `#!/bin/sh`
   - `set -e`
   - `mkdir -p /app/data/apps /app/data/imports` — ensure subdirectories exist for app data and imports
   - `exec "$@"` — hand off to CMD
2. Update `backend/Dockerfile`:
   - After the `COPY app/ app/` line, add `COPY docker-entrypoint.sh /app/docker-entrypoint.sh`
   - Add `RUN chmod +x /app/docker-entrypoint.sh` (before `USER sempkm`)
   - Add `ENTRYPOINT ["/app/docker-entrypoint.sh"]` between `USER sempkm` and `CMD`
3. Verify: `docker compose build api` succeeds without errors.

## Inputs

- ``frontend/docker-entrypoint.sh` — reference pattern for the entrypoint script`
- ``backend/Dockerfile` — current Dockerfile to modify`

## Expected Output

- ``backend/docker-entrypoint.sh` — new entrypoint script ensuring data subdirectories exist`
- ``backend/Dockerfile` — updated with COPY, chmod, and ENTRYPOINT directives`

## Verification

docker compose build api 2>&1 | tail -5 && echo 'Build succeeded'
