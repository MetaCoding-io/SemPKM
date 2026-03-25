---
estimated_steps: 16
estimated_files: 9
skills_used: []
---

# T01: Rate limits, query timeout, error disclosure fix, auth failure logging

1. Add @limiter.limit decorators to endpoints:
   - POST /api/sparql: '60/minute'
   - POST /api/copilot/chat: '20/minute'
   - POST /api/auth/tokens: '5/minute'
   - POST /api/commands: '20/minute'

2. Add SPARQL query timeout:
   - In backend/app/triplestore/client.py, set httpx timeout to 30s on query() and update() methods
   - Handle httpx.TimeoutException → return 504 Gateway Timeout with message 'Query timed out after 30 seconds'

3. Add global exception handler in backend/app/main.py:
   - Catch unhandled Exception, log full traceback, return 500 with generic {"detail": "Internal server error"}
   - Replace detail=str(e) patterns in auth/router.py, workflow/router.py, dashboard/router.py, task_templates/router.py with generic messages

4. Add failed auth attempt logging:
   - In verify endpoint: log WARNING with source IP on invalid token
   - In API token auth: log WARNING with token prefix on invalid token
   - In rate limit triggers: log WARNING with source IP

Unit tests: verify 429 response after exceeding rate limit, verify timeout returns 504, verify generic error message instead of stack trace.

## Inputs

- `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md`

## Expected Output

- `backend/app/sparql/router.py`
- `backend/app/copilot/router.py`
- `backend/app/auth/router.py`
- `backend/app/api/router.py`
- `backend/app/triplestore/client.py`
- `backend/app/main.py`

## Verification

cd backend && .venv/bin/python -m pytest tests/ -v -x --timeout=60
