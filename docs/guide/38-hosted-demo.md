# Chapter 38: Hosted Demo Instance

The **Hosted Demo** is a pre-populated, read-only SemPKM instance that lets prospective users explore the full workspace — Mental Models, objects, edges, dashboards, and the guided tour — without installing Docker or creating an account.

This chapter covers deploying your own hosted demo instance, including configuration, sample data, SSL termination, and periodic reset.

---

## Prerequisites

- **Docker and Docker Compose** — the demo runs as a multi-container Docker stack
- **A VPS or cloud server** — for public deployment (any provider with Docker support)
- **A domain name** — for automatic HTTPS via Caddy (e.g., `demo.sempkm.app`)

For local testing, only Docker is required.

---

## Quick Start

To launch a demo instance locally:

```bash
# Clone the repository
git clone https://github.com/your-org/sempkm.git
cd sempkm

# Deploy the demo stack (builds, starts, seeds data)
bash scripts/deploy-demo.sh

# Visit the demo
open http://localhost:3902
```

The deploy script handles the full lifecycle: building containers, waiting for health, seeding sample data, and verifying the result.

---

## DEMO_MODE Configuration

The demo stack is controlled by the `DEMO_MODE=true` environment variable, set in `docker-compose.demo.yml`. When enabled, `DEMO_MODE` changes three behaviors:

1. **Anonymous access** — All authentication checks return a synthetic read-only guest user. No login page is shown; visitors land directly in the workspace.
2. **Setup wizard bypass** — The first-run setup wizard is skipped entirely. The demo is immediately usable after deployment.
3. **Demo-specific UI** — The guided tour auto-starts on first visit, and a "Try SemPKM" CTA banner appears after tour completion.

### Docker Compose File

The demo uses its own Compose file (`docker-compose.demo.yml`) with separate ports, volumes, and network to avoid conflicts with the development stack:

| Service     | Dev Port | Demo Port |
|-------------|----------|-----------|
| Frontend    | 3000     | 3902      |
| API         | 8001     | 8902      |

```bash
# Start the demo stack
docker compose -f docker-compose.demo.yml up -d --build

# Stop and remove (including volumes)
docker compose -f docker-compose.demo.yml down -v
```

---

## Read-Only Enforcement

The demo enforces read-only access at the nginx reverse-proxy layer. The custom nginx configuration (`frontend/nginx.demo.conf`) blocks all write HTTP methods before any location matching:

- **Blocked methods:** `POST`, `PUT`, `DELETE`, `PATCH` — return `403 Forbidden` with a JSON body:
  ```json
  {"error": "Demo instance is read-only"}
  ```
- **Allowed methods:** `GET`, `HEAD`, `OPTIONS` — pass through to the API normally

This is a defense-in-depth measure. Even though the synthetic guest user has no write permissions at the application layer, the nginx block ensures that no write request reaches the API server.

---

## Sample Data

The seed script (`scripts/seed-demo-data.py`) populates the demo with realistic sample data across multiple Mental Models.

### What It Creates

| Category        | Count | Details                                            |
|-----------------|-------|----------------------------------------------------|
| Mental Models   | 4     | Basic PKM (auto-installed), CRM, Zettelkasten+, Research Workflow |
| Objects         | 74+   | Notes, concepts, contacts, zettelkasten notes, papers, claims |
| Cross-model edges | Multiple | Relationships connecting objects across model boundaries |
| Markdown bodies | Multiple | Rich content on key objects for demo readability   |
| Dashboard       | 1     | Pre-built demo dashboard with cross-view context filtering |

### Running the Seed Script

The seed script runs inside the API container:

```bash
# Full seed (install models, create objects, edges, bodies, dashboard)
docker compose -f docker-compose.demo.yml exec api \
  python /app/scripts/seed-demo-data.py

# Verify seed data without making changes
docker compose -f docker-compose.demo.yml exec api \
  python /app/scripts/seed-demo-data.py --verify-only
```

The script is **idempotent** — safe to run multiple times. Models are checked before installation, edges are verified via SPARQL ASK before creation, and body writes are inherently idempotent.

---

## Demo Tour

