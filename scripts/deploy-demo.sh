#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# DNS/SSL Setup (one-time, before first deployment)
# ============================================================================
#
# Prerequisites:
#   - A VPS with Docker and Docker Compose installed
#   - A domain (e.g. demo.sempkm.app) with DNS A record pointing to the VPS IP
#
# Steps:
#   1. Install Caddy on the host:
#        sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
#        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
#        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
#        sudo apt update && sudo apt install -y caddy
#
#   2. Copy the Caddyfile to the Caddy config directory and update the domain:
#        sudo cp Caddyfile /etc/caddy/Caddyfile
#        sudo sed -i 's/demo.sempkm.app/YOUR_DOMAIN/' /etc/caddy/Caddyfile
#
#   3. Reload Caddy to pick up the new config:
#        sudo systemctl reload caddy
#
#   Caddy will automatically obtain and renew SSL/HTTPS certificates from
#   Let's Encrypt. No manual certificate management is needed.
#
#   Verify Caddy status:  sudo systemctl status caddy
#   View Caddy logs:      journalctl -u caddy
# ============================================================================

COMPOSE_FILE="docker-compose.demo.yml"

echo "=== SemPKM Demo Deployment ==="

# 1. Start the demo stack
echo "[1/4] Starting demo stack..."
docker compose -f "$COMPOSE_FILE" up -d --build

# 2. Wait for API health
echo "[2/4] Waiting for API to be healthy..."
until docker compose -f "$COMPOSE_FILE" exec -T api curl -sf http://localhost:8000/api/health > /dev/null 2>&1; do
  sleep 2
done
echo "  API is healthy."

# 3. Run seed script
echo "[3/4] Seeding demo data..."
docker compose -f "$COMPOSE_FILE" exec -T api python /app/scripts/seed-demo-data.py

# 4. Verify
echo "[4/4] Verifying..."
docker compose -f "$COMPOSE_FILE" exec -T api python /app/scripts/seed-demo-data.py --verify-only

echo ""
echo "=== Demo instance ready ==="
echo "  Frontend: http://localhost:3902"
echo "  API:      http://localhost:8902"

# ============================================================================
# Periodic Reset via Cron
# ============================================================================
#
# To keep the demo instance fresh, set up a periodic reset using cron.
# This tears down the stack, rebuilds, and re-seeds every 6 hours:
#
#   crontab -e
#   0 */6 * * * /path/to/scripts/reset-demo.sh >> /var/log/sempkm-demo-reset.log 2>&1
#
# Although the demo nginx config blocks all write methods (POST/PUT/DELETE/PATCH)
# with 403, the periodic reset handles any edge cases and keeps the instance
# running on the latest code.
#
# View reset history:  tail -100 /var/log/sempkm-demo-reset.log
# ============================================================================

# ============================================================================
# Health Check / Uptime Monitoring
# ============================================================================
#
# The API exposes a health endpoint that can be used with uptime monitoring
# services (e.g. UptimeRobot, Healthchecks.io, or a simple cron probe):
#
#   curl -sf http://localhost:3902/api/health
#
# Returns HTTP 200 with JSON body when the API and triplestore are healthy.
# For external monitoring, use the public HTTPS URL instead:
#
#   curl -sf https://YOUR_DOMAIN/api/health
# ============================================================================
