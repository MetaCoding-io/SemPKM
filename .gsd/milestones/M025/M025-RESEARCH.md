# M025: Hosted Demo Instance — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

M025 is a deployment and content milestone — no new platform features required. The existing Docker Compose stack (3 services: triplestore, api, nginx) deploys unchanged to a VPS. Read-only enforcement is achievable at the nginx layer by blocking POST/PUT/DELETE/PATCH on write endpoints, requiring zero backend code changes. The existing Driver.js tour infrastructure (`frontend/static/js/tutorials.js`) provides the pattern for a demo-optimized tour. Sample data generation is the heaviest slice — the 5 existing Mental Models each ship seed data in JSON-LD, but the demo needs 30-50 richly interconnected objects with cross-model relationships that make the graph, table, and canvas views visually compelling.

The primary risk is the demo tour — it needs to work flawlessly for anonymous visitors on first load, with no pre-existing session state. The existing tours assume an authenticated user with the workspace loaded. A demo tour must handle auto-login (or bypass auth entirely) and guide visitors through a curated 3-minute path.

## Recommendation

**Slice ordering by risk:**
1. **Read-only enforcement** (nginx + optional env var) — prove the demo can't be corrupted before anything else
2. **Auto-login / anonymous access** — visitors must land in the workspace without setup wizard or login
3. **Sample data generation script** — create the 30-50 interconnected objects with bodies, edges, tags
4. **Demo-optimized Driver.js tour** — 3-minute "wow" flow highlighting graph, canvas, forms, validation
5. **Pre-built demo dashboard** — showcase cross-view context filtering
6. **Cloud deployment config** — docker-compose.demo.yml, SSL, DNS, periodic reset cron
7. **E2E tests + docs** — verify the demo flow, write landing page CTA copy

## Implementation Landscape

### Key Files

- `docker-compose.yml` — Base deployment config (3 services: triplestore, api, frontend). Demo compose file will extend this with read-only nginx config and demo environment variables.
- `frontend/nginx.conf` — All HTTP routing. Read-only enforcement goes here: block POST/PUT/DELETE/PATCH on `/api/commands`, `/api/commands/bulk`, `/browser/objects/*/body`, and all admin write routes. Return 403 JSON `{"error": "Demo instance is read-only"}`.
- `frontend/static/js/tutorials.js` — Existing Driver.js tours (Welcome 10-step, Create Object 4-step). Demo tour follows same IIFE pattern with `window.startDemoTour()`. Uses `driver.js@1.4.0` CDN in `base.html`.
- `backend/app/commands/router.py` — POST `/api/commands` and `/api/commands/bulk` are the **only write choke points** for object/edge/body mutations. Protected by `require_role_or_api("owner", "member")`.
- `backend/app/auth/` — Setup wizard, magic links, session management. Demo needs either: (a) pre-created demo user with auto-login cookie, or (b) `DEMO_MODE=true` env var that bypasses auth and returns a synthetic user.
- `models/*/seed/*.jsonld` — Existing seed data per model. Basic-pkm, CRM, Zettelkasten, Research, PPV all have seed JSON-LD. Demo script will generate additional interconnected objects using the Command API (or direct JSON-LD seed injection).
- `backend/app/dashboard/` — DashboardSpec model (SQLite JSON). Demo dashboard must be pre-created — either via migration script or API call at startup.
- `backend/app/browser/workspace.py` — Workspace template rendering. May need a `demo_mode` template variable to show tour auto-start and "Import your own vault" CTA banner.

### Write Endpoints to Block (nginx read-only)

All mutation endpoints discovered in the codebase:

```
# Command API (the primary write surface)
POST /api/commands
POST /api/commands/bulk

# Browser object mutations
POST /browser/objects/*/body          # body.set / body.diff
POST /browser/ontology/*             # class/property CRUD

# Admin mutations
POST /admin/models/*/install
POST /admin/models/*/uninstall
POST /admin/models/*/refresh-artifacts
POST /admin/apps/*

# SPARQL writes
POST /api/sparql/saved               # save queries
PUT  /api/sparql/saved/*
DELETE /api/sparql/saved/*

# Dashboard/Workflow CRUD
POST /api/dashboards
PUT  /api/dashboards/*
DELETE /api/dashboards/*
POST /api/workflows
PUT  /api/workflows/*
DELETE /api/workflows/*

# Federation
POST /api/federation/*
POST /api/inbox

# Comments, favorites, etc.
POST /browser/comments/*
POST /favorites/toggle
```

**Simplest approach:** Block all non-GET/HEAD/OPTIONS methods at nginx level for everything except `/api/health` and auth endpoints needed for auto-login. This is ~10 lines of nginx config.

### Auth Bypass for Demo

Two approaches investigated:

