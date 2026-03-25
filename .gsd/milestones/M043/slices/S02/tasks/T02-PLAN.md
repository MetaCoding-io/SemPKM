---
estimated_steps: 15
estimated_files: 4
skills_used: []
---

# T02: CORS consolidation to backend + HTTP security headers in nginx

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

## Inputs

- `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md`

## Expected Output

- `frontend/nginx.conf`
- `frontend/nginx.demo.conf`
- `backend/app/main.py`

## Verification

curl -sI http://localhost:3000/api/sparql 2>/dev/null | grep -i 'access-control\|x-frame\|x-content-type\|referrer-policy\|permissions-policy'
