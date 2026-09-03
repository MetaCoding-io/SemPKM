# SemPKM Codebase Guide

**Last updated:** 2026-09-03

> **Keeping this file honest:** when a milestone adds a backend module, a top-level
> directory, a Mental Model, or a Compose stack, update this file (and the
> `.planning/codebase/` deep-dives) in the same change. Sanity-check the module
> list against `ls backend/app` — this map intentionally avoids exact file/line
> counts because those rot fastest.

## Overview

SemPKM is an event-sourced RDF knowledge graph application with htmx server-side rendering. It provides an IDE-style workspace for creating, browsing, and exploring structured knowledge through auto-generated forms, views, and graph visualizations.

The dev stack runs four Docker services: a **FastAPI backend** (Python, host port 8001), an **nginx frontend** (static assets + reverse proxy, host port 4000), an **RDF4J triplestore** (SPARQL graph database), and **Jaeger** (tracing). All writes flow through a single `POST /api/commands` endpoint into an immutable event store with current-state materialization. All reads query `urn:sempkm:current` via SPARQL and render Jinja2/htmx partials.

Domain schemas are pluggable **Mental Models** (OWL ontology + SHACL shapes + view specs + dashboards/workflows + seed data) installed at runtime from the bundled catalog or the remote marketplace. Beyond the web app, the repo ships **first-party platform apps** (`apps/` — sync integrations, RSS reader, media scheduler), a **browser extension** (`extension/`), and an **Expo mobile companion** (`mobile/`).

---

## Directory Layout

```
SemPKM/
├── backend/                       # FastAPI Python backend
│   ├── app/                       # Application package (~39 modules, see tables below)
│   ├── migrations/                # Alembic SQL migrations
│   ├── ontologies/                # Bundled base ontologies (gist)
│   └── pyproject.toml             # Python dependencies
├── frontend/                      # Nginx static server + auth pages
│   ├── static/css/                # CSS (theme tokens, workspace, per-view styles)
│   ├── static/js/                 # Vanilla JS modules (window.SemPKM namespace)
│   ├── login.html / setup.html / invite.html
│   └── nginx.conf                 # Reverse proxy config
├── apps/                          # First-party platform apps (run by the app platform)
│   │                              #   linear-sync, github-sync, jira-sync, monday-sync,
│   │                              #   asana-sync, todoist-sync, google-calendar,
│   │                              #   outlook-calendar, caldav-calendar,
│   │                              #   rss-reader, media-scheduler, test-app
├── extension/                     # WebExtension (Chrome + Firefox manifests):
│   │                              #   sidebar, popup, content scripts, AI insights
├── mobile/                        # Expo/React Native companion app (context reporting)
├── models/                        # Mental Model bundles (see Mental Models below)
├── config/rdf4j/                  # RDF4J repository config (TTL)
├── docs/guide/                    # User guide (50+ markdown chapters + HTML viewer)
├── e2e/                           # Playwright E2E tests (tests/, fixtures/, helpers/, scripts/)
├── scripts/                       # Dev utilities (reset-instance.sh, ...)
├── .gsd/                          # Milestone/requirements tracking (PROJECT.md is the
│                                  #   up-to-date architecture snapshot)
├── .planning/codebase/            # Deep-dive architecture docs (see references below)
├── docker-compose.yml             # Dev stack (see Docker Stacks below for the others)
├── docker-compose.{test,test-ollama,demo,cloud,federation-test}.yml
└── Caddyfile.cloud / Caddyfile.demo
```

---

## Backend Modules

All modules live under `backend/app/`. Standard shape per module: `__init__.py`, `router.py`, `service.py`, `models.py`, `schemas.py` (subset as needed).

### Core

