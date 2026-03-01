# Chapter 2: Core Concepts

This chapter introduces the building blocks you will encounter every time you use SemPKM. Each concept is explained with concrete examples from the **Basic PKM** Mental Model -- the starter model that ships with every SemPKM instance and gives you four types: Note, Concept, Project, and Person.

## Objects

An **object** is the fundamental unit of knowledge in SemPKM. Every piece of information you create -- a person, a project, a note, a concept -- is an object. Each object has three key characteristics:

1. **A type** that determines its structure (e.g., "Project" or "Person").
2. **Properties** that hold its data (e.g., a title, a status, a start date).
3. **An optional Markdown body** for free-form rich text alongside the structured fields.

Under the hood, each object is identified by a unique IRI (Internationalized Resource Identifier) -- something like `https://example.org/data/abc123`. You never need to see or type these IRIs; SemPKM manages them automatically. When you create a new Project called "SemPKM Development", the system mints an IRI, assigns the type, and stores all properties as RDF triples.

For example, the seed data that ships with Basic PKM includes a Project object with the title "SemPKM Development", status "active", priority "high", and a start date of January 15, 2026. It also includes a Markdown body on the related Note object "Architecture Decision: Event Sourcing" that explains the team's persistence strategy with headings, bullet points, and technical detail -- all stored alongside the structured fields.

> **Tip:** Think of an object as a "smart document" -- it has structured, queryable fields like a database row, plus a free-text body like a wiki page.

## Types

A **type** defines the category of an object and determines which properties and relationships are available for it. Types come from installed Mental Models -- you do not create them manually.

The Basic PKM Mental Model defines four types:

| Type | Purpose | Icon |
|------|---------|------|
| **Note** | An observation, idea, reference, meeting note, or journal entry | file-text |
| **Concept** | An abstract topic, domain area, or term worth defining | lightbulb |
| **Project** | A tracked initiative or effort with status and participants | folder-kanban |
| **Person** | A person known to you, with contact info and organizational context | user |

When you click **New Object** in the workspace, you pick a type first. That choice determines which form fields appear, which relationship slots are available, and which views can display the object.

Types are defined using OWL (Web Ontology Language) classes inside a Mental Model's ontology file. The Basic PKM ontology declares `bpkm:Project` as an `owl:Class` with the label "Project" and the comment "A project or initiative being tracked." But you never need to interact with OWL directly -- SemPKM reads these definitions and generates the UI for you.

> **Note:** Installing a new Mental Model adds new types to your instance. For example, a "Research" Mental Model might add Paper, Dataset, and Experiment types alongside the existing Basic PKM types.

## Properties

**Properties** are the named fields on an object. Each property has a name, a data type (text, date, URL, etc.), and optional constraints like "required" or "pick from this list." Properties are defined in the Mental Model's SHACL shapes and rendered automatically as form fields in the object editor.

For example, the Project type has these properties organized into groups:

- **Basic Info** -- Title (required text), Description (text), Status (pick from: active, completed, on-hold, cancelled), Priority (pick from: low, medium, high, critical)
- **Dates** -- Start Date, End Date
- **Relationships** -- Participants (links to Person objects), Notes (links to Note objects)
- **Metadata** -- Tags, Created timestamp, Modified timestamp

When you open a Project in the editor, SemPKM reads the SHACL shape for `bpkm:ProjectShape` and renders each property as the appropriate form control: a text input for Title, a dropdown for Status, a date picker for Start Date, and a reference search field for Participants. The grouping (Basic Info, Dates, Relationships, Metadata) and the ordering within each group are also defined in the shape.

The Person type illustrates a different set of properties: Name (required, from the FOAF vocabulary), Email, Job Title, Organization, Phone, URL, and a Notes text field. The Concept type uses SKOS vocabulary properties: Label (required), Alternative Labels, Definition, and hierarchy relationships (Broader, Narrower, Related).

> **Tip:** Property constraints are assistive. If you skip a required field, SemPKM will flag it in the Lint Panel rather than preventing you from saving.

## Edges

An **edge** is a typed, directional relationship between two objects. Unlike wiki-links or backlinks in other tools, edges in SemPKM carry a specific meaning defined by the Mental Model's ontology.

Consider the Basic PKM model's relationship types:

- `hasParticipant` -- connects a Project to a Person (e.g., "SemPKM Development" has participant "Alice Chen")
- `participatesIn` -- the inverse: connects a Person to a Project
- `hasNote` -- connects a Project to a Note
- `isAbout` -- connects a Note to a Concept (e.g., "Architecture Decision: Event Sourcing" is about "Event Sourcing")
- `relatedProject` -- connects a Note to its Project context
- `broader` / `narrower` / `related` -- connect Concepts to each other in a hierarchy (e.g., "Event Sourcing" is broader than "Knowledge Management")

Edges are first-class citizens in SemPKM. They appear in the **Relationships** group of the object editor, show up as connections in the Graph view, and can be traversed in SPARQL queries. When you add Alice Chen as a participant on the SemPKM Development project, you are creating an edge of type `hasParticipant`. That edge is stored as an RDF triple and surfaced in both the Project's form (under Participants) and Alice's form (under Projects, via the inverse `participatesIn` property).

Because edges are typed, SemPKM can enforce constraints. The `hasParticipant` property on a Project only accepts Person objects -- you cannot accidentally link a Note there. The `isAbout` property on a Note only accepts Concept objects. These constraints come from the SHACL shapes (`sh:class` declarations) and are enforced during validation.

> **Note:** Edges can also carry annotations -- additional properties on the relationship itself, not just on the source or target object. This is useful for recording context like "role on project" or "date joined."

## Mental Models

A **Mental Model** is an installable package that brings a coherent set of types, properties, relationships, validation rules, view definitions, and seed data into your SemPKM instance. Mental Models are the mechanism that gives SemPKM its structure.

Each Mental Model is a directory containing:

| File | Purpose |
|------|---------|
| `manifest.yaml` | Metadata: model ID, version, name, description, namespace, prefixes, icons |
| `ontology/*.jsonld` | OWL class and property definitions (the "schema") |
| `shapes/*.jsonld` | SHACL node shapes defining form fields, groups, ordering, constraints |
| `views/*.jsonld` | View specifications: SPARQL queries + renderer configs for tables, cards, graphs |
| `seed/*.jsonld` | Optional starter data to populate when the model is first installed |

The Basic PKM model (`basic-pkm`) is auto-installed on first startup if no other models are present. Its manifest declares four types with distinct icons and colors (Note in blue, Concept in orange, Project in green, Person in teal), a namespace prefix `bpkm:`, and entrypoints for each of its four JSON-LD files.

When a Mental Model is installed, SemPKM writes its ontology, shapes, and views into separate named graphs in the triplestore, registers the model in a metadata graph, materializes any seed data through the event system, and registers the model's namespace prefixes. Removal is the reverse -- but SemPKM will refuse to remove a model if user-created objects of its types still exist, protecting your data.

You manage Mental Models from the **Admin** section of the workspace. Installing a new model is as simple as placing its directory in the `models/` folder and triggering an install through the API.

> **Tip:** Think of Mental Models as "apps" for your knowledge base. The Basic PKM model is the default app; you can add domain-specific models (Research, CRM, Software Engineering) to extend your instance's vocabulary without changing existing data.

## Views

A **view** is a saved browsing configuration that determines how a set of objects is displayed. Each view is defined by a SPARQL query (which selects and shapes the data) and a renderer type (which determines the visual layout).

SemPKM supports three renderer types:

### Table View

Displays objects as sortable, filterable rows. The Basic PKM model ships with table views for all four types. For example, the "Projects Table" view shows columns for Title, Status, Priority, and Start Date, sorted by title by default. The "People Table" view shows Name, Job Title, Organization, and Email.

<!-- Screenshot: Projects Table view showing several projects with status and priority columns -->

### Card View

Displays objects as visual cards with a title, subtitle, and summary content. The "Projects Cards" view shows the project title as the card heading and the status as the subtitle. The "People Cards" view shows the person's name and job title.

<!-- Screenshot: People Cards view showing contact cards for Alice, Bob, and Carol -->

### Graph View

Displays objects and their relationships as an interactive node-and-edge diagram. The "Projects Graph" view renders projects as nodes with edges to their participants (Person nodes) and notes (Note nodes). The "Concepts Graph" view shows the broader/narrower/related hierarchy between concepts.

