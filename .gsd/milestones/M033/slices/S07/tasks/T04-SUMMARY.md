---
id: T04
parent: S07
milestone: M033
provides:
  - Cloud deployment chapter (39-cloud-deployment.md) with DNS, compose, certs, firewall, backup, local TLS, troubleshooting
  - Setup wizard two-step flow documented in installation guide (03-installation-and-setup.md)
  - Caddy cloud profile referenced in production deployment guide (20-production-deployment.md)
  - SEMPKM_DOMAIN and instance config documented in environment variables appendix
  - All three guide index files updated with chapter 39 entry
key_files:
  - docs/guide/39-cloud-deployment.md
  - docs/guide/03-installation-and-setup.md
  - docs/guide/20-production-deployment.md
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/README.md
  - docs/guide/index.html
  - backend/app/templates/guide.html
key_decisions:
  - Used chapter 39 instead of plan's 38 — chapter 38 is already "Hosted Demo" in all three guide indexes
patterns_established:
  - none
observability_surfaces:
  - none (documentation-only task)
duration: 10m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T04: Documentation updates and guide index sync

**Added cloud deployment chapter, setup wizard docs, and synced all three guide index files with chapter 39 entry**

## What Happened

Created `docs/guide/39-cloud-deployment.md` — a comprehensive cloud deployment chapter covering: prerequisites (server, domain, DNS), environment configuration from `.env.cloud.example`, the `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d` start command, certificate verification, firewall rules (ports 80/443), backup procedures for both RDF4J and SQL, local TLS testing with mkcert, updating the deployment, and a troubleshooting section covering DNS propagation, port conflicts, Let's Encrypt rate limits, container startup failures, and SSE streaming issues.

Updated `docs/guide/03-installation-and-setup.md` — rewrote the "First-Run Setup Wizard" section as a two-step flow. Step 1 (new) documents deployment mode selection with a table explaining the three modes (Local Only, Custom Domain, Decide Later) and their namespace strategies. Includes the one-way-door warning and the env-var bypass tip. Renumbered existing steps (Find Setup Token → Step 2, Claim Instance → Step 3, Verify Starter Model → Step 4).

Updated `docs/guide/20-production-deployment.md` — added a "Caddy Cloud Profile" subsection under "Reverse Proxy and HTTPS" with a quick-start command and reference to the full chapter 39.

Updated `docs/guide/appendix-a-environment-variables.md` — added `SEMPKM_DOMAIN` to the variable reference table and a new "Instance Configuration File" section documenting `data/.instance-config.json`.

Updated all three guide index files in sync: `docs/guide/README.md` (markdown TOC), `docs/guide/index.html` (sidebar `data-file` link), `backend/app/templates/guide.html` (htmx button with cloud icon).

## Verification

All 4 task-level checks pass: chapter file exists, all three index files reference cloud-deployment, SEMPKM_DOMAIN documented, setup wizard flow documented.

All 7 slice-level checks pass: 26 unit tests pass, compose merge validates, all three guide files reference cloud-deployment, infrastructure files exist, local TLS files exist, certs gitignored, namespace guard test passes.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/39-cloud-deployment.md` | 0 | ✅ pass | <0.1s |
| 2 | `grep -c "cloud-deployment\|39-cloud-deployment\|Cloud Deployment" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html \| grep -v ":0$" \| wc -l` returns 3 | 0 | ✅ pass | <0.1s |
| 3 | `grep -q "SEMPKM_DOMAIN" docs/guide/appendix-a-environment-variables.md` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "deployment mode\|Deployment Mode\|setup wizard\|Setup Wizard" docs/guide/03-installation-and-setup.md` | 0 | ✅ pass | <0.1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v` | 0 | ✅ pass | 0.59s |
| 6 | `docker compose -f docker-compose.yml -f docker-compose.cloud.yml config --quiet` | 0 | ✅ pass | <0.5s |
| 7 | `test -f Caddyfile.cloud && test -f docker-compose.cloud.yml && test -f .env.cloud.example` | 0 | ✅ pass | <0.1s |
| 8 | `test -f Caddyfile.local-tls && test -f docker-compose.local-tls.yml` | 0 | ✅ pass | <0.1s |
| 9 | `grep -q "certs/" .gitignore` | 0 | ✅ pass | <0.1s |
| 10 | `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_namespace_guard_409_when_data_exists -v` | 0 | ✅ pass | 0.50s |

## Diagnostics

- **Chapter file**: `test -f docs/guide/39-cloud-deployment.md` confirms cloud deployment docs exist
- **Index sync**: `grep -c "cloud-deployment" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` — all three should return ≥1
- **Wizard docs**: `grep -c "Deployment Mode" docs/guide/03-installation-and-setup.md` confirms wizard documentation

## Deviations

- Used chapter number 39 instead of the plan's 38 — chapter 38 was already occupied by "Hosted Demo" in all three guide index files. The plan referenced `38-cloud-deployment.md` assuming the slot was free, but the README, index.html, and guide.html all had `38-hosted-demo` entries.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/39-cloud-deployment.md` — new: comprehensive cloud deployment chapter with DNS, compose, certs, firewall, backup, local TLS, troubleshooting
- `docs/guide/03-installation-and-setup.md` — updated: rewrote setup wizard section as two-step flow with deployment mode documentation
- `docs/guide/20-production-deployment.md` — updated: added Caddy cloud profile subsection with quick-start and chapter 39 reference
- `docs/guide/appendix-a-environment-variables.md` — updated: added SEMPKM_DOMAIN variable and instance config file documentation
- `docs/guide/README.md` — updated: added chapter 39 entry in table of contents
- `docs/guide/index.html` — updated: added chapter 39 sidebar link
- `backend/app/templates/guide.html` — updated: added chapter 39 htmx button with cloud icon
- `.gsd/milestones/M033/slices/S07/tasks/T04-PLAN.md` — added Observability Impact section per pre-flight check
