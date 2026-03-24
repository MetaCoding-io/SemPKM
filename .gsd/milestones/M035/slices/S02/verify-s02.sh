#!/usr/bin/env bash
# S02 Slice Verification — Graph Context Injection & Conversation Persistence
# Checks: file existence, import chains, endpoint registration, migration validity,
#          schema fields, system prompt wiring, frontend wiring.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
cd "$PROJECT_ROOT"

PASS=0
FAIL=0
TOTAL=0

check() {
  local desc="$1"
  shift
  TOTAL=$((TOTAL + 1))
  if "$@" > /dev/null 2>&1; then
    echo "  PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc"
    FAIL=$((FAIL + 1))
  fi
}

check_sub() {
  # Run command in a subshell so cd doesn't affect parent
  local desc="$1"
  local cmd="$2"
  TOTAL=$((TOTAL + 1))
  if (eval "$cmd") > /dev/null 2>&1; then
    echo "  PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== S02 Slice Verification ==="
echo ""

# --- File existence ---
echo "-- File existence --"
check "context.py exists" test -f backend/app/copilot/context.py
check "models.py exists" test -f backend/app/copilot/models.py
check "conversation.py exists" test -f backend/app/copilot/conversation.py
check "migration 016 exists" test -f backend/migrations/versions/016_copilot_conversations.py
check "test_graph_context.py exists" test -f backend/tests/test_graph_context.py
check "test_conversation_service.py exists" test -f backend/tests/test_conversation_service.py
check "verify-s02.sh exists (self)" test -f .gsd/milestones/M035/slices/S02/verify-s02.sh

echo ""

# --- Import chains ---
echo "-- Import chains --"
check_sub "GraphContextService importable" \
  "cd backend && .venv/bin/python -c 'from app.copilot.context import GraphContextService; print(\"OK\")'"
check_sub "CopilotConversation importable" \
  "cd backend && .venv/bin/python -c 'from app.copilot.models import CopilotConversation, CopilotMessage; print(\"OK\")'"
check_sub "ConversationService importable" \
  "cd backend && .venv/bin/python -c 'from app.copilot.conversation import ConversationService; print(\"OK\")'"

echo ""

# --- Endpoint registration ---
echo "-- Endpoint registration --"
check "GET /conversations route" grep -q '/conversations' backend/app/api/copilot.py
check "POST /conversations route" grep -q 'async def create_conversation' backend/app/api/copilot.py
check "DELETE /conversations/{id} route" grep -q 'async def delete_conversation' backend/app/api/copilot.py

echo ""

# --- Migration validity ---
echo "-- Migration validity --"
check "Migration has copilot_conversations table" grep -q 'copilot_conversations' backend/migrations/versions/016_copilot_conversations.py
check "Migration has copilot_messages table" grep -q 'copilot_messages' backend/migrations/versions/016_copilot_conversations.py
check_sub "Migration is valid Python" \
  "cd backend && .venv/bin/python -c \"import ast; ast.parse(open('migrations/versions/016_copilot_conversations.py').read()); print('OK')\""

echo ""

# --- Schema and service wiring ---
echo "-- Schema and service wiring --"
check "active_object_iri in schemas.py" grep -q 'active_object_iri' backend/app/copilot/schemas.py
check "graph_context in service.py" grep -q 'graph_context' backend/app/copilot/service.py

echo ""

# --- Frontend wiring ---
echo "-- Frontend wiring --"
check "_activeObjectIri in copilot.js" grep -q '_activeObjectIri' frontend/static/js/copilot.js
check "_currentConversationId in copilot.js" grep -q '_currentConversationId' frontend/static/js/copilot.js
check "conversation_created event in copilot.js" grep -q 'conversation_created' frontend/static/js/copilot.js
check "sempkm:tab-activated in copilot.js" grep -q 'sempkm:tab-activated' frontend/static/js/copilot.js

echo ""
echo "=== Results: $PASS/$TOTAL passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
