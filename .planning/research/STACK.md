# Technology Stack

**Project:** SemPKM
**Researched:** 2026-02-21
**Overall Confidence:** MEDIUM-HIGH (versions verified via PyPI/npm live APIs; ecosystem maturity assessed from training data + verified signals)

---

## Recommended Stack

### Python Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12+ | Runtime | Current stable with best async performance; 3.13 acceptable but 3.12 is the broadest-compatibility sweet spot for Docker images. All key deps require >=3.10 | HIGH (verified: all deps support 3.12) |
| uv | 0.10.x | Package manager + virtualenv | 10-100x faster than pip, replaces pip+pip-tools+venv in one tool, lockfile support, deterministic installs. The standard for new Python projects in 2025/2026 | HIGH (verified: 0.10.4 on PyPI) |

### Core Backend Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| FastAPI | ~0.129 | HTTP API framework | Already decided. Modern async, automatic OpenAPI docs, Pydantic-native validation, excellent for building both REST command API and SPARQL proxy endpoints | HIGH (verified: 0.129.0 on PyPI, requires >=3.10) |
| Pydantic | ~2.12 | Data validation + serialization | FastAPI's native model layer. Use for command API request/response models, Mental Model manifest validation, config. V2 is significantly faster than v1 | HIGH (verified: 2.12.5 on PyPI) |
| uvicorn | ~0.41 | ASGI server | Standard production server for FastAPI. Use with `--workers` for production or behind gunicorn | HIGH (verified: 0.41.0 on PyPI) |
| Jinja2 | ~3.1 | HTML templating | Renders htmx admin shell templates server-side. FastAPI has native Jinja2 support via `Starlette.templating` | HIGH (verified: 3.1.6 on PyPI) |
| python-multipart | ~0.0.22 | Form parsing | Required by FastAPI for file uploads (Mental Model `.sempkm-model` archive upload) | HIGH (verified: 0.0.22 on PyPI) |

### RDF / Semantic Web Core

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| rdflib | ~7.6 | RDF graph manipulation | The Python RDF library. Parses/serializes Turtle, JSON-LD, N-Triples, TriG, RDF/XML natively. Use for: building event graphs, SHACL shape loading, Mental Model ontology parsing, RDF construction before SPARQL INSERT. JSON-LD is built-in since rdflib 6.x (no separate plugin needed) | HIGH (verified: 7.6.0 on PyPI) |
| pySHACL | ~0.31 | SHACL validation | The only production-grade Python SHACL validator. Supports SHACL Core (what SemPKM needs), SHACL Advanced Features, optional OWL-RL inference. Part of the RDFLib ecosystem. Use for async validation of data graphs against Mental Model shapes | HIGH (verified: 0.31.0 on PyPI) |
| SPARQLWrapper | ~2.0 | SPARQL HTTP client | Sends SPARQL queries/updates to the triplestore over HTTP. Mature, well-maintained. Use for all triplestore communication from the FastAPI backend | HIGH (verified: 2.0.0 on PyPI) |
| owlrl | ~7.1 | RDFS/OWL inference | Optional: needed if pySHACL validation requires RDFS or OWL-RL inference expansion. Keep as optional dependency; SemPKM v1 likely only needs it for RDFS subclass inference in SHACL validation | MEDIUM (verified: 7.1.4 on PyPI; need may depend on shape complexity) |

### Triplestore

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **RDF4J** (recommended) | 5.2.2 | SPARQL 1.1 triplestore | Actively maintained (Docker image updated Dec 2025). Full SPARQL 1.1 Query + Update. Named graph support (essential for event sourcing). Supports multiple repository types (in-memory, native, LMDB). Eclipse Foundation backed. Use the `eclipse/rdf4j-workbench` Docker image which includes both the SPARQL server and admin UI | HIGH (verified: 5.2.2 Docker image, pushed 2025-12-16) |
| Blazegraph (fallback) | 2.1.5 | SPARQL 1.1 triplestore | Already in semantic-stack reference. BUT: last Docker image push was 2020-04-02, effectively unmaintained since Systap acquisition by Amazon (Neptune). Still works, still fast for named graphs, but no security patches or bug fixes. Use only if RDF4J has a specific deficiency for the workload | LOW (verified: last update 2020, project abandoned) |

