---
estimated_steps: 5
estimated_files: 7
skills_used: []
---

# T04: Documentation updates and guide index sync

**Slice:** S07 — Deployment & Onboarding Overhaul
**Milestone:** M033

## Description

Update user documentation to cover the new setup wizard flow, cloud deployment via Caddy compose profile, and new environment variables. Create a new cloud deployment chapter. Keep the three guide index files in sync (Knowledge entry: README.md, index.html, guide.html must all reference new chapters).

## Steps

1. **Update `docs/guide/03-installation-and-setup.md`** — add a "Setup Wizard" section documenting the two-step flow:
   - Step 1: Deployment mode selection (local/domain/later) with explanation of each mode's namespace strategy
   - Step 2: Account creation with setup token (existing, briefly referenced)
   - Explain the one-way-door nature of namespace selection
   - Mention that operators who set `BASE_NAMESPACE` in `.env` bypass the wizard

2. **Update `docs/guide/20-production-deployment.md`** — add a "Caddy Cloud Profile" subsection:
   - Reference the new `docs/guide/38-cloud-deployment.md` for full guide
   - Quick-start: `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d`
   - Brief mention of automatic TLS, HTTP/2, HTTP/3 benefits
   - Keep existing nginx production notes intact

3. **Create `docs/guide/38-cloud-deployment.md`** — comprehensive cloud deployment chapter:
   - Prerequisites: domain name, DNS A record pointing to server, Docker installed
   - Copy `.env.cloud.example` to `.env` and configure `SEMPKM_DOMAIN`, `BASE_NAMESPACE`, etc.
   - Start command: `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d`
   - Certificate verification: how to check Let's Encrypt certs are provisioned
   - Firewall: ports 80 and 443 must be open
   - Backup notes: `docker compose exec api` backup commands
   - Local TLS testing section: mkcert setup instructions, `docker compose -f docker-compose.yml -f docker-compose.local-tls.yml up`
   - Troubleshooting: common issues (DNS not propagated, port blocked, cert rate limits)

4. **Update `docs/guide/appendix-a-environment-variables.md`** — add entries for:
   - `SEMPKM_DOMAIN` — domain for cloud deployment (used by Caddy)
   - Document `data/.instance-config.json` as the instance configuration file (not an env var, but related)

5. **Update all three guide index files** (Knowledge entry — three files must stay in sync):
   - `docs/guide/README.md` — add `38-cloud-deployment.md` entry in the table of contents
   - `docs/guide/index.html` — add corresponding `<button>` or sidebar entry
   - `backend/app/templates/guide.html` — add corresponding entry in the Jinja2 template
   - Match the existing pattern for chapter numbering and ordering

## Must-Haves

- [ ] Cloud deployment chapter exists with DNS, compose command, cert verification, troubleshooting
- [ ] Installation guide documents the two-step wizard flow
- [ ] Production deployment references the Caddy cloud profile
- [ ] Environment variables appendix includes `SEMPKM_DOMAIN`
- [ ] All three guide index files reference `38-cloud-deployment` (README.md, index.html, guide.html)

## Verification

- `test -f docs/guide/38-cloud-deployment.md` — cloud deployment chapter exists
- `grep -c "38-cloud-deployment\|cloud-deployment\|Cloud Deployment" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html | grep -v ":0$" | wc -l` returns 3
- `grep -q "SEMPKM_DOMAIN" docs/guide/appendix-a-environment-variables.md` — env var documented
- `grep -q "deployment mode\|Deployment Mode\|setup wizard\|Setup Wizard" docs/guide/03-installation-and-setup.md` — wizard flow documented

## Inputs

- `docs/guide/03-installation-and-setup.md` — existing installation chapter to extend
- `docs/guide/20-production-deployment.md` — existing production chapter to extend
- `docs/guide/appendix-a-environment-variables.md` — existing env var appendix to extend
- `docs/guide/README.md` — guide table of contents
- `docs/guide/index.html` — standalone docs site sidebar
- `backend/app/templates/guide.html` — in-app docs template
- `.env.cloud.example` — T03's example env file for reference

## Observability Impact

This task is documentation-only — no runtime signals, logs, or diagnostics are added. The observability surface is the documentation itself:
- **Inspection**: `test -f docs/guide/38-cloud-deployment.md` confirms chapter creation
- **Sync verification**: `grep -c "cloud-deployment" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` confirms all three guide indexes reference the new chapter
- **Failure visibility**: A missing entry in any of the three guide index files means the documentation is out of sync (Knowledge entry)

## Expected Output

- `docs/guide/03-installation-and-setup.md` — updated with setup wizard flow
- `docs/guide/20-production-deployment.md` — updated with Caddy cloud profile reference
- `docs/guide/38-cloud-deployment.md` — new cloud deployment chapter
- `docs/guide/appendix-a-environment-variables.md` — updated with SEMPKM_DOMAIN
- `docs/guide/README.md` — updated table of contents
- `docs/guide/index.html` — updated sidebar
- `backend/app/templates/guide.html` — updated in-app docs template
