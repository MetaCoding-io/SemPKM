# Chapter 16: The Data Model

SemPKM stores all of your knowledge -- Notes, Concepts, Projects, People, and the
relationships between them -- as structured data in an RDF triplestore. This chapter
explains the core data model in practical terms: how your data is represented, how
named graphs keep things organized, why all writes go through an event-sourced
command pipeline, and how SHACL validation keeps your data consistent.

You do not need to understand RDF deeply to use SemPKM day-to-day. But if you want
to write SPARQL queries, use the Command API, or build your own Mental Models,
this chapter gives you the foundation.

---

## RDF Fundamentals

### Triples

Every piece of data in SemPKM is stored as a **triple**: a three-part statement
with a subject, predicate, and object.

```
<subject>  <predicate>  <object> .
```

For example, a Note called "Meeting Notes" with an `rdfs:label` property is stored
as:

```turtle
<https://example.org/data/Note/meeting-notes>
    rdf:type  <https://example.org/data/Note> ;
    rdfs:label  "Meeting Notes" .
```

That is two triples:

| Subject | Predicate | Object |
|---------|-----------|--------|
| `.../Note/meeting-notes` | `rdf:type` | `.../Note` |
| `.../Note/meeting-notes` | `rdfs:label` | `"Meeting Notes"` |

### IRIs

Subjects and predicates are identified by **IRIs** (Internationalized Resource
Identifiers) -- essentially URLs that uniquely name things. SemPKM mints IRIs
for your objects automatically using the pattern:

```
{base_namespace}/{Type}/{slug-or-uuid}
```

For example, with the default base namespace `https://example.org/data/`:

- A Person named Alice: `https://example.org/data/Person/alice`
- A Project: `https://example.org/data/Project/q1-planning`
- An Edge: `https://example.org/data/Edge/550e8400-e29b-41d4-a716-446655440000`

Objects can have a human-readable slug (like `alice`) or fall back to a UUID.
Edges always use UUIDs.

### How SemPKM Hides the Complexity

You rarely need to think about triples or IRIs directly. The workspace presents
your data as objects with properties, bodies, and relationships -- familiar
concepts for any note-taking or knowledge management tool. The RDF layer
underneath gives you capabilities that traditional tools lack: queryable
relationships, schema validation, and standards-based interoperability.

> **Tip:** When you see a "compact IRI" like `rdfs:label` in the UI or in
> queries, that is shorthand for the full IRI
> `http://www.w3.org/2000/01/rdf-schema#label`. SemPKM automatically expands
> common prefixes for you. See the prefix table at the end of this section.

### Common Prefixes

SemPKM ships with these built-in prefix mappings. You can use them in SPARQL
queries and Command API payloads without declaring them:

| Prefix    | Namespace                                         | Usage                       |
|-----------|---------------------------------------------------|-----------------------------|
| `rdf`     | `http://www.w3.org/1999/02/22-rdf-syntax-ns#`     | Core RDF vocabulary         |
| `rdfs`    | `http://www.w3.org/2000/01/rdf-schema#`            | Labels, comments            |
| `owl`     | `http://www.w3.org/2002/07/owl#`                   | Ontology constructs         |
| `xsd`     | `http://www.w3.org/2001/XMLSchema#`                | Datatypes (string, date...) |
| `sh`      | `http://www.w3.org/ns/shacl#`                      | SHACL shapes/validation     |
| `skos`    | `http://www.w3.org/2004/02/skos/core#`             | Concept schemes             |
| `dcterms` | `http://purl.org/dc/terms/`                        | Dublin Core (modified, etc) |
| `schema`  | `https://schema.org/`                              | Schema.org vocabulary       |
| `foaf`    | `http://xmlns.com/foaf/0.1/`                       | People and social           |
| `prov`    | `http://www.w3.org/ns/prov#`                       | Provenance                  |
| `sempkm`  | `urn:sempkm:`                                      | SemPKM system namespace     |

Additional prefixes are added when Mental Models are installed, and you can
register your own user-defined prefixes. The prefix registry uses a layered
precedence: user overrides take priority over model-provided prefixes, which
take priority over built-in prefixes.

---

## Named Graphs

RDF triplestores support **named graphs** -- groups of triples identified by a
graph IRI. SemPKM uses named graphs extensively to separate different kinds of
data. Think of them as folders that keep your current state, event history, schemas,
and validation results cleanly separated.

### `sempkm:current` -- The Current State Graph

**IRI:** `urn:sempkm:current`

This is the single source of truth for the live state of your workspace. When you
view a Note, edit a Project, or browse the navigation tree, the data comes from
this graph. All SPARQL queries through the `/api/sparql` endpoint are automatically
scoped to this graph.

When a command is executed (e.g., `object.create`), the resulting triples are
**materialized** into this graph. "Materialized" means the triples are inserted
(or old values deleted and new values inserted) so the current state always
reflects the latest version of everything.

### `sempkm:events/<id>` -- Event Graphs

**IRI pattern:** `urn:sempkm:event:{uuid}`

Each write operation produces an immutable event graph. The event graph contains:

- **Metadata triples** -- the event's type, timestamp, operation type, affected
  IRIs, description, and performer information.
- **Data triples** -- the actual triples that were created or changed by the
  operation.

Event graphs are never modified after creation. Even undo operations create new
compensating events rather than altering existing ones. This makes the event log
a reliable audit trail.

