---
id: S04
parent: M043
milestone: M043
provides:
  - Rate limiting infrastructure on 6 endpoints
  - SecurityAuditLog table and log_security_event() helper
  - Global error disclosure protection
  - Security model documentation at docs/security-model.md
requires:
  - slice: S02
    provides: CORS consolidation to FastAPI — rate limit headers no longer duplicated by nginx
affects:
  - S05
key_files:
  - backend/app/auth/audit.py
  - backend/app/auth/models.py
  - backend/app/auth/rate_limit.py
  - backend/app/main.py
  - backend/app/sparql/router.py
  - backend/app/commands/router.py
  - backend/app/auth/router.py
  - backend/app/api/copilot.py
  - backend/migrations/versions/024_add_security_audit_log.py
  - docs/security-model.md
  - backend/tests/test_security_hardening.py
key_decisions:
  - Keep slowapi headers_enabled=False and set Retry-After explicitly in custom handler — avoids crash on Pydantic-model-returning endpoints
  - SecurityAuditLog uses integer auto-increment PK (not UUID) — append-only audit log benefits from sequential IDs for time-range queries
  - Audit helper catches all exceptions internally — audit logging must never fail the parent operation
  - Global exception handler returns generic 500 with full traceback logged — eliminates error disclosure (F-025)
patterns_established:
  - Rate limit pattern: @limiter.limit decorator + custom handler with WARNING logging and explicit Retry-After
  - Audit logging pattern: log_security_event() with internal exception handling — call-site never needs try/catch
  - Error disclosure protection: global exception handler + generic messages replace detail=str(e)
observability_surfaces:
  - WARNING logs on rate limit exceeded (source IP + path)
  - WARNING logs on failed auth attempts (source IP + token prefix)
  - SecurityAuditLog table captures login, token, and session events with source IP and detail JSON
  - ERROR logs with full traceback for unhandled exceptions (generic message to client)
drill_down_paths:
  - .gsd/milestones/M043/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M043/slices/S04/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-25T15:31:21.681Z
blocker_discovered: false
---

# S04: Rate Limits, Warnings & Documentation

**Added rate limits to 6 endpoint groups, SPARQL query timeout, global error disclosure protection, failed auth attempt logging, SecurityAuditLog table with wiring into 6 auth operations, and comprehensive security model documentation.**

## What Happened

T01 added rate limiting, query timeout, error disclosure fixes, and auth failure logging. Rate limits were applied via `@limiter.limit` decorators to SPARQL (60/min), copilot (20/min), token creation (5/min), commands (20/min), magic-link (5/min), and verify (10/min) endpoints — using the existing slowapi infrastructure. A custom rate limit handler replaces the default to log WARNING-level events with source IP and set explicit Retry-After headers, since slowapi's built-in header injection crashes on Pydantic-model-returning endpoints.

The SPARQL query timeout was already configured at 30s on the httpx client. T01 added httpx.TimeoutException catch blocks in both GET/POST SPARQL endpoints, returning 504 with a clear timeout message.

Error disclosure was addressed by adding a global `@app.exception_handler(Exception)` that returns generic 500 responses while logging full tracebacks, and by replacing all 6 `detail=str(e)` patterns across auth, workflow, dashboard, and task_templates routers with generic messages.

Failed auth attempt logging was wired into the verify endpoint (invalid/expired tokens, replay attempts), Bearer token authentication (invalid tokens with prefix logged), and rate limit exceeded events.

T02 created the SecurityAuditLog SQL model (id, event_type, user_id, source_ip, detail JSON, created_at) with Alembic migration 024 and three indexes. The `log_security_event()` async helper manages its own DB session and catches all exceptions internally — audit logging never fails the parent operation. Six auth operations were wired: login_success, login_failed (invalid token + replay), session_revoked_all, token_created, token_revoked.

T02 also produced `docs/security-model.md` (123 lines) documenting the shared-data authorization model, role hierarchy, authentication flows, API token scopes, audit trail event types, rate limits by endpoint, SPARQL security defenses, federation model, secret management, and app platform trust boundaries.

## Verification

56 security-related tests pass (test_security_hardening, test_auth_tokens, test_commands_bearer_auth, test_token_scopes). Zero `detail=str(e)` patterns remain in the codebase. SecurityAuditLog model, migration, and audit helper all verified. docs/security-model.md exists with 123 lines of comprehensive documentation. Rate limit decorators confirmed on all 6 endpoint groups.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Rate limits were applied to 6 endpoints instead of the planned 4 — magic-link (5/min) and verify (10/min) were added for additional security. slowapi headers_enabled kept False due to Pydantic model response incompatibility — Retry-After set explicitly in custom handler instead.

## Known Limitations

No admin UI for viewing audit logs — table and logging only. Admin UI is a future milestone. The _audit() wrapper silently degrades in test environments that don't set async_session_factory on app.state.

## Follow-ups

Admin UI for browsing SecurityAuditLog entries. Audit log retention/rotation policy. Consider moving rate limit configuration to Settings for runtime adjustment.

## Files Created/Modified

- `backend/app/sparql/router.py` — Added @limiter.limit('60/minute') and httpx.TimeoutException catch for 504 response
- `backend/app/api/copilot.py` — Added @limiter.limit('20/minute') to POST /api/copilot/chat
- `backend/app/auth/router.py` — Added rate limits (5/min magic-link, 10/min verify, 5/min token creation), auth failure WARNING logs, audit logging for 6 operations, generic error messages replacing detail=str(e)
- `backend/app/auth/dependencies.py` — Added WARNING log with source IP and token prefix on invalid Bearer tokens
- `backend/app/auth/rate_limit.py` — Added custom _rate_limit_exceeded_handler_with_logging with WARNING log and Retry-After header
- `backend/app/commands/router.py` — Added @limiter.limit('20/minute') to POST /api/commands
- `backend/app/main.py` — Added global @app.exception_handler(Exception) returning generic 500
- `backend/app/triplestore/client.py` — Timeout already configured — no changes needed
- `backend/app/workflow/router.py` — Replaced detail=str(e) with generic error message
- `backend/app/dashboard/router.py` — Replaced detail=str(e) with generic error message
- `backend/app/task_templates/router.py` — Replaced detail=str(e) with generic error message
- `backend/app/context/router.py` — Added @limiter.limit('12/minute') to context update endpoint
- `backend/app/auth/models.py` — Added SecurityAuditLog model with 6 columns and AUDIT_EVENT_TYPES constant
- `backend/app/auth/audit.py` — Created log_security_event() async helper with internal exception handling
- `backend/migrations/versions/024_add_security_audit_log.py` — Alembic migration creating security_audit_log table with 3 indexes
- `docs/security-model.md` — New 123-line document covering shared-data model, roles, auth, scopes, audit, rate limits, SPARQL security, federation
- `backend/tests/test_security_hardening.py` — 5 new tests: rate limit 429, timeout 504, generic error message, auth failure logging, rate limit logging
- `backend/tests/test_commands_bearer_auth.py` — Updated for rate limit decorator compatibility
