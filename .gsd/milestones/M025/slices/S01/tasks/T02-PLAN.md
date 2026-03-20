---
estimated_steps: 4
estimated_files: 2
---

# T02: Create demo nginx config and docker-compose.demo.yml

**Slice:** S01 — Read-only enforcement + DEMO_MODE anonymous access
**Milestone:** M025

## Description

Create the read-only nginx configuration and Docker Compose file for the demo instance. The nginx config blocks all non-GET/HEAD/OPTIONS HTTP methods with a 403 JSON response (decision D245 — default-deny is safer than endpoint-by-endpoint allowlisting). The compose file wires together DEMO_MODE env var, the demo nginx config, separate volumes/ports/network so it can run alongside the dev stack.

## Steps

1. **Create `frontend/nginx.demo.conf`:**
   - Copy `frontend/nginx.conf` as the starting point
   - Add a **default-deny block** near the top of the `server {}` block, BEFORE any `location` blocks. Use nginx's `limit_except` or a map-based approach. The simplest correct approach:
     ```nginx
     # Demo mode: block all write methods globally.
     # Exceptions (GET-safe endpoints) are handled by returning before this fires.
     # This MUST come before specific location blocks in the server context.
     
     # Allow GET/HEAD/OPTIONS globally, deny everything else with 403 JSON
     if ($request_method !~ ^(GET|HEAD|OPTIONS)$) {
         set $demo_deny 1;
     }
     
     # Exception: /api/health needs no special treatment (GET-only)
     # Exception: /api/auth/status needs no special treatment (GET-only)
     ```
   - **IMPORTANT nginx caveat:** `if` in server context is tricky. The cleanest approach for nginx is to use a **`map` directive** in the `http` context (but we only have the `server` block in this conf file). Alternative: add an `error_page` based approach, or use `limit_except` inside each location block.
   - **Recommended approach:** Add a single `location @deny_write` named location, then in a top-level catch-all, check the method:
     ```nginx
     # Read-only enforcement for demo mode
     # Block all non-safe HTTP methods with 403 JSON response
     set $deny_write 0;
     if ($request_method !~ ^(GET|HEAD|OPTIONS)$) {
         set $deny_write 1;
     }
     ```
     Then in each `location` block that proxies to the API, add at the start:
     ```nginx
     if ($deny_write = 1) {
         add_header Content-Type application/json always;
         return 403 '{"error": "Demo instance is read-only"}';
     }
     ```
   - Actually, the simplest and most correct approach: since this is a **separate** nginx.conf for demo only, just add the write-deny check at the top of the server block using a **rewrite/return pattern**:
     ```nginx
     # Demo read-only enforcement: block all write methods
     if ($request_method !~ ^(GET|HEAD|OPTIONS)$) {
         return 403 '{"error": "Demo instance is read-only"}';
     }
     ```
     Place this as the FIRST directive in the `server {}` block. This catches ALL write methods on ALL routes. The `/api/health` and `/api/auth/status` endpoints are GET-only, so they pass through. The CORS OPTIONS preflight also passes through (OPTIONS is in the allow list).
   - **NOTE:** The `add_header Content-Type` does NOT work with bare `return` in an `if` block. The `return` in `if` will set a text/plain content type by default. To return JSON with correct content-type, use:
     ```nginx
     # Approach: use error_page for proper JSON content-type
     error_page 495 = @read_only;
     if ($request_method !~ ^(GET|HEAD|OPTIONS)$) {
         return 495;
     }
     location @read_only {
         default_type application/json;
         return 403 '{"error": "Demo instance is read-only"}';
     }
     ```
     This uses a custom error code (495) to redirect to a named location that returns proper JSON.
   - Keep ALL existing `location` blocks unchanged from `nginx.conf` — the read-only guard fires before any location matching for non-GET/HEAD/OPTIONS methods.