**Decision: Use RDF4J as primary triplestore.** Blazegraph is unmaintained and a liability for a new project. RDF4J provides equivalent SPARQL 1.1 capabilities with active maintenance. The semantic-stack reference already includes RDF4J alongside Blazegraph.

**RDF4J Docker deployment:**
```yaml
services:
  rdf4j:
    image: eclipse/rdf4j-workbench:5.2.2
    ports:
      - "8080:8080"
    volumes:
      - rdf4j_data:/var/rdf4j
```

### Event Sourcing Infrastructure

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| rdflib (Graph construction) | ~7.6 | Build event RDF graphs | Construct event named graphs in Python, serialize to TriG/N-Quads, then INSERT into triplestore via SPARQL UPDATE. No separate event store needed -- events live as named graphs in RDF4J | HIGH |
| SPARQLWrapper (event writes) | ~2.0 | INSERT events into triplestore | SPARQL UPDATE `INSERT DATA { GRAPH <event:xxx> { ... } }` to write event named graphs. SPARQL query to replay/project current state | HIGH |

**No separate event store.** The triplestore IS the event store. Events are RDF named graphs, current state is a materialized graph derived from replaying/projecting events. This is the core architectural decision from the vision doc.

### Supporting Backend Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| PyYAML | ~6.0 | YAML parsing | Mental Model manifest.yaml parsing, view/dashboard spec parsing | HIGH (verified: 6.0.3) |
| httpx | ~0.28 | Async HTTP client | Webhook delivery (outbound HTTP POST), any async HTTP needs. Prefer over `requests` because it supports async natively | HIGH (verified: 0.28.1) |
| aiofiles | ~25.1 | Async file I/O | Mental Model archive extraction, filesystem projection writes | HIGH (verified: 25.1.0) |
| structlog | ~25.5 | Structured logging | JSON-structured logs for all backend services. Better than stdlib logging for debugging RDF/SPARQL issues | HIGH (verified: 25.5.0) |
| watchfiles | ~1.1 | File watching | Dev mode: watch for Mental Model file changes, auto-reload. Optional production use for projection refresh triggers | MEDIUM (verified: 1.1.1) |
| Markdown | ~3.10 | Markdown rendering | Render object body markdown to HTML for the Object Browser. Extensible with custom extensions | HIGH (verified: 3.10.2) |
| typer | ~0.24 | CLI framework | Management CLI for SemPKM: `sempkm init`, `sempkm model install`, `sempkm replay-events`, etc. Built on Click, uses type hints | HIGH (verified: 0.24.0) |
| rich | ~14.3 | Terminal formatting | Pretty CLI output, progress bars for event replay, table formatting for model listing | MEDIUM (verified: 14.3.3) |

### Frontend: Admin Shell (htmx)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| htmx | ~2.0 | Hypermedia interactions | Already decided. Server-rendered HTML with progressive enhancement. Perfect for admin UIs: model management, webhook config, system status. No JS build step needed -- serve from CDN or static files | HIGH (verified: 2.0.8 on npm) |
| Jinja2 | ~3.1 | Server-side templates | (same as backend -- renders the HTML that htmx enhances) | HIGH |
| Alpine.js | ~3.x | Lightweight JS reactivity | Optional companion to htmx for small client-side state (dropdowns, modals, toggles) without React overhead. NOT required but useful for interactive admin widgets | MEDIUM (version not verified; training data says 3.14.x) |

