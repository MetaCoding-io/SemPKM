# S02: Compression & HTTP Caching

**Goal:** nginx serves gzip-compressed responses with correct cache headers — immutable for content-hashed assets, no-cache with ETag for HTML pages.
**Demo:** `curl -H "Accept-Encoding: gzip" -sI http://localhost:3000/assets/vendor-*.min.js` returns `Content-Encoding: gzip` and `Cache-Control: public, max-age=31536000, immutable`. Auth pages return ETag and 304 on conditional GET. Proxied HTML from FastAPI is gzip-compressed.

## Must-Haves

- Server-level `gzip on` with `gzip_proxied any` compresses dynamic (proxied) HTML responses
- `gzip_static on` in `/assets/` block serves S01's pre-built `.gz` files with zero CPU cost
- `/assets/` responses include `Cache-Control: public, max-age=31536000, immutable`
- Auth HTML pages (`login.html`, `setup.html`, `invite.html`) include `Cache-Control: no-cache` enabling ETag conditional GET (304 Not Modified)
- Dev-mode `/css/` and `/js/` blocks unchanged (`no-store, no-cache, must-revalidate`)
- Both `nginx.conf` and `nginx.demo.conf` updated identically (demo config also needs the `/assets/` block which S01 only added to nginx.conf)
- `nginx -t` passes in Docker container

## Verification

All verification via curl against running Docker stack:

- `curl -H "Accept-Encoding: gzip" -sI http://localhost:3000/assets/vendor-*.min.js | grep -q 'Content-Encoding: gzip'` — gzip_static serves pre-compressed assets
- `curl -H "Accept-Encoding: gzip" -sI http://localhost:3000/assets/vendor-*.min.js | grep -q 'immutable'` — immutable cache header on hashed assets
- `curl -H "Accept-Encoding: gzip" -sI http://localhost:3000/browser/ | grep -q 'Content-Encoding: gzip'` — gzip compresses proxied HTML
- `curl -sI http://localhost:3000/login.html | grep -q 'ETag'` — ETag present on auth pages
- `curl -sI http://localhost:3000/login.html | grep -q 'Cache-Control: no-cache'` — no-cache on auth pages
- Auth page conditional GET returns 304 Not Modified
- `curl -sI http://localhost:3000/js/workspace.js | grep -q 'no-store'` — dev files still no-cache
- `docker compose exec frontend nginx -t` — config syntax valid

## Tasks

- [ ] **T01: Add gzip compression and cache headers to nginx configs** `est:45m`
  - Why: This is the entire slice — add server-level gzip, gzip_static on /assets/, immutable cache headers on hashed assets, no-cache + ETag on auth pages. Both nginx.conf and nginx.demo.conf.
  - Files: `frontend/nginx.conf`, `frontend/nginx.demo.conf`
  - Do: (1) Add gzip server-level directives to both configs. (2) Add `gzip_static on` and `Cache-Control: immutable` to the existing `/assets/` block in nginx.conf. (3) Add the full `/assets/` block to nginx.demo.conf (missing from S01). (4) Add `Cache-Control: no-cache` to all three auth page location blocks. (5) Rebuild frontend container. (6) Verify all 8 curl checks pass.
  - Verify: All 8 curl checks from the Verification section above pass against running Docker stack.
  - Done when: `nginx -t` passes, gzip and cache headers confirmed on all three response categories (hashed assets, auth HTML, proxied HTML), dev-mode files unchanged.

## Files Likely Touched

- `frontend/nginx.conf`
- `frontend/nginx.demo.conf`
