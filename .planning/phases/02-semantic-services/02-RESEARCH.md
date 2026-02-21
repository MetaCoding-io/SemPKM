# Phase 2: Semantic Services - Research

**Researched:** 2026-02-21
**Domain:** IRI label resolution, prefix registries, SHACL validation (async), RDF service layer
**Confidence:** HIGH

## Summary

Phase 2 introduces three backend service layers that sit between the Phase 1 event-sourced triplestore and the downstream UI phases (4, 5): a label resolution service, a prefix registry, and an asynchronous SHACL validation engine. All three consume data from RDF4J via SPARQL and expose internal APIs that later phases call.

The standard stack is pyshacl (0.31.0) for SHACL validation, cachetools (7.0.1) for label caching, and asyncio.Queue for sequential background validation. pyshacl is the only mature, actively maintained Python SHACL validator -- it is part of the RDFLib organization, supports all SHACL Core Constraint Components, returns W3C-compliant validation reports as rdflib Graph objects, and works with in-memory rdflib graphs directly. RDF4J has built-in SHACL via ShaclSail, but it validates synchronously on commit (blocking the write path), which violates the user decision for non-blocking async validation. The pyshacl approach also avoids reconfiguring the triplestore's Sail stack.

**Primary recommendation:** Use pyshacl with in-process asyncio.Queue for sequential validation, fetch data from RDF4J via SPARQL CONSTRUCT into rdflib Graphs, store validation reports as named graphs back in RDF4J.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **IRI display fallback**: Primary fallback when no label found: QName format (prefix:localName). When prefix is unknown: truncated IRI (.../localName) with full IRI in tooltip. Label service must support configurable language preference. Display pattern: label only in UI surfaces, with QName shown on hover/tooltip for power users. Label precedence chain: dcterms:title > rdfs:label > skos:prefLabel > schema:name > QName fallback > truncated IRI fallback.
- **Prefix registry defaults**: Built-in prefix set: core + common vocabs (~10-12 prefixes: rdf, rdfs, owl, xsd, sh, skos, dcterms, schema, foaf, prov, etc.). LOV (Linked Open Vocabularies) integration: one-time import from LOV REST API to add vocabulary prefixes to the registry, plus a CLI command for re-syncing. Layer precedence: User overrides > Model-provided > Built-in. Registry supports both directions: forward lookup (prefix -> namespace) and reverse lookup (namespace -> prefix).
- **Validation report detail**: Three severity tiers: Violation, Warning, Info. Per-property detail: each result includes object IRI + property path + constraint + failing value + human message. Human messages: use sh:message from the shape when provided, otherwise auto-generate a fallback message. Storage: summary + full report.
- **Validation trigger & feel**: Trigger: every command (each object.create, object.patch, body.set, edge.create, edge.patch triggers validation immediately after commit). Scope: full re-validation of all objects against all shapes after each commit. UI notification: polling endpoint (GET /api/validation/latest or similar). Concurrency: queue and run sequentially -- if validation is running when the next commit arrives, new validation queues behind it. Every commit gets its own immutable report.

