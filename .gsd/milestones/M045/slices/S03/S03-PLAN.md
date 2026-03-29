# S03: Regression Verification & Documentation

**Goal:** Verify all M043+M044+M045 security fixes hold under regression testing, and document the complete 44-finding audit disposition plus all new security features in security-model.md.
**Demo:** After this: E2E test suite passes against hardened stack. security-model.md documents all 44 finding dispositions. Dependency scanning documented.

## Tasks
- [x] **T01: All 218 security tests pass (78 M045 + 140 M043) and Docker/Caddyfile hardening verified across all compose files** — Run all 11 security-related test files (218 tests total) and verify Docker hardening via static file checks. Fix any test failures in M045-modified files. This proves all M043+M044+M045 security fixes hold.

## Steps

1. Run M045-specific tests: `cd backend && .venv/bin/python -m pytest tests/test_ssrf_guard.py tests/test_federation_integrity.py tests/test_model_audit.py tests/test_zip_validator.py tests/test_app_token_isolation.py -v` — expect 78 passes.
2. Run M043-specific tests: `cd backend && .venv/bin/python -m pytest tests/test_sparql_injection_regression.py tests/test_sparql_builder.py tests/test_magic_link_hardening.py tests/test_token_scopes.py tests/test_session_management.py tests/test_security_hardening.py -v` — expect 140 passes.
3. If any tests fail in M045-modified files, diagnose and fix. If failures are in unrelated pre-existing code, document as known issues.
4. Verify Docker hardening statically:
   - `grep -q 'USER sempkm' backend/Dockerfile` — non-root user
   - `! grep -q '\-\-reload' backend/Dockerfile` — no hot-reload in production CMD (note: grep for the CMD line specifically, dev compose restores --reload via command override)
   - `grep -c 'no-new-privileges' docker-compose.yml docker-compose.test.yml docker-compose.demo.yml docker-compose.federation-test.yml docker-compose.test-ollama.yml` — present in all compose files
   - `grep -c 'cap_drop' docker-compose.yml docker-compose.test.yml docker-compose.demo.yml docker-compose.federation-test.yml docker-compose.test-ollama.yml` — present in all compose files
5. Verify Caddyfile cloud security:
   - `! grep -q 'unpkg.com\|cdn.jsdelivr.net\|cdnjs.cloudflare.com' Caddyfile.cloud` — stale CDN domains removed
   - `grep -q 'Strict-Transport-Security' Caddyfile.cloud` — HSTS present

## Must-Haves

- [ ] All 78 M045-specific tests pass
- [ ] All 140 M043-specific tests pass
- [ ] Docker hardening verified: non-root, no --reload in prod, security_opt, cap_drop
- [ ] Caddyfile verified: no stale CDN domains, HSTS present
  - Estimate: 30m
  - Files: backend/tests/test_ssrf_guard.py, backend/tests/test_federation_integrity.py, backend/tests/test_model_audit.py, backend/tests/test_zip_validator.py, backend/tests/test_app_token_isolation.py, backend/tests/test_sparql_injection_regression.py, backend/tests/test_sparql_builder.py, backend/tests/test_magic_link_hardening.py, backend/tests/test_token_scopes.py, backend/tests/test_session_management.py, backend/tests/test_security_hardening.py, backend/Dockerfile, docker-compose.yml, Caddyfile.cloud
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_ssrf_guard.py tests/test_federation_integrity.py tests/test_model_audit.py tests/test_zip_validator.py tests/test_app_token_isolation.py tests/test_sparql_injection_regression.py tests/test_sparql_builder.py tests/test_magic_link_hardening.py tests/test_token_scopes.py tests/test_session_management.py tests/test_security_hardening.py -v && echo '--- Docker checks ---' && grep -q 'USER sempkm' backend/Dockerfile && echo 'USER: OK' && grep -q 'Strict-Transport-Security' Caddyfile.cloud && echo 'HSTS: OK'
- [x] **T02: Rewrote security-model.md with complete 44-finding disposition table, 6 new security feature sections, and dependency scanning docs** — Update `docs/security-model.md` to serve as the comprehensive security reference for SemPKM, documenting all 44 M042 findings with their dispositions and all new security features added in M043-M045.

## Steps

1. Read the existing `docs/security-model.md` (123 lines) to understand current structure.
2. Read `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md` to get all 44 finding IDs and descriptions.
3. Read S01 and S02 summaries (inlined in context) for details on M045 features.
4. Update existing sections:
   - Security Event Audit Trail: change model_installed/model_uninstalled from "(future)" to current — these are implemented in M045/S01
   - App Platform Trust Model: add per-app JWT key isolation (HMAC-SHA256 derivation)
   - Federation: add SSRF protection, SHA-256 hash integrity, namespace filtering
5. Add new sections:
   - **SSRF Protection**: `validate_outbound_url()` utility, 4 code paths protected (federation sync, inbox post, inbox discovery, webhook dispatch), DNS resolution + IP category checking
   - **Federation Integrity**: SHA-256 content hash on exports, verification on imports, namespace filtering (urn:sempkm:* except shared, OWL/SHACL class injection prevention)
   - **ZIP Upload Protection**: `validate_zip_contents()` checks (uncompressed size ≤2GB, file count ≤50k, compression ratio ≤100:1), wired into Obsidian and Notion importers
   - **Docker Hardening**: non-root UID 1000, no-new-privileges, cap_drop ALL, no --reload in production
   - **Weak Key Rejection**: startup guard rejects known weak SECRET_KEY values in non-demo mode
   - **Cloud Security Headers**: HSTS (2-year max-age, includeSubDomains, preload), CSP without stale CDN domains
6. Add **M042 Security Audit Findings Disposition** section with a table mapping all 44 F-XXX IDs to their resolution status (Fixed by M043/M044/M045, or By Design/Documented) with brief descriptions.
7. Add **Dependency Scanning** section documenting:
   - `pip-audit` for Python dependencies (install: `pip install pip-audit`, run: `pip-audit`)
   - `npm audit` for JavaScript dependencies (run from frontend/)
   - Recommendation for `.github/dependabot.yml` configuration
   - Note that no CI pipeline currently exists — these are manual commands
8. Verify the final document: all 44 F-XXX IDs present, all new M045 sections present, model audit events no longer marked "future".

## Must-Haves

- [ ] All 44 F-XXX finding IDs (F-001 through F-044) appear in the disposition table
- [ ] New sections for: SSRF Protection, Federation Integrity, ZIP Upload Protection, Docker Hardening, Weak Key Rejection, Cloud Security Headers
- [ ] Model install/uninstall audit events updated from future to current
- [ ] Dependency scanning documented with pip-audit and npm audit commands
- [ ] Per-app JWT isolation documented
- [ ] Document is well-structured markdown with no broken formatting
  - Estimate: 45m
  - Files: docs/security-model.md
  - Verify: grep -c 'F-0' docs/security-model.md | xargs -I{} test {} -ge 44 && echo 'All 44 findings present' && grep -q 'SSRF' docs/security-model.md && grep -q 'ZIP' docs/security-model.md && grep -q 'pip-audit' docs/security-model.md && grep -q 'HMAC-SHA256' docs/security-model.md && grep -q 'no-new-privileges' docs/security-model.md && echo 'All sections verified'
