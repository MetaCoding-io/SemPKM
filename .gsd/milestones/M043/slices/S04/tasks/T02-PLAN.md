---
estimated_steps: 19
estimated_files: 4
skills_used: []
---

# T02: Security audit log table + shared-data model documentation

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

## Inputs

- `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md`

## Expected Output

- `backend/app/auth/models.py`
- `backend/app/auth/audit.py`
- `backend/migrations/versions/xxx_add_security_audit_log.py`
- `docs/security-model.md`

## Verification

cd backend && .venv/bin/python -m pytest tests/ -v -x --timeout=60 && test -f /home/james/Code/SemPKM/docs/security-model.md
