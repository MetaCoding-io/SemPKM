# Codebase Structure

**Analysis Date:** 2026-03-09

## Directory Layout

```
SemPKM/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── admin/              # Admin UI router (model/webhook management)
│   │   ├── auth/               # Passwordless auth (magic link, sessions, roles)
│   │   ├── browser/            # IDE-style workspace router (main UI)
│   │   ├── canvas/             # Spatial canvas workspace (save/load, neighbor loading)
│   │   ├── commands/           # Write command API (POST /api/commands)
│   │   │   └── handlers/       # One handler per command type
│   │   ├── db/                 # SQLAlchemy engine, session, base model
│   │   ├── debug/              # SPARQL console, command debug UI (dev only)
│   │   ├── events/             # Event store: immutable named graphs + materialization
│   │   ├── health/             # GET /api/health endpoint
│   │   ├── indieauth/          # IndieAuth OAuth2 provider (authorization, token, PKCE)
│   │   ├── inference/          # OWL 2 RL inference engine (forward-chaining, entailments)
│   │   ├── lint/               # Structured SHACL lint results (paginated API, SSE stream)
│   │   ├── models/             # Mental Model loader, registry, manifest schema
│   │   ├── monitoring/         # PostHog error middleware and analytics client
│   │   ├── obsidian/           # Obsidian vault import (ZIP upload, scan, streaming progress)
│   │   ├── rdf/                # IRI minting, JSON-LD utils, namespace definitions
│   │   ├── services/           # Domain services (labels, shapes, validation, webhooks, prefixes)
│   │   ├── shell/              # Admin shell router (dashboard, admin, health pages)
│   │   ├── sparql/             # SPARQL passthrough router + scoping utility
│   │   ├── templates/          # Jinja2 HTML templates
│   │   │   ├── admin/          # Admin page templates (7 templates)
│   │   │   ├── browser/        # Workspace, nav tree, object tab, views templates (39 templates)
│   │   │   ├── components/     # Shared partials (_sidebar.html, _tabs.html)
│   │   │   ├── debug/          # Debug UI templates
│   │   │   ├── errors/         # Error page templates (403.html)
│   │   │   ├── forms/          # Form partials (_field.html, _group.html, object_form.html)
│   │   │   ├── indieauth/      # IndieAuth authorization consent UI (2 templates)
│   │   │   ├── obsidian/       # Obsidian import UI templates (10 templates)
│   │   │   └── webid/          # WebID profile page template (1 template)
│   │   ├── triplestore/        # RDF4J async HTTP client + repository setup
│   │   ├── validation/         # Async SHACL validation queue + report models
│   │   ├── vfs/                # Virtual filesystem / WebDAV (tree, content, collections, write, cache)
│   │   ├── views/              # ViewSpec service + router
│   │   ├── webid/              # WebID profile (username, key generation, publish)
│   │   ├── config.py           # Pydantic BaseSettings (env vars)
│   │   ├── dependencies.py     # FastAPI dependency functions (pull from app.state)
│   │   └── main.py             # App factory, lifespan, router registration
│   ├── migrations/             # Alembic SQL migrations
│   │   └── versions/           # Migration scripts
│   ├── Dockerfile
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/                   # Nginx static server + HTML auth pages
│   ├── static/
│   │   ├── css/                # CSS stylesheets (9 files)
│   │   │   ├── style.css       # Base application styles
│   │   │   ├── workspace.css   # Workspace layout and object editor
│   │   │   ├── forms.css       # SHACL-driven form styles
│   │   │   ├── views.css       # Table, cards, graph view styles
│   │   │   ├── theme.css       # CSS custom properties (light/dark)
│   │   │   ├── settings.css    # Settings page styles
│   │   │   ├── dockview-sempkm-bridge.css  # Dockview theme variable bridge
│   │   │   ├── import.css      # Obsidian import UI styles
│   │   │   └── vfs-browser.css # VFS file browser panel styles
│   │   └── js/                 # JavaScript modules (17 files)
│   │       ├── app.js          # Application bootstrap and event wiring
│   │       ├── auth.js         # Session management, auth state
│   │       ├── canvas.js       # Spatial canvas interactions (Cytoscape.js)
│   │       ├── cleanup.js      # Resource cleanup utilities
│   │       ├── column-prefs.js # Table column persistence (localStorage)
│   │       ├── editor.js       # Object editing, command dispatch
│   │       ├── graph.js        # Graph visualization (Cytoscape.js)
│   │       ├── markdown-render.js  # marked.js rendering + DOMPurify
│   │       ├── named-layouts.js    # Named layout save/restore
│   │       ├── posthog.js      # PostHog analytics SDK loader
│   │       ├── settings.js     # Settings page interactions
│   │       ├── sidebar.js      # Sidebar toggle
│   │       ├── theme.js        # Dark/light mode toggle
│   │       ├── tutorials.js    # Driver.js guided tour overlays
│   │       ├── vfs-browser.js  # VFS file browser panel
│   │       ├── workspace.js    # Split pane management, object tab logic
│   │       └── workspace-layout.js  # Dockview workspace layout manager
│   ├── index.html              # Unused placeholder
│   ├── login.html              # Auth page (served directly by nginx)
│   ├── setup.html              # First-run setup page
│   ├── invite.html             # Invitation acceptance page
│   ├── Dockerfile
│   └── nginx.conf              # Reverse proxy config
├── models/                     # Mental Model bundles (mounted into container)
│   ├── basic-pkm/              # Bundled starter model (Notes, Projects, Concepts, Persons)
│   │   ├── manifest.yaml       # Model metadata and entrypoints
│   │   ├── ontology/           # OWL ontology (JSON-LD)
│   │   ├── shapes/             # SHACL shapes for form generation (JSON-LD)
│   │   ├── views/              # ViewSpec definitions (JSON-LD)
│   │   └── seed/               # Seed data objects (JSON-LD)
│   └── ppv/                    # PPV (Personal Productivity Vault) model bundle
│       ├── manifest.yaml       # Model metadata
│       ├── ontology/           # OWL ontology
│       ├── rules/              # Business rules
│       ├── shapes/             # SHACL shapes
│       ├── views/              # ViewSpec definitions
│       └── seed/               # Seed data
├── config/
│   └── rdf4j/
│       └── sempkm-repo.ttl     # RDF4J repository configuration (TTL)
├── docs/                       # GitHub Pages site + user guide markdown files
│   └── guide/                  # User guide markdown (served as /docs/guide/* by FastAPI)
├── e2e/                        # Playwright end-to-end tests
│   ├── tests/                  # Test files organized by feature area
│   │   ├── 00-setup/           # Setup wizard tests (2 specs)
│   │   ├── 01-objects/         # Object CRUD tests (6 specs)
│   │   ├── 02-views/           # View spec tests (4 specs)
│   │   ├── 03-navigation/      # Nav tree tests (6 specs)
│   │   ├── 04-validation/      # SHACL validation tests (1 spec)
│   │   ├── 05-admin/           # Admin panel tests (4 specs)
│   │   ├── 06-settings/        # Settings tests (5 specs)
│   │   ├── 07-multi-user/      # Multi-user tests (2 specs)
│   │   ├── 08-search/          # Full-text search tests (2 specs)
│   │   ├── 09-inference/       # OWL inference tests (1 spec)
│   │   ├── 10-lint-dashboard/  # Lint dashboard tests (1 spec)
│   │   ├── 11-helptext/        # Help text tests (1 spec)
│   │   ├── 12-bug-fixes/       # Regression bug fix tests (1 spec)
│   │   ├── 13-v24-coverage/    # v2.4 coverage tests (3 specs)
│   │   ├── 14-obsidian-import/ # Obsidian import tests (3 specs)
│   │   ├── 15-webid/           # WebID profile tests (1 spec)
│   │   ├── 16-indieauth/       # IndieAuth flow tests (1 spec)
│   │   └── screenshots/        # Marketing screenshot capture (2 specs)
│   ├── fixtures/               # Shared Playwright fixtures
│   ├── helpers/                # Test helper utilities
│   └── screenshots/            # Screenshot output directory
├── orig_specs/                 # Original design specifications (reference only)
├── scripts/
│   └── reset-instance.sh       # Dev reset script
├── .planning/                  # GSD planning documents
│   ├── codebase/               # THIS directory: codebase analysis docs
│   ├── milestones/             # Milestone phase plans and summaries
│   └── phases/                 # Current phase plans
└── docker-compose.yml          # Full stack: api + frontend + triplestore services
```

