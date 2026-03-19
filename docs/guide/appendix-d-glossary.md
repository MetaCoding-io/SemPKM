# Appendix D: Glossary

Alphabetical definitions of key terms used throughout the SemPKM documentation and interface.

---

**ABox**
(Assertional Box) The set of individual instances (objects) in a knowledge base, as opposed to the class definitions (TBox).

**API Surface**
The set of structured JSON endpoints that external clients — browser extensions, mobile apps, CLI tools, and integrations — use to interact with a SemPKM instance. Includes instance discovery, type listing, SHACL shapes, and context query. See [Chapter 31: API Surface](31-api-surface.md).

**API Token**
A secret key generated in the Admin panel that allows external clients (like the browser extension) to authenticate with your SemPKM instance without a session cookie. Tokens are created at Settings > API Keys and shown only once. See [Chapter 31: API Surface](31-api-surface.md) and [Chapter 32: Browser Extension](32-browser-extension.md).

**App Contribution**
A UI element an app contributes to the workspace: right-pane sections, views, command palette entries, or object renderer overrides. Declared in the manifest's `ui.contributions` section. See [Chapter 29: App Platform](29-app-platform.md).

**App Manifest**
The `manifest.yaml` file in an app's root directory that declares its identity, dependencies, permissions, tasks, frontend assets, and UI contributions. The platform validates the manifest at install time using a Pydantic schema. See [Chapter 29: App Platform](29-app-platform.md).

**App Platform**
The subsystem that manages third-party and first-party Python applications. Apps run as sandboxed subprocesses communicating with the platform via HTTP over unix domain sockets. See [Chapter 29: App Platform](29-app-platform.md).

**App Sandbox**
The isolation boundary for each app: a separate Python subprocess with its own virtual environment, communicating with the platform only through a scoped HTTP API. Apps cannot access platform internals directly. See [Chapter 29: App Platform](29-app-platform.md).

**App SDK**
The `sempkm-app-sdk` Python package that provides the `App` class, `AppContext`, and scoped clients for building SemPKM applications. Installed automatically into each app's virtual environment. See [Chapter 29: App Platform](29-app-platform.md).

**Argument** (Research Workflow)
A structured reasoning unit that synthesizes claims and evidence to address a research question. Each argument presents a thesis supported by referenced claims and evidence items. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**Bidirectional Sync**
A sync mode where changes flow in both directions between two systems. In Linear Sync, bidirectional mode pushes SemPKM task changes back to Linear in addition to pulling Linear issues. See [Chapter 34: Linear Sync](34-linear-sync.md).

**Block**
A content unit within a dashboard. Six types: view-embed, markdown, object-embed, create-form, sparql-result, and divider. Each block occupies a named slot in the dashboard's grid layout. See [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md).

**Body Diff**
An incremental change record for object body content. When editing an existing body, SemPKM stores only the unified diff (additions and deletions) rather than the full replacement text. The event log renders body diffs with green (additions) and red (deletions) highlighting. See [Chapter 15: Understanding the Event Log](15-event-log.md).

**Browser Extension**
A Chrome/Firefox extension that captures typed, schema-validated objects from any web page directly into your SemPKM knowledge graph. Supports SHACL-driven forms, auto-population from page metadata and schema.org JSON-LD, relationship creation, and keyboard shortcuts. See [Chapter 32: Browser Extension](32-browser-extension.md).

**Carousel View**
A tabbed browsing interface for Mental Model views that groups table, card, and graph views into a single page with a tab strip. Each tab loads a different view of the same type's data, letting you switch between display formats without navigating away. See [Chapter 7: Browsing and Visualizing Data](07-browsing-and-visualizing.md).

**Claim** (Research Workflow)
A specific assertion or proposition extracted from a paper, with a confidence level ranging from established to refuted. Claims accumulate supporting and refuting evidence over time. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**Company** (Personal CRM)
An organization entity representing a business your contacts work at. Tracks industry, size, and website to provide context for relationships. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**Contact** (Personal CRM)
A person in your professional or personal network. Tracks name, email, role, company affiliation, and interaction history. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**Content Negotiation**
An HTTP mechanism where the server returns different representations of a resource based on the client's `Accept` header. SemPKM uses content negotiation for WebID profiles: browsers receive an HTML page while Linked Data clients receive JSON-LD or Turtle. See [Chapter 25: WebID Profiles](25-webid-profiles.md).

