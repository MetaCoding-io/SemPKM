---
estimated_steps: 5
estimated_files: 3
---

# T01: Caddy reverse proxy config, reset script, and deploy script update

**Slice:** S04 — Cloud deployment config + E2E + docs
**Milestone:** M025

## Description

Create the deployment infrastructure for the hosted demo: a Caddyfile for automatic HTTPS via Let's Encrypt, a reset script for periodic clean-state restoration, and update the existing deploy script with DNS/SSL instructions and cron documentation.

This task covers DEMO-07 (Docker Compose demo config with SSL), DEMO-08 (periodic data reset), and DEMO-09 (basic uptime monitoring — documenting the existing health check endpoint).

The Caddyfile runs on the host machine (not in Docker) per D246, and proxies to Docker's nginx on port 3902. The reset script tears down the stack, rebuilds, waits for health, and re-seeds — suitable for running via cron.

## Steps

1. Create `Caddyfile` at the repository root with:
   - Domain placeholder `demo.sempkm.app` (with a comment noting this should be changed to the actual domain)
   - `reverse_proxy localhost:3902` — proxies to Docker's nginx
   - Caddy handles TLS automatically via Let's Encrypt (no explicit tls block needed for default behavior, but add a comment explaining this)
   - Add response header for `X-Robots-Tag: noindex, nofollow` to prevent search engine indexing of the demo instance

2. Create `scripts/reset-demo.sh` with:
   - Shebang `#!/usr/bin/env bash` and `set -euo pipefail`
   - `COMPOSE_FILE="docker-compose.demo.yml"` variable (matching deploy-demo.sh pattern)
   - Step 1: `docker compose -f "$COMPOSE_FILE" down -v` — tear down with volumes
   - Step 2: `docker compose -f "$COMPOSE_FILE" up -d --build` — rebuild and start
   - Step 3: Health wait loop (same pattern as deploy-demo.sh — `until curl -sf ...`)
   - Step 4: Re-seed via `docker compose -f "$COMPOSE_FILE" exec -T api python /app/scripts/seed-demo-data.py`
   - Step 5: Verification via `--verify-only` flag
   - Clear echo messages for each step, matching deploy-demo.sh style
   - Make executable: `chmod +x scripts/reset-demo.sh`

3. Update `scripts/deploy-demo.sh`:
   - Add a comment block at the top (after the shebang/set) with DNS/SSL setup instructions:
     - Prerequisites: a VPS with Docker, a domain pointing to the VPS IP
     - Install Caddy on the host: `sudo apt install -y caddy`
     - Copy Caddyfile to `/etc/caddy/Caddyfile` and update the domain
     - `sudo systemctl reload caddy`
     - Caddy will automatically obtain and renew SSL certificates
   - Add a cron setup section at the bottom (after the final echo block):
     - Comment block showing how to set up periodic reset: `0 */6 * * * /path/to/scripts/reset-demo.sh >> /var/log/sempkm-demo-reset.log 2>&1`
     - Comment explaining this resets the demo every 6 hours to clear visitor modifications (though nginx blocks writes, this handles any edge cases and keeps the instance fresh)
   - Add a health check monitoring note: `curl -sf http://localhost:3902/api/health` can be used with uptime monitoring services

## Must-Haves

- [ ] `Caddyfile` exists with domain placeholder, reverse_proxy to localhost:3902, and noindex header
- [ ] `scripts/reset-demo.sh` is executable and tears down, rebuilds, health-waits, and re-seeds
- [ ] `scripts/deploy-demo.sh` has DNS/SSL setup instructions and cron documentation
- [ ] Both scripts pass `bash -n` syntax check

## Verification

- `bash -n scripts/reset-demo.sh` — exits 0
- `bash -n scripts/deploy-demo.sh` — exits 0
- `cat Caddyfile` — contains `demo.sempkm.app`, `reverse_proxy`, `X-Robots-Tag`
- `test -x scripts/reset-demo.sh` — is executable
- `grep -c "caddy\|Caddy\|SSL\|HTTPS" scripts/deploy-demo.sh` — at least 3 matches (DNS/SSL instructions present)
- `grep "cron\|reset-demo" scripts/deploy-demo.sh` — cron setup documentation present

## Observability Impact

- **Reset script stdout:** Each step emits a labeled echo (`[1/5] Tearing down...`, etc.) for log-based debugging when run via cron
- **Health check wait loop:** Blocks until `curl -sf` succeeds against the API health endpoint — visible failure if the loop times out
- **Cron log capture:** Documented cron entry redirects stdout+stderr to `/var/log/sempkm-demo-reset.log` for post-mortem analysis
- **Caddy access logs:** Caddy logs requests to systemd journal; includes TLS certificate status and proxy errors
- **Failure mode:** `set -euo pipefail` in reset script ensures any command failure stops execution immediately with non-zero exit; cron captures the failure point in the log file
- **Inspection commands:** `docker compose -f docker-compose.demo.yml ps` shows container health; `journalctl -u caddy` shows proxy/TLS status; `tail /var/log/sempkm-demo-reset.log` shows last reset outcome

## Inputs

- `scripts/deploy-demo.sh` — existing 4-phase deployment wrapper from S02 (start → health → seed → verify)
- `docker-compose.demo.yml` — existing 3-service demo stack from S01 (ports 3902/8902)
- D246: Caddy reverse proxy runs on host, proxies to Docker's nginx on port 3902

## Expected Output

- `Caddyfile` — new file: ~15 lines, Caddy reverse proxy config with automatic HTTPS
- `scripts/reset-demo.sh` — new file: ~30 lines, executable reset script for cron
- `scripts/deploy-demo.sh` — modified: added DNS/SSL instructions comment block and cron documentation section
