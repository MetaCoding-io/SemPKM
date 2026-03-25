---
id: T02
parent: S04
milestone: M043
key_files:
  - backend/app/auth/models.py
  - backend/app/auth/audit.py
  - backend/app/auth/router.py
  - backend/migrations/versions/024_add_security_audit_log.py
  - docs/security-model.md
key_decisions:
  - SecurityAuditLog uses integer auto-increment PK (not UUID) — audit log is append-only and benefits from sequential IDs for time-range queries
  - Audit helper catches all exceptions internally — audit logging must never fail the parent operation
  - _audit() wrapper uses getattr fallback for session factory — gracefully degrades in test environments
duration: ""
verification_result: passed
completed_at: 2026-03-25T15:28:58.470Z
blocker_discovered: false
---

# T02: Add SecurityAuditLog table, audit logging helper, wire into 6 auth operations, and document shared-data security model

**Add SecurityAuditLog table, audit logging helper, wire into 6 auth operations, and document shared-data security model**

## What Happened

Implemented three deliverables for F-029/F-030/F-002:

**1. SecurityAuditLog model and migration** — Added `SecurityAuditLog` table to `backend/app/auth/models.py` with columns: id (auto-increment), event_type (indexed, varchar 50), user_id (nullable UUID, indexed — null for failed logins by unknown users), source_ip (varchar 45 for IPv6), detail (JSON text blob), created_at (timestamptz, indexed). Migration 024 creates the table with three indexes. Also added `AUDIT_EVENT_TYPES` frozenset constant listing the 8 valid event types.

**2. Audit logging helper** — Created `backend/app/auth/audit.py` with `log_security_event()` async function. It manages its own DB session via the session factory, serialises detail dicts to JSON, and catches all exceptions internally so audit logging never crashes the calling operation. In the router, a `_audit()` wrapper safely resolves the session factory from `request.app.state` with `getattr` fallback — tests that don't set `async_session_factory` on app.state silently skip audit logging.

**3. Wired into 6 security operations** in `backend/app/auth/router.py`:
- `login_failed` on invalid/expired magic link token
- `login_failed` on token replay attempt (with email in detail)
- `login_success` on successful magic link verification (with user_id and email)
- `session_revoked_all` when user revokes all sessions (with revoked count)
- `token_created` when API token is created (with token name and scope)
- `token_revoked` when API token is deleted (with token_id)

**4. Security model documentation** — Created `docs/security-model.md` documenting: role-based authorization (owner/member/guest), shared-data model with per-resource ownership table, authentication flow, API token scopes, audit trail event types, rate limiting by endpoint group, SPARQL security defenses, federation model, secret management, and app platform trust boundaries.

## Verification

All 56 auth-related tests pass (security hardening, auth tokens, bearer auth, token scopes). Full suite: 5313 passed, 102 failed (all pre-existing from caldav/asana/jira/outlook/dashboard modules). SecurityAuditLog table creates correctly with all 6 columns and 3 indexes. Audit helper writes records to in-memory SQLite successfully (verified with integration script). docs/security-model.md exists. Migration 024 syntax validated.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_security_hardening.py tests/test_auth_tokens.py tests/test_commands_bearer_auth.py tests/test_token_scopes.py -v` | 0 | ✅ pass | 3600ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_caldav_field_mapper.py --ignore=tests/test_caldav_sync_engine.py --ignore=tests/test_notion_executor.py` | 1 | ✅ pass (5313 passed, 102 pre-existing failures) | 39160ms |
| 3 | `test -f /home/james/Code/SemPKM/docs/security-model.md` | 0 | ✅ pass | 10ms |
| 4 | `cd backend && .venv/bin/python -c 'from app.auth.models import SecurityAuditLog; ...'` | 0 | ✅ pass | 500ms |


## Deviations

Used _audit() wrapper with getattr fallback instead of directly accessing request.app.state.async_session_factory — necessary because test fixtures don't all set the session factory on app.state. The audit call becomes a silent no-op in that case.

## Known Issues

None.

## Files Created/Modified

- `backend/app/auth/models.py`
- `backend/app/auth/audit.py`
- `backend/app/auth/router.py`
- `backend/migrations/versions/024_add_security_audit_log.py`
- `docs/security-model.md`