## Directory Purposes

**`backend/app/commands/`:**
- Purpose: The exclusive write path for all semantic data changes
- Contains: `router.py` (POST /api/commands), `dispatcher.py` (handler registry), `schemas.py` (Pydantic command models), `exceptions.py`, `handlers/` (object_create, object_patch, body_set, edge_create, edge_patch)
- Key files: `backend/app/commands/dispatcher.py`, `backend/app/commands/schemas.py`

**`backend/app/events/`:**
- Purpose: Event sourcing core — atomic commit of immutable named graphs + current state materialization
- Contains: `store.py` (EventStore class, Operation dataclass, SPARQL builders), `models.py` (event RDF predicates), `store.py`
- Key files: `backend/app/events/store.py`

**`backend/app/services/`:**
- Purpose: Domain service singletons instantiated at startup and injected via app.state
- Contains: `labels.py` (LabelService with TTL cache), `models.py` (ModelService), `shapes.py` (ShapesService for SHACL form generation), `validation.py` (ValidationService, pyshacl), `webhooks.py` (WebhookService), `prefixes.py` (PrefixRegistry), `icons.py` (IconService), `settings.py` (SettingsService)
- Key files: `backend/app/services/labels.py`, `backend/app/services/shapes.py`

**`backend/app/browser/`:**
- Purpose: The main IDE-style workspace UI — three-column layout with nav tree, object editor, views panel
- Contains: `router.py` with endpoints for workspace, nav_tree, tree_children, object_tab, body_save, search_suggestions, type_picker, create_object, edit_object, view_menu, lint_panel
- Key files: `backend/app/browser/router.py` (largest router, ~800+ lines)