**Context Badge**
The extension icon badge showing the count of related objects found for the current page. Appears ~2 seconds after page load when auto-context is enabled. A number (teal) indicates matches found; "!" (red) indicates a query error. See [Chapter 33: Context Overlay](33-context-overlay.md).

**Context Overlay**
The browser extension feature that shows related objects from your SemPKM knowledge graph when browsing any web page. Includes the context badge and knowledge sidebar. See [Chapter 33: Context Overlay](33-context-overlay.md).

**Context Query**
An API endpoint (`POST /api/context-query`) that finds objects in the knowledge graph related to a given page context. Accepts a URL, title, and/or keywords; returns matching objects via exact URL matching (SPARQL) and full-text keyword search (LuceneSail FTS). Used primarily by browser extensions to surface related knowledge while browsing. See [Chapter 31: API Surface](31-api-surface.md).

**Cross-View Context**
A dashboard mechanism where selecting a row in one block filters data in other blocks. The source block emits a context IRI on row click; consumer blocks bind it to a SPARQL variable and re-fetch their data. See [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md).

**Dashboard**
A configurable multi-block layout page that combines views, markdown, object embeds, forms, and SPARQL results into a single workspace tab. Five layout templates arrange blocks in a CSS Grid. See [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md).

**Deal** (Personal CRM)
A business opportunity tracked through a pipeline from lead through qualification, proposal, and negotiation to won or lost. Deals link to contacts and companies. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**Edge**
A typed, directional relationship between two objects. Unlike a simple link, an edge carries a specific predicate (relationship type) such as `hasParticipant` or `isAbout`. Edges are first-class resources in SemPKM with their own IRIs, meaning they can carry annotation properties (like labels or timestamps) in addition to connecting a source and target. See also: Object, Property.

**Embed Node**
A canvas node that displays live content from another part of SemPKM (view, dashboard, SPARQL result, or object) inside an iframe. Embeds are interactive and update in real-time. Maximum 8 per canvas. See [Chapter 27: Spatial Canvas](27-spatial-canvas.md).

**Entailment**
The process of deriving new triples from existing data using ontological reasoning rules. SemPKM supports RDFS and OWL entailment (e.g., inferring that if Alice is a `Researcher` and `Researcher` is a subclass of `Person`, then Alice is also a `Person`). Configure entailment in Settings > Inference. See [Chapter 13: Settings](13-settings.md).

**Evidence** (Research Workflow)
Empirical data, experimental results, or observations that support or refute research claims. Each piece of evidence has a type (e.g., empirical-data, case-study) and a strength assessment (strong through preliminary). See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**Event**
An immutable, timestamped record of a change made to the knowledge base. Every mutation -- creating an object, editing a property, setting a body, creating an edge -- produces an event stored as a named graph in the triplestore. Events form the audit trail and enable undo. Events record who made the change, when it happened, and exactly which triples were added or removed. See also: Named Graph, Event Sourcing.

**Event Sourcing**
The architectural pattern used by SemPKM where every state change is stored as an immutable event rather than directly modifying the current state. The "current state" graph is a materialized view derived from replaying all events. This provides full history, undo capability, and temporal queries.

**Favorites**
Objects starred by the user for quick access. Shown in the FAVORITES section of the Explorer panel.

**FleetingNote** (Zettelkasten+)
A quick-capture note in the Zettelkasten workflow — the entry point for raw ideas and thoughts that will be processed later into literature or permanent notes. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**Gist**
A minimalist upper ontology (v14.0.0) by Semantic Arts that provides foundational classes and properties. Auto-loaded in SemPKM as the semantic foundation for all Mental Models.

