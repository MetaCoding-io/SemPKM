#!/usr/bin/env bash
# verify-s03.sh — Structural verification for S03: AI Personas & Object Creation from Chat
# Checks file existence, imports, string presence, and test suite health.

PASS=0
FAIL=0
TOTAL=0

# Get the project root (where this script lives relative to)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Walk up from .gsd/milestones/M035/slices/S03/ to project root
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

check() {
    local desc="$1"
    shift
    TOTAL=$((TOTAL + 1))
    if "$@" > /dev/null 2>&1; then
        echo "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $desc"
        FAIL=$((FAIL + 1))
    fi
}

check_grep() {
    local desc="$1"
    local pattern="$2"
    local file="$3"
    TOTAL=$((TOTAL + 1))
    if grep -q "$pattern" "$PROJECT_ROOT/$file" 2>/dev/null; then
        echo "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $desc"
        FAIL=$((FAIL + 1))
    fi
}

check_pytest() {
    local desc="$1"
    shift
    TOTAL=$((TOTAL + 1))
    if (cd "$PROJECT_ROOT/backend" && .venv/bin/python -m pytest "$@" -q --tb=no) > /dev/null 2>&1; then
        echo "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $desc"
        FAIL=$((FAIL + 1))
    fi
}

check_import() {
    local desc="$1"
    local stmt="$2"
    TOTAL=$((TOTAL + 1))
    if (cd "$PROJECT_ROOT/backend" && .venv/bin/python -c "$stmt") > /dev/null 2>&1; then
        echo "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $desc"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== S03 Structural Verification ==="
echo ""

# --- File existence ---
echo "## File Existence"
check "backend/app/copilot/personas.py exists" test -f "$PROJECT_ROOT/backend/app/copilot/personas.py"
check "backend/migrations/versions/017_ai_personas.py exists" test -f "$PROJECT_ROOT/backend/migrations/versions/017_ai_personas.py"
check "backend/tests/test_ai_personas.py exists" test -f "$PROJECT_ROOT/backend/tests/test_ai_personas.py"
check "backend/tests/test_object_creation_chat.py exists" test -f "$PROJECT_ROOT/backend/tests/test_object_creation_chat.py"
echo ""

# --- Import checks ---
echo "## Import Checks"
check_import "AIPersonaService importable" "from app.copilot.personas import AIPersonaService"
check_import "AIPersona model importable" "from app.copilot.models import AIPersona"
echo ""

# --- String presence checks ---
echo "## String Presence"
check_grep "persona_id in schemas.py" "persona_id" "backend/app/copilot/schemas.py"
check_grep "persona_prompt in service.py" "persona_prompt" "backend/app/copilot/service.py"
check_grep "create_object in copilot.py (API)" "create_object" "backend/app/api/copilot.py"
check_grep "create_object in copilot.js (frontend)" "create_object" "frontend/static/js/copilot.js"
check_grep "copilot-persona in copilot.css" "copilot-persona" "frontend/static/css/copilot.css"
check_grep "copilot-create in copilot.css" "copilot-create" "frontend/static/css/copilot.css"
check_grep "persona endpoints in copilot.py" "/personas" "backend/app/api/copilot.py"
echo ""

# --- Test suites ---
echo "## Test Suites"
check_pytest "test_ai_personas.py passes" tests/test_ai_personas.py
check_pytest "test_object_creation_chat.py passes" tests/test_object_creation_chat.py
check_pytest "test_copilot_service.py passes (S01 regression)" tests/test_copilot_service.py
check_pytest "test_conversation_service.py passes (S02 regression)" tests/test_conversation_service.py
echo ""

# --- Summary ---
echo "=== Results: $PASS/$TOTAL passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
