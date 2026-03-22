# S01: Deployment & Onboarding Overhaul

**Goal:** Eliminate the dangerous `example.org` default namespace, guide new users through deployment mode selection before account creation, and provide a one-command cloud deployment with Caddy auto-TLS.
**Demo:** A fresh SemPKM instance shows a two-step setup wizard: Step 1 asks deployment mode (local/domain/later), Step 2 is the existing token+email claim. Instance config persists in `data/.instance-config.json`. Cloud deployment works via `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up` with Caddy serving HTTPS.

## Must-Haves

- `InstanceConfig` Pydantic model with `instance_id`, `deployment_mode`, `base_namespace`, `app_base_url`, `configured_at`
- `load_instance_config()` / `save_instance_config()` with atomic write to `data/.instance-config.json`
- Config priority chain: explicit env var > instance config file > Pydantic default
- `POST /api/setup/configure-instance` endpoint accepting `{mode, domain?}`, writing instance config, returning derived namespace
- `GET /api/auth/status` extended with `instance_configured: bool`
- Startup warning when `BASE_NAMESPACE` is still `example.org` and no instance config exists
- Two-step `setup.html` wizard: deployment mode → account creation
- `docker-compose.cloud.yml` + `Caddyfile.cloud` for Caddy-based cloud deployment
- `.env.cloud.example` documenting required cloud environment variables

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (pytest for backend unit/integration; browser for setup wizard UI)
- Human/UAT required: no (automated verification sufficient)

## Verification

- `cd backend && python -m pytest tests/test_instance_config.py -v` — unit tests for InstanceConfig model, load/save, priority chain, configure-instance endpoint
- `grep -q "instance_configured" backend/app/auth/schemas.py` — StatusResponse extended
- `grep -q "configure-instance" backend/app/api/setup_routes.py` — endpoint exists
- `test -f docker-compose.cloud.yml && test -f Caddyfile.cloud && test -f .env.cloud.example` — cloud infra files exist
- Visual: setup.html shows two-step flow with deployment mode radio buttons, then token+email form

## Observability / Diagnostics

- Runtime signals: structured log at startup showing which config source won for `base_namespace` (env var / instance config / default); warning log when `example.org` default is active
- Inspection surfaces: `GET /api/auth/status` returns `instance_configured: bool`; `data/.instance-config.json` is human-readable JSON
- Failure visibility: `POST /api/setup/configure-instance` returns 400 with detail message when domain validation fails or user data already exists
- Redaction constraints: none (no secrets in instance config)

## Integration Closure

- Upstream surfaces consumed: `backend/app/config.py` (Settings model), `backend/app/auth/router.py` (status endpoint), `backend/app/main.py` (lifespan startup)
- New wiring introduced in this slice: setup_routes router mounted in main.py, config.py loads instance config on import, auth status response gains `instance_configured` field
- What remains before the milestone is truly usable end-to-end: nothing for deployment — this slice is self-contained. Other slices (S02-S06) are independent features.

## Tasks

- [x] **T01: Instance config module, setup endpoint, and config priority chain** `est:2h`
  - Why: The foundational backend work — creates the instance config model, persistence, the configure-instance API endpoint, config priority chain integration in Settings, startup validation, and comprehensive unit tests. Everything else depends on this.
  - Files: `backend/app/instance_config.py`, `backend/app/api/setup_routes.py`, `backend/app/config.py`, `backend/app/auth/router.py`, `backend/app/auth/schemas.py`, `backend/app/main.py`, `backend/tests/test_instance_config.py`
  - Do: (1) Create `instance_config.py` with InstanceConfig Pydantic model, load/save with atomic write, generate_instance_id(). (2) Create `setup_routes.py` with `POST /api/setup/configure-instance` that validates mode/domain, checks for existing user data, writes config. (3) Modify `config.py` to load instance config and apply priority chain. (4) Add `instance_configured` to StatusResponse and auth/status endpoint. (5) Add startup namespace validation warning in main.py. (6) Wire setup router into main.py. (7) Write comprehensive pytest tests.
  - Verify: `cd backend && python -m pytest tests/test_instance_config.py -v` passes all tests
  - Done when: Config priority chain works (env > instance config > default), endpoint writes config, auth/status includes instance_configured, startup warns about example.org

- [x] **T02: Two-step setup wizard frontend** `est:1.5h`
  - Why: The user-facing half — transforms the single-step setup page into a two-step flow where Step 1 collects deployment mode (calling the T01 endpoint) and Step 2 is the existing account claim form.
  - Files: `frontend/static/setup.html`, `frontend/static/js/auth.js`, `frontend/static/css/style.css`
  - Do: (1) Redesign setup.html with two step containers — Step 1 has three radio options (local/domain/later) with domain input field, Step 2 is existing token+email form. (2) Update auth.js handleSetupForm() to be multi-step: Step 1 calls POST /api/setup/configure-instance, Step 2 calls POST /api/auth/setup. (3) Update checkAuthStatus() to use instance_configured from status response to decide which step to show. (4) Add CSS for step indicator, radio cards, domain input validation styling. (5) Add one-way-door warning text about namespace permanence.
  - Verify: Manual browser verification — setup.html shows Step 1 with radio cards, selecting "Local only" and clicking Next calls configure-instance API, then shows Step 2
  - Done when: Two-step wizard flow works end-to-end — deployment mode → account creation with proper API calls at each step

- [x] **T03: Cloud deployment infrastructure (Caddy compose + Caddyfile)** `est:1h`
  - Why: Provides the one-command cloud deployment path. Independent of T01/T02 — these are infrastructure files that consume the same backend.
  - Files: `docker-compose.cloud.yml`, `Caddyfile.cloud`, `.env.cloud.example`, `Caddyfile`, `docker-compose.demo.yml`, `.gitignore`
  - Do: (1) Create docker-compose.cloud.yml as a compose override that replaces nginx frontend with Caddy, adds caddy_data/caddy_config volumes. (2) Create Caddyfile.cloud using {$SEMPKM_DOMAIN} with static file serving, auth page routing, SSE proxy config, and API reverse proxy. (3) Create .env.cloud.example with all required cloud vars. (4) Rename Caddyfile → Caddyfile.demo and update docker-compose.demo.yml reference. (5) Add certs/ to .gitignore for future mkcert support.
  - Verify: `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet` validates compose syntax; `test -f Caddyfile.cloud && test -f .env.cloud.example && test -f Caddyfile.demo`
  - Done when: Compose config validates without errors, all cloud infra files exist with correct content, demo Caddyfile renamed

## Files Likely Touched

- `backend/app/instance_config.py` (new)
- `backend/app/api/setup_routes.py` (new)
- `backend/app/config.py`
- `backend/app/auth/router.py`
- `backend/app/auth/schemas.py`
- `backend/app/main.py`
- `backend/tests/test_instance_config.py` (new)
- `frontend/static/setup.html`
- `frontend/static/js/auth.js`
- `frontend/static/css/style.css`
- `docker-compose.cloud.yml` (new)
- `Caddyfile.cloud` (new)
- `.env.cloud.example` (new)
- `Caddyfile` → `Caddyfile.demo` (rename)
- `docker-compose.demo.yml`
- `.gitignore`
