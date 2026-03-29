# S03: Regression Verification & Documentation — UAT

**Milestone:** M045
**Written:** 2026-03-29T00:24:19.708Z

## UAT: Regression Verification & Documentation

### Preconditions
- Backend virtual environment at `backend/.venv/` with all test dependencies installed
- All 5 Docker compose files present: `docker-compose.yml`, `docker-compose.test.yml`, `docker-compose.demo.yml`, `docker-compose.federation-test.yml`, `docker-compose.test-ollama.yml`
- `docs/security-model.md` exists
- `Caddyfile.cloud` exists
- `backend/Dockerfile` exists

---

### Test 1: M045 Security Tests (78 tests)
**Steps:**
1. Run: `cd backend && .venv/bin/python -m pytest tests/test_ssrf_guard.py tests/test_federation_integrity.py tests/test_model_audit.py tests/test_zip_validator.py tests/test_app_token_isolation.py -v`

**Expected:** 78 passed, 0 failed. Tests cover SSRF URL validation (loopback, private, reserved IPs), federation hash verification and namespace filtering, model install/uninstall audit logging, ZIP bomb detection (size/count/ratio limits), and per-app JWT key isolation with weak key rejection.

---

### Test 2: M043 Security Tests (140 tests)
**Steps:**
1. Run: `cd backend && .venv/bin/python -m pytest tests/test_sparql_injection_regression.py tests/test_sparql_builder.py tests/test_magic_link_hardening.py tests/test_token_scopes.py tests/test_session_management.py tests/test_security_hardening.py -v`

**Expected:** 140 passed, 0 failed. Third-party deprecation warnings from slowapi and httpx are acceptable.

---

### Test 3: Docker Non-Root User
**Steps:**
1. Run: `grep 'USER sempkm' backend/Dockerfile`

**Expected:** At least one line matches — production image runs as non-root UID 1000.

---

### Test 4: Docker Production CMD Has No --reload
**Steps:**
1. Run: `grep -E 'CMD|ENTRYPOINT' backend/Dockerfile | grep -v '#'`

**Expected:** CMD line contains `uvicorn app.main:app --host 0.0.0.0 --port 8000` with NO `--reload` flag. (Dev compose restores --reload via command override.)

---

### Test 5: Security Options in All Compose Files
**Steps:**
1. Run: `grep -c 'no-new-privileges' docker-compose.yml docker-compose.test.yml docker-compose.demo.yml docker-compose.federation-test.yml docker-compose.test-ollama.yml`
2. Run: `grep -c 'cap_drop' docker-compose.yml docker-compose.test.yml docker-compose.demo.yml docker-compose.federation-test.yml docker-compose.test-ollama.yml`

**Expected:** Both commands show counts ≥ 1 for all 5 files.

---

### Test 6: Caddyfile Cloud Security
**Steps:**
1. Run: `grep -E 'unpkg.com|cdn.jsdelivr.net|cdnjs.cloudflare.com' Caddyfile.cloud` — should return nothing (exit code 1)
2. Run: `grep 'Strict-Transport-Security' Caddyfile.cloud` — should match

**Expected:** No stale CDN domains. HSTS header configured.

---

### Test 7: Security Model Document — Finding Coverage
**Steps:**
1. Run: `grep -oP 'F-0\d+' docs/security-model.md | sort -u | wc -l`

**Expected:** Output is `44` — all M042 findings from F-001 through F-044 documented.

---

### Test 8: Security Model Document — New Sections
**Steps:**
1. Run: `grep -c 'SSRF' docs/security-model.md` — should be ≥ 1
2. Run: `grep -c 'ZIP' docs/security-model.md` — should be ≥ 1
3. Run: `grep -c 'pip-audit' docs/security-model.md` — should be ≥ 1
4. Run: `grep -c 'HMAC-SHA256' docs/security-model.md` — should be ≥ 1
5. Run: `grep -c 'no-new-privileges' docs/security-model.md` — should be ≥ 1
6. Run: `grep -c '(future)' docs/security-model.md` — should be `0`

**Expected:** All 6 new sections present. No "(future)" placeholders remain — model audit events are documented as implemented.

---

### Test 9: Edge Case — Missing Compose File
**Steps:**
1. Verify all 5 compose files exist: `ls -1 docker-compose.yml docker-compose.test.yml docker-compose.demo.yml docker-compose.federation-test.yml docker-compose.test-ollama.yml`

**Expected:** All 5 files listed. If any is missing, security hardening checks in Test 5 would fail.

---

### Test 10: Edge Case — Finding ID Continuity
**Steps:**
1. Run: `grep -oP 'F-0\d+' docs/security-model.md | sort -u` and verify sequence covers F-001 through F-044 with no gaps

**Expected:** 44 unique IDs in contiguous sequence. No duplicate or out-of-range IDs.
