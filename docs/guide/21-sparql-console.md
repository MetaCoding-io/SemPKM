# SPARQL Console

The SPARQL Console lets you query your entire knowledge base using SPARQL 1.1 -- the standard query language for RDF data. Whether you want to explore how your data is structured, find objects matching specific criteria, or investigate relationships between items, the console gives you direct read access to the triplestore.

## Getting Started

### Opening the Console

Press **Alt+J** to open the bottom panel, then click the **SPARQL** tab. The console opens with a default query that lists all triples in your knowledge base:

```sparql
SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 20
```

You can also access the standalone SPARQL page by navigating to `/sparql` in the sidebar.

### Running Your First Query

1. Type or paste a SPARQL SELECT query in the editor pane
2. Press **Ctrl+Enter** or click the **Run** button to execute
3. Results appear in the table below the editor, with one column per SPARQL variable

If the query has a syntax error, an error message appears in place of results. Check for missing braces, misspelled keywords, or undeclared prefixes.

## The Editor

The SPARQL editor uses CodeMirror, providing a comfortable editing experience:

- **Syntax highlighting** -- SPARQL keywords (`SELECT`, `WHERE`, `FILTER`, `OPTIONAL`) are colored distinctly from IRIs, variables, and literals
- **Auto-indentation** -- New lines inside braces are automatically indented
- **Bracket matching** -- Matching braces and parentheses are highlighted when your cursor is next to one
- **Line numbers** -- Displayed in the left gutter for easy reference when debugging long queries

## Multi-Tab Queries

The console supports multiple query tabs, so you can work on several queries simultaneously without losing your place.

- **Create a new tab** -- Click the **+** button next to the existing tabs
- **Switch tabs** -- Click any tab to switch to its query
- **Rename a tab** -- Double-click the tab label and type a new name (e.g., "Note counts", "Person edges")
- **Close a tab** -- Click the **x** on a tab to remove it

Each tab maintains its own query text and results independently.

### Query Persistence

Your queries and tabs are automatically saved to browser localStorage (key: `sempkm-sparql`). They survive full browser close and reopen -- you will not lose work between sessions.

## Prefixes

Common prefixes are automatically injected by the server before execution -- you can use them without declaring them:

| Prefix | Namespace | Usage |
|--------|-----------|-------|
| `dcterms:` | `http://purl.org/dc/terms/` | Titles, descriptions, dates |
| `skos:` | `http://www.w3.org/2004/02/skos/core#` | Concept labels |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` | Labels, comments |
| `foaf:` | `http://xmlns.com/foaf/0.1/` | People names |
| `sempkm:` | `urn:sempkm:` | System namespace |
| `schema:` | `https://schema.org/` | Schema.org vocabulary |

Additional prefixes from your installed Mental Models are also available. You can explicitly declare prefixes at the top of your query if needed, but it is rarely necessary.

## Working with Results

Results appear in a table below the editor. Each column corresponds to a variable in your `SELECT` clause.

### Object Links

IRI values in query results that belong to your knowledge base render as clickable links. Clicking an IRI opens that object in the active editor group -- the same behavior as clicking an object in the sidebar.

### Large Result Sets

By default, queries are not limited unless you include a `LIMIT` clause. For exploratory queries, always add `LIMIT 50` or similar to avoid fetching thousands of rows. You can increase the limit once you know the result size is manageable.

## Example Queries

These examples use the Basic PKM model types (Note, Person, Project, Concept).

**List all Notes with their titles:**

```sparql
SELECT ?note ?title WHERE {
  ?note a sempkm:Note ;
        dcterms:title ?title .
}
ORDER BY ?title
```

**Find all relationships from a specific Project:**

```sparql
SELECT ?predicate ?target ?targetLabel WHERE {
  <https://example.org/data/Project/q1-planning> ?predicate ?target .
  FILTER(isIRI(?target))
  OPTIONAL { ?target dcterms:title ?t }
  OPTIONAL { ?target skos:prefLabel ?p }
  OPTIONAL { ?target foaf:name ?n }
  BIND(COALESCE(?t, ?p, ?n, STR(?target)) AS ?targetLabel)
}
```

