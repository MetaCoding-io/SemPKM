# Phase 1: Core Data Foundation - Research

**Researched:** 2026-02-21
**Domain:** Event-sourced RDF data path (Python/FastAPI + RDF4J triplestore + htmx dev console)
**Confidence:** HIGH

## Summary

Phase 1 establishes SemPKM's foundational data layer: a Docker Compose deployment with three services (FastAPI backend, RDF4J triplestore, nginx-served dev console) connected through an event-sourced write path that stores immutable events as RDF named graphs and materializes a current graph state. The command API is RPC-style (`POST /api/commands`) accepting JSON-LD payloads with batch support and all-or-nothing transaction semantics.

The core technical challenge is implementing event sourcing on top of RDF4J named graphs -- a novel architecture where each API request produces one immutable named graph containing the event metadata and the changed triples, and a separate "current state" named graph is eagerly updated to reflect the accumulated state. RDF4J's native store with context (named graph) indexing, full SPARQL 1.1 UPDATE support, and transaction isolation make this feasible. The Python stack uses rdflib (7.6.0) with its built-in JSON-LD support and the new RDF4J Store integration, FastAPI with Pydantic v2 discriminated unions for command dispatch, and httpx as the async HTTP client for triplestore communication.

**Primary recommendation:** Use rdflib's RDF4J Store/Client integration (available since rdflib 7.5.0) for programmatic triplestore access with transaction support, direct SPARQL UPDATE for event graph creation, and SPARQL SELECT/CONSTRUCT via the RDF4J REST API (`/repositories/{id}`) for reads. Build the command API as a single FastAPI endpoint with Pydantic discriminated unions routing to per-command handlers.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Event model
- One event graph per API request (batch of commands shares a single named graph)
- Rich metadata per event: timestamp, operation type, affected IRIs, human-readable description
- Eager materialization: current state graph is updated on each commit, not reconstructed on read
- Events are immutable for v1, but graph naming should be designed to support future archival/compaction without breaking references

#### Command API contract
- RPC-style single endpoint: POST /api/commands with `{command: 'object.create', params: {...}}`
- JSON-LD payloads throughout (both request and response)
- Batch support: accept an array of commands in a single request
- All-or-nothing transaction semantics: entire batch succeeds or entire batch rolls back, no partial commits

#### Object identity
- IRI pattern: `{namespace}/{Type}/{slug-or-uuid}` (e.g., `https://example.org/data/Person/alice` or `https://example.org/data/Note/550e8400-...`)
- Client can provide a slug; system falls back to UUID if not provided
- User-configurable base namespace (default provided, user can set their own domain for future federation)
- Type is fixed at creation and encoded in the IRI path; type changes are not allowed (create a new object instead)
- Edges are first-class resources with their own IRIs (enables edge annotations, metadata, and versioning in later phases)

#### Frontend bootstrap
- Dev console: SPARQL query box + command form for manual testing, plus health/status page with version info
- htmx + vanilla JS from the start (aligns with Phase 4 admin portal stack)
- Served from a separate container (e.g., nginx), not from FastAPI directly
- SPARQL query box auto-injects common prefixes (rdf:, rdfs:, sempkm:, etc.)

