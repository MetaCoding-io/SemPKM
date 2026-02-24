# Architecture Patterns

**Domain:** RDF-based Personal Knowledge Management (Semantic PKM)
**Researched:** 2026-02-21
**Confidence:** MEDIUM (architecture grounded in project specs + training data on RDF/semantic web patterns; no live verification available)

## Recommended Architecture

SemPKM is a layered system with clear separation between the semantic data core, the command/query surfaces, derived projections, and the presentation layer. The architecture follows an event-sourced CQRS pattern adapted for RDF: commands produce immutable events stored as named graphs in the triplestore, while reads go through SPARQL queries against a materialized current-state graph.

```
+---------------------------------------------------------------+
|                      PRESENTATION LAYER                       |
|  +-------------------+    +-------------------------------+   |
|  | Admin Shell       |    | Object Browser (React IDE)    |   |
|  | (htmx/vanilla)    |    | panes, tabs, command palette  |   |
|  | - Model mgmt      |    | - Renderers (obj/form/table/  |   |
|  | - Webhook config   |    |   cards/graph/dashboard)      |   |
|  | - System status    |    | - SHACL lint panel            |   |
|  +--------+----------+    +------+------------------------+   |
|           |                      |                            |
|           |    iframe boundary   |                            |
+-----------+----------------------+----------------------------+
            |                      |
+-----------v----------------------v----------------------------+
|                     FastAPI BACKEND                            |
|                                                               |
|  +------------------+  +------------------+  +-------------+  |
|  | Command API      |  | SPARQL Proxy     |  | Mental Model|  |
|  | (write surface)  |  | (read surface)   |  | Manager     |  |
|  | object.create    |  | forwards queries |  | install/    |  |
|  | object.patch     |  | to triplestore   |  | remove/list |  |
|  | body.set         |  +--------+---------+  +------+------+  |
|  | edge.create      |           |                   |         |
|  | edge.patch       |           |                   |         |
|  +--------+---------+           |                   |         |
|           |                     |                   |         |
|  +--------v---------+  +-------v---------+  +------v------+  |
|  | Event Producer   |  | Label Service   |  | Bundle      |  |
|  | (creates events) |  | (IRI -> label)  |  | Validator   |  |
|  +--------+---------+  +-----------------+  +-------------+  |
|           |                                                   |
|  +--------v-----------------------------------------+         |
|  | Core Services                                    |         |
|  | +----------------+  +------------------------+   |         |
|  | | SHACL Engine   |  | Prefix Registry        |   |         |
|  | | (async valid.) |  | (model > user > built-in)  |         |
|  | +----------------+  +------------------------+   |         |
|  | +----------------+  +------------------------+   |         |
|  | | Projection Svc |  | Webhook Dispatcher     |   |         |
|  | | (FS projection)|  | (best-effort outbound) |   |         |
|  | +----------------+  +------------------------+   |         |
|  +--------------------------------------------------+         |
|           |                                                   |
+-----------+---------------------------------------------------+
            |
+-----------v---------------------------------------------------+
|                     DATA LAYER                                 |
|  +----------------------------------------------------------+ |
|  | Triplestore (Blazegraph / RDF4J via Docker)               | |
|  |                                                           | |
|  | Named Graphs:                                             | |
|  |   sempkm:events/<eventId>   -- immutable event graphs     | |
|  |   sempkm:current            -- materialized current state | |
|  |   sempkm:shapes/<modelId>   -- installed SHACL shapes     | |
|  |   sempkm:ontology/<modelId> -- installed ontologies       | |
|  |   sempkm:validation/<id>    -- validation report graphs   | |
|  |                                                           | |
|  | Endpoints:                                                | |
|  |   SPARQL Query (read)                                     | |
|  |   SPARQL Update (internal only, not exposed externally)   | |
|  +----------------------------------------------------------+ |
+---------------------------------------------------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | Interface |
|-----------|---------------|-------------------|-----------|
| **Admin Shell (htmx)** | Model management, webhook config, system status pages | FastAPI backend via HTML-over-HTTP | HTTP (htmx AJAX, form posts) |
| **Object Browser (React IDE)** | Create/browse/explore objects; render views, dashboards, forms, graphs | FastAPI backend via JSON API | REST/JSON + SPARQL results |
| **FastAPI Backend** | Orchestrates all business logic; single point of authority for writes and read proxying | Triplestore, filesystem, external webhooks | HTTP REST |
| **Command API** | Accept write commands, produce events, update materialized state | Event Producer, SHACL Engine, Projection Service | Internal function calls |
| **SPARQL Proxy** | Forward SPARQL queries from UI to triplestore; inject prefix context | Triplestore SPARQL endpoint | SPARQL Protocol |
| **Event Producer** | Create immutable event named graphs from commands | Triplestore (SPARQL UPDATE), Webhook Dispatcher | Internal |
| **SHACL Engine** | Async validation of data against installed shapes; produce validation reports | Triplestore (reads shapes + data), stores validation reports | Internal; triggered by events |
| **Mental Model Manager** | Install/remove/list models; validate bundles; load ontologies + shapes + views into system | Bundle Validator, Triplestore, View Registry | Internal + API endpoints |
| **Bundle Validator** | Schema validation, ID namespacing, reference integrity, export policy checks on .sempkm-model archives | Mental Model Manager | Internal |
| **Label Service** | Resolve IRIs to human-readable labels (dcterms:title > rdfs:label > skos:prefLabel > schema:name > IRI fallback) | Triplestore (label queries), caching layer | Internal service, used by renderers |
| **Prefix Registry** | Merge model/user/built-in prefix mappings; QName resolution | Mental Model shapes (sh:declare), user config | Internal service |
| **Projection Service** | Generate read-only filesystem projection (markdown + sidecars) from current state | Triplestore, filesystem | Internal; triggered by events |
| **Webhook Dispatcher** | Send best-effort outbound notifications for events to configured URLs | External HTTP endpoints | HTTP POST |
| **Triplestore** | Durable RDF storage, SPARQL query/update, named graph management | FastAPI backend (all access mediated by backend) | SPARQL Protocol |

### Data Flow

#### Write Path (Command -> Event -> Projections)

```
User Action (UI)
    |
    v
