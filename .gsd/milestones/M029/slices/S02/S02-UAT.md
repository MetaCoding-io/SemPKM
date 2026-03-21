# S02: Compression & HTTP Caching — UAT

**Milestone:** M029
**Written:** 2026-03-20

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: All verification is HTTP header inspection via curl against the running Docker stack — no code paths to unit test, purely nginx configuration behavior.

## Preconditions

- Docker stack running via `docker compose up -d` (main compose, not test compose)
- Frontend container healthy and serving on port 3000
- At least one content-hashed asset exists in `/srv/built-assets/` (from S01 build)

## Smoke Test

```bash
curl -sI -H "Accept-Encoding: gzip" http://localhost:3000/login.html | grep -E "Content-Encoding|Cache-Control|ETag"
```
Expected: All three headers present — `Content-Encoding: gzip`, `Cache-Control: no-cache`, `ETag: "<hash>"`.

## Test Cases

### 1. Hashed assets: gzip_static serves pre-compressed files

1. Get asset name from manifest: `ASSET=$(docker compose exec frontend cat /srv/built-assets/manifest.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('vendor.js',''))")`
2. `curl -sI -H "Accept-Encoding: gzip" "http://localhost:3000/assets/${ASSET}"`
3. **Expected:** Response includes `Content-Encoding: gzip` — nginx serves the `.gz` sibling file from disk, not compressing on the fly.

### 2. Hashed assets: immutable cache header

1. Same asset URL as test 1
2. `curl -sI "http://localhost:3000/assets/${ASSET}"`
3. **Expected:** `Cache-Control: public, max-age=31536000, immutable` — browser caches for 1 year, never revalidates.

### 3. Proxied HTML: gzip compression

1. `curl -s -H "Accept-Encoding: gzip" -o /dev/null -D - -L http://localhost:3000/browser/`
2. **Expected:** At least one response in the redirect chain shows `Content-Encoding: gzip`. The `/browser/` path redirects to `/login.html` (unauthenticated) which is compressed.

### 4. Auth pages: ETag present

1. `curl -sI http://localhost:3000/login.html`
2. **Expected:** `ETag` header present with a quoted hash value (e.g., `"69ace645-947"`).

### 5. Auth pages: no-cache header

1. `curl -sI http://localhost:3000/login.html`
2. **Expected:** `Cache-Control: no-cache` — browser revalidates every time.

### 6. Auth pages: conditional GET returns 304

1. Get ETag: `ETAG=$(curl -sI http://localhost:3000/login.html | grep -i ETag | awk '{print $2}' | tr -d '\r')`
2. `curl -sI -H "If-None-Match: ${ETAG}" http://localhost:3000/login.html`
3. **Expected:** `HTTP/1.1 304 Not Modified` — no response body transferred, saving bandwidth on repeat visits.

### 7. Dev files: no-store preserved

1. `curl -sI http://localhost:3000/js/workspace.js`
2. **Expected:** `Cache-Control: no-store, no-cache, must-revalidate` — dev files never cached.

### 8. Config syntax valid

1. `docker compose exec frontend nginx -t`
2. **Expected:** `nginx: configuration file /etc/nginx/nginx.conf syntax is ok`

## Edge Cases

### All three auth pages have consistent headers

1. `curl -sI http://localhost:3000/setup.html | grep Cache-Control`
2. `curl -sI http://localhost:3000/login.html | grep Cache-Control`
3. `curl -sI http://localhost:3000/invite.html | grep Cache-Control`
4. **Expected:** All three return `Cache-Control: no-cache`.

### CSS dev files unchanged

1. `curl -sI http://localhost:3000/css/workspace.css | grep Cache-Control`
2. **Expected:** `Cache-Control: no-store, no-cache, must-revalidate` — CSS dev files not affected by gzip/cache changes.

### Non-gzip client gets uncompressed response

1. `curl -sI http://localhost:3000/login.html` (no Accept-Encoding header)
2. **Expected:** No `Content-Encoding: gzip` header — response is uncompressed.

## Failure Signals

- Missing `Content-Encoding: gzip` on `/assets/` requests → `gzip_static` can't find `.gz` siblings (S01 build issue or volume mount issue)
- Missing `Content-Encoding: gzip` on proxied HTML → `gzip_proxied` not set to `any`, or response under `gzip_min_length` (256 bytes)
- `nginx -t` failure → syntax error in config, check error output for line number
- 304 not returned → `etag` directive might be disabled or overridden
- `Cache-Control` missing entirely → `add_header` not in the correct location block

## Requirements Proved By This UAT

- PERF-04 (gzip compression) — tests 1, 3 prove static and dynamic gzip
- PERF-05 (HTTP caching) — tests 2, 4, 5, 6 prove immutable + conditional GET caching

## Not Proven By This UAT

- Lighthouse score impact — deferred to S05 which runs full Lighthouse measurements
- Browser cache behavior in real browsers — curl simulates but doesn't prove browser cache hit behavior
- Demo config (`nginx.demo.conf`) — verified by code review (identical directives) but not curl-tested since the demo stack isn't running

## Notes for Tester

- Must use the main `docker-compose.yml` stack, not `docker-compose.test.yml` — the test stack uses plain nginx:stable-alpine without built assets.
- The asset filename in test 1 changes on every build (content hash). Always read it from `manifest.json`.
- If the main tree stack is occupied, stop it first and start the M029 worktree's stack. Port 3000 can only be used by one stack at a time.