### Claude's Discretion
- Docker Compose service configuration and networking details
- RDF4J repository type and configuration
- FastAPI project structure and internal architecture
- Event graph IRI naming scheme (within the archival-compatible constraint)
- Error response format and HTTP status code mapping
- Dev console visual design and layout

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CORE-01 | System persists all writes as immutable events stored in RDF named graphs within the triplestore | Event graph model using RDF4J named graphs (contexts); each event is a named graph with metadata triples + data triples; SPARQL UPDATE INSERT DATA with GRAPH clause; rdflib RDF4J Store transaction support |
| CORE-02 | System materializes a current graph state projection derived from the event log | Eager materialization into a dedicated `sempkm:current` named graph; on each commit, apply INSERT/DELETE against the current graph within the same RDF4J transaction; SPARQL UPDATE DELETE/INSERT patterns |
| CORE-03 | RDF4J triplestore is deployed and configured via Docker Compose | `eclipse/rdf4j-workbench` Docker image (latest 5.x); native store with `spoc,posc,cspo` indexes for context-based queries; repository auto-creation via REST API PUT on startup; `/var/rdf4j` volume for persistence |
| CORE-04 | User can execute SPARQL queries against the current graph state via a read endpoint | FastAPI GET/POST `/api/sparql` endpoint that proxies to RDF4J's `/repositories/{id}` with FROM clause scoping to current graph; returns `application/sparql-results+json` |
| CORE-05 | System provides a command API for writes: object.create, object.patch, body.set, edge.create, edge.patch | FastAPI POST `/api/commands` with Pydantic discriminated union on `command` field; per-command handlers generate RDF triples; batch wrapped in single RDF4J transaction producing one event graph |
| ADMN-01 | User can deploy SemPKM via docker-compose up with all services | Three-service Docker Compose: rdf4j (triplestore), api (FastAPI/uvicorn), frontend (nginx serving htmx); health checks with `depends_on: condition: service_healthy`; named Docker network |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | latest (0.115+) | Async Python web framework, command API + SPARQL proxy | Standard async Python API framework; Pydantic v2 integration, OpenAPI docs, dependency injection |
| rdflib | 7.6.0 | RDF graph manipulation, JSON-LD parsing/serialization, SPARQL | The canonical Python RDF library; built-in JSON-LD support since 6.0; new RDF4J Store/Client since 7.5 |
| Pydantic | v2 (2.x) | Request/response validation, settings management | Ships with FastAPI; discriminated unions for command dispatch; BaseSettings for configuration |
| uvicorn | 0.41+ | ASGI server for FastAPI | Standard production ASGI server; async performance |
| httpx | 0.28+ | Async HTTP client for RDF4J REST API communication | Modern async Python HTTP client; used internally by rdflib RDF4J store |
| RDF4J Server | 5.x (Docker: `eclipse/rdf4j-workbench`) | RDF triplestore with SPARQL 1.1 and named graph support | Actively maintained; full SPARQL 1.1 Query + Update; REST API; transaction support; Docker image available |
| htmx | 2.0 | Dev console frontend interactivity | Minimal JS; server-rendered HTML fragments; aligns with Phase 4 admin portal decision |
| nginx | stable-alpine | Static file serving + reverse proxy for dev console | Lightweight; serves htmx frontend from separate container per user decision |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Jinja2 | 3.x | HTML template rendering for dev console pages served by FastAPI | Dev console partial templates; SPARQL results rendering; htmx fragment responses |
| python-dotenv | 1.x | Environment variable loading | Local development; Docker Compose .env file support |
| jinja2-fragments | 0.4+ | Render individual Jinja2 blocks as HTML fragments | htmx partial updates without full page render; used with `hx-target` swaps |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rdflib RDF4J Store | SPARQLWrapper + raw HTTP | SPARQLWrapper is simpler but lacks transaction support and named graph management; rdflib provides unified RDF manipulation + serialization |
| rdflib RDF4J Store | Direct httpx calls to RDF4J REST API | More control but must handle SPARQL construction, result parsing, and transaction lifecycle manually; rdflib abstracts this |
| Jinja2 templates | FastAPI returning raw HTML strings | Templates provide layout inheritance, partials, and maintainability |
| nginx | Caddy | Caddy has simpler config and automatic HTTPS but nginx is more widely known and lighter for static serving |

**Installation:**
```bash
# Backend (Python 3.12+)
pip install fastapi[standard] rdflib[rdf4j] httpx pydantic-settings jinja2 jinja2-fragments

# Frontend (CDN or vendored)
# htmx 2.0 via CDN: https://unpkg.com/htmx.org@2.0.4
```

## Architecture Patterns

### Recommended Project Structure
```
sempkm/
├── docker-compose.yml
├── .env                          # Base namespace, service URLs
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app factory, lifespan, middleware
│   │   ├── config.py             # Pydantic BaseSettings (env vars)
│   │   ├── dependencies.py       # Shared deps (triplestore client)
│   │   ├── commands/
│   │   │   ├── __init__.py
│   │   │   ├── router.py         # POST /api/commands endpoint
│   │   │   ├── schemas.py        # Pydantic command models (discriminated union)
│   │   │   ├── dispatcher.py     # Command -> handler routing
│   │   │   ├── handlers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── object_create.py
│   │   │   │   ├── object_patch.py
│   │   │   │   ├── body_set.py
│   │   │   │   ├── edge_create.py
│   │   │   │   └── edge_patch.py
│   │   │   └── exceptions.py     # Command-specific errors
│   │   ├── sparql/
│   │   │   ├── __init__.py
│   │   │   ├── router.py         # GET/POST /api/sparql endpoint
│   │   │   └── client.py         # SPARQL query execution against RDF4J
│   │   ├── events/
│   │   │   ├── __init__.py
│   │   │   ├── store.py          # Event graph creation + materialization
│   │   │   └── models.py         # Event metadata RDF vocabulary
│   │   ├── rdf/
│   │   │   ├── __init__.py
│   │   │   ├── namespaces.py     # SemPKM namespace definitions
│   │   │   ├── iri.py            # IRI minting (namespace + type + slug/uuid)
│   │   │   └── jsonld.py         # JSON-LD <-> rdflib conversion utilities
│   │   ├── triplestore/
│   │   │   ├── __init__.py
│   │   │   ├── client.py         # RDF4J client wrapper (connection, health)
│   │   │   └── setup.py          # Repository creation on startup
│   │   └── health/
│   │       ├── __init__.py
│   │       └── router.py         # GET /api/health
│   └── tests/
│       ├── conftest.py
│       ├── test_commands/
│       ├── test_sparql/
│       └── test_events/
├── frontend/
│   ├── Dockerfile                # nginx:stable-alpine
│   ├── nginx.conf                # Static files + API proxy
│   ├── static/
│   │   ├── index.html            # Dev console main page
│   │   ├── sparql.html           # SPARQL query page
│   │   ├── commands.html         # Command form page
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── app.js            # Minimal vanilla JS (prefix injection, etc.)
│   └── templates/                # (optional) If using FastAPI to serve fragments
└── config/
    └── rdf4j/
        └── sempkm-repo.ttl       # Native store repository config template
```