### Claude's Discretion
- Exact caching strategy for label resolution (TTL, invalidation approach)
- Internal batch resolution API design
- SHACL validation engine implementation (in-process vs subprocess, library choice)
- Auto-generated message templates and formatting
- LOV API integration details (endpoints, caching of LOV responses)
- Polling endpoint response format and timing

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFR-01 | System resolves IRIs to human-readable labels using the label precedence chain (dcterms:title > rdfs:label > skos:prefLabel > schema:name > IRI fallback) | Label service with SPARQL CONSTRUCT batch query using COALESCE for precedence, cachetools TTLCache for caching, language preference filtering via FILTER(LANG()) |
| INFR-02 | System provides a prefix registry merging model-provided, user-override, and built-in prefix mappings for QName rendering across the UI | Three-layer prefix registry (built-in dict + model graph + user overrides in named graph), LOV REST API for one-time vocabulary import, bidirectional lookup via Python dict + reverse dict |
| SHCL-01 | System runs SHACL validation asynchronously after each commit (non-blocking UI) | pyshacl 0.31.0 validate() called via asyncio.to_thread() inside asyncio.Queue worker, triggered after EventStore.commit() returns, no blocking of HTTP response |
| SHCL-05 | System persists immutable SHACL validation reports tied to each commit as named graphs | Validation report stored as named graph (urn:sempkm:validation:{event-uuid}) via SPARQL INSERT DATA, linked to event IRI, plus summary triples for fast polling |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyshacl | 0.31.0 | SHACL validation engine | Only mature Python SHACL validator; part of RDFLib org; supports all SHACL Core Constraint Components; returns W3C-compliant validation reports as rdflib Graph objects |
| cachetools | 7.0.1 | In-memory TTL cache for label resolution | Lightweight, well-maintained, TTLCache with per-item expiry; no external dependencies; 7.0.1 released Feb 2026 |
| rdflib | >=7.5.0 (existing) | RDF graph manipulation, SPARQL parsing, serialization | Already in project; pyshacl depends on rdflib >=7.1.1; needed for CONSTRUCT result parsing and validation report manipulation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | >=0.28 (existing) | HTTP client for LOV API calls and triplestore | Already in project; used for LOV REST API integration |
| asyncio (stdlib) | N/A | Queue + worker for async validation | asyncio.Queue for FIFO sequential validation; asyncio.to_thread() for CPU-bound pyshacl offload |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pyshacl (in-process) | RDF4J ShaclSail | ShaclSail validates synchronously on commit (blocks writes); would require changing repo config from NativeStore to ShaclSail wrapping NativeStore; no async option. User decision explicitly requires non-blocking validation. |
| pyshacl (in-process) | pyshacl subprocess | Extra process overhead, serialization cost to pass graphs; in-process with asyncio.to_thread() is simpler and sufficient for single-user app |
| cachetools | Python stdlib functools.lru_cache | lru_cache lacks TTL expiry; labels can become stale after edits. TTLCache auto-expires entries. |
| cachetools | Redis | Over-engineering for single-user in-process caching; adds infrastructure dependency |

**Installation:**
```bash
pip install pyshacl>=0.31.0 cachetools>=7.0
```

Add to `backend/pyproject.toml` dependencies:
```toml
dependencies = [
    # ... existing ...
    "pyshacl>=0.31.0",
    "cachetools>=7.0",
]
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── commands/           # (existing) Command handlers
├── events/             # (existing) Event store
├── health/             # (existing) Health endpoint
├── rdf/                # (existing) Namespace, IRI minting
├── sparql/             # (existing) SPARQL query endpoint
├── triplestore/        # (existing) RDF4J client
├── services/           # NEW: Phase 2 service layer
│   ├── __init__.py
│   ├── labels.py       # LabelService: resolve IRIs to human-readable labels
│   ├── prefixes.py     # PrefixRegistry: manage prefix<->namespace mappings
│   └── validation.py   # ValidationService: async SHACL validation engine
└── validation/         # NEW: Validation infrastructure
    ├── __init__.py
    ├── queue.py         # AsyncValidationQueue: asyncio.Queue + worker
    ├── report.py        # ValidationReport: parse/store/query reports
    └── router.py        # GET /api/validation/latest, GET /api/validation/{event_iri}
```

### Pattern 1: Label Resolution with SPARQL COALESCE + TTLCache

**What:** Batch-resolve IRI labels using a single SPARQL query with COALESCE for precedence chain, cache results with TTL.

**When to use:** Every time the UI needs to display human-readable names for IRIs (all downstream phases).