<!-- Screenshot: Concepts Graph view showing Knowledge Management, Semantic Web, and Event Sourcing connected by broader/related edges -->

Views are bundled with Mental Models so that each model provides sensible defaults for browsing its types. You can switch between views using the view selector in the workspace toolbar.

> **Note:** Views are powered by SPARQL queries executed against your live data. When a Mental Model defines a table view, it includes the exact SPARQL SELECT query that fetches the columns, along with configuration for column order and default sort.

## Events

Every mutation in SemPKM -- creating an object, updating a property, adding an edge -- is recorded as an immutable **event**. Events are the system's source of truth for change history.

Each event is stored as a named graph in the triplestore and contains:

- **Timestamp** -- when the change occurred (ISO 8601 UTC)
- **Operation type** -- what kind of change (e.g., `object.create`, `object.patch`, `edge.create`, `body.set`)
- **Affected IRIs** -- which objects were changed
- **Description** -- a human-readable summary of the change
- **Performer** -- who made the change (user IRI and role)
- **Data triples** -- the actual RDF triples that were added or removed

When you create a new Note called "Architecture Decision: Event Sourcing", SemPKM creates an event with operation type `object.create`, records all the triples that make up the note (its title, body, type, tags, creation timestamp), and atomically materializes those triples into the current state graph. The event graph and the state update happen in a single RDF4J transaction -- if either fails, both roll back.

This event-sourcing architecture gives you several capabilities. You can view the full history of any object and see exactly what changed and when. You can see who made each change. And because events are immutable, they form a reliable audit trail that cannot be retroactively modified.

> **Note:** Events are created by the **Commands** system. All writes flow through `POST /api/commands`, which accepts operations like `object.create`, `object.patch`, `edge.create`, and `body.set`. Commands within a single batch execute atomically -- all succeed or all fail.

## Validation (Linting)

SemPKM uses **SHACL validation** to check your data against the rules defined in your installed Mental Models. After every save, a background validation job runs and reports any issues in the **Lint Panel**.

Validation checks include:

- **Required properties** -- Does a Project have a title? Does a Person have a name?
- **Cardinality** -- Does a field that should have at most one value (like Status) actually have only one?
- **Allowed values** -- Is the Project's status one of "active", "completed", "on-hold", or "cancelled"?
- **Type constraints** -- Does the `hasParticipant` edge point to a Person object, not a Note?
- **Datatype checks** -- Is a date field actually a valid date? Is a URL field a valid URI?

Validation is **assistive, not blocking**. You can save an object even if it has validation issues. The Lint Panel will show warnings and violations, but it will never prevent you from persisting your work. This design philosophy recognizes that knowledge capture often happens incrementally -- you might create a Project with just a title and fill in the rest later.

Validation results are stored as named graphs in the triplestore, with summary statistics (conforms, violation count, warning count) available for fast polling. Each validation report is linked to the event that triggered it, so you can trace which change introduced a validation issue.

> **Warning:** If no Mental Models are installed (which should not happen -- Basic PKM auto-installs on first startup), validation will return a synthetic "conforms" result since there are no shapes to validate against.

## How These Concepts Fit Together

Here is how the pieces connect using a concrete example:

1. You install the **Basic PKM Mental Model**, which provides the types Project, Person, Note, and Concept, along with their shapes, views, and seed data.
2. You create a **Project** object called "Knowledge Garden" by filling in the auto-generated form (Title, Description, Status, Priority -- all defined by the ProjectShape).
3. You add Carol Singh as a **participant** by creating an **edge** of type `hasParticipant` linking the Project to a Person object.
4. You write a **Note** called "Taxonomy Design Ideas" with a Markdown body containing your thoughts, and link it to the Concept "Knowledge Management" using an `isAbout` edge.
5. Each of these actions creates an immutable **event** recording exactly what changed, when, and by whom.
6. After each save, **SHACL validation** runs in the background and reports any issues (e.g., a Note missing its required title) in the Lint Panel.
7. You browse your growing knowledge base using **views** -- a table of all projects, a card grid of all people, or a graph showing how notes, concepts, and projects interconnect.

With these concepts in hand, you are ready to install SemPKM and start using it.

---

**Previous:** [Chapter 1: What is SemPKM?](01-what-is-sempkm.md) | **Next:** [Chapter 3: Installation and Setup](03-installation-and-setup.md)