**GitHub Sync**
A SemPKM app that synchronizes GitHub Issues and Pull Requests with `bpkm:Task` objects. Supports pull sync (GitHub → SemPKM), push sync (SemPKM → GitHub), and bidirectional mode. PRs that reference issues are linked via `bpkm:dependsOn` edges. See [Chapter 35: GitHub Sync](35-github-sync.md).

**IndieAuth**
An authentication and authorization protocol built on OAuth 2.0 that uses personal URLs (like WebID profiles) as identities. SemPKM acts as an IndieAuth provider, allowing you to sign into other IndieAuth-compatible services using your SemPKM identity. See [Chapter 26: IndieAuth](26-indieauth.md).

**Inference**
The automatic derivation of implicit facts from explicit data using ontological rules. In SemPKM, inference materializes triples such as `owl:inverseOf` relationships and `rdfs:subClassOf` hierarchies. Also called entailment. See [Chapter 13: Settings](13-settings.md).

**Interaction** (Personal CRM)
A recorded touchpoint with a contact — meetings, calls, emails, coffees, or conferences. Interactions build a contact's history and trigger follow-up tracking. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**Instance Discovery**
The `GET /.well-known/sempkm` endpoint that returns a JSON document describing a SemPKM instance — its version, available API endpoints, supported authentication methods, and enabled capabilities. External clients should call this endpoint first to learn how to interact with the instance. See [Chapter 31: API Surface](31-api-surface.md).

**IRI**
Internationalized Resource Identifier. The globally unique identifier for every resource in SemPKM -- every object, every property, every type, every edge. IRIs look like URLs (e.g., `https://example.org/data/Person/alice-chen`) or URNs (e.g., `urn:sempkm:model:basic-pkm:Project`). They serve the same role as primary keys in a relational database, but are globally unique by design.

**JSON-LD**
JSON for Linking Data. The serialization format used by SemPKM for Mental Model files (ontologies, shapes, views, seed data). JSON-LD is standard JSON with a `@context` block that maps short keys to full IRIs, making it both human-readable and machine-processable as RDF.

**Knowledge Sidebar**
The side panel (Chrome) or sidebar (Firefox) showing related objects from SemPKM grouped by type, with actions to open, link, or add evidence. Opened via Alt+K or from the extension popup. See [Chapter 33: Context Overlay](33-context-overlay.md).

**Layout** (dashboard)
The CSS Grid template that arranges blocks on a dashboard. Five options: single, sidebar-main, grid-2x2, grid-3, and top-bottom. Each layout defines named slots where blocks are placed. See [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md).

**LiteratureNote** (Zettelkasten+)
A note that summarizes a key idea from a source in your own words. Each literature note references a single source and preserves the original quote for attribution. Part of the Zettelkasten provenance chain. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**Linear Sync**
A SemPKM app that synchronizes Linear project management issues with `bpkm:Task` objects. Supports pull sync (Linear → SemPKM), push sync (SemPKM → Linear), and bidirectional mode. See [Chapter 34: Linear Sync](34-linear-sync.md).

**Lint Dashboard**
A global page that shows all validation results across every object in the knowledge base. Unlike the per-object Lint Panel, the dashboard provides a system-wide overview of data quality, groupable by type, severity, or violation message. Accessible from the sidebar under Tools. See [Chapter 14: System Health and Debugging](14-system-health-and-debugging.md).

**Lint**
The validation report for an object, displayed in the **Lint Panel** on the right side of the workspace. Linting checks the object's data against its SHACL shape and reports violations (missing required fields, invalid values, etc.). Lint is assistive -- it warns but does not block saving.

**Materialization**
The process of applying event operations to the current state graph. When a command is executed, the event store records the event and then materializes it by running SPARQL INSERT and DELETE operations against the `urn:sempkm:current` graph. The result is an up-to-date view of all objects and their current property values.

**Mental Model**
An installable package that defines a domain vocabulary for SemPKM. A Mental Model includes an ontology (types and properties), SHACL shapes (form structure and validation rules), view specifications (table, card, and graph queries), and optional seed data (starter objects). The built-in "Basic PKM" model provides Note, Concept, Project, and Person types. See also: Ontology, Shape, View.