**Example:**
```python
# Source: W3C SPARQL 1.1 COALESCE + pyshacl docs + cachetools docs
from cachetools import TTLCache
from rdflib import URIRef

class LabelService:
    """Resolve IRIs to human-readable labels with precedence chain and caching."""

    def __init__(self, triplestore_client, prefix_registry, ttl: int = 300, maxsize: int = 4096):
        self._client = triplestore_client
        self._prefixes = prefix_registry
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._language_prefs = ["en"]  # configurable

    async def resolve(self, iri: str) -> str:
        """Resolve a single IRI to its best label."""
        if iri in self._cache:
            return self._cache[iri]
        labels = await self.resolve_batch([iri])
        return labels.get(iri, self._iri_fallback(iri))

    async def resolve_batch(self, iris: list[str]) -> dict[str, str]:
        """Resolve multiple IRIs in a single SPARQL query."""
        # Check cache first, collect misses
        results = {}
        misses = []
        for iri in iris:
            if iri in self._cache:
                results[iri] = self._cache[iri]
            else:
                misses.append(iri)

        if not misses:
            return results

        # Build VALUES-based SPARQL query with COALESCE
        values_clause = " ".join(f"(<{iri}>)" for iri in misses)
        lang_filter = self._build_lang_filter()
        query = f"""
        SELECT ?iri ?label WHERE {{
          VALUES (?iri) {{ {values_clause} }}
          OPTIONAL {{ ?iri dcterms:title ?t . {lang_filter("?t")} }}
          OPTIONAL {{ ?iri rdfs:label ?r . {lang_filter("?r")} }}
          OPTIONAL {{ ?iri skos:prefLabel ?s . {lang_filter("?s")} }}
          OPTIONAL {{ ?iri schema:name ?n . {lang_filter("?n")} }}
          BIND(COALESCE(?t, ?r, ?s, ?n) AS ?label)
        }}
        """
        sparql_results = await self._client.query(query)
        for binding in sparql_results["results"]["bindings"]:
            iri_val = binding["iri"]["value"]
            if "label" in binding:
                label = binding["label"]["value"]
                self._cache[iri_val] = label
                results[iri_val] = label
            else:
                fallback = self._iri_fallback(iri_val)
                self._cache[iri_val] = fallback
                results[iri_val] = fallback

        return results

    def _iri_fallback(self, iri: str) -> str:
        """QName fallback, then truncated IRI fallback."""
        qname = self._prefixes.compact(iri)
        if qname != iri:  # prefix found
            return qname
        # Truncated IRI: .../localName
        local = iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        return f".../{local}" if local else iri

    def invalidate(self, iris: list[str]) -> None:
        """Invalidate cache entries after writes."""
        for iri in iris:
            self._cache.pop(iri, None)
```

### Pattern 2: Three-Layer Prefix Registry

**What:** Prefix registry with three layers: built-in (hardcoded), model-provided (from installed Mental Model graphs), user-override (persisted in a named graph). Lookup respects precedence: user > model > built-in.

**When to use:** Every IRI-to-QName compaction and every QName-to-IRI expansion across the system.

**Example:**
```python
# Source: Project architecture + LOV API docs
from typing import Optional

class PrefixRegistry:
    """Three-layer prefix registry with bidirectional lookup."""

    BUILTIN: dict[str, str] = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "sh": "http://www.w3.org/ns/shacl#",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "dcterms": "http://purl.org/dc/terms/",
        "schema": "https://schema.org/",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "prov": "http://www.w3.org/ns/prov#",
        "sempkm": "urn:sempkm:",
    }

    def __init__(self):
        self._model_prefixes: dict[str, str] = {}
        self._user_prefixes: dict[str, str] = {}
        # Reverse maps (namespace -> prefix) built on demand
        self._reverse_cache: Optional[dict[str, str]] = None

    def expand(self, qname: str) -> Optional[str]:
        """Expand prefix:localName to full IRI."""
        if ":" not in qname:
            return None
        prefix, local = qname.split(":", 1)
        ns = self._lookup_prefix(prefix)
        return f"{ns}{local}" if ns else None

    def compact(self, iri: str) -> str:
        """Compact full IRI to prefix:localName. Returns IRI if no prefix matches."""
        reverse = self._get_reverse_map()
        # Find longest matching namespace
        best_prefix = None
        best_ns_len = 0
        for ns, prefix in reverse.items():
            if iri.startswith(ns) and len(ns) > best_ns_len:
                best_prefix = prefix
                best_ns_len = len(ns)
        if best_prefix:
            return f"{best_prefix}:{iri[best_ns_len:]}"
        return iri

    def _lookup_prefix(self, prefix: str) -> Optional[str]:
        """Look up namespace by prefix. User > Model > Built-in."""
        return (
            self._user_prefixes.get(prefix)
            or self._model_prefixes.get(prefix)
            or self.BUILTIN.get(prefix)
        )
```

### Pattern 3: Async Validation Queue with Sequential Processing

**What:** asyncio.Queue-based worker that processes validation jobs one at a time in FIFO order, triggered after every EventStore.commit(). Uses asyncio.to_thread() to offload CPU-bound pyshacl work.

