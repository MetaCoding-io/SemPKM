# Architecture

**Analysis Date:** 2026-03-09

## Pattern Overview

**Overall:** Event-Sourced RDF Knowledge Graph with HTMX Server-Side Rendering

**Key Characteristics:**
- All writes flow through a single `POST /api/commands` endpoint using a Command pattern with a discriminated union of command types
- Every write creates an immutable named graph event in RDF4J; current state is materialized into `urn:sempkm:current` in the same atomic transaction
- The UI is server-rendered HTML using Jinja2 + jinja2-fragments, with htmx driving partial DOM updates (no JS framework)
- RDF-based "Mental Models" (ontology + SHACL shapes + view specs + seed data) are installed at runtime and stored in named graphs
- Two storage backends: RDF4J triplestore (semantic data, events, models) + SQLite/PostgreSQL (auth, sessions, settings)

## Layers

**HTTP / Routing Layer:**
- Purpose: Receives HTTP requests, validates auth, dispatches to routers
- Location: `backend/app/main.py`, `backend/app/**/router.py`
- Contains: FastAPI routers, exception handlers, middleware, lifespan startup
- Depends on: Service layer, auth dependencies
- Used by: Nginx reverse proxy

**Command Layer (Writes):**
- Purpose: The exclusive write path for all semantic data mutations
- Location: `backend/app/commands/`
- Contains: `router.py` (single `POST /api/commands` endpoint), `dispatcher.py` (handler registry), `schemas.py` (discriminated union Command type), `handlers/` (one file per command type)
- Depends on: EventStore, TriplestoreClient, ValidationQueue, WebhookService
- Used by: Frontend JS via `fetch('/api/commands', ...)`

**Event Store:**
- Purpose: Atomic commit of Operations into immutable event graphs + current state materialization
- Location: `backend/app/events/store.py`
- Contains: `EventStore.commit()`, `Operation` dataclass, SPARQL builder functions
- Depends on: TriplestoreClient (raw HTTP to RDF4J transactions)
- Used by: Commands router

**Service Layer:**
- Purpose: Domain logic, query execution, caching, background processing
- Location: `backend/app/services/`, `backend/app/views/service.py`, `backend/app/validation/`
- Contains: `LabelService`, `ModelService`, `ShapesService`, `ValidationService`, `ViewSpecService`, `WebhookService`, `PrefixRegistry`, `AsyncValidationQueue`
- Depends on: TriplestoreClient, SQLAlchemy session, rdflib
- Used by: Routers via FastAPI dependency injection from `app.state.*`

**Auth Layer:**
- Purpose: Passwordless session auth (magic link), role-based access (owner/member)
- Location: `backend/app/auth/`
- Contains: `models.py` (SQLAlchemy User/UserSession/Invitation/InstanceConfig), `service.py`, `router.py`, `dependencies.py` (get_current_user, require_role, optional_current_user), `tokens.py`
- Depends on: SQLite/PostgreSQL via SQLAlchemy (aiosqlite), httpOnly cookie `sempkm_session`
- Used by: All protected routers via `Depends(require_role(...))`

**IndieAuth Layer:**
- Purpose: IndieAuth OAuth2 provider — authorization code flow with PKCE for IndieWeb identity
- Location: `backend/app/indieauth/`
- Contains: `service.py` (IndieAuthService), `router.py` (authorization, token, introspection, metadata), `models.py` (SQLAlchemy: AuthorizationCode, AccessToken), `schemas.py`, `scopes.py`
- Depends on: Auth layer (user sessions), SQLAlchemy
- Used by: External IndieWeb clients requesting authorization

**WebID Layer:**
- Purpose: WebID profile management — username, RSA key generation, link management, public profile
- Location: `backend/app/webid/`
- Contains: `service.py` (WebIdService), `router.py` (API endpoints + public `/users/{username}`), `schemas.py`
- Depends on: Auth layer, TriplestoreClient
- Used by: IndieAuth (identity verification), public profile pages

