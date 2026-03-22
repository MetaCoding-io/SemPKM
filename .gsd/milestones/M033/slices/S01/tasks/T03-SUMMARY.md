---
id: T03
parent: S01
milestone: M033
provides:
  - docker-compose.cloud.yml compose override replacing nginx with Caddy for cloud deployments
  - Caddyfile.cloud with all nginx routes translated (static, SSE, WebDAV, upload, catch-all)
  - .env.cloud.example documenting all required and optional cloud environment variables
  - Caddyfile renamed to Caddyfile.demo to avoid confusion with cloud config
  - .gitignore updated with certs/ and data/.instance-config.json exclusions
key_files:
  - docker-compose.cloud.yml
  - Caddyfile.cloud
  - .env.cloud.example
  - Caddyfile.demo
  - .gitignore
key_decisions:
  - Compose override file (not profiles) for cloud deployment — simpler invocation with explicit -f flags, no profile confusion
  - CORS handled by FastAPI CORSMiddleware only, not duplicated at Caddy layer — nginx's CORS headers were belt-and-suspenders per design doc
  - SEMPKM_DOMAIN defaults to localhost for safety — self-signed cert, no accidental ACME requests
  - .env.cloud.example added to gitignore exclusion alongside .env.example
patterns_established:
  - Caddy SSE streaming uses flush_interval -1 (equivalent to nginx proxy_buffering off)
  - Caddy handle blocks ordered most-specific-first — static files before catch-all reverse_proxy
observability_surfaces:
  - docker compose config --quiet validates merged compose without starting containers
  - Caddy logs certificate acquisition/renewal/errors to stdout (docker compose logs frontend)
  - SEMPKM_DOMAIN=localhost default produces self-signed cert — successful startup with real domain confirms DNS+ACME
duration: 10min
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: Cloud deployment infrastructure (Caddy compose + Caddyfile)

**Created docker-compose.cloud.yml override, Caddyfile.cloud with all nginx proxy routes translated, .env.cloud.example with documented variables, renamed demo Caddyfile, and updated .gitignore — all 8 task checks and 5 slice checks passing.**

## What Happened

Built the one-command cloud deployment infrastructure:

1. **`docker-compose.cloud.yml`** — Compose override that replaces the nginx `frontend` service with `caddy:2-alpine`. Exposes ports 443+80 (auto HTTP→HTTPS redirect), mounts `Caddyfile.cloud` as read-only config, adds `caddy_data` and `caddy_config` volumes for certificate storage and runtime config. Depends on `api` service_healthy.

2. **`Caddyfile.cloud`** — Complete translation of all 14 nginx location blocks. Static files (CSS, JS, built assets) served directly with appropriate cache headers. Auth pages (setup/login/invite) served with no-cache. Three SSE streaming endpoints (LLM chat, lint validation, Obsidian scan) configured with `flush_interval -1`. WebDAV with 300s extended timeouts. Obsidian upload with `max_size 0` (unlimited). Catch-all reverse_proxy to api:8000. CORS delegated to FastAPI middleware per design doc. Domain set via `{$SEMPKM_DOMAIN:localhost}` environment variable.

3. **`.env.cloud.example`** — Documents all required (SEMPKM_DOMAIN, BASE_NAMESPACE, APP_BASE_URL, COOKIE_SECURE, SECRET_KEY) and optional (SMTP, CORS, triplestore) variables with explanatory comments.

4. **`Caddyfile` → `Caddyfile.demo`** — Renamed the existing host-level demo reverse proxy config. The demo compose (`docker-compose.demo.yml`) uses `nginx.demo.conf`, not the Caddyfile, so no compose update was needed.

5. **`.gitignore`** — Added `certs/` (future mkcert support), `data/.instance-config.json` (instance-specific, not committable), and `!.env.cloud.example` exclusion so the example file is tracked.

## Verification

All 8 task-level checks pass:
- `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet` exits 0
- Caddyfile.cloud exists with SEMPKM_DOMAIN and reverse_proxy
- .env.cloud.example exists
- Caddyfile.demo exists, old Caddyfile gone
- certs/ in .gitignore

All 5 slice-level checks pass:
- 32/32 backend unit tests pass (test_instance_config.py)
- instance_configured in auth schemas, configure-instance in setup routes
- All three cloud infra files exist

Route coverage audit: all 14 nginx location blocks have corresponding Caddy handle blocks.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet` | 0 | ✅ pass | 0.5s |
| 2 | `test -f Caddyfile.cloud` | 0 | ✅ pass | <0.1s |
| 3 | `test -f .env.cloud.example` | 0 | ✅ pass | <0.1s |
| 4 | `test -f Caddyfile.demo` | 0 | ✅ pass | <0.1s |
| 5 | `test ! -f Caddyfile` | 0 | ✅ pass | <0.1s |
| 6 | `grep -q "certs/" .gitignore` | 0 | ✅ pass | <0.1s |
| 7 | `grep -q "SEMPKM_DOMAIN" Caddyfile.cloud` | 0 | ✅ pass | <0.1s |
| 8 | `grep -q "reverse_proxy" Caddyfile.cloud` | 0 | ✅ pass | <0.1s |
| 9 | `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v` | 0 | ✅ pass | 0.28s |
| 10 | `grep -q "instance_configured" backend/app/auth/schemas.py` | 0 | ✅ pass | <0.1s |
| 11 | `grep -q "configure-instance" backend/app/api/setup_routes.py` | 0 | ✅ pass | <0.1s |
| 12 | `test -f docker-compose.cloud.yml && test -f Caddyfile.cloud && test -f .env.cloud.example` | 0 | ✅ pass | <0.1s |

## Diagnostics

- **Compose validation:** `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config` shows the full merged config including volume definitions and port mappings.
- **Caddy logs:** `docker compose -f docker-compose.yml -f docker-compose.cloud.yml logs frontend` shows TLS certificate acquisition, renewal, and any ACME challenge failures.
- **Domain default:** SEMPKM_DOMAIN defaults to `localhost` which produces a self-signed cert — a working startup with a real domain confirms DNS and ACME are properly configured.
- **Route audit:** Compare `grep "handle" Caddyfile.cloud` against `grep "location" frontend/nginx.conf` to verify all routes are covered.

## Deviations

- Used filesystem `cp`+`rm` instead of `git mv` for Caddyfile rename — per Rule R06, the system handles commits and we avoid git commands in auto-mode execution.
- Demo compose (`docker-compose.demo.yml`) did not need updating — it uses `nginx.demo.conf`, not the Caddyfile. The existing Caddyfile was a host-level reverse proxy to the demo container, not a Docker-mounted config.
- Added `!.env.cloud.example` to .gitignore — the existing `.env.*` pattern would have ignored the cloud example file. This wasn't in the plan but is necessary for the file to be tracked.

## Known Issues

None.

## Files Created/Modified

- `docker-compose.cloud.yml` — **new** — Compose override replacing nginx with Caddy for cloud deployments
- `Caddyfile.cloud` — **new** — Caddy reverse proxy config with all nginx routes translated
- `.env.cloud.example` — **new** — Documented environment variables for cloud deployment
- `Caddyfile.demo` — **renamed** from `Caddyfile` — existing demo host-level reverse proxy
- `Caddyfile` — **deleted** — renamed to Caddyfile.demo
- `.gitignore` — **modified** — added certs/, data/.instance-config.json, !.env.cloud.example
- `.gsd/milestones/M033/slices/S01/tasks/T03-PLAN.md` — **modified** — added Observability Impact section
