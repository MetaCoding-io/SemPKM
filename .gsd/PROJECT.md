# SemPKM

## What This Is

SemPKM is a semantics-native personal knowledge management platform where users store RDF data and interact with it through typed objects, relationships, and views — powered by installable "Mental Models" that bundle ontologies, SHACL shapes, views, and seed data into instant PKM experiences. It's a self-hosted web application with a Python/FastAPI backend and an htmx/vanilla-web frontend: admin portal for model and webhook management, IDE-style workspace for object creation and editing, multi-renderer data browsing (table, cards, graph, spatial canvas), Obsidian vault import, and decentralized identity (WebID + IndieAuth).

## Core Value

Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## Current State

**Active milestone:** M050 — View System Rework (in progress)

S01 (Smart Type Dropdown) complete — replaced the 37-pill type bar with a renderer-filtered `<select>` dropdown across all 11 view templates. Kanban shows only types with status fields, calendar/timeline shows only types with date fields, map shows only types with geo fields. View Variants dropdown removed. S02 (Toolbar Cleanup + View Polish) and S03 (Save/Restore Flow + E2E Tests) remain.

**Previous milestone:** M049 — Backend Performance & Observability (2026-04-05)

Eliminated the sequential SPARQL query waterfall in object tab loads (3→1 queries, 5→1 label batches, asyncio.gather parallelization), added OpenTelemetry distributed tracing with Jaeger v2 backend, and built Server-Timing headers plus an admin performance dashboard with p50/p95/p99 percentile charts. 70 new tests. R001 (lazy-loaded panels) validated.

**Previous milestone:** M048 — Critical Bug Fixes (2026-04-05)

Fixed five showstopper bugs: broken Table/Cards view rendering (missing SPARQL PREFIX declarations in reconstructed queries), phantom save events (save now diff-based — only changed properties generate events), missing delete UI (toolbar + command palette + explorer hover with inbound edge cleanup), absent creation timestamps (auto-injected dcterms:created/modified on object creation), and Docker fresh-volume deploy failures (entrypoint script, consolidated lucene volume, triplestore readiness polling). 45 new unit tests across 4 test files.

## Requirements

### Validated

<!-- Shipped and confirmed valuable in v1.0. -->

- ✓ Event-sourced write path with immutable events as RDF named graphs — v1.0
- ✓ Materialized current graph state from event log — v1.0
- ✓ RDF4J triplestore via Docker Compose — v1.0
- ✓ SPARQL endpoint for reads with automatic graph scoping — v1.0
- ✓ Command API (object.create, object.patch, body.set, edge.create, edge.patch) — v1.0
- ✓ Async SHACL validation with lint panel (violations gate conformance ops) — v1.0
- ✓ SHACL-driven form generation from shapes — v1.0
- ✓ Mental Model manager (install/remove/list from .sempkm-model archives) — v1.0
- ✓ Mental Model manifest validation (schema, ID namespacing, reference integrity) — v1.0
- ✓ Starter Mental Model: Basic PKM (Projects, People, Notes, Concepts) — v1.0
- ✓ IDE-style workspace (Split.js panes, tabs, command palette, keyboard shortcuts) — v1.0
- ✓ Core renderers: object page, SHACL forms, table, cards, graph (2D) — v1.0
- ✓ View spec execution (SPARQL query + renderer + layout config) — v1.0
- ✓ Prefix registry and QName resolution (4-layer: user > model > LOV > built-in) — v1.0
- ✓ Label service (dcterms:title > rdfs:label > skos:prefLabel > schema:name > IRI fallback) — v1.0
- ✓ Admin portal (htmx): model management, webhook config, system status — v1.0
- ✓ Simple outbound webhooks (object.changed, edge.changed, validation.completed) — v1.0
- ✓ Passwordless multi-user auth (setup wizard, magic links, session-based) — v1.0
- ✓ RBAC: owner/member/guest roles with server-side enforcement — v1.0
- ✓ Event provenance: performed_by + performed_by_role on every user write — v1.0
- ✓ SQL data layer for auth (SQLite local, PostgreSQL cloud-ready) — v1.0

### Validated (v2.0)

- ✓ Read-only object view with CSS 3D flip to edit mode — v2.0
- ✓ VS Code-style split panes, bottom panel, collapsible sidebar — v2.0
- ✓ Dark mode with tri-state toggle — v2.0
- ✓ Global settings system — v2.0
- ✓ Event log explorer, LLM connection, guided tours — v2.0

### Validated (v2.1–v2.6 + M002–M049)

All features from v2.1 through v2.6 and milestones M002 through M049 validated. See REQUIREMENTS.md for full details.

Key milestones: Full-text search (v2.2), SPARQL console (v2.2), Dockview workspace (v2.3), OWL inference + SHACL-AF rules (v2.4), Obsidian import + WebID + IndieAuth (v2.5), Federation + VFS + Canvas (v2.6), Security hardening (M002), Knowledge organization (M003), Ontology system (M004), Platform polish (M005), Dashboards & workflows (M006–M007), Spatial canvas (M008), App platform (M009), RSS reader (M010), 4 mental models (M011), Workspace polish (M012), API surface (M013), Browser extension (M014–M015, M028), 9 sync apps (M016–M024), Demo instance (M025), Homepage (M026), Notion import (M027), Frontend performance (M029), Lint UX (M030), Saved views + kanban + graph3D + calendar + timeline + map (M031–M034), AI copilot (M035), Business planning models (M036), Mobile app (M037), Media scheduler (M038), RDF import (M039), Context rules (M040), Notifications (M041), SPARQL security (M043), Frontend cleanup (M044), Backend security (M045), E2E tests (M046), PPV model (M047), Critical bug fixes (M048), Backend performance & observability (M049), **View system rework (M050, in progress)**.
