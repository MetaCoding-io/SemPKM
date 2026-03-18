---
estimated_steps: 4
estimated_files: 1
---

# T02: Fix nginx Authorization forwarding and add CORS

**Slice:** S01 — Dual-Auth, CORS, nginx fix, and Well-Known Endpoint
**Milestone:** M013

## Description

The `/api/` proxy block in nginx.conf doesn't forward the `Authorization` header — only the `/dav/` block does. Browser extensions send `Authorization: Bearer <token>` which gets silently stripped by nginx, so FastAPI never sees it. Fix this and add CORS headers so browser extensions can make cross-origin requests.

## Steps

1. Read `frontend/nginx.conf` to understand the current proxy blocks
2. In the `location /api/` block, add `proxy_set_header Authorization $http_authorization;` and `proxy_pass_header Authorization;` (copying the pattern from the `/dav/` block)
3. Add a new `location = /.well-known/sempkm` block that proxies to `http://api:8000/.well-known/sempkm` with the same headers (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto, Cookie, Authorization)
4. Add CORS headers to the `/api/` block and `/.well-known/sempkm` block:
   - `add_header Access-Control-Allow-Origin "*" always;`
   - `add_header Access-Control-Allow-Headers "Authorization, Content-Type, Accept" always;`
   - `add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;`
5. Handle OPTIONS preflight in the `/api/` block: `if ($request_method = OPTIONS) { return 204; }`

## Must-Haves

- [ ] Authorization header forwarded on `/api/` proxy block
- [ ] `/.well-known/sempkm` proxied to FastAPI backend with Authorization forwarding
- [ ] CORS headers present on all `/api/` responses
- [ ] OPTIONS preflight returns 204 with CORS headers

## Verification

- `docker compose restart frontend`
- `curl -v -H "Authorization: Bearer test" http://localhost:3000/api/types 2>&1 | grep -i "authorization"` — header reaches backend (visible in response or backend log)
- `curl -v -X OPTIONS http://localhost:3000/api/types -H "Origin: chrome-extension://abc" -H "Access-Control-Request-Method: GET" 2>&1 | grep -i "access-control"` — CORS headers present

## Inputs

- `frontend/nginx.conf` — current proxy configuration with `/dav/` as reference for Authorization forwarding

## Observability Impact

- **New signal — CORS headers on `/api/` responses:** `curl -v` against any `/api/` endpoint will now show `Access-Control-Allow-Origin`, `Access-Control-Allow-Headers`, and `Access-Control-Allow-Methods` response headers. Their absence indicates nginx didn't reload or the config has a syntax error.
- **New signal — OPTIONS preflight 204:** `curl -X OPTIONS` to any `/api/` path returns HTTP 204 with CORS headers. A 405 or proxy error means the `if ($request_method = OPTIONS)` block is missing or misconfigured.
- **Changed signal — Authorization header forwarding:** `/api/` requests now pass `Authorization` through to FastAPI. Visible in FastAPI debug logs (`app.auth.dependencies` logger shows "via Bearer token" when Bearer auth resolves). If the header is still stripped, the backend will never log the Bearer path — always the "Not authenticated" fallback.
- **New proxy block — `/.well-known/sempkm`:** nginx access log will show requests to this path proxied to `api:8000`. A 502 means the backend endpoint doesn't exist yet (expected until T03). A 404 means the nginx block is missing.
- **Failure visibility:** nginx config syntax errors surface via `docker compose restart frontend` failing with non-zero exit and `nginx -t` output in container logs.

## Expected Output

- `frontend/nginx.conf` — updated with Authorization forwarding on `/api/`, new `/.well-known/sempkm` block, and CORS headers
