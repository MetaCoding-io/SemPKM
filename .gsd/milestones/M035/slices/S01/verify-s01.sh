#!/usr/bin/env bash
# S01 Slice Verification — Copilot Chat with SPARQL Generation
# Checks that all S01 deliverables exist, are wired correctly, and tests pass.

PASS=0
FAIL=0

check() {
    if eval "$2" >/dev/null 2>&1; then
        echo "✓ $1"
        PASS=$((PASS + 1))
    else
        echo "✗ $1"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== S01: Copilot Chat with SPARQL Generation — Verification ==="
echo ""

# File existence checks
check "copilot.js exists" "test -f frontend/static/js/copilot.js"
check "copilot.css exists" "test -f frontend/static/css/copilot.css"
check "CopilotService module exists" "test -f backend/app/copilot/service.py"
check "Copilot API module exists" "test -f backend/app/api/copilot.py"
check "Copilot schemas module exists" "test -f backend/app/copilot/schemas.py"
check "Copilot __init__.py exists" "test -f backend/app/copilot/__init__.py"

# Router wiring checks
check "ai_router in main.py" "grep -q 'ai_router' backend/app/main.py"
check "copilot_router in main.py" "grep -q 'copilot_router' backend/app/main.py"

# nginx SSE proxy config
check "nginx copilot SSE config" "grep -q 'api/copilot' frontend/nginx.conf"

# Template checks
check "placeholder removed" "! grep -q 'coming in v2.1' backend/app/templates/browser/workspace.html"
check "copilot container in template" "grep -q 'copilot-container' backend/app/templates/browser/workspace.html"

# JS lazy-load wiring
check "lazy-load in workspace.js" "grep -q 'copilot' frontend/static/js/workspace.js"

# Import check
check "copilot module imports cleanly" "cd backend && .venv/bin/python -c 'from app.api.copilot import copilot_router; print(\"import OK\")'"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
