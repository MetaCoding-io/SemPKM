# SemPKM

## What This Is

SemPKM is a semantics-native personal knowledge management platform where users store RDF data and interact with it through typed objects, relationships, and views — powered by installable "Mental Models" that bundle ontologies, SHACL shapes, views, and seed data into instant PKM experiences. It's a self-hosted web application with a Python/FastAPI backend and an htmx/vanilla-web frontend: admin portal for model and webhook management, IDE-style workspace for object creation and editing, multi-renderer data browsing (table, cards, graph, spatial canvas), Obsidian vault import, and decentralized identity (WebID + IndieAuth).

## Core Value

Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## Current State

**Last completed milestone:** M051 — Workspace UX Improvements (2026-04-06)

Fixed six workspace interaction paper-cuts: global dropdown dismiss/escape via new `dropdown-dismiss.js` (click-outside, Escape, position:fixed repositioning escaping dockview overflow), stripped ' Shape' suffix from explorer type labels at the backend, replaced stale event log placeholder, enriched VFS mount dropdown with human-readable model titles, added object tab refresh button, fixed command palette scroll jump, replaced fragile shadow-DOM persona/layout input hacks with reusable `showInputDialog()` using native `<dialog>`, and fixed admin graph popover positioning. 10 files changed, 388 insertions.

**Previous milestone:** M050 — View System Rework (2026-04-05)

Replaced the 37-pill type bar with renderer-filtered smart dropdowns across all 11 view templates, removed the confusing View Variants concept, fixed calendar dark mode nav icons via FC6 custom properties, added timeline popover dismiss on Escape/click-outside, and repaired the save/restore view flow with E2E coverage. Key additions: `get_compatible_types()` on ViewSpecService reuses SHACL introspection to filter types by renderer compatibility, `type_filter_dropdown.html` partial, `openGenericViewTab()` selectedType parameter for saved view restoration.

**Previous milestone:** M049 — Backend Performance & Observability (2026-04-05)

Eliminated the sequential SPARQL query waterfall in object tab loads (3→1 queries, 5→1 label batches, asyncio.gather parallelization), added OpenTelemetry distributed tracing with Jaeger v2 backend, and built Server-Timing headers plus an admin performance dashboard with p50/p95/p99 percentile charts. 70 new tests. R001 (lazy-loaded panels) validated.

## Architecture

- **Backend:** Python 3.12, FastAPI, async SQLAlchemy (SQLite/PostgreSQL), RDF4J triplestore via Docker
- **Frontend:** htmx, vanilla JS (IIFE modules under `window.SemPKM` namespace), Dockview workspace, CSS custom properties theming
- **Views:** 11 renderers (table, cards, kanban, graph, graph3D, calendar, timeline, map, OKR, BMC, quadrant, decision-matrix) with SHACL-driven type filtering
- **Mental Models:** `.sempkm-model` archives bundling ontology, shapes, rules, views, seed data, dashboards, workflows
- **Apps:** SDK-based platform apps (RSS, Linear, GitHub, Monday, Todoist, YouTube, Spotify, Podcast, Media Scheduler)
- **Mobile:** Expo SDK 55 React Native app with geofencing, pedometer, calendar integration
- **AI:** Copilot with streaming SSE, SPARQL generation, conversation persistence
- **Security:** SSRF guards, ZIP validation, rate limiting, audit logging, SPARQL injection prevention, CSP headers
- **Observability:** OpenTelemetry tracing (Jaeger), Server-Timing headers, admin performance dashboard
