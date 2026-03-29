# S02: Docker Hardening & Infrastructure Security

**Goal:** Harden Docker containers (non-root, no-new-privileges, cap-drop), protect ZIP uploads against bomb attacks, reject weak SECRET_KEY on startup, isolate per-app JWT signing keys, and clean stale CDN domains from Caddyfile CSP.
**Demo:** After this: docker compose up starts with non-root containers. ZIP upload of oversized archive returns clear error. Startup refuses weak SECRET_KEY in non-demo mode. Caddyfile.cloud CSP has no stale CDN domains.

## Tasks
- [x] **T01: Hardened backend Dockerfile to run as non-root UID 1000 (sempkm) and added security_opt/cap_drop to all 6 compose files** — Harden the backend Dockerfile to run as non-root (UID 1000) and add security_opt/cap_drop to all compose files.

## Steps

1. Edit `backend/Dockerfile`:
   - After the `WORKDIR /app` and before `COPY` commands, add `RUN groupadd -r sempkm && useradd -r -u 1000 -g sempkm sempkm`
   - After `RUN mkdir -p /app/data`, add `RUN chown -R sempkm:sempkm /app/data`
   - Remove `--reload --reload-dir /app/app` from the CMD line (production should not auto-reload)
   - Add `USER sempkm` after all RUN commands that need root (after COPY steps)
   - Final CMD: `["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`

2. Edit `docker-compose.yml` (dev):
   - Add to `api` service: `security_opt: ["no-new-privileges:true"]` and `cap_drop: [ALL]`
   - Add to `api` service: `command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/app"]` to restore dev hot-reload
   - Add to `frontend` service: `security_opt: ["no-new-privileges:true"]` and `cap_drop: [ALL]`

3. Edit `docker-compose.test.yml`:
   - Add `security_opt` and `cap_drop` to `api` and `frontend` services

4. Edit `docker-compose.demo.yml`:
   - Add `security_opt` and `cap_drop` to `api` and `frontend` services

5. Edit `docker-compose.cloud.yml`:
   - Add `security_opt` and `cap_drop` to the `frontend` override (api inherits from base compose)

6. Edit `docker-compose.federation-test.yml`:
   - Add `security_opt` and `cap_drop` to `api-a`, `api-b`, `frontend-a`, `frontend-b` services

7. Edit `docker-compose.test-ollama.yml`:
   - Add `security_opt` and `cap_drop` to `api` and `frontend` services

## Must-Haves

- [ ] Dockerfile has `USER sempkm` with UID 1000
- [ ] Dockerfile CMD has no `--reload` flag
- [ ] `/app/data` owned by sempkm user before USER directive
- [ ] All 6 compose files have `security_opt: ["no-new-privileges:true"]` and `cap_drop: [ALL]` on api/frontend services
- [ ] Dev compose restores `--reload` via command override
  - Estimate: 45m
  - Files: backend/Dockerfile, docker-compose.yml, docker-compose.test.yml, docker-compose.demo.yml, docker-compose.cloud.yml, docker-compose.federation-test.yml, docker-compose.test-ollama.yml
  - Verify: grep -q 'USER sempkm' backend/Dockerfile && ! grep -q '\-\-reload' backend/Dockerfile | tail -1 && grep -c 'no-new-privileges' docker-compose.yml docker-compose.test.yml docker-compose.demo.yml docker-compose.cloud.yml docker-compose.federation-test.yml docker-compose.test-ollama.yml | grep -v ':0$' | wc -l
- [x] **T02: Added ZIP bomb protection to Obsidian and Notion importers with shared validate_zip_contents() utility checking uncompressed size, file count, and compression ratio** — Create a shared ZIP validation utility and wire it into both importers to reject oversized or suspicious archives before extraction.

## Steps

1. Create `backend/app/security/zip_validator.py`:
   - Function `validate_zip_contents(zip_path: Path, max_uncompressed_mb: int = 2048, max_files: int = 50000) -> None`
   - Uses `zipfile.ZipFile(zip_path).infolist()` to sum `file_size` and count entries BEFORE calling extractall
   - Raises `ValueError('ZIP archive uncompressed size ({size_mb:.1f} MB) exceeds limit ({max_uncompressed_mb} MB)')` if total `file_size` exceeds limit
   - Raises `ValueError('ZIP archive contains {count} files, exceeding limit of {max_files}')` if file count exceeds limit
   - Check compression ratio: if any single entry has `compress_size > 0` and `file_size / compress_size > 100`, raise `ValueError('Suspicious compression ratio ({ratio:.0f}:1) detected in {entry.filename}')`
   - Log warnings at `logger.warning` for suspicious but passing archives (ratio > 50)

2. Edit `backend/app/obsidian/router.py`:
   - Import `validate_zip_contents` from `app.security.zip_validator`
   - In `_write_and_extract()`, after writing the ZIP to disk and before `zf.extractall()`, call `validate_zip_contents(zip_path)`
   - Catch `ValueError` from validation, clean up files, return 400 HTML error with the validation message

3. Edit `backend/app/notion/router.py`:
   - Same changes as obsidian router — import, validate before extract, catch ValueError

4. Create `backend/tests/test_zip_validator.py`:
   - Test: normal ZIP passes validation
   - Test: ZIP exceeding uncompressed size limit raises ValueError
   - Test: ZIP exceeding file count limit raises ValueError
   - Test: ZIP with suspicious compression ratio raises ValueError
   - Test: empty ZIP passes validation
   - Test: custom limits are respected
   - Use `zipfile.ZipFile` to create test fixtures in-memory or tmpdir

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| zipfile.ZipFile.infolist() | Re-raise as ValueError with context | N/A (local I/O) | Caught by existing BadZipFile handler |