### Pattern 1: Event-Sourced Write Path

**What:** Every write operation produces an immutable event stored as a named graph in RDF4J, then eagerly materializes changes into the current state graph.

**When to use:** All command API writes.

**Architecture:**
```
Client Request -> FastAPI /api/commands
  -> Parse & validate (Pydantic discriminated union)
  -> Begin RDF4J transaction
  -> Execute command handler(s) -> generate triples
  -> Create event named graph (metadata + data triples)
  -> Apply changes to current state graph (INSERT/DELETE)
  -> Commit transaction (atomic)
  -> Return JSON-LD response
```

**Example - Event Graph Structure:**
```sparql
# Event graph IRI: sempkm:event/{uuid}
# Contains metadata about the event + the actual data triples

INSERT DATA {
  GRAPH <urn:sempkm:event:550e8400-e29b-41d4-a716-446655440000> {
    <urn:sempkm:event:550e8400-e29b-41d4-a716-446655440000>
      a sempkm:Event ;
      sempkm:timestamp "2026-02-21T10:30:00Z"^^xsd:dateTime ;
      sempkm:operationType "object.create" ;
      sempkm:affectedIRI <https://example.org/data/Person/alice> ;
      sempkm:description "Created Person: alice" .

    <https://example.org/data/Person/alice>
      a <https://example.org/data/Person> ;
      rdfs:label "Alice" ;
      schema:name "Alice Smith" .
  }
}
```

**Example - Current State Materialization:**
```sparql
# For object.create: INSERT new triples into current state
INSERT DATA {
  GRAPH <urn:sempkm:current> {
    <https://example.org/data/Person/alice>
      a <https://example.org/data/Person> ;
      rdfs:label "Alice" ;
      schema:name "Alice Smith" .
  }
}

# For object.patch: DELETE old + INSERT new in current state
DELETE {
  GRAPH <urn:sempkm:current> {
    <https://example.org/data/Person/alice> schema:name ?oldName .
  }
}
INSERT {
  GRAPH <urn:sempkm:current> {
    <https://example.org/data/Person/alice> schema:name "Alice Jones" .
  }
}
WHERE {
  GRAPH <urn:sempkm:current> {
    <https://example.org/data/Person/alice> schema:name ?oldName .
  }
}
```

### Pattern 2: RPC-Style Command Dispatch with Pydantic Discriminated Unions

**What:** A single `POST /api/commands` endpoint accepts different command types via a discriminator field, dispatching to the appropriate handler.

**When to use:** All write operations.

**Example:**
```python
# schemas.py
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field

class ObjectCreate(BaseModel):
    command: Literal["object.create"]
    params: ObjectCreateParams

class ObjectPatch(BaseModel):
    command: Literal["object.patch"]
    params: ObjectPatchParams

class BodySet(BaseModel):
    command: Literal["body.set"]
    params: BodySetParams

class EdgeCreate(BaseModel):
    command: Literal["edge.create"]
    params: EdgeCreateParams

class EdgePatch(BaseModel):
    command: Literal["edge.patch"]
    params: EdgePatchParams

Command = Annotated[
    Union[ObjectCreate, ObjectPatch, BodySet, EdgeCreate, EdgePatch],
    Field(discriminator="command"),
]

class CommandRequest(BaseModel):
    """Single command or batch. Batch = list of commands."""
    commands: list[Command] | Command
```

```python
# router.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api")

@router.post("/commands")
async def execute_commands(
    request: CommandRequest,
    triplestore=Depends(get_triplestore),
):
    commands = request.commands if isinstance(request.commands, list) else [request.commands]
    # All-or-nothing: single transaction wrapping all commands
    async with triplestore.transaction() as txn:
        results = []
        for cmd in commands:
            handler = get_handler(cmd.command)
            result = await handler(cmd.params, txn)
            results.append(result)
    return {"results": results}
```

