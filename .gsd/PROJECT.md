# SemPKM

## What This Is

SemPKM is a semantics-native personal knowledge management platform where users store RDF data and interact with it through typed objects, relationships, and views — powered by installable "Mental Models" that bundle ontologies, SHACL shapes, views, and seed data into instant PKM experiences. It's a self-hosted web application with a Python/FastAPI backend and an htmx/vanilla-web frontend: admin portal for model and webhook management, IDE-style workspace for object creation and editing, multi-renderer data browsing (table, cards, graph, spatial canvas), Obsidian vault import, and decentralized identity (WebID + IndieAuth).

## Core Value

Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## Current State

**Last completed milestone:** M052 — UI Design System & Polish Pass (2026-04-06)

Established consistent visual identity across the Object Browser workspace. Kanban cards enriched with priority badges, due dates, and type icons via SHACL-driven `_detect_enrichment_fields()`; columns have keyword-based status color accents. Property tables have zebra striping with hover highlights and sh:description tooltips. Type badges show Lucide icons with per-type color accents. Active tabs visually distinct with bold weight, 3px accent bar, and box-shadow. View explorer uses 9 colored Lucide icons per renderer replacing Unicode glyphs. Body editor collapsed from dual light/dark CM6 themes to single CSS-var-driven definition. Form section headers have primary-color accent bars with raised backgrounds. Timeline bars show four status colors (done/active/blocked/cancelled). Right panel shows helpful empty state with info icon. 15 files changed, 708 insertions, 33/33 kanban tests pass.

**Previous milestone:** M051 — Workspace UX Improvements (2026-04-06)

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
