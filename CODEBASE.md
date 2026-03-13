# SemPKM Codebase Guide

**Last updated:** 2026-03-12

## Overview

SemPKM is an event-sourced RDF knowledge graph application with HTMX server-side rendering. It provides an IDE-style workspace for creating, browsing, and exploring structured knowledge through auto-generated forms, views, and graph visualizations.

The system runs three Docker services: a **FastAPI backend** (Python, port 8001), an **nginx frontend** (static assets + reverse proxy, port 3000), and an **RDF4J triplestore** (SPARQL graph database). All writes flow through a single `POST /api/commands` endpoint into an immutable event store with current-state materialization. All reads query `urn:sempkm:current` via SPARQL and render Jinja2/htmx partials.

Domain schemas are pluggable "Mental Models" (OWL ontology + SHACL shapes + view specs + seed data) installed at runtime.

---

## Directory Layout

```
SemPKM/
├── backend/                       # FastAPI Python backend
│   ├── app/                       # Application package (24 modules)
│   │   ├── admin/                 # Admin UI router (models, webhooks)
│   │   ├── auth/                  # Passwordless auth (magic link, sessions, roles)
│   │   ├── browser/               # IDE-style workspace router (main UI)
│   │   ├── canvas/                # Spatial canvas (save/load, neighbor loading)
│   │   ├── commands/              # Write command API (POST /api/commands)
│   │   ├── db/                    # SQLAlchemy engine, session, base model
│   │   ├── debug/                 # SPARQL console, command debug (dev only)
│   │   ├── events/                # Event store (immutable graphs + materialization)
│   │   ├── health/                # GET /api/health endpoint
│   │   ├── indieauth/             # IndieAuth OAuth2 provider (PKCE)
│   │   ├── inference/             # OWL 2 RL inference engine
│   │   ├── lint/                  # Structured SHACL lint results API
│   │   ├── models/                # Mental Model loader, registry
│   │   ├── monitoring/            # PostHog error middleware
│   │   ├── obsidian/              # Obsidian vault import (ZIP/scan/stream)
│   │   ├── rdf/                   # IRI minting, JSON-LD, namespaces
│   │   ├── services/              # Domain services (labels, shapes, etc.)
│   │   ├── shell/                 # Admin shell router (dashboard pages)
│   │   ├── sparql/                # SPARQL passthrough + graph scoping
│   │   ├── templates/             # Jinja2 HTML templates (9 subdirs, ~67 files)
│   │   ├── triplestore/           # RDF4J async HTTP client
│   │   ├── validation/            # Background SHACL validation queue
│   │   ├── vfs/                   # Virtual filesystem / WebDAV browser
│   │   ├── views/                 # ViewSpec service + router
│   │   ├── webid/                 # WebID profile management
│   │   ├── config.py              # Pydantic BaseSettings (env vars)
│   │   ├── dependencies.py        # FastAPI DI functions
│   │   └── main.py                # App factory, lifespan, router registration
│   ├── migrations/                # Alembic SQL migrations
│   └── pyproject.toml             # Python dependencies
├── frontend/                      # Nginx static server + auth pages
│   ├── static/css/                # 9 CSS files
│   ├── static/js/                 # 17 JS modules
│   ├── login.html                 # Auth page
│   ├── setup.html                 # First-run setup
│   ├── invite.html                # Invitation acceptance
│   └── nginx.conf                 # Reverse proxy config
├── models/                        # Mental Model bundles
│   ├── basic-pkm/                 # Starter: Notes, Projects, Concepts, Persons
│   └── ppv/                       # Personal Productivity Vault
├── config/rdf4j/                  # RDF4J repository config (TTL)
├── docs/guide/                    # User guide markdown
├── e2e/                           # Playwright E2E tests
│   ├── tests/                     # 17 test directories, ~46 spec files
│   ├── fixtures/                  # Auth, seed data, test harness
│   └── helpers/                   # Selectors, wait helpers, API client
├── scripts/                       # Dev utilities (reset-instance.sh)
├── .planning/                     # Planning docs + codebase analysis
└── docker-compose.yml             # Full stack definition
```

---

## Backend Modules

### Core

| Module | Purpose | Key Files | Lines |
|--------|---------|-----------|-------|
| `main` | App factory, lifespan startup, router registration | `main.py` | — |
| `config` | Pydantic BaseSettings (env vars) | `config.py` | — |
| `dependencies` | FastAPI DI functions (pull from app.state) | `dependencies.py` | — |
| `db` | SQLAlchemy engine, async session, Base model | `engine.py`, `session.py` | ~60 |
| `rdf` | IRI minting, JSON-LD parsing, namespace definitions | `iri.py`, `namespaces.py`, `jsonld.py` | ~190 |
| `triplestore` | RDF4J async HTTP client + repository setup | `client.py`, `setup.py` | ~250 |
| `sparql` | SPARQL passthrough router + `scope_to_current_graph()` | `client.py`, `router.py` | ~260 |

