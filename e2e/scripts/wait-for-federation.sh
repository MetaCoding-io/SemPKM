#!/usr/bin/env bash
# Wait for both federation test instances to become healthy.
# Polls /api/health on both instances with linear backoff (capped at 5s).
set -euo pipefail

INSTANCE_A_URL="${FED_INSTANCE_A_URL:-http://localhost:3911}"
INSTANCE_B_URL="${FED_INSTANCE_B_URL:-http://localhost:3912}"

HEALTH_A="$INSTANCE_A_URL/api/health"
HEALTH_B="$INSTANCE_B_URL/api/health"

MAX_ATTEMPTS=20
ATTEMPT=0
WAIT=2

A_HEALTHY=false
B_HEALTHY=false

echo "Waiting for federation instances to become healthy..."
echo "  Instance A: $HEALTH_A"
echo "  Instance B: $HEALTH_B"

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  ATTEMPT=$((ATTEMPT + 1))

  if [ "$A_HEALTHY" = false ] && curl -sf "$HEALTH_A" > /dev/null 2>&1; then
    A_HEALTHY=true
    echo "  ✓ Instance A healthy (attempt $ATTEMPT)"
  fi

  if [ "$B_HEALTHY" = false ] && curl -sf "$HEALTH_B" > /dev/null 2>&1; then
    B_HEALTHY=true
    echo "  ✓ Instance B healthy (attempt $ATTEMPT)"
  fi

  if [ "$A_HEALTHY" = true ] && [ "$B_HEALTHY" = true ]; then
    echo "Both federation instances healthy after $ATTEMPT attempts."
    exit 0
  fi

  echo "  Attempt $ATTEMPT/$MAX_ATTEMPTS — waiting ${WAIT}s..."
  sleep "$WAIT"
  # Cap wait at 5 seconds
  if [ "$WAIT" -lt 5 ]; then
    WAIT=$((WAIT + 1))
  fi
done

echo "ERROR: Federation health check failed after $MAX_ATTEMPTS attempts."
[ "$A_HEALTHY" = false ] && echo "  ✗ Instance A ($HEALTH_A) never became healthy"
[ "$B_HEALTHY" = false ] && echo "  ✗ Instance B ($HEALTH_B) never became healthy"
echo "Check logs: docker compose -f docker-compose.federation-test.yml logs api-a api-b"
exit 1