**When to use:** After every command commit. The command endpoint returns immediately; validation runs in background.

**Example:**
```python
# Source: FastAPI FIFO queue pattern + pyshacl docs
import asyncio
import logging
from dataclasses import dataclass

import pyshacl
from rdflib import Graph

logger = logging.getLogger(__name__)

@dataclass
class ValidationJob:
    event_iri: str
    timestamp: str

class AsyncValidationQueue:
    """Sequential async validation queue."""

    def __init__(self, triplestore_client, shapes_loader):
        self._queue: asyncio.Queue[ValidationJob] = asyncio.Queue()
        self._client = triplestore_client
        self._shapes_loader = shapes_loader
        self._task: asyncio.Task | None = None
        self._latest_report: dict | None = None

    async def start(self):
        """Start the worker (call during app lifespan startup)."""
        self._task = asyncio.create_task(self._worker())

    async def stop(self):
        """Stop the worker (call during app lifespan shutdown)."""
        if self._task:
            self._task.cancel()

    async def enqueue(self, event_iri: str, timestamp: str):
        """Enqueue a validation job (non-blocking)."""
        await self._queue.put(ValidationJob(event_iri=event_iri, timestamp=timestamp))

    async def _worker(self):
        """Process validation jobs sequentially."""
        while True:
            job = await self._queue.get()
            try:
                await self._validate(job)
            except Exception:
                logger.exception("Validation failed for event %s", job.event_iri)
            finally:
                self._queue.task_done()

    async def _validate(self, job: ValidationJob):
        """Fetch data, run pyshacl, store report."""
        # 1. Fetch current state as rdflib Graph via CONSTRUCT
        data_graph = await self._fetch_current_graph()
        # 2. Load SHACL shapes
        shapes_graph = await self._shapes_loader()
        # 3. Run pyshacl in thread (CPU-bound)
        conforms, report_graph, report_text = await asyncio.to_thread(
            pyshacl.validate,
            data_graph,
            shacl_graph=shapes_graph,
            allow_infos=True,
            allow_warnings=True,
        )
        # 4. Store report as named graph
        await self._store_report(job, conforms, report_graph, report_text)
```

### Pattern 4: SPARQL CONSTRUCT for Data Fetching

**What:** Extend TriplestoreClient with a `construct()` method that returns raw Turtle/N-Triples, parseable by rdflib.

**When to use:** Fetching the entire current state graph for validation, or fetching specific subgraphs.

**Example:**
```python
# Source: RDF4J REST API docs
# Add to TriplestoreClient:

async def construct(self, sparql: str) -> bytes:
    """Execute a SPARQL CONSTRUCT and return raw Turtle bytes."""
    resp = await self._client.post(
        self._repo_url,
        data={"query": sparql},
        headers={"Accept": "text/turtle"},
    )
    resp.raise_for_status()
    return resp.content

# Usage in validation:
async def _fetch_current_graph(self) -> Graph:
    """Fetch entire current state graph as rdflib Graph."""
    turtle_bytes = await self._client.construct(
        "CONSTRUCT { ?s ?p ?o } FROM <urn:sempkm:current> WHERE { ?s ?p ?o }"
    )
    g = Graph()
    g.parse(data=turtle_bytes, format="turtle")
    return g
```

### Pattern 5: Validation Report Storage as Named Graph

**What:** Store each validation report as an immutable named graph tied to its event IRI. Store a lightweight summary alongside the full report for fast polling.

**When to use:** After every validation run completes.

**Example:**
```python
# Named graph IRI pattern: urn:sempkm:validation:{event-uuid}
# Extract event UUID from event IRI: urn:sempkm:event:{uuid}
# Validation graph: urn:sempkm:validation:{uuid}

# Summary triples (stored in urn:sempkm:validations named graph):
# <urn:sempkm:validation:{uuid}> a sempkm:ValidationReport .
# <urn:sempkm:validation:{uuid}> sempkm:forEvent <urn:sempkm:event:{uuid}> .
# <urn:sempkm:validation:{uuid}> sempkm:conforms true/false .
# <urn:sempkm:validation:{uuid}> sempkm:violationCount 3 .
# <urn:sempkm:validation:{uuid}> sempkm:warningCount 1 .
# <urn:sempkm:validation:{uuid}> sempkm:infoCount 0 .
# <urn:sempkm:validation:{uuid}> sempkm:timestamp "2026-02-21T..." .

# Full report: the pyshacl report_graph serialized into
# named graph urn:sempkm:validation:{uuid}
```