Command API endpoint (e.g., POST /api/commands/object.create)
    |
    v
Command Handler
    |-- Validates command payload (Pydantic)
    |-- Generates event RDF (triples describing what changed)
    |-- Assigns eventId, commitId, timestamp
    |
    v
Event Producer
    |-- Writes event as named graph: sempkm:events/<eventId>
    |-- Updates materialized current-state graph: sempkm:current
    |   (applies the delta: INSERT/DELETE against current graph)
    |
    v
Post-Commit Pipeline (async, non-blocking)
    |
    +-- SHACL Engine
    |   |-- Loads relevant shapes from sempkm:shapes/<modelId>
    |   |-- Validates affected resources against shapes
    |   |-- Stores validation report as sempkm:validation/<reportId>
    |   |-- Updates current diagnostics index
    |   +-- Emits validation.completed event
    |
    +-- Projection Service
    |   |-- Determines affected objects from event
    |   |-- Regenerates X.md, X.meta.json, X.edges.json
    |   +-- Atomic file writes (temp + rename)
    |
    +-- Webhook Dispatcher
        |-- Matches event type against webhook subscriptions
        +-- POSTs event payload to registered URLs (best-effort)
```

#### Read Path (SPARQL Query)

```
User Action (UI: open view, dashboard, search)
    |
    v
React IDE / Admin Shell
    |-- Constructs or loads SPARQL query from view spec
    |-- Resolves {{contextIri}} template params
    |
    v
SPARQL Proxy (FastAPI)
    |-- Optionally injects PREFIX declarations from active registry
    |-- Forwards query to triplestore SPARQL endpoint
    |-- Queries run against sempkm:current graph (or UNION of graphs)
    |
    v
Triplestore
    |-- Executes SPARQL SELECT/CONSTRUCT/ASK
    |-- Returns results (JSON, XML, or Turtle)
    |
    v
FastAPI
    |-- Transforms results if needed (label enrichment)
    |
    v
