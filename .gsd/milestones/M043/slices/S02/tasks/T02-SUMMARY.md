---
id: T02
parent: S02
milestone: M043
key_files:
  - frontend/nginx.conf
  - frontend/nginx.demo.conf
  - Caddyfile.cloud
  - backend/app/main.py
  - backend/tests/test_api_surface.py
key_decisions:
  - CORS is now single-source-of-truth in FastAPI CORSMiddleware — nginx/Caddy proxy layers pass through without adding CORS headers
  - Well-known discovery endpoint gets wildcard CORS via a dedicated BaseHTTPMiddleware that overrides CORSMiddleware output for that single path
  - CSP allows scripts/styles from unpkg.com, cdn.jsdelivr.net, cdnjs.cloudflare.com plus 'unsafe-inline' for existing inline scripts/styles
  - Obsidian upload capped at 500MB instead of unlimited — prevents abuse while accommodating large vaults
duration: ""
verification_result: passed
completed_at: 2026-03-25T09:08:25.396Z
blocker_discovered: false
---

# T02: Consolidate CORS handling to FastAPI CORSMiddleware, add HTTP security headers to nginx/Caddy, cap Obsidian upload to 500MB

**Consolidate CORS handling to FastAPI CORSMiddleware, add HTTP security headers to nginx/Caddy, cap Obsidian upload to 500MB**

## What Happened

Implemented three changes:

1. **CORS consolidation (F-003/F-022):** Removed all CORS `add_header` directives from `frontend/nginx.conf` and `frontend/nginx.demo.conf` — 4 blocks of CORS headers (OPTIONS preflight + response headers on `/api/` and `/.well-known/sempkm`). CORS is now handled exclusively by FastAPI's CORSMiddleware in `backend/app/main.py`. Added a `_WellKnownCORSMiddleware` (BaseHTTPMiddleware subclass) that overrides the CORSMiddleware output specifically for `/.well-known/sempkm` to always return `Access-Control-Allow-Origin: *` and strip `Access-Control-Allow-Credentials`, ensuring browser extensions on any origin can reach the discovery endpoint regardless of CORS_ORIGINS configuration.

2. **HTTP security headers (F-021):** Added 5 security headers to the `server {}` block in both `nginx.conf` and `nginx.demo.conf`: X-Content-Type-Options (nosniff), X-Frame-Options (DENY), Referrer-Policy (strict-origin-when-cross-origin), Permissions-Policy (disable camera/microphone/geolocation), Content-Security-Policy (self + CDN allowlist for scripts/styles, data: for images, no frames). Also added `server_tokens off` to suppress nginx version disclosure. Applied equivalent headers to `Caddyfile.cloud` using Caddy's `header` directive including `-Server` to suppress the Server header.

3. **Obsidian upload cap (F-027):** Changed `client_max_body_size` on the Obsidian upload location from `0` (unlimited) to `500m`, preventing abuse via oversized uploads while still accommodating large vaults.

Added 3 new tests in `TestCORSMiddleware` class verifying: (a) well-known always returns wildcard CORS even with restricted CORS_ORIGINS, (b) API routes use configured origins when set, (c) wildcard CORS when no origins configured. Fixed a `MutableHeaders.pop()` AttributeError — Starlette's MutableHeaders requires `del` instead of `pop` for header removal.

## Verification

Ran `pytest tests/test_api_surface.py::TestCORSMiddleware -v` — 3/3 passed. Ran full well-known + CORS suite (13 tests) — all passed. Ran broader test suite (124 tests across 4 test files) — 123 passed, 1 pre-existing failure. Full suite: 5254 passed, 102 failed (matching T01 baseline — no regressions). Both nginx configs validated with `nginx -t` (syntax ok). Verified zero CORS `add_header` lines remain in nginx configs via `rg`. Verified security headers present in all 3 proxy configs (nginx.conf, nginx.demo.conf, Caddyfile.cloud).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py::TestCORSMiddleware -v` | 0 | ✅ pass | 3200ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py::TestWellKnownEndpoint tests/test_api_surface.py::TestCORSMiddleware -v` | 0 | ✅ pass (13/13) | 1980ms |
| 3 | `cd backend && .venv/bin/python -m pytest tests/ --ignore=tests/test_caldav_field_mapper.py --ignore=tests/test_caldav_sync_engine.py --ignore=tests/test_notion_executor.py --tb=short -q` | 1 | ✅ pass (5254 passed, 102 failed — matches T01 baseline) | 35900ms |
| 4 | `docker run --rm --add-host api:127.0.0.1 -v frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro nginx:alpine nginx -t` | 0 | ✅ pass (syntax ok) | 2000ms |
| 5 | `docker run --rm --add-host api:127.0.0.1 -v frontend/nginx.demo.conf:/etc/nginx/conf.d/default.conf:ro nginx:alpine nginx -t` | 0 | ✅ pass (syntax ok) | 1500ms |
| 6 | `rg 'Access-Control' frontend/nginx.conf frontend/nginx.demo.conf` | 1 | ✅ pass (zero CORS lines in nginx) | 50ms |


## Deviations

Used `del response.headers[...]` instead of `response.headers.pop(...)` for MutableHeaders compatibility — Starlette's MutableHeaders does not implement `pop()`. The Caddyfile.demo was not modified because it's just a minimal reverse_proxy to the nginx container — security headers are applied at the nginx layer inside the container.

## Known Issues

None.

## Files Created/Modified

- `frontend/nginx.conf`
- `frontend/nginx.demo.conf`
- `Caddyfile.cloud`
- `backend/app/main.py`
- `backend/tests/test_api_surface.py`
