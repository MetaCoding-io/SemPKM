---
estimated_steps: 18
estimated_files: 14
skills_used: []
---

# T01: Run full security test regression suite and verify Docker hardening

Run all 11 security-related test files (218 tests total) and verify Docker hardening via static file checks. Fix any test failures in M045-modified files. This proves all M043+M044+M045 security fixes hold.

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

## Inputs

- ``backend/tests/test_ssrf_guard.py` — 23 SSRF guard tests from S01`
- ``backend/tests/test_federation_integrity.py` — 17 federation integrity tests from S01`
- ``backend/tests/test_model_audit.py` — 10 model audit tests from S01`
- ``backend/tests/test_zip_validator.py` — 16 ZIP validator tests from S02`
- ``backend/tests/test_app_token_isolation.py` — 12 per-app token isolation tests from S02`
- ``backend/tests/test_sparql_injection_regression.py` — 18 SPARQL injection regression tests from M043`
- ``backend/tests/test_sparql_builder.py` — 66 SPARQL builder tests from M043`
- ``backend/tests/test_magic_link_hardening.py` — magic link single-use tests from M043`
- ``backend/tests/test_token_scopes.py` — API token scope tests from M043`
- ``backend/tests/test_session_management.py` — session cap/revoke tests from M043`
- ``backend/tests/test_security_hardening.py` — rate limit, error disclosure, auth logging tests from M043`
- ``backend/Dockerfile` — verify non-root user and no --reload`
- ``docker-compose.yml` — verify security_opt and cap_drop`
- ``Caddyfile.cloud` — verify HSTS and clean CSP`

## Expected Output

- ``backend/tests/test_ssrf_guard.py` — confirmed passing (23 tests)`
- ``backend/tests/test_federation_integrity.py` — confirmed passing (17 tests)`
- ``backend/tests/test_model_audit.py` — confirmed passing (10 tests)`
- ``backend/tests/test_zip_validator.py` — confirmed passing (16 tests)`
- ``backend/tests/test_app_token_isolation.py` — confirmed passing (12 tests)`
- ``backend/tests/test_sparql_injection_regression.py` — confirmed passing (18 tests)`
- ``backend/tests/test_sparql_builder.py` — confirmed passing (66 tests)`
- ``backend/tests/test_security_hardening.py` — confirmed passing`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_ssrf_guard.py tests/test_federation_integrity.py tests/test_model_audit.py tests/test_zip_validator.py tests/test_app_token_isolation.py tests/test_sparql_injection_regression.py tests/test_sparql_builder.py tests/test_magic_link_hardening.py tests/test_token_scopes.py tests/test_session_management.py tests/test_security_hardening.py -v && echo '--- Docker checks ---' && grep -q 'USER sempkm' backend/Dockerfile && echo 'USER: OK' && grep -q 'Strict-Transport-Security' Caddyfile.cloud && echo 'HSTS: OK'