### Frontend: IDE Object Browser (React)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| React | ~19.2 | UI framework | Already decided. React 19 with Server Components not relevant here (SPA embedded in iframe). Use client-side React for the IDE workspace | HIGH (verified: 19.2.4 on npm) |
| TypeScript | ~5.9 | Type safety | Non-negotiable for an IDE-grade UI. Catches RDF/IRI handling bugs, enforces view spec types, enables IDE autocompletion | HIGH (verified: 5.9.3 on npm) |
| Vite | ~7.3 | Build tool + dev server | Fastest dev experience (HMR), tree-shaking, ESM-native. The standard React build tool in 2025/2026 (Create React App is dead) | HIGH (verified: 7.3.1 on npm) |
| Zustand | ~5.0 | State management | Lightweight, no boilerplate, TypeScript-native. Perfect for IDE state: open tabs, active pane, selected object, command palette state. Simpler than Redux, more capable than Context | HIGH (verified: 5.0.11 on npm) |
| TanStack Query | ~5.90 | Server state management | Manages SPARQL query results, caching, refetching, loading states. Separates server state from UI state cleanly. Handles the "data from SPARQL endpoint" concern | HIGH (verified: 5.90.21 on npm) |
| TanStack Table | ~8.21 | Table renderer | Headless table library for the Table view renderer. Sorting, filtering, pagination, column resizing -- all needed for SPARQL SELECT result display | HIGH (verified: 8.21.3 on npm) |
| react-resizable-panels | ~4.6 | IDE pane layout | Resizable split panes for IDE layout (sidebar, main content, inspector). Used by VS Code-inspired UIs | HIGH (verified: 4.6.4 on npm) |
| cmdk | ~1.1 | Command palette | Command-K palette component. Keyboard-first navigation, fuzzy search. Essential for IDE-grade UX | HIGH (verified: 1.1.1 on npm) |
| Tailwind CSS | ~4.2 | Styling | Utility-first CSS. Fast to prototype, consistent design tokens, great for complex IDE layouts. v4 is CSS-native (no PostCSS plugin required) | HIGH (verified: 4.2.0 on npm) |
| Radix UI | ~1.1.x | Accessible UI primitives | Unstyled, accessible components (dialogs, dropdowns, tooltips, tabs). Combine with Tailwind for consistent, accessible IDE chrome | HIGH (verified: @radix-ui/react-dialog 1.1.15) |

### Frontend: Graph Visualization

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Cytoscape.js | ~3.33 | 2D graph rendering (primary) | Most mature graph visualization library. Supports custom node/edge styling by type, multiple layout algorithms (force-directed, hierarchical, concentric), event handling, plugins. Well-suited for RDF graph visualization where nodes are typed objects and edges are typed predicates | HIGH (verified: 3.33.1 on npm) |
| react-force-graph-2d | ~1.29 | 2D graph rendering (alternative) | WebGL-based, handles large graphs better than Cytoscape SVG rendering. Consider if graph sizes exceed ~1000 nodes. Simpler API but less customizable styling | MEDIUM (verified: 1.29.1 on npm) |

**Decision: Use Cytoscape.js for v1 graph visualization.** It has the richest styling API (needed for type-based node/edge rendering), best layout algorithm selection, and deepest plugin ecosystem. Switch to react-force-graph-2d only if performance becomes an issue with large graphs.

### Frontend: SPARQL/Code Editing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| CodeMirror 6 | ~6.39 | SPARQL query editor | Mature, extensible code editor. Has community SPARQL mode. Needed for the SPARQL view spec editor and ad-hoc query panel. v6 is the current major version (v5 is legacy) | HIGH (verified: @codemirror/view 6.39.15) |

### Infrastructure / DevOps

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Docker | latest | Container runtime | Runs RDF4J triplestore, SemPKM backend, and development environment | HIGH |
| Docker Compose | v2 | Multi-container orchestration | Defines the full stack: RDF4J + SemPKM backend + (optional) dev tools | HIGH |
| uv | ~0.10 | Python dependency management | Replaces pip, pip-tools, venv. Use `uv.lock` for deterministic installs. Use `uv run` for script execution | HIGH (verified: 0.10.4) |

