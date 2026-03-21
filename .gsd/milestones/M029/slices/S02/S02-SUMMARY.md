---
id: S02
parent: M029
milestone: M029
provides:
  - gzip compression for all response types (static assets via gzip_static, proxied HTML via gzip_proxied any)
  - immutable cache headers (max-age=31536000) on content-hashed /assets/ files
  - no-cache with ETag conditional GET (304) on auth HTML pages
  - /assets/ location block added to nginx.demo.conf (was missing from S01)
  - three-tier cache strategy pattern for the project
requires:
  - slice: S01
    provides: content-hashed assets in /srv/built-assets/ with .gz siblings, manifest.json, /assets/ location block in nginx.conf
affects:
  - S05
key_files:
  - frontend/nginx.conf
  - frontend/nginx.demo.conf
key_decisions:
  - gzip_comp_level 6 — good compression/CPU tradeoff for dynamic responses
  - gzip_min_length 256 — avoids compressing tiny API responses where overhead exceeds savings
  - Three-tier cache strategy: immutable for hashed assets, no-cache for auth HTML, no-store for dev assets
patterns_established:
  - Three-tier cache strategy covers all response categories in the app
  - gzip_static on for pre-compressed assets (zero CPU cost), gzip_proxied any for dynamic responses
  - Auth pages use no-cache + ETag for conditional GET, not no-store (allows 304 Not Modified)
observability_surfaces:
  - "curl -sI -H 'Accept-Encoding: gzip' http://localhost:3000/assets/<hash>.min.js — check Content-Encoding and Cache-Control"
  - "curl -sI http://localhost:3000/login.html — check ETag and Cache-Control: no-cache"
  - "docker compose exec frontend nginx -t — config syntax validation"
  - "docker compose exec frontend nginx -T — dump full resolved config"
drill_down_paths:
  - .gsd/milestones/M029/slices/S02/tasks/T01-SUMMARY.md
duration: 30m
verification_result: passed
completed_at: 2026-03-20
---

# S02: Compression & HTTP Caching

**nginx serves gzip-compressed responses with correct three-tier cache headers — immutable for hashed assets, no-cache with ETag for auth HTML, no-store for dev files.**

## What Happened

Single task (T01) applied gzip compression and cache headers to both `nginx.conf` and `nginx.demo.conf`:

1. **Server-level gzip** — `gzip on; gzip_proxied any; gzip_comp_level 6; gzip_min_length 256` with a comprehensive MIME type list (text/css, application/javascript, application/json, image/svg+xml, etc.). This compresses all proxied FastAPI HTML responses on the fly.

2. **`/assets/` block** — `gzip_static on` serves S01's pre-built `.gz` sibling files at zero CPU cost. `Cache-Control: public, max-age=31536000, immutable` is safe because all filenames contain content hashes. The demo config (`nginx.demo.conf`) was missing the entire `/assets/` block from S01 — this slice added it.

3. **Auth page caching** — `Cache-Control: no-cache` on `/setup.html`, `/login.html`, and `/invite.html`. Combined with nginx's default ETag generation, this enables conditional GET (304 Not Modified) while ensuring browsers always revalidate.

Dev-mode `/css/` and `/js/` blocks remain unchanged with `no-store, no-cache, must-revalidate`.

## Verification

All 8 curl checks from the slice plan pass against the running Docker stack:

1. ✅ `gzip_static` serves pre-compressed hashed assets (`Content-Encoding: gzip`)
2. ✅ Immutable cache header on hashed assets (`Cache-Control: public, max-age=31536000, immutable`)
3. ✅ Gzip compresses proxied/static HTML (`Content-Encoding: gzip` on `/browser/` redirect chain)
4. ✅ ETag present on auth pages
5. ✅ `Cache-Control: no-cache` on auth pages
6. ✅ Conditional GET returns 304 Not Modified when ETag matches
7. ✅ Dev JS files still return `no-store` (unchanged)
8. ✅ `nginx -t` passes (config syntax valid)

Additional checks: all three auth pages (setup, login, invite) confirmed with `Cache-Control: no-cache`.

## Requirements Advanced

- PERF-04 (gzip compression) — nginx serves gzip-compressed responses for CSS/JS/HTML (referenced in roadmap, not yet in REQUIREMENTS.md)
- PERF-05 (HTTP caching) — immutable cache headers on hashed assets, conditional GET on auth pages (referenced in roadmap, not yet in REQUIREMENTS.md)

## Requirements Validated

- none — PERF-04 and PERF-05 are not yet registered in REQUIREMENTS.md. S05 will validate them with Lighthouse measurements.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- The verification was run against the main tree's Docker stack (port 3000) instead of a worktree-specific stack (port 3901) because the worktree's fresh volumes triggered a triplestore lock race condition. The nginx configs are identical — the volume mount serves the worktree's files, and all 8 curl checks passed.
- The demo config gap (missing `/assets/` block in `nginx.demo.conf`) was a carry-over from S01 that this slice fixed.

## Known Limitations

- `gzip_proxied any` compresses all proxied responses, including small JSON API responses. The `gzip_min_length 256` threshold mitigates but doesn't eliminate overhead on tiny payloads.
- The test compose (`docker-compose.test.yml`) uses a plain `nginx:stable-alpine` image without the multi-stage build, so `/assets/` content-hashed files aren't available in that stack. Production verification requires the main `docker-compose.yml`.

## Follow-ups

- none

## Files Created/Modified

- `frontend/nginx.conf` — Added server-level gzip block, `gzip_static on` + immutable cache header on `/assets/`, `Cache-Control: no-cache` on three auth page blocks
- `frontend/nginx.demo.conf` — Identical changes plus new `/assets/` location block (was missing from S01)

## Forward Intelligence

### What the next slice should know
- The nginx config is now fully set up for S05's Lighthouse verification. All three cache tiers are active: immutable (hashed assets), no-cache (auth HTML), no-store (dev files).
- The demo config (`nginx.demo.conf`) is now in sync with `nginx.conf` for all `/assets/`, gzip, and cache directives.

### What's fragile
- The test compose stack (`docker-compose.test.yml`) doesn't build the frontend Docker image, so it has no `/assets/` or `/srv/built-assets/`. Any test that needs to verify compression or caching of hashed assets must use the main `docker-compose.yml`.

### Authoritative diagnostics
- `curl -sI -H "Accept-Encoding: gzip" http://localhost:3000/assets/<asset>` — the definitive check for gzip + cache headers on production assets
- `docker compose exec frontend nginx -T` — dumps the full resolved nginx config for inspection

### What assumptions changed
- Original plan assumed both nginx configs were in sync from S01. In reality, `nginx.demo.conf` was missing the `/assets/` block entirely — this slice fixed it.
