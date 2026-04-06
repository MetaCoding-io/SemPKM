# SemPKM

## What This Is

SemPKM is a semantics-native personal knowledge management platform where users store RDF data and interact with it through typed objects, relationships, and views — powered by installable "Mental Models" that bundle ontologies, SHACL shapes, views, and seed data into instant PKM experiences. It's a self-hosted web application with a Python/FastAPI backend and an htmx/vanilla-web frontend: admin portal for model and webhook management, IDE-style workspace for object creation and editing, multi-renderer data browsing (table, cards, kanban, graph, spatial canvas), Obsidian vault import, and decentralized identity (WebID + IndieAuth).

## Core Value

Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## Current State

**Active milestone:** M055 — Browser History & Tab Recovery (in progress)

S01 (URL Sync & History Navigation) complete: wired History API pushState/popstate to dockview panel activation. URL reflects active tab via `?tab=` query parameter, browser back/forward navigates tab history, deep-link URLs open correct tabs on page load. 6 Playwright E2E tests pass. Requirements R015 (URL reflects active tab) and R016 (bookmarkable URLs) validated.

S02 (Closed Tab Recovery) pending.

**Previous milestone:** M054 — Explorer Composable Filter/Group/Sort (2026-04-06)

Replaced the flat OBJECTS explorer dropdown with a composable filter/group/sort engine. S01 built the core: `ExplorerConfig` dataclass with composable SPARQL query builders, config-options API returning SHACL-discovered properties, grouped tree rendering templates, and frontend config builder panel. S02 added server-side persistence: `ExplorerConfigSpec` model (migration 026), async CRUD service with By Type/By Tag preset seeding at startup, config selector UI with save/load/delete, Hierarchy pseudo-preset (`__hierarchy__` sentinel), localStorage persistence, and multi-panel OBJECTS sections with independent per-section state via Map keyed by DOM element. 66 tests pass. Requirements R011 (persistence), R012 (multi-panel), R013 (presets) validated.

## Architecture

- **Backend:** Python 3.12, FastAPI, async SQLAlchemy (SQLite/PostgreSQL), RDF4J triplestore via Docker
- **Frontend:** htmx, vanilla JS (IIFE modules under `window.SemPKM` namespace), Dockview workspace, CSS custom properties theming
- **Workspace URL:** `?tab=<panelId>` query parameter reflects active tab. History API pushState on tab switch, popstate for back/forward. Deep-link handler supports 9 tab ID formats (object IRIs, special:*, view:*, generic-view:*, dashboard:*, workflow:*, catalog:*, app-page:*, app-view:*). Two guard flags (`_historyReady`, `_navigatingFromHistory`) prevent history pollution during layout restore and popstate handling.
- **Explorer:** Composable config system with `ExplorerConfig` dataclass — filter/group/sort layers compose SPARQL independently. Config-options API exposes SHACL-derived type properties with `preferred_group` flags for enum-like properties. Server-side config persistence via `ExplorerConfigSpec` model with CRUD API and preset seeding. Multi-panel OBJECTS sections with per-section state Map and independent config selectors. `prop:` prefix convention distinguishes type-specific properties from built-in options.
- **Views:** 11 renderers (table, cards, kanban, graph, graph3D, calendar, timeline, map, OKR, BMC, quadrant, decision-matrix) with SHACL-driven type filtering
- **Mental Models:** `.sempkm-model` archives bundling ontology, shapes, rules, views, seed data, dashboards, workflows
- **Model Marketplace:** Remote JSON registry + .tar.gz archives, SHA-256 verified, downloaded to `/app/data/models/` on writable volume. `MarketplaceRegistryService` with 1-hour monotonic cache, SSRF guard, graceful offline fallback. Version checking with `packaging.version.Version` comparison and safe download-before-remove update flow.
- **Security:** SSRF guard (`validate_outbound_url()`), ZIP validator (`validate_zip_contents()`), tar validator (`validate_tar_contents()` + `safe_extract()`), rate limiting, audit logging, CSP headers
