# SPARQL Console

The SPARQL Console lets you query your entire knowledge base using SPARQL 1.1 — the standard query language for RDF data.

## Opening the Console

Press **Ctrl+J** to open the bottom panel, then click the **SPARQL** tab. The console opens with a default query showing all objects in your knowledge base.

## Running Queries

1. Type or paste a SPARQL SELECT query in the editor pane
2. Press **Ctrl+Enter** or click the **Run** button to execute
3. Results appear in the table below the editor

The editor supports syntax highlighting, prefix autocomplete, and multi-tab queries.

## Prefixes

Common prefixes are automatically injected by the server before execution — you can use them without declaring them:

- `dcterms:` — Dublin Core terms (titles, descriptions)
- `skos:` — SKOS concepts (prefLabels)
- `rdfs:` — RDF Schema (labels)
- `foaf:` — FOAF (names)
- `sempkm:` — SemPKM system namespace
- `schema:` — Schema.org

## Query Persistence

Your queries and tabs are automatically saved to browser localStorage (key: `sempkm-sparql`). They survive full browser close and reopen — you will not lose work between sessions.

## Object Links

IRI values in query results that belong to your knowledge base render as clickable links. Clicking an IRI opens that object in the active editor group — the same behavior as clicking an object in the sidebar.

## Access

The SPARQL Console is available to all authenticated users (owner, member, and guest roles). Queries are automatically scoped to your current knowledge base state — event log data does not appear in results.

## Example Queries

**All objects with labels:**
```sparql
SELECT ?subject ?type ?label WHERE {
  ?subject a ?type .
  OPTIONAL { ?subject dcterms:title ?t }
  OPTIONAL { ?subject skos:prefLabel ?p }
  BIND(COALESCE(?t, ?p, STR(?subject)) AS ?label)
}
ORDER BY ?type
LIMIT 50
```

**All notes:**
```sparql
SELECT ?note ?title WHERE {
  ?note a sempkm:Note ;
        dcterms:title ?title .
}
```

---

**Previous:** [Chapter 20: Production Deployment](20-production-deployment.md) | **Next:** [Chapter 22: Keyword Search](22-keyword-search.md)
