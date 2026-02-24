#!/usr/bin/env bash
# Wait for the test environment health endpoint to respond.
# Polls http://localhost:3901/api/health with exponential backoff.
set -euo pipefail

BASE_URL="${TEST_BASE_URL:-http://localhost:3901}"
HEALTH_URL="$BASE_URL/api/health"
MAX_ATTEMPTS=20
ATTEMPT=0
WAIT=2

echo "Waiting for $HEALTH_URL to respond..."

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  ATTEMPT=$((ATTEMPT + 1))
  if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    echo "Health check passed after $ATTEMPT attempts."
    exit 0
  fi
  echo "  Attempt $ATTEMPT/$MAX_ATTEMPTS failed, retrying in ${WAIT}s..."
  sleep "$WAIT"
  # Cap wait at 5 seconds
  if [ "$WAIT" -lt 5 ]; then
    WAIT=$((WAIT + 1))
  fi
done

echo "ERROR: Health check failed after $MAX_ATTEMPTS attempts."
echo "Check docker compose logs: docker compose -f docker-compose.test.yml logs"
exit 1