### `sempkm:shapes/<modelId>` -- Shape Graphs

**IRI pattern:** `urn:sempkm:shapes:{model-id}`

When you install a Mental Model, its SHACL shapes are stored in a dedicated named
graph. Shapes define the structure of your object types -- what properties they
have, which are required, what datatypes are expected, and how forms are rendered
in the UI.

### `sempkm:ontology/<modelId>` -- Ontology Graphs

**IRI pattern:** `urn:sempkm:ontology:{model-id}`

Mental Models can include OWL ontology definitions (class hierarchies, property
definitions, domain/range constraints). These are stored in their own named graph,
separate from shapes.

### `sempkm:validation/<id>` -- Validation Report Graphs

**IRI pattern:** Determined by the validation report IRI.

Each time SHACL validation runs, the results are stored in a validation report
graph. A shared `urn:sempkm:validations` graph holds summary triples (conforms,
violation count, warning count, etc.) for quick polling.

> **Note:** The separation of named graphs is what allows SemPKM to give you
> a clean view of your data via SPARQL while keeping the event history, schemas,
> and validation results accessible when you need them.

---

## Event-Sourced Architecture

SemPKM uses an **event-sourced architecture** for all data writes. This is a
deliberate design choice with significant benefits for a knowledge management tool.

### How It Works

1. **You issue a command.** Whether you click Save in the editor, submit a form, or
   call the Command API, the operation is expressed as a command (e.g.,
   `object.patch`).

2. **The handler builds an Operation.** The command handler computes the exact
   triples to insert and delete. It does not touch the triplestore directly.

3. **EventStore.commit() runs atomically.** In a single transaction:
   - An immutable event named graph is created with metadata and data triples.
   - The current state graph (`urn:sempkm:current`) is updated: old values are
     deleted first, then new values are inserted.
   - If anything fails, the entire transaction rolls back -- no partial writes.

4. **Async validation is triggered.** After the commit succeeds, a validation job
   is enqueued. The validation queue runs SHACL validation in the background
   without blocking the UI.

### Why Not Direct Edits?

You might wonder why SemPKM does not allow direct SPARQL UPDATE statements against
the current state graph. The event-sourced approach provides:

- **Complete audit trail.** Every change is recorded with who made it, when, and
  what the change was. You can answer "who changed this property last Tuesday?"
  by browsing the Event Log.

- **Undo.** Because events record both the new values and (by querying earlier
  events) the old values, the system can build compensating events that restore
  previous state.

- **Atomicity.** Each command is all-or-nothing. If you submit a batch of commands,
  they all succeed or all fail together. You never end up with half-applied changes.

- **Sync readiness.** The immutable event log is a natural foundation for multi-device
  sync, conflict resolution, and replication in future versions.

- **Debugging.** When something looks wrong, the event log tells you exactly how
  the data got to its current state.

### The Materialization Pattern

The term "materialization" refers to applying an event's changes to the current
state graph. For each operation, the system computes two lists:

- **Materialize deletes** -- triple patterns to remove from `urn:sempkm:current`.
  For patch operations, these use SPARQL variables (like `?old_0`) to match
  whatever the current value is.
- **Materialize inserts** -- concrete triples to add to `urn:sempkm:current`.

Deletes always run before inserts within a transaction. This ensures that variable
patterns only match existing values, not values that are about to be inserted.

---

## SHACL and Validation

### What Is SHACL?

SHACL (Shapes Constraint Language) is a W3C standard for describing and validating
the structure of RDF data. In SemPKM, SHACL shapes serve a dual purpose:

1. **Form generation.** SHACL shapes define what properties an object type has,
   their labels, datatypes, whether they are required, and their display order.
   The UI reads these shapes to render forms automatically.

2. **Data validation.** After each write, SemPKM runs pyshacl validation against
   all installed shapes. Violations, warnings, and informational messages appear
   in the **Lint panel** for each object.

### How Validation Runs

Validation is **asynchronous and non-blocking**. Here is the flow:

1. A command commits successfully and the current state is updated.
2. A validation job is enqueued in the `AsyncValidationQueue`.
3. The background worker picks up the job and runs full SHACL validation:
   - Fetches the entire current state graph via `CONSTRUCT`.
   - Loads all installed SHACL shapes.
   - Runs `pyshacl.validate()` (in a thread, since it is CPU-bound).
   - Parses the results into a `ValidationReport`.
   - Stores the report in the triplestore and caches a summary in memory.
4. The Lint panel polls for the latest report and displays results.

### Queue Coalescing

If multiple commands are executed rapidly (e.g., a batch operation), the validation
queue **coalesces** -- it drains pending jobs and runs validation only for the
latest event. Since validation checks the full current state, intermediate
validations would produce obsolete results anyway. This prevents unnecessary work.

### Assistive, Not Blocking

Validation in SemPKM is **assistive**: violations appear in the Lint panel as
feedback, but they do not prevent you from saving. You can create objects that
do not yet satisfy all shape constraints and fix them later. This is intentional
-- a PKM tool should not block your flow of thought.

> **Tip:** Open the Lint panel for any object to see its current validation
> status. Violations show what needs attention, warnings flag potential issues,
> and informational messages offer suggestions.

---

## Next Steps

Now that you understand the data model, you can use the Command API to automate
writes. Continue to [The Command API](17-command-api.md).
