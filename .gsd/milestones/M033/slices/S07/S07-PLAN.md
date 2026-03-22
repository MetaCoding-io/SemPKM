# S07: Deployment & Onboarding Overhaul

**Goal:** Fresh Docker instances guide users through deployment mode selection (local/domain/later), persist instance config, and optionally deploy with Caddy for automatic HTTPS.
**Demo:** Fresh Docker instance shows setup wizard with deployment mode step. docker-compose.cloud.yml starts Caddy + nginx + API + triplestore with automatic HTTPS.

## Must-Haves

- Instance config model (`data/.instance-config.json`) with load/save/generate
- `POST /api/setup/configure-instance` endpoint with mode validation and namespace guard
- Config priority chain: explicit env var > instance config > Pydantic default
- Startup namespace validation warning when `example.org` default is still active
- `instance_configured` field added to `GET /api/auth/status` response
- Setup wizard two-step flow: deployment mode → account creation
- `Caddyfile.cloud` with domain template, static serving, SSE streaming, WebDAV proxy
- `docker-compose.cloud.yml` replacing nginx with Caddy for cloud deployments
- `Caddyfile.local-tls` and `docker-compose.local-tls.yml` for mkcert-based local HTTPS
- `certs/` in `.gitignore`
- Documentation: cloud deployment chapter, updated installation guide, env var appendix
- Three guide index files kept in sync (README.md, index.html, guide.html)

## Proof Level

- This slice proves: operational
- Real runtime required: no (compose config validation + unit tests are sufficient; full Docker test deferred to integration)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v` — unit tests for config model and configure-instance endpoint
- `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet` — validates merged compose
- `grep -c "cloud-deployment" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` — all three return ≥1
- `test -f Caddyfile.cloud && test -f docker-compose.cloud.yml && test -f .env.cloud.example` — infrastructure files exist
- `test -f Caddyfile.local-tls && test -f docker-compose.local-tls.yml` — local TLS files exist
- `grep -q "certs/" .gitignore` — certs directory is gitignored
- `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_namespace_guard_409_when_data_exists -v` — namespace guard failure path verified

## Observability / Diagnostics

- Runtime signals: startup log warning when `base_namespace` is still `example.org` and no instance config exists; log line when instance config overrides Pydantic default
- Inspection surfaces: `data/.instance-config.json` file presence and content; `GET /api/auth/status` `instance_configured` field
- Failure visibility: `POST /api/setup/configure-instance` returns 409 if user data exists in triplestore (namespace change guard)
- Redaction constraints: none (no secrets in instance config)

## Integration Closure

- Upstream surfaces consumed: `backend/app/config.py` (Settings), `backend/app/auth/router.py` (status endpoint), `backend/app/auth/schemas.py` (StatusResponse), `frontend/static/setup.html`, `frontend/static/js/auth.js`, `frontend/nginx.conf` (location blocks for Caddy replication)
- New wiring introduced in this slice: `setup_routes` router registered in `main.py`, instance config loaded at startup in `config.py`, `auth.js` multi-step flow calls new endpoint before existing setup endpoint
- What remains before the milestone is truly usable end-to-end: nothing — S07 is the final slice

## Tasks

- [x] **T01: Instance config model, configure-instance endpoint, and config priority chain** `est:2h`
  - Why: Foundation for the entire deployment overhaul — every other task depends on the instance config model and the configure-instance endpoint. Implements the config priority chain (env var > instance config > Pydantic default) and the namespace guard.
  - Files: `backend/app/instance_config.py`, `backend/app/api/setup_routes.py`, `backend/app/config.py`, `backend/app/main.py`, `backend/app/auth/router.py`, `backend/app/auth/schemas.py`, `backend/tests/test_instance_config.py`
  - Do: (1) Create `instance_config.py` with InstanceConfig Pydantic model, load/save/generate functions. (2) Create `setup_routes.py` with `POST /api/setup/configure-instance` — accepts mode/domain, validates, writes config, returns namespace. Guard: refuses if triplestore has data. Must be callable without auth (runs before owner account exists). (3) Modify `config.py` to load instance config when `base_namespace` matches Pydantic default. (4) Add startup namespace validation warning in `main.py`. (5) Add `instance_configured` to StatusResponse and auth_status endpoint. (6) Register setup_routes router in main.py. (7) Write comprehensive unit tests.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v`
  - Done when: All tests pass covering load/save/generate, all three modes (local/domain/later), domain validation, namespace guard (409 when data exists), and status response includes `instance_configured`

