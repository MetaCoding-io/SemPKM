# Appendix D: Glossary

Alphabetical definitions of key terms used throughout the SemPKM documentation and interface.

---

**Carousel View**
A tabbed browsing interface for Mental Model views that groups table, card, and graph views into a single page with a tab strip. Each tab loads a different view of the same type's data, letting you switch between display formats without navigating away. See [Chapter 7: Browsing and Visualizing Data](07-browsing-and-visualizing.md).

**Content Negotiation**
An HTTP mechanism where the server returns different representations of a resource based on the client's `Accept` header. SemPKM uses content negotiation for WebID profiles: browsers receive an HTML page while Linked Data clients receive JSON-LD or Turtle. See [Chapter 25: WebID Profiles](25-webid-profiles.md).

**Edge**
A typed, directional relationship between two objects. Unlike a simple link, an edge carries a specific predicate (relationship type) such as `hasParticipant` or `isAbout`. Edges are first-class resources in SemPKM with their own IRIs, meaning they can carry annotation properties (like labels or timestamps) in addition to connecting a source and target. See also: Object, Property.

**Entailment**
The process of deriving new triples from existing data using ontological reasoning rules. SemPKM supports RDFS and OWL entailment (e.g., inferring that if Alice is a `Researcher` and `Researcher` is a subclass of `Person`, then Alice is also a `Person`). Configure entailment in Settings > Inference. See [Chapter 13: Settings](13-settings.md).

**Event**
An immutable, timestamped record of a change made to the knowledge base. Every mutation -- creating an object, editing a property, setting a body, creating an edge -- produces an event stored as a named graph in the triplestore. Events form the audit trail and enable undo. Events record who made the change, when it happened, and exactly which triples were added or removed. See also: Named Graph, Event Sourcing.

**Event Sourcing**
The architectural pattern used by SemPKM where every state change is stored as an immutable event rather than directly modifying the current state. The "current state" graph is a materialized view derived from replaying all events. This provides full history, undo capability, and temporal queries.

**IndieAuth**
An authentication and authorization protocol built on OAuth 2.0 that uses personal URLs (like WebID profiles) as identities. SemPKM acts as an IndieAuth provider, allowing you to sign into other IndieAuth-compatible services using your SemPKM identity. See [Chapter 26: IndieAuth](26-indieauth.md).

**Inference**
The automatic derivation of implicit facts from explicit data using ontological rules. In SemPKM, inference materializes triples such as `owl:inverseOf` relationships and `rdfs:subClassOf` hierarchies. Also called entailment. See [Chapter 13: Settings](13-settings.md).

**IRI**
Internationalized Resource Identifier. The globally unique identifier for every resource in SemPKM -- every object, every property, every type, every edge. IRIs look like URLs (e.g., `https://example.org/data/Person/alice-chen`) or URNs (e.g., `urn:sempkm:model:basic-pkm:Project`). They serve the same role as primary keys in a relational database, but are globally unique by design.

**JSON-LD**
JSON for Linking Data. The serialization format used by SemPKM for Mental Model files (ontologies, shapes, views, seed data). JSON-LD is standard JSON with a `@context` block that maps short keys to full IRIs, making it both human-readable and machine-processable as RDF.

**Lint Dashboard**
A global page that shows all validation results across every object in the knowledge base. Unlike the per-object Lint Panel, the dashboard provides a system-wide overview of data quality, groupable by type, severity, or violation message. Accessible from the sidebar under Tools. See [Chapter 14: System Health and Debugging](14-system-health-and-debugging.md).

**Lint**
The validation report for an object, displayed in the **Lint Panel** on the right side of the workspace. Linting checks the object's data against its SHACL shape and reports violations (missing required fields, invalid values, etc.). Lint is assistive -- it warns but does not block saving.

**Materialization**
The process of applying event operations to the current state graph. When a command is executed, the event store records the event and then materializes it by running SPARQL INSERT and DELETE operations against the `urn:sempkm:current` graph. The result is an up-to-date view of all objects and their current property values.

**Mental Model**
An installable package that defines a domain vocabulary for SemPKM. A Mental Model includes an ontology (types and properties), SHACL shapes (form structure and validation rules), view specifications (table, card, and graph queries), and optional seed data (starter objects). The built-in "Basic PKM" model provides Note, Concept, Project, and Person types. See also: Ontology, Shape, View.

**Named Graph**
An RDF concept where a set of triples is associated with a graph IRI. SemPKM uses named graphs extensively: the current state lives in `urn:sempkm:current`, each event occupies its own named graph, and each Mental Model's ontology, shapes, and views are stored in separate named graphs. Named graphs enable SemPKM to organize, query, and manage different sets of triples independently.

**Obsidian Import**
The built-in wizard for migrating an Obsidian vault into SemPKM. Upload a `.zip` of your vault, map Obsidian folders and tags to SemPKM types, configure property mappings, and import notes as typed objects with relationships preserved. See [Chapter 24: Obsidian Onboarding](24-obsidian-onboarding.md).

