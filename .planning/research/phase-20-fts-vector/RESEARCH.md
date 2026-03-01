## Decision

Use RDF4J's built-in LuceneSail for keyword full-text search (v2.2, Phase 20a), and defer pgvector + sentence-transformers semantic search to a later phase (Phase 20b) after PostgreSQL migration is complete.

**Rationale:**
- LuceneSail wraps the existing NativeStore at the SAIL layer — zero new containers, zero sync infrastructure, zero write-path changes; the Lucene index is updated synchronously within each RDF4J transaction
- SemPKM already runs RDF4J 5.0.1; LuceneSail ships in the RDF4J distribution; activation requires only a repository config file change (`config/rdf4j/sempkm-repo.ttl`)
- PKM-scale datasets (hundreds to low thousands of objects) are well within LuceneSail's ~100K object scale limit
- SPARQL-native integration (`search:matches` property path) allows FTS results to be combined with type filters and graph scoping (`FROM <urn:sempkm:current>`) in a single query
- For semantic search (Phase 20b), pgvector reuses the existing PostgreSQL/asyncpg infrastructure already present in the codebase; `all-MiniLM-L6-v2` (22MB model, 384 dims, ~14k sent/sec CPU) requires no GPU

**Alternatives ruled out:**
- **OpenSearch/Elasticsearch sidecar** — adds 512MB+ RAM, requires custom sync pipeline, eventual consistency, and operational overhead that is disproportionate to PKM-scale data; LuceneSail provides ~80% of the benefit at 0% additional infrastructure cost
- **Apache Jena (Fuseki + jena-text)** — switching triplestores would require rewriting TriplestoreClient, EventStore transaction logic, and repository setup; the different SPARQL property function syntax and REST API are not compatible with the existing codebase
- **Oxigraph** — no built-in FTS capability whatsoever (confirmed via GitHub issue #48); would require an external sidecar to achieve any FTS
- **GraphDB (Ontotext)** — licensing restrictions for commercial use; different REST API requiring TriplestoreClient rewrite; not worth switching for FTS alone
- **SQLite FTS5 (stopgap)** — acceptable only if PostgreSQL migration for Phase 20b is blocked; fragile for scale above ~10K objects; not the primary path

---

# Phase 20: Full-Text Search + Vector Store Research

**Domain:** Search infrastructure for a Semantic Personal Knowledge Management system
**Researched:** 2026-02-27
**Overall Confidence:** MEDIUM-HIGH (RDF4J LuceneSail well-documented; vector/hybrid search patterns well-established; some integration details need runtime validation)

---

## Executive Summary / Recommendation

**Use RDF4J's built-in LuceneSail for keyword full-text search (Phase 20a), then add pgvector + sentence-transformers for semantic search later (Phase 20b).**

SemPKM already runs RDF4J 5.0.1 with a NativeStore. RDF4J ships with LuceneSail, a stacked SAIL that wraps the NativeStore and automatically indexes all literal values into a Lucene index. This is the lowest-friction path to full-text search: it requires only a repository configuration change (new Turtle config file), zero new containers, and zero sync infrastructure. LuceneSail automatically indexes statements as they flow through the SAIL layer, meaning the existing `EventStore.commit()` write path needs no changes -- writes that go through the RDF4J REST API are intercepted by LuceneSail transparently.

For semantic/vector search (Phase 20b), add pgvector to the existing SQLite-or-PostgreSQL database layer. SemPKM already has `asyncpg` in its dependencies and a `DATABASE_URL` config for SQL. When the project migrates to PostgreSQL for production (which the asyncpg dependency suggests is planned), pgvector becomes a natural extension. Use `sentence-transformers/all-MiniLM-L6-v2` (22MB model, 384 dimensions, ~14k sentences/sec on CPU) for embeddings. Combine keyword + vector results using Reciprocal Rank Fusion (RRF).

**Do NOT add OpenSearch/Elasticsearch as a sidecar.** It adds a ~512MB+ container, requires a custom sync pipeline, and solves the same problem LuceneSail solves natively with zero overhead.

---

## 1. RDF4J's Built-in LuceneSail

**Confidence: MEDIUM-HIGH** (official docs + multiple community sources; some named graph edge cases need runtime validation)

### What It Is

LuceneSail is a stacked SAIL implementation included in the RDF4J distribution. It wraps any base SAIL (NativeStore, MemoryStore) and automatically intercepts all statement additions/removals to maintain a synchronized Lucene index. The Lucene index stores all literal values and enables full-text search via a special SPARQL query syntax.

### How It Works

1. **Stacked architecture:** LuceneSail wraps the NativeStore as a "decorator." All SPARQL queries and updates pass through LuceneSail first.
2. **Automatic indexing:** When statements are added/removed (including via SPARQL UPDATE), LuceneSail's change listener automatically updates the Lucene index. No manual sync needed.
3. **SPARQL integration:** Search queries use a virtual `search:` namespace with property paths to invoke Lucene queries from within SPARQL.

### Current Repository Configuration

The current SemPKM repo config (`config/rdf4j/sempkm-repo.ttl`) uses a plain NativeStore:

```turtle
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

### Proposed LuceneSail Configuration

To add LuceneSail, wrap the NativeStore with a delegate pattern:

```turtle
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix config: <tag:rdf4j.org,2023:config/> .

[] a config:Repository ;
   config:rep.id "sempkm" ;
   rdfs:label "SemPKM Knowledge Base" ;
   config:rep.impl [
      config:rep.type "openrdf:SailRepository" ;
      config:sail.impl [
         config:sail.type "openrdf:LuceneSail" ;
         config:lucene.luceneDir "/var/rdf4j/lucene-index" ;
         config:sail.delegate [
            config:sail.type "openrdf:NativeStore" ;
            config:native.tripleIndexes "spoc,posc,cspo" ;
            config:sail.defaultQueryEvaluationMode "STANDARD"
         ]
      ]
   ] .
```

**IMPORTANT caveat:** The exact Turtle config vocabulary for LuceneSail in RDF4J 5.x using the unified `tag:rdf4j.org,2023:config/` namespace needs runtime validation. The legacy vocabulary used `@prefix lucene: <http://www.openrdf.org/config/sail/lucene#>` which may still work. The config above is a best-effort reconstruction from documentation and community examples. **Test this against the actual RDF4J 5.0.1 Docker image before committing.**

### SPARQL Query Syntax for Full-Text Search

```sparql
PREFIX search: <http://www.openrdf.org/contrib/lucenesail#>

SELECT ?subject ?score ?snippet
FROM <urn:sempkm:current>
WHERE {
  ?subject search:matches [
    search:query "knowledge management" ;
    search:score ?score ;
    search:snippet ?snippet
  ] .
}
ORDER BY DESC(?score)
LIMIT 20
```

Key query properties:
- `search:matches` -- links subject to search result (required)
- `search:query` -- the Lucene query string (required). Supports Lucene syntax: wildcards (`alic*`), phrases (`"exact phrase"`), boolean (`term1 AND term2`)
- `search:property` -- restrict search to a specific predicate (optional; omit to search all literals)
- `search:score` -- relevance score (optional)
- `search:snippet` -- highlighted text snippet (optional)

### FTS + SPARQL Filtering Composition

This is a critical question for SemPKM. The answer is **yes, you can combine FTS with SPARQL filtering**, but with caveats.

**Pattern 1: FTS + type filter (works well)**
```sparql
PREFIX search: <http://www.openrdf.org/contrib/lucenesail#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?subject ?score ?snippet
FROM <urn:sempkm:current>
WHERE {
  ?subject search:matches [
    search:query "meeting notes" ;
    search:score ?score ;
    search:snippet ?snippet
  ] .
  ?subject rdf:type <https://example.org/data/Note> .
}
ORDER BY DESC(?score)
```

**Pattern 2: FTS + graph restriction (needs validation)**
```sparql
SELECT ?subject ?score ?snippet
WHERE {
  GRAPH <urn:sempkm:current> {
    ?subject search:matches [
      search:query "meeting notes" ;
      search:score ?score ;
      search:snippet ?snippet
    ] .
    ?subject rdf:type <https://example.org/data/Note> .
  }
}
```

**Named graph limitation:** GitHub issue [#2077](https://github.com/eclipse/rdf4j/issues/2077) on the RDF4J repo indicates that using `GRAPH ?graph` with `search:matches` to discover which graph a result belongs to has had problems. For SemPKM this is less of a concern because we always scope to `urn:sempkm:current` via `FROM` clause. But this should be validated at implementation time.

### Indexing Configuration

LuceneSail can be configured to control what gets indexed:

- **`indexedfields`** -- specific predicates to index (default: all literal-valued predicates)
- **`indexedlang`** -- restrict to specific languages (e.g., "en")
- **`indexedtypes`** -- restrict to subjects of specific rdf:types
- **`reindexQuery`** -- custom SPARQL query for reindexation (default indexes everything including all named graphs)

For SemPKM, recommended configuration:
- Index all predicates (titles, labels, body text, descriptions)
- Filter to `en` language or untagged literals
- No type restriction (search across all PKM object types)
- Set `reindexQuery` to scope to `urn:sempkm:current` to avoid indexing event graph metadata

### Reindexing

LuceneSail supports full reindexation via a Java API method (`LuceneSail.reindex()`). This is a long-running operation that deletes and rebuilds the entire index. There is **no REST API endpoint** for triggering reindex -- it requires Java-level access or a restart with a fresh index directory.

For SemPKM, reindexing options:
1. **Delete the Lucene index directory and restart the RDF4J container** (simple, works for small datasets)
2. Create a custom RDF4J plugin that exposes a reindex endpoint (complex, unnecessary at PKM scale)

### Docker Image Compatibility

The `eclipse/rdf4j-workbench:5.0.1` Docker image ships as a WAR deployed on Tomcat. The RDF4J distribution includes the LuceneSail module (`rdf4j-sail-lucene`). However, whether the LuceneSail JAR is included in the Docker image's classpath needs **runtime verification**. If not, we would need to extend the Docker image to add the JAR.

**Verification step:** Check if `/usr/local/tomcat/webapps/rdf4j-server/WEB-INF/lib/rdf4j-sail-lucene-*.jar` exists in the container.

---

## 2. Alternative Triplestores with FTS

### Apache Jena (Fuseki + Lucene)

**Confidence: MEDIUM**

Jena's `jena-text` module provides Lucene/Solr integration for full-text search within SPARQL. It uses a property function syntax:

```sparql
PREFIX text: <http://jena.apache.org/text#>

SELECT ?s ?score
WHERE {
  (?s ?score) text:query ("meeting notes" 10) .
  ?s rdf:type <http://example.org/Note> .
}
```

**Pros:**
- Mature, well-documented FTS integration
- Automatic index updates on dataset changes via assembler configuration
- Fuseki is the most widely-deployed open-source SPARQL server

**Cons:**
- Replacing RDF4J with Jena would be a major migration
- Different SPARQL property function syntax for FTS
- Different REST API (Fuseki vs. RDF4J Server)
- SemPKM's `TriplestoreClient` is built entirely around RDF4J's transaction API (`begin_transaction`, `commit_transaction`, `transaction_update`)
- Jena's transaction model differs from RDF4J's URL-based transaction handles

**Verdict:** Not a drop-in replacement. Switching would require rewriting the TriplestoreClient, EventStore transaction logic, and repository setup. Not recommended.

### Oxigraph

**Confidence: HIGH**

Oxigraph is a lightweight SPARQL database written in Rust. It supports SPARQL 1.1 Query and Update.

**Full-text search: NOT SUPPORTED.** [GitHub issue #48](https://github.com/oxigraph/oxigraph/issues/48) proposes FTS as a feature request, but it has not been implemented as of 2026. Oxigraph has no built-in FTS capability whatsoever.

**Verdict:** Not viable for FTS without an external sidecar.

### GraphDB (Ontotext)

**Confidence: MEDIUM**

GraphDB (all editions including Free) includes a [Lucene Connector](https://graphdb.ontotext.com/documentation/11.2/lucene-graphdb-connector.html) that provides FTS via SPARQL. Configuration is done via SPARQL UPDATE commands that create connector instances. Query syntax uses a custom `luc:` namespace.

**Pros:**
- Strong FTS via built-in Lucene connector
- Also offers Elasticsearch and OpenSearch connectors (Enterprise only)
- More polished than RDF4J's LuceneSail

**Cons:**
- GraphDB Free has licensing restrictions for commercial use
- Different query syntax from RDF4J LuceneSail (`luc:query` vs `search:matches`)
- Different deployment model and REST API
- Would require TriplestoreClient rewrite

**Verdict:** Not recommended as a migration target for this feature alone. If SemPKM ever needed to switch triplestores for other reasons, GraphDB's FTS is excellent.

---

## 3. OpenSearch/Elasticsearch as a Sidecar

**Confidence: MEDIUM**

### Architecture

```
EventStore.commit()
    |
    v
RDF4J (SPARQL UPDATE)  -->  Post-commit hook  -->  Indexer  -->  OpenSearch
    |                                                                  |
    v                                                                  v
SPARQL queries for browsing                                  Search API for FTS
```

### Sync Strategy

Two approaches:

**A. Post-commit webhook (recommended if using this approach):**
After `EventStore.commit()` succeeds, publish the `EventResult` (containing affected IRIs) to a background task. An indexer fetches the full object data via SPARQL CONSTRUCT and upserts it into OpenSearch.

**B. Change Data Capture (more complex):**
Poll the RDF4J event graphs for new events since last checkpoint. Fetch affected objects and index them. Requires a checkpoint/cursor mechanism.

### Document Schema

```json
{
  "iri": "https://example.org/data/Note/my-note",
  "type": "Note",
  "title": "Meeting Notes",
  "body": "Discussed quarterly goals...",
  "labels": ["meeting", "quarterly"],
  "created": "2026-01-15T10:00:00Z",
  "all_text": "Meeting Notes Discussed quarterly goals..."
}
```

### Pros
- Full Lucene/BM25 ranking with rich query DSL
- Fuzzy matching, boosting, highlighting, aggregations, autocomplete
- Faceted search out of the box
- Scales to millions of documents
- Could later add vector search (k-NN plugin)

### Cons
- **Adds ~512MB+ RAM to Docker stack** (OpenSearch minimum heap)
- Requires custom sync infrastructure (indexer service, background task, error handling)
- Eventual consistency (index lags behind writes)
- Operational complexity (index management, mapping migrations, cluster health monitoring)
- Overkill for PKM-scale data (hundreds to low thousands of objects)
- Yet another thing to back up, version, and maintain

### Verdict

**Not recommended for SemPKM.** The complexity cost far outweighs the benefit at PKM scale. LuceneSail provides ~80% of the functionality at 0% additional infrastructure cost. OpenSearch becomes relevant only if SemPKM evolves into a multi-tenant SaaS with millions of objects per tenant, and even then pgvector with PostgreSQL full-text search may suffice.

---

## 4. pgvector + sentence-transformers for Semantic Search

**Confidence: MEDIUM-HIGH**

### What It Provides

Semantic/vector search finds results by meaning, not just keyword match. "How do I organize my projects?" would match a note titled "Task management methodology" even though they share no keywords. This is the key differentiator that keyword search alone cannot provide.

### Architecture

```
Write Path:
  EventStore.commit()
    |
    v
  Post-commit hook (async)
    |
    v
  Embedding Service (sentence-transformers in FastAPI process)
    |
    v
  pgvector INSERT (iri, embedding, text_content)

Read Path:
  User query "organize projects"
    |
    v
  Embed query --> 384-dim vector
    |
    v
  pgvector cosine similarity search
    |
    v
  Top-K results (IRIs + scores)
    |
    v
  Fetch object labels/types via SPARQL or label cache
```

### Technology Choices

| Component | Choice | Why |
|-----------|--------|-----|
| Embedding model | `all-MiniLM-L6-v2` | 22MB model, 384 dims, ~14k sent/sec on CPU, no GPU needed |
| Vector store | pgvector (PostgreSQL extension) | Reuses existing DB infra; SemPKM already has asyncpg in deps |
| Index type | HNSW | Best recall/speed tradeoff for < 1M vectors |
| Distance metric | Cosine similarity | Standard for normalized sentence embeddings |

### Database Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE search_embeddings (
    iri TEXT PRIMARY KEY,
    rdf_type TEXT NOT NULL,
    text_content TEXT NOT NULL,        -- concatenated searchable text
    embedding vector(384) NOT NULL,    -- all-MiniLM-L6-v2 output
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX idx_embeddings_hnsw ON search_embeddings
    USING hnsw (embedding vector_cosine_ops);

-- For keyword FTS within PostgreSQL (complement to vector search)
ALTER TABLE search_embeddings
    ADD COLUMN tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('english', text_content)) STORED;

CREATE INDEX idx_embeddings_tsv ON search_embeddings USING gin(tsv);

-- For type-filtered vector search
CREATE INDEX idx_embeddings_type ON search_embeddings (rdf_type);
```

### Hybrid Search (Keyword + Vector) via Reciprocal Rank Fusion

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

async def hybrid_search(
    db: AsyncSession,
    query: str,
    type_filter: str | None = None,
    limit: int = 20,
    k: int = 60,
) -> list[dict]:
    """Hybrid keyword + vector search with RRF fusion."""
    query_embedding = model.encode(query).tolist()

    # Build optional type filter clause
    type_clause = "AND rdf_type = $3" if type_filter else ""
    params_vec = [query_embedding, 30, type_filter] if type_filter else [query_embedding, 30]
    params_kw = [query, 30, type_filter] if type_filter else [query, 30]

    # 1. Vector search (top 30 candidates)
    vector_results = await db.fetch(f"""
        SELECT iri, 1 - (embedding <=> $1::vector) as score
        FROM search_embeddings
        WHERE true {type_clause}
        ORDER BY embedding <=> $1::vector
        LIMIT $2
    """, *params_vec)

    # 2. Keyword search (top 30 candidates)
    keyword_results = await db.fetch(f"""
        SELECT iri, ts_rank(tsv, plainto_tsquery('english', $1)) as score
        FROM search_embeddings
        WHERE tsv @@ plainto_tsquery('english', $1) {type_clause}
        ORDER BY score DESC
        LIMIT $2
    """, *params_kw)

    # 3. Reciprocal Rank Fusion
    scores: dict[str, float] = {}
    for rank, row in enumerate(vector_results):
        scores[row["iri"]] = scores.get(row["iri"], 0) + 1.0 / (k + rank + 1)
    for rank, row in enumerate(keyword_results):
        scores[row["iri"]] = scores.get(row["iri"], 0) + 1.0 / (k + rank + 1)

    # 4. Sort by combined score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"iri": iri, "score": score} for iri, score in ranked[:limit]]
```

### Memory Requirements

- **Model:** ~43MB VRAM (float16) or ~80MB RAM (float32 CPU inference)
- **10,000 embeddings at 384 dims (float32):** ~15MB storage
- **HNSW index overhead:** ~2x the vector data, so ~30MB for 10K vectors
- **Total overhead:** < 150MB RAM for model + index at PKM scale

### SQLite Consideration

SemPKM currently defaults to SQLite (`sqlite+aiosqlite`). pgvector requires PostgreSQL. Options:

1. **Phase 20b requires PostgreSQL migration.** This is already implied by the `asyncpg` dependency in `pyproject.toml`.
2. **Stopgap alternative:** Use SQLite FTS5 for keyword search and `hnswlib` (a C++ library with Python bindings) for vector search with numpy-file persistence. Works for < 10K objects but does not scale and is fragile.

**Recommendation:** When implementing Phase 20b, require PostgreSQL. Use SQLite FTS5 as a keyword-only stopgap only if PostgreSQL migration is blocked.

---

## 5. How FTS Composes with SPARQL Filtering (Detailed)

**Confidence: MEDIUM**

### RDF4J LuceneSail Composition

LuceneSail integrates directly into SPARQL query evaluation. The `search:matches` pattern is resolved as a "magic predicate" -- the Lucene query runs first, producing a set of matching subjects with scores, which then JOIN with the rest of the SPARQL WHERE clause.

**This means:**
- You CAN combine FTS with `rdf:type` filters -- FTS finds candidates, type triple pattern narrows results
- You CAN use `FROM <urn:sempkm:current>` to scope to the current state graph
- You CAN add `OPTIONAL` clauses to fetch additional properties of matched subjects
- The query optimizer may or may not push graph restrictions into the Lucene query -- results should be correct either way but performance may vary

**Full example: search notes by type + keyword with metadata**
```sparql
PREFIX search: <http://www.openrdf.org/contrib/lucenesail#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX schema: <https://schema.org/>

SELECT ?subject ?title ?type ?score ?snippet
FROM <urn:sempkm:current>
WHERE {
  ?subject search:matches [
    search:query "quarterly planning" ;
    search:score ?score ;
    search:snippet ?snippet
  ] .
  ?subject rdf:type ?type .
  OPTIONAL { ?subject dcterms:title ?title }
}
ORDER BY DESC(?score)
LIMIT 20
```

### pgvector Composition

With the sidecar approach, filtering works differently -- there is no SPARQL integration:

1. Run vector/keyword search in PostgreSQL to get candidate IRIs + scores
2. Use those IRIs in a SPARQL `VALUES` clause to fetch RDF properties and labels
3. Or store enough metadata (type, title) in the pgvector table to avoid the SPARQL round-trip for search results display

**Pre-filtering in PostgreSQL is better for performance:**
```sql
SELECT iri, 1 - (embedding <=> $1::vector) as score
FROM search_embeddings
WHERE rdf_type = 'Note'
ORDER BY embedding <=> $1::vector
LIMIT 20
```

**Post-enrichment via SPARQL:**
```sparql
SELECT ?iri ?title ?type
FROM <urn:sempkm:current>
WHERE {
  VALUES (?iri) { (<iri1>) (<iri2>) (<iri3>) }
  ?iri rdf:type ?type .
  OPTIONAL { ?iri dcterms:title ?title }
}
```

This two-step pattern (search in pgvector, enrich in SPARQL) is clean and keeps search performance independent of triplestore query speed.

---

## 6. Write Path Integration

### LuceneSail (Phase 20a) -- Zero Changes Required

This is the single biggest advantage of LuceneSail. Because it wraps the NativeStore at the SAIL layer, **every SPARQL UPDATE that flows through the RDF4J REST API is automatically intercepted and indexed.** This includes:

- `EventStore.commit()` which sends SPARQL INSERT DATA / DELETE WHERE via the transaction API
- Direct SPARQL UPDATEs via the statements endpoint
- Any bulk data loading

**No hooks needed. No async indexing. No sync infrastructure.**

The Lucene index is updated synchronously within the same RDF4J transaction. When `EventStore.commit()` calls `commit_transaction()`, the Lucene index is already consistent with the RDF data.

### pgvector (Phase 20b) -- Post-Commit Hook Required

For vector embeddings, we need a hook after `EventStore.commit()`. The cleanest approach is an event listener pattern:

```python
# In EventStore, add a listener mechanism:
class EventStore:
    def __init__(self, client: TriplestoreClient) -> None:
        self._client = client
        self._listeners: list[Callable] = []

    def add_listener(self, callback: Callable[[EventResult], Awaitable[None]]) -> None:
        self._listeners.append(callback)

    async def commit(self, operations, performed_by=None, performed_by_role=None):
        # ... existing commit logic unchanged ...
        await self._client.commit_transaction(txn_url)

        result = EventResult(
            event_iri=event_iri,
            timestamp=timestamp,
            affected_iris=all_affected_iris,
        )

        # Notify listeners (non-blocking)
        for listener in self._listeners:
            try:
                await listener(result)
            except Exception:
                logger.warning("Post-commit listener failed", exc_info=True)

        return result
```

**Embedding update listener:**
```python
class EmbeddingService:
    def __init__(self, db, triplestore_client, model_name="all-MiniLM-L6-v2"):
        self._db = db
        self._ts = triplestore_client
        self._model = SentenceTransformer(model_name)
        self._queue: asyncio.Queue = asyncio.Queue()

    async def on_commit(self, result: EventResult) -> None:
        """Queue affected IRIs for async embedding."""
        for iri in result.affected_iris:
            await self._queue.put(iri)

    async def process_queue(self) -> None:
        """Background task: process embedding queue."""
        while True:
            iri = await self._queue.get()
            try:
                text = await self._fetch_text(iri)
                if text:
                    embedding = self._model.encode(text)
                    await self._upsert(iri, text, embedding)
            except Exception:
                logger.warning(f"Embedding failed for {iri}", exc_info=True)
```

**Reindex strategy:**
```python
async def reindex_all(self) -> int:
    """Full reindex: fetch all objects from SPARQL, embed, upsert."""
    results = await self._ts.query("""
        SELECT ?s (GROUP_CONCAT(?text; separator=" ") AS ?alltext)
        FROM <urn:sempkm:current>
        WHERE {
            ?s rdf:type ?type .
            ?s ?p ?text .
            FILTER(isLiteral(?text))
            FILTER(?type != <urn:sempkm:StateGraph>)
        }
        GROUP BY ?s
    """)
    count = 0
    subjects = results["results"]["bindings"]
    for batch in chunked(subjects, 64):
        texts = [b["alltext"]["value"] for b in batch]
        embeddings = self._model.encode(texts)
        for binding, emb in zip(batch, embeddings):
            await self._upsert(binding["s"]["value"], binding["alltext"]["value"], emb)
            count += 1
    return count
```

---

## 7. Comparison Matrix

| Criterion | RDF4J LuceneSail | OpenSearch Sidecar | pgvector + sentence-transformers | SQLite FTS5 |
|-----------|------------------|--------------------|----------------------------------|-------------|
| **Search type** | Keyword (Lucene) | Keyword (Lucene) | Semantic + keyword hybrid | Keyword (BM25) |
| **New containers** | 0 | 1 (512MB+ RAM) | 0 (reuse existing DB) | 0 |
| **Sync infrastructure** | None (automatic) | Custom hook + indexer | Post-commit hook | Post-commit hook |
| **Write path changes** | None | Moderate | Moderate | Moderate |
| **SPARQL integration** | Native (in-query) | None (separate API) | None (separate API) | None (separate API) |
| **Query capabilities** | Wildcards, phrases, boolean | Full Lucene DSL, facets, aggs | Cosine similarity, RRF hybrid | MATCH, BM25 ranking |
| **Relevance ranking** | Lucene TF-IDF | Lucene BM25 | Embedding cosine + BM25 hybrid | BM25 |
| **Highlighted snippets** | Yes | Yes | No (needs custom impl) | Yes (via snippet()) |
| **Autocomplete** | Limited | Yes (suggest API) | No | Yes (prefix queries) |
| **Scale limit** | ~100K objects | Millions | ~1M with HNSW | ~100K objects |
| **Operational complexity** | Low | High | Medium | Low |
| **Requires PostgreSQL** | No | No | Yes | No |
| **Semantic understanding** | No | No | Yes | No |
| **Setup effort** | Low (config change) | High (new service) | Medium (schema + model) | Medium (schema + sync) |
| **Fit for SemPKM** | Excellent | Poor | Good (Phase 20b) | Acceptable stopgap |

---

## 8. Recommended Implementation Approach

### Phase 20a: Keyword FTS via LuceneSail

**Effort:** 1-2 days
**Prerequisites:** Verify LuceneSail JAR is in Docker image

**Steps:**

1. **Verify Docker image compatibility:**
   - Exec into the RDF4J container
   - Check for `rdf4j-sail-lucene-*.jar` in the webapp lib directory
   - If missing, create a custom Dockerfile extending `eclipse/rdf4j-workbench:5.0.1`

2. **Update repo config** (`config/rdf4j/sempkm-repo.ttl`):
   - Wrap NativeStore with LuceneSail (see config in Section 1)
   - Add `luceneDir` pointing to a Docker volume path
   - Add Lucene index volume to `docker-compose.yml`:
     ```yaml
     volumes:
       - rdf4j_data:/var/rdf4j
       - lucene_index:/var/rdf4j/lucene-index
     ```

3. **Handle initial deployment:**
   - Existing repository must be deleted and recreated with the new config
   - Or use the RDF4J REST API `POST /repositories/{id}/config` to update in place
   - The Lucene index will be empty; LuceneSail will index data incrementally as it is accessed/modified
   - For immediate full index: delete index dir and restart, or trigger writes on all objects

4. **Add SearchService** to backend (`backend/app/services/search.py`):
   ```python
   class SearchService:
       async def search(
           self, query: str, type_filter: str | None = None, limit: int = 20
       ) -> list[SearchResult]:
           sparql = self._build_search_query(query, type_filter, limit)
           results = await self._client.query(sparql)
           return self._parse_results(results)
   ```

5. **Add search API endpoint** (`GET /api/search?q=term&type=Note&limit=20`):
   - Returns JSON: `{ results: [{ iri, title, type, score, snippet }] }`

6. **Add search UI:**
   - Search bar in top nav or Ctrl+K command palette
   - htmx-powered results panel with type facet toggles
   - Result items link to object view pages

### Phase 20b: Semantic Search via pgvector

**Effort:** 3-5 days
**Prerequisites:** PostgreSQL migration completed

**Steps:**

1. Add PostgreSQL + pgvector to Docker stack (or add pgvector extension to existing PostgreSQL)
2. Create `search_embeddings` table with vector column and HNSW index
3. Add `sentence-transformers` to `pyproject.toml` dependencies
4. Load `all-MiniLM-L6-v2` model on FastAPI startup (lazy-load to avoid slow cold starts)
5. Add `EmbeddingService` with post-commit listener on EventStore
6. Add background task for async embedding queue processing
7. Add `GET /api/search?q=term&mode=hybrid` endpoint for hybrid search
8. Add reindex management command: `python -m app.cli reindex-embeddings`
9. UI: toggle between "keyword" and "smart" search modes

### Phase 20c: Search UX Polish

**Effort:** 2-3 days
**Prerequisites:** Phase 20a complete

**Steps:**

1. Autocomplete / typeahead suggestions (debounced input, htmx `hx-trigger="input changed delay:300ms"`)
2. Search result previews with highlighted snippets
3. "Related items" sidebar using vector similarity (Phase 20b)
4. Recent searches history (localStorage)
5. Search scope selector (all types, specific type, within current workspace)

---

## 9. Risks and Mitigations

### Risk 1: LuceneSail JAR Not in Docker Image

**Severity:** HIGH (blocks Phase 20a entirely)
**Likelihood:** MEDIUM -- the RDF4J distribution includes LuceneSail, but the Docker image may ship a minimal subset
**Mitigation:** Inspect the container. If missing, extend the Dockerfile:
```dockerfile
FROM eclipse/rdf4j-workbench:5.0.1
# Copy LuceneSail and Lucene dependencies
COPY lucene-jars/ /usr/local/tomcat/webapps/rdf4j-server/WEB-INF/lib/
```
Required JARs: `rdf4j-sail-lucene`, `lucene-core`, `lucene-analyzers-common`, `lucene-queryparser`, `lucene-highlighter`. These must all be the versions compatible with RDF4J 5.0.1.

### Risk 2: LuceneSail Config Syntax Wrong for RDF4J 5.x

**Severity:** MEDIUM (blocks until corrected, but solvable by trial)
**Likelihood:** MEDIUM
**Mitigation:** RDF4J 5.x unified the config namespace to `tag:rdf4j.org,2023:config/` but still supports legacy `http://www.openrdf.org/config/` vocabulary. Try both. Check the built-in templates in the Workbench (`/var/rdf4j/server/templates/`). The Workbench UI may also have a "Native Store + Lucene" template to reference.

### Risk 3: Named Graph Scoping with LuceneSail

**Severity:** MEDIUM (FTS returns results from event graphs = wrong/noisy results)
**Likelihood:** LOW-MEDIUM
**Mitigation:** SemPKM already uses `FROM <urn:sempkm:current>` to scope queries. Even if the Lucene index contains literals from event graphs, the `FROM` clause restricts the SPARQL join, so only subjects that exist in `urn:sempkm:current` will appear in results. Additionally, the `reindexQuery` parameter can be configured to only index the current state graph:
```
reindexQuery=SELECT ?s ?p ?o WHERE { GRAPH <urn:sempkm:current> { ?s ?p ?o } }
```

### Risk 4: Repository Migration (NativeStore to LuceneSail)

**Severity:** MEDIUM (potential data loss if done wrong)
**Likelihood:** LOW
**Mitigation:** LuceneSail wraps NativeStore, so the underlying data files (.dat, .idx) are unchanged. The safest migration:
1. Back up the `rdf4j_data` volume
2. Stop the RDF4J container
3. Replace `config.ttl` in the repository directory (or delete repo and recreate)
4. Start the container
5. Verify data integrity with a SPARQL count query

### Risk 5: Embedding Model Size and Latency (Phase 20b)

**Severity:** LOW
**Likelihood:** LOW
**Mitigation:** `all-MiniLM-L6-v2` is tiny (22MB model weights, ~80MB RAM at runtime). Embedding is async via a background queue. Even synchronous embedding adds < 100ms per object write. For batch reindex of 10K objects at ~14K sentences/sec: under 1 second.

### Risk 6: PostgreSQL Not Yet Available (Phase 20b)

**Severity:** MEDIUM (blocks vector search entirely)
**Likelihood:** MEDIUM -- SemPKM currently uses SQLite
**Mitigation:** Phase 20b explicitly depends on PostgreSQL migration. If PostgreSQL is not ready:
- Phase 20a (LuceneSail keyword FTS) has no PostgreSQL dependency and works immediately
- As a stopgap for vector search, use `hnswlib` Python library with numpy file persistence (no database needed). Fragile but functional for < 10K objects.
- SQLite FTS5 can provide keyword search independent of LuceneSail if needed

---

## 10. Key Sources

### RDF4J LuceneSail
- [RDF4J LuceneSail Documentation](https://rdf4j.org/documentation/programming/lucene/) -- PRIMARY reference
- [RDF4J LuceneSail GitHub Source Docs](https://github.com/eclipse-rdf4j/rdf4j-doc/blob/master/site/content/documentation/programming/lucene.md)
- [LuceneSail JavaDoc (5.1.3)](https://rdf4j.org/javadoc/latest/org/eclipse/rdf4j/sail/lucene/LuceneSail.html)
- [RDF4J Repository Configuration Reference](https://rdf4j.org/documentation/reference/configuration/)
- [RDF4J REST API Reference](https://rdf4j.org/documentation/reference/rest-api/)
- [Named Graph + LuceneSail Issue #2077](https://github.com/eclipse/rdf4j/issues/2077)
- [Lucene 9 Compatibility Issue #5090](https://github.com/eclipse-rdf4j/rdf4j/issues/5090)
- [Google Groups: LuceneSail Config Template](https://groups.google.com/g/rdf4j-users/c/epF4Af1jXGU)

### Apache Jena Text Search
- [Jena Full Text Search Documentation](https://jena.apache.org/documentation/query/text-query.html)

### Oxigraph
- [Oxigraph FTS Feature Request (Issue #48)](https://github.com/oxigraph/oxigraph/issues/48)

### GraphDB
- [Lucene GraphDB Connector (11.2)](https://graphdb.ontotext.com/documentation/11.2/lucene-graphdb-connector.html)
- [Lucene Full-Text Search (9.8, deprecated)](https://graphdb.ontotext.com/documentation/9.8/free/full-text-search.html)

### pgvector
- [pgvector GitHub](https://github.com/pgvector/pgvector) -- Confidence: HIGH (official repo)
- [pgvector Hybrid Search Examples](https://github.com/pgvector/pgvector-python/blob/master/examples/hybrid_search/rrf.py) -- Confidence: HIGH

### sentence-transformers / Embeddings
- [all-MiniLM-L6-v2 on HuggingFace](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) -- Confidence: HIGH
- [Model Memory Requirements Discussion](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/discussions/39) -- Confidence: HIGH

### OpenSearch / Elasticsearch + RDF
- [Open Semantic Search: RDF Connector](https://opensemanticsearch.org/connector/rdf/)
- [Amazon Neptune OpenSearch Integration](https://docs.aws.amazon.com/neptune/latest/userguide/full-text-search-model.html)

---

## 11. Open Questions (Need Phase-Specific Research)

1. **Is `rdf4j-sail-lucene` JAR included in the `eclipse/rdf4j-workbench:5.0.1` Docker image?**
   Must verify by running `docker exec` and listing JARs in the WEB-INF/lib directory. This is the single highest-priority validation item.

2. **Exact Turtle config syntax for LuceneSail in RDF4J 5.x unified namespace.**
   The `tag:rdf4j.org,2023:config/` namespace was introduced in RDF4J 5.0. The exact property names for LuceneSail config (`luceneDir`, `reindexQuery`, etc.) under this namespace need validation. Check `/var/rdf4j/server/templates/` inside the container for built-in templates.

3. **Does `FROM <urn:sempkm:current>` properly filter LuceneSail results?**
   The `FROM` clause should restrict the SPARQL join to the current state graph, but the Lucene index itself may contain literals from event graphs. The risk is that a subject IRI from an event graph that happens to also exist in the current graph could surface. Testing with actual data is needed.

4. **Performance impact of LuceneSail on write throughput.**
   LuceneSail synchronously indexes on every write. For PKM-scale writes (dozens per hour) this is negligible, but should be measured to confirm no regression on `EventStore.commit()` latency.

5. **PostgreSQL migration timeline.**
   Phase 20b depends on this. Currently SemPKM uses SQLite with asyncpg available as a declared dependency but unused by default. The migration plan and timeline affect when semantic search can be delivered.

6. **Lucene version compatibility in RDF4J 5.0.1.**
   GitHub issue [#5090](https://github.com/eclipse-rdf4j/rdf4j/issues/5090) discusses Lucene 9 compatibility. RDF4J 5.0.1 may still use Lucene 8. This matters if we need to add JARs manually -- we must match the Lucene major version exactly.

---

## v2.2 Handoff

**Target:** v2.2 Data Discovery milestone, Phase 20a (keyword FTS)

### Prerequisites Before Implementation

1. **Verify LuceneSail JAR presence in Docker image** — exec into the running `eclipse/rdf4j-workbench:5.0.1` container and confirm `rdf4j-sail-lucene-*.jar` exists in `/usr/local/tomcat/webapps/rdf4j-server/WEB-INF/lib/`. If absent, extend the Dockerfile to add it (see Section 9, Risk 1). This is the single highest-priority validation item.

2. **Validate LuceneSail Turtle config syntax for RDF4J 5.x** — the unified `tag:rdf4j.org,2023:config/` namespace was introduced in RDF4J 5.0; the exact property names for LuceneSail configuration (`luceneDir`, `reindexQuery`, etc.) need runtime validation. Check `/var/rdf4j/server/templates/` inside the container for built-in config templates.

3. **Validate `FROM <urn:sempkm:current>` scoping with LuceneSail** — confirm that the `FROM` clause in SPARQL queries properly restricts LuceneSail results to the current state graph and does not surface subjects from event graphs.

### Phase 20a First Steps (Keyword FTS)

1. Update `config/rdf4j/sempkm-repo.ttl` — wrap NativeStore with LuceneSail delegate pattern (see Section 1, Proposed LuceneSail Configuration); add `luceneDir` pointing to a Docker volume path; add `reindexQuery` scoped to `urn:sempkm:current`

2. Add `lucene_index` Docker volume to `docker-compose.yml`; document migration procedure (backup `rdf4j_data` volume, update config, restart container, verify data with SPARQL count query)

3. Create `backend/app/services/search.py` — `SearchService.search(query, type_filter, limit)` executes the SPARQL FTS query pattern from Section 1 against the TriplestoreClient

4. Add `GET /api/search?q=term&type=Note&limit=20` endpoint returning `{results: [{iri, title, type, score, snippet}]}`

5. Integrate search UI into command palette (Ctrl+K, requirement FTS-03) — this aligns with the existing `ninja-keys` command palette from Phase 13

6. Requirements satisfied: FTS-01 (keyword search), FTS-02 (result display with type + snippet), FTS-03 (command palette integration)

### Phase 20b Prerequisites (Semantic Search — Deferred)

Phase 20b is blocked until:
- PostgreSQL migration is complete (SemPKM currently uses SQLite by default)
- `sentence-transformers` and `pgvector` Python packages added to `pyproject.toml`

First step when unblocked: create `search_embeddings` table with HNSW index (see Section 4, Database Schema), add `EmbeddingService` with post-commit listener pattern on `EventStore` (see Section 6, Write Path Integration).