| Module | Purpose |
|--------|---------|
| `main` | App factory, lifespan startup, router registration |
| `config` | Pydantic BaseSettings (env vars) |
| `dependencies` | FastAPI DI functions (pull from `app.state`) |
| `db` | SQLAlchemy engine, async session, Base model |
| `rdf` | IRI minting, JSON-LD parsing, namespace definitions |
| `triplestore` | RDF4J async HTTP client + repository setup |
| `sparql` | SPARQL passthrough router + `scope_to_current_graph()` |
| `middleware` | ETag conditional GET for JSON APIs, request timing + admin report |
| `security` | SSRF guard (`validate_outbound_url`), ZIP-bomb and tar validators |

### Commands and Events

| Module | Purpose |
|--------|---------|
| `commands` | Write command API (single `POST /api/commands` endpoint): router, dispatcher, typed handlers |
| `events` | Event store: immutable named graphs + current-state materialization, diff/undo support |

### Services and Knowledge

| Module | Purpose |
|--------|---------|
| `services` | Domain service singletons: labels, shapes, webhooks, settings, search (Lucene), LLM connection, marketplace registry, ops log, email, icons, prefixes |
| `models` | Mental Model loader, registry, manifest validation, bundled-model discovery |
| `views` | ViewSpec service + paginated SPARQL query execution for all view renderers |
| `validation` | Background SHACL validation queue (asyncio worker) |
| `inference` | OWL 2 RL forward-chaining inference engine |
| `lint` | Structured SHACL lint results (paginated API, SSE stream) |
| `ontology` | Ontology viewer endpoints: TBox class graph/tree, ABox, RBox, user-created classes |

### Auth, Identity, and Federation

| Module | Purpose |
|--------|---------|
| `auth` | Passwordless magic-link auth, sessions, roles (owner/member), teams |
| `indieauth` | IndieAuth OAuth2 provider (authorization code + PKCE) |
| `webid` | WebID profile (username, Ed25519 keys, link management, public page) |
| `federation` | Instance-to-instance federation: shared graphs, WebFinger, LDN inbox, RFC 9421 HTTP Message Signatures, RDF Patch sync (see [user guide ch. 51](docs/guide/51-federation.md)) |

### UI Routers

| Module | Purpose |
|--------|---------|
| `browser` | Main IDE-style workspace (nav tree, object tabs, forms, views, lint, explorer configs) |
| `admin` | Admin portal (models + marketplace, webhooks, users, teams, API keys, applications, federation SPARQL-endpoint allowlist) |
| `shell` | Top-level navigation pages, Docs & Tutorials hub (`GUIDE_SECTIONS` chapter registry) |
| `debug` | SPARQL console, command executor (dev only) |
| `api` | External API surface: well-known discovery, types/shapes/context-query endpoints |

### Features

| Module | Purpose |
|--------|---------|
| `canvas` | Spatial canvas workspace (save/load, RDF neighbor loading) |
| `dashboard` | DashboardSpec CRUD + GridStack dashboard builder/renderer |
| `workflow` | WorkflowSpec CRUD + step-by-step workflow runner/builder |
| `apps` | App platform: manifest validation, subprocess lifecycle manager, scheduler, proxy, tokens, admin routes |
| `copilot` | AI Copilot chat — natural-language SPARQL generation and execution |
| `obsidian` | Obsidian vault import (ZIP upload, scan, streaming progress) |
| `notion` | Notion workspace ZIP import (scanner, models, router) |
| `rdf_import` | Generic RDF data import: format detection, parsing, subject extraction |
| `vfs` | Virtual filesystem / WebDAV (file browser, collections, resources) |
| `context` | Context awareness: user location/activity/time tracking (feeds mobile + overlay) |
| `persona` | Workspace persona management (named layout/sidebar/explorer configurations) |
| `favorites` | Starred objects (SQLAlchemy model) |
| `task_templates` | RDF-backed reusable task template CRUD |
| `monitoring` | PostHog error middleware (captures 5xx exceptions) |
| `health` | Health check endpoint (`GET /api/health`) |

---

## Frontend Assets

