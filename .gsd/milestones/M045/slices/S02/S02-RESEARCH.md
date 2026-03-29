# S02 Research: Docker Hardening & Infrastructure Security

## Summary

Targeted research — all items are straightforward infrastructure/config changes using known patterns. No novel technology, no ambiguous requirements. Six independent fixes batched into one slice.

## Recommendation

Six independent changes, all low-coupling. Natural task decomposition:
1. **Docker non-root + compose hardening** (F-023, F-024) — the riskiest item due to volume permissions
2. **ZIP bomb protection** (F-035) — shared utility + apply to both importers
3. **SECRET_KEY startup check + per-app JWT isolation** (F-026, F-042) — config/crypto changes in `main.py` and `apps/tokens.py`
4. **Caddyfile CSP cleanup + HSTS** (CSP stale, HSTS) — two-line config fix
5. **Dependency scanning documentation** (F-034) — documentation-only task

Tasks 1-4 are independent and could be done in any order. Task 5 depends on nothing. The riskiest item (Docker non-root) should go first to surface permission issues early.

## Implementation Landscape

### 1. Docker Non-Root (F-023) + Remove --reload (F-024)

**Backend Dockerfile (`backend/Dockerfile`):**
- Currently runs as root, CMD includes `--reload --reload-dir /app/app`
- Add: `RUN groupadd -r sempkm && useradd -r -u 1000 -g sempkm sempkm` (UID 1000 per D359)
- `RUN chown -R sempkm:sempkm /app/data` before the USER directive
- `USER sempkm` after all RUN commands that need root
- Remove `--reload --reload-dir /app/app` from CMD — production containers should not auto-reload
- Dev stack overrides CMD in `docker-compose.yml` via `command:` to add `--reload`

**Frontend Dockerfile (`frontend/Dockerfile`):**
- Uses `nginx:stable-alpine` which binds port 80 (requires root or CAP_NET_BIND_SERVICE)
- Simpler approach: keep nginx as root for port 80 binding but add `no-new-privileges` in compose
- Alternative: switch to port 8080 + non-root user. This requires updating all compose files' port mappings. Heavier change for marginal benefit since nginx drops privileges after binding.

**docker-compose.yml (all variants):**
- Add to both `api` and `frontend` services:
  ```yaml
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  ```
- For `api` service, add `command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/app"]` to restore dev-mode reload
- Currently zero compose files have `security_opt` or `cap_drop`

**Compose files that need updates:**
- `docker-compose.yml` (dev)
- `docker-compose.test.yml` (E2E test)
- `docker-compose.demo.yml` (demo)
- `docker-compose.cloud.yml` (cloud — only overrides frontend)
- `docker-compose.federation-test.yml` (federation test — check if it defines api/frontend)
- `docker-compose.test-ollama.yml` (ollama test variant)