React Renderer
    |-- Table: maps SELECT bindings to columns
    |-- Cards: maps SELECT bindings to card layout
    |-- Graph: maps CONSTRUCT results to node/edge rendering
    |-- Form: reads SHACL shape + current values, renders editable fields
    |-- Dashboard: composes panels, each running its own sub-query
```

#### Mental Model Installation Flow

```
User uploads .sempkm-model archive
    |
    v
Mental Model Manager
    |-- Extracts ZIP
    |-- Reads manifest.yaml
    |
    v
Bundle Validator
    |-- Schema validates manifest against manifest.schema.json
    |-- Checks view/dashboard specs against view schemas
    |-- Verifies ID uniqueness and namespacing (modelId::localId)
    |-- Checks reference integrity (all viewId refs exist)
    |-- Enforces cross-model export policy (private-by-default)
    |-- Verifies renderer compatibility with running SemPKM version
    |-- Validates {{param}} template substitution (IRI-only rule)
    |
    v
Installation
    |-- Loads ontology.ttl into sempkm:ontology/<modelId> named graph
    |-- Loads shapes.ttl into sempkm:shapes/<modelId> named graph
    |-- Registers views + dashboards in view/dashboard registry
    |-- Extracts prefix declarations from SHACL (sh:declare)
    |-- Registers dashboard defaults in type-based registry
    |-- Optionally loads seed.ttl into current graph
    |
    v
System ready to use new Mental Model types
```

## Patterns to Follow

### Pattern 1: CQRS with RDF (Command/Query Responsibility Segregation)

**What:** Strictly separate the write surface (Command API producing events) from the read surface (SPARQL queries against materialized state). Commands never return query results; queries never mutate state.

**When:** Always. This is the foundational architectural pattern.

**Why:** RDF triplestores are optimized for query workloads but poorly suited as transactional write engines with complex business logic. By mediating all writes through a command API that produces events, you get auditability, undo capability, and the freedom to reshape the materialized read model without changing the canonical event log.

**Example:**
```python
# Command handler - write path
@router.post("/api/commands/object.create")
async def create_object(cmd: ObjectCreateCommand):
    event = Event(
        id=generate_event_id(),
        type="object.changed",
        action="created",
        time=utcnow(),
        commit_id=generate_commit_id(),
        subject=cmd.iri,
        data=cmd.triples,
    )
    # 1. Write event to event graph
    await triplestore.insert_named_graph(
        f"sempkm:events/{event.id}", event.to_rdf()
    )
    # 2. Apply delta to current-state graph
    await triplestore.update(
        f"INSERT DATA {{ GRAPH sempkm:current {{ {event.data.as_ntriples()} }} }}"
    )
    # 3. Trigger async post-commit pipeline
    await post_commit_pipeline.enqueue(event)
    return {"eventId": event.id, "commitId": event.commit_id}
```

### Pattern 2: Named Graphs as Organizational Units

**What:** Use named graphs to partition RDF data by purpose: event graphs, current state, shapes, ontologies, validation reports. Each has a predictable IRI pattern.

**When:** All data storage in the triplestore.

**Why:** Named graphs provide natural boundaries for access control, lifecycle management, and query scoping. Events are immutable graphs. Current state is a mutable derived graph. Shapes are per-model graphs loaded/unloaded with model installation. This avoids the "big bag of triples" anti-pattern where everything lives in a default graph with no organizational structure.

**Graph naming convention:**
```
sempkm:events/<eventId>         -- immutable event
sempkm:current                   -- materialized current state (mutable derived)
sempkm:shapes/<modelId>          -- SHACL shapes for installed model
sempkm:ontology/<modelId>        -- ontology triples for installed model
sempkm:validation/<reportId>     -- immutable validation report
sempkm:system/config             -- system configuration
```

### Pattern 3: SHACL as the Single Source of UI Structure

**What:** SHACL shapes drive both validation AND form generation. A shape defines what fields exist, their types, ordering, grouping, and constraints. The form renderer reads shapes; the validation engine reads the same shapes. One definition, two uses.

**When:** Whenever displaying editable forms or validating data.

**Why:** Eliminates the dual-maintenance problem of separate form definitions and validation rules. SHACL already has the expressiveness needed (sh:property for fields, sh:order for layout, sh:group for sections, sh:datatype for input types, sh:in for dropdowns, sh:minCount for required fields). Mental Model authors define shapes once and get both forms and validation for free.

**Example flow:**
```
Shape: ex:ProjectShape
  sh:targetClass ex:Project
  sh:property [
    sh:path dcterms:title
    sh:name "Title"           --> form label
    sh:datatype xsd:string    --> text input
    sh:minCount 1             --> required field (+ validation)
    sh:order 1                --> first field
    sh:group ex:GroupBasics   --> "Basics" section
    sh:severity sh:Violation  --> violation if missing
  ]