**Inference Layer:**
- Purpose: OWL 2 RL forward-chaining inference — generates inferred triples from ontology axioms
- Location: `backend/app/inference/`
- Contains: `service.py` (InferenceService — loads ontology+data, runs owlrl, diffs, stores), `entailments.py` (entailment type classification: rdfs:subClassOf, owl:inverseOf, etc.), `models.py`, `router.py`
- Depends on: TriplestoreClient, rdflib, owlrl
- Used by: Manual trigger via API; inferred triples stored in `urn:sempkm:inferred`

**Lint Layer:**
- Purpose: Structured SHACL lint results — paginated REST API and SSE streaming
- Location: `backend/app/lint/`
- Contains: `service.py` (LintService), `router.py` (GET results/status/diff, SSE stream), `models.py`, `broadcast.py`
- Depends on: ValidationService, TriplestoreClient
- Used by: Browser workspace lint panel

**Template / UI Layer:**
- Purpose: Server-rendered HTML with htmx partials for dynamic updates
- Location: `backend/app/templates/`
- Contains: Jinja2 templates (`base.html`, `browser/workspace.html`, `browser/nav_tree.html`, `forms/object_form.html`, `components/_sidebar.html`)
- Depends on: jinja2-fragments (block-level rendering for htmx), service layer data
- Used by: Browser router, admin router, views router

**Triplestore Client:**
- Purpose: Low-level async HTTP client for RDF4J REST API
- Location: `backend/app/triplestore/client.py`
- Contains: `TriplestoreClient` (query, update, begin_transaction, commit_transaction, rollback_transaction, transaction_update, construct)
- Depends on: httpx.AsyncClient
- Used by: EventStore, all service classes

**Mental Model System:**
- Purpose: Pluggable domain ontologies, SHACL shapes, view specs, and seed data
- Location: `models/basic-pkm/` (shipped model), `backend/app/models/` (loader/registry)
- Contains: Per-model named graphs (`urn:sempkm:model:{id}:ontology`, `:shapes`, `:views`, `:seed`); registry in `urn:sempkm:models`
- Depends on: TriplestoreClient, rdflib (JSON-LD parsing)
- Used by: ViewSpecService, ShapesService, ModelService

**Canvas Layer:**
- Purpose: Spatial canvas workspace — persist/restore canvas state, load RDF neighbor nodes
- Location: `backend/app/canvas/`
- Contains: `service.py` (CanvasService), `router.py` (canvas API endpoints), `schemas.py`
- Depends on: TriplestoreClient
- Used by: Browser canvas view via `frontend/static/js/canvas.js`

**VFS / WebDAV Layer:**
- Purpose: Virtual filesystem — browse RDF data as a file/folder hierarchy
- Location: `backend/app/vfs/`
- Contains: `provider.py` (VfsProvider), `router.py` (file-browser page + API), `collections.py`, `resources.py`, `write.py`, `cache.py`, `auth.py`
- Depends on: TriplestoreClient, Auth layer
- Used by: VFS browser panel via `frontend/static/js/vfs-browser.js`

**Obsidian Import Layer:**
- Purpose: Import Obsidian vault ZIP files into the knowledge graph
- Location: `backend/app/obsidian/`
- Contains: `router.py` (upload/scan/stream/discard), `scanner.py` (markdown vault scanner), `executor.py` (import executor), `models.py`, `broadcast.py` (SSE progress)
- Depends on: EventStore, TriplestoreClient, commands
- Used by: Obsidian import UI templates

**Monitoring Layer:**
- Purpose: PostHog error middleware — captures unhandled 5xx exceptions
- Location: `backend/app/monitoring/`
- Contains: `middleware.py` (PostHogErrorMiddleware), `posthog.py` (client), `router.py`
- Depends on: PostHog SDK (optional)
- Used by: FastAPI middleware stack

**Frontend Static Assets:**
- Purpose: CSS theming (9 files), JS modules (17 files) for workspace interactions, graph visualization
- Location: `frontend/static/`
- Contains: `css/` (style.css, workspace.css, forms.css, views.css, theme.css, settings.css, dockview-sempkm-bridge.css, import.css, vfs-browser.css), `js/` (app.js, editor.js, workspace.js, workspace-layout.js, graph.js, canvas.js, vfs-browser.js, auth.js, named-layouts.js, tutorials.js, posthog.js, cleanup.js, etc.)
- Depends on: htmx 2.0.4, Cytoscape.js, Split.js, marked.js, DOMPurify, Lucide icons, Driver.js, Dockview (all loaded from CDN)
- Used by: All HTML pages

