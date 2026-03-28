---
estimated_steps: 6
estimated_files: 2
skills_used: []
---

# T03: Wire model install/uninstall security audit logging

Add security audit logging for model install and uninstall operations in the admin router. The SecurityAuditLog model and log_security_event helper already exist (M043 F-029). The event types `model_installed` and `model_uninstalled` are already defined in AUDIT_EVENT_TYPES. This task wires the calls into the admin router handlers. Write unit tests.

Steps:
1. In `backend/app/admin/router.py`, add `from app.auth.audit import log_security_event` at the top.
2. In `admin_models_install()`, after a successful install (inside the `else` branch where `result.success` is True), add a fire-and-forget call: get the session factory from `request.app.state.async_session_factory`, call `await log_security_event(factory, 'model_installed', source_ip, user_id=user.id, detail={'model_id': result.model_id, 'path': path})`. Use the same `_client_ip` pattern from auth/router.py. Wrap in try/except to ensure audit failure doesn't break model install.
3. In `admin_models_remove()`, after a successful remove (inside the `else` branch), add: `await log_security_event(factory, 'model_uninstalled', source_ip, user_id=user.id, detail={'model_id': model_id})`. Same fire-and-forget pattern.
4. Write `backend/tests/test_model_audit.py` testing: (a) successful model install writes `model_installed` event to SecurityAuditLog, (b) successful model uninstall writes `model_uninstalled` event, (c) audit failure doesn't crash the install/uninstall operation, (d) detail field includes model_id. Use in-memory SQLite and mock the ModelService.

## Inputs

- ``backend/app/admin/router.py` — admin_models_install() and admin_models_remove() handlers to extend`
- ``backend/app/auth/audit.py` — log_security_event() helper to call`
- ``backend/app/auth/models.py` — SecurityAuditLog model and AUDIT_EVENT_TYPES`

## Expected Output

- ``backend/app/admin/router.py` — audit logging wired into install and remove handlers`
- ``backend/tests/test_model_audit.py` — unit tests for model audit logging`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_model_audit.py -v