**Option A: Pre-seeded demo user + auto-login redirect** — Setup wizard runs on first boot, creates a "Demo Visitor" user. A startup script creates a long-lived session and sets a cookie. Visitors hitting the demo URL get redirected through a `/demo-login` endpoint that sets the session cookie and redirects to `/browser/`. Simpler but fragile — session expiry, cookie domain issues.

**Option B: `DEMO_MODE` env var** — When set, the `get_current_user` dependency returns a synthetic read-only user without checking session/cookie. No login page shown. Workspace loads immediately. More robust but requires a small backend change (~15 lines in `backend/app/auth/dependencies.py`).

**Recommendation: Option B** — It's a clean, testable change. The synthetic user gets `role: "guest"` which already has restricted permissions. Combined with nginx write-blocking, this is defense-in-depth.

### Sample Data Strategy

Existing seed data per model (from JSON-LD files):
- **basic-pkm**: Projects, People, Notes, Concepts, Tasks, Milestones (6 types)
- **CRM**: Contacts, Companies, Interactions, Deals (4 types, 12 seed objects)
- **Zettelkasten**: 5 note types with provenance chain
- **Research**: Papers, Claims, Evidence, Questions, Arguments (5 types)
- **PPV**: Projects, Areas, Resources, Archives

The demo needs ~30-50 objects with **cross-model edges** (e.g., a CRM Contact who is also a basic-pkm Person, a Research Paper cited in a Zettelkasten LiteratureNote). This requires a standalone Python script that:
1. Installs all 4 main models (basic-pkm, CRM, zettelkasten, research)
2. Creates demo objects via the Command API (or bulk endpoint)
3. Creates cross-model edges
4. Sets up tags, bodies with markdown content, and validation-triggering data (overdue task, stale contact, unprocessed note)

The script should be idempotent — check if demo data exists before creating.

### Demo Tour Design

The existing Welcome tour targets installed users who need feature orientation. The demo tour needs a different flow:

1. **Graph view** — "See your knowledge as a connected graph" (open graph, show interconnected nodes)
2. **Click a node** — "Every node is a typed object with properties" (open an object, show SHACL form)
3. **Validation** — "SemPKM validates your data automatically" (show lint panel with real warnings)
4. **Canvas** — "Arrange your knowledge spatially" (open pre-built canvas with embeds)
5. **Dashboard** — "Build dashboards that filter across views" (open demo dashboard)
6. **Multiple models** — "Install Mental Models for different workflows" (show models page)
7. **CTA** — "Ready to try it yourself?" (centered card with install link)

~7 steps, ~3 minutes. Each step auto-navigates (opening tabs, switching views) using existing `openTab()`, `window.location` patterns from the Create Object tour.

### Deployment Architecture

