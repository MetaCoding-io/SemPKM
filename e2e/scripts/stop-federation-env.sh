#!/usr/bin/env bash
# Stop the federation test environment and remove all volumes.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.federation-test.yml"

echo "==> Stopping federation environment and removing volumes..."
docker compose -f "$COMPOSE_FILE" down -v

echo "==> Federation environment stopped."