**`backend/app/templates/browser/`:**
- Purpose: Jinja2 templates for browser UI — both full pages and htmx partial fragments
- Key files: `workspace.html` (three-column layout), `nav_tree.html` (hierarchical RDF tree), `object_tab.html` (object detail view), `forms/object_form.html` (SHACL-driven form), `table_view.html`, `cards_view.html`, `graph_view.html`

**`backend/app/triplestore/`:**
- Purpose: Thin async wrapper around RDF4J REST API
- Contains: `client.py` (TriplestoreClient), `setup.py` (ensure_repository — creates repo from TTL config if missing)
- Key files: `backend/app/triplestore/client.py`

**`backend/app/rdf/`:**
- Purpose: RDF utilities — IRI minting, JSON-LD parsing, namespace definitions
- Contains: `iri.py` (mint_object_iri, mint_event_iri), `namespaces.py` (SEMPKM, DATA, COMMON_PREFIXES, CURRENT_GRAPH_IRI), `jsonld.py`
- Key files: `backend/app/rdf/namespaces.py`, `backend/app/rdf/iri.py`

**`backend/app/models/`:**
- Purpose: Mental Model lifecycle — loading JSON-LD bundles, validating manifests, installing into triplestore
- Contains: `loader.py`, `manifest.py` (ManifestSchema Pydantic model), `registry.py` (SPARQL operations for model named graphs), `router.py`, `validator.py`
- Key files: `backend/app/models/registry.py`, `backend/app/models/manifest.py`

