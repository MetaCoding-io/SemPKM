---
estimated_steps: 5
estimated_files: 7
skills_used: []
---

# T03: Caddy cloud profile, local TLS profile, and infrastructure files

**Slice:** S07 — Deployment & Onboarding Overhaul
**Milestone:** M033

## Description

Create the Docker Compose infrastructure for cloud deployment (Caddy replacing nginx with automatic HTTPS) and local TLS testing (mkcert certificates). This task is independent of the backend/frontend work in T01/T02 — it's pure infrastructure.

The cloud Caddyfile must replicate all nginx.conf location blocks: static file serving (`/css/`, `/js/`, `/assets/`), auth pages, SSE streaming paths (with `flush_interval -1`), WebDAV proxy, Obsidian upload/scan, and the catch-all reverse proxy to FastAPI. The compose override replaces the `frontend` service entirely.

## Steps

1. **Create `Caddyfile.cloud`** — production Caddy config template:
   - Domain from env: `{$SEMPKM_DOMAIN:localhost}`
   - Static file serving:
     - `/assets/*` from `/srv/built-assets/` with immutable cache headers
     - `/css/*` from `/srv/static/css/` with no-cache headers
     - `/js/*` from `/srv/static/js/` with no-cache headers
   - Auth pages: `/setup.html`, `/login.html`, `/invite.html` from `/srv/static/` with no-cache
   - SSE streaming paths (must have `flush_interval -1` on reverse_proxy — equivalent to nginx `proxy_buffering off`):
     - `/browser/llm/chat/stream`
     - `/api/lint/stream`
     - Obsidian scan stream: `/browser/import/scan/*/stream` (path matcher)
   - Obsidian upload: `/browser/import/upload` — no body size limit
   - WebDAV: `/dav/*` — reverse proxy to `api:8000` (Caddy forwards Authorization header by default, no special config needed)
   - CORS: handled by FastAPI `CORSMiddleware` — no Caddy-level CORS headers needed
   - Well-known: `/.well-known/sempkm` — reverse proxy to `api:8000` (no special handling needed, catch-all covers it)
   - Catch-all: `reverse_proxy api:8000`
   - `encode gzip`
   - `merge_slashes` is not needed — Caddy does not merge slashes by default

2. **Create `docker-compose.cloud.yml`** — compose override file:
   - Redefines the `frontend` service as `caddy:2-alpine`
   - Ports: `443:443`, `80:80` (Caddy auto-redirects HTTP→HTTPS)
   - Volumes: `./Caddyfile.cloud:/etc/caddy/Caddyfile`, `caddy_data:/data`, `caddy_config:/config`, `./frontend/static:/srv/static:ro`, `frontend_assets:/srv/built-assets:ro`
   - `depends_on: api: condition: service_healthy`
   - `networks: [sempkm]`
   - Additional volumes: `caddy_data`, `caddy_config`
   - Environment: `SEMPKM_DOMAIN: ${SEMPKM_DOMAIN:-localhost}` passed to Caddy via env

3. **Create `.env.cloud.example`** with documented variables:
   ```
   SEMPKM_DOMAIN=sempkm.example.com
   BASE_NAMESPACE=https://sempkm.example.com/data/
   APP_BASE_URL=https://sempkm.example.com
   COOKIE_SECURE=true
   ```

4. **Create local TLS infrastructure**:
   - `Caddyfile.local-tls` — `localhost` with `tls /etc/caddy/certs/local.pem /etc/caddy/certs/local-key.pem`, same routing as cloud Caddyfile but simplified (no domain template)
   - `docker-compose.local-tls.yml` — override that replaces frontend with Caddy, mounts `./certs:/etc/caddy/certs:ro`, ports 443+80

5. **Rename and update existing files**:
   - Rename `Caddyfile` → `Caddyfile.demo` (the existing host-level Caddy config for the demo instance)
   - Add `certs/` to `.gitignore` (mkcert private keys must never be committed)

## Must-Haves

- [ ] `Caddyfile.cloud` replicates all nginx.conf location equivalents
- [ ] SSE paths use `flush_interval -1` for streaming
- [ ] `docker-compose.cloud.yml` merges cleanly with `docker-compose.yml`
- [ ] `.env.cloud.example` documents all required cloud variables
- [ ] `Caddyfile.local-tls` uses mkcert cert paths
- [ ] `docker-compose.local-tls.yml` mounts certs directory
- [ ] `certs/` is in `.gitignore`
- [ ] `Caddyfile` renamed to `Caddyfile.demo`

## Verification

- `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet` — exits 0 (merged compose is valid)
- `test -f Caddyfile.cloud && test -f docker-compose.cloud.yml && test -f .env.cloud.example` — cloud files exist
- `test -f Caddyfile.local-tls && test -f docker-compose.local-tls.yml` — local TLS files exist
- `test -f Caddyfile.demo && ! test -f Caddyfile` — rename completed
- `grep -q "certs/" .gitignore` — certs directory gitignored
- `grep -q "flush_interval" Caddyfile.cloud` — SSE streaming configured
- `grep -q "SEMPKM_DOMAIN" Caddyfile.cloud .env.cloud.example` — domain variable referenced

## Inputs

- `frontend/nginx.conf` — reference for all location blocks that must be replicated in Caddy
- `docker-compose.yml` — base compose file that the override extends
- `docker-compose.demo.yml` — reference for compose override pattern
- `Caddyfile` — existing demo Caddy config to rename

## Expected Output

- `Caddyfile.cloud` — production Caddy config template with domain variable
- `docker-compose.cloud.yml` — compose override replacing nginx with Caddy
- `.env.cloud.example` — example cloud environment variables
- `Caddyfile.local-tls` — localhost Caddy config with mkcert cert paths
- `docker-compose.local-tls.yml` — local TLS compose override
- `Caddyfile.demo` — renamed from `Caddyfile`
- `.gitignore` — updated with `certs/` entry

## Observability Impact

- **Compose validation**: `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet` should exit 0 — confirms the cloud profile merges cleanly with the base stack
- **Caddy startup**: When running the cloud stack, Caddy logs certificate provisioning status to stdout. If SEMPKM_DOMAIN is invalid or DNS not configured, Caddy logs a clear ACME error (visible via `docker compose logs frontend`)
- **Local TLS**: Missing `certs/` directory causes Caddy to fail with "open /etc/caddy/certs/local.pem: no such file or directory" — tells the user to run mkcert
- **Infrastructure file presence**: `test -f Caddyfile.cloud && test -f docker-compose.cloud.yml` — files exist check is the primary signal for deployment readiness
- **No runtime signals**: This task is pure infrastructure (static config files). No application-level logging or API endpoints are affected