Vanilla JS modules under `frontend/static/js/` (IIFE, `window.SemPKM` namespace), bundled with esbuild — no SPA framework. Grouped by area:

| Area | Files |
|------|-------|
| Bootstrap & shared | `app.js`, `api-fetch.js`, `auth.js`, `cleanup.js`, `sempkm-shims.js`, `dropdown-dismiss.js`, `posthog.js`, `theme.js` |
| Workspace shell | `workspace.js`, `workspace-layout.js` (Dockview, deep links, closed-tab recovery), `sidebar.js`, `named-layouts.js`, `explorer-config.js`, `context-indicator.js`, `tutorials.js` |
| Editing | `editor.js` (command dispatch), `markdown-render.js` (marked.js + DOMPurify), `recurrence-editor.js`, `column-prefs.js` |
| View renderers | `graph.js` (Cytoscape), `kanban.js`, `calendar.js`, `okr.js`, `bmc.js`, `quadrant.js`, `decision-matrix.js` |
| Feature panels | `canvas.js` (spatial canvas), `ontology-graph.js` (TBox graph), `federation.js` (collab/inbox panels), `copilot.js`, `sparql-console.js`, `vfs-browser.js`, `settings.js` |

CSS under `frontend/static/css/` follows the same split: base (`style.css`, `theme.css` — light/dark tokens), workspace (`workspace.css`, `dockview-sempkm-bridge.css`, `forms.css`, `views.css`), and one file per feature panel/renderer (`federation.css`, `copilot.css`, `explorer-config.css`, `okr.css`, `bmc.css`, `quadrant.css`, `decision-matrix.css`, `context-indicator.css`, `import.css`, `vfs-browser.css`, `settings.css`).

---

## Templates

Jinja2 templates under `backend/app/templates/` (rendered full-page or as htmx fragments via `jinja2-fragments`):

```
backend/app/templates/
├── base.html / base_embed.html   # Base layouts (htmx, CDN scripts, sidebar)
├── admin/        # Admin portal (models, marketplace, webhooks, users, apps, federation endpoints)
├── browser/      # Workspace: nav tree, object tabs, views, lint, canvas, dashboards,
│                 #   workflows, ontology viewer, federation panels (largest group)
├── components/   # Shared partials (_sidebar.html, _tabs.html)
├── debug/        # SPARQL console, command executor
├── errors/       # Error pages
├── forms/        # SHACL-driven form partials
├── importer/     # Generic import UI shared pieces
├── indieauth/    # IndieAuth authorization consent UI
├── notion/       # Notion import wizard
├── obsidian/     # Obsidian import wizard
├── rdf_import/   # RDF import wizard
└── webid/        # WebID public profile page
```

---

## Mental Models

Mental Models are pluggable domain schemas containing:
- `manifest.yaml` — metadata (modelId, version, namespace, entrypoints, icons)
- `ontology/` — OWL ontology (JSON-LD)
- `shapes/` — SHACL shapes for auto-generated forms (JSON-LD)
- `views/` — ViewSpec definitions for the view renderers (JSON-LD)
- `seed/` — Seed data objects (JSON-LD)
- optionally dashboards, workflows, and rules

**Bundled models** (`models/`, mounted read-only at `/app/models/`):

| Model | Domain |
|-------|--------|
| `basic-pkm` | Starter PKM: Notes, Projects, Concepts, Persons |
| `zettelkasten` | Zettelkasten note-taking (fleeting/literature/permanent notes) |
| `research` | Research workflow (papers, claims, research questions) |
| `crm` | Contacts, companies, deals, interactions |
| `business-planning` | OKRs, Business Model Canvas, decision matrices |
| `ppv` | Pillars–Pipelines–Vaults personal productivity |
| `rss-feeds` | Types backing the RSS Reader app |
| `media-scheduler` | Types backing the Media Scheduler app |