### Development / Quality

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ruff | ~0.15 | Python linter + formatter | Replaces flake8 + black + isort in one tool. 10-100x faster. The standard Python linter in 2025/2026 | HIGH (verified: 0.15.2) |
| mypy | ~1.19 | Python type checker | Static type checking for the backend. Essential for catching RDF/IRI type confusion bugs | HIGH (verified: 1.19.1) |
| pytest | ~9.0 | Python test framework | Standard. Use with pytest-asyncio for async FastAPI tests and pytest-cov for coverage | HIGH (verified: 9.0.2) |
| pytest-asyncio | ~1.3 | Async test support | Tests FastAPI endpoints and async SPARQL operations | HIGH (verified: 1.3.0) |
| pytest-cov | ~7.0 | Test coverage | Coverage reporting for CI | HIGH (verified: 7.0.0) |
| pre-commit | ~4.5 | Git hooks | Run ruff + mypy on commit. Catch issues before CI | HIGH (verified: 4.5.1) |
| Vitest | latest | Frontend test framework | Jest-compatible but Vite-native. Tests React components and SPARQL result transformations | HIGH (training data; standard for Vite projects) |
| Playwright | latest | E2E testing | Browser-based testing for htmx admin + React IDE. Needed for testing iframe embedding and cross-frame communication | MEDIUM (training data) |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Triplestore | RDF4J 5.2.2 | Blazegraph 2.1.5 | Unmaintained since 2020; no security patches; Docker image last updated Apr 2020. RDF4J is actively maintained by Eclipse Foundation |
| Triplestore | RDF4J 5.2.2 | Oxigraph (embedded) | Oxigraph (0.5.5) is promising as an embedded Rust triplestore with Python bindings, but it is pre-1.0, has smaller community, and the project explicitly states it is not production-ready yet. Good future option for embedded/portable deployment |
| Triplestore | RDF4J 5.2.2 | Apache Jena Fuseki | Java-based like RDF4J but heavier, more complex configuration. RDF4J is simpler to deploy via Docker and has a cleaner REST API |
| RDF library | rdflib 7.6 | Apache Jena (via Py4J) | Crossing the JVM boundary adds complexity. rdflib is native Python, well-maintained, and sufficient for graph construction/serialization |
| SHACL validator | pySHACL 0.31 | TopBraid SHACL (Java) | JVM dependency. pySHACL is Python-native, RDFLib ecosystem, supports SHACL Core which is all SemPKM v1 needs |
| Package manager | uv | poetry | Poetry is slower, has dependency resolution issues at scale, and is being superseded by uv in the Python ecosystem |
| Package manager | uv | pip + pip-tools | Slower, no integrated venv management, no lockfile format standardization |
| State management | Zustand | Redux Toolkit | Overkill for this use case. Zustand is simpler, less boilerplate, equally performant |
| State management | Zustand | Jotai | Atomic state model is harder to reason about for IDE-style state (many interdependent pieces) |
| Graph viz | Cytoscape.js | D3.js | D3 is lower-level, requires more code for graph visualization. Cytoscape provides graph-specific abstractions (nodes, edges, layouts) out of the box |
| Graph viz | Cytoscape.js | Sigma.js (3.0) | Sigma excels at very large graphs (10K+ nodes) via WebGL. Overkill for PKM-scale graphs. Less flexible styling than Cytoscape |
| Build tool | Vite 7 | Webpack | Webpack is legacy. Vite is faster, simpler config, better DX |
| CSS | Tailwind CSS 4 | CSS Modules | Tailwind is faster to iterate with, has better design system consistency, and v4 requires zero config |
| Async HTTP | httpx | aiohttp | httpx has a cleaner API, supports both sync and async, better maintained |
| YAML parsing | PyYAML | ruamel.yaml | ruamel.yaml preserves comments (useful for editing YAML) but SemPKM only reads YAML manifests, does not edit them. PyYAML is simpler and faster for read-only use |
| Markdown | Python-Markdown | mistune | Python-Markdown has richer extension ecosystem. mistune is faster but less extensible. For PKM body rendering, extensibility (custom link handling, RDF-aware extensions) matters more |
| CLI | typer | click | typer is built on click but uses type hints for argument definitions, reducing boilerplate. Functionally equivalent but better DX |
| Frontend framework | React (IDE) + htmx (admin) | React for everything | htmx is dramatically simpler for server-rendered admin pages. Using React for model management forms would be overengineering |
| Frontend framework | React (IDE) + htmx (admin) | htmx for everything | htmx cannot deliver IDE-grade interactivity (resizable panes, command palette, complex graph viz, drag-and-drop). React is necessary for the Object Browser |