**Milestone** (Basic PKM v2.0)
A project phase that groups related tasks toward a deliverable or deadline. Milestones have a target date and status (planned, active, completed, cancelled). See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

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

**Paper** (Research Workflow)
An academic paper, journal article, preprint, or other publication in the Research Workflow model. Papers are the source material from which claims are extracted and citation networks are built. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**PermanentNote** (Zettelkasten+)
An atomic, self-contained knowledge claim — the core unit of a Zettelkasten. Permanent notes express your own ideas and connect to other permanent notes via argumentation links (supports, contradicts, followsFrom, relatedTo). See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**Persona**
A named workspace configuration that stores panel layout, sidebar arrangement, and explorer mode. Switching personas instantly reconfigures the workspace without affecting user settings like theme or font size. See [Chapter 30: Workspace Personas](30-personas.md).

**PKCE**
Proof Key for Code Exchange. A security extension to the OAuth 2.0 authorization code flow that prevents authorization code interception attacks. SemPKM's IndieAuth provider requires PKCE for all authorization requests. The client generates a random `code_verifier`, sends a hashed `code_challenge` with the authorization request, then proves possession of the original verifier when exchanging the code for a token. See [Chapter 26: IndieAuth](26-indieauth.md). A W3C standard for defining ontologies -- formal descriptions of types, properties, and their relationships. SemPKM uses OWL Class and Property declarations in Mental Model ontology files.

**Property Flip**
A toggle on spatial canvas object nodes that switches between the Markdown body and a compact property table showing SHACL-derived metadata. See [Chapter 27: Spatial Canvas](27-spatial-canvas.md).

**Property**
A named attribute of an object. Properties can hold literal values (strings, dates, numbers, URIs) or references to other objects. In RDF terms, a property is a predicate in a subject-predicate-object triple. SemPKM distinguishes between datatype properties (literal values) and object properties (references to other resources). See also: Edge, Object.

**Pull Sync**
The process of fetching data from an external system into SemPKM. In Linear Sync, pull sync imports Linear issues as `bpkm:Task` objects with field mapping. See [Chapter 34: Linear Sync](34-linear-sync.md).

**Push Sync**
The process of sending local changes from SemPKM back to an external system. In Linear Sync, push sync detects modified tasks and updates the corresponding Linear issues. See [Chapter 34: Linear Sync](34-linear-sync.md).

**RBox**
(Relational Box) The set of properties (object properties and datatype properties) defined in an ontology. Viewable in the Ontology Viewer's RBox tab.

**RDF**
Resource Description Framework. The W3C standard data model that underpins SemPKM. All data is stored as triples: subject-predicate-object statements. For example, "Alice Chen" (subject) "has job title" (predicate) "Lead Developer" (object). RDF enables flexible, schema-on-read data that can be queried, linked, and extended without migrations.

**ResearchQuestion** (Research Workflow)
An open question driving a research investigation. Research questions can be addressed by arguments that synthesize claims and evidence. Status tracks progress from open through partially-answered to answered. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**SHACL**
Shapes Constraint Language.

**SHACL-AF Rule**
A SHACL Advanced Features rule that generates new triples from existing data. Unlike validation shapes (which check constraints), SHACL-AF rules produce inferred triples -- for example, automatically deriving a `fullName` property by concatenating `firstName` and `lastName`. SemPKM executes SHACL-AF rules as part of the inference pipeline. See [Chapter 16: The Data Model](16-data-model.md). A W3C standard for validating RDF data against a set of conditions (shapes). In SemPKM, SHACL shapes serve double duty: they define the form structure for editing objects (field names, order, groups, data types, dropdowns) and they provide validation rules (required fields, allowed values, cardinality). See also: Shape, Validation.

**Shape**
A SHACL node shape that describes the expected structure of a specific type. Each shape lists property constraints (what fields should exist, their data types, whether they are required, allowed values) and property groups (how fields are organized in the form). Shapes drive both form generation and data validation. See also: SHACL, Mental Model.

