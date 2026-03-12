#!/usr/bin/env bash
# Start the federation test environment with two SemPKM instances.
# Always tears down first to ensure a clean state.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.federation-test.yml"

echo "==> Generating per-instance nginx configs..."
mkdir -p "$REPO_ROOT/e2e/federation"
sed 's|http://api:|http://api-a:|g' "$REPO_ROOT/frontend/nginx.conf" \
  > "$REPO_ROOT/e2e/federation/nginx-a.conf"
sed 's|http://api:|http://api-b:|g' "$REPO_ROOT/frontend/nginx.conf" \
  > "$REPO_ROOT/e2e/federation/nginx-b.conf"

echo "==> Tearing down any existing federation environment..."
docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true

echo "==> Building and starting federation environment (2 instances)..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "==> Waiting for both instances to be healthy..."
"$(dirname "$0")/wait-for-federation.sh"

echo "==> Federation environment ready"
echo "    Instance A: http://localhost:3911 (API: http://localhost:8911)"
echo "    Instance B: http://localhost:3912 (API: http://localhost:8912)"