---

## Stack Architecture Summary

```
+--------------------------------------------------+
|                    Browser                        |
|  +--------------------------------------------+  |
|  |  htmx Admin Shell (server-rendered)        |  |
|  |  - Model management                        |  |
|  |  - Webhook config                          |  |
|  |  - System status                           |  |
|  +--------------------------------------------+  |
|  |  React IDE Object Browser (iframe)         |  |
|  |  - Resizable panes (react-resizable-panels)|  |
|  |  - SPARQL editor (CodeMirror 6)            |  |
|  |  - Graph viz (Cytoscape.js)                |  |
|  |  - Tables (TanStack Table)                 |  |
|  |  - Command palette (cmdk)                  |  |
|  |  - State: Zustand + TanStack Query         |  |
|  +--------------------------------------------+  |
+--------------------------------------------------+
                        |
                   HTTP / JSON
                        |
+--------------------------------------------------+
|  FastAPI Backend (Python 3.12+, uvicorn)          |
|  +--------------------------------------------+  |
|  |  Command API    | SPARQL Proxy | Admin API  |  |
|  +--------------------------------------------+  |
|  |  Event Sourcing Engine (rdflib graph build) |  |
|  |  SHACL Validator (pySHACL, async)           |  |
|  |  Mental Model Manager (YAML, ZIP, rdflib)   |  |
|  |  Webhook Dispatcher (httpx async)           |  |
|  |  Projection Service (aiofiles)              |  |
|  +--------------------------------------------+  |
+--------------------------------------------------+
                        |
              SPARQL 1.1 over HTTP
                        |
+--------------------------------------------------+
|  RDF4J 5.2.2 (Docker)                            |
|  - Named graphs (event store)                     |
|  - Current state graph (materialized projection)  |
|  - SPARQL 1.1 Query + Update                      |
+--------------------------------------------------+
```

---

## Installation

### Backend

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project
uv init sempkm --python 3.12
cd sempkm

# Core dependencies
uv add fastapi uvicorn[standard] pydantic
uv add rdflib pyshacl SPARQLWrapper
uv add jinja2 python-multipart pyyaml
uv add httpx aiofiles structlog markdown
uv add typer rich

# Dev dependencies
uv add --dev ruff mypy pytest pytest-asyncio pytest-cov
uv add --dev pre-commit httpx  # httpx also used for test client
```

### Frontend (React IDE)

```bash
cd frontend
npm create vite@latest ide -- --template react-ts
cd ide

# Core
npm install react react-dom
npm install zustand @tanstack/react-query @tanstack/react-table
npm install react-resizable-panels cmdk
npm install cytoscape
npm install @codemirror/view @codemirror/state @codemirror/lang-sql  # SPARQL mode via SQL base
npm install tailwindcss @tailwindcss/vite

# UI primitives
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu
npm install @radix-ui/react-tabs @radix-ui/react-tooltip
npm install @radix-ui/react-popover

# Dev
npm install -D typescript @types/react @types/react-dom
npm install -D vitest @testing-library/react
npm install -D @types/cytoscape
```

### Infrastructure

```bash
# Docker Compose for triplestore
cat > docker-compose.yml << 'EOF'
services:
  rdf4j:
    image: eclipse/rdf4j-workbench:5.2.2
    container_name: sempkm-rdf4j
    ports:
      - "8080:8080"
    volumes:
      - rdf4j_data:/var/rdf4j
    restart: unless-stopped

volumes:
  rdf4j_data:
EOF
```

---

## Version Pinning Strategy

Use **compatible release** (`~=`) pinning in `pyproject.toml` for Python deps:
- `rdflib~=7.6` -- allows 7.6.x patches but not 7.7
- `fastapi~=0.129` -- allows 0.129.x but not 0.130
- `pyshacl~=0.31` -- allows 0.31.x but not 0.32

Use **caret** (`^`) in `package.json` for npm deps (default npm behavior):
- `"react": "^19.2.0"` -- allows 19.x.x but not 20.0.0
- `"cytoscape": "^3.33.0"` -- allows 3.x.x

Lock exact versions in `uv.lock` and `package-lock.json` for reproducible builds.

---

## Key Integration Notes

### rdflib + RDF4J Communication Pattern
```python
# Build RDF graph in Python
from rdflib import Graph, URIRef, Literal, Namespace
from SPARQLWrapper import SPARQLWrapper

g = Graph(identifier=URIRef("urn:sempkm:event:123"))
# ... add triples to graph ...

# Serialize to N-Quads for SPARQL INSERT
nquads = g.serialize(format="nquads")

# Insert into RDF4J via SPARQL UPDATE
sparql = SPARQLWrapper("http://localhost:8080/rdf4j-server/repositories/sempkm/statements")
sparql.setQuery(f"INSERT DATA {{ {nquads} }}")
sparql.method = "POST"
sparql.query()
```

### pySHACL Async Validation Pattern
```python
import asyncio
from pyshacl import validate
from rdflib import Graph

async def validate_async(data_graph: Graph, shapes_graph: Graph):
    """Run SHACL validation in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    conforms, results_graph, results_text = await loop.run_in_executor(
        None,  # default thread pool
        lambda: validate(
            data_graph,
            shacl_graph=shapes_graph,
            inference='none',  # or 'rdfs' if needed
            abort_on_first=False,
        )
    )
    return conforms, results_graph, results_text
```

### htmx + FastAPI Integration
```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/admin/models")
async def list_models(request: Request):
    # htmx partial vs full page
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("partials/model_list.html", {"request": request, "models": models})
    return templates.TemplateResponse("admin/models.html", {"request": request, "models": models})
```

---

## Sources

All versions verified against live package registries on 2026-02-21:

- **PyPI JSON API** (`https://pypi.org/pypi/{package}/json`): rdflib 7.6.0, FastAPI 0.129.0, pySHACL 0.31.0, SPARQLWrapper 2.0.0, Pydantic 2.12.5, uvicorn 0.41.0, httpx 0.28.1, Jinja2 3.1.6, PyYAML 6.0.3, structlog 25.5.0, aiofiles 25.1.0, typer 0.24.0, rich 14.3.3, Markdown 3.10.2, watchfiles 1.1.1, owlrl 7.1.4, pytest 9.0.2, pytest-asyncio 1.3.0, pytest-cov 7.0.0, ruff 0.15.2, mypy 1.19.1, pre-commit 4.5.1, uv 0.10.4, oxigraph 0.5.5, oxrdflib 0.5.0, pyld 2.0.4
- **npm registry** (`https://registry.npmjs.org/{package}/latest`): htmx 2.0.8, React 19.2.4, Vite 7.3.1, TypeScript 5.9.3, Zustand 5.0.11, TanStack Query 5.90.21, TanStack Table 8.21.3, react-resizable-panels 4.6.4, cmdk 1.1.1, Cytoscape.js 3.33.1, CodeMirror 6.39.15, Tailwind CSS 4.2.0, Radix UI Dialog 1.1.15, react-force-graph-2d 1.29.1, D3 7.9.0, Sigma.js 3.0.2
- **Docker Hub API**: RDF4J Workbench 5.2.2 (last pushed 2025-12-16), Blazegraph 2.1.5 (last pushed 2020-04-02)
- **Local reference**: `semantic-stack` project at `/home/james/Code/semantic-stack/docker-compose.yml`
- **Project specs**: SemPKM vision doc, PROJECT.md, API overview, event types spec, decision log v0.3
