# Appendix F: FAQ

Frequently asked questions about SemPKM, organized by topic.

---

## Data and Storage

### How is my data stored?

SemPKM stores all knowledge data as RDF triples in an Eclipse RDF4J triplestore (a specialized graph database). Every object, property, relationship, and event is represented as a set of subject-predicate-object triples organized into named graphs:

- **Current state graph** (`urn:sempkm:current`) -- the live, up-to-date view of all your objects and their current property values.
- **Event graphs** -- one named graph per mutation event, forming an immutable audit trail.
- **Model graphs** -- separate named graphs for each Mental Model's ontology, shapes, and views.

User accounts, sessions, and application settings are stored in a separate SQL database (SQLite by default, PostgreSQL for production).

### Is there data lock-in?

No. SemPKM is built on open standards specifically to avoid lock-in:

- **RDF** is a W3C standard data format supported by hundreds of tools and databases.
- **SPARQL** lets you query and export your data in standard formats (N-Triples, Turtle, JSON-LD, N-Quads).
- **RDF4J** is open-source and supports standard RDF export via its REST API.

You can export your entire knowledge base at any time:

```bash
curl -H "Accept: application/n-quads" \
  http://localhost:8001/rdf4j-server/repositories/sempkm/statements \
  > my-data-export.nq
```

The exported N-Quads file can be imported into any other RDF-compatible tool or triplestore.

### Can I import data from other tools?

SemPKM does not currently have a built-in import wizard for other tools (like Obsidian vaults or Notion exports). However, because data is written through the Command API, you can build import scripts that:

1. Parse your source data (Markdown files, CSV, JSON).
2. Map it to your Mental Model's types and properties.
3. Submit `object.create` and `edge.create` commands via `POST /api/commands`.

For RDF data specifically, you could load it directly into the triplestore via the RDF4J REST API, though you would need to ensure it follows SemPKM's naming conventions and includes proper type triples.

> **Tip:** See [Appendix C: Command API Reference](appendix-c-command-api-reference.md) for the full API specification to build import scripts against.

---

## Compatibility

### Can I use SemPKM with Obsidian?

Not directly -- SemPKM and Obsidian use fundamentally different storage models. Obsidian stores data as Markdown files in a local folder with `[[wiki-links]]` for connections. SemPKM stores data as typed RDF triples in a triplestore with formally defined relationships.

However, there are potential integration points:

- **Export:** You could write a script that queries SemPKM via SPARQL and generates Markdown files with frontmatter and wiki-links for use in Obsidian.
- **Import:** Conversely, you could parse an Obsidian vault and create SemPKM objects via the Command API.
- **Parallel use:** Some users keep both tools -- Obsidian for quick daily capture, SemPKM for structured long-term knowledge.

The key difference is that SemPKM relationships are typed and queryable (`hasParticipant`, `isAbout`), while Obsidian links are untyped. An import from Obsidian would need to classify each link by type as part of the migration process.

### Does SemPKM work on mobile?

SemPKM's web interface is designed for desktop use with a multi-pane IDE-style layout. While it loads in mobile browsers, the three-column workspace (Explorer, Editor, Details) does not adapt well to small screens. Mobile support is not a current priority, but the API endpoints work fine from any HTTP client, so a dedicated mobile app could be built against the Command API.

---

## Users and Collaboration

### Does SemPKM support multiple users?

Yes. SemPKM has built-in multi-user support with two roles:

- **Owner** -- full access to all features including user management, model installation, settings, and webhooks.
- **Member** -- can create, edit, and browse objects and edges, but cannot manage users or install models.

The first user created during setup becomes the owner. Additional users can be invited via the user management interface.

> **Note:** All users currently share a single knowledge base. There are no per-user workspaces or access control on individual objects. Multi-tenancy (separate knowledge bases per team or organization) is planned for a future version.

### How does authentication work?

SemPKM uses passwordless authentication via magic links. When a user wants to log in:

1. They enter their email address.
2. SemPKM sends a magic link (a one-time URL with a signed token) to that email.
3. Clicking the link creates an authenticated session.

If SMTP is not configured (common in development), the magic link token is displayed directly in the browser response or API logs instead of being emailed.

Sessions are cookie-based and last 30 days by default (configurable via `SESSION_DURATION_DAYS`).

---

## Mental Models

### Can I write my own Mental Model?

Absolutely -- this is one of SemPKM's core design goals. A Mental Model is a directory containing:

