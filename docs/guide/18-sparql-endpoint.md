# Chapter 18: The SPARQL Endpoint

SPARQL is the standard query language for RDF data. SemPKM exposes a read-only
SPARQL endpoint that lets you query your knowledge base directly -- list objects
by type, find items by property, traverse relationship chains, and compute
aggregates. You can use SPARQL from the built-in console in the Debug panel or
via the HTTP API from external tools and scripts.

---

## Accessing SPARQL

### The Debug Console

The quickest way to run SPARQL queries is the built-in **SPARQL console** available
in the Debug panel of the workspace. Type your query, press Execute, and see the
results rendered as a table.

<!-- Screenshot: SPARQL console in the Debug panel with a sample query and results -->

### The HTTP API

For scripting and integration, SemPKM provides a SPARQL endpoint at `/api/sparql`.
It supports both GET and POST requests.

**GET** -- query as a URL parameter:

```bash
curl "http://localhost:8000/api/sparql?query=SELECT%20%3Fs%20%3Fp%20%3Fo%20WHERE%20%7B%20%3Fs%20%3Fp%20%3Fo%20%7D%20LIMIT%2010" \
  -b cookies.txt
```

**POST (form-encoded)** -- standard SPARQL Protocol:

```bash
curl -X POST http://localhost:8000/api/sparql \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -b cookies.txt \
  -d 'query=SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10'
```

**POST (JSON body)** -- convenience format:

```bash
curl -X POST http://localhost:8000/api/sparql \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
  }'
```

All three methods require authentication via the `sempkm_session` cookie. See
[The Command API](17-command-api.md) for how to obtain a session for scripting.

---

## Query Basics

### Automatic Graph Scoping

By default, all queries are automatically scoped to the **current state graph**
(`urn:sempkm:current`). SemPKM injects a `FROM <urn:sempkm:current>` clause before
the `WHERE` keyword so you only see your live data -- not internal event graphs,
shape graphs, or validation reports.

This means you can write simple queries like:

```sparql
SELECT ?note ?label
WHERE {
  ?note a <https://example.org/data/Note> ;
        rdfs:label ?label .
}
```

And you will only get results from your current workspace state. You do not need to
add `GRAPH` or `FROM` clauses yourself.

If your query already contains a `FROM` or `GRAPH` clause, SemPKM leaves it
unchanged -- you are explicitly controlling the graph scope.

> **Tip:** For advanced debugging, the JSON POST format accepts an `all_graphs`
> parameter. Setting `"all_graphs": true` bypasses the automatic scoping and queries
> across all named graphs, including event graphs and shapes. Use this for
> troubleshooting, not for regular queries.

### Automatic Prefix Injection

SemPKM automatically prepends `PREFIX` declarations for all common prefixes
(rdf, rdfs, owl, xsd, sh, skos, dcterms, schema, foaf, prov, sempkm) if they
are not already declared in your query. This means you can use prefixed names
like `rdfs:label` or `schema:email` without writing out the `PREFIX` lines:

```sparql
SELECT ?person ?name
WHERE {
  ?person a <https://example.org/data/Person> ;
          rdfs:label ?name .
}
```

The above works without declaring `PREFIX rdfs: <...>` -- SemPKM injects it
automatically.

### Result Format

The endpoint returns results in `application/sparql-results+json` format, the
standard JSON serialization for SPARQL query results. The structure is:

```json
{
  "head": {
    "vars": ["person", "name"]
  },
  "results": {
    "bindings": [
      {
        "person": {
          "type": "uri",
          "value": "https://example.org/data/Person/alice"
        },
        "name": {
          "type": "literal",
          "value": "Alice Johnson"
        }
      }
    ]
  }
}
```

Each binding is an object with variable names as keys and RDF term descriptions
as values. The `type` field indicates whether the value is a `uri`, `literal`, or
`bnode` (blank node).

---

## Example Queries

The following examples use the Basic PKM Mental Model types (Note, Concept,
Project, Person) to illustrate common query patterns.

### List All Objects of a Type

Find all Notes in your workspace:

```sparql
SELECT ?note ?label
WHERE {
  ?note a <https://example.org/data/Note> ;
        rdfs:label ?label .
}
ORDER BY ?label
```

### Find Objects by Property Value

Find a Person by email address:

```sparql
SELECT ?person ?name
WHERE {
  ?person a <https://example.org/data/Person> ;
          rdfs:label ?name ;
          schema:email "alice@example.com" .
}
```

