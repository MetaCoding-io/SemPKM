#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.demo.yml"
HEALTH_URL="http://localhost:8000/api/health"
MAX_WAIT=120

echo "=== SemPKM Demo Reset ==="
echo "  Started at: $(date -Iseconds)"

# 1. Tear down the stack (including volumes for clean state)
echo "[1/5] Tearing down demo stack..."
docker compose -f "$COMPOSE_FILE" down -v

# 2. Rebuild and start fresh
echo "[2/5] Rebuilding and starting demo stack..."
docker compose -f "$COMPOSE_FILE" up -d --build

# 3. Wait for API health
echo "[3/5] Waiting for API to be healthy (timeout: ${MAX_WAIT}s)..."
elapsed=0
until docker compose -f "$COMPOSE_FILE" exec -T api curl -sf "$HEALTH_URL" > /dev/null 2>&1; do
  sleep 2
  elapsed=$((elapsed + 2))
  if [ "$elapsed" -ge "$MAX_WAIT" ]; then
    echo "  ERROR: API did not become healthy within ${MAX_WAIT}s"
    exit 1
  fi
done
echo "  API is healthy after ${elapsed}s."

# 4. Re-seed demo data
echo "[4/5] Seeding demo data..."
docker compose -f "$COMPOSE_FILE" exec -T api python /app/scripts/seed-demo-data.py

# 5. Verify seed data
echo "[5/5] Verifying demo data..."
docker compose -f "$COMPOSE_FILE" exec -T api python /app/scripts/seed-demo-data.py --verify-only

echo ""
echo "=== Demo reset complete ==="
echo "  Finished at: $(date -Iseconds)"
echo "  Frontend: http://localhost:3902"
echo "  API:      http://localhost:8902"
