---
id: S07
milestone: M033
title: "Deployment & Onboarding Overhaul"
status: done
tasks_completed: [T01, T02, T03, T04]
tasks_total: 4
duration_estimate: "6h"
duration_actual: "~1.2h"
completed_at: 2026-03-21
verification_result: passed
---

# S07 Summary: Deployment & Onboarding Overhaul

## What This Slice Delivered

Fresh SemPKM instances now guide users through a two-step setup wizard — first selecting a deployment mode (local, custom domain, or decide later), then creating the owner account. The deployment mode determines the RDF namespace strategy (URN for local, `https://{domain}/data/` for domain). Once data exists, the namespace is locked — the configure-instance endpoint returns 409 if called after objects are created.

Cloud deployment is a one-command operation via `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d`, replacing nginx with Caddy for automatic HTTPS (Let's Encrypt). A local TLS profile with mkcert is also available for development.

Comprehensive documentation covers the new wizard flow, cloud deployment, environment variables, and troubleshooting.

## Key Components

### T01: Instance Config Model & Configure-Instance Endpoint
- `backend/app/instance_config.py` — `InstanceConfig` Pydantic model with `load_instance_config()`, `save_instance_config()` (atomic write via tmp + `os.replace`), and `generate_instance_id()` (UUID4)
- `backend/app/api/setup_routes.py` — `POST /api/setup/configure-instance` with three modes (`local`/`domain`/`later`), domain hostname validation, namespace guard (409 when triplestore has data), auth guard (403 when already configured outside setup mode)
- Config priority chain in `config.py`: explicit env var > `data/.instance-config.json` > Pydantic default. Detection uses Pydantic default comparison, not `os.environ` (since docker-compose always sets env vars)
- `instance_configured: bool` added to `GET /api/auth/status` response
- Startup WARNING when `base_namespace` is still `example.org` with no instance config
- 26 unit tests covering model, persistence, all modes, guards, and priority chain

### T02: Setup Wizard Two-Step UI
- `setup.html` redesigned: step indicator (dot-line-dot), deployment mode radio cards with descriptions, conditional domain input with smooth max-height transition, live namespace preview, one-way-door warning
- `auth.js`: `handleDeploymentStep()` manages mode selection and API call; `checkAuthStatus()` reads `instance_configured` to route to correct step; `_showSetupStep()` centralizes step visibility
- CSS: step indicator, radio card (border + hover + selected accent), domain input group, namespace preview (monospace), warning box (amber)

### T03: Caddy Cloud & Local TLS Profiles
- `Caddyfile.cloud` — all nginx.conf location blocks translated to Caddy `handle` directives: static assets, auth pages (no-cache), 3 SSE streaming paths (`flush_interval -1`), Obsidian upload (unlimited body size), WebDAV proxy, API catch-all. Domain templated via `{$SEMPKM_DOMAIN}`
- `docker-compose.cloud.yml` — compose override replacing frontend with `caddy:2-alpine`, Caddy data/config volumes, ports 443+80
- `.env.cloud.example` — documented cloud deployment variables
- `Caddyfile.local-tls` — localhost with mkcert cert paths; `docker-compose.local-tls.yml` — override mounting `./certs`
- Existing `Caddyfile` renamed to `Caddyfile.demo`; `certs/` added to `.gitignore`

### T04: Documentation & Guide Index Sync
- `docs/guide/39-cloud-deployment.md` — DNS, compose command, cert verification, firewall, backup, local TLS, troubleshooting
- `03-installation-and-setup.md` — setup wizard rewritten as two-step flow with mode table
- `20-production-deployment.md` — Caddy cloud profile subsection added
- `appendix-a-environment-variables.md` — `SEMPKM_DOMAIN` and instance config documented
- All three guide indexes updated (README.md, index.html, guide.html) — chapter 39 (not 38, which was occupied by Hosted Demo)

## Decisions Made

| ID | Decision | Choice |
|----|----------|--------|
| D306 | Instance config persistence strategy | `data/.instance-config.json` with priority chain: env var > instance config > Pydantic default. Detect env var override by comparing against Pydantic default sentinel. |

## Patterns Established

- **httpx.AsyncClient + ASGITransport**: First use in this codebase for endpoint testing with mock app state — `test_instance_config.py` establishes the pattern for testing FastAPI endpoints without running a server
- **Compose override pattern for deployment profiles**: Override only the frontend service, add profile-specific volumes, keep API/triplestore unchanged. Both cloud and local-tls profiles follow this pattern.
- **Atomic config file write**: `save_instance_config()` uses tmp file + `os.replace()` for crash-safe persistence

## What the Next Slice Should Know

S07 is the final slice of M033. No downstream slices depend on this work within the milestone.

For future milestones:
- The `POST /api/setup/configure-instance` endpoint is only callable before data exists in the triplestore. If a future feature needs to change namespaces post-data, the guard in `setup_routes.py` must be relaxed.
- The config priority chain (env var > instance config > default) uses Pydantic default comparison in `config.py`. If `Settings.base_namespace` default changes from `https://example.org/data/`, update the comparison logic.
- Chapter numbering: 39 is cloud deployment. Don't reuse 38 (Hosted Demo).
- Three guide index files must stay in sync — see Knowledge entry about `README.md`, `index.html`, and `guide.html`.

## Verification Results

| # | Check | Result |
|---|-------|--------|
| 1 | 26 unit tests pass (`test_instance_config.py`) | ✅ |
| 2 | Cloud compose merge validates (`docker compose config --quiet`) | ✅ |
| 3 | Local TLS compose merge validates | ✅ |
| 4 | All three guide indexes reference cloud-deployment | ✅ |
| 5 | Infrastructure files exist (Caddyfile.cloud, docker-compose.cloud.yml, .env.cloud.example) | ✅ |
| 6 | Local TLS files exist (Caddyfile.local-tls, docker-compose.local-tls.yml) | ✅ |
| 7 | `certs/` in .gitignore | ✅ |
| 8 | Namespace guard test passes (409 when data exists) | ✅ |