**Object**
The primary unit of data in SemPKM. An object is an RDF resource with a type (like Note, Person, or Project), a set of properties (title, status, email), and optionally a Markdown body and edges to other objects. Objects are identified by IRIs and displayed as form-based editors in the workspace.

**Ontology**
The formal definition of types (classes) and properties within a Mental Model. Written in OWL (Web Ontology Language) and serialized as JSON-LD. The ontology declares what kinds of objects can exist and what properties they can have, along with domain/range constraints and inverse relationships. See also: Mental Model, Type, Property.

**OWL**
Web Ontology Language.

**PKCE**
Proof Key for Code Exchange. A security extension to the OAuth 2.0 authorization code flow that prevents authorization code interception attacks. SemPKM's IndieAuth provider requires PKCE for all authorization requests. The client generates a random `code_verifier`, sends a hashed `code_challenge` with the authorization request, then proves possession of the original verifier when exchanging the code for a token. See [Chapter 26: IndieAuth](26-indieauth.md). A W3C standard for defining ontologies -- formal descriptions of types, properties, and their relationships. SemPKM uses OWL Class and Property declarations in Mental Model ontology files.

**Property**
A named attribute of an object. Properties can hold literal values (strings, dates, numbers, URIs) or references to other objects. In RDF terms, a property is a predicate in a subject-predicate-object triple. SemPKM distinguishes between datatype properties (literal values) and object properties (references to other resources). See also: Edge, Object.

**RDF**
Resource Description Framework. The W3C standard data model that underpins SemPKM. All data is stored as triples: subject-predicate-object statements. For example, "Alice Chen" (subject) "has job title" (predicate) "Lead Developer" (object). RDF enables flexible, schema-on-read data that can be queried, linked, and extended without migrations.

**SHACL**
Shapes Constraint Language.

**SHACL-AF Rule**
A SHACL Advanced Features rule that generates new triples from existing data. Unlike validation shapes (which check constraints), SHACL-AF rules produce inferred triples -- for example, automatically deriving a `fullName` property by concatenating `firstName` and `lastName`. SemPKM executes SHACL-AF rules as part of the inference pipeline. See [Chapter 16: The Data Model](16-data-model.md). A W3C standard for validating RDF data against a set of conditions (shapes). In SemPKM, SHACL shapes serve double duty: they define the form structure for editing objects (field names, order, groups, data types, dropdowns) and they provide validation rules (required fields, allowed values, cardinality). See also: Shape, Validation.

**Shape**
A SHACL node shape that describes the expected structure of a specific type. Each shape lists property constraints (what fields should exist, their data types, whether they are required, allowed values) and property groups (how fields are organized in the form). Shapes drive both form generation and data validation. See also: SHACL, Mental Model.

**SPARQL**
SPARQL Protocol and RDF Query Language. The standard query language for RDF data, analogous to SQL for relational databases. SemPKM uses SPARQL internally for all data retrieval and manipulation. View specifications contain SPARQL queries that power table, card, and graph views. The bottom panel includes a SPARQL console for running ad-hoc queries.

**Triple**
The atomic unit of data in RDF: a subject-predicate-object statement. For example: `<Person/alice> <foaf:name> "Alice Chen"` is a triple stating that the resource `Person/alice` has the name "Alice Chen". All data in SemPKM -- objects, properties, edges, events -- is ultimately stored as triples.

**Triplestore**
A database optimized for storing and querying RDF triples. SemPKM uses Eclipse RDF4J as its triplestore, running as a Docker container. The triplestore holds all object data, ontologies, shapes, views, event graphs, and the current state graph.

**Type**
A classification for objects, defined as an OWL class in a Mental Model's ontology. The Basic PKM model defines four types: Note, Concept, Project, and Person. Each type has associated SHACL shapes (for forms and validation) and view specifications (for browsing). When you create a new object, you choose its type.

**Validation**
The process of checking an object's data against its SHACL shape. Validation runs asynchronously after every save operation. Results appear in the Lint Panel and include violation severity (warning or error), the affected property, and a human-readable message. Validation is non-blocking -- you can always save your work regardless of validation results. See also: SHACL, Lint.

**WebID**
A personal identifier that is also a web URL pointing to a machine-readable profile document. In SemPKM, each user gets a WebID at `{APP_BASE_URL}/id/{username}` that serves both a human-readable HTML profile and Linked Data (JSON-LD/Turtle) via content negotiation. WebIDs enable decentralized identity -- you can use your SemPKM WebID to authenticate with other services via IndieAuth. See [Chapter 25: WebID Profiles](25-webid-profiles.md).

**View**
A named query-and-renderer combination that displays a collection of objects. Each view targets a specific type and uses a SPARQL query to fetch data, combined with a renderer type (table, card, or graph) to determine the visual layout. Views are defined in Mental Model bundles and appear in the Views menu. See also: Mental Model, SPARQL.

## See Also

- [Core Concepts](02-core-concepts.md) -- introductory explanation of these terms in context
- [The Data Model](16-data-model.md) -- technical details of how RDF, events, and named graphs work together

---

**Previous:** [Appendix C: Command API Reference](appendix-c-command-api-reference.md) | **Next:** [Appendix E: Troubleshooting](appendix-e-troubleshooting.md)
