---
estimated_steps: 6
estimated_files: 2
---

# T01: Add gzip compression and cache headers to nginx configs

**Slice:** S02 — Compression & HTTP Caching
**Milestone:** M029

## Description

Add gzip compression and HTTP cache headers to both `frontend/nginx.conf` and `frontend/nginx.demo.conf`. This is the entire slice scope — there are no backend code changes, no build pipeline changes, and no new libraries. The work is purely additive nginx configuration.

Three categories of responses need different treatment:
1. **Content-hashed assets (`/assets/`):** `gzip_static on` (serves pre-built .gz files from S01) + `Cache-Control: public, max-age=31536000, immutable` (safe because filenames change on content change)
2. **Auth HTML pages:** `Cache-Control: no-cache` (tells browsers to revalidate via ETag, which nginx generates automatically for static files)
3. **Proxied HTML from FastAPI:** Server-level `gzip on` with `gzip_proxied any` compresses these responses on the fly

Important: `nginx.demo.conf` is missing the `/assets/` location block entirely — S01 only added it to `nginx.conf`. This task must add it to the demo config too, with all the same directives.

## Steps

1. **Add server-level gzip block to `nginx.conf`** — Insert after the `merge_slashes off;` line and before the first `location` block:
   ```nginx
   # Compression for dynamic (proxied) responses
   gzip on;
   gzip_vary on;
   gzip_proxied any;
   gzip_comp_level 6;
   gzip_min_length 256;
   gzip_types
       text/plain
       text/css
       text/javascript
       application/javascript
       application/json
       application/xml
       image/svg+xml
       text/xml;
   ```

2. **Update the `/assets/` block in `nginx.conf`** — Add `gzip_static on;` and the immutable cache header. The block should become:
   ```nginx
   location /assets/ {
       alias /srv/built-assets/;
       gzip_static on;
       add_header Cache-Control "public, max-age=31536000, immutable";
       try_files $uri =404;
   }
   ```

3. **Add `Cache-Control: no-cache` to auth page blocks in `nginx.conf`** — Update each of the three auth page location blocks (`/setup.html`, `/login.html`, `/invite.html`) to include:
   ```nginx
   add_header Cache-Control "no-cache";
   ```
   Place it before the `try_files` directive. nginx's built-in ETag generation is on by default for static files — no explicit `etag on;` needed.

4. **Mirror all changes to `nginx.demo.conf`** — Apply the identical gzip server-level block. Add the full `/assets/` block (it's missing entirely in demo config — copy from nginx.conf with the gzip_static and cache-control directives). Add `Cache-Control: no-cache` to the three auth page blocks. The demo config must be identical to nginx.conf except for the read-only enforcement block at the top.

5. **Rebuild and restart the frontend container:**
   ```bash
   docker compose build frontend
   docker compose up -d frontend
   docker compose exec frontend nginx -t
   ```

6. **Run all verification curl checks** against `http://localhost:3000`:
   - Hashed asset returns `Content-Encoding: gzip` (need to resolve actual filename from manifest first: `docker compose exec frontend cat /srv/built-assets/manifest.json | python3 -c "import sys,json; m=json.load(sys.stdin); print(m.get('vendor.js',''))"`)
   - Hashed asset returns `Cache-Control: public, max-age=31536000, immutable`
   - Proxied HTML (`/browser/`) returns `Content-Encoding: gzip`
   - Auth page (`/login.html`) returns `ETag` header
   - Auth page returns `Cache-Control: no-cache`
   - Auth page conditional GET with `If-None-Match` returns `304 Not Modified`
   - Dev-mode JS (`/js/workspace.js`) still returns `no-store, no-cache`
   - `nginx -t` reports syntax OK

## Must-Haves

- [ ] Server-level gzip directives with `gzip_proxied any` in both config files
- [ ] `gzip_static on` in `/assets/` block (serves S01's pre-built .gz siblings at zero CPU cost)
- [ ] `Cache-Control: public, max-age=31536000, immutable` on `/assets/` responses
- [ ] `Cache-Control: no-cache` on auth HTML pages (login, setup, invite)
- [ ] `/assets/` block added to `nginx.demo.conf` (missing from S01)
- [ ] Dev-mode `/css/` and `/js/` cache headers unchanged
- [ ] `nginx -t` passes in container

## Verification

- `docker compose exec frontend nginx -t` — syntax OK
- `curl -H "Accept-Encoding: gzip" -sI http://localhost:3000/assets/<VENDOR_HASH>.min.js` shows `Content-Encoding: gzip` and `Cache-Control: public, max-age=31536000, immutable`
- `curl -H "Accept-Encoding: gzip" -sI http://localhost:3000/browser/` shows `Content-Encoding: gzip`
- `curl -sI http://localhost:3000/login.html` shows `ETag:` and `Cache-Control: no-cache`
- Conditional GET: extract ETag value, send `curl -sI -H "If-None-Match: <etag>" http://localhost:3000/login.html`, confirm `304 Not Modified`
- `curl -sI http://localhost:3000/js/workspace.js | grep Cache-Control` shows `no-store, no-cache, must-revalidate` (unchanged)

## Observability Impact

**What changes:**
- `/assets/` responses gain `Content-Encoding: gzip` (from `gzip_static on` serving `.gz` siblings) and `Cache-Control: public, max-age=31536000, immutable`
- Auth pages (`/login.html`, `/setup.html`, `/invite.html`) gain `Cache-Control: no-cache` header; ETag was already present (nginx default for static files)
- Proxied HTML responses (e.g. `/browser/`) gain `Content-Encoding: gzip` and `Vary: Accept-Encoding`
- Dev-mode `/css/` and `/js/` responses remain unchanged (`no-store, no-cache, must-revalidate`)

**How to inspect:**
- `curl -sI -H "Accept-Encoding: gzip" http://localhost:3000/<path>` — check `Content-Encoding` and `Cache-Control` headers
- `docker compose exec frontend nginx -T` — dump full resolved config
- Browser DevTools → Network tab → select request → Headers tab

**Failure signals:**
- Missing `Content-Encoding: gzip` on `/assets/` → `.gz` files not present in `/srv/built-assets/` (S01 build issue)
- Missing `Cache-Control` header → `add_header` directive missing or overridden by parent block
- `nginx -t` failure → config syntax error (line number in stderr)

## Inputs

- `frontend/nginx.conf` — current config with `/assets/` block (from S01), no gzip directives, no cache headers
- `frontend/nginx.demo.conf` — current demo config MISSING the `/assets/` block entirely
- S01 build pipeline generates `.gz` pre-compressed siblings for all files in `frontend/dist/` — these are what `gzip_static on` will serve

## Expected Output

- `frontend/nginx.conf` — updated with gzip server block, gzip_static + immutable on /assets/, no-cache on auth pages
- `frontend/nginx.demo.conf` — updated identically (including the new /assets/ block)
- All 8 curl verification checks passing against running Docker stack