Form Renderer reads shape --> generates form with "Title" text field, required
SHACL Validator reads shape --> validates that dcterms:title exists
```

### Pattern 4: Event-Driven Async Pipeline

**What:** After each commit (command execution), trigger an asynchronous pipeline of derived work: SHACL validation, filesystem projection updates, webhook notifications. The write path returns immediately; derived work happens in background workers.

**When:** Every write operation.

**Why:** Keeps write latency low. Validation can be expensive (loading shapes, running SHACL against potentially large datasets). Projection file writes are I/O-bound. Webhooks depend on external services. None of these should block the user from seeing their edit reflected in the UI.

**Consistency model:** The current-state graph is updated synchronously (so reads immediately reflect writes), but validation reports, projections, and webhooks are eventually consistent.

### Pattern 5: View Spec as Declarative Data Contract

**What:** Views are YAML specs combining a SPARQL query, a renderer type, layout configuration, and optional parameters. They are static declarations, not code. The runtime interprets them.

**When:** All data display in the Object Browser.

**Why:** Declarative view specs are portable across Mental Models, versionable, validatable at install time, and safe (no arbitrary code execution). The SPARQL query defines what data flows into the renderer; the layout config defines how it is presented. This clean separation means the same query could be rendered as a table or as cards by changing the renderer field.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Direct Triplestore Writes from Frontend

**What:** Allowing the React IDE or admin shell to send SPARQL UPDATE directly to the triplestore.

**Why bad:** Bypasses event sourcing entirely. No audit trail. No validation triggering. No projection updates. No webhook notifications. Breaks the entire CQRS contract.

**Instead:** All writes go through the Command API. The triplestore's SPARQL UPDATE endpoint is accessible only to the backend (internal network). The frontend has no direct path to mutate data.

### Anti-Pattern 2: Synchronous Validation Blocking Writes

**What:** Running SHACL validation synchronously before accepting a write, and rejecting writes that produce violations.

**Why bad:** Makes the system punitive rather than assistive. Users cannot save partial work. Validation latency blocks the write path. Contradicts the design principle "constraints are assistive (linting), not punitive."

**Instead:** Accept all writes immediately. Run validation asynchronously. Show violations in the lint panel as guidance. Only gate conformance-required operations (publish/export) on violations.

### Anti-Pattern 3: Big Bag of Triples (No Graph Partitioning)

**What:** Storing everything -- events, current state, shapes, validation reports -- in a single default graph.

**Why bad:** Makes it impossible to distinguish event history from current state. Cannot unload a Mental Model's shapes without scanning all triples. Queries against current state accidentally hit event data. Lifecycle management becomes a nightmare.

**Instead:** Strict named graph partitioning with predictable IRI patterns (see Pattern 2).

### Anti-Pattern 4: Coupling Renderers to Specific Ontologies

**What:** Building renderers that hardcode knowledge of specific ontology terms (e.g., a "Project renderer" that knows about `ex:status`).

**Why bad:** Breaks the Mental Model abstraction. New models cannot use renderers designed for old models. The whole point of SHACL-driven UX is that renderers are generic -- they read shape metadata to determine what to display.

**Instead:** Renderers are generic (table, form, cards, graph, dashboard). They read SHACL shapes and view specs to determine what to render. The only ontology-specific knowledge lives in the Mental Model's shapes and view definitions, not in renderer code.

### Anti-Pattern 5: Eager Full-Graph Projections

**What:** Regenerating the entire filesystem projection on every commit.

**Why bad:** O(n) work for every write, where n is the total number of objects. Causes filesystem churn that annoys tools like Obsidian's file watchers.

**Instead:** Incremental projection: examine the event to determine which objects were affected, and update only their files (X.md, X.meta.json, X.edges.json). Per the spec, "SemPKM updates only the minimum set of files required."

## Key Architectural Decisions Already Made

These decisions from the v0.3 design sessions define the architecture. They are settled, not open for debate.

| Decision | Implication |
|----------|-------------|
| Event log is canonical truth | Triplestore stores events as named graphs; current state is derived |
| Edges are first-class resources | sempkm:Edge resources with subject/predicate/object, not just triples |
| SHACL drives forms + linting | Single source for UI structure and validation |
| SPARQL for reads, Command API for writes | CQRS pattern; no external SPARQL UPDATE |
| htmx shell + React IDE (iframe) | Two distinct frontend technologies with iframe boundary |
| Private-by-default cross-model embedding | Explicit exports in manifest.yaml |
| Violations gate conformance ops only | Assistive validation, not punitive |
| Single-user v1 | No auth complexity in initial architecture |

## Component Build Order (Dependencies)

This is the critical section for roadmap planning. Components have strict dependencies that constrain build order.

### Tier 0: Foundation (must build first)

```
Triplestore Setup (Docker) --> everything depends on data storage
  |
  v
