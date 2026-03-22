---
id: T03
parent: S07
milestone: M033
provides:
  - Caddyfile.cloud with domain template, static serving, SSE streaming, WebDAV proxy
  - docker-compose.cloud.yml replacing nginx with Caddy for cloud deployments
  - .env.cloud.example with documented cloud deployment variables
  - Caddyfile.local-tls with mkcert certificate paths for local HTTPS testing
  - docker-compose.local-tls.yml compose override for local TLS
  - Caddyfile.demo (renamed from existing Caddyfile)
key_files:
  - Caddyfile.cloud
  - docker-compose.cloud.yml
  - .env.cloud.example
  - Caddyfile.local-tls
  - docker-compose.local-tls.yml
  - Caddyfile.demo
  - .gitignore
key_decisions:
  - Caddy handle directives replicate all nginx location blocks rather than using route — handle evaluates in order of specificity by default, matching nginx's "most specific location wins" behavior
  - request_body max_size 0 used for Obsidian upload (Caddy's equivalent of nginx client_max_body_size 0)
  - CORS headers not duplicated in Caddy — FastAPI CORSMiddleware handles them, no proxy-level CORS needed (nginx had redundant CORS due to its CORS preflight handling)
patterns_established:
  - Compose override pattern for deployment profiles — override only the frontend service, add profile-specific volumes, keep API/triplestore services unchanged
  - .env.cloud.example exception added to .gitignore alongside existing .env.example exception
observability_surfaces:
  - Compose validation via docker compose config --quiet (exit 0 = valid merge)
  - Caddy ACME errors visible via docker compose logs frontend when domain/DNS is misconfigured
  - Missing certs/ directory causes clear Caddy startup error pointing to mkcert setup
duration: 12m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T03: Caddy cloud profile, local TLS profile, and infrastructure files

**Created Caddyfile.cloud, docker-compose.cloud.yml, local TLS profile, .env.cloud.example, and renamed existing Caddyfile to Caddyfile.demo**

## What Happened

Created `Caddyfile.cloud` translating all nginx.conf location blocks to Caddy `handle` directives. Static assets (/assets/, /css/, /js/) serve from /srv/built-assets and /srv/static with appropriate cache headers. Auth pages (setup.html, login.html, invite.html) serve with no-cache. Three SSE streaming paths use `flush_interval -1` (Caddy's equivalent of nginx proxy_buffering off). Obsidian upload uses `request_body { max_size 0 }` for unlimited body size. WebDAV and catch-all reverse proxy to api:8000. The domain is templated via `{$SEMPKM_DOMAIN:localhost}` environment variable with localhost fallback.

Created `docker-compose.cloud.yml` as a compose override that replaces the nginx frontend service with `caddy:2-alpine`. Mounts the Caddyfile, Caddy persistent data volumes, and the same static/built-asset volumes the nginx service used. Exposes ports 443+80 for HTTPS with automatic HTTP→HTTPS redirect. Passes SEMPKM_DOMAIN through as an environment variable.

Created `.env.cloud.example` documenting all required cloud variables (SEMPKM_DOMAIN, BASE_NAMESPACE, APP_BASE_URL, COOKIE_SECURE) and optional SMTP configuration. Added `!.env.cloud.example` exception to `.gitignore` since the existing `.env.*` pattern would have excluded it.

Created `Caddyfile.local-tls` — same routing structure as cloud but for localhost with explicit `tls` directive pointing to mkcert certificate paths (/etc/caddy/certs/local.pem). Created matching `docker-compose.local-tls.yml` override that mounts the local `./certs` directory.

Renamed existing `Caddyfile` to `Caddyfile.demo` — the host-level reverse proxy config for the demo instance. Added `certs/` to `.gitignore` to prevent mkcert private keys from being committed.

## Verification

All 7 task-level checks pass: cloud files exist, local TLS files exist, rename completed, certs gitignored, flush_interval present, SEMPKM_DOMAIN referenced, compose merge validates.

Slice-level checks: 26/26 unit tests pass, compose merge validates, infrastructure files exist, local TLS files exist, certs gitignored, namespace guard test passes. The `cloud-deployment` grep returns 0 as expected — that's T04's documentation task.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet` | 0 | ✅ pass | <0.5s |
| 2 | `test -f Caddyfile.cloud && test -f docker-compose.cloud.yml && test -f .env.cloud.example` | 0 | ✅ pass | <0.1s |
| 3 | `test -f Caddyfile.local-tls && test -f docker-compose.local-tls.yml` | 0 | ✅ pass | <0.1s |
| 4 | `test -f Caddyfile.demo && ! test -f Caddyfile` | 0 | ✅ pass | <0.1s |
| 5 | `grep -q "certs/" .gitignore` | 0 | ✅ pass | <0.1s |
| 6 | `grep -q "flush_interval" Caddyfile.cloud` | 0 | ✅ pass | <0.1s |
| 7 | `grep -q "SEMPKM_DOMAIN" Caddyfile.cloud .env.cloud.example` | 0 | ✅ pass | <0.1s |
| 8 | `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v` | 0 | ✅ pass | 0.57s |
| 9 | `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_namespace_guard_409_when_data_exists -v` | 0 | ✅ pass | 0.45s |
| 10 | `docker compose -f docker-compose.yml -f docker-compose.local-tls.yml config --quiet` | 0 | ✅ pass | <0.5s |

## Diagnostics

- **Compose validation**: `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet` — exit 0 confirms valid merge
- **Caddy startup**: When running the cloud stack, Caddy logs ACME certificate provisioning to stdout. Check `docker compose -f docker-compose.yml -f docker-compose.cloud.yml logs frontend` for errors
- **Local TLS**: Missing `certs/` directory produces a clear Caddy error pointing the user to run mkcert
- **File presence**: `ls Caddyfile.cloud docker-compose.cloud.yml .env.cloud.example Caddyfile.local-tls docker-compose.local-tls.yml Caddyfile.demo` confirms all infrastructure files

## Deviations

- Added `!.env.cloud.example` exception to `.gitignore` — not in the plan but necessary because the existing `.env.*` pattern would have excluded the example file from git tracking.
- Also validated the local TLS compose merge (`docker compose -f docker-compose.yml -f docker-compose.local-tls.yml config --quiet`) — not explicitly required but confirms both profiles work.

## Known Issues

None.

## Files Created/Modified

- `Caddyfile.cloud` — new: production Caddy config with domain template, all nginx.conf location equivalents, SSE streaming, WebDAV, gzip
- `docker-compose.cloud.yml` — new: compose override replacing nginx with Caddy, adds caddy_data/caddy_config volumes, ports 443+80
- `.env.cloud.example` — new: documented cloud deployment environment variables
- `Caddyfile.local-tls` — new: localhost Caddy config with mkcert cert paths
- `docker-compose.local-tls.yml` — new: local TLS compose override mounting certs directory
- `Caddyfile.demo` — renamed from `Caddyfile` (existing demo instance reverse proxy)
- `.gitignore` — added `certs/` entry and `!.env.cloud.example` exception
- `.gsd/milestones/M033/slices/S07/tasks/T03-PLAN.md` — added Observability Impact section per pre-flight check
