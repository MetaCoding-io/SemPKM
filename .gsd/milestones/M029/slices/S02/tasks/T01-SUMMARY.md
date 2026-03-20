---
id: T01
parent: S02
milestone: M029
provides:
  - gzip compression for all response types (static, proxied)
  - immutable cache headers on content-hashed assets
  - no-cache with ETag support on auth HTML pages
  - /assets/ location block in nginx.demo.conf
key_files:
  - frontend/nginx.conf
  - frontend/nginx.demo.conf
key_decisions:
  - gzip_comp_level 6 — good compression/CPU tradeoff for dynamic responses
  - gzip_min_length 256 — avoids compressing tiny API responses where overhead exceeds savings
patterns_established:
  - Three-tier cache strategy: immutable for hashed assets, no-cache for auth HTML, no-store for dev assets
observability_surfaces:
  - "curl -sI -H 'Accept-Encoding: gzip' http://localhost:3000/assets/<hash>.min.js — check Content-Encoding and Cache-Control"
  - "curl -sI http://localhost:3000/login.html — check ETag and Cache-Control: no-cache"
  - "docker compose exec frontend nginx -t — config syntax validation"
  - "docker compose exec frontend nginx -T — dump full resolved config"
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Add gzip compression and cache headers to nginx configs

**Added gzip compression (static + dynamic) and three-tier cache headers to both nginx.conf and nginx.demo.conf**

## What Happened

Applied three categories of nginx configuration to both `nginx.conf` and `nginx.demo.conf`:

1. **Server-level gzip block** — `gzip on; gzip_proxied any;` with level 6 compression for text/css/js/json/xml/svg MIME types, 256-byte minimum length. This compresses all proxied FastAPI responses on the fly.

2. **`/assets/` block updates** — Added `gzip_static on` (serves S01's pre-built `.gz` siblings at zero CPU cost) and `Cache-Control: public, max-age=31536000, immutable` (safe because filenames contain content hashes). The demo config was missing the entire `/assets/` block from S01 — added it with all directives.

3. **Auth page cache headers** — Added `Cache-Control: no-cache` to `/setup.html`, `/login.html`, and `/invite.html` blocks. Combined with nginx's default ETag generation, this enables conditional GET (304 Not Modified) while ensuring browsers always revalidate.

Dev-mode `/css/` and `/js/` blocks remain unchanged with `no-store, no-cache, must-revalidate`.

## Verification

All 9 curl checks pass against the running Docker stack:

- `nginx -t` — syntax OK
- Hashed asset (`vendor-58e5bf86.min.js`) returns `Content-Encoding: gzip` and `Cache-Control: public, max-age=31536000, immutable`
- Login page returns `Content-Encoding: gzip` when accessed with `Accept-Encoding: gzip`
- Login page returns `ETag` and `Cache-Control: no-cache`
- Conditional GET with `If-None-Match: <etag>` returns `304 Not Modified`
- Dev JS (`workspace.js`) still returns `Cache-Control: no-store, no-cache, must-revalidate`
- Dev CSS (`workspace.css`) still returns `Cache-Control: no-store, no-cache, must-revalidate`
- All three auth pages (setup, login, invite) return `Cache-Control: no-cache`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose exec frontend nginx -t` | 0 | ✅ pass | <1s |
| 2 | `curl -H "Accept-Encoding: gzip" -sI .../assets/vendor-58e5bf86.min.js \| grep Content-Encoding` | 0 | ✅ pass | <1s |
| 3 | `curl -H "Accept-Encoding: gzip" -sI .../assets/vendor-58e5bf86.min.js \| grep immutable` | 0 | ✅ pass | <1s |
| 4 | `curl -s -H "Accept-Encoding: gzip" -L .../browser/ \| grep Content-Encoding` | 0 | ✅ pass | <1s |
| 5 | `curl -sI .../login.html \| grep ETag` | 0 | ✅ pass | <1s |
| 6 | `curl -sI .../login.html \| grep 'Cache-Control: no-cache'` | 0 | ✅ pass | <1s |
| 7 | `curl -sI -H "If-None-Match: <etag>" .../login.html \| grep 304` | 0 | ✅ pass | <1s |
| 8 | `curl -sI .../js/workspace.js \| grep no-store` | 0 | ✅ pass | <1s |
| 9 | `curl -sI .../setup.html \| grep no-cache` + invite.html | 0 | ✅ pass | <1s |

## Diagnostics

- `curl -sI -H "Accept-Encoding: gzip" http://localhost:3000/<path>` — inspect Content-Encoding and Cache-Control per path
- `docker compose exec frontend nginx -T` — dump full resolved config to verify directives are active
- `docker compose logs frontend` — access/error logs for debugging
- Missing `Content-Encoding: gzip` on `/assets/` → `.gz` files not present (S01 build issue)
- Missing `Content-Encoding: gzip` on proxied HTML → response under 256 bytes or MIME type not in gzip_types list

## Deviations

- Proxied HTML gzip check (`/browser/`) required following the 302→`/login.html` redirect because the API requires authentication. The gzip compression is confirmed working on the static auth page served through the gzip module. Server-level `gzip on; gzip_proxied any;` is correctly configured for authenticated proxied responses.

## Known Issues

None.

## Files Created/Modified

- `frontend/nginx.conf` — Added server-level gzip block, `gzip_static on` + immutable cache header on `/assets/`, `Cache-Control: no-cache` on three auth page blocks
- `frontend/nginx.demo.conf` — Identical changes plus new `/assets/` location block (was missing from S01)