Named Graph Schema (graph naming conventions, IRI patterns)
  |
  v
RDF Serialization Utilities (Python: parse/serialize Turtle, JSON-LD, N-Triples)
```

**Rationale:** Nothing works without the triplestore running and the ability to read/write RDF data. The named graph schema defines the organizational structure for all subsequent data. These are pure infrastructure with no dependencies on business logic.

### Tier 1: Core Data Path (write path + read path)

```
Event Model (event RDF structure, event types)
  |
  v
Command API (object.create, object.patch, body.set, edge.create, edge.patch)
  |                                                      |
  v                                                      v
Event Producer (write events to named graphs)    Materialization
  |                                              (project events
  v                                               to current state)
SPARQL Proxy (read surface for frontend)
```

**Rationale:** The write path and read path form the minimum viable data flow. Without events and materialization, you have no data. Without SPARQL reads, you cannot display anything. The Command API is deliberately minimal (6 commands).

**Dependencies:**
- Event Model depends on Tier 0 (needs RDF serialization + named graphs)
- Command API depends on Event Model
- Materialization depends on Event Model
- SPARQL Proxy depends on Triplestore (Tier 0)

### Tier 2: Semantic Services (make data meaningful)

```
Prefix Registry (merge model/user/built-in prefixes)
  |
  v
Label Service (IRI -> human label resolution)
  |
  v
SHACL Engine (async validation, report storage)
```

**Rationale:** These services make raw RDF data usable. Labels turn IRIs into readable names. Prefixes enable QName display. SHACL validation provides the lint/conformance layer. They depend on Tier 1 because they read data from the triplestore, but they are independent of each other and can be built in parallel.

**Dependencies:**
- All three depend on Tier 1 (need data in the triplestore to operate on)
- Label Service depends on Prefix Registry (for QName fallbacks)
- SHACL Engine depends on shapes being loadable (but this can use test shapes initially)

### Tier 3: Mental Model System (installable experiences)

```
Bundle Format Parser (read .sempkm-model ZIP archives)
  |
  v
Bundle Validator (schema, IDs, references, exports, renderers)
  |
  v
Mental Model Manager (install/remove/list)
  |-- Loads ontology into sempkm:ontology/<modelId>
  |-- Loads shapes into sempkm:shapes/<modelId>
  |-- Registers views + dashboards
  |-- Extracts prefix declarations
  +-- Loads seed data
