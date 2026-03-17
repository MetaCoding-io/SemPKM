---
depends_on: [M011]
---

# M025: Hosted Demo Instance

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

A pre-populated, publicly accessible SemPKM instance that lets prospective users explore the product without installing Docker. Pre-loaded with all Mental Models (basic-pkm v2, CRM, Zettelkasten+, Research Workflow) and 30-50 interconnected sample objects. Includes an optimized guided tour (Driver.js) for first-time visitors and a pre-built dashboard showing graph, table, and canvas together.

## Why This Milestone

Docker is the #1 conversion barrier. Users who would love SemPKM never discover that because they bounce at "docker compose up." A live demo instance removes this wall entirely — click a link, explore for 3 minutes, see the value, then decide to self-host.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Visit a public URL (e.g., demo.sempkm.app) and land in a pre-populated workspace
- Take a guided tour (Driver.js) optimized for first-time visitors showing the graph, table, canvas, and SHACL forms
- Explore 30-50 interconnected objects across 4 Mental Models
- See a pre-built dashboard combining project overview, task hub, and knowledge graph
- See typed relationships, validation warnings, and inference in action
- Click "Import your own vault" CTA at the end of the tour
- NOT be able to modify the demo data (read-only or periodic reset)

### Entry point / environment

- Entry point: Public URL (e.g., `https://demo.sempkm.app`)
- Environment: Cloud-hosted (VPS or container service)
- Live dependencies involved: RDF4J triplestore, nginx, API server

## Completion Class

- Contract complete means: demo instance deploys reliably, sample data loads correctly, tour completes without errors
- Integration complete means: all 4 models installed and functional, sample objects demonstrate cross-model relationships, dashboard renders with real data
- Operational complete means: instance stays up, handles concurrent visitors, resets periodically (or is read-only), costs are manageable

## Final Integrated Acceptance

- New visitor visits the URL, tour starts automatically, completes in under 3 minutes
- Visitor can browse objects, open views, explore the graph, see the spatial canvas
- Validation warnings appear on seed data (overdue task, stale contact, unprocessed fleeting note)
- Demo resets or stays read-only so visitors don't see other visitors' test data

## Risks and Unknowns

- **Hosting cost** — RDF4J + API server + nginx. Minimum viable: single small VPS (~$10-20/month).
- **Multi-visitor isolation** — If writable, visitors corrupt each other's experience. Options: read-only mode, per-session isolated instances (expensive), periodic reset (simple).
- **Tour optimization** — Existing Driver.js tours target installed users. Demo tour needs different flow emphasizing "wow" moments over feature training.

## Existing Codebase / Prior Art

- `frontend/static/js/tours.js` — Existing Driver.js tour infrastructure
- `docker-compose.yml` — Docker deployment (basis for cloud deployment)
- M011 — Mental Models with sample data

## Relevant Requirements

- New: DEMO-01 (hosted instance), DEMO-02 (guided tour), DEMO-03 (sample data)

## Scope

### In Scope

- Cloud deployment configuration (Docker Compose for VPS or Fly.io/Railway)
- Sample data generation script (30-50 objects across 4 models with rich relationships)
- Demo-optimized Driver.js tour (3-minute "wow" flow)
- Pre-built demo dashboard
- Read-only mode or periodic reset mechanism
- SSL/TLS via Let's Encrypt or cloud provider
- Basic monitoring (uptime check)

### Out of Scope / Non-Goals

- Multi-tenant SaaS platform
- User accounts on the demo (anonymous access only)
- Write capabilities for visitors (read-only)
- High-availability / auto-scaling
- Paid hosting infrastructure (keep costs minimal)

## Technical Constraints

- Same Docker Compose stack as local dev (api + triplestore + nginx)
- Minimal cloud infrastructure (single VPS or container)
- SSL termination required
- Read-only enforcement at API level or nginx level

## Integration Points

- **M011 Mental Models** — all 4 models installed with sample data
- **Driver.js** — tour infrastructure already exists
- **DashboardSpec** — pre-built demo dashboard
- **Docker Compose** — deployment configuration