## Negative Tests

- Malformed inputs: corrupt ZIP file (caught by existing BadZipFile handler, not this code)
- Error paths: ZIP with zero-byte compressed entries (ratio calculation division by zero — guard with `compress_size > 0`)
- Boundary conditions: ZIP exactly at limit passes, ZIP 1 byte over limit fails

## Must-Haves

- [ ] `validate_zip_contents()` checks uncompressed size, file count, and compression ratio
- [ ] Both Obsidian and Notion importers call validator before extractall
- [ ] ValueError from validator returns 400 with descriptive error message
- [ ] Unit tests cover all three rejection criteria plus happy path
  - Estimate: 40m
  - Files: backend/app/security/zip_validator.py, backend/app/obsidian/router.py, backend/app/notion/router.py, backend/tests/test_zip_validator.py
  - Verify: cd backend && python -m pytest tests/test_zip_validator.py -v
- [x] **T03: Add weak SECRET_KEY startup rejection and per-app JWT key isolation via HMAC-SHA256 derivation** — Reject known weak SECRET_KEY values at startup when not in demo/test mode, and derive per-app HMAC signing keys instead of using the platform-wide key directly.

## Steps

1. Edit `backend/app/main.py` in the `# --- Security Startup Warnings ---` section (around line 497):
   - Define `_WEAK_KEYS = {"changeme", "secret", "password", "admin"}`
   - After the existing localhost checks, add: if `settings.secret_key` is in `_WEAK_KEYS` and `settings.demo_mode` is `False`, log `logger.error("SECRET_KEY is a known weak value ('%s'). ...", settings.secret_key)` and `raise SystemExit(1)`
   - The demo key (`demo-secret-key-not-for-production`) and E2E test key (`e2e-test-secret-key-do-not-use-in-production`) are NOT in the weak list — they're intentional and clearly labeled
   - An empty `secret_key` is fine because `_get_secret_key()` auto-generates a secure random key

2. Edit `backend/app/apps/tokens.py`:
   - Add `import hmac` and `import hashlib`
   - Add function `get_app_secret(app_id: str) -> str` that calls `get_secret()` for the platform key, then returns `hmac.new(platform_key.encode(), app_id.encode(), hashlib.sha256).hexdigest()`
   - Keep `get_secret()` as-is for backward compat (other callers may still use it)

3. Edit `backend/app/apps/manager.py` line 193:
   - Change `generate_app_token(app_id, {}, get_secret())` to `generate_app_token(app_id, {}, get_app_secret(app_id))`
   - Update import to include `get_app_secret`

4. Edit `backend/app/apps/router.py` lines 79-80:
   - Change `secret = get_secret()` to `secret = get_app_secret(app_id)` — `app_id` is already available as a route parameter
   - Update import to include `get_app_secret`
   - Also update the `generate_app_token` call on the renewal path to use `get_app_secret(app_id)`

5. Create `backend/tests/test_app_token_isolation.py`:
   - Test: `get_app_secret('app-a')` != `get_app_secret('app-b')` (different apps get different keys)
   - Test: `get_app_secret('app-a')` called twice returns same value (deterministic)
   - Test: token signed with `get_app_secret('app-a')` validates with same key
   - Test: token signed with `get_app_secret('app-a')` does NOT validate with `get_app_secret('app-b')`
   - Test: startup rejection of weak key (mock settings, capture SystemExit)
   - Test: startup allows demo key when demo_mode=True

## Must-Haves

- [ ] Startup exits with error on weak SECRET_KEY when demo_mode=False
- [ ] Demo key passes when demo_mode=True
- [ ] `get_app_secret(app_id)` derives per-app key via HMAC-SHA256
- [ ] manager.py and router.py use `get_app_secret(app_id)` instead of `get_secret()`
- [ ] Unit tests prove key isolation and startup rejection
  - Estimate: 45m
  - Files: backend/app/main.py, backend/app/apps/tokens.py, backend/app/apps/manager.py, backend/app/apps/router.py, backend/tests/test_app_token_isolation.py
  - Verify: cd backend && python -m pytest tests/test_app_token_isolation.py -v
- [x] **T04: Removed 3 stale CDN domains from Caddyfile.cloud CSP and added HSTS header with 2-year max-age** — Remove stale CDN domains from Caddyfile.cloud CSP directives and add HSTS header for cloud deployments.

## Steps

1. Edit `Caddyfile.cloud` header block:
   - In Content-Security-Policy, remove `https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com` from `script-src` directive
   - Result: `script-src 'self' 'unsafe-inline'`
   - Same removal from `style-src` directive
   - Result: `style-src 'self' 'unsafe-inline'`
   - Add `Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"` to the header block

## Must-Haves

- [ ] CSP `script-src` contains no CDN domains
- [ ] CSP `style-src` contains no CDN domains
- [ ] HSTS header present with max-age >= 63072000
  - Estimate: 10m
  - Files: Caddyfile.cloud
  - Verify: ! grep -q 'unpkg.com\|cdn.jsdelivr.net\|cdnjs.cloudflare.com' Caddyfile.cloud && grep -q 'Strict-Transport-Security' Caddyfile.cloud