```

**Rationale:** Mental Models are the primary user-facing packaging of ontologies + shapes + views. The manager depends on the SHACL engine (to validate shapes are well-formed), the prefix registry (to extract declarations), and the view registry (to register views). This is why it is Tier 3, not Tier 2.

**Dependencies:**
- Depends on Tier 2 (prefix extraction, SHACL shapes)
- Depends on view/dashboard registry (can be built as part of this tier)
- Starter model (Basic PKM) is the first test case

### Tier 4: Presentation Layer (UI)

```
Admin Shell (htmx)                    Object Browser (React IDE)
  |-- Model management UI               |-- Workspace layout (panes, tabs)
  |-- Webhook config                     |-- Command palette
  |-- System status                      |-- Object renderer
                                         |-- Form renderer (SHACL-driven)
                                         |-- Table renderer
                                         |-- Cards renderer
                                         |-- Graph renderer (2D)
                                         |-- Dashboard renderer
                                         |-- SHACL lint panel
                                         |-- SPARQL editor
```

**Rationale:** The presentation layer depends on everything below it. However, the admin shell and Object Browser can be developed in parallel with each other. Within the Object Browser, renderers can be built incrementally: start with the object renderer and form renderer (most fundamental), then table, cards, dashboard, and graph.

**Suggested renderer build order within Tier 4:**
1. Object renderer (view a single object's properties)
2. Form renderer (create/edit via SHACL shapes -- proves the SHACL-UI contract)
3. Table renderer (list objects -- most common view type)
4. Dashboard renderer (compose panels -- enables the "wow-in-10-minutes" demo)
5. Cards renderer (visual alternative to tables)
6. Graph renderer (requires graph layout library, most complex)

**Dependencies:**
- Object renderer depends on Label Service, Prefix Registry (Tier 2)
- Form renderer depends on SHACL Engine (Tier 2), Command API (Tier 1)
- Table renderer depends on SPARQL Proxy (Tier 1)
- Dashboard renderer depends on other renderers + view registry (Tier 3)
- Lint panel depends on SHACL Engine (Tier 2)

### Tier 5: Derived Services (can ship after core UX works)

```
Projection Service (filesystem projection)
  |-- Watch events, generate .md + .meta.json + .edges.json
  |
Webhook Dispatcher (outbound event notifications)
  |-- Match events to subscriptions, POST to URLs
  |
Export Service (JSON-LD export)
  |-- Serialize subsets of current graph as JSON-LD