### Commands and Events

| Module | Purpose | Key Files | Lines |
|--------|---------|-----------|-------|
| `commands` | Write command API (single `POST /api/commands` endpoint) | `router.py`, `dispatcher.py`, `schemas.py`, `handlers/` | ~750 |
| `events` | Event store: immutable named graphs + current state materialization | `store.py`, `models.py` | ~860 |

### Services

| Module | Purpose | Key Files | Lines |
|--------|---------|-----------|-------|
| `services` | Domain service singletons (labels, shapes, validation, webhooks, prefixes, icons, settings) | `labels.py`, `shapes.py`, `webhooks.py`, `settings.py` | ~2830 |
| `models` | Mental Model loader, registry, manifest validation | `loader.py`, `registry.py`, `manifest.py` | ~1080 |
| `views` | ViewSpec service + paginated SPARQL query execution | `service.py`, `router.py` | ~1780 |
| `validation` | Background SHACL validation queue (asyncio worker) | `queue.py`, `report.py`, `router.py` | ~530 |
| `inference` | OWL 2 RL forward-chaining inference engine | `service.py`, `entailments.py` | ~1360 |
| `lint` | Structured SHACL lint results (paginated API, SSE stream) | `service.py`, `router.py`, `broadcast.py` | ~810 |

### Auth and Identity

| Module | Purpose | Key Files | Lines |
|--------|---------|-----------|-------|
| `auth` | Passwordless magic-link auth, sessions, roles (owner/member) | `service.py`, `models.py`, `dependencies.py`, `tokens.py` | ~1170 |
| `indieauth` | IndieAuth OAuth2 provider (authorization code + PKCE) | `service.py`, `router.py`, `models.py`, `scopes.py` | ~860 |
| `webid` | WebID profile (username, RSA keys, link management, public page) | `service.py`, `router.py`, `schemas.py` | ~490 |

### UI Routers

| Module | Purpose | Key Files | Lines |
|--------|---------|-----------|-------|
| `browser` | Main IDE-style workspace (nav tree, object tabs, forms, views, lint) | `router.py` | ~1570 |
| `admin` | Admin portal (model management, webhooks, user management) | `router.py` | ~860 |
| `shell` | Top-level navigation pages (dashboard, admin, health) | `router.py` | ~120 |
| `debug` | SPARQL console, command executor (dev only) | `router.py` | ~30 |

### Features

| Module | Purpose | Key Files | Lines |
|--------|---------|-----------|-------|
| `canvas` | Spatial canvas workspace (save/load, RDF neighbor loading) | `service.py`, `router.py`, `schemas.py` | ~510 |
| `obsidian` | Obsidian vault import (ZIP upload, scan, streaming progress) | `scanner.py`, `executor.py`, `router.py`, `broadcast.py` | ~1890 |
| `vfs` | Virtual filesystem / WebDAV (file browser, collections, resources) | `provider.py`, `router.py`, `collections.py`, `write.py`, `cache.py` | ~1230 |
| `monitoring` | PostHog error middleware (captures 5xx exceptions) | `middleware.py`, `posthog.py` | ~170 |
| `health` | Health check endpoint (`GET /api/health`) | `router.py` | ~30 |

---

## Frontend Assets

### JavaScript (17 files)

| File | Purpose | Lines |
|------|---------|-------|
| `app.js` | Application bootstrap and event wiring | ~450 |
| `workspace.js` | Split pane management, object tab logic, right pane sections | ~2120 |
| `workspace-layout.js` | Dockview workspace layout manager | ~550 |
| `canvas.js` | Spatial canvas interactions (Cytoscape.js graph exploration) | ~940 |
| `graph.js` | Graph visualization (Cytoscape.js + fcose/dagre layouts) | ~690 |
| `vfs-browser.js` | VFS file browser panel | ~650 |
| `editor.js` | Object editing, command dispatch via fetch | ~260 |
| `auth.js` | Session management, auth state, login flow | ~340 |
| `tutorials.js` | Driver.js guided tour overlays | ~270 |
| `column-prefs.js` | Table column visibility persistence (localStorage) | ~190 |
| `named-layouts.js` | Named layout save/restore | ~180 |
| `sidebar.js` | Sidebar toggle | ~140 |
| `markdown-render.js` | Markdown rendering (marked.js + DOMPurify) | ~130 |
| `theme.js` | Dark/light mode toggle | ~130 |
| `posthog.js` | PostHog analytics SDK loader | ~120 |
| `cleanup.js` | Resource cleanup utilities | ~60 |
| `settings.js` | Settings page interactions | ~50 |

