---
id: S02
parent: M043
milestone: M043
provides:
  - All app endpoints require authentication (Depends(get_current_user))
  - CORS handled exclusively by FastAPI — downstream slices adding new endpoints get CORS automatically
  - HTTP security headers on all responses via proxy layer
  - Setup endpoint guarded by setup_mode flag
requires:
  []
affects:
  - S04
  - S05
key_files:
  - backend/app/browser/apps.py
  - backend/app/api/setup_routes.py
  - backend/app/main.py
  - frontend/nginx.conf
  - frontend/nginx.demo.conf
  - Caddyfile.cloud
  - backend/tests/test_api_surface.py
  - backend/tests/test_app_views_commands.py
key_decisions:
  - D362: CORS single-source-of-truth in FastAPI — all nginx/Caddy CORS removed, _WellKnownCORSMiddleware for browser extension discovery
  - D363: HTTP security headers standard set for all proxy layers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, server_tokens off)
  - D364: Obsidian upload capped at 500MB (was unlimited)
patterns_established:
  - CORS ownership pattern: FastAPI CORSMiddleware is sole authority, proxy layers (nginx/Caddy) pass through without adding CORS headers
  - Per-path CORS override via BaseHTTPMiddleware: intercept specific paths and overwrite CORSMiddleware output when different CORS policy needed
  - Security headers in proxy layer: apply at nginx/Caddy level so they cover static files too, not just FastAPI routes
observability_surfaces:
  - Startup warnings logged at WARNING level for: demo_mode on non-localhost, cookie_secure=False on non-localhost, cookie_secure mismatch with HTTPS base URL
drill_down_paths:
  - .gsd/milestones/M043/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M043/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-25T09:12:05.757Z
blocker_discovered: false
---

# S02: Access Control & CORS Fixes

**Added authentication to 6 unprotected app endpoints, consolidated CORS ownership to FastAPI, added HTTP security headers to all proxy layers, guarded the setup endpoint, added startup misconfiguration warnings, and capped Obsidian upload size.**

## What Happened

Two tasks delivered the full scope of F-001 (unauthenticated endpoints), F-003/F-022 (CORS consolidation), F-004 (setup guard), F-021 (security headers), and F-027 (upload size cap).

T01 added `Depends(get_current_user)` to all 6 unprotected endpoints in `browser/apps.py`: apps_explorer, app_page, right_pane_sections, views_explorer_apps, app_view_tab, and commands_list. Also guarded the setup endpoint in `setup_routes.py` with a `setup_mode` check (returns 403 if not in setup mode), and added three startup warning checks to the lifespan in `main.py`: demo_mode on non-localhost, cookie_secure=False on non-localhost, and cookie_secure mismatch with HTTPS base URL. T01 also fixed a pre-existing bug where `manager.registry` was never wired to the real AppRegistry in test_app_views_commands.py — 14 previously-broken tests now pass.

T02 removed all CORS `add_header` directives from both nginx.conf and nginx.demo.conf (4 blocks each). CORS is now exclusively handled by FastAPI's CORSMiddleware — when CORS_ORIGINS is set, those specific origins are used; when empty, wildcard applies (matching prior behavior). A dedicated `_WellKnownCORSMiddleware` overrides the CORSMiddleware for `/.well-known/sempkm` to always return `Access-Control-Allow-Origin: *`, ensuring browser extensions on any origin can reach the discovery endpoint. T02 added 5 security headers plus `server_tokens off` to both nginx configs and the Caddyfile.cloud. The Obsidian upload location was capped at 500MB (was unlimited).

The full test suite shows 5254 passed / 102 failed — matching the pre-S02 baseline with no regressions. The 1 S02-specific failure (test_navigate_matching_app_page_includes_appid_pageid) predates M043.

## Verification

71 targeted tests passed (6 auth enforcement, 3 CORS middleware, 10 well-known endpoint, 52 app views/commands + setup). 1 pre-existing failure (appId/pageId feature not implemented). Full suite: 5254 passed / 102 failed — stable baseline. Both nginx configs validated with `nginx -t`. Zero CORS add_header lines remain in nginx configs (verified via rg). Security headers present in nginx.conf, nginx.demo.conf, and Caddyfile.cloud.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Fixed pre-existing bug in test_app_views_commands.py (manager.registry not wired to AppRegistry) — not in the plan but required for test suite to pass with new auth enforcement. Used `del response.headers[key]` instead of `.pop()` for Starlette MutableHeaders compatibility.

## Known Limitations

CSP includes 'unsafe-inline' for scripts and styles — required by existing htmx inline event handlers. Can be tightened after vendoring CDN deps (M029) and eliminating inline scripts. One pre-existing test failure (appId/pageId in command palette response) predates M043.

## Follow-ups

CSP tightening after CDN deps are vendored (M029) — remove CDN domains from allowlist. Consider nonce-based CSP for inline scripts when htmx usage is refactored.

## Files Created/Modified

- `backend/app/browser/apps.py` — Added Depends(get_current_user) to all 6 unprotected endpoints
- `backend/app/api/setup_routes.py` — Added setup_mode guard — returns 403 if not in setup mode
- `backend/app/main.py` — Added CORSMiddleware config, _WellKnownCORSMiddleware, startup security warnings (demo_mode + cookie_secure)
- `frontend/nginx.conf` — Removed all CORS add_header directives, added 5 security headers + server_tokens off + CSP, capped Obsidian upload at 500m
- `frontend/nginx.demo.conf` — Removed all CORS add_header directives, added same security headers as nginx.conf
- `Caddyfile.cloud` — Added security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, CSP, -Server)
- `backend/tests/test_api_surface.py` — Added 3 CORS middleware tests (wildcard well-known, configured origins, default wildcard)
- `backend/tests/test_app_views_commands.py` — Fixed manager.registry wiring, added auth dependency overrides, 6 new unauthenticated 401 tests
- `backend/tests/test_instance_config.py` — Added auth dependency override for setup guard test
- `backend/tests/test_sparql_injection_regression.py` — Added auth dependency override for F007 injection tests
