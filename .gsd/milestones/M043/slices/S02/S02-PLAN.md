# S02: Access Control & CORS Fixes

**Goal:** Add authentication to 6 unprotected app endpoints (F-001), move CORS ownership to FastAPI (F-003/F-022), guard setup endpoint (F-004), add HTTP security headers (F-021).
**Demo:** Unauthenticated GET to /browser/apps/explorer returns 401. CORS preflight handled by FastAPI only — no duplicate headers from nginx.

## Must-Haves

- All 6 app endpoints have Depends(get_current_user)\n- All CORS add_header directives removed from nginx.conf and nginx.demo.conf\n- FastAPI CORSMiddleware configured with CORS_ORIGINS for cloud, plus special wildcard handling for /.well-known/sempkm\n- Security headers added to nginx: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, server_tokens off\n- Setup endpoint checks setup_mode before allowing configuration\n- Existing E2E tests pass

## Proof Level

- This slice proves: Unit tests + header verification + E2E pass

## Integration Closure

Browser extension discovery verified working with backend-only CORS. Existing E2E tests pass.

## Verification

- 401 responses on previously open endpoints visible in access logs. Security headers visible in response headers.

## Tasks

- [x] **T01: Add authentication to app endpoints + setup guard + startup warnings** `est:2h`
  1. Add `user: User = Depends(get_current_user)` to all 6 unprotected endpoints in browser/apps.py:
   - GET /browser/apps/explorer
   - GET /browser/apps/{app_id}/page/{page_id}
   - GET /browser/apps/right-pane-sections
   - GET /browser/apps/views/explorer
   - GET /browser/apps/{app_id}/view/{view_id}
   - GET /browser/apps/commands

2. Guard setup endpoint: In backend/app/api/setup_routes.py, add a check that setup_mode is active before allowing POST /api/setup/configure-instance. Return 403 if not in setup mode and data already exists.

3. Add startup warnings:
   - When demo_mode=True and APP_BASE_URL is non-localhost: log WARNING
   - When cookie_secure=False and APP_BASE_URL starts with https:// or is non-localhost: log WARNING
   - Add these checks to the lifespan function in main.py

Unit tests: verify unauthenticated requests to /browser/apps/explorer return 401.
  - Files: `backend/app/browser/apps.py`, `backend/app/api/setup_routes.py`, `backend/app/main.py`
  - Verify: cd backend && .venv/bin/python -m pytest tests/ -v -x --timeout=60

- [x] **T02: CORS consolidation to backend + HTTP security headers in nginx** `est:2h`
  1. Remove all CORS add_header directives from frontend/nginx.conf (lines 74-77, 96-98, 116-118, 122-125) and frontend/nginx.demo.conf equivalent sections.

2. Configure FastAPI CORSMiddleware in backend/app/main.py:
   - When CORS_ORIGINS is set: use those origins (cloud deployment)
   - When CORS_ORIGINS is empty: use wildcard (local dev, matches current behavior)
   - Add a secondary CORS-like middleware or route-specific header for /.well-known/sempkm that always returns Access-Control-Allow-Origin: * regardless of CORS_ORIGINS setting

3. Add HTTP security headers to nginx.conf (in the server block, applying to all responses):
   - server_tokens off
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - Referrer-Policy: strict-origin-when-cross-origin
   - Permissions-Policy: camera=(), microphone=(), geolocation=()
   - Content-Security-Policy: default-src 'self'; script-src 'self' https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none';
   - Apply same headers to nginx.demo.conf and ensure Caddyfile.cloud equivalents

4. Set client_max_body_size 500m on the Obsidian upload location (F-027).

5. Verify: no duplicate CORS headers in curl response, security headers present, browser extension discovery still works.
  - Files: `frontend/nginx.conf`, `frontend/nginx.demo.conf`, `backend/app/main.py`, `Caddyfile.cloud`
  - Verify: curl -sI http://localhost:3000/api/sparql 2>/dev/null | grep -i 'access-control\|x-frame\|x-content-type\|referrer-policy\|permissions-policy'

## Files Likely Touched

- backend/app/browser/apps.py
- backend/app/api/setup_routes.py
- backend/app/main.py
- frontend/nginx.conf
- frontend/nginx.demo.conf
- Caddyfile.cloud
