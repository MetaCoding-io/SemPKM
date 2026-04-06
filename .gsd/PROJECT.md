# SemPKM

## What This Is

SemPKM is a semantics-native personal knowledge management platform where users store RDF data and interact with it through typed objects, relationships, and views — powered by installable "Mental Models" that bundle ontologies, SHACL shapes, views, and seed data into instant PKM experiences. It's a self-hosted web application with a Python/FastAPI backend and an htmx/vanilla-web frontend: admin portal for model and webhook management, IDE-style workspace for object creation and editing, multi-renderer data browsing (table, cards, kanban, graph, spatial canvas), Obsidian vault import, and decentralized identity (WebID + IndieAuth).

## Core Value

Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## Current State

**Active milestone:** M056 — Ontology Visualization Overhaul (in progress)

S01 complete: TBox Graph API + Hierarchical Rendering + Detail Panel. The Ontology Viewer TBox tab now shows a Cytoscape.js hierarchical graph with gist classes at the top and model types below, a graph/tree toggle, and a bottom detail panel for class properties on node click. S02 (multi-model filtering, visual polish, persistence) is next.

**Previous milestone:** M055 — Browser History & Tab Recovery (2026-04-06)

Wired History API to dockview workspace — URL reflects active tab via `?tab=`, browser back/forward navigates tab history, deep-link URLs open correct tabs, and Ctrl+Shift+T recovers closed tabs from a 20-entry LIFO stack. 10 E2E tests pass across Chromium and Firefox. Requirements R014-R017 validated.

## Architecture

- **Backend:** Python 3.12, FastAPI, async SQLAlchemy (SQLite/PostgreSQL), RDF4J triplestore via Docker
- **Frontend:** htmx, vanilla JS (IIFE modules under `window.SemPKM` namespace), Dockview workspace, CSS custom properties theming
- **Workspace URL:** `?tab=<panelId>` query parameter reflects active tab. History API pushState on tab switch, popstate for back/forward. Deep-link handler supports 9 tab ID formats (object IRIs, special:*, view:*, generic-view:*, dashboard:*, workflow:*, catalog:*, app-page:*, app-view:*). Two guard flags (`_historyReady`, `_navigatingFromHistory`) prevent history pollution during layout restore and popstate handling.
- **Closed Tab Recovery:** Module-private `_closedTabStack` (20-entry max LIFO) in workspace-layout.js captures panel metadata in `onDidRemovePanel`. `reopenClosedTab()` dispatches to correct opener for all tab types. Skip-and-try-next when tab already open. Ctrl+Shift+T shortcut + command palette entry.
- **Ontology Viewer:** TBox tab shows Cytoscape.js hierarchical graph (dagre TB layout) as primary view with graph/tree toggle. `GET /browser/ontology/tbox/graph-data` returns all TBox classes with subClassOf edges as Cytoscape-compatible {nodes, edges} JSON. Source-based node coloring (gist=slate, models=palette, user=teal). Node click loads class detail in bottom panel. Theme switching via `sempkm:theme-changed`. Cleanup registered via `SemPKM.registerCleanup()`.
- **Explorer:** Composable config system with `ExplorerConfig` dataclass — filter/group/sort layers compose SPARQL independently. Config-options API exposes SHACL-derived type properties with `preferred_group` flags for enum-like properties. Server-side config persistence via `ExplorerConfigSpec` model with CRUD API and preset seeding. Multi-panel OBJECTS sections with per-section state Map and independent config selectors. `prop:` prefix convention distinguishes type-specific properties from built-in options.
- **Views:** 11 renderers (table, cards, kanban, graph, graph3D, calendar, timeline, map, OKR, BMC, quadrant, decision-matrix) with SHACL-driven type filtering
- **Mental Models:** `.sempkm-model` archives bundling ontology, shapes, rules, views, seed data, dashboards, workflows
- **Model Marketplace:** Remote JSON registry + .tar.gz archives, SHA-256 verified, downloaded to `/app/data/models/` on writable volume. `MarketplaceRegistryService` with 1-hour monotonic cache, SSRF guard, graceful offline fallback. Version checking with `packaging.version.Version` comparison and safe download-before-remove update flow.
- **Security:** SSRF guard (`validate_outbound_url()`), ZIP validator (`validate_zip_contents()`), tar validator (`validate_tar_contents()` + `safe_extract()`), rate limiting, audit logging, CSP headers