## Data Flow

**Write Flow (Object Create):**

1. Frontend calls `fetch('/api/commands', {method: 'POST', body: JSON.stringify({command: 'object.create', params: {...}})})` from `frontend/static/js/editor.js`
2. `backend/app/commands/router.py` `execute_commands()` receives the request; `require_role("owner", "member")` validates session cookie against SQLite
3. `backend/app/commands/dispatcher.py` `dispatch()` looks up `handle_object_create` in `HANDLER_REGISTRY`
4. `backend/app/commands/handlers/object_create.py` mints IRI (`urn:sempkm:data:{type}:{slug-or-uuid}`), builds `Operation` with `data_triples` and `materialize_inserts`
5. `backend/app/events/store.py` `EventStore.commit()`:
   - Opens RDF4J transaction via `TriplestoreClient.begin_transaction()`
   - Inserts event metadata + data triples into new named graph `urn:sempkm:event:{uuid}`
   - Inserts materialization triples into `urn:sempkm:current`
   - Commits transaction (both atomic)
6. `AsyncValidationQueue.enqueue()` schedules background SHACL validation (non-blocking)
7. `WebhookService.dispatch()` fires `object.changed` webhook (fire-and-forget)
8. Response: `{results: [{iri, event_iri, command}], event_iri, timestamp}`

**Read Flow (Browser / Workspace):**

1. Browser makes htmx-triggered GET request (e.g., `GET /browser/workspace`)
2. `backend/app/browser/router.py` handler runs SPARQL SELECT against `urn:sempkm:current` via `TriplestoreClient.query()`
3. `LabelService.resolve_batch()` resolves IRIs to labels using COALESCE SPARQL with TTL cache
4. Jinja2Blocks renders HTML template (or fragment block for htmx partial)
5. Response: full HTML page or `HX-Request` partial with `hx-swap` target

**Model Installation Flow:**

1. `ModelService.install_model()` reads JSON-LD files from `models/{id}/`
2. rdflib parses ontology/shapes/views/seed into `rdflib.Graph` objects
3. `write_graph_to_named_graph()` inserts each graph into `urn:sempkm:model:{id}:{artifact}`
4. `register_model()` writes metadata into `urn:sempkm:models`
5. Seed data objects are committed via `EventStore.commit()` into `urn:sempkm:current`

**Validation Flow (Background):**

1. After every `EventStore.commit()`, event IRI is enqueued into `AsyncValidationQueue`
2. Background worker (asyncio.Task) coalesces pending jobs, runs only the latest
3. `ValidationService.validate()` executes pyshacl against `urn:sempkm:current` using SHACL shapes from all model graphs
4. Report summary cached on `AsyncValidationQueue.latest_report`
5. `WebhookService.dispatch("validation.completed", ...)` fires after validation

**State Management:**

- All services are singletons stored on `app.state.*` during lifespan startup (`backend/app/main.py`)
- FastAPI dependency injection via `backend/app/dependencies.py` pulls services from `request.app.state`
- No in-process mutable state beyond `LabelService._cache` (TTLCache) and `AsyncValidationQueue._latest_report`

## Key Abstractions

**Operation:**
- Purpose: A single logical write (create/patch/delete) described as RDF triples
- Examples: `backend/app/events/store.py` (Operation dataclass), `backend/app/commands/handlers/object_create.py`
- Pattern: Command handlers return an `Operation`; `EventStore.commit()` consumes a list of `Operation`s

**Command (Discriminated Union):**
- Purpose: Type-safe write intent with Pydantic validation before handler dispatch
- Examples: `backend/app/commands/schemas.py` — `ObjectCreateCommand`, `ObjectPatchCommand`, `BodySetCommand`, `EdgeCreateCommand`, `EdgePatchCommand`
- Pattern: `Annotated[Union[...], Field(discriminator="command")]`; dispatcher uses `HANDLER_REGISTRY` dict

