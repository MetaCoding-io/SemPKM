# S02: Docker Hardening & Infrastructure Security — UAT

**Milestone:** M045
**Written:** 2026-03-29T00:10:14.518Z

## UAT: S02 Docker Hardening & Infrastructure Security

### Preconditions
- Docker and docker compose installed
- Backend venv at `backend/.venv/` with dependencies
- Access to `Caddyfile.cloud`, `backend/Dockerfile`, and all compose files

---

### Test 1: Non-root Docker container
**Steps:**
1. Run `docker build -t sempkm-uat backend/`
2. Run `docker run --rm sempkm-uat id`
3. Run `docker run --rm sempkm-uat stat -c '%U:%G' /app/data`

**Expected:**
- Step 2 output: `uid=1000(sempkm) gid=1000(sempkm) groups=1000(sempkm)`
- Step 3 output: `sempkm:sempkm`

### Test 2: No --reload in production Dockerfile
**Steps:**
1. Run `grep 'CMD' backend/Dockerfile`

**Expected:**
- CMD line contains `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- CMD line does NOT contain `--reload`

### Test 3: Dev compose restores hot-reload
**Steps:**
1. Run `grep -A1 'command:' docker-compose.yml | head -2`

**Expected:**
- Output contains `--reload --reload-dir /app/app`

### Test 4: security_opt and cap_drop on all compose files
**Steps:**
1. Run `grep -c 'no-new-privileges' docker-compose.yml docker-compose.test.yml docker-compose.demo.yml docker-compose.federation-test.yml docker-compose.test-ollama.yml`
2. Run `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config | grep -c 'no-new-privileges'`

**Expected:**
- Step 1: Each standalone file shows ≥2 occurrences (1 per api + 1 per frontend); federation-test shows 4
- Step 2: Merged cloud config shows 2 occurrences (inherited from base)

### Test 5: ZIP bomb — oversized archive rejected
**Steps:**
1. Run `cd backend && .venv/bin/python -m pytest tests/test_zip_validator.py::TestUncompressedSizeLimit -v`

**Expected:**
- 3 tests pass: exceeding limit raises, exactly at limit passes, 1 byte over fails

### Test 6: ZIP bomb — excessive file count rejected
**Steps:**
1. Run `cd backend && .venv/bin/python -m pytest tests/test_zip_validator.py::TestFileCountLimit -v`

**Expected:**
- 2 tests pass: exceeding count raises, exactly at limit passes

### Test 7: ZIP bomb — suspicious compression ratio rejected
**Steps:**
1. Run `cd backend && .venv/bin/python -m pytest tests/test_zip_validator.py::TestCompressionRatio -v`

**Expected:**
- 3 tests pass: suspicious ratio raises, moderate passes, zero-byte compressed entry skipped

### Test 8: ZIP validator wired into both importers
**Steps:**
1. Run `grep -c 'validate_zip_contents' backend/app/obsidian/router.py backend/app/notion/router.py`
2. Run `grep -c 'except ValueError' backend/app/obsidian/router.py backend/app/notion/router.py`

**Expected:**
- Both files show ≥1 occurrence of `validate_zip_contents`
- Both files show ≥1 occurrence of `except ValueError`

### Test 9: Weak SECRET_KEY rejected at startup
**Steps:**
1. Run `cd backend && .venv/bin/python -m pytest tests/test_app_token_isolation.py::TestWeakKeyStartupRejection -v`

**Expected:**
- 7 tests pass: 4 weak keys cause SystemExit, demo key allowed in demo mode, E2E test key allowed, weak key allowed in demo mode

### Test 10: Per-app JWT key isolation
**Steps:**
1. Run `cd backend && .venv/bin/python -m pytest tests/test_app_token_isolation.py::TestGetAppSecret -v`
2. Run `cd backend && .venv/bin/python -m pytest tests/test_app_token_isolation.py::TestTokenIsolation -v`

**Expected:**
- Step 1: 3 tests pass — different apps get different keys, same app is deterministic, key is hex SHA-256
- Step 2: 2 tests pass — token validates with own key, fails with other app's key

### Test 11: Caddyfile CSP — no stale CDN domains
**Steps:**
1. Run `grep 'script-src\|style-src' Caddyfile.cloud`

**Expected:**
- Neither line contains `unpkg.com`, `cdn.jsdelivr.net`, or `cdnjs.cloudflare.com`
- Both contain `'self' 'unsafe-inline'`

### Test 12: HSTS header present
**Steps:**
1. Run `grep 'Strict-Transport-Security' Caddyfile.cloud`

**Expected:**
- Output: `Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"`

---

### Edge Cases

**E1: Empty ZIP passes validation**
- Run `cd backend && .venv/bin/python -m pytest tests/test_zip_validator.py::TestHappyPath::test_empty_zip_passes -v`
- Expected: PASS

**E2: Custom limits respected**
- Run `cd backend && .venv/bin/python -m pytest tests/test_zip_validator.py::TestCustomLimits -v`
- Expected: 3 tests PASS — custom size, count, and ratio limits all honored

**E3: Error messages include context**
- Run `cd backend && .venv/bin/python -m pytest tests/test_zip_validator.py::TestErrorMessages -v`
- Expected: 3 tests PASS — size error includes actual+limit, count error includes actual+limit, ratio error includes filename