- [x] **T02: Setup wizard two-step UI** `est:1.5h`
  - Why: The frontend half of the deployment mode feature — guides first-time users through deployment selection before account creation.
  - Files: `frontend/static/setup.html`, `frontend/static/js/auth.js`, `frontend/static/css/style.css`
  - Do: (1) Redesign setup.html with two-step flow: step 1 = deployment mode radio cards (local/domain/later), step 2 = existing token+email form. Add step indicator (Step 1 of 2 / Step 2 of 2). Domain input with inline validation (no protocol prefix, valid hostname). "Cannot change after data is created" warning. (2) Update `auth.js` — `checkAuthStatus()` checks `instance_configured` field, shows step 1 or step 2 accordingly. `handleSetupForm()` becomes multi-step: step 1 calls `POST /api/setup/configure-instance`, step 2 calls existing `POST /api/auth/setup`. (3) Add CSS for step indicator, radio card styling, domain input group.
  - Verify: `grep -q "configure-instance" frontend/static/js/auth.js && grep -q "deployment-mode\|step-indicator" frontend/static/css/style.css`
  - Done when: setup.html renders a two-step wizard; step 1 POSTs to configure-instance and shows appropriate feedback; step 2 is the existing account creation; CSS styles radio cards and step indicator

- [x] **T03: Caddy cloud profile, local TLS profile, and infrastructure files** `est:1.5h`
  - Why: Provides one-command cloud deployment with automatic HTTPS and optional local TLS for testing. Independent of the backend/frontend work.
  - Files: `Caddyfile.cloud`, `docker-compose.cloud.yml`, `.env.cloud.example`, `Caddyfile.local-tls`, `docker-compose.local-tls.yml`, `Caddyfile`, `.gitignore`
  - Do: (1) Create `Caddyfile.cloud` — domain template `{$SEMPKM_DOMAIN}`, static file serving for `/css/`, `/js/`, `/assets/`, auth pages with no-cache, reverse proxy to `api:8000` for everything else, `flush_interval -1` for SSE paths (llm/chat/stream, lint/stream, import scan stream), WebDAV proxy passthrough, gzip encoding. Replicate all nginx.conf location blocks. (2) Create `docker-compose.cloud.yml` — override that replaces frontend service with Caddy, adds caddy_data/caddy_config volumes, ports 443+80. (3) Create `.env.cloud.example` with SEMPKM_DOMAIN, BASE_NAMESPACE, APP_BASE_URL, COOKIE_SECURE=true. (4) Create `Caddyfile.local-tls` — localhost with mkcert cert paths, same routing as cloud. (5) Create `docker-compose.local-tls.yml` — override mounting certs/ directory. (6) Rename `Caddyfile` → `Caddyfile.demo`. (7) Add `certs/` to `.gitignore`.
  - Verify: `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet && test -f Caddyfile.cloud && test -f .env.cloud.example && test -f Caddyfile.local-tls && test -f docker-compose.local-tls.yml && grep -q "certs/" .gitignore`
  - Done when: Merged cloud compose validates without error; all infrastructure files exist; Caddyfile.cloud covers all nginx.conf location equivalents (static, SSE, WebDAV, API catch-all); certs/ is gitignored

- [x] **T04: Documentation updates and guide index sync** `est:1h`
  - Why: Users need deployment instructions and environment variable documentation. The three guide index files must stay in sync (Knowledge entry).
  - Files: `docs/guide/03-installation-and-setup.md`, `docs/guide/20-production-deployment.md`, `docs/guide/38-cloud-deployment.md`, `docs/guide/appendix-a-environment-variables.md`, `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`
  - Do: (1) Update `03-installation-and-setup.md` — document the new setup wizard two-step flow with deployment mode selection, explain the three modes and their namespace implications. (2) Update `20-production-deployment.md` — add Caddy cloud profile section with quick-start, reference the cloud deployment chapter. (3) Create `38-cloud-deployment.md` — step-by-step Caddy cloud guide: DNS setup, `.env` configuration, docker compose command, certificate verification, firewall rules, backup notes. (4) Update `appendix-a-environment-variables.md` — add `SEMPKM_DOMAIN`, document `data/.instance-config.json`. (5) Add new chapter entry to all three guide index files: `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`.
  - Verify: `grep -c "cloud-deployment\|38-cloud-deployment" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html | grep -v ":0$" | wc -l` returns 3 (all three files have the entry)
  - Done when: Cloud deployment chapter exists; installation guide documents new wizard flow; all three guide index files reference the new chapter; appendix documents SEMPKM_DOMAIN and instance config

## Files Likely Touched

- `backend/app/instance_config.py` (new)
- `backend/app/api/setup_routes.py` (new)
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/auth/router.py`
- `backend/app/auth/schemas.py`
- `backend/tests/test_instance_config.py` (new)
- `frontend/static/setup.html`
- `frontend/static/js/auth.js`
- `frontend/static/css/style.css`
- `Caddyfile.cloud` (new)
- `docker-compose.cloud.yml` (new)
- `.env.cloud.example` (new)
- `Caddyfile.local-tls` (new)
- `docker-compose.local-tls.yml` (new)
- `Caddyfile` → `Caddyfile.demo` (rename)
- `.gitignore`
- `docs/guide/03-installation-and-setup.md`
- `docs/guide/20-production-deployment.md`
- `docs/guide/38-cloud-deployment.md` (new)
- `docs/guide/appendix-a-environment-variables.md`
- `docs/guide/README.md`
- `docs/guide/index.html`
- `backend/app/templates/guide.html`
