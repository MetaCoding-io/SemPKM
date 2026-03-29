---
id: S02
parent: M045
milestone: M045
provides:
  - Non-root Docker containers with no-new-privileges and cap-drop ALL
  - ZIP bomb protection for Obsidian and Notion importers
  - Weak SECRET_KEY startup guard
  - Per-app JWT key isolation via HMAC-SHA256
  - HSTS header on cloud deployment
  - Clean CSP without stale CDN domains
requires:
  []
affects:
  - S03
key_files:
  - backend/Dockerfile
  - backend/app/security/zip_validator.py
  - backend/app/main.py
  - backend/app/apps/tokens.py
  - backend/app/apps/manager.py
  - backend/app/apps/router.py
  - backend/app/obsidian/router.py
  - backend/app/notion/router.py
  - backend/tests/test_zip_validator.py
  - backend/tests/test_app_token_isolation.py
  - Caddyfile.cloud
  - docker-compose.yml
  - docker-compose.test.yml
  - docker-compose.demo.yml
  - docker-compose.cloud.yml
  - docker-compose.federation-test.yml
  - docker-compose.test-ollama.yml
key_decisions:
  - D373: Per-app JWT signing keys derived via HMAC-SHA256(platform_key, app_id) — deterministic, no extra storage
  - D374: Cloud compose overlay inherits security_opt/cap_drop from base — no duplication
patterns_established:
  - ZIP validation via central directory inspection (infolist) before extraction — shared utility at backend/app/security/zip_validator.py
  - Per-app secret derivation via HMAC-SHA256 — get_app_secret(app_id) in backend/app/apps/tokens.py
  - Non-root Docker pattern: create system user after WORKDIR, chown data dirs, USER directive after all root-requiring steps, dev compose restores --reload via command override
observability_surfaces:
  - Weak SECRET_KEY rejection logs logger.error with the offending key name before SystemExit(1)
  - ZIP validator logs logger.warning for compression ratios > 50:1 that are below the rejection threshold
drill_down_paths:
  - .gsd/milestones/M045/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M045/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M045/slices/S02/tasks/T03-SUMMARY.md
  - .gsd/milestones/M045/slices/S02/tasks/T04-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-29T00:10:14.518Z
blocker_discovered: false
---

# S02: Docker Hardening & Infrastructure Security

**Hardened Docker containers to run as non-root UID 1000 with no-new-privileges/cap-drop, added ZIP bomb protection to both importers, rejected weak SECRET_KEY on startup, isolated per-app JWT signing keys via HMAC-SHA256, and cleaned stale CDN domains from Caddyfile CSP with HSTS.**

## What Happened

Four tasks across Docker infrastructure, file upload security, application startup, and cloud deployment headers.

**T01 — Docker hardening:** Created `sempkm` user (UID 1000) in the backend Dockerfile with `USER sempkm` directive after all root-requiring build steps. Removed `--reload` from production CMD. Added `security_opt: ["no-new-privileges:true"]` and `cap_drop: [ALL]` to every api and frontend service across all 6 compose files (dev, test, demo, cloud, federation-test, test-ollama). Dev compose restores hot-reload via explicit `command:` override. Cloud overlay inherits security directives from base compose — adding duplicates caused validation errors, so the overlay only declares its caddy-specific overrides.

**T02 — ZIP bomb protection:** Created `backend/app/security/zip_validator.py` with `validate_zip_contents()` that inspects the ZIP central directory via `infolist()` without extracting. Checks three criteria: uncompressed size (default 2048 MB), file count (default 50,000), and per-entry compression ratio (default 100:1). Wired into both Obsidian and Notion importer `_write_and_extract()` functions before `extractall()`. Both routers catch `ValueError` and return styled 400 HTML error. 16 unit tests cover all rejection criteria, boundary conditions, custom limits, and error message quality.

**T03 — Weak key rejection & per-app key isolation:** Added `_WEAK_KEYS` set to `main.py` Security Startup Warnings section — server raises `SystemExit(1)` when `secret_key` matches a known weak value (`changeme`, `secret`, `password`, `admin`) and `demo_mode` is `False`. Demo and E2E test keys pass by design. Added `get_app_secret(app_id)` to `tokens.py` using `HMAC-SHA256(platform_key, app_id)` for deterministic per-app key derivation. Updated `manager.py` and `router.py` to use per-app keys — a compromised app token can no longer forge tokens for other apps. 12 unit tests.

**T04 — Caddyfile CSP & HSTS:** Removed `unpkg.com`, `cdn.jsdelivr.net`, and `cdnjs.cloudflare.com` from both `script-src` and `style-src` CSP directives. Added `Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"` (2-year max-age with preload).

## Verification

All slice-level verification checks pass:

1. `grep -q 'USER sempkm' backend/Dockerfile` → PASS
2. `! grep -q '--reload' backend/Dockerfile` → PASS (no reload in production CMD)
3. `grep -c 'no-new-privileges' docker-compose*.yml` → 2/2/2/4/2 across 5 standalone files; cloud overlay inherits from base (verified via `docker compose config`)
4. Dev compose `command:` override restores `--reload --reload-dir /app/app` → PASS
5. `cd backend && .venv/bin/python -m pytest tests/test_zip_validator.py -v` → 16/16 PASS
6. `cd backend && .venv/bin/python -m pytest tests/test_app_token_isolation.py -v` → 12/12 PASS
7. `! grep -q 'unpkg.com\|cdn.jsdelivr.net\|cdnjs.cloudflare.com' Caddyfile.cloud` → PASS
8. `grep -q 'Strict-Transport-Security' Caddyfile.cloud` → PASS (max-age=63072000)

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Cloud compose overlay does not duplicate security_opt/cap_drop — inherits from base docker-compose.yml via compose merge. Adding duplicates caused validation errors.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `backend/Dockerfile` — Added sempkm user (UID 1000), USER directive, chown /app/data, removed --reload from production CMD
- `docker-compose.yml` — Added security_opt: no-new-privileges:true and cap_drop: ALL to api and frontend; added command override restoring --reload for dev
- `docker-compose.test.yml` — Added security_opt and cap_drop to api and frontend services
- `docker-compose.demo.yml` — Added security_opt and cap_drop to api and frontend services
- `docker-compose.cloud.yml` — Inherits security directives from base compose
- `docker-compose.federation-test.yml` — Added security_opt and cap_drop to api-a, api-b, frontend-a, frontend-b
- `docker-compose.test-ollama.yml` — Added security_opt and cap_drop to api and frontend services
- `backend/app/security/zip_validator.py` — New shared ZIP bomb validator checking uncompressed size, file count, compression ratio
- `backend/app/obsidian/router.py` — Wired validate_zip_contents() before extractall with ValueError → 400 error
- `backend/app/notion/router.py` — Wired validate_zip_contents() before extractall with ValueError → 400 error
- `backend/tests/test_zip_validator.py` — 16 unit tests covering all ZIP validation criteria
- `backend/app/main.py` — Added _WEAK_KEYS set and startup rejection for weak SECRET_KEY in non-demo mode
- `backend/app/apps/tokens.py` — Added get_app_secret(app_id) using HMAC-SHA256 derivation
- `backend/app/apps/manager.py` — Switched from get_secret() to get_app_secret(app_id) for app token generation
- `backend/app/apps/router.py` — Switched from get_secret() to get_app_secret(app_id) for app token validation and renewal
- `backend/tests/test_app_token_isolation.py` — 12 unit tests for key derivation, token isolation, weak key rejection
- `Caddyfile.cloud` — Removed 3 stale CDN domains from CSP, added HSTS with 2-year max-age