### Anti-Patterns to Avoid
- **Synchronous validation in the command handler:** Violates the user decision for non-blocking writes. Validation MUST happen after the HTTP response returns.
- **Global mutable prefix dict without thread safety:** The prefix registry will be read from async contexts; use immutable snapshots or proper locking if mutating.
- **Fetching labels one-at-a-time:** Always batch label resolution. Single-IRI SPARQL queries per label create N+1 query problems.
- **Storing validation reports as JSON blobs:** Reports are RDF (W3C SHACL spec). Store them as named graphs in the triplestore for queryability.
- **Using RDF4J ShaclSail for this use case:** It validates synchronously on commit and would block writes. The user explicitly chose async non-blocking validation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SHACL validation | Custom constraint checker | pyshacl 0.31.0 | SHACL spec is 100+ pages; pyshacl implements all Core Constraint Components, produces W3C-compliant reports, handles severity, sh:message, property paths |
| Label precedence chain | Custom RDF property walker | SPARQL COALESCE in a single query | COALESCE handles the precedence natively in SPARQL; no application-level logic needed |
| TTL caching | Custom dict with timestamps | cachetools.TTLCache | Handles eviction, TTL per item, maxsize bounds, thread-safe reads |
| SHACL report parsing | Custom Turtle parser | rdflib Graph.parse() | rdflib already parses the report graph from pyshacl; query with SPARQL or iterate triples |
| Prefix vocabulary discovery | Scraping vocab sites | LOV REST API | LOV catalogs 550+ vocabularies with prefix/namespace; simple JSON API |

**Key insight:** SHACL validation is an entire W3C specification with complex constraint interactions (logical operators, qualified cardinality, property paths, SPARQL-based constraints). Attempting to hand-roll even a subset would be a multi-month effort with inevitable spec compliance gaps.

## Common Pitfalls

### Pitfall 1: CONSTRUCT Results Not Scoped to Current Graph
**What goes wrong:** CONSTRUCT queries without explicit FROM clause return triples from all named graphs (including event graphs), causing validation to run against historical data mixed with current state.
**Why it happens:** The existing `scope_to_current_graph()` utility injects FROM before WHERE, but a validation CONSTRUCT must explicitly use `FROM <urn:sempkm:current>`.
**How to avoid:** Always use `CONSTRUCT { ?s ?p ?o } FROM <urn:sempkm:current> WHERE { ?s ?p ?o }` when fetching data for validation.
**Warning signs:** Validation finds violations on deleted/patched data that no longer exists in current state.

### Pitfall 2: pyshacl is CPU-Bound and Blocks the Event Loop
**What goes wrong:** Calling `pyshacl.validate()` directly in an async function blocks the entire FastAPI event loop, making all other requests hang during validation.
**Why it happens:** pyshacl is pure Python, CPU-bound graph processing. Python's GIL prevents true parallelism with threads for CPU work, but asyncio.to_thread() at least yields back to the event loop between GIL releases (rdflib does release the GIL in some C extensions).
**How to avoid:** Use `asyncio.to_thread(pyshacl.validate, ...)` to offload to a thread. For very large graphs, consider `loop.run_in_executor(ProcessPoolExecutor(), ...)` but this requires pickling the graphs.
**Warning signs:** Health check endpoint becomes unresponsive during validation; command responses take 10+ seconds.

### Pitfall 3: Cache Invalidation After Writes
**What goes wrong:** Label cache serves stale labels after object.patch changes a dcterms:title. User sees old label until TTL expires.
**Why it happens:** Cache TTL alone is not sufficient for write-your-own-read consistency.
**How to avoid:** Explicitly invalidate affected IRIs from the cache after each commit. The EventResult already contains `affected_iris` -- pass these to `LabelService.invalidate()`.
**Warning signs:** Label changes don't appear until cache TTL expires (e.g., 5 minutes later).