Find all Projects created after a specific date:

```sparql
SELECT ?project ?label ?created
WHERE {
  ?project a <https://example.org/data/Project> ;
           rdfs:label ?label ;
           schema:dateCreated ?created .
  FILTER(?created > "2026-01-01"^^xsd:date)
}
ORDER BY DESC(?created)
```

### Search by Label (Text Matching)

Find all objects whose label contains "planning" (case-insensitive):

```sparql
SELECT ?obj ?label
WHERE {
  ?obj rdfs:label ?label .
  FILTER(CONTAINS(LCASE(?label), "planning"))
}
```

### Traverse Relationships

Find all People linked to a specific Project through edges:

```sparql
SELECT ?person ?personLabel ?edgeLabel
WHERE {
  ?edge a sempkm:Edge ;
        sempkm:source ?person ;
        sempkm:target <https://example.org/data/Project/q1-planning> ;
        sempkm:predicate schema:memberOf .
  ?person rdfs:label ?personLabel .
  OPTIONAL { ?edge rdfs:label ?edgeLabel }
}
```

Find all objects connected to a given object in either direction:

```sparql
SELECT ?related ?label ?predicate
WHERE {
  {
    ?edge a sempkm:Edge ;
          sempkm:source <https://example.org/data/Person/alice> ;
          sempkm:target ?related ;
          sempkm:predicate ?predicate .
  }
  UNION
  {
    ?edge a sempkm:Edge ;
          sempkm:target <https://example.org/data/Person/alice> ;
          sempkm:source ?related ;
          sempkm:predicate ?predicate .
  }
  ?related rdfs:label ?label .
}
```

### Count Objects by Type

Get a summary of how many objects of each type exist:

```sparql
SELECT ?type (COUNT(?obj) AS ?count)
WHERE {
  ?obj a ?type .
}
GROUP BY ?type
ORDER BY DESC(?count)
```

### Find Objects with Bodies

List all Notes that have Markdown body content:

```sparql
SELECT ?note ?label (STRLEN(?body) AS ?bodyLength)
WHERE {
  ?note a <https://example.org/data/Note> ;
        rdfs:label ?label ;
        sempkm:body ?body .
}
ORDER BY DESC(?bodyLength)
```

### Find Recently Modified Objects

List the 10 most recently modified objects:

```sparql
SELECT ?obj ?label ?modified
WHERE {
  ?obj rdfs:label ?label ;
       dcterms:modified ?modified .
}
ORDER BY DESC(?modified)
LIMIT 10
```

### Find Unlinked Objects

Find objects that have no outbound or inbound edges (isolated nodes):

```sparql
SELECT ?obj ?label
WHERE {
  ?obj rdfs:label ?label .
  FILTER NOT EXISTS {
    ?edge a sempkm:Edge ;
          sempkm:source ?obj .
  }
  FILTER NOT EXISTS {
    ?edge2 a sempkm:Edge ;
           sempkm:target ?obj .
  }
}
```

---

## Limitations

### Read-Only by Design

The SPARQL endpoint is **read-only**. You cannot execute `INSERT`, `DELETE`,
`LOAD`, or any other SPARQL Update operations through this endpoint. Attempting
to do so will result in an error.

This is intentional: all writes must go through the [Command API](17-command-api.md)
to preserve the event-sourced architecture. Direct SPARQL updates would bypass
the event log, breaking the audit trail, undo capability, and validation pipeline.

If you need to write data programmatically, use the Command API (`POST /api/commands`).

### Query Performance

Queries run against the RDF4J triplestore. For most knowledge bases (thousands to
tens of thousands of triples), queries execute in milliseconds. If you are working
with a very large dataset:

- Use `LIMIT` to cap result set size.
- Avoid unbound triple patterns like `SELECT * WHERE { ?s ?p ?o }` without filters.
- Use specific type filters (`?x a <Type>`) to narrow the search space.

> **Warning:** The `all_graphs` parameter bypasses graph scoping and queries
> across all named graphs, including the potentially large event log. Use it
> sparingly and always with `LIMIT` to avoid slow queries.

---

## Next Steps

You now have the tools to both read (SPARQL) and write (Command API) your SemPKM
data programmatically. To learn how to define your own object types, properties,
and validation rules, continue to
[Creating Mental Models](19-creating-mental-models.md).