### CSS (9 files)

| File | Purpose |
|------|---------|
| `style.css` | Base application styles |
| `workspace.css` | Workspace layout, object editor, panels |
| `forms.css` | SHACL-driven form styles |
| `views.css` | Table, cards, graph view styles (incl. 3D flip cards) |
| `theme.css` | CSS custom properties (light/dark mode tokens) |
| `settings.css` | Settings page styles |
| `dockview-sempkm-bridge.css` | Dockview theme variable bridge |
| `import.css` | Obsidian import UI styles |
| `vfs-browser.css` | VFS file browser panel styles |

---

## Templates

```
backend/app/templates/
├── base.html                  # Base layout (htmx, CDN scripts, sidebar)
├── admin/       (7)           # Admin portal (models, webhooks, users)
├── browser/     (39)          # Workspace, nav tree, object tab, views, lint, canvas
├── components/  (2)           # Shared partials (_sidebar.html, _tabs.html)
├── debug/       (3)           # SPARQL console, command executor
├── errors/      (1)           # Error pages (403)
├── forms/       (3)           # SHACL-driven form partials
├── indieauth/   (2)           # IndieAuth authorization consent UI
├── obsidian/    (10)          # Obsidian import wizard UI
└── webid/       (1)           # WebID public profile page
```

---

## Mental Models

Mental Models are pluggable domain schemas containing:
- `manifest.yaml` -- metadata (modelId, version, namespace, entrypoints, icons)
- `ontology/` -- OWL ontology (JSON-LD)
- `shapes/` -- SHACL shapes for auto-generated forms (JSON-LD)
- `views/` -- ViewSpec definitions for table/cards/graph renderers (JSON-LD)
- `seed/` -- Seed data objects (JSON-LD)

**Installed models:**

| Model | Domain | Types |
|-------|--------|-------|
| `basic-pkm` | Personal Knowledge Management | Note, Project, Concept, Person |
| `ppv` | Personal Productivity Vault | Extended productivity types + rules |

Models are mounted read-only into the container at `/app/models/` and installed via the admin UI or `ModelService.install_model()`. Each model's artifacts are stored in named graphs: `urn:sempkm:model:{id}:ontology`, `:shapes`, `:views`, `:seed`.

---

## E2E Tests

82 spec files across 28 directories (80 functional + 2 screenshot capture).

| Directory | Test Area | Specs |
|-----------|-----------|-------|
| `00-setup/` | Setup wizard, magic link auth, health check | 3 |
| `01-objects/` | Object CRUD, deletion, edges, edge.patch, markdown, tooltips | 11 |
| `02-views/` | Table, cards, graph, pagination, column prefs | 7 |
| `03-navigation/` | Nav tree, tabs, keyboard shortcuts, sidebar reorder, layouts | 7 |
| `04-validation/` | Lint API, validation lifecycle, lint panel | 3 |
| `05-admin/` | Admin portal, models, webhooks, SPARQL, debug pages | 9 |
| `06-settings/` | Settings, dark mode, events, LLM config, docs, misc endpoints | 9 |
| `07-multi-user/` | Member permissions, sessions, invite flow | 3 |
| `08-search/` | Full-text search, fuzzy toggle | 2 |
| `09-inference/` | OWL inference engine | 1 |
| `10-lint-dashboard/` | Lint dashboard | 1 |
| `11-helptext/` | Help text / tooltips | 1 |
| `12-bug-fixes/` | Regression tests | 1 |
| `13-v24-coverage/` | v2.4 coverage, VFS browser, VFS mountspec | 4 |
| `14-obsidian-import/` | Obsidian vault import | 3 |
| `15-webid/` | WebID profile | 1 |
| `16-indieauth/` | IndieAuth OAuth2 flow | 1 |
| `17-spatial-canvas/` | Canvas UI + API (sessions, subgraph, wiki-links) | 2 |
| `18-federation/` | Federation UI partials, federation sync | 2 |
| `19-explorer-modes/` | Explorer mode switching (by-type, hierarchy, by-tag) | 1 |
| `20-favorites/` | Favorites star toggle and sidebar | 1 |
| `20-tags/` | Tag pills and tag explorer | 1 |
| `20-vfs-explorer/` | VFS explorer mount mode | 1 |
| `21-comments/` | Comments thread, soft-delete | 1 |
| `22-ontology/` | Ontology viewer (TBox, ABox, RBox) | 1 |
| `23-class-creation/` | User-created classes | 1 |
| `99-rate-limiting/` | Auth rate limiting (429) | 1 |
| `screenshots/` | Marketing + guide screenshot capture | 2 |
| *(root)* | VFS WebDAV | 1 |

