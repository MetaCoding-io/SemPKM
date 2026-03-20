---
estimated_steps: 6
estimated_files: 3
---

# T02: Wire script into Docker Compose, create deploy wrapper, and verify against live stack

**Slice:** S02 — Sample data generation script
**Milestone:** M025

## Description

The seed script from T01 exists on disk but can't be executed inside the Docker container without a volume mount, and there's no documented deployment flow. This task wires the script into the demo compose stack, creates a deployment wrapper, and verifies the full seeding flow works against a live Docker stack.

**Critical constraint from S01 Forward Intelligence:** The demo nginx blocks ALL POST methods. The seed script bypasses this by running inside the API container via `docker compose exec` and importing app modules directly — it never touches HTTP. However, `DEMO_MODE=true` is set on the API container, which makes `get_current_user` return a guest user. Since the seed script doesn't use HTTP auth at all (direct module imports), this is fine — but the `settings.demo_mode` flag IS visible to any code that reads config. The script's `ModelService.install()` and `EventStore.commit()` do NOT check `demo_mode`, so they work regardless.

## Steps

1. **Add `./scripts:/app/scripts:ro` volume mount to `docker-compose.demo.yml`** in the `api` service's `volumes` section. Add it after the existing `./docs:/app/docs:ro` mount. The `:ro` flag is intentional — the script only reads from this mount.

2. **Create `scripts/deploy-demo.sh`** — a Bash wrapper that orchestrates the full demo deployment:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   
   COMPOSE_FILE="docker-compose.demo.yml"
   
   echo "=== SemPKM Demo Deployment ==="
   
   # 1. Start the demo stack
   echo "[1/4] Starting demo stack..."
   docker compose -f "$COMPOSE_FILE" up -d --build
   
   # 2. Wait for API health
   echo "[2/4] Waiting for API to be healthy..."
   until docker compose -f "$COMPOSE_FILE" exec -T api curl -sf http://localhost:8000/api/health > /dev/null 2>&1; do
     sleep 2
   done
   echo "  API is healthy."
   
   # 3. Run seed script
   echo "[3/4] Seeding demo data..."
   docker compose -f "$COMPOSE_FILE" exec -T api python /app/scripts/seed-demo-data.py
   
   # 4. Verify
   echo "[4/4] Verifying..."
   docker compose -f "$COMPOSE_FILE" exec -T api python /app/scripts/seed-demo-data.py --verify-only
   
   echo ""
   echo "=== Demo instance ready ==="
   echo "  Frontend: http://localhost:3902"
   echo "  API:      http://localhost:8902"
   ```
   - Make executable with `chmod +x scripts/deploy-demo.sh`

3. **Start the demo stack** and verify it comes up healthy:
   ```bash
   docker compose -f docker-compose.demo.yml up -d --build
   ```
   - Wait for API health check to pass
   - Verify basic-pkm auto-installed: `curl http://localhost:8902/api/models`

4. **Run the seed script** inside the container:
   ```bash
   docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py
   ```
   - Watch for any import errors, connection issues, or permission problems
   - Fix any issues in the script (update T01's output file directly)

5. **Verify seeded data** — run all verification checks:
   - `curl http://localhost:8902/api/models | python3 -m json.tool` — 4 models listed
   - `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py --verify-only` — counts check out
   - Navigate browser to `http://localhost:3902/browser/` — objects visible in explorer
   - Re-run the seed script to confirm idempotency — no errors, no new data created

6. **Tear down the demo stack** after verification:
   ```bash
   docker compose -f docker-compose.demo.yml down -v
   ```

## Must-Haves

- [ ] `docker-compose.demo.yml` has `./scripts:/app/scripts:ro` volume mount on api service
- [ ] `scripts/deploy-demo.sh` wrapper orchestrates start → health wait → seed → verify
- [ ] Seed script runs successfully inside the container with no import or connection errors
- [ ] 4 models visible in `GET /api/models` response
- [ ] Re-running seed script produces no errors and no duplicate data
- [ ] Script's built-in verification reports ≥50 objects and ≥10 cross-model edges

## Verification

- `docker compose -f docker-compose.demo.yml config --quiet` — compose YAML valid
- `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py` — exits 0
- `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py --verify-only` — reports ≥50 objects, ≥10 edges
- `curl http://localhost:8902/api/models | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)>=4, f'Expected 4+ models, got {len(d)}'"` — passes
- Re-run seed script — exits 0 with all "skipped" messages (idempotency proof)

## Observability Impact

- Signals added/changed: deploy-demo.sh prints phased progress with clear labels
- How a future agent inspects this: `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py --verify-only` re-runs just verification
- Failure state exposed: seed script prints per-phase errors to stderr without aborting

## Inputs

- `scripts/seed-demo-data.py` — T01's output, the complete seed script
- `docker-compose.demo.yml` — S01's output, the demo compose stack definition
- S01 Summary: demo stack on ports 3902/8902, nginx blocks POST, API has DEMO_MODE=true

## Expected Output

- `docker-compose.demo.yml` — Modified: `./scripts:/app/scripts:ro` volume added
- `scripts/deploy-demo.sh` — New: deployment wrapper script (executable)
- `scripts/seed-demo-data.py` — Possibly modified: any bug fixes discovered during live testing
- Verification evidence: seed script exit 0, 4 models installed, ≥50 objects, ≥10 cross-model edges, idempotent re-run
