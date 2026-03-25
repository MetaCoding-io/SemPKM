# S02: Access Control & CORS Fixes — UAT

**Milestone:** M043
**Written:** 2026-03-25T09:12:05.758Z

# S02 UAT — Access Control & CORS Fixes

## Preconditions
- Docker stack running (`docker compose up -d`)
- User is NOT logged in (fresh browser / cleared cookies) for auth tests
- User IS logged in for CORS/header verification tests
- `curl` available on host

## Test Cases

### TC-01: Unauthenticated app endpoints return 401
1. Open a new browser tab (not logged in)
2. Navigate to `http://localhost:3000/browser/apps/explorer`
3. **Expected:** Redirected to login page (302 → /login.html) or receive 401 JSON
4. Repeat for:
   - `GET /browser/apps/views/explorer` → 401/redirect
   - `GET /browser/apps/commands` → 401/redirect
   - `GET /browser/apps/right-pane-sections?iri=http://example.org/test` → 401/redirect
5. **Expected:** All return 401 or redirect to login

### TC-02: Authenticated app endpoints work normally
1. Log in to the application
2. Navigate to workspace → verify Apps explorer section loads
3. Open an installed app page → verify content renders
4. **Expected:** All app endpoints function normally when authenticated

### TC-03: CORS headers come from FastAPI only
1. Run: `curl -sI http://localhost:3000/api/sparql 2>/dev/null | grep -i 'access-control'`
2. **Expected:** Exactly one `Access-Control-Allow-Origin` header (not duplicated)
3. Run: `curl -sI -H 'Origin: http://example.com' http://localhost:3000/.well-known/sempkm | grep -i 'access-control'`
4. **Expected:** `Access-Control-Allow-Origin: *` (wildcard, no credentials header)

### TC-04: Security headers present on all responses
1. Run: `curl -sI http://localhost:3000/ | grep -iE 'x-content-type|x-frame|referrer-policy|permissions-policy|content-security-policy'`
2. **Expected:**
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
   - `Content-Security-Policy: default-src 'self'; ...`
3. Run: `curl -sI http://localhost:3000/ | grep -i server`
4. **Expected:** No `Server: nginx/x.x.x` header (server_tokens off)

### TC-05: Setup endpoint guard
1. With app already configured, send: `curl -X POST http://localhost:3000/api/setup/configure-instance -H 'Content-Type: application/json' -d '{}'`
2. **Expected:** 403 Forbidden (setup_mode not active)

### TC-06: Obsidian upload size limit
1. Verify nginx config: `docker compose exec frontend grep client_max_body_size /etc/nginx/conf.d/default.conf`
2. **Expected:** Obsidian location shows `500m`, default shows `10m`

### TC-07: Browser extension discovery still works
1. Run: `curl -s http://localhost:3000/.well-known/sempkm` (unauthenticated)
2. **Expected:** 401 JSON response (requires auth)
3. Run with valid bearer token: `curl -s -H 'Authorization: Bearer <token>' http://localhost:3000/.well-known/sempkm`
4. **Expected:** JSON with version, endpoints, auth, capabilities
5. Verify CORS: response includes `Access-Control-Allow-Origin: *`

### TC-08: Startup warnings (manual verification)
1. Set `DEMO_MODE=true` and `APP_BASE_URL=https://example.com` in .env
2. Restart backend: `docker compose restart api`
3. Check logs: `docker compose logs api | grep WARNING`
4. **Expected:** Warning about demo_mode with non-localhost URL
5. Reset to normal configuration

### Edge Cases

### TC-09: CORS preflight (OPTIONS) handled correctly
1. Run: `curl -sI -X OPTIONS -H 'Origin: http://localhost:3001' -H 'Access-Control-Request-Method: GET' http://localhost:3000/api/sparql`
2. **Expected:** 200 with CORS headers (Access-Control-Allow-Methods, Access-Control-Allow-Headers)
3. No duplicate CORS headers in response