**`backend/app/auth/`:**
- Purpose: Session-based passwordless auth system
- Contains: `models.py` (User, UserSession, Invitation, InstanceConfig, UserSetting SQLAlchemy ORM), `service.py` (AuthService), `router.py` (/api/auth/*), `dependencies.py` (get_current_user, require_role), `tokens.py` (setup token, magic link JWT), `schemas.py`
- Key files: `backend/app/auth/dependencies.py`, `backend/app/auth/models.py`

**`backend/app/validation/`:**
- Purpose: Background SHACL validation queue
- Contains: `queue.py` (AsyncValidationQueue — asyncio.Task worker with coalescing), `report.py` (ValidationReport, ValidationReportSummary), `router.py` (GET /api/validation/report)
- Key files: `backend/app/validation/queue.py`

**`backend/app/canvas/`:**
- Purpose: Spatial canvas workspace — save/load canvas state, load RDF neighbor nodes for graph exploration
- Contains: `router.py` (canvas API endpoints), `service.py` (CanvasService), `schemas.py` (Pydantic models)
- Key files: `backend/app/canvas/service.py`

**`backend/app/indieauth/`:**
- Purpose: IndieAuth OAuth2 provider — authorization code flow with PKCE for IndieWeb identity
- Contains: `router.py` (authorization, token, introspection, metadata endpoints), `service.py` (IndieAuthService), `models.py` (SQLAlchemy models), `schemas.py`, `scopes.py` (scope definitions)
- Key files: `backend/app/indieauth/service.py`, `backend/app/indieauth/router.py`

**`backend/app/inference/`:**
- Purpose: OWL 2 RL forward-chaining inference engine — inferred triples stored in `urn:sempkm:inferred`
- Contains: `service.py` (InferenceService), `entailments.py` (entailment type classification), `models.py` (data models), `router.py` (inference trigger endpoint)
- Key files: `backend/app/inference/service.py`, `backend/app/inference/entailments.py`

**`backend/app/lint/`:**
- Purpose: Structured SHACL lint results API — paginated, filterable access to validation results
- Contains: `router.py` (REST endpoints + SSE stream), `service.py` (LintService), `models.py` (result models), `broadcast.py` (SSE broadcast)
- Key files: `backend/app/lint/service.py`, `backend/app/lint/router.py`

**`backend/app/obsidian/`:**
- Purpose: Obsidian vault import — ZIP upload, markdown scanning, streaming progress, RDF conversion
- Contains: `router.py` (upload/scan/stream/discard endpoints), `scanner.py` (vault scanner), `executor.py` (import executor), `models.py` (import models), `broadcast.py` (progress SSE)
- Key files: `backend/app/obsidian/router.py`, `backend/app/obsidian/scanner.py`

**`backend/app/vfs/`:**
- Purpose: Virtual filesystem / WebDAV — file-browser UI and API for navigating RDF data as files
- Contains: `router.py` (browser page + API endpoints), `provider.py` (VFS provider), `collections.py` (collection handling), `resources.py` (resource rendering), `write.py` (write operations), `cache.py` (response caching), `auth.py` (WebDAV auth)
- Key files: `backend/app/vfs/router.py`, `backend/app/vfs/provider.py`

**`backend/app/webid/`:**
- Purpose: WebID profile management — username setup, RSA key generation, link management, public profile
- Contains: `router.py` (API + public profile endpoints), `service.py` (WebIdService), `schemas.py` (Pydantic models)
- Key files: `backend/app/webid/router.py`, `backend/app/webid/service.py`

**`backend/app/monitoring/`:**
- Purpose: PostHog error middleware and analytics client — captures 5xx exceptions to PostHog
- Contains: `middleware.py` (PostHogErrorMiddleware), `posthog.py` (PostHog client), `router.py` (monitoring endpoints)
- Key files: `backend/app/monitoring/middleware.py`

**`backend/app/shell/`:**
- Purpose: Admin shell router — serves dashboard, admin, and health pages with htmx partial support
- Contains: `router.py` (shell page endpoints)
- Key files: `backend/app/shell/router.py`

**`models/basic-pkm/`:**
- Purpose: The bundled starter Mental Model — PKM domain with Notes, Projects, Concepts, Persons
- Contains: `manifest.yaml` (model ID, version, namespace, entrypoints, icons), `ontology/basic-pkm.jsonld`, `shapes/basic-pkm.jsonld`, `views/basic-pkm.jsonld`, `seed/basic-pkm.jsonld`
- Key files: `models/basic-pkm/manifest.yaml`

**`models/ppv/`:**
- Purpose: PPV (Personal Productivity Vault) Mental Model — extended PKM domain with productivity types
- Contains: `manifest.yaml`, `ontology/`, `shapes/`, `views/`, `seed/`, `rules/` (business rules)
- Key files: `models/ppv/manifest.yaml`

**`frontend/static/js/`:**
- Purpose: Client-side JavaScript for workspace interactions (17 files)
- Core files: `app.js` (bootstrap), `editor.js` (object editing, command dispatch), `workspace.js` (split pane management, ~2100 lines), `workspace-layout.js` (Dockview layout manager), `auth.js` (session management)
- Visualization: `graph.js` (Cytoscape.js graph visualization), `canvas.js` (spatial canvas, ~940 lines)
- UI: `sidebar.js` (sidebar toggle), `theme.js` (dark/light mode), `column-prefs.js` (table column persistence), `markdown-render.js` (marked.js rendering), `named-layouts.js` (layout persistence), `settings.js` (settings page)
- Features: `vfs-browser.js` (VFS file browser), `tutorials.js` (Driver.js guided tours), `posthog.js` (PostHog analytics), `cleanup.js` (resource cleanup)

**`frontend/static/css/`:**
- Purpose: CSS stylesheets (9 files)
- Core: `style.css` (base), `workspace.css` (workspace layout), `forms.css` (SHACL forms), `views.css` (table/cards/graph), `theme.css` (CSS custom properties), `settings.css` (settings page)
- Features: `dockview-sempkm-bridge.css` (Dockview theme bridge), `import.css` (Obsidian import UI), `vfs-browser.css` (VFS browser panel)

**`e2e/tests/`:**
- Purpose: Playwright sequential E2E tests organized by feature (17 directories, ~46 spec files)
- Directories: `00-setup/` through `16-indieauth/` plus `screenshots/`
- Key files: `e2e/tests/00-setup/01-setup-wizard.spec.ts` (requires fresh Docker stack)
- Pattern: Numbered directories run in order, each directory is a feature area

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI app factory, lifespan, all router registrations
- `frontend/nginx.conf`: Reverse proxy routing rules
- `docker-compose.yml`: Service definitions (api on 8000, frontend on 80→3901, triplestore on 8080)

**Configuration:**
- `backend/app/config.py`: All environment-variable-driven settings via pydantic-settings
- `models/basic-pkm/manifest.yaml`: Bundled model metadata

**Core Logic:**
- `backend/app/events/store.py`: EventStore — the write heart of the system
- `backend/app/commands/dispatcher.py`: Command dispatcher and handler registry
- `backend/app/commands/schemas.py`: All command types as discriminated union
- `backend/app/triplestore/client.py`: RDF4J HTTP client
- `backend/app/rdf/namespaces.py`: All RDF namespace definitions and `CURRENT_GRAPH_IRI`
- `backend/app/sparql/client.py`: `scope_to_current_graph()` — critical for query correctness

**Services:**
- `backend/app/services/labels.py`: Label resolution with TTL cache
- `backend/app/services/shapes.py`: SHACL shape extraction for form generation
- `backend/app/views/service.py`: ViewSpec loading and paginated query execution
- `backend/app/validation/queue.py`: Background SHACL validation worker
- `backend/app/inference/service.py`: OWL 2 RL inference engine
- `backend/app/lint/service.py`: Structured lint results service
- `backend/app/canvas/service.py`: Spatial canvas persistence
- `backend/app/vfs/provider.py`: Virtual filesystem provider
- `backend/app/webid/service.py`: WebID profile management
- `backend/app/indieauth/service.py`: IndieAuth OAuth2 provider

**Auth & Identity:**
- `backend/app/auth/dependencies.py`: `get_current_user`, `require_role`, `optional_current_user`
- `backend/app/auth/models.py`: SQLAlchemy ORM models (User, UserSession, Invitation, InstanceConfig, UserSetting)
- `backend/app/indieauth/router.py`: IndieAuth OAuth2 endpoints (authorization, token, introspection)
- `backend/app/webid/router.py`: WebID profile endpoints + public profile page

**Templates:**
- `backend/app/templates/base.html`: Base layout with htmx, CDN scripts, sidebar
- `backend/app/templates/browser/workspace.html`: Three-column IDE workspace layout
- `backend/app/templates/browser/nav_tree.html`: Hierarchical nav tree (htmx lazy-loaded)
- `backend/app/templates/forms/object_form.html`: SHACL-driven object create/edit form

**Testing:**
- `e2e/`: All tests; run from this directory with `npx playwright test --project=chromium`
- `e2e/fixtures/`: Shared test fixtures
- `e2e/helpers/`: Test utility functions

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `object_create.py`, `labels.py`)
- HTML templates: `snake_case.html` or `_snake_case.html` for partials (e.g., `nav_tree.html`, `_sidebar.html`, `_field.html`)
- CSS: `kebab-case.css` (e.g., `workspace.css`, `forms.css`)
- JS: `kebab-case.js` (e.g., `editor.js`, `workspace-layout.js`, `column-prefs.js`)

**Directories:**
- Python packages: `snake_case/` (e.g., `commands/`, `triplestore/`)
- Template subdirs: `snake_case/` mirroring router names (e.g., `templates/browser/`)

**Python:**
- Classes: `PascalCase` (e.g., `TriplestoreClient`, `EventStore`, `LabelService`)
- Functions/methods: `snake_case` (e.g., `handle_object_create`, `resolve_batch`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `CURRENT_GRAPH_IRI`, `HANDLER_REGISTRY`, `MODELS_GRAPH`)
- Private functions: `_snake_case` prefix (e.g., `_register_handlers`, `_build_insert_data_sparql`)

**Named Graphs (RDF):**
- `urn:sempkm:current` — current materialized state (single graph)
- `urn:sempkm:event:{uuid}` — immutable event graphs
- `urn:sempkm:models` — model registry
- `urn:sempkm:model:{id}:ontology|shapes|views|seed` — per-model artifact graphs

**Command Types:**
- Dotted namespacing: `object.create`, `object.patch`, `body.set`, `edge.create`, `edge.patch`

## Where to Add New Code

**New Command Type:**
1. Add params class and command class to `backend/app/commands/schemas.py` (extend the `Command` union)
2. Create handler `backend/app/commands/handlers/{command_name}.py` returning `Operation`
3. Register handler in `backend/app/commands/dispatcher.py` `_register_handlers()`
4. Add webhook mapping in `backend/app/commands/router.py` `_COMMAND_EVENT_MAP`

**New Service:**
1. Create `backend/app/services/{name}.py` with service class
2. Instantiate in `backend/app/main.py` lifespan startup, store as `app.state.{name}_service`
3. Add getter dependency in `backend/app/dependencies.py`
4. Use via `Depends(get_{name}_service)` in routers

**New Router / Feature Area:**
1. Create `backend/app/{feature}/router.py` with `APIRouter(prefix="/{feature}")`
2. Create `backend/app/{feature}/__init__.py`
3. Import and register in `backend/app/main.py` (`app.include_router(...)`)
4. Add templates to `backend/app/templates/{feature}/`

**New Template:**
- Full page: `backend/app/templates/{feature}/{page}.html` — extend `base.html`
- htmx partial: Define `{% block content_block %}` in full page; router renders with `templates.TemplateResponse(block_name="content_block")` using jinja2-fragments

**New Mental Model:**
1. Create `models/{model-id}/manifest.yaml`, `ontology/`, `shapes/`, `views/`, `seed/`
2. Mount directory into container (docker-compose volume)
3. Install via admin UI or `ModelService.install_model()`

**New SQL Table:**
1. Add SQLAlchemy model in `backend/app/auth/models.py` (or new models file imported from there)
2. Create Alembic migration in `backend/migrations/versions/`

**Utilities:**
- RDF/SPARQL helpers: `backend/app/rdf/` or `backend/app/sparql/`
- Shared template filters: `backend/app/main.py` (register on `templates.env.filters`)

## Special Directories

**`.planning/`:**
- Purpose: GSD planning artifacts — phase plans, summaries, research, codebase analysis
- Generated: No
- Committed: Yes

**`.claude/worktrees/`:**
- Purpose: Agent worktrees for parallel Claude agent execution
- Generated: Yes (by GSD tooling)
- Committed: No (gitignored per worktree)

**`backend/.venv/`:**
- Purpose: Python virtual environment (uv-managed)
- Generated: Yes
- Committed: No

**`e2e/node_modules/`:**
- Purpose: Playwright and test dependencies
- Generated: Yes
- Committed: No

**`e2e/playwright-report/` and `e2e/test-results/`:**
- Purpose: Playwright test output and failure screenshots
- Generated: Yes
- Committed: No

**`.meta/output/`:**
- Purpose: Repomix-generated codebase snapshot for AI analysis
- Generated: Yes (by repomix)
- Committed: Yes

---

*Structure analysis: 2026-03-09*
