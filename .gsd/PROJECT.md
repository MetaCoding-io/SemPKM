# SemPKM

## What This Is

SemPKM is a semantics-native personal knowledge management platform where users store RDF data and interact with it through typed objects, relationships, and views — powered by installable "Mental Models" that bundle ontologies, SHACL shapes, views, and seed data into instant PKM experiences. It's a self-hosted web application with a Python/FastAPI backend and an htmx/vanilla-web frontend: admin portal for model and webhook management, IDE-style workspace for object creation and editing, multi-renderer data browsing (table, cards, kanban, graph, spatial canvas), Obsidian vault import, and decentralized identity (WebID + IndieAuth).

## Core Value

Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## Current State

**Last completed milestone:** M053 — Model Marketplace (2026-04-06)

Built a cloud-hosted model marketplace enabling one-click model discovery and installation from an in-app admin UI without filesystem access. Admin → Mental Models page auto-discovers bundled models as installable cards. Browse Marketplace section fetches a remote JSON registry with model cards, install buttons, and installed badges. Full security pipeline: SSRF guard on all outbound HTTP, SHA-256 hash verification, tar bomb/traversal protection (33 unit tests). Downloaded models persist in `/app/data/models/` on writable volume. Version checking with `packaging.version.Version` — green "Up to date" / amber "Update available" badges with safe download-before-remove update flow. 63 unit tests total (33 tar_validator + 30 marketplace_service). 16 source files, 2335 lines changed.

**Previous milestone:** M052 — UI Design System & Polish Pass (2026-04-06)

Established consistent visual identity across the Object Browser workspace. Kanban cards enriched with priority badges, due dates, and type icons. Property tables have zebra striping with hover highlights. Type badges show Lucide icons. Active tabs visually distinct. View explorer uses colored Lucide icons. Body editor uses single CSS-var-driven CM6 theme. Form section headers have accent bars. Timeline bars show four status colors. 15 files changed, 708 insertions.

## Architecture

- **Backend:** Python 3.12, FastAPI, async SQLAlchemy (SQLite/PostgreSQL), RDF4J triplestore via Docker
- **Frontend:** htmx, vanilla JS (IIFE modules under `window.SemPKM` namespace), Dockview workspace, CSS custom properties theming
- **Views:** 11 renderers (table, cards, kanban, graph, graph3D, calendar, timeline, map, OKR, BMC, quadrant, decision-matrix) with SHACL-driven type filtering
- **Mental Models:** `.sempkm-model` archives bundling ontology, shapes, rules, views, seed data, dashboards, workflows
- **Model Marketplace:** Remote JSON registry + .tar.gz archives, SHA-256 verified, downloaded to `/app/data/models/` on writable volume. `MarketplaceRegistryService` with 1-hour monotonic cache, SSRF guard, graceful offline fallback. Version checking with `packaging.version.Version` comparison and safe download-before-remove update flow.
- **Security:** SSRF guard (`validate_outbound_url()`), ZIP validator (`validate_zip_contents()`), tar validator (`validate_tar_contents()` + `safe_extract()`), rate limiting, audit logging, CSP headers