### Pattern 3: IRI Minting

**What:** Generate deterministic, human-readable IRIs from namespace + type + slug, with UUID fallback.

**When to use:** `object.create` and `edge.create` commands.

**Example:**
```python
# iri.py
import uuid
from urllib.parse import quote

def mint_object_iri(
    base_namespace: str,
    type_name: str,
    slug: str | None = None,
) -> str:
    """Mint an IRI for a new object.

    Pattern: {namespace}/{Type}/{slug-or-uuid}
    Example: https://example.org/data/Person/alice
    """
    identifier = slug if slug else str(uuid.uuid4())
    safe_id = quote(identifier, safe="")
    return f"{base_namespace.rstrip('/')}/{type_name}/{safe_id}"

def mint_edge_iri(base_namespace: str) -> str:
    """Mint an IRI for a new edge resource.

    Edges always get UUIDs (no human-readable slugs).
    Pattern: {namespace}/Edge/{uuid}
    """
    return f"{base_namespace.rstrip('/')}/Edge/{uuid.uuid4()}"
```

### Pattern 4: SPARQL Read Proxy

**What:** FastAPI endpoint that proxies SPARQL queries to RDF4J, scoping them to the current state graph.

**When to use:** All read operations via `/api/sparql`.

**Example:**
```python
# sparql/router.py
@router.post("/sparql")
async def sparql_query(
    query: str = Form(...),
    triplestore=Depends(get_triplestore),
):
    """Execute SPARQL SELECT against the current state graph."""
    # Inject FROM clause to scope to current graph if not already present
    scoped_query = scope_to_current_graph(query)
    result = await triplestore.query(scoped_query)
    return Response(
        content=result,
        media_type="application/sparql-results+json",
    )
```

### Pattern 5: Docker Compose Service Topology

**What:** Three-service deployment with health checks and dependency ordering.

**When to use:** The standard deployment model.

**Example:**
```yaml
# docker-compose.yml
services:
  triplestore:
    image: eclipse/rdf4j-workbench:5.0.1
    ports:
      - "8080:8080"
    volumes:
      - rdf4j_data:/var/rdf4j
    environment:
      JAVA_OPTS: "-Xmx1g"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/rdf4j-server/protocol"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - sempkm

  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      TRIPLESTORE_URL: http://triplestore:8080/rdf4j-server
      REPOSITORY_ID: sempkm
      BASE_NAMESPACE: https://example.org/data/
    depends_on:
      triplestore:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - sempkm

  frontend:
    image: nginx:stable-alpine
    ports:
      - "3000:80"
    volumes:
      - ./frontend/static:/usr/share/nginx/html:ro
      - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      api:
        condition: service_healthy
    networks:
      - sempkm

networks:
  sempkm:

volumes:
  rdf4j_data:
```

### Anti-Patterns to Avoid

- **Reconstructing state on read:** Never replay the full event log to answer queries. Eager materialization means the current state graph is always up-to-date. This is a locked user decision.
- **Using SPARQL UPDATE as the external write surface:** All writes must go through the command API to maintain the event log. SPARQL UPDATE is only used internally by the backend.
- **Storing events outside the triplestore:** Events are RDF named graphs inside RDF4J, not in a separate database. This is a core architectural decision.
- **Serving frontend from FastAPI:** The user decided the dev console runs in a separate nginx container. FastAPI serves only the API.
- **Using `application/sparql-query` content type directly:** RDF4J expects form-encoded SPARQL queries via POST (`application/x-www-form-urlencoded` with `query=...`), not raw SPARQL in the body.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RDF graph manipulation | Custom triple manipulation code | rdflib Graph/Dataset | rdflib handles RDF parsing, serialization, namespace management, and SPARQL; battle-tested |
| JSON-LD processing | Custom JSON-to-RDF conversion | rdflib built-in JSON-LD serializer/parser | JSON-LD spec is complex (expansion, compaction, framing); rdflib handles it since v6.0 |
| SPARQL query construction | String concatenation of SPARQL | rdflib prepareQuery or f-strings with parameterized bindings | String concat risks SPARQL injection; use parameterized patterns |
| RDF4J REST API communication | Raw HTTP calls with manual error handling | rdflib RDF4J Store/Client (rdflib 7.5+) | Handles transactions, content negotiation, result parsing, connection management |
| UUID generation | Custom ID schemes | Python uuid.uuid4() | Standard, collision-resistant |
| HTTP client | requests (sync) | httpx (async) | FastAPI is async; httpx supports async natively and is used by rdflib's RDF4J integration |
| Environment/settings management | Manual os.environ parsing | Pydantic BaseSettings | Type validation, .env support, documentation via schema |