**Run:** `cd e2e && npx playwright test --project=chromium` (sequential, 1 worker)

---

## Docker Services

| Service | Image | Internal Port | Host Port | Purpose |
|---------|-------|---------------|-----------|---------|
| `triplestore` | `eclipse/rdf4j-workbench:5.0.1` | 8080 | (internal) | RDF4J SPARQL graph database |
| `api` | Custom (`./backend` Dockerfile) | 8000 | 8001 | FastAPI backend (uvicorn, hot-reload) |
| `frontend` | `nginx:stable-alpine` | 80 | 3000 | Static assets + reverse proxy to API |

**Key volumes:** `rdf4j_data` (triplestore persistence), `sempkm_data` (SQLite + secrets), `lucene_index` (full-text search)

---

## Data Flow

### Write Flow

```
Browser JS (editor.js)
  |  POST /api/commands {command: "object.create", params: {...}}
  v
nginx (port 3000) --> proxy_pass --> FastAPI (port 8000)
  |
  v
commands/router.py --> dispatcher.py --> handlers/object_create.py
  |  Returns Operation (data_triples + materialize_inserts)
  v
events/store.py EventStore.commit()
  |  1. Begin RDF4J transaction
  |  2. Insert event triples into urn:sempkm:event:{uuid}
  |  3. Materialize into urn:sempkm:current
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
Jinja2Blocks renders template (full page or htmx partial)
  |
  v
HTML response (hx-swap into DOM)
```

---

## Key Conventions

- **Single write path:** All data mutations go through `POST /api/commands` -- never direct SPARQL UPDATE
- **Event sourcing:** Every write creates an immutable named graph event; current state is materialized
- **Module structure:** Each module follows `__init__.py`, `router.py`, `service.py`, `models.py`, `schemas.py`
- **Service injection:** Services are singletons on `app.state.*`, injected via FastAPI `Depends()` from `dependencies.py`
- **htmx partials:** Routes serve both full pages and htmx fragments using `jinja2-fragments` block rendering
- **Graph scoping:** All SPARQL reads use `scope_to_current_graph()` to prevent event graph data leaking
- **Named graphs:** `urn:sempkm:current` (state), `urn:sempkm:event:{uuid}` (events), `urn:sempkm:model:{id}:{artifact}` (models), `urn:sempkm:inferred` (inference)
- **Label precedence:** `dcterms:title > rdfs:label > skos:prefLabel > schema:name > foaf:name > QName`
- **Naming:** Python `snake_case`, CSS/JS `kebab-case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`

### Where to Add New Code

- **New command type:** `commands/schemas.py` (union) + `commands/handlers/{name}.py` + register in `dispatcher.py`
- **New service:** `services/{name}.py` + instantiate in `main.py` lifespan + DI in `dependencies.py`
- **New router/feature:** `{feature}/router.py` + `__init__.py` + register in `main.py` + templates in `templates/{feature}/`
- **New Mental Model:** `models/{id}/manifest.yaml` + `ontology/`, `shapes/`, `views/`, `seed/`

See `.planning/codebase/STRUCTURE.md` for full details.

---

## Deep-Dive References

| Document | Contents |
|----------|----------|
| [`.planning/codebase/ARCHITECTURE.md`](.planning/codebase/ARCHITECTURE.md) | Layer details, data flows, key abstractions, entry points |
| [`.planning/codebase/STACK.md`](.planning/codebase/STACK.md) | All dependencies and versions (Python, CDN, Docker) |
| [`.planning/codebase/CONVENTIONS.md`](.planning/codebase/CONVENTIONS.md) | Code style, naming, error handling, template patterns |
| [`.planning/codebase/INTEGRATIONS.md`](.planning/codebase/INTEGRATIONS.md) | External services, auth flows, webhooks, RDF vocabularies |
| [`.planning/codebase/TESTING.md`](.planning/codebase/TESTING.md) | Test framework, fixtures, helpers, patterns |
| [`.planning/codebase/CONCERNS.md`](.planning/codebase/CONCERNS.md) | Tech debt, security considerations, performance bottlenecks |
| [`.planning/codebase/STRUCTURE.md`](.planning/codebase/STRUCTURE.md) | Full directory tree, module purposes, where-to-add guides |
