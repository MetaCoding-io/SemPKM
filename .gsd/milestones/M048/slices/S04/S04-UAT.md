# S04: Docker Permissions + Model Loading Diagnosis — UAT

**Milestone:** M048
**Written:** 2026-04-05T19:48:44.697Z

## UAT: Docker Permissions + Model Loading Diagnosis

### Preconditions
- Docker and Docker Compose installed and running
- Project repository checked out with current code
- No running SemPKM containers (or willing to stop them)

### Test 1: Entrypoint Script Exists and Is Valid
1. Verify `backend/docker-entrypoint.sh` exists
2. Check it starts with `#!/bin/sh` and contains `set -e`
3. Check it runs `mkdir -p /app/data/apps /app/data/imports`
4. Check it ends with `exec "$@"`
- **Expected:** All four checks pass — script is a valid POSIX shell entrypoint

### Test 2: Dockerfile Wiring
1. Open `backend/Dockerfile`
2. Verify `COPY docker-entrypoint.sh /app/docker-entrypoint.sh` appears after source COPY
3. Verify `RUN chmod +x /app/docker-entrypoint.sh` appears before `USER sempkm`
4. Verify `ENTRYPOINT ["/app/docker-entrypoint.sh"]` appears between `USER sempkm` and `CMD`
- **Expected:** Entrypoint is copied, made executable while still root, and set as ENTRYPOINT running as sempkm

### Test 3: Docker Build Succeeds
1. Run `docker compose build api`
- **Expected:** Build completes with exit code 0, image tagged as sempkm-api

### Test 4: Fresh-Volume Deploy — Full Cycle
1. Run `docker compose down -v` to destroy all volumes
2. Run `docker compose up --build -d`
3. Wait for all services to show "healthy" in `docker compose ps`
4. Check `docker compose logs api` for entrypoint mkdir output
- **Expected:** All 3 services (api, frontend, triplestore) healthy. No permission errors in logs.

### Test 5: Data Directories Created
1. Run `docker compose exec -T api ls -la /app/data/apps /app/data/imports`
- **Expected:** Both directories exist, owned by sempkm (uid 1000)

### Test 6: No Separate Lucene Volume
1. Run `docker compose config --volumes`
2. Verify `lucene_index` is NOT in the output
- **Expected:** Only `rdf4j_data` and other expected volumes appear — no separate lucene volume

### Test 7: Business-Planning Model Install
1. Run `curl -s -X POST http://localhost:8001/api/models/business-planning/install`
- **Expected:** 200 response indicating successful installation

### Test 8: 33 NodeShapes Loaded
1. Query the triplestore directly:
   ```
   curl -s -X POST http://localhost:8001/api/sparql \
     -H 'Content-Type: application/json' \
     -d '{"query": "SELECT (COUNT(?s) AS ?count) WHERE { GRAPH <urn:sempkm:model:business-planning:shapes> { ?s a <http://www.w3.org/ns/shacl#NodeShape> } }"}'
   ```
- **Expected:** count = 33

### Test 9: Verification Script
1. Check `scripts/verify-docker-fresh.sh` exists and is executable
2. Review script contents — should automate Tests 4–8
- **Expected:** Script exists, is executable, contains the full verification sequence

### Edge Cases

**EC1: Repeated Fresh Deploy**
1. Run `docker compose down -v && docker compose up --build -d` a second time
- **Expected:** Succeeds identically — entrypoint is idempotent (mkdir -p), repo creation is idempotent

**EC2: Triplestore Slow Start**
1. If triplestore takes >10s to initialize on a slow machine, the API's `_wait_for_repo_ready()` should retry
2. Check `docker compose logs api` for retry messages
- **Expected:** WARNING-level log lines showing retry attempts with status codes, eventual success