A 7-step guided tour built with [Driver.js](https://driverjs.com/) walks new visitors through the SemPKM workspace.

### Tour Steps

1. **Explorer panel** — navigating types and objects
2. **Object editor** — viewing and editing object properties
3. **Edge panel** — exploring relationships between objects
4. **Views** — table, card, and graph views
5. **SPARQL console** — querying the knowledge graph
6. **Dashboard** — multi-view layouts with cross-view context
7. **CTA** — install prompt for SemPKM

### Auto-Start Behavior

When `DEMO_MODE` is enabled, the tour auto-starts on the visitor's first page load. After completion (or dismissal), the tour does not appear again.

### Manual Restart

A "Restart Tour" button in the workspace toolbar lets visitors replay the tour at any time.

### localStorage Keys

| Key                        | Purpose                              |
|----------------------------|--------------------------------------|
| `sempkm_demo_tour_done`   | Set to `'1'` when tour completes     |
| `sempkm_demo_cta_dismissed` | Set to `'1'` when CTA banner is dismissed |

Clearing these keys (or using a fresh browser/incognito window) resets the tour and CTA state.

---

## Demo Dashboard

The seed script creates a pre-built dashboard (UUID `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee`) that demonstrates **cross-view context filtering** — selecting a row in one view block filters data in connected blocks.

This dashboard is automatically available in the workspace after seeding. It showcases multi-model data in a single layout, making it an effective way for prospective users to understand SemPKM's dashboard capabilities.

---

## CTA Banner

After the tour completes, a "Try SemPKM" call-to-action banner appears at the bottom of the workspace.

### Behavior

- **Appears** after the demo tour finishes (listens for the `sempkm:demo-tour-done` custom event)
- **Dismiss** — clicking the ✕ button sets `sempkm_demo_cta_dismissed` in localStorage and hides the banner with a slide-down animation
- **Persistence** — once dismissed, the banner does not reappear for that browser session

### Customizing the CTA Link

The CTA button links to a configurable target. To change where the "Try SemPKM" button points, edit the demo CTA template in `frontend/static/js/tutorials.js` — look for the `Ready to Try SemPKM?` step in the `startDemoTour` function.

---

## SSL with Caddy

For production deployment with HTTPS, SemPKM includes a `Caddyfile` at the repository root that configures [Caddy](https://caddyserver.com/) as a reverse proxy with automatic TLS.

### Installing Caddy

On Debian/Ubuntu:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

### Configuring the Caddyfile

1. Copy the Caddyfile to Caddy's config directory:
   ```bash
   sudo cp Caddyfile /etc/caddy/Caddyfile
   ```

2. Replace the domain placeholder with your actual domain:
   ```bash
   sudo sed -i 's/demo.sempkm.app/YOUR_DOMAIN/' /etc/caddy/Caddyfile
   ```

3. Reload Caddy:
   ```bash
   sudo systemctl reload caddy
   ```

Caddy automatically obtains and renews TLS certificates from Let's Encrypt — no manual certificate management is needed.

### Verifying Caddy

```bash
# Check Caddy is running
sudo systemctl status caddy

# View Caddy logs (certificate status, proxy errors)
journalctl -u caddy
```

The Caddyfile also sets the `X-Robots-Tag: noindex, nofollow` header to prevent search engines from indexing the demo instance.

---

## Periodic Reset

To keep the demo instance clean, use `scripts/reset-demo.sh` with a cron job. The reset script performs a 5-phase clean-state restoration:

1. **Tear down** — `docker compose down -v` (removes containers and volumes)
2. **Rebuild** — `docker compose up -d --build` (fresh containers)
3. **Health wait** — polls the API health endpoint (120-second timeout)
4. **Seed** — re-runs the seed script to populate sample data
5. **Verify** — confirms seed data integrity

### Cron Setup

To reset every 6 hours:

```bash
# Edit the crontab
crontab -e

# Add this line:
0 */6 * * * /path/to/sempkm/scripts/reset-demo.sh >> /var/log/sempkm-demo-reset.log 2>&1
```

Each reset step is labeled `[1/5]` through `[5/5]` with timestamps for post-mortem inspection of the log file.

### Error Handling

The reset script uses `set -euo pipefail` — any step failure stops execution immediately with a non-zero exit code. The health check has a 120-second timeout with an explicit error message if the API does not become healthy.

---

## Health Monitoring

The API exposes a health endpoint for uptime checks:

```bash
curl -sf http://localhost:3902/api/health
```

This returns a JSON response with the application version and health status. Use this endpoint for:

- **Uptime monitoring** — configure your monitoring tool (e.g., Uptime Kuma, Healthchecks.io) to poll this URL
- **Deployment verification** — the deploy and reset scripts both use this endpoint to confirm the stack is healthy
- **Debugging** — if the health check fails, the API container is likely not running or not yet ready

For the Docker-internal health check, the API container uses `http://localhost:8000/api/health`.

---

## Troubleshooting

### Port Conflicts

If port 3902 or 8902 is already in use:

```bash
# Check what's using the port
lsof -i :3902

# The demo ports are configurable in docker-compose.demo.yml
```

### Seed Script Failures

If the seed script fails:

```bash
# Check API container logs
docker compose -f docker-compose.demo.yml logs api

# Verify the API is healthy before seeding
docker compose -f docker-compose.demo.yml exec api \
  curl -sf http://localhost:8000/api/health

# Re-run seed with full output
docker compose -f docker-compose.demo.yml exec api \
  python /app/scripts/seed-demo-data.py
```

### Stale Data

If the demo data looks wrong or incomplete:

```bash
# Full reset: tear down, rebuild, and re-seed
bash scripts/reset-demo.sh

# Or verify existing data without changes
docker compose -f docker-compose.demo.yml exec api \
  python /app/scripts/seed-demo-data.py --verify-only
```

### Tour Not Starting

If the demo tour does not auto-start:

1. Check that `DEMO_MODE=true` is set in the environment
2. Clear `sempkm_demo_tour_done` from localStorage (or use incognito)
3. Check the browser console for `[SemPKM] Demo tour` log messages
4. Verify Driver.js is loaded: `window.driver` should be defined

---

## See Also

- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) — `DEMO_MODE` and other configuration
- [Chapter 29: App Platform](29-app-platform.md) — how apps extend SemPKM
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — the Mental Models installed by the seed script

---

**Previous:** [Chapter 37: Monday.com Sync](37-monday-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
