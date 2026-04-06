# SemPKM

## What This Is

SemPKM is a semantics-native personal knowledge management platform where users store RDF data and interact with it through typed objects, relationships, and views — powered by installable "Mental Models" that bundle ontologies, SHACL shapes, views, and seed data into instant PKM experiences. It's a self-hosted web application with a Python/FastAPI backend and an htmx/vanilla-web frontend: admin portal for model and webhook management, IDE-style workspace for object creation and editing, multi-renderer data browsing (table, cards, graph, spatial canvas), Obsidian vault import, and decentralized identity (WebID + IndieAuth).

## Core Value

Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## Current State

**Active milestone:** M053 — Model Marketplace (in progress)

S01 complete: Admin → Mental Models page auto-discovers bundled models from /app/models/ and displays them as installable cards with one-click install. `scan_available_models()` scans for valid manifests, filters already-installed models, and returns metadata. Responsive card grid with htmx one-click install replaces the old text-input form (preserved as collapsed fallback).

S02 complete: Cloud-hosted model marketplace with full install pipeline. `MarketplaceRegistryService` fetches remote registry.json with 1-hour cache, SSRF guard on all outbound HTTP, SHA-256 hash verification before extraction, tar bomb/traversal protection via `tar_validator.py` (6 security checks + `data_filter`), and safe extraction to `/app/data/models/`. Admin UI has "Browse Marketplace" section with htmx lazy-load, model cards with install buttons and installed badges. `resolve_model_dir()` searches both bundled and downloaded model directories across 4 call sites. 54 unit tests (33 tar_validator + 21 marketplace_service).

Next: S03 adds version checking and update notifications for installed marketplace models.

**Last completed milestone:** M052 — UI Design System & Polish Pass (2026-04-06)

Established consistent visual identity across the Object Browser workspace. Kanban cards enriched with priority badges, due dates, and type icons via SHACL-driven `_detect_enrichment_fields()`; columns have keyword-based status color accents. Property tables have zebra striping with hover highlights and sh:description tooltips. Type badges show Lucide icons with per-type color accents. Active tabs visually distinct with bold weight, 3px accent bar, and box-shadow. View explorer uses 9 colored Lucide icons per renderer replacing Unicode glyphs. Body editor collapsed from dual light/dark CM6 themes to single CSS-var-driven definition. Form section headers have primary-color accent bars with raised backgrounds. Timeline bars show four status colors (done/active/blocked/cancelled). Right panel shows helpful empty state with info icon. 15 files changed, 708 insertions, 33/33 kanban tests pass.

## Architecture

- **Backend:** Python 3.12, FastAPI, async SQLAlchemy (SQLite/PostgreSQL), RDF4J triplestore via Docker
- **Frontend:** htmx, vanilla JS (IIFE modules under `window.SemPKM` namespace), Dockview workspace, CSS custom properties theming
- **Views:** 11 renderers (table, cards, kanban, graph, graph3D, calendar, timeline, map, OKR, BMC, quadrant, decision-matrix) with SHACL-driven type filtering
- **Mental Models:** `.sempkm-model` archives bundling ontology, shapes, rules, views, seed data, dashboards, workflows
- **Model Marketplace:** Remote JSON registry + .tar.gz archives, SHA-256 verified, downloaded to `/app/data/models/` on writable volume