Models install via the admin UI (bundled catalog card grid) or from the **remote marketplace** (`MarketplaceRegistryService`: JSON registry + SHA-256-verified `.tar.gz` archives, version checking, downloads to `/app/data/models/`). Each model's artifacts land in named graphs: `urn:sempkm:model:{id}:ontology`, `:shapes`, `:views`, `:seed`.

---

## E2E Tests

Playwright specs under `e2e/tests/`, grouped by numbered directory (55+ directories; run `ls e2e/tests` for the current list):

| Range | Test Areas |
|-------|-----------|
| `00`–`08` | Setup/auth, object CRUD + edges, view renderers, navigation/tabs/shortcuts, validation/lint, admin portal, settings, multi-user, search |
| `09`–`17` | Inference, lint dashboard, helptext, regressions, VFS, Obsidian import, WebID, IndieAuth, spatial canvas |
| `18`–`23` | Federation (UI + two-instance sync), explorer modes, favorites/tags/VFS explorer, comments, ontology viewer, class creation |
| `24`–`30` | Tag hierarchy, browser extension, ops log, mental models + marketplace, event log, body diff, personas, API surface, app platform |
| `31`–`47` | Sync apps (Linear, GitHub, Jira, Monday, Asana, Todoist, Google/Outlook/CalDAV calendars), RSS reader, business planning, dashboard blocks, copilot, PPV |
| `50`–`99` | Hosted demo, browser history, media scheduler, Notion import, rate limiting |
| `screenshots/` | Marketing + guide screenshot capture |

**Run:** `cd e2e && npx playwright test --project=chromium` against the test stack (`docker compose -f docker-compose.test.yml up -d --build`, sequential, 1 worker). Federation specs need the federation stack (`--project=federation`).

---

## Docker Stacks

Dev stack (`docker-compose.yml`):

| Service | Image | Host Port | Purpose |
|---------|-------|-----------|---------|
| `triplestore` | `eclipse/rdf4j-workbench:5.0.1` | (internal) | RDF4J SPARQL graph database |
| `api` | Custom (`./backend` Dockerfile) | 8001 | FastAPI backend (uvicorn, hot-reload) |
| `frontend` | `nginx:stable-alpine` | 4000 | Static assets + reverse proxy to API |
| `jaeger` | `jaegertracing/all-in-one` | 16686 (UI), 4318 (OTLP) | Distributed tracing |

**Key volumes:** `rdf4j_data` (triplestore persistence), `sempkm_data` (SQLite + secrets), plus hot-reload bind mounts (see [CLAUDE.md](CLAUDE.md) — Python, templates, CSS, JS, and migrations reload without a rebuild).