### Pitfall 4: Validation Queue Grows Unbounded During Rapid Edits
**What goes wrong:** User makes 20 rapid edits; 20 full re-validations queue up and run sequentially, each taking seconds. System appears to "lag behind" indefinitely.
**Why it happens:** User decision says "every command triggers validation" with "full re-validation."
**How to avoid:** Consider a debounce/coalesce strategy: if multiple jobs are queued, only the latest matters (since it's full re-validation, earlier results will be superseded). Drain the queue and process only the last job. Alternatively, set a maximum queue depth and drop intermediate jobs.
**Warning signs:** Queue size grows monotonically; validation results are always many commits behind current state.

### Pitfall 5: LOV API Unavailability
**What goes wrong:** LOV API (lov.linkeddata.es) is a community service with no SLA. If it's down during prefix import, the CLI command fails.
**Why it happens:** External dependency on a free community service.
**How to avoid:** Cache the LOV vocabulary list locally after first successful fetch. Make the CLI command idempotent -- skip already-imported prefixes. Provide a timeout and graceful error message.
**Warning signs:** LOV import hangs or returns HTTP 500. The service has had historical downtime.

### Pitfall 6: Language Preference Filtering Drops All Labels
**What goes wrong:** SPARQL FILTER(LANG(?label) = "en") drops labels that have no language tag at all (plain literals).
**Why it happens:** In RDF, a plain literal like `"My Title"` has LANG() = "" (empty string), not "en".
**How to avoid:** Use `FILTER(!BOUND(?label) || LANG(?label) = "" || LANG(?label) = "en")` to accept both untagged and language-matched literals. Or use a two-step approach: prefer language-tagged, fall back to untagged.
**Warning signs:** IRIs with plain-literal labels show QName fallback instead of the actual label.

## Code Examples

Verified patterns from official sources:

### pyshacl.validate() with In-Memory Graphs
```python
# Source: https://github.com/RDFLib/pySHACL README
from pyshacl import validate
from rdflib import Graph

data_graph = Graph()
data_graph.parse(data=turtle_bytes, format="turtle")

shapes_graph = Graph()
shapes_graph.parse(data=shapes_turtle, format="turtle")

conforms, results_graph, results_text = validate(
    data_graph,
    shacl_graph=shapes_graph,
    allow_infos=True,       # Info severity doesn't fail validation
    allow_warnings=True,    # Warning severity doesn't fail validation
    # abort_on_first=False  # default: validate everything
)

# conforms: bool -- True if no violations
# results_graph: rdflib.Graph -- W3C SHACL ValidationReport
# results_text: str -- human-readable text report
```

### Parsing the Validation Report Graph
```python
# Source: W3C SHACL spec https://www.w3.org/TR/shacl/#validation-report
from rdflib.namespace import SH

# Query the results_graph for individual validation results
REPORT_QUERY = """
SELECT ?result ?severity ?focusNode ?path ?value ?message ?sourceShape ?component
WHERE {
    ?report a sh:ValidationReport ;
            sh:result ?result .
    ?result sh:resultSeverity ?severity ;
            sh:focusNode ?focusNode .
    OPTIONAL { ?result sh:resultPath ?path }
    OPTIONAL { ?result sh:value ?value }
    OPTIONAL { ?result sh:resultMessage ?message }
    OPTIONAL { ?result sh:sourceShape ?sourceShape }
    OPTIONAL { ?result sh:sourceConstraintComponent ?component }
}
"""

for row in results_graph.query(REPORT_QUERY):
    # row.severity is one of: sh:Violation, sh:Warning, sh:Info
    # row.focusNode is the IRI of the object that failed
    # row.path is the property path (e.g., dcterms:title)
    # row.message is sh:message from shape or auto-generated
    pass
```

### LOV REST API Vocabulary List
```python
# Source: https://lov.linkeddata.es/dataset/lov/api
import httpx

async def fetch_lov_vocabularies() -> list[dict]:
    """Fetch all vocabulary prefixes from LOV."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://lov.linkeddata.es/dataset/lov/api/v2/vocabulary/list"
        )
        resp.raise_for_status()
        vocabs = resp.json()

    # Each entry: {"prefix": "schema", "nsp": "http://schema.org/", "uri": "...", "titles": [...]}
    return [
        {"prefix": v["prefix"], "namespace": v["nsp"]}
        for v in vocabs
        if "prefix" in v and "nsp" in v
    ]
```

### asyncio.Queue FIFO Worker
```python
# Source: https://johnsturgeon.me/2022/12/10/fastapi-writing-a-fifo-queue-with-asyncioqueue/
import asyncio

async def validation_worker(queue: asyncio.Queue, validate_fn):
    """Process validation jobs one at a time in FIFO order."""
    while True:
        job = await queue.get()
        try:
            await validate_fn(job)
        except Exception as e:
            logging.exception("Validation failed: %s", e)
        finally:
            queue.task_done()

# Start in lifespan:
# queue = asyncio.Queue()
# asyncio.create_task(validation_worker(queue, do_validation))
```

### SPARQL Batch Label Resolution with Language Preference
```python
# Source: W3C SPARQL 1.1 spec + RDF label best practices
BATCH_LABEL_QUERY = """
SELECT ?iri ?label WHERE {{
  VALUES (?iri) {{ {values} }}
  OPTIONAL {{ ?iri dcterms:title ?t .
              FILTER(LANG(?t) = "" || LANG(?t) = "{lang}") }}
  OPTIONAL {{ ?iri rdfs:label ?r .
              FILTER(LANG(?r) = "" || LANG(?r) = "{lang}") }}
  OPTIONAL {{ ?iri skos:prefLabel ?s .
              FILTER(LANG(?s) = "" || LANG(?s) = "{lang}") }}
  OPTIONAL {{ ?iri schema:name ?n .
              FILTER(LANG(?n) = "" || LANG(?n) = "{lang}") }}
  BIND(COALESCE(?t, ?r, ?s, ?n) AS ?label)
}}
"""
```

### Polling Endpoint for Latest Validation
```python
# Source: Architecture decision (polling endpoint per user decision)
@router.get("/api/validation/latest")
async def get_latest_validation(
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Return the latest validation report summary."""
    query = """
    SELECT ?report ?event ?conforms ?violations ?warnings ?infos ?ts
    WHERE {
      GRAPH <urn:sempkm:validations> {
        ?report a sempkm:ValidationReport ;
                sempkm:forEvent ?event ;
                sempkm:conforms ?conforms ;
                sempkm:violationCount ?violations ;
                sempkm:warningCount ?warnings ;
                sempkm:infoCount ?infos ;
                sempkm:timestamp ?ts .
      }
    }
    ORDER BY DESC(?ts) LIMIT 1
    """
    result = await client.query(query)
    # ... format and return
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pyshacl <0.27 (validate all nodes) | pyshacl 0.27+ focus node filtering | Oct 2024 | Can validate only specific nodes if needed (useful for incremental validation in future) |
| pyshacl <0.29 (inferences in data graph) | pyshacl 0.29+ (inferences in separate named graph) | Nov 2024 | Cleaner separation; won't pollute data graph with inferred triples |
| pyshacl <0.31 (single graph) | pyshacl 0.31+ validate_each() for multi-graph | Jan 2026 | Could validate per-model graphs independently in future |
| cachetools <7.0 (Python 3.7+) | cachetools 7.0+ (Python 3.10+) | Feb 2026 | Dropped old Python support; current project uses 3.12 |

**Deprecated/outdated:**
- pyshacl <0.29: Required Python 3.8+, now minimum 3.9. Project uses 3.12 so no concern.
- The `@app.on_event("startup")` pattern for FastAPI: Deprecated in favor of `lifespan` context manager. Project already uses `lifespan` (see main.py).

## Open Questions

1. **SHACL shapes source in Phase 2**
   - What we know: SHACL shapes will be part of Mental Models (Phase 3). In Phase 2, we need shapes to validate against.
   - What's unclear: Where do shapes come from before Phase 3 is implemented? Do we use test shapes? A hardcoded shapes graph?
   - Recommendation: Phase 2 should define the shapes loading interface (a callable that returns an rdflib Graph). During Phase 2 testing, use fixture shapes. Phase 3 will implement the actual loader that reads shapes from installed Mental Model named graphs. The validation engine should accept any shapes graph.

2. **Validation report named graph scoping**
   - What we know: Validation reports are stored as named graphs. The SPARQL read endpoint scopes to `urn:sempkm:current` by default.
   - What's unclear: Should validation reports be accessible via the general SPARQL endpoint or only via the dedicated validation API?
   - Recommendation: Store reports in dedicated named graphs (`urn:sempkm:validation:{uuid}`) and summaries in `urn:sempkm:validations`. The general SPARQL endpoint stays scoped to current state. A dedicated validation router provides report access.

3. **Incremental vs full re-validation performance**
   - What we know: User decision is "full re-validation" after each commit. For small graphs this is fine.
   - What's unclear: At what graph size does full re-validation become noticeably slow?
   - Recommendation: Implement full re-validation as decided. Monitor timing. pyshacl 0.27+ supports focus node filtering if incremental validation is needed later. The queue coalesce pattern (Pitfall 4) mitigates rapid-edit scenarios.

4. **Auto-generated fallback messages**
   - What we know: sh:message from shapes is preferred. When not present, auto-generate from constraint metadata.
   - What's unclear: Exact template format for auto-generated messages.
   - Recommendation: Use a simple template like `"{property_path} {constraint_type}: {details}"` -- e.g., "dcterms:title sh:minCount: minimum 1 value required". Parse sh:sourceConstraintComponent from the validation result to determine constraint type.

## Sources

### Primary (HIGH confidence)
- [pyshacl GitHub README](https://github.com/RDFLib/pySHACL) - validate() API, parameters, return values, in-memory graph support
- [pyshacl PyPI](https://pypi.org/project/pyshacl/) - Version 0.31.0, released 2026-01-16, requires Python >=3.9, rdflib dependency
- [pyshacl FEATURES.md](https://github.com/RDFLib/pySHACL/blob/master/FEATURES.md) - All SHACL Core Constraint Components supported
- [pyshacl CHANGELOG](https://raw.githubusercontent.com/RDFLib/pySHACL/master/CHANGELOG.md) - Version history, breaking changes, focus node filtering (0.27+)
- [W3C SHACL Spec](https://www.w3.org/TR/shacl/) - ValidationReport/ValidationResult structure, severity levels, sh:message
- [LOV API docs](https://lov.linkeddata.es/dataset/lov/api) - REST API endpoints: /api/v2/vocabulary/list, /autocomplete, /info, /search
- [LOV vocabulary list endpoint](https://lov.linkeddata.es/dataset/lov/api/v2/vocabulary/list) - JSON response format verified: {prefix, nsp, uri, titles}
- [RDF4J SHACL docs](https://rdf4j.org/documentation/programming/shacl/) - ShaclSail behavior: synchronous on commit, not suitable for async pattern
- [RDF4J REST API](https://rdf4j.org/documentation/reference/rest-api/) - CONSTRUCT query Accept header: text/turtle for Turtle response
- [cachetools PyPI](https://pypi.org/project/cachetools/) - Version 7.0.1, released 2026-02-10, TTLCache(maxsize, ttl) API
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) - BackgroundTasks for simple cases

### Secondary (MEDIUM confidence)
- [FastAPI FIFO Queue with asyncio.Queue](https://johnsturgeon.me/2022/12/10/fastapi-writing-a-fifo-queue-with-asyncioqueue/) - asyncio.Queue worker pattern for sequential processing, verified against Python asyncio docs
- [Python asyncio docs](https://docs.python.org/3/library/asyncio-eventloop.html) - run_in_executor for CPU-bound work, to_thread for blocking calls
- [Human-readable names in RDF](https://www.bobdc.com/blog/rdflabels/) - Label property hierarchy, language tag handling

### Tertiary (LOW confidence)
- LOV API uptime/reliability: Based on community reports. LOV is a well-known service but has no formal SLA. Import should handle failures gracefully.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pyshacl is the only mature Python SHACL validator; cachetools is well-established; both verified via PyPI and GitHub
- Architecture: HIGH - Patterns are straightforward composition of verified libraries with existing project architecture; async queue pattern is well-documented
- Pitfalls: HIGH - Based on direct code review of Phase 1 (graph scoping, event loop blocking) and verified library behavior (pyshacl CPU-bound, cache invalidation)

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (stable domain; pyshacl and cachetools are mature)
