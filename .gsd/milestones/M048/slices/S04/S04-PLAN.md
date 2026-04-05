# S04: Docker Permissions + Model Loading Diagnosis

**Goal:** Docker fresh-volume deploy succeeds with robust entrypoint, and reinstalled business-planning model loads all 33 NodeShapes.
**Demo:** After this: docker compose down -v && docker compose up --build -d succeeds on fresh volume. Install business-planning model → SPARQL query confirms all 33 NodeShapes loaded.

## Tasks
- [x] **T01: Added backend/docker-entrypoint.sh ensuring /app/data/apps and /app/data/imports exist on startup, wired into Dockerfile as ENTRYPOINT** — Create a `backend/docker-entrypoint.sh` script that ensures data subdirectories exist before handing off to the CMD. Update `backend/Dockerfile` to COPY and ENTRYPOINT the script.

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
  - Estimate: 15m
  - Files: backend/docker-entrypoint.sh, backend/Dockerfile
  - Verify: docker compose build api 2>&1 | tail -5 && echo 'Build succeeded'
- [x] **T02: Verify fresh-volume Docker deploy and reinstall business-planning model** — Run the full fresh-volume Docker deploy cycle and fix the stale business-planning model by reinstalling it. This is primarily an operational/verification task — code changes only if issues are discovered.

**Context — stale model data:** The business-planning model was installed 2026-03-23 from an older archive with only 2 NodeShapes (EisenhowerMatrix + EisenhowerItem). The current archive at `models/business-planning/shapes/business-planning.jsonld` has 33 NodeShapes across 1665 triples. The install pipeline is correct — this is a stale data issue.

**Context — user-data guard:** The `remove()` method in `backend/app/services/models.py:754` checks for user data before allowing removal. Since the installed model created seed data (Eisenhower instances exist in `urn:sempkm:current`), the standard uninstall will be BLOCKED with: "Cannot remove model 'business-planning': user data exists for types: ..."

**Context — model named graphs:** The model uses these named graphs (from `backend/app/models/registry.py:25`, class `ModelGraphs`):
- `urn:sempkm:model:business-planning:ontology`
- `urn:sempkm:model:business-planning:shapes`
- `urn:sempkm:model:business-planning:views`
- `urn:sempkm:model:business-planning:seed`
- `urn:sempkm:model:business-planning:rules`
- Registration triples in `urn:sempkm:models`

Steps:
1. Bring up Docker stack fresh: `docker compose down -v && docker compose up --build -d`
2. Wait for all services healthy: `docker compose ps` — all should show "healthy"
3. Check `docker compose logs api` for entrypoint output (mkdir should succeed)
4. Install business-planning model via API: `curl -s -X POST http://localhost:8001/api/models/business-planning/install`
5. Verify 33 NodeShapes loaded via SPARQL query against the triplestore:
   ```
   curl -s -X POST http://localhost:8001/api/sparql \
     -H 'Content-Type: application/json' \
     -d '{"query": "SELECT (COUNT(?s) AS ?count) WHERE { GRAPH <urn:sempkm:model:business-planning:shapes> { ?s a <http://www.w3.org/ns/shacl#NodeShape> } }"}'
   ```
   Expected: count = 33
6. If the fresh-volume install succeeds with 33 shapes, the stale data theory is confirmed and the fix is simply 'reinstall from current archive on fresh data'.

**If Docker is not available in the execution environment:** Document the verification commands in a runnable script `scripts/verify-docker-fresh.sh` so it can be run manually.
  - Estimate: 25m
  - Files: scripts/verify-docker-fresh.sh
  - Verify: test -f scripts/verify-docker-fresh.sh && echo 'Verification script exists'