2. **Create `docker-compose.demo.yml`:**
   - Define 3 services: `triplestore`, `api`, `frontend` — same images as base compose
   - `triplestore`: same config, but use `rdf4j_demo_data` volume and `sempkm-demo` network
   - `api`: same build/config but add `DEMO_MODE: "true"` to environment. Use `sempkm_demo_data` volume, `sempkm-demo` network. Port `8902:8000`. Add `COOKIE_SECURE: "false"` and `RATE_LIMIT_ENABLED: "false"` for local testing. Use a fixed `SECRET_KEY` (doesn't matter for demo — no real sessions).
   - `frontend`: use `nginx.demo.conf` instead of `nginx.conf`. Port `3902:80`. `sempkm-demo` network.
   - Separate volumes: `rdf4j_demo_data`, `sempkm_demo_data`
   - Separate network: `sempkm-demo`
   - Add a comment at the top explaining usage: `docker compose -f docker-compose.demo.yml up -d --build`

3. **Validate nginx config syntax:**
   - Run: `docker run --rm -v $(pwd)/frontend/nginx.demo.conf:/etc/nginx/conf.d/default.conf:ro nginx:stable-alpine nginx -t`
   - Must output "syntax is ok" and "test is successful"

4. **Verify compose file syntax:**
   - Run: `docker compose -f docker-compose.demo.yml config --quiet` (validates YAML and compose schema)

## Must-Haves

- [ ] `frontend/nginx.demo.conf` blocks POST/PUT/DELETE/PATCH with `403 {"error": "Demo instance is read-only"}`
- [ ] GET/HEAD/OPTIONS pass through to all existing locations unchanged
- [ ] `/api/health` returns 200 (GET-only, passes the safe method check)
- [ ] CORS OPTIONS preflight returns 204 (OPTIONS is in the allow list)
- [ ] `docker-compose.demo.yml` sets `DEMO_MODE: "true"` on the api service
- [ ] `docker-compose.demo.yml` mounts `nginx.demo.conf` on the frontend service
- [ ] Separate volumes and ports from dev stack (no conflicts when both run)
- [ ] `nginx -t` passes on the demo config
- [ ] `docker compose config` validates the compose file

## Verification

- `docker run --rm -v $(pwd)/frontend/nginx.demo.conf:/etc/nginx/conf.d/default.conf:ro nginx:stable-alpine nginx -t` — "syntax is ok"
- `docker compose -f docker-compose.demo.yml config --quiet` — exits 0
- Manual review: confirm no `location` blocks were modified from base nginx.conf (only the read-only guard was added)

## Observability Impact

- **nginx 403 response:** Any POST/PUT/DELETE/PATCH request to the demo frontend returns `403 {"error": "Demo instance is read-only"}` with `Content-Type: application/json`. Verify with `curl -X POST http://localhost:3902/api/commands`.
- **Docker service ports:** Demo stack uses ports 3902 (frontend) and 8902 (API), separate from dev (3000/8001) and test (3901/8901). Check with `docker compose -f docker-compose.demo.yml ps`.
- **DEMO_MODE env:** The API container has `DEMO_MODE=true` in its environment. Verify with `docker compose -f docker-compose.demo.yml exec api env | grep DEMO_MODE`.
- **Failure visibility:** If nginx.demo.conf has a syntax error, the frontend container will crash on startup — visible via `docker compose -f docker-compose.demo.yml logs frontend`. If the read-only guard is misconfigured, POST requests will reach the API instead of returning 403 at nginx.

## Inputs

- `frontend/nginx.conf` — Base nginx config to copy and extend
- `docker-compose.yml` — Base compose file for reference on service definitions
- `docker-compose.test.yml` — Reference for the pattern of separate ports/volumes/network
- Decision D245 — default-deny on non-GET methods

## Expected Output

- `frontend/nginx.demo.conf` — New file: base nginx.conf + read-only enforcement block
- `docker-compose.demo.yml` — New file: 3-service demo stack with DEMO_MODE and demo nginx