**Key insight:** The RDF ecosystem has mature Python libraries. rdflib 7.6.0 with the RDF4J Store integration handles the entire triplestore communication layer, including transactions, named graph management, and SPARQL execution. Building a custom HTTP layer for RDF4J is unnecessary.

## Common Pitfalls

### Pitfall 1: RDF4J Named Graph Deletion on Clear
**What goes wrong:** RDF4J does not support empty named graphs. When you clear all triples from a named graph, the graph itself is deleted from the repository and disappears from `graph_names()`.
**Why it happens:** RDF4J's storage model treats named graphs as implicit -- they exist if and only if they contain triples.
**How to avoid:** Never clear event graphs (they are immutable). For the current state graph, if it needs to be empty, keep a sentinel triple (e.g., `<urn:sempkm:current> a sempkm:StateGraph`) that is never removed.
**Warning signs:** Graph name not found after operations that were expected to preserve it.

### Pitfall 2: Transaction Isolation with Eager Materialization
**What goes wrong:** If the event graph write and current state update are not in the same transaction, a crash between them leaves the system in an inconsistent state (event recorded but state not updated, or vice versa).
**Why it happens:** Developers might write the event first, commit, then update the current state in a separate operation.
**How to avoid:** Always wrap event graph creation AND current state materialization in a single RDF4J transaction. Use `conn.begin()` ... `conn.commit()` with rollback on error. rdflib's RDF4J Store supports this via the `transaction()` context manager.
**Warning signs:** Current state missing recent changes; event graphs existing without corresponding state changes.

### Pitfall 3: SPARQL Query Scoping to Current Graph
**What goes wrong:** SPARQL queries return results from ALL named graphs (including event graphs), not just the current state.
**Why it happens:** Without explicit FROM or GRAPH clauses, SPARQL queries against the default graph in RDF4J query the union of all graphs (depending on repository configuration).
**How to avoid:** Always scope read queries to the current state graph using `FROM <urn:sempkm:current>` or `GRAPH <urn:sempkm:current> { ... }`. The SPARQL proxy endpoint should inject this scoping automatically.
**Warning signs:** Duplicate results; event metadata appearing in regular queries; query performance degradation as event count grows.

### Pitfall 4: JSON-LD Context Management
**What goes wrong:** JSON-LD responses lack a proper `@context`, making them unusable as linked data. Or contexts reference remote URLs that cause network calls on every parse.
**Why it happens:** Developers serialize RDF to JSON-LD without specifying a compact context, producing verbose expanded form with full IRIs.
**How to avoid:** Define a SemPKM JSON-LD context once (with prefix mappings for sempkm:, rdf:, rdfs:, schema:, etc.) and use it consistently for serialization via `graph.serialize(format='json-ld', context=SEMPKM_CONTEXT)`. Serve the context locally, never reference external URLs.
**Warning signs:** Response payloads contain full IRIs instead of prefixed names; responses are much larger than expected.

### Pitfall 5: RDF4J Repository Not Created on First Start
**What goes wrong:** The FastAPI backend starts but cannot connect to a repository because it does not exist yet.
**Why it happens:** `eclipse/rdf4j-workbench` starts with no repositories. The repository must be created programmatically.
**How to avoid:** Implement a startup check in FastAPI's lifespan that creates the repository if it does not exist, using a PUT to `/rdf4j-server/repositories/{id}` with a Turtle configuration body. Use `depends_on: condition: service_healthy` in Docker Compose to ensure RDF4J is ready.
**Warning signs:** 404 errors from RDF4J; connection refused during startup.

### Pitfall 6: Batch Command Partial Failure
**What goes wrong:** In a batch of commands, command 3 of 5 fails, but commands 1-2 have already been committed.
**Why it happens:** Each command handler commits independently instead of operating within a shared transaction.
**How to avoid:** Wrap the entire batch in a single RDF4J transaction. If any command fails, rollback the entire transaction. This is a locked user decision (all-or-nothing semantics).
**Warning signs:** Partial state changes visible after batch failures; event graphs with incomplete data.

### Pitfall 7: RDF4J Index Configuration for Context Queries
**What goes wrong:** Queries scoped to specific named graphs (contexts) are slow because the default indexes (`spoc`, `posc`) do not start with the context field.
**Why it happens:** The default native store indexes optimize for subject-based and predicate-based lookups but not context-first lookups.
**How to avoid:** Add a `cspo` (context-subject-predicate-object) index to the native store configuration. This is critical because SemPKM's primary read pattern is "all triples in the current state graph" (`GRAPH <urn:sempkm:current> { ?s ?p ?o }`).
**Warning signs:** Slow query performance that worsens as the number of named graphs grows; full index scans in RDF4J query logs.

## Code Examples