**Count objects by type:**

```sparql
SELECT ?type (COUNT(?s) AS ?count) WHERE {
  ?s a ?type .
}
GROUP BY ?type
ORDER BY DESC(?count)
```

**Query across named graphs (include event metadata):**

```sparql
SELECT ?event ?timestamp ?opType WHERE {
  GRAPH ?event {
    ?event a sempkm:Event ;
           sempkm:timestamp ?timestamp ;
           sempkm:operationType ?opType .
  }
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
}
ORDER BY DESC(?timestamp)
LIMIT 20
```

**All objects with labels (any label property):**

```sparql
SELECT ?subject ?type ?label WHERE {
  ?subject a ?type .
  OPTIONAL { ?subject dcterms:title ?t }
  OPTIONAL { ?subject skos:prefLabel ?p }
  OPTIONAL { ?subject foaf:name ?n }
  BIND(COALESCE(?t, ?p, ?n, STR(?subject)) AS ?label)
}
ORDER BY ?type
LIMIT 50
```

## Access

The SPARQL Console is available to all authenticated users (owner, member, and guest roles). Queries are automatically scoped to your current knowledge base state (`urn:sempkm:current` graph) -- event log data does not appear in default results unless you explicitly query event named graphs.

> **For Advanced Users:** The console supports SELECT queries only. CONSTRUCT and DESCRIBE queries can be run via the SPARQL API endpoint (`/api/sparql`) directly -- see [Chapter 18: The SPARQL Endpoint](18-sparql-endpoint.md). UPDATE and DELETE operations are not supported through the console or API; all data modifications must go through the command API to ensure proper event logging, validation, and webhook dispatch. If you need to query the Lucene full-text index from SPARQL, see the `luc:matches` predicate described in [Chapter 22: Keyword Search](22-keyword-search.md).

## Graph Visualization

When a SPARQL query returns results that follow the **triple pattern** — variables named `?s`, `?p`, and `?o` (or similar subject/predicate/object columns) — the console automatically detects this and offers an interactive graph visualization alongside the standard results table.

### Table/Graph Tab Switcher

A **Table/Graph** tab switcher appears above the results area when triple-pattern results are detected. A hint reading "Triple pattern detected" confirms that the graph tab is available. Click the **Graph** tab to switch from the tabular view to the graph visualization.

### How the Graph Works

The graph visualization is powered by **Cytoscape.js** and renders query results as a node-link diagram:

- **Subject** and **object** values from each result row become **nodes** in the graph.
- **Predicate** values become **directed edges** connecting the subject node to the object node.
- Edges display the predicate label and point from subject to object.

### Layout

The graph automatically selects an appropriate layout algorithm based on the result size:

- **Small graphs** (fewer than 30 nodes): Uses the **dagre** layout, which arranges nodes in a directed tree structure. This produces clean, readable layouts for hierarchical or sparse data.
- **Larger graphs** (30 or more nodes): Uses the **fcose** (force-directed) layout, which positions nodes by simulating physical forces. Connected nodes attract each other while unconnected nodes repel, producing organic layouts that reveal clusters and communities.

### Using Graph Visualization Effectively

The graph tab is most useful for exploring relationship patterns in your knowledge base. To get triple-pattern results, structure your queries with three columns representing subject, predicate, and object:

```sparql
SELECT ?s ?p ?o WHERE {
  ?s ?p ?o .
  FILTER(isIRI(?o))
}
LIMIT 50
```

> **Tip:** Use `SELECT ?s ?p ?o WHERE { ... }` queries to visually explore how objects relate to each other. Start with a small `LIMIT` to keep the graph readable, then increase it as needed.

---

**Previous:** [Chapter 20: Production Deployment](20-production-deployment.md) | **Next:** [Chapter 22: Keyword Search](22-keyword-search.md)
