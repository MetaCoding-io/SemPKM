# S02: Sample data generation script

**Goal:** A self-contained Python seed script installs 4 Mental Models and creates cross-model edges + markdown bodies, producing 61 interconnected objects visible in the demo instance's explorer, graph, and table views with validation warnings firing.

**Demo:** Run `docker compose -f docker-compose.demo.yml exec api python /app/scripts/seed-demo-data.py` against a fresh demo stack → 4 models installed, 61 objects with ~12 cross-model edges and ~8 rich markdown bodies visible in the explorer, graph view shows interconnected clusters, SHACL validation warnings fire for overdue task, stale contact, and unprocessed fleeting note.

## Must-Haves

- Script installs 3 non-default models (crm, zettelkasten, research — basic-pkm auto-installs at startup)
- ~12 cross-model edges connect objects across model boundaries (visible in graph view)
- ~8-10 key objects have markdown bodies set (visible in object read view)
- Idempotent — safe to run multiple times without duplicate edges or errors
- Validation warnings fire on seed data (overdue task, stale contact, unprocessed fleeting note)
- `docker-compose.demo.yml` mounts `./scripts/` into the container
- Deployment wrapper script orchestrates: start stack → wait health → seed → verify

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Docker stack with triplestore)
- Human/UAT required: no

## Verification

- `docker compose -f docker-compose.demo.yml exec api python /app/scripts/seed-demo-data.py` completes without errors
- Script's built-in verification phase reports ≥50 objects, 4 installed models, ≥10 cross-model edges
- `curl http://localhost:8902/api/models | python3 -m json.tool` shows 4 models
- `curl http://localhost:3902/browser/lint` returns page with validation warnings
- Re-running the script produces no errors and no duplicate data (idempotency)

## Observability / Diagnostics

- Runtime signals: Script prints phased progress (`[1/5] Installing models...`, `[2/5] Creating edges...`, etc.) with per-step counts
- Inspection surfaces: Script's `--verify-only` flag re-runs just the verification phase against an existing stack
- Failure visibility: Each phase catches and reports per-item errors without aborting the whole script

## Integration Closure

- Upstream surfaces consumed: `docker-compose.demo.yml` (S01), `DEMO_MODE=true` env var (S01), `frontend/nginx.demo.conf` (S01)
- New wiring introduced in this slice: `./scripts:/app/scripts:ro` volume mount in docker-compose.demo.yml, `scripts/deploy-demo.sh` wrapper
- What remains before the milestone is truly usable end-to-end: S03 (demo tour + dashboard + CTA), S04 (SSL + E2E + docs)

## Tasks

- [x] **T01: Write seed-demo-data.py with model install, cross-model edges, and markdown bodies** `est:1h30m`
  - Why: The core deliverable — a script that transforms a bare demo stack into a richly populated demo instance with interconnected data across 4 models
  - Files: `scripts/seed-demo-data.py`
  - Do: Write an async Python script that imports app modules directly (TriplestoreClient, EventStore, ModelService, PrefixRegistry). Phase 1: install crm, zettelkasten, research models (basic-pkm auto-installs). Phase 2: create ~12 cross-model edges via EventStore.commit(). Phase 3: set markdown bodies on ~8-10 key objects. Phase 4: verify counts via SPARQL. All phases idempotent — check before creating.
  - Verify: `python -c "import ast; ast.parse(open('scripts/seed-demo-data.py').read())"` — valid Python syntax
  - Done when: Script parses cleanly and contains all 4 phases with idempotency checks, cross-model edge definitions, and markdown body content

- [x] **T02: Wire script into Docker Compose, create deploy wrapper, and verify against live stack** `est:45m`
  - Why: The script must be accessible inside the container and the full deployment flow must work end-to-end — without this integration wiring, the script is just a file on disk
  - Files: `docker-compose.demo.yml`, `scripts/deploy-demo.sh`, `scripts/seed-demo-data.py` (minor fixes if needed)
  - Do: Add `./scripts:/app/scripts:ro` volume mount to the api service in docker-compose.demo.yml. Create `scripts/deploy-demo.sh` that orchestrates: start demo stack, wait for health, exec seed script, verify. Start the demo stack, run the seed script, verify object counts and validation warnings.
  - Verify: `bash scripts/deploy-demo.sh` completes successfully with all verification checks passing
  - Done when: Demo stack has 4 models installed, ≥50 objects visible, cross-model edges in graph, validation warnings firing, and re-running the seed script is idempotent

## Files Likely Touched

- `scripts/seed-demo-data.py` — New: the seed script
- `scripts/deploy-demo.sh` — New: deployment wrapper
- `docker-compose.demo.yml` — Modified: add scripts volume mount
