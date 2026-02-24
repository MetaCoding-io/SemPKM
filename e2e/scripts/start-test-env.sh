#!/usr/bin/env bash
# Start the E2E test environment with fresh volumes.
# Always tears down first to ensure a clean state.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.test.yml"

echo "==> Tearing down any existing test environment..."
docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true

echo "==> Building and starting test environment..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "==> Waiting for services to be healthy..."
"$(dirname "$0")/wait-for-healthy.sh"

echo "==> Test environment ready at http://localhost:3901"