**Spatial Canvas**
An interactive freeform workspace for exploring your knowledge graph visually. Unlike auto-layout graph views, the canvas starts empty and lets you build a custom map by dragging objects from the navigation tree, expanding neighborhoods, and arranging nodes by hand. Named sessions let you save and switch between different explorations. See [Chapter 27: Spatial Canvas](27-spatial-canvas.md).

**Step** (workflow)
An individual stage in a workflow. Three types: view (opens a view), dashboard (opens a dashboard), and form (opens a create form). Each step has an optional label displayed in the stepper bar. See [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md).

**StructureNote** (Zettelkasten+)
An organizing note that curates permanent notes into coherent topics — argument maps, field surveys, or indexes. Structure notes sit at the top of the Zettelkasten provenance chain. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**SPARQL**
SPARQL Protocol and RDF Query Language. The standard query language for RDF data, analogous to SQL for relational databases. SemPKM uses SPARQL internally for all data retrieval and manipulation. View specifications contain SPARQL queries that power table, card, and graph views. The bottom panel includes a SPARQL console for running ad-hoc queries.

**TBox**
(Terminological Box) The set of class definitions and their hierarchy in an ontology. Viewable in the Ontology Viewer's TBox tab.

**Task** (Basic PKM v2.0)
A unit of work with status tracking (todo, in-progress, done, blocked, cancelled), priority, effort sizing, due dates, and person assignment. Tasks link to projects and milestones to form a work graph. See [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md).

**Triple**
The atomic unit of data in RDF: a subject-predicate-object statement. For example: `<Person/alice> <foaf:name> "Alice Chen"` is a triple stating that the resource `Person/alice` has the name "Alice Chen". All data in SemPKM -- objects, properties, edges, events -- is ultimately stored as triples.

**Triplestore**
A database optimized for storing and querying RDF triples. SemPKM uses Eclipse RDF4J as its triplestore, running as a Docker container. The triplestore holds all object data, ontologies, shapes, views, event graphs, and the current state graph.

**Type**
A classification for objects, defined as an OWL class in a Mental Model's ontology. The Basic PKM model defines four types: Note, Concept, Project, and Person. Each type has associated SHACL shapes (for forms and validation) and view specifications (for browsing). When you create a new object, you choose its type.

**Upper Ontology**
A high-level, domain-independent ontology that provides general concepts (like Event, Person, Organization) that domain-specific models extend. In SemPKM, gist serves as the upper ontology.

**Validation**
The process of checking an object's data against its SHACL shape. Validation runs asynchronously after every save operation. Results appear in the Lint Panel and include violation severity (warning or error), the affected property, and a human-readable message. Validation is non-blocking -- you can always save your work regardless of validation results. See also: SHACL, Lint.

**WebID**
A personal identifier that is also a web URL pointing to a machine-readable profile document. In SemPKM, each user gets a WebID at `{APP_BASE_URL}/id/{username}` that serves both a human-readable HTML profile and Linked Data (JSON-LD/Turtle) via content negotiation. WebIDs enable decentralized identity -- you can use your SemPKM WebID to authenticate with other services via IndieAuth. See [Chapter 25: WebID Profiles](25-webid-profiles.md).

**View**
A named query-and-renderer combination that displays a collection of objects. Each view targets a specific type and uses a SPARQL query to fetch data, combined with a renderer type (table, card, or graph) to determine the visual layout. Views are defined in Mental Model bundles and appear in the Views menu. See also: Mental Model, SPARQL.

**Workflow**
An ordered sequence of steps that guides users through a multi-step process, with a stepper UI for navigation. Steps can be views, dashboards, or forms. Created and launched from the Explorer sidebar. See [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md).

## See Also

- [Core Concepts](02-core-concepts.md) -- introductory explanation of these terms in context
- [The Data Model](16-data-model.md) -- technical details of how RDF, events, and named graphs work together

---

**Previous:** [Appendix C: Command API Reference](appendix-c-command-api-reference.md) | **Next:** [Appendix E: Troubleshooting](appendix-e-troubleshooting.md)
