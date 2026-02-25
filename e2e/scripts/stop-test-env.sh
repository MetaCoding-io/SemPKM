#!/usr/bin/env bash
# Stop the E2E test environment and remove volumes.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.test.yml"

echo "==> Stopping test environment and removing volumes..."
docker compose -f "$COMPOSE_FILE" down -v

echo "==> Test environment stopped."
