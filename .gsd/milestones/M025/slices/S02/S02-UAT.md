# S02: Sample data generation script — UAT

**Milestone:** M025
**Written:** 2026-03-20

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: The seed script must run against a live Docker stack with triplestore — artifact-only verification cannot confirm data persistence, model installation, or SPARQL counts.

## Preconditions

- Docker and Docker Compose installed
- No other SemPKM stack running on ports 3902/8902/7202
- Working directory is the repository root (where `docker-compose.demo.yml` exists)
- Internet access for Docker image pulls (first run only)

## Smoke Test

Run `bash scripts/deploy-demo.sh` — it should start the demo stack, seed data, and print "Demo instance ready" with frontend URL at `http://localhost:3902`.

## Test Cases

### 1. Full deployment pipeline via deploy-demo.sh

1. Run `bash scripts/deploy-demo.sh`
2. Wait for all 4 phases to complete (typically 30-60s)
3. **Expected:** Script prints `[1/4] Starting demo stack...`, `[2/4] Waiting for API to be healthy...`, `[3/4] Seeding demo data...`, `[4/4] Verifying...`, then `=== Demo instance ready ===` with URLs

### 2. Seed script installs all 4 models

1. Run `curl -s http://localhost:8902/api/models | python3 -m json.tool`
2. **Expected:** JSON array with 4 models: basic-pkm, crm, research, zettelkasten (order may vary)

### 3. Object count meets threshold

1. Run `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py --verify-only`
2. **Expected:** Verification output shows: objects ≥50 (actual should be ~74), models ≥4, edges ≥10 (actual should be 12), bodies ≥8 (actual should be 10). All checks show ✓.

### 4. Types from all models visible via API

1. Run `curl -s http://localhost:8902/api/types | python3 -c "import json,sys; types=json.load(sys.stdin); print(f'{len(types)} types'); models=set(t['model_id'] for t in types); print(f'Models: {sorted(models)}')" `
2. **Expected:** ~21 types listed, with model_ids from all 4 installed models

### 5. Cross-model edges exist in triplestore

1. Run `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py --verify-only`
2. Check the "cross-model edges" line
3. **Expected:** ≥10 cross-model edges reported (actual should be 12)

### 6. Markdown bodies set on objects

1. Run `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py --verify-only`
2. Check the "bodies" line
3. **Expected:** ≥8 bodies reported (actual should be 10)

### 7. Anonymous access still works after seeding

1. Open `http://localhost:3902/browser/` in a fresh browser (no cookies)
2. **Expected:** Workspace loads without login page — explorer shows objects from all 4 models

### 8. Write-blocking still enforced after seeding

1. Run `curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:3902/api/commands -H 'Content-Type: application/json' -d '{}'`
2. **Expected:** HTTP 403

## Edge Cases

### Idempotent re-run

1. Run the seed script a second time: `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py`
2. **Expected:** All models report "already installed (skipped)", all edges report "already exists (skipped)". Exit code 0. Object counts unchanged from first run.

### --verify-only against empty stack

1. Start a fresh demo stack without running the seed script: `docker compose -f docker-compose.demo.yml up -d --build`
2. Wait for health, then run: `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py --verify-only`
3. **Expected:** Verification reports lower counts (only basic-pkm auto-installed, ~12 objects from its seed data). Some checks may show ✗ for not meeting thresholds. Exit code may be non-zero or verification table shows failures. Script does NOT modify data.

### Stack teardown and rebuild

1. Run `docker compose -f docker-compose.demo.yml down -v` to destroy all data
2. Run `bash scripts/deploy-demo.sh` again
3. **Expected:** Full seed pipeline succeeds from scratch. Same object/edge/body counts as first run.

## Failure Signals

- Seed script prints `✗ failed` for any item — indicates an edge creation or body set failure
- `ModuleNotFoundError: No module named 'app'` — sys.path fix missing or script moved from expected location
- `curl /api/models` returns fewer than 4 models — model installation failed
- Verification counts below thresholds (objects <50, edges <10, bodies <8) — partial seed failure
- `deploy-demo.sh` hangs on health check — API container failed to start
- Re-run creates duplicate data (edge count increases) — idempotency check broken

## Requirements Proved By This UAT

- DEMO-03 (Sample data) — partially proved; 74 objects across 4 models with 12 cross-model edges and 10 markdown bodies, verified by SPARQL counts and API queries. Full visual verification in explorer/graph/table deferred to S03.
- DEMO-01 (Anonymous access) — regression-checked by test case 7 (still works after seeding)
- DEMO-02 (Read-only enforcement) — regression-checked by test case 8 (still enforced after seeding)

## Not Proven By This UAT

- Visual appearance of sample data in explorer, graph, and table views (requires browser testing — S03)
- SHACL validation warnings firing on seed data (requires workspace lint page — S03)
- Demo tour referencing specific seed objects (S03)
- Dashboard rendering with seed data (S03)
- SSL termination and cloud deployment (S04)

## Notes for Tester

- The demo stack uses ports 3902/8902/7202 to avoid conflicting with the dev stack (3901/8901/7201)
- First `docker compose up` pulls images and builds — may take 2-5 minutes. Subsequent starts are fast.
- The seed script takes ~5 seconds on first run (model installs are the slow part)
- If you see `"Connection refused"` from curl, the API may still be starting — wait a few seconds and retry
- `--verify-only` is safe to run at any time without modifying data
- The object count of 74 exceeds the milestone target of 30-50 — this is expected and correct
