---
estimated_steps: 5
estimated_files: 6
skills_used:
  - best-practices
---

# T03: Cloud deployment infrastructure (Caddy compose + Caddyfile)

**Slice:** S01 — Deployment & Onboarding Overhaul
**Milestone:** M033

## Description

Create the infrastructure files for one-command cloud deployment with Caddy auto-TLS. This includes a Docker Compose override file, a Caddy configuration template, and an example environment file. Also renames the existing demo Caddyfile to avoid confusion and updates .gitignore.

Design reference: `.gsd/design/DEPLOYMENT-AND-ONBOARDING-DESIGN.md` section 4 (Caddy Cloud Profile).

## Steps

1. **Create `docker-compose.cloud.yml`:**
   - Compose override that replaces the nginx `frontend` service with Caddy
   - Image: `caddy:2-alpine`
   - Ports: `443:443` and `80:80` (Caddy auto-redirects HTTP→HTTPS)
   - Volumes: `./Caddyfile.cloud:/etc/caddy/Caddyfile`, `caddy_data:/data`, `caddy_config:/config`, `./frontend/static:/srv/static:ro`, `frontend_assets:/srv/built-assets:ro`
   - Depends on: `api` (service_healthy)
   - Network: `sempkm`
   - Add `caddy_data` and `caddy_config` volumes
   - Usage: `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up`

2. **Create `Caddyfile.cloud`:**
   - Domain from env: `{$SEMPKM_DOMAIN:localhost}` (defaults to localhost for safety)
   - Static file handling: `/css/*` and `/js/*` from `/srv/static/`, `/assets/*` from `/srv/built-assets/`
   - Auth pages: `/setup.html`, `/login.html`, `/invite.html` from `/srv/static/` with no-cache headers
   - SSE endpoints need `flush_interval -1` for streaming: `/browser/llm/chat/stream`, `/api/lint/stream`
   - WebDAV: `/dav/*` reverse_proxy to `api:8000` with extended timeouts
   - Obsidian upload: `/browser/import/upload` with no request body limit
   - API and catch-all: `reverse_proxy api:8000`
   - Compression: `encode gzip`
   - Note: Caddy does NOT merge slashes by default — correct behavior, no special config needed

3. **Create `.env.cloud.example`:**
   - `SEMPKM_DOMAIN=sempkm.example.com` (required — your domain)
   - `BASE_NAMESPACE=https://sempkm.example.com/data/` (set by setup wizard, or manually)
   - `APP_BASE_URL=https://sempkm.example.com`
   - `COOKIE_SECURE=true`
   - `SECRET_KEY=` (auto-generated on first run)
   - Optional SMTP block (commented out)
   - `CORS_ORIGINS=https://sempkm.example.com` (if needed for extension)
   - Comments explaining each variable

4. **Rename demo Caddyfile:**
   - `git mv Caddyfile Caddyfile.demo`
   - Update `docker-compose.demo.yml` if it references `Caddyfile` (check first — the demo compose may mount it or the demo may use a host-level Caddy, not Docker Caddy)

5. **Update `.gitignore`:**
   - Add `certs/` for future mkcert support
   - Add `data/.instance-config.json` (contains instance ID, should not be committed — lives on Docker volume anyway)

## Must-Haves

- [ ] `docker-compose.cloud.yml` validates with `docker compose config --quiet`
- [ ] `Caddyfile.cloud` covers all proxy routes from current `nginx.conf` (API, SSE, WebDAV, uploads, static)
- [ ] `.env.cloud.example` documents all required cloud variables
- [ ] Existing demo Caddyfile renamed to `Caddyfile.demo`
- [ ] `certs/` in .gitignore

## Verification

- `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet` exits 0 (valid compose syntax)
- `test -f Caddyfile.cloud` — Caddy config exists
- `test -f .env.cloud.example` — example env exists
- `test -f Caddyfile.demo` — demo Caddyfile renamed
- `test ! -f Caddyfile` — old Caddyfile gone (renamed)
- `grep -q "certs/" .gitignore` — gitignore updated
- `grep -q "SEMPKM_DOMAIN" Caddyfile.cloud` — domain variable used
- `grep -q "reverse_proxy" Caddyfile.cloud` — API proxy configured

## Inputs

- `docker-compose.yml` — base compose file that the cloud override extends
- `frontend/nginx.conf` — all proxy routes to replicate in Caddyfile.cloud
- `Caddyfile` — existing demo Caddyfile to rename
- `docker-compose.demo.yml` — may reference Caddyfile, needs checking
- `.gitignore` — existing gitignore to extend

## Expected Output

- `docker-compose.cloud.yml` — new cloud compose override
- `Caddyfile.cloud` — new Caddy configuration for cloud deployment
- `.env.cloud.example` — new example environment file
- `Caddyfile.demo` — renamed from Caddyfile
- `docker-compose.demo.yml` — possibly updated if it referenced Caddyfile
- `.gitignore` — updated with certs/ entry