**Volume permission risk:**
- `sempkm_data` volume: created by Docker, initial ownership depends on the Dockerfile. Since the Dockerfile creates `/app/data` with `mkdir` as root, existing volumes have root-owned files. After switching to UID 1000, the container can't write to existing volumes.
- Mitigation: Add an entrypoint script that checks ownership and runs `chown` if needed. But the container runs as non-root, so it can't chown. Solution: use `COPY --chown=sempkm:sempkm` for build-time files, and for the data volume, set ownership in the Dockerfile *before* the USER directive: `RUN mkdir -p /app/data && chown sempkm:sempkm /app/data`.
- For existing deployments: document `docker compose down && docker compose up` (volume contents are preserved but new container's UID 1000 user needs write access). Named volumes created fresh should work since the Dockerfile `RUN chown` sets the right ownership. Existing volumes may need manual `docker exec -u root <container> chown -R 1000:0 /app/data`.

### 2. ZIP Bomb Protection (F-035)

**Current state:**
- `backend/app/obsidian/router.py` line ~152: `zf.extractall(extract_path)` with no size/count check
- `backend/app/notion/router.py` line ~183: identical pattern
- Both accept ZIP uploads via `UploadFile` parameter
- nginx caps upload at `client_max_body_size 500m` (D364), so compressed size is bounded
- But uncompressed size is unbounded — a 500MB ZIP could expand to hundreds of GB

**Implementation:**
- Create `backend/app/security/zip_validator.py` (or add to existing `backend/app/security/` package from S01)
- Function: `validate_zip_contents(zip_path: Path, max_uncompressed_mb: int = 2048, max_files: int = 50000) -> None`
- Uses `ZipFile.infolist()` to sum `file_size` and count entries *before* calling `extractall()`
- Raises `ValueError` with descriptive message on violation
- Call in both importers between "write ZIP to disk" and "extractall"
- Also check compression ratio: if any single entry has `compress_size > 0` and `file_size / compress_size > 100`, flag as suspicious (zip bomb heuristic)

**Files to modify:**
- `backend/app/security/zip_validator.py` (new)
- `backend/app/obsidian/router.py` — add validation call in `_write_and_extract()`
- `backend/app/notion/router.py` — add validation call in `_write_and_extract()`

### 3. SECRET_KEY Startup Check (F-026) + Per-App JWT Isolation (F-042)

**SECRET_KEY check:**
- `backend/app/main.py` has a "Security Startup Warnings" section starting at ~line 498
- Add a check: if `settings.secret_key` is a known weak value AND `settings.demo_mode` is False, log ERROR and raise `SystemExit(1)`
- Known weak values: `"demo-secret-key-not-for-production"`, `"changeme"`, `"secret"`, `"e2e-test-secret-key-do-not-use-in-production"`
- When `settings.secret_key` is empty, the system auto-generates a secure key via `_get_secret_key()` in `tokens.py`, so empty is safe
- `docker-compose.demo.yml` sets `SECRET_KEY: demo-secret-key-not-for-production` with `DEMO_MODE: "true"` — this combination should be allowed

**Per-app JWT key derivation (F-042):**
- `backend/app/apps/tokens.py`: `get_secret()` returns platform-wide key
- Change to `get_app_secret(app_id: str)` using `hmac.new(platform_key.encode(), app_id.encode(), 'sha256').hexdigest()`
- Callers: `backend/app/apps/manager.py` line 193 (`generate_app_token(app_id, {}, get_secret())`) and `backend/app/apps/router.py` line 79 (`secret = get_secret()`)
- Both callers already have `app_id` in scope — pass it to the new function
- Token renewal in router.py: extract `app_id` from the expired token's `sub` claim (`app:{app_id}`) to derive the correct key for re-signing
- Backward compat: existing tokens signed with old key will fail validation. Since tokens are ephemeral (1h TTL, generated at app startup), this is a non-issue — apps get new tokens on restart.

### 4. Caddyfile.cloud CSP Cleanup + HSTS

**CSP (line 20 of Caddyfile.cloud):**
- Current: `script-src 'self' https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'`
- Since M044 vendored all CDN deps, these three domains are stale
- Fix: `script-src 'self' 'unsafe-inline'` (matches nginx.conf which is already clean)
- Same for `style-src`: remove the three CDN domains
- nginx.conf (line 13) already has the correct CSP without CDN domains
- nginx.demo.conf (line 21) also already clean

**HSTS:**
- Caddy with auto-TLS handles HTTPS certificates automatically
- Add `Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"` to the header block
- Only in Caddyfile.cloud — nginx configs serve over HTTP (behind Caddy or for local dev), so HSTS would be wrong there

### 5. Dependency Scanning Documentation (F-034)

- No CI/CD pipeline exists (no `.github/workflows/`)
- Document the manual commands in `docs/security-model.md` (or create if it doesn't exist):
  - `cd backend && pip-audit` (requires `pip install pip-audit`)
  - `cd frontend && npm audit`
  - Mention Dependabot for GitHub repos
- This is documentation-only work

## Constraints & Risks

1. **Volume permission (Docker non-root):** Primary risk. New containers with UID 1000 can't write to volumes initially owned by root. The Dockerfile's `RUN chown` only affects new volumes. Existing deployments need a migration path. Recommend documenting `docker compose down -v` for clean restart, or a one-time `docker exec -u root` chown.

2. **Compose file sprawl:** Six compose files need security_opt/cap_drop. The cloud compose only overrides frontend — api service inherits from base docker-compose.yml, so it gets the hardening automatically.

3. **Test compose:** `docker-compose.test.yml` uses `SECRET_KEY: e2e-test-secret-key-do-not-use-in-production`. This must be exempt from the startup rejection — either by adding it to the known-weak list with a test-mode exemption, or by treating `RATE_LIMIT_ENABLED: "false"` as an implicit test flag. Simplest: add both `demo-secret-key-not-for-production` and `e2e-test-secret-key-do-not-use-in-production` to the known list, and only reject when `demo_mode` is False AND the key is in the known-weak list AND the key doesn't contain `test` or `e2e`.

   Actually simpler: reject only when the key is in a very short list (`changeme`, `secret`, empty-string-that-isn't-really-empty) and let the demo/test keys pass — they're intentional. The real threat is someone deploying to production with a guessable key, not with a clearly-labeled test key. Alternatively: only reject `demo-secret-key-not-for-production` when `demo_mode=False`. The E2E key is fine since the test stack isn't publicly accessible.

4. **App token backward compat:** Per-app HMAC derivation changes the signing key. All existing app tokens become invalid. Since tokens have 1h TTL and are regenerated on app startup, this is a restart-only impact — no migration needed.

## Files Inventory

| File | What | Change |
|------|------|--------|
| `backend/Dockerfile` | Backend container image | Add non-root user, remove --reload from CMD |
| `docker-compose.yml` | Dev compose | Add security_opt, cap_drop, command override for --reload |
| `docker-compose.test.yml` | Test compose | Add security_opt, cap_drop |
| `docker-compose.demo.yml` | Demo compose | Add security_opt, cap_drop |
| `docker-compose.cloud.yml` | Cloud compose (frontend only) | Add security_opt, cap_drop to frontend override |
| `docker-compose.federation-test.yml` | Federation test | Add security_opt, cap_drop if it defines api/frontend |
| `docker-compose.test-ollama.yml` | Ollama test variant | Add security_opt, cap_drop if applicable |
| `backend/app/security/zip_validator.py` | New: ZIP bomb protection utility | Create |
| `backend/app/obsidian/router.py` | Obsidian importer | Add zip validation before extractall |
| `backend/app/notion/router.py` | Notion importer | Add zip validation before extractall |
| `backend/app/main.py` | App startup | Add SECRET_KEY weak-key rejection |
| `backend/app/apps/tokens.py` | App JWT tokens | Add per-app HMAC key derivation |
| `backend/app/apps/manager.py` | App lifecycle manager | Use get_app_secret(app_id) |
| `backend/app/apps/router.py` | App token renewal | Use get_app_secret(app_id) |
| `Caddyfile.cloud` | Cloud reverse proxy | Remove stale CDN domains from CSP, add HSTS |
| `backend/tests/test_zip_validator.py` | New: ZIP validator tests | Create |
| `backend/tests/test_app_token_isolation.py` | New: per-app JWT tests | Create |

## Verification Strategy

- `docker compose build` succeeds with non-root user
- `docker compose up` starts correctly, API healthcheck passes
- SQLite DB is writable (confirm via API call creating data)
- ZIP bomb upload returns 400 with descriptive error (unit test)
- Startup with `SECRET_KEY=changeme DEMO_MODE=false` exits with error
- Startup with `SECRET_KEY=demo-secret-key-not-for-production DEMO_MODE=true` succeeds
- App tokens signed with different app_ids have different signing keys (unit test)
- `Caddyfile.cloud` CSP contains no CDN domains (grep check)