### RDF4J Repository Configuration (Turtle)
```turtle
# config/rdf4j/sempkm-repo.ttl
# Source: https://rdf4j.org/documentation/reference/configuration/
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix config: <tag:rdf4j.org,2023:config/> .

[] a config:Repository ;
   config:rep.id "sempkm" ;
   rdfs:label "SemPKM Knowledge Base" ;
   config:rep.impl [
      config:rep.type "openrdf:SailRepository" ;
      config:sail.impl [
         config:sail.type "openrdf:NativeStore" ;
         config:native.tripleIndexes "spoc,posc,cspo" ;
         config:sail.defaultQueryEvaluationMode "STANDARD"
      ]
   ] .
```

### Repository Auto-Creation on Startup
```python
# triplestore/setup.py
# Source: https://github.com/eclipse-rdf4j/rdf4j/discussions/3130
import httpx
from pathlib import Path

async def ensure_repository(base_url: str, repo_id: str) -> None:
    """Create RDF4J repository if it does not exist."""
    repo_url = f"{base_url}/repositories/{repo_id}"
    async with httpx.AsyncClient() as client:
        # Check if repository exists
        resp = await client.get(f"{repo_url}/size")
        if resp.status_code == 200:
            return  # Already exists

        # Create repository with native store config
        config_path = Path(__file__).parent.parent.parent / "config" / "rdf4j" / "sempkm-repo.ttl"
        config_ttl = config_path.read_text()
        resp = await client.put(
            repo_url,
            content=config_ttl,
            headers={"Content-Type": "text/turtle"},
        )
        resp.raise_for_status()
```

### Event Store - Creating an Event Graph
```python
# events/store.py
from datetime import datetime, timezone
from uuid import uuid4
from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS, XSD

SEMPKM = Namespace("urn:sempkm:")

def create_event_graph(
    operation_type: str,
    affected_iris: list[str],
    description: str,
    data_triples: list[tuple],
) -> tuple[URIRef, Graph]:
    """Create an immutable event named graph.

    Returns (event_graph_iri, graph_with_triples).
    """
    event_id = str(uuid4())
    event_iri = URIRef(f"urn:sempkm:event:{event_id}")

    g = Graph(identifier=event_iri)

    # Event metadata
    g.add((event_iri, RDF.type, SEMPKM.Event))
    g.add((event_iri, SEMPKM.timestamp,
           Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime)))
    g.add((event_iri, SEMPKM.operationType, Literal(operation_type)))
    g.add((event_iri, SEMPKM.description, Literal(description)))

    for iri in affected_iris:
        g.add((event_iri, SEMPKM.affectedIRI, URIRef(iri)))

    # Data triples (the actual content of the change)
    for s, p, o in data_triples:
        g.add((s, p, o))

    return event_iri, g
```

### Materializing Current State via SPARQL UPDATE
```python
# events/store.py (continued)

async def materialize_create(
    client,  # RDF4J client with active transaction
    current_graph_iri: URIRef,
    data_triples: list[tuple],
) -> None:
    """Insert new triples into the current state graph."""
    # Build INSERT DATA with GRAPH clause
    triples_str = "\n    ".join(
        f"<{s}> <{p}> {_serialize_object(o)} ."
        for s, p, o in data_triples
    )
    sparql = f"""
    INSERT DATA {{
      GRAPH <{current_graph_iri}> {{
        {triples_str}
      }}
    }}
    """
    await client.update(sparql)

async def materialize_patch(
    client,
    current_graph_iri: URIRef,
    subject_iri: URIRef,
    patches: dict,  # {predicate_iri: new_value}
) -> None:
    """Update specific predicates for a subject in current state."""
    for pred_iri, new_value in patches.items():
        sparql = f"""
        DELETE {{
          GRAPH <{current_graph_iri}> {{
            <{subject_iri}> <{pred_iri}> ?old .
          }}
        }}
        INSERT {{
          GRAPH <{current_graph_iri}> {{
            <{subject_iri}> <{pred_iri}> {_serialize_object(new_value)} .
          }}
        }}
        WHERE {{
          OPTIONAL {{
            GRAPH <{current_graph_iri}> {{
              <{subject_iri}> <{pred_iri}> ?old .
            }}
          }}
        }}
        """
        await client.update(sparql)
```

### FastAPI Application Factory with Lifespan
```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.triplestore.setup import ensure_repository

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure RDF4J repository exists
    await ensure_repository(
        base_url=settings.triplestore_url,
        repo_id=settings.repository_id,
    )
    yield
    # Shutdown: cleanup if needed

app = FastAPI(
    title="SemPKM API",
    lifespan=lifespan,
)

# Include routers
from app.commands.router import router as commands_router
from app.sparql.router import router as sparql_router
from app.health.router import router as health_router

app.include_router(commands_router)
app.include_router(sparql_router)
app.include_router(health_router)
```