**Mental Model:**
- Purpose: Pluggable domain schema (ontology + SHACL + views + seed) loaded at runtime
- Examples: `models/basic-pkm/manifest.yaml`, `backend/app/models/registry.py` `ModelGraphs`
- Pattern: Each model lives in four named graphs identified by `urn:sempkm:model:{id}:{artifact}`

**Named Graphs:**
- Purpose: Isolate semantic data by type (events, current state, model artifacts)
- Examples: `urn:sempkm:current` (materialized state), `urn:sempkm:event:{uuid}` (immutable events), `urn:sempkm:models` (model registry), `urn:sempkm:model:{id}:{artifact}`
- Pattern: All SPARQL reads scope to `FROM <urn:sempkm:current>` (enforced by `scope_to_current_graph()` in `backend/app/sparql/client.py`)

**ViewSpec:**
- Purpose: SPARQL-backed view definition (table/card/graph renderer) bundled in a Mental Model
- Examples: `backend/app/views/service.py` `ViewSpec` dataclass
- Pattern: Loaded from `urn:sempkm:model:{id}:views` graphs; `ViewSpecService` executes paginated queries

## Entry Points

**FastAPI Application:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app` (Docker CMD)
- Responsibilities: Lifespan startup (service initialization, triplestore setup, SQL schema), router registration, Jinja2 template engine setup, exception handling, static file mounting

**Nginx Reverse Proxy:**
- Location: `frontend/nginx.conf`
- Triggers: Port 80 (Docker Compose exposes as host port 3901)
- Responsibilities: Serve static assets (`/css/`, `/js/`), serve auth HTML pages directly (`/login.html`, `/setup.html`, `/invite.html`), proxy `/api/*` and all other routes to FastAPI at `http://api:8000`; SSE endpoint `/browser/llm/chat/stream` has `proxy_buffering off`

**Auth Entry Points:**
- Setup: `POST /api/auth/setup` — first-run claim with setup token
- Login: `POST /api/auth/magic-link` → `POST /api/auth/verify` → sets `sempkm_session` cookie
- Session check: `GET /api/auth/me`

**Commands Endpoint:**
- Location: `backend/app/commands/router.py`
- Triggers: `POST /api/commands` with `{"command": "object.create", "params": {...}}` or array
- Responsibilities: Parse single/batch commands, dispatch to handlers, commit via EventStore, enqueue validation, dispatch webhooks

## Error Handling

**Strategy:** Layered — HTTP-level (exception handler in main.py), command-level (CommandError), service-level (logged warnings with fallback)

**Patterns:**
- `backend/app/main.py` `auth_exception_handler`: routes 401/403 to either htmx inline error fragment or full-page redirect/error template depending on `HX-Request` header
- `CommandError` (`backend/app/commands/exceptions.py`): carries `status_code` and `message`; caught in commands router and returned as JSON error
- Service methods catch triplestore failures with `logger.warning(..., exc_info=True)` and return empty/fallback results (never raise to caller)
- `AsyncValidationQueue._worker()`: catches all exceptions, logs, and continues — never crashes the worker
- `EventStore.commit()`: explicit try/except with `rollback_transaction()` on failure

## Cross-Cutting Concerns

**Logging:** `logging.basicConfig(level=logging.INFO)` at app startup; each module uses `logger = logging.getLogger(__name__)`

**Validation:** SHACL-based post-write validation via `AsyncValidationQueue` (background, non-blocking); Pydantic v2 for all command/request schema validation

**Authentication:** httpOnly cookie `sempkm_session` → SQLite session lookup → `User` object; `require_role("owner", "member")` factory dependency used on all write endpoints; `optional_current_user` for public endpoints

**SPARQL Graph Scoping:** `scope_to_current_graph()` in `backend/app/sparql/client.py` injects `FROM <urn:sempkm:current>` into all user/view SPARQL queries to prevent event graph data from leaking into results

**Monitoring:** `PostHogErrorMiddleware` (`backend/app/monitoring/middleware.py`) captures unhandled 5xx exceptions to PostHog (disabled by default; enabled via `posthog_enabled=True` env var)

---

*Architecture analysis: 2026-03-09*