Additional self-contained stacks (ports and purposes in the [README](README.md#docker-stacks)): `docker-compose.test.yml` (E2E target with ~10 mock integration APIs; `test-ollama` variant swaps the mock LLM for real Ollama), `demo` (read-only public demo), `cloud` (Caddy TLS overlay), and `federation-test` (two full instances side by side).

---

## Data Flow

### Write Flow

```
Browser JS (editor.js)
  |  POST /api/commands {command: "object.create", params: {...}}
  v
nginx (port 4000) --> proxy_pass --> FastAPI (port 8000)
  |
  v
commands/router.py --> dispatcher.py --> handlers/{command}.py
  |  Returns Operation (data_triples + materialize_inserts)
  v
events/store.py EventStore.commit()
  |  1. Begin RDF4J transaction
  |  2. Insert event triples into urn:sempkm:event:{uuid}
  |  3. Materialize into urn:sempkm:current (or a target graph, e.g. a shared graph)
  |  4. Commit transaction (atomic)
  v
Async: ValidationQueue.enqueue() + WebhookService.dispatch()
```

### Read Flow

```
Browser htmx (hx-get="/browser/object-tab?iri=...")
  |
  v
nginx --> FastAPI browser/router.py
  |  SPARQL SELECT FROM <urn:sempkm:current>
  |  via TriplestoreClient.query()
  v
LabelService.resolve_batch() (TTL-cached)
  |
  v
Jinja2 renders template (full page or htmx partial)
  |
  v
HTML response (hx-swap into DOM)
```

---

## Key Conventions

- **Single write path:** All data mutations go through `POST /api/commands` — never direct SPARQL UPDATE
- **Event sourcing:** Every write creates an immutable named graph event; current state is materialized. The event log UI supports per-event diff and undo
- **Module structure:** Each module follows `__init__.py`, `router.py`, `service.py`, `models.py`, `schemas.py`
- **Service injection:** Services are singletons on `app.state.*`, injected via FastAPI `Depends()` from `dependencies.py`
- **htmx partials:** Routes serve both full pages and htmx fragments using `jinja2-fragments` block rendering
- **Graph scoping:** All SPARQL reads use `scope_to_current_graph()` to prevent event graph data leaking; shared graph membership adds extra `FROM` clauses
- **Named graphs:** `urn:sempkm:current` (state), `urn:sempkm:event:{uuid}` (events), `urn:sempkm:model:{id}:{artifact}` (models), `urn:sempkm:inferred` (inference), `urn:sempkm:shared:{uuid}` (federation shared graphs), `urn:sempkm:inbox:{uuid}` (LDN notifications)
- **Label precedence:** `dcterms:title > rdfs:label > skos:prefLabel > schema:name > foaf:name > QName`
- **Naming:** Python `snake_case`, CSS/JS `kebab-case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`
- **Outbound HTTP:** Anything fetching a user-supplied URL must go through `security/ssrf.py::validate_outbound_url()`

### Where to Add New Code

- **New command type:** `commands/schemas.py` (union) + `commands/handlers/{name}.py` + register in `dispatcher.py`
- **New service:** `services/{name}.py` + instantiate in `main.py` lifespan + DI in `dependencies.py`
- **New router/feature:** `{feature}/router.py` + `__init__.py` + register in `main.py` + templates in `templates/{feature}/`
- **New Mental Model:** `models/{id}/manifest.yaml` + `ontology/`, `shapes/`, `views/`, `seed/`
- **New platform app:** `apps/{id}/manifest.yaml` + entrypoint; install via Admin > Applications
- **New user guide chapter:** the chapter list lives in THREE places — `docs/guide/README.md`, `docs/guide/index.html`, and `GUIDE_SECTIONS` in `shell/router.py` (see `.gsd/KNOWLEDGE.md`)

See `.planning/codebase/STRUCTURE.md` for full details.

---

## Deep-Dive References

| Document | Contents |
|----------|----------|
| [`.gsd/PROJECT.md`](.gsd/PROJECT.md) | Current architecture snapshot, updated per milestone (freshest source) |
| [`.planning/codebase/ARCHITECTURE.md`](.planning/codebase/ARCHITECTURE.md) | Layer details, data flows, key abstractions, entry points |
| [`.planning/codebase/STACK.md`](.planning/codebase/STACK.md) | All dependencies and versions (Python, CDN, Docker) |
| [`.planning/codebase/CONVENTIONS.md`](.planning/codebase/CONVENTIONS.md) | Code style, naming, error handling, template patterns |
| [`.planning/codebase/INTEGRATIONS.md`](.planning/codebase/INTEGRATIONS.md) | External services, auth flows, webhooks, RDF vocabularies |
| [`.planning/codebase/TESTING.md`](.planning/codebase/TESTING.md) | Test framework, fixtures, helpers, patterns |
| [`.planning/codebase/CONCERNS.md`](.planning/codebase/CONCERNS.md) | Tech debt, security considerations, performance bottlenecks |
| [`.planning/codebase/STRUCTURE.md`](.planning/codebase/STRUCTURE.md) | Full directory tree, module purposes, where-to-add guides |