**Target: Single VPS (~$10-20/month)**
- Provider: Any Docker-capable VPS (Hetzner, DigitalOcean, Linode)
- `docker-compose.demo.yml` extending base compose with:
  - `DEMO_MODE=true` env var
  - Read-only nginx config override
  - SSL via Caddy reverse proxy (simpler than Let's Encrypt + certbot + nginx)
  - Periodic reset via cron (`docker compose down -v && docker compose up -d` every 24h)
- DNS: `demo.sempkm.app` A record pointing to VPS IP

**Caddy vs nginx for SSL:** Caddy handles Let's Encrypt automatically with zero config. Run Caddy on the host, proxy to Docker's nginx on port 3000. Avoids modifying nginx.conf for SSL.

### Dashboard Pre-creation

DashboardSpec is SQLite JSON (not RDF — per D105/D150). The demo dashboard must be created by the seed script after the database exists. Options:
- POST to `/api/dashboards` in the seed script
- Direct SQLAlchemy insert in a startup hook

The dashboard should demonstrate cross-view context filtering: a table view of Projects, clicking a row filters a Notes view below.

### Build Order

1. **S01: Read-only nginx + DEMO_MODE auth bypass** — Prove anonymous visitors can browse but not write. This is the foundation — everything else depends on it being solid.
2. **S02: Sample data generation script** — Create the 30-50 interconnected objects. Must run after models are installed. Script outputs to stdout for verification.
3. **S03: Demo tour + dashboard + CTA** — The user-facing experience. Depends on sample data existing.
4. **S04: Cloud deployment + E2E + docs** — docker-compose.demo.yml, Caddy SSL, DNS config, deployment script, reset cron. E2E test verifies the full demo flow. User guide page for self-hosters who want their own demo.

### Verification Approach

- **S01:** Start demo compose, verify: (a) visiting `/` lands in workspace without login, (b) POST to `/api/commands` returns 403, (c) all read routes work, (d) graph/table/canvas views render
- **S02:** Run seed script, verify: (a) 30-50 objects visible in explorer, (b) cross-model edges visible in Relations panel, (c) lint warnings fire for validation-triggering data, (d) graph view shows interconnected nodes
- **S03:** Load workspace, verify: (a) tour starts (auto or button), (b) completes in <3 min, (c) dashboard renders with filtering, (d) CTA banner visible
- **S04:** Deploy to VPS, verify: (a) HTTPS works, (b) full demo flow on public URL, (c) reset cron restores clean state

## Constraints

- **No backend feature changes** — M025 should not introduce new platform capabilities. DEMO_MODE is a configuration flag, not a feature.
- **Same Docker Compose stack** — Demo must use the identical 3-service architecture. No new containers except optional Caddy for SSL.
- **DashboardSpec is SQLite JSON** — Cannot bundle dashboards in Mental Model archives (D150). Must be created by seed script.
- **Auth system has no anonymous mode** — The `get_current_user` dependency always requires a valid session. DEMO_MODE needs to bypass this.
- **Driver.js loaded from CDN** — Tours depend on `driver.js@1.4.0` CDN availability. For demo reliability, consider vendoring the JS/CSS.

## Common Pitfalls

- **nginx write-blocking must be comprehensive** — Missing even one POST route allows data corruption. Use a default-deny approach: block all POST/PUT/DELETE/PATCH except a short allowlist (health check, auto-login).
- **Session cookie domain** — If demo runs at `demo.sempkm.app`, cookies set for `localhost` won't work. The auto-login or DEMO_MODE approach must handle the production domain.
- **Tour element selectors** — The demo tour will reference DOM elements that depend on data being loaded (e.g., objects in explorer, graph nodes). Timing issues between htmx loads and tour step rendering are the #1 fragility risk. Use lazy element functions (existing pattern in tutorials.js).
- **RDF4J cold start** — First request after container start takes 5-10s as RDF4J initializes indices. The health check handles this, but demo visitors hitting the URL immediately after a reset may see slow loads.
- **Periodic reset deletes volumes** — Any user-created bookmarks or session state is lost. The reset cron must be documented. Consider: reset only the triplestore + SQLite volumes, keep nginx/Caddy state.

## Open Risks

- **Multi-visitor isolation** — If DEMO_MODE creates a single shared session, all visitors see the same state. With read-only enforcement, this is acceptable (no writes = no corruption). But if two visitors trigger the tour simultaneously, Driver.js popover positioning may conflict. Mitigation: tour is per-browser-tab, no shared state.
- **Hosting cost creep** — RDF4J with LuceneSail needs ~512MB-1GB RAM. Combined with FastAPI + nginx, minimum viable VPS is 2GB RAM (~$10-12/month). If traffic spikes, the single VPS will struggle. Mitigation: monitor with uptime check, scale only if needed.
- **Tour maintenance burden** — DOM selectors change as the UI evolves. The demo tour will need updates whenever workspace layout changes. Mitigation: use stable IDs (already present in workspace.html) and lazy element functions.

## Candidate Requirements

Based on CONTEXT.md scope and research findings:

| ID | Requirement | Type |
|----|-------------|------|
| DEMO-01 | Anonymous visitors can access workspace without login | table-stakes |
| DEMO-02 | All write operations blocked at nginx level (403 response) | table-stakes |
| DEMO-03 | 30-50 interconnected sample objects across 4+ Mental Models | table-stakes |
| DEMO-04 | Demo-optimized Driver.js tour completes in <3 minutes | table-stakes |
| DEMO-05 | Pre-built demo dashboard with cross-view context filtering | expected |
| DEMO-06 | "Try SemPKM" CTA banner visible after tour completion | expected |
| DEMO-07 | Docker Compose demo config with SSL termination | table-stakes |
| DEMO-08 | Periodic data reset (cron or container restart) | expected |
| DEMO-09 | Basic uptime monitoring (health check endpoint) | expected |
| DEMO-10 | Validation warnings visible on seed data (overdue task, stale contact) | expected |

**Not required for M025:** Multi-tenant isolation, user accounts, write capabilities, auto-scaling, SaaS infrastructure.

## Sources

- `docker-compose.yml` — Base 3-service deployment (triplestore, api, frontend)
- `docker-compose.test.yml` — Alternate compose pattern with separate volumes/ports
- `frontend/nginx.conf` — Complete routing config (~200 lines), all proxy rules
- `frontend/static/js/tutorials.js` — Driver.js tour infrastructure (Welcome + Create Object tours)
- `backend/app/commands/router.py` — Command API write surface (`require_role_or_api` guard)
- `models/*/seed/*.jsonld` — Existing seed data across 5 models
- `backend/app/auth/dependencies.py` — Auth dependency chain (`get_current_user`, `require_role_or_api`)
