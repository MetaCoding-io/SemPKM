---
estimated_steps: 24
estimated_files: 1
skills_used: []
---

# T02: Verify fresh-volume Docker deploy and reinstall business-planning model

Run the full fresh-volume Docker deploy cycle and fix the stale business-planning model by reinstalling it. This is primarily an operational/verification task — code changes only if issues are discovered.

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

## Inputs

- ``backend/docker-entrypoint.sh` — the new entrypoint from T01`
- ``backend/Dockerfile` — updated Dockerfile from T01`
- ``docker-compose.yml` — Docker compose configuration`
- ``models/business-planning/shapes/business-planning.jsonld` — current model archive with 33 NodeShapes`

## Expected Output

- ``scripts/verify-docker-fresh.sh` — runnable verification script for fresh-volume deploy + model install`

## Verification

test -f scripts/verify-docker-fresh.sh && echo 'Verification script exists'