### JSON-LD Response Serialization
```python
# rdf/jsonld.py
from rdflib import Graph
import json

SEMPKM_CONTEXT = {
    "@context": {
        "sempkm": "urn:sempkm:",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "schema": "https://schema.org/",
        "dcterms": "http://purl.org/dc/terms/",
        "skos": "http://www.w3.org/2004/02/skos/core#",
    }
}

def graph_to_jsonld(graph: Graph) -> dict:
    """Serialize an rdflib Graph to compacted JSON-LD."""
    jsonld_str = graph.serialize(
        format="json-ld",
        context=SEMPKM_CONTEXT["@context"],
    )
    return json.loads(jsonld_str)
```

### Nginx Configuration for Dev Console
```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name localhost;

    # Static files (htmx dev console)
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ =404;
    }

    # Proxy API requests to FastAPI backend
    location /api/ {
        proxy_pass http://api:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Health Check Endpoint
```python
# health/router.py
from fastapi import APIRouter, Depends
from app.dependencies import get_triplestore_client

router = APIRouter(prefix="/api")

@router.get("/health")
async def health_check(client=Depends(get_triplestore_client)):
    triplestore_ok = await client.is_healthy()
    return {
        "status": "healthy" if triplestore_ok else "degraded",
        "services": {
            "api": "up",
            "triplestore": "up" if triplestore_ok else "down",
        },
        "version": "0.1.0",
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| rdflib-jsonld separate package | JSON-LD built into rdflib core | rdflib 6.0 (2021) | No separate install needed; `format='json-ld'` works out of the box |
| SPARQLWrapper for RDF4J communication | rdflib RDF4J Store/Client | rdflib 7.5 (2025) | Native transaction support, repository management, typed results |
| Pydantic v1 discriminated unions (manual) | Pydantic v2 built-in discriminator support | Pydantic 2.0 (2023) | Cleaner syntax via `Field(discriminator=...)`, better error messages |
| RDF4J config vocab `openrdf:` namespace | Unified `tag:rdf4j.org,2023:config/` namespace | RDF4J 4.3 (2023) | New config vocabulary; old `openrdf:` style still supported but deprecated |
| ConjunctiveGraph for named graphs | Dataset class | rdflib 7.x | ConjunctiveGraph deprecated; Dataset is the modern quad-aware interface |
| Blazegraph as triplestore | RDF4J native store | Project decision | Blazegraph unmaintained since 2020; RDF4J actively maintained |
| FastAPI `on_event("startup")` | Lifespan context manager | FastAPI 0.93+ | Deprecated decorator pattern replaced by async context manager |

**Deprecated/outdated:**
- `rdflib-jsonld` package: Fully merged into rdflib core since 6.0; do not install separately
- `ConjunctiveGraph`: Deprecated in rdflib 7.x; use `Dataset` for quad-aware operations
- `FastAPI.on_event("startup"/"shutdown")`: Deprecated; use lifespan context manager
- Blazegraph Docker image (`lyrasis/blazegraph:2.1.5`): Unmaintained since 2020; not suitable for new projects
- RDF4J old config namespace (`http://www.openrdf.org/config/`): Still works but prefer `tag:rdf4j.org,2023:config/`

## Open Questions

1. **rdflib RDF4J Store async support**
   - What we know: rdflib 7.5+ includes RDF4J Store/Client that uses httpx internally. The rdflib docs show synchronous usage patterns.
   - What's unclear: Whether the rdflib RDF4J Store supports async operations natively, or if we need to wrap sync calls in `asyncio.to_thread()` or use the lower-level httpx client directly for async SPARQL UPDATE operations.
   - Recommendation: Start with rdflib's RDF4J Client for repository setup and management. For the hot path (command execution with transactions), test async compatibility. If rdflib's client is sync-only, use httpx async client directly for SPARQL UPDATE operations within transactions, and rdflib for RDF graph construction and serialization.

2. **Event graph IRI scheme and future compaction**
   - What we know: Events need URN-style IRIs (`urn:sempkm:event:{uuid}`). The user wants graph naming designed for future archival/compaction.
   - What's unclear: The exact compaction strategy. Should event IRIs encode timestamps for range-based archival? Should there be a prefix structure that groups events by date?
   - Recommendation: Use `urn:sempkm:event:{uuid}` for v1. UUIDs are sufficient for unique identification. If timestamp-based archival is needed later, the event metadata contains timestamps for filtering. Adding date prefixes to IRIs would complicate minting without clear v1 benefit.

3. **SPARQL query scoping strategy**
   - What we know: Reads must be scoped to the current state graph. The SPARQL proxy can inject `FROM <urn:sempkm:current>`.
   - What's unclear: Whether to inject `FROM` clauses (changes the default graph) or wrap the query body in `GRAPH <urn:sempkm:current> { ... }`. Also whether users should be able to query event graphs directly (for debugging/audit).
   - Recommendation: Inject `FROM <urn:sempkm:current>` by default for the public SPARQL endpoint. This is less intrusive than rewriting the query body. For advanced use, support an optional parameter to query all graphs or specific event graphs. Implementation detail for planning phase.

4. **Edge resource RDF modeling**
   - What we know: Edges are first-class resources with their own IRIs (e.g., `{namespace}/Edge/{uuid}`). They represent relationships between objects.
   - What's unclear: The exact RDF predicates for edge resources. Likely: `sempkm:Edge` type, `sempkm:source`, `sempkm:target`, `sempkm:predicate` (the relationship type). Whether edges should also be materialized as direct triples (e.g., `<alice> <knows> <bob>`) in addition to the edge resource representation.
   - Recommendation: For Phase 1, store edges as `sempkm:Edge` resources with source/target/predicate properties. Defer simple-triple projection to a later phase as the v0.3 spec describes it as optional. Define the edge vocabulary clearly so it can be extended with annotations in later phases.

5. **RDF4J Docker image version pinning**
   - What we know: The semantic-stack reference uses `eclipse/rdf4j-workbench:5.0.1`. The latest available is 5.2.x.
   - What's unclear: Whether to pin to 5.0.1 (known working) or use 5.2.x (latest features, new config vocabulary). The RDF4J protocol version 12 is required by rdflib's RDF4J Store.
   - Recommendation: Use `eclipse/rdf4j-workbench:5.0.1` initially for consistency with the proven semantic-stack setup. Upgrade to 5.2.x can be done later if needed. Verify protocol version 12 compatibility at startup.

## Sources

### Primary (HIGH confidence)
- [RDF4J REST API documentation](https://rdf4j.org/documentation/reference/rest-api/) - REST API endpoints, SPARQL protocol compliance, transaction support
- [RDF4J Repository and SAIL Configuration](https://rdf4j.org/documentation/reference/configuration/) - Native store config parameters, triple indexes, WAL settings, config vocabulary
- [rdflib RDF4J integration docs](https://rdflib.readthedocs.io/en/stable/rdf4j/) - RDF4JStore setup, transaction support, named graph operations, namespace management
- [rdflib PyPI](https://pypi.org/project/rdflib/) - Version 7.6.0, Python 3.8+, built-in JSON-LD support
- [FastAPI official docs](https://fastapi.tiangolo.com/) - Templates, deployment, lifespan
- [Pydantic unions documentation](https://docs.pydantic.dev/latest/concepts/unions/) - Discriminated union syntax for Pydantic v2
- [RDF4J Docker README](https://github.com/eclipse-rdf4j/rdf4j-tools/blob/master/assembly/src/main/dist/docker/README.md) - Docker image ports, volumes, environment variables
- [RDF4J GitHub Discussion #3130](https://github.com/eclipse-rdf4j/rdf4j/discussions/3130) - Programmatic repository creation via REST API PUT

### Secondary (MEDIUM confidence)
- [Docker Compose health checks guide](https://www.tvaidyan.com/2025/02/13/health-checks-in-docker-compose-a-practical-guide/) - depends_on with service_healthy condition
- [GraphDB RDF4J REST API docs](https://graphdb.ontotext.com/documentation/11.1/rdf4j-rest-api.html) - SPARQL query/update endpoint patterns (RDF4J protocol compatible)
- [htmx server-side examples](https://htmx.org/server-examples/) - htmx + FastAPI integration patterns
- [jinja2-fragments](https://github.com/sponsfreixes/jinja2-fragments) - Rendering Jinja2 template blocks as HTML fragments for htmx
- [FastAPI best practices](https://github.com/zhanymkanov/fastapi-best-practices) - Project structure, module organization

### Tertiary (LOW confidence)
- Event sourcing in RDF triplestores is a novel architecture -- no established reference implementations found. The pattern is sound based on named graph semantics but lacks community validation. Benchmarking is recommended during Phase 1 implementation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries are well-established, actively maintained, and have current documentation. Versions verified against PyPI and Docker Hub.
- Architecture: HIGH for individual components, MEDIUM for the event-sourcing-on-named-graphs integration pattern. The individual pieces (RDF4J named graphs, SPARQL UPDATE, FastAPI command dispatch) are well-documented. Their combination for event sourcing is novel but architecturally sound.
- Pitfalls: HIGH - Derived from official documentation (RDF4J named graph behavior, rdflib caveats) and standard engineering concerns (transaction isolation, query scoping). The index configuration pitfall is particularly important and well-supported by RDF4J docs.

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (30 days -- stable ecosystem, no major releases expected)