- A `manifest.yaml` with metadata and configuration
- An ontology file (OWL classes and properties in JSON-LD)
- A shapes file (SHACL constraints for form generation and validation)
- A views file (SPARQL-powered table, card, and graph views)
- Optionally, a seed data file with starter objects

See [Chapter 19: Creating Mental Models](19-creating-mental-models.md) for a complete walkthrough with examples.

### Can I install multiple Mental Models at the same time?

Yes. Each Mental Model operates in its own namespace and named graph. You can install "Basic PKM" alongside a custom "Research" model, for example. Objects from different models can coexist and even reference each other, though cross-model relationships require using full IRIs.

### What happens to my data if I remove a Mental Model?

Removing a Mental Model deletes its ontology, shapes, and view definitions from the triplestore. However, objects you created using that model's types remain in the current state graph. They will still exist as RDF data but will lose their form rendering (no shapes means no auto-generated forms) and will not appear in model-specific views. You can still access them via SPARQL.

---

## Concepts

### What is the difference between an Edge and a property?

Both edges and properties represent relationships, but they serve different purposes:

**Properties** are direct predicate-value pairs on an object. When you set a Project's status to "active", that is a property -- a simple `(Project, bpkm:status, "active")` triple. Properties hold literal values (strings, dates, numbers, URIs) or direct references to other objects.

**Edges** are first-class relationship resources with their own IRIs. When you link a Project to a Person via `hasParticipant`, SemPKM creates an Edge resource with `sempkm:source`, `sempkm:target`, and `sempkm:predicate` properties. This means edges can carry their own annotation properties (labels, timestamps, weights, notes) beyond just connecting two objects.

In practice:

- Use **properties** for simple attributes and straightforward references (a Note's "Related Project" field).
- Use **edges** when the relationship itself has meaningful metadata (e.g., "Alice joined this project on January 15 as Lead Developer").

The form-based UI handles both transparently -- reference fields in forms create edges behind the scenes.

### What is the difference between a Type and a Shape?

A **Type** (OWL class) declares that something *exists* in your domain. Saying `bpkm:Project` is a type means "Projects are a thing in this knowledge base."

A **Shape** (SHACL node shape) declares what a type *looks like* -- what properties it should have, which are required, what values are allowed, and how fields are ordered in the form. The shape `bpkm:ProjectShape` says "A Project should have a title (required), a status (dropdown with four options), a priority, dates, participants, and notes."

Types live in the ontology file; shapes live in the shapes file. They are connected by `sh:targetClass` -- the shape points to the type it describes.

### What are Named Graphs?

Named Graphs are an RDF concept where a set of triples is given a unique identifier (an IRI). Think of it as a "folder" or "partition" for triples. SemPKM uses named graphs to organize data:

- `urn:sempkm:current` -- the current state of all objects
- `urn:sempkm:event:2026-01-15T09:00:00Z:abc123` -- a single event's data
- `urn:sempkm:model:basic-pkm:ontology` -- the Basic PKM ontology triples

Named graphs allow SemPKM to update, query, and manage different data sets independently. For example, replaying events works by iterating over event named graphs in order.

---

## Operations

### How do I back up my data?

See the "Backup and Restore" section in [Chapter 20: Production Deployment](20-production-deployment.md). In short:

1. Back up the RDF4J triplestore volume (all object and event data).
2. Back up the SQL database (user accounts and settings).

### How do I reset everything and start fresh?

- **Reset users and settings only:** Run `./scripts/reset-instance.sh`. This preserves triplestore data (objects, events) but wipes user accounts and the setup token.
- **Full reset including data:** Run `docker compose down -v` to remove all Docker volumes, then `docker compose up -d` to start fresh.

### Can I use SemPKM without Docker?

SemPKM is designed to run as a Docker Compose stack for simplicity. Running it without Docker is possible but requires manual setup:

1. Install and configure RDF4J Server separately.
2. Install Python 3.12+ and the backend dependencies.
3. Serve the frontend static files via any web server.
4. Set environment variables to point to your RDF4J instance.

This is not officially supported and is recommended only for development or advanced users who need a custom deployment.

## See Also

- [What is SemPKM?](01-what-is-sempkm.md) -- introduction and overview
- [Core Concepts](02-core-concepts.md) -- detailed explanation of types, objects, edges, and events
- [Appendix D: Glossary](appendix-d-glossary.md) -- term definitions
- [Appendix E: Troubleshooting](appendix-e-troubleshooting.md) -- common issues and solutions
