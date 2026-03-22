---
id: S01
parent: M033
milestone: M033
provides:
  - InstanceConfig Pydantic model with atomic load/save to data/.instance-config.json
  - POST /api/setup/configure-instance endpoint (local/domain/later modes)
  - Config priority chain (env var > instance config > default)
  - instance_configured field in GET /api/auth/status
  - Startup namespace warning when example.org default is active
  - Two-step setup wizard UI (deployment mode → account creation)
  - docker-compose.cloud.yml + Caddyfile.cloud for cloud deployment with auto-TLS
  - .env.cloud.example documenting required cloud environment variables
requires: []
affects: []
key_files:
  - backend/app/instance_config.py
  - backend/app/api/setup_routes.py
  - backend/app/config.py
  - frontend/static/setup.html
  - frontend/static/js/auth.js
  - docker-compose.cloud.yml
  - Caddyfile.cloud
  - .env.cloud.example
  - backend/tests/test_instance_config.py
key_decisions: []
patterns_established:
  - "Atomic file write for instance config (write tmp then rename)"
  - "Config priority chain: env var > instance config file > Pydantic default"
  - "Radio card UI pattern for setup wizard deployment mode selection"
observability_surfaces:
  - "Structured log at startup showing config source for base_namespace"
  - "Warning log when example.org default namespace is active"
  - "GET /api/auth/status returns instance_configured: bool"
  - "POST /api/setup/configure-instance returns 400 with detail on validation failures"
drill_down_paths:
  - .gsd/milestones/M033/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M033/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M033/slices/S01/tasks/T03-SUMMARY.md
duration: 55min
verification_result: passed
completed_at: 2026-03-22
---

# S01: Deployment & Onboarding Overhaul

**Eliminated dangerous example.org default namespace with instance config, two-step setup wizard, and one-command Caddy cloud deployment — 32 unit tests passing**

## What Happened

T01 built the backend: InstanceConfig Pydantic model with atomic file persistence to `data/.instance-config.json`, a `POST /api/setup/configure-instance` endpoint supporting local/domain/later modes with domain validation and user-data guards, a config priority chain (env var > instance config > default), `instance_configured` in auth status, and a startup warning when the example.org default is active. 32 tests cover the model, priority chain, and endpoint.

T02 built the frontend: transformed the single-step setup page into a two-step wizard with deployment mode radio cards, domain input with protocol stripping, one-way-door warning, and step routing based on `instance_configured`.

T03 created cloud deployment infrastructure: `docker-compose.cloud.yml` override replacing nginx with Caddy for auto-TLS, `Caddyfile.cloud` with all nginx routes translated, `.env.cloud.example` with documented variables, and renamed the demo Caddyfile to avoid confusion.

## Verification

All verification checks passed: 32 unit tests, setup wizard renders two-step flow, cloud infra files exist, `instance_configured` field present in auth status schema, `configure-instance` endpoint registered.

## Deviations

- Renamed existing `Caddyfile` to `Caddyfile.demo` to avoid confusion with the new cloud config.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/instance_config.py` — InstanceConfig model with load/save/generate
- `backend/app/api/setup_routes.py` — POST /api/setup/configure-instance endpoint
- `backend/app/config.py` — Config priority chain integration
- `backend/app/auth/schemas.py` — instance_configured field
- `backend/app/main.py` — Startup namespace warning
- `frontend/static/setup.html` — Two-step setup wizard
- `frontend/static/js/auth.js` — Step routing and domain validation
- `frontend/static/css/style.css` — Radio card and wizard step styles
- `docker-compose.cloud.yml` — Caddy cloud deployment override
- `Caddyfile.cloud` — Caddy config with all routes
- `.env.cloud.example` — Cloud environment variable documentation
- `backend/tests/test_instance_config.py` — 32 unit tests

## Forward Intelligence

### What the next slice should know
- Instance config is at `data/.instance-config.json` and is gitignored.

### What's fragile
- Nothing identified.

### Authoritative diagnostics
- `GET /api/auth/status` returns `instance_configured` field.
- `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v` for full test suite.

### What assumptions changed
- None.
