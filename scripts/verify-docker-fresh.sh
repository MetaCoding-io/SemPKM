#!/usr/bin/env bash
# Verify fresh-volume Docker deploy and business-planning model install.
#
# Usage: ./scripts/verify-docker-fresh.sh
#
# This script:
#   1. Tears down existing containers and volumes
#   2. Rebuilds and starts the stack
#   3. Waits for all services to be healthy
#   4. Creates an owner account and obtains a session cookie
#   5. Installs the business-planning model
#   6. Verifies 33 NodeShapes are loaded in the triplestore
#
# Prerequisites: Docker Compose, curl, jq (optional, for pretty output)

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

COOKIE_JAR=$(mktemp)
trap 'rm -f "$COOKIE_JAR"' EXIT

echo "=== Step 1: Tear down existing stack and volumes ==="
docker compose down -v 2>&1 | tail -5

echo ""
echo "=== Step 2: Build and start fresh ==="
docker compose up --build -d 2>&1 | tail -10

echo ""
echo "=== Step 3: Wait for services to be healthy ==="
MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    API_STATUS=$(docker compose ps --format json api 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health',''))" 2>/dev/null || echo "")
    if [ "$API_STATUS" = "healthy" ]; then
        echo "API is healthy after ${ELAPSED}s"
        break
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo "  Waiting... (${ELAPSED}s)"
done

if [ "$API_STATUS" != "healthy" ]; then
    echo "ERROR: API did not become healthy within ${MAX_WAIT}s"
    docker compose logs api | tail -30
    exit 1
fi

docker compose ps
echo ""

echo "=== Step 4: Verify entrypoint created data directories ==="
docker compose exec -T api ls -d /app/data/apps /app/data/imports
echo "Directories exist ✓"
echo ""

echo "=== Step 5: Create owner account ==="
SETUP_TOKEN=$(docker compose exec -T api cat /app/data/.setup-token)
curl -sf -X POST http://localhost:8001/api/auth/setup \
    -H "Content-Type: application/json" \
    -d "{\"token\": \"$SETUP_TOKEN\", \"email\": \"admin@example.com\", \"display_name\": \"Admin\"}" \
    > /dev/null
echo "Owner account created ✓"

echo ""
echo "=== Step 6: Obtain session cookie ==="
MAGIC_TOKEN=$(curl -sf -X POST http://localhost:8001/api/auth/magic-link \
    -H "Content-Type: application/json" \
    -d '{"email": "admin@example.com"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -sf -c "$COOKIE_JAR" -X POST http://localhost:8001/api/auth/verify \
    -H "Content-Type: application/json" \
    -d "{\"token\": \"$MAGIC_TOKEN\"}" > /dev/null
echo "Session obtained ✓"

echo ""
echo "=== Step 7: Install business-planning model ==="
INSTALL_RESULT=$(curl -sf -b "$COOKIE_JAR" -X POST http://localhost:8001/api/models/install \
    -H "Content-Type: application/json" \
    -d '{"path": "/app/models/business-planning"}')
echo "$INSTALL_RESULT"
echo "Model installed ✓"

echo ""
echo "=== Step 8: Verify 33 NodeShapes loaded ==="
# Query the triplestore directly (the /api/sparql endpoint scopes to
# urn:sempkm:current, so model graphs are not visible through it)
SHAPE_COUNT=$(docker compose exec -T api curl -sf -X POST \
    http://triplestore:8080/rdf4j-server/repositories/sempkm \
    -H 'Content-Type: application/sparql-query' \
    -H 'Accept: application/sparql-results+json' \
    -d 'SELECT (COUNT(?s) AS ?count) WHERE { GRAPH <urn:sempkm:model:business-planning:shapes> { ?s a <http://www.w3.org/ns/shacl#NodeShape> } }' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['results']['bindings'][0]['count']['value'])")

echo "NodeShape count: $SHAPE_COUNT"
if [ "$SHAPE_COUNT" = "33" ]; then
    echo "✅ PASS: All 33 NodeShapes loaded"
else
    echo "❌ FAIL: Expected 33 NodeShapes, got $SHAPE_COUNT"
    exit 1
fi

echo ""
echo "=== All checks passed ==="
