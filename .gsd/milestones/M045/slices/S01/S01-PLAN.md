# S01: SSRF Guards, Federation Integrity & Audit Extension

**Goal:** Close SSRF vectors in federation and webhook subsystems, add SHA-256 integrity verification and namespace filtering to federation imports, and extend security audit logging to model install/uninstall events.
**Demo:** After this: Federation sync endpoint rejects loopback/private URLs with 400. Federation export includes SHA-256 hash. Namespace-filtered import rejects system-namespace triples. Model install/uninstall events appear in SecurityAuditLog.

## Tasks
- [x] **T01: Created validate_outbound_url() SSRF guard and wired it into all 4 outbound HTTP code paths (federation sync, inbox POST, profile discovery, webhook dispatch) with 23 passing tests** — Create a shared SSRF validation utility at `backend/app/security/ssrf.py` that resolves hostnames and rejects loopback, private, link-local, and reserved IPs. Restrict schemes to http/https. Apply it to all outbound HTTP code paths: federation sync (`FederationService.sync_shared_graph`), federation outbound notifications (`FederationService._post_to_inbox`, `FederationService._discover_inbox_from_profile`, `FederationService.notify_remote_members_of_change` inbox discovery calls), and webhook dispatch (`WebhookService.dispatch`). Add input validation to the federation sync router endpoint to reject obviously invalid URLs before they reach the service layer. Write comprehensive unit tests proving the guard blocks dangerous URLs and passes safe ones.

Steps:
1. Create `backend/app/security/__init__.py` and `backend/app/security/ssrf.py` with `validate_outbound_url(url: str) -> None` that raises `ValueError` on blocked URLs. Implementation: parse with `urllib.parse.urlparse`, reject non-http(s) schemes, resolve hostname via `socket.getaddrinfo`, check each resolved IP against `ipaddress.ip_address(addr).is_loopback`, `.is_private`, `.is_link_local`, `.is_reserved`, `.is_multicast`. Also reject hostnames like `localhost`, `0.0.0.0`, `[::]`.
2. In `backend/app/federation/service.py`, add `from app.security.ssrf import validate_outbound_url`. Call `validate_outbound_url(remote_instance_url)` at the top of `sync_shared_graph()` before any HTTP request. Call `validate_outbound_url(inbox_url)` in `_post_to_inbox()`. Call `validate_outbound_url(profile_url)` in `_discover_inbox_from_profile()`.
3. In `backend/app/federation/router.py`, add URL validation in `sync_shared_graph()` router handler — catch ValueError from the service and return HTTP 400.
4. In `backend/app/services/webhooks.py`, add `from app.security.ssrf import validate_outbound_url`. Call `validate_outbound_url(config.target_url)` at the top of `dispatch()` before the httpx POST. Log blocked URLs at WARNING.
5. Write `backend/tests/test_ssrf_guard.py` with tests: blocks `http://127.0.0.1`, `http://localhost`, `http://[::1]`, `http://10.0.0.1`, `http://172.16.0.1`, `http://192.168.1.1`, `http://169.254.169.254` (AWS metadata), `ftp://example.com` (wrong scheme), `http://0.0.0.0`; passes `https://example.com`, `https://federation.example.org:8443/api`. Test that ValueError message includes the reason.
  - Estimate: 1h
  - Files: backend/app/security/__init__.py, backend/app/security/ssrf.py, backend/app/federation/service.py, backend/app/federation/router.py, backend/app/services/webhooks.py, backend/tests/test_ssrf_guard.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_ssrf_guard.py -v
- [x] **T02: Added SHA-256 integrity hash to federation exports and namespace-filtered import with 17 passing tests** — Add content integrity verification (SHA-256 hash) to federation patch exports and imports per D372 backward-compat strategy. Add namespace filtering to reject system-managed predicates in incoming federation triples per F-037. Write unit tests.

Steps:
1. In `backend/app/federation/schemas.py`, add optional `content_hash: str | None = None` field to `PatchExportResponse`.
2. In `backend/app/federation/router.py` `export_patches()`, compute SHA-256 of `patch_text` and include it as `content_hash` in the response.
3. In `backend/app/federation/service.py` `sync_shared_graph()`, after receiving the remote response, check for `content_hash` field. If present, compute SHA-256 of received `patch_text` and compare. If mismatch, add error to SyncResult and return without applying. If absent, log WARNING about missing integrity verification.
4. Create `backend/app/federation/namespace_filter.py` with `filter_federation_triples(triples: list[tuple]) -> tuple[list[tuple], list[tuple]]` that splits triples into (allowed, rejected). Reject triples where any of s/p/o starts with system namespaces: `urn:sempkm:` (except `urn:sempkm:shared:` which is the federation graph itself), any predicate in `http://www.w3.org/2002/07/owl#`, `http://www.w3.org/ns/shacl#`, `http://www.w3.org/1999/02/22-rdf-syntax-ns#type` when the object is an OWL/SHACL class.
5. In `backend/app/federation/service.py` `sync_shared_graph()`, after deserializing the patch and before building Operations, call `filter_federation_triples()` on the inserts list. Log the count of rejected triples at WARNING if any. Use only the allowed triples for the Operation.
6. Write `backend/tests/test_federation_integrity.py` with tests: (a) export includes content_hash, (b) import with correct hash passes, (c) import with wrong hash fails, (d) import with missing hash logs warning but proceeds, (e) namespace filter rejects sempkm: predicates, (f) namespace filter rejects owl:Class triples, (g) namespace filter rejects sh: predicates, (h) namespace filter allows normal data triples, (i) namespace filter allows urn:sempkm:shared: graph IRIs in subjects.
  - Estimate: 1h
  - Files: backend/app/federation/schemas.py, backend/app/federation/router.py, backend/app/federation/service.py, backend/app/federation/namespace_filter.py, backend/tests/test_federation_integrity.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_federation_integrity.py -v
- [ ] **T03: Wire model install/uninstall security audit logging** — Add security audit logging for model install and uninstall operations in the admin router. The SecurityAuditLog model and log_security_event helper already exist (M043 F-029). The event types `model_installed` and `model_uninstalled` are already defined in AUDIT_EVENT_TYPES. This task wires the calls into the admin router handlers. Write unit tests.

Steps:
1. In `backend/app/admin/router.py`, add `from app.auth.audit import log_security_event` at the top.
2. In `admin_models_install()`, after a successful install (inside the `else` branch where `result.success` is True), add a fire-and-forget call: get the session factory from `request.app.state.async_session_factory`, call `await log_security_event(factory, 'model_installed', source_ip, user_id=user.id, detail={'model_id': result.model_id, 'path': path})`. Use the same `_client_ip` pattern from auth/router.py. Wrap in try/except to ensure audit failure doesn't break model install.
3. In `admin_models_remove()`, after a successful remove (inside the `else` branch), add: `await log_security_event(factory, 'model_uninstalled', source_ip, user_id=user.id, detail={'model_id': model_id})`. Same fire-and-forget pattern.
4. Write `backend/tests/test_model_audit.py` testing: (a) successful model install writes `model_installed` event to SecurityAuditLog, (b) successful model uninstall writes `model_uninstalled` event, (c) audit failure doesn't crash the install/uninstall operation, (d) detail field includes model_id. Use in-memory SQLite and mock the ModelService.
  - Estimate: 45m
  - Files: backend/app/admin/router.py, backend/tests/test_model_audit.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_model_audit.py -v
