# S04: Rate Limits, Warnings & Documentation

**Goal:** Add rate limits to 4 endpoint groups (F-017), add SPARQL query timeout (F-011), document shared-data model (F-002), add error disclosure protection (F-025), add security event logging foundation (F-029/F-030).
**Demo:** SPARQL endpoint returns 429 after 60 requests/minute. Startup log shows warning when demo_mode=true with non-localhost URL. ARCHITECTURE.md documents shared-data model.

## Must-Haves

- @limiter.limit decorators: SPARQL 60/min, copilot 20/min, token creation 5/min, batch commands 20/min\n- Triplestore query timeout of 30s via httpx timeout parameter\n- Global exception handler returns generic error messages, logs full exception\n- Failed auth attempts logged at WARNING with source IP\n- SecurityAuditLog SQL table created with login/token/role-change event types\n- Shared-data model documented in architecture docs\n- All tests pass

## Proof Level

- This slice proves: Unit tests for rate limit responses + startup warning log verification + documentation review

## Integration Closure

Rate limits use existing slowapi infrastructure. No new dependencies. Documentation is write-only.

## Verification

- 429 responses include Retry-After header. Failed auth attempts logged at WARNING. Startup warnings visible in container logs. Security audit log table created.

## Tasks

- [ ] **T01: Rate limits, query timeout, error disclosure fix, auth failure logging** `est:3h`
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
  - Files: `backend/app/sparql/router.py`, `backend/app/copilot/router.py`, `backend/app/auth/router.py`, `backend/app/api/router.py`, `backend/app/triplestore/client.py`, `backend/app/main.py`, `backend/app/workflow/router.py`, `backend/app/dashboard/router.py`, `backend/app/task_templates/router.py`
  - Verify: cd backend && .venv/bin/python -m pytest tests/ -v -x --timeout=60

- [ ] **T02: Security audit log table + shared-data model documentation** `est:3h`
  1. Create SecurityAuditLog model in backend/app/auth/models.py:
   - id: int (auto)
   - event_type: str (login_success, login_failed, token_created, token_revoked, session_revoked_all, role_changed, model_installed, model_uninstalled)
   - user_id: UUID (nullable — failed logins don't have a user)
   - source_ip: str
   - detail: str (JSON blob with event-specific data)
   - created_at: datetime

2. Create audit logging helper: log_security_event(db, event_type, user_id, source_ip, detail) in backend/app/auth/audit.py

3. Wire audit logging into key security operations:
   - Successful login (verify endpoint)
   - Failed login attempts
   - API token creation/revocation
   - Session revoke-all
   - Role changes (if any endpoint exists)

4. Create Alembic migration for security_audit_log table.

5. Document the shared-data model:
   - Add a 'Security Model' section to docs explaining: all authenticated users share the same triplestore data, SQL-backed resources (canvas, dashboards, workflows, queries, tokens) are user-scoped, federation provides cross-instance sharing
   - Update ARCHITECTURE.md or create docs/security-model.md

Note: No admin UI for viewing audit logs in this milestone — just the table and logging. Admin UI is a future milestone.
  - Files: `backend/app/auth/models.py`, `backend/app/auth/audit.py`, `backend/app/auth/router.py`, `backend/app/services/models.py`
  - Verify: cd backend && .venv/bin/python -m pytest tests/ -v -x --timeout=60 && test -f /home/james/Code/SemPKM/docs/security-model.md

## Files Likely Touched

- backend/app/sparql/router.py
- backend/app/copilot/router.py
- backend/app/auth/router.py
- backend/app/api/router.py
- backend/app/triplestore/client.py
- backend/app/main.py
- backend/app/workflow/router.py
- backend/app/dashboard/router.py
- backend/app/task_templates/router.py
- backend/app/auth/models.py
- backend/app/auth/audit.py
- backend/app/services/models.py