```

**Rationale:** These are valuable but not required for the core create/browse/explore loop. Projections enable Obsidian interop. Webhooks enable n8n automation. Exports enable data portability. All three depend on the event system (Tier 1) and can be built incrementally after the core UX is functional.

## Scalability Considerations

This is a single-user self-hosted application, so scale concerns are modest. The main concern is responsiveness with growing knowledge bases.

| Concern | At 100 objects | At 10K objects | At 100K objects |
|---------|---------------|---------------|-----------------|
| **SPARQL query latency** | Sub-millisecond | Low ms (with indexes) | 10-100ms; may need query optimization hints |
| **Event log size** | Negligible | Hundreds of named graphs; fine | Thousands of named graphs; consider archival/compaction strategy |
| **SHACL validation** | Near-instant | Seconds (validate affected objects only) | Validate incrementally (only changed resources), never full-graph |
| **Projection generation** | Trivial | Incremental updates keep it fast | Incremental is essential; full regen would be minutes |
| **Label cache** | No cache needed | In-memory cache advisable | LRU cache with TTL; preload common labels |
| **Triplestore memory** | <100MB | ~1GB | 2-4GB; Blazegraph needs JVM heap tuning |

### Performance-Critical Decisions

1. **Label Service must cache aggressively.** Every rendered IRI triggers a label lookup. At 10K objects with views showing 50+ items, this is thousands of lookups per page load. Use an in-memory LRU cache invalidated by object.changed events.

2. **SHACL validation must be incremental.** Only validate resources affected by the current commit, not the entire graph. The event payload includes the subject IRI; use that to scope validation.

3. **Materialization must be synchronous but fast.** The delta between event triples and current-state graph is typically small (a few triples per command). Use targeted INSERT DATA / DELETE DATA against the current-state graph, not full rematerialization.

4. **SPARQL queries in view specs should include LIMIT.** Unbounded SELECTs against a growing graph will eventually become slow. View specs already support `defaults.pageSize`; enforce it at the SPARQL level.

## Technology-Specific Architecture Notes

### Blazegraph vs RDF4J

The project lists both as options. Architecture implications:

**Blazegraph:**
- Standalone Java application, deployed via Docker
- Native SPARQL 1.1 endpoint (REST API)
- Good performance for medium datasets (up to ~50M triples)
- Built-in named graph support (quads mode required)
- Note: Blazegraph is in maintenance mode (no active development), but stable for a single-user PKM
- SHACL validation is NOT built into Blazegraph; must be done application-side

**RDF4J:**
- Java framework; RDF4J Server provides SPARQL endpoint via Docker
- More actively maintained than Blazegraph
- Native SHACL validation support (can offload validation to the store)
- Better Linked Data Fragments support
- Slightly more complex setup but more future-proof

**Recommendation:** Start with Blazegraph for simplicity (single JAR, well-documented REST API, good enough for v1). Plan the architecture so the triplestore is swappable behind the SPARQL Proxy abstraction. Application-side SHACL validation (using a Python library like pyshacl) keeps the architecture store-agnostic.

### Python SHACL Ecosystem

Application-side SHACL validation in Python uses **pyshacl**. The architecture should:
- Load shapes from the triplestore (or cache them from model installation)
- Load the data subgraph for affected resources
- Run pyshacl validation
- Store the resulting validation report as RDF in a named graph

### FastAPI Backend Structure

```
sempkm/
  api/
    commands.py       # Command API endpoints
    sparql.py         # SPARQL proxy endpoint
    models.py         # Mental Model management endpoints
    webhooks.py       # Webhook configuration endpoints
    system.py         # System status endpoints
  core/
    events.py         # Event model and producer
    materializer.py   # Event -> current state projection
    shacl_engine.py   # Async SHACL validation
    label_service.py  # IRI -> label resolution
    prefix_registry.py # Prefix management
  models/
    manager.py        # Mental Model install/remove/list
    validator.py      # Bundle validation
    parser.py         # .sempkm-model ZIP parsing
  projections/
    filesystem.py     # Filesystem projection service
  webhooks/
    dispatcher.py     # Outbound webhook delivery
  triplestore/
    client.py         # SPARQL query/update client (abstracts Blazegraph/RDF4J)
    graphs.py         # Named graph management
  config.py           # Application configuration
  main.py             # FastAPI app entry point
```

## Sources

- Project specs: `/home/james/Code/SemPKM/orig_specs/docs/vision.md` (architecture overview sections 5-8)
- Decision log: `/home/james/Code/SemPKM/orig_specs/docs/decisions/v0.3.md`
- API spec: `/home/james/Code/SemPKM/orig_specs/spec/api/overview.md`
- SHACL UI profile: `/home/james/Code/SemPKM/orig_specs/spec/shacl-ui/shacl-ui-profile.md`
- Gating policy: `/home/james/Code/SemPKM/orig_specs/spec/shacl-ui/gating.md`
- View specs: `/home/james/Code/SemPKM/orig_specs/spec/views/renderers.md`, `params.md`, `dashboards.md`
- Projection spec: `/home/james/Code/SemPKM/orig_specs/spec/projections/projection.md`, `refresh.md`
- Prefix registry: `/home/james/Code/SemPKM/orig_specs/spec/prefixes/prefix-registry.md`
- Label service: `/home/james/Code/SemPKM/orig_specs/spec/ui/labels.md`
- Mental Model format: `/home/james/Code/SemPKM/orig_specs/spec/mental-model/bundle_format.md`, `validation.md`, `exports.md`
- Event types: `/home/james/Code/SemPKM/orig_specs/spec/events/types.md`
- Starter model: `/home/james/Code/SemPKM/orig_specs/models/starter-basic-pkm/` (manifest, ontology, shapes, views)
- W3C SHACL spec (training data, MEDIUM confidence)
- Blazegraph and RDF4J architecture (training data, MEDIUM confidence)
- Event sourcing / CQRS patterns (training data, HIGH confidence -- well-established patterns)
- pyshacl library capabilities (training data, LOW confidence -- needs version verification)
