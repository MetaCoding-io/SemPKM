# Chapter 19: Creating Mental Models

This chapter walks you through creating your own Mental Model from scratch. By the end, you will understand the bundle format, know how to write an ontology, SHACL shapes, view specs, and seed data, and be able to test and package your model for installation.

We will use the built-in "Basic PKM" model as a running example throughout, pointing to its actual files so you can study a working reference alongside this guide.

## The Bundle Format

A Mental Model is a directory with a fixed structure. At the top level sits a `manifest.yaml` file, and below it are subdirectories for each artifact type:

```
my-research/
  manifest.yaml
  ontology/
    my-research.jsonld
  shapes/
    my-research.jsonld
  views/
    my-research.jsonld
  seed/
    my-research.jsonld
```

Each subdirectory contains a single JSON-LD file (named after the model ID by convention). The manifest tells SemPKM where to find each file and provides metadata about the model.

> **Note:** All JSON-LD files must use inline `@context` mappings. Remote `@context` URLs (like `https://schema.org/`) are rejected because the Docker containers may not have internet access. Define all prefixes directly in each file.

### Required Artifacts

| Directory    | File              | Purpose                                      | Required |
|-------------|-------------------|----------------------------------------------|----------|
| (root)      | `manifest.yaml`   | Model metadata, prefixes, entrypoints, icons | Yes      |
| `ontology/` | `{modelId}.jsonld` | OWL classes and properties                   | Yes      |
| `shapes/`   | `{modelId}.jsonld` | SHACL shapes for forms and validation        | Yes      |
| `views/`    | `{modelId}.jsonld` | View specifications (table, card, graph)     | Yes      |
| `seed/`     | `{modelId}.jsonld` | Starter objects loaded on first install      | No       |

## The Manifest

The manifest is the entry point for your model. SemPKM reads it first, validates it against a strict schema, and uses it to locate all other files.

Here is the complete manifest from the Basic PKM model:

```yaml
modelId: basic-pkm
version: "1.0.0"
name: "Basic PKM"
description: "Personal knowledge management with Projects, People, Notes, and Concepts."
namespace: "urn:sempkm:model:basic-pkm:"
prefixes:
  bpkm: "urn:sempkm:model:basic-pkm:"
entrypoints:
  ontology: "ontology/basic-pkm.jsonld"
  shapes: "shapes/basic-pkm.jsonld"
  views: "views/basic-pkm.jsonld"
  seed: "seed/basic-pkm.jsonld"
icons:
  - type: "bpkm:Note"
    icon: "file-text"
    color: "#4e79a7"
    tree:
      icon: "file-text"
      color: "#4e79a7"
      size: 16
    tab:
      icon: "file-text"
      color: "#4e79a7"
      size: 14
    graph:
      icon: "file-text"
      color: "#4e79a7"
  - type: "bpkm:Concept"
    icon: "lightbulb"
    color: "#f28e2b"
    tree:
      icon: "lightbulb"
      color: "#f28e2b"
      size: 16
    tab:
      icon: "lightbulb"
      color: "#f28e2b"
      size: 14
    graph:
      icon: "lightbulb"
      color: "#f28e2b"
```

### Required Fields

| Field         | Type              | Rules                                                     |
|--------------|-------------------|-----------------------------------------------------------|
| `modelId`    | string            | Lowercase letters, digits, hyphens. 2--64 characters. Pattern: `^[a-z][a-z0-9-]*$` |
| `version`    | string            | Semantic versioning: `MAJOR.MINOR.PATCH` (e.g., `"1.0.0"`) |
| `name`       | string            | Human-readable display name. 1--200 characters.            |
| `description`| string            | Optional. Up to 2000 characters.                           |
| `namespace`  | string            | Must follow the pattern `urn:sempkm:model:{modelId}:` exactly. |
| `prefixes`   | map[string,string] | Prefix-to-namespace mappings. At minimum, include your model prefix. |
| `entrypoints`| object            | Paths to artifact files, relative to the model root directory. |

### Entrypoints

The `entrypoints` section maps artifact types to file paths. If you omit entrypoints, SemPKM uses defaults based on the `{modelId}` placeholder:

| Entrypoint  | Default Value                   | Required |
|-------------|--------------------------------|----------|
| `ontology`  | `ontology/{modelId}.jsonld`    | Yes      |
| `shapes`    | `shapes/{modelId}.jsonld`      | Yes      |
| `views`     | `views/{modelId}.jsonld`       | Yes      |
| `seed`      | `seed/{modelId}.jsonld`        | No       |

The `{modelId}` placeholder is resolved automatically from the manifest. You can also specify explicit paths if you prefer a different naming convention.

### Icons

The `icons` array assigns Lucide icon names and colors to each type your model defines. Each entry supports per-context overrides for the **Explorer tree**, **editor tabs**, and **graph nodes**:

```yaml
icons:
  - type: "bpkm:Project"        # Type IRI (compact form using model prefixes)
    icon: "folder-kanban"         # Default Lucide icon name
    color: "#59a14f"              # Default color (hex)
    tree:                         # Override for Explorer tree
      icon: "folder-kanban"
      color: "#59a14f"
      size: 16                    # Icon size in pixels
    tab:                          # Override for editor tabs
      icon: "folder-kanban"
      color: "#59a14f"
      size: 14
    graph:                        # Override for graph nodes
      icon: "folder-kanban"
      color: "#59a14f"
```

The `type` field uses compact IRI notation (e.g., `bpkm:Project`), which is expanded against the `prefixes` defined in your manifest.

> **Tip:** Browse the Lucide icon library at [lucide.dev](https://lucide.dev) to find icon names. Use distinct colors per type so they are easy to distinguish in the Explorer tree and graph views.

### Settings

Models can contribute custom settings that appear in the **Settings** tab. Each setting definition includes a key, label, input type, and default value:

```yaml
settings:
  - key: "defaultNoteType"
    label: "Default Note Type"
    description: "The note type pre-selected when creating a new Note"
    input_type: "select"
    options: ["observation", "idea", "reference", "meeting-note", "journal"]
    default: "observation"
  - key: "enableAutoTags"
    label: "Auto-tagging"
    input_type: "toggle"
    default: "false"
```

Supported input types: `text`, `select`, `toggle`, `color`.

## Defining an Ontology

The ontology file declares the types (classes) and properties that your model introduces. It is written as JSON-LD using OWL vocabulary.

### File Structure

```json
{
  "@context": {
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "schema": "https://schema.org/",
    "dcterms": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "bpkm": "urn:sempkm:model:basic-pkm:"
  },
  "@graph": [
    ...
  ]
}
```

The `@context` block maps short prefixes to full namespace URIs. The `@graph` array contains all your type and property declarations.

### Declaring Types

Each type is an `owl:Class` with a label and description:

```json
{
  "@id": "bpkm:Project",
  "@type": "owl:Class",
  "rdfs:label": "Project",
  "rdfs:comment": "A project or initiative being tracked"
}
```

The `@id` uses your model's namespace prefix. The `rdfs:label` is what users see in the type picker and Explorer tree.

### Declaring Properties

Properties come in two kinds:

**Datatype properties** hold literal values (strings, dates, numbers):

```json
{
  "@id": "bpkm:status",
  "@type": "owl:DatatypeProperty",
  "rdfs:label": "Status",
  "rdfs:comment": "Status of a project (active, completed, on-hold, cancelled)",
  "rdfs:domain": { "@id": "bpkm:Project" },
  "rdfs:range": { "@id": "xsd:string" }
}
```

**Object properties** link to other objects:

```json
{
  "@id": "bpkm:hasParticipant",
  "@type": "owl:ObjectProperty",
  "rdfs:label": "Has Participant",
  "rdfs:comment": "People involved in a project",
  "rdfs:domain": { "@id": "bpkm:Project" },
  "rdfs:range": { "@id": "bpkm:Person" }
}
```

### Using Standard Vocabularies

A key best practice is to reuse well-known vocabularies instead of inventing your own properties for common concepts. The Basic PKM model demonstrates this:

| Vocabulary   | Prefix     | Used For                                |
|-------------|-----------|------------------------------------------|
| Dublin Core  | `dcterms:` | `title`, `description`, `created`, `modified`, `source` |
| FOAF         | `foaf:`    | `name`, `mbox` (email), `phone`          |
| Schema.org   | `schema:`  | `jobTitle`, `worksFor`, `startDate`, `endDate`, `url` |
| SKOS         | `skos:`    | `prefLabel`, `altLabel`, `definition`, `broader`, `narrower`, `related` |

By using `dcterms:title` instead of `bpkm:title`, your data becomes interoperable with any system that understands Dublin Core -- which is virtually every knowledge management tool on the web.

> **Tip:** Only create model-specific properties when no standard vocabulary covers your concept. For example, `bpkm:status` and `bpkm:noteType` are model-specific because there is no widely adopted standard property for project status dropdowns.

### Inverse Properties

You can declare inverse relationships using `owl:inverseOf`. This tells SemPKM that two properties are mirror images of each other:

```json
{
  "@id": "bpkm:participatesIn",
  "@type": "owl:ObjectProperty",
  "rdfs:label": "Participates In",
  "rdfs:domain": { "@id": "bpkm:Person" },
  "rdfs:range": { "@id": "bpkm:Project" },
  "owl:inverseOf": { "@id": "bpkm:hasParticipant" }
}
```

When a Person participates in a Project, the inverse relationship (Project has participant) is understood automatically.

## Writing SHACL Shapes

SHACL shapes are the heart of automatic form generation in SemPKM. Each shape describes the expected structure of a type -- which properties it should have, their data types, cardinality, display order, and grouping. SemPKM reads these shapes and generates form fields, validation rules, and editor layouts from them.

### Node Shapes

A node shape targets an OWL class and lists its property constraints:

```json
{
  "@id": "bpkm:ProjectShape",
  "@type": "sh:NodeShape",
  "sh:targetClass": { "@id": "bpkm:Project" },
  "rdfs:label": "Project Shape",
  "sh:property": [
    ...
  ]
}
```

The `sh:targetClass` connects this shape to the corresponding OWL class. All objects of that type will be validated against this shape and rendered using its property list.

### Property Constraints

Each entry in the `sh:property` array describes one form field. Here is a complete example with all commonly used attributes:

```json
{
  "sh:path": { "@id": "bpkm:status" },
  "sh:name": "Status",
  "sh:datatype": { "@id": "xsd:string" },
  "sh:in": { "@list": ["active", "completed", "on-hold", "cancelled"] },
  "sh:defaultValue": "active",
  "sh:minCount": 0,
  "sh:maxCount": 1,
  "sh:order": 3,
  "sh:group": { "@id": "bpkm:ProjectBasicInfoGroup" }
}
```

### Shape Attribute Reference

| Attribute        | Purpose                                      | Example                                            |
|-----------------|----------------------------------------------|----------------------------------------------------|
| `sh:path`       | The RDF property this constraint applies to  | `{ "@id": "dcterms:title" }`                       |
| `sh:name`       | Display label shown in the form              | `"Title"`                                           |
| `sh:datatype`   | Expected data type for literal values        | `{ "@id": "xsd:string" }`, `{ "@id": "xsd:date" }` |
| `sh:class`      | Expected type for object references          | `{ "@id": "bpkm:Person" }`                         |
| `sh:minCount`   | Minimum number of values (1 = required)      | `1`                                                 |
| `sh:maxCount`   | Maximum number of values (1 = single-value)  | `1`                                                 |
| `sh:order`      | Display order within the form (lower = first)| `1`, `2`, `3`                                       |
| `sh:group`      | Property group for visual grouping in form   | `{ "@id": "bpkm:ProjectBasicInfoGroup" }`           |
| `sh:in`         | Allowed values list (renders as dropdown)    | `{ "@list": ["low", "medium", "high"] }`            |
| `sh:defaultValue`| Pre-filled value for new objects             | `"active"`                                          |

### Supported Data Types

| XSD Type         | Form Widget     | Notes                        |
|-----------------|----------------|-------------------------------|
| `xsd:string`    | Text input      | Single-line text field        |
| `xsd:date`      | Date picker     | ISO 8601 date (YYYY-MM-DD)   |
| `xsd:dateTime`  | DateTime picker | ISO 8601 datetime             |
| `xsd:integer`   | Number input    | Whole numbers                 |
| `xsd:decimal`   | Number input    | Decimal numbers               |
| `xsd:boolean`   | Checkbox        | True/false toggle             |
| `xsd:anyURI`    | URL input       | Rendered as clickable link    |

### Dropdown Fields with sh:in

When you provide an `sh:in` list, SemPKM renders the field as a dropdown select instead of a free-text input:

```json
{
  "sh:path": { "@id": "bpkm:priority" },
  "sh:name": "Priority",
  "sh:datatype": { "@id": "xsd:string" },
  "sh:in": { "@list": ["low", "medium", "high", "critical"] },
  "sh:defaultValue": "medium",
  "sh:maxCount": 1,
  "sh:order": 4,
  "sh:group": { "@id": "bpkm:ProjectBasicInfoGroup" }
}
```

This produces a dropdown with four options, defaulting to "medium" for new Projects.

### Object References with sh:class

To create a field that links to another object, use `sh:class` instead of `sh:datatype`:

```json
{
  "sh:path": { "@id": "bpkm:hasParticipant" },
  "sh:name": "Participants",
  "sh:class": { "@id": "bpkm:Person" },
  "sh:order": 8,
  "sh:group": { "@id": "bpkm:ProjectRelationshipsGroup" }
}
```

Notice there is no `sh:maxCount` here -- omitting it means the field accepts multiple values (a Project can have many participants). SemPKM renders this as a multi-select reference picker filtered to objects of type `bpkm:Person`.

For single-value references, add `sh:maxCount: 1`:

```json
{
  "sh:path": { "@id": "bpkm:relatedProject" },
  "sh:name": "Related Project",
  "sh:class": { "@id": "bpkm:Project" },
  "sh:maxCount": 1,
  "sh:order": 5,
  "sh:group": { "@id": "bpkm:NoteRelationshipsGroup" }
}
```

### Cardinality Rules

| `sh:minCount` | `sh:maxCount` | Meaning                                | Form Behavior               |
|--------------|--------------|----------------------------------------|-----------------------------|
| 0 (or omit)  | 1            | Optional, single value                 | Optional field              |
| 1            | 1            | Required, single value                 | Required field with marker  |
| 0 (or omit)  | (omit)       | Optional, multiple values              | Multi-value field           |
| 1            | (omit)       | At least one required, multiple values | Required multi-value field  |

### Property Groups

Groups organize form fields into collapsible sections. Define groups as separate nodes in your shapes file:

```json
{
  "@id": "bpkm:ProjectBasicInfoGroup",
  "@type": "sh:PropertyGroup",
  "rdfs:label": "Basic Info",
  "sh:order": 1
},
{
  "@id": "bpkm:ProjectDatesGroup",
  "@type": "sh:PropertyGroup",
  "rdfs:label": "Dates",
  "sh:order": 2
},
{
  "@id": "bpkm:ProjectRelationshipsGroup",
  "@type": "sh:PropertyGroup",
  "rdfs:label": "Relationships",
  "sh:order": 3
}
```

The `sh:order` on groups controls the top-level section order. Within each group, individual property `sh:order` values control field order.

> **Tip:** Use a consistent naming convention for group IDs: `{ModelPrefix}:{TypeName}{GroupName}Group`. For example, `bpkm:ProjectDatesGroup`, `bpkm:PersonContactGroup`.

## Defining Views

Views tell SemPKM how to display collections of objects. Each view is a combination of a SPARQL query (that fetches the data) and a renderer type (that controls the visual layout).

### View Spec Structure

Each view is a node of type `sempkm:ViewSpec`:

```json
{
  "@id": "bpkm:view-project-table",
  "@type": "sempkm:ViewSpec",
  "rdfs:label": "Projects Table",
  "sempkm:targetClass": { "@id": "bpkm:Project" },
  "sempkm:rendererType": "table",
  "sempkm:sparqlQuery": "SELECT ?s ?title ?status ?priority ?startDate WHERE { ... }",
  "sempkm:columns": "title,status,priority,startDate",
  "sempkm:sortDefault": "title"
}
```

### View Attributes

| Attribute              | Purpose                                        | Required |
|-----------------------|------------------------------------------------|----------|
| `rdfs:label`          | Display name shown in the Views menu           | Yes      |
| `sempkm:targetClass`  | The type this view applies to                  | Yes      |
| `sempkm:rendererType` | Renderer: `table`, `card`, or `graph`          | Yes      |
| `sempkm:sparqlQuery`  | SPARQL query that fetches view data            | Yes      |
| `sempkm:columns`      | Comma-separated column list (table renderer)   | Table only |
| `sempkm:sortDefault`  | Default sort column (table renderer)           | No       |
| `sempkm:cardTitle`    | Property IRI used as card title (card renderer)| Card only |
| `sempkm:cardSubtitle` | Property IRI used as card subtitle             | No       |

### Table Views

Table views use a `SELECT` query. The `?s` variable must bind to the object IRI (used for row click-through). Additional variables become column values:

```sparql
SELECT ?s ?title ?status ?priority ?startDate
WHERE {
  ?s a <urn:sempkm:model:basic-pkm:Project> ;
     <http://purl.org/dc/terms/title> ?title .
  OPTIONAL { ?s <urn:sempkm:model:basic-pkm:status> ?status } .
  OPTIONAL { ?s <urn:sempkm:model:basic-pkm:priority> ?priority } .
  OPTIONAL { ?s <https://schema.org/startDate> ?startDate } .
}
```

The `sempkm:columns` attribute maps to the SPARQL variable names (without the `?` prefix). The column order in the `columns` string determines the display order.

> **Warning:** SPARQL queries in view specs must use full IRIs, not prefixed names. The query is sent directly to the triplestore, which does not have access to your model's prefix mappings within the query string itself.

### Card Views

Card views also use `SELECT` queries but render each result as a visual card:

```json
{
  "@id": "bpkm:view-project-card",
  "@type": "sempkm:ViewSpec",
  "rdfs:label": "Projects Cards",
  "sempkm:targetClass": { "@id": "bpkm:Project" },
  "sempkm:rendererType": "card",
  "sempkm:sparqlQuery": "SELECT ?s ?title ?description ?status ?priority WHERE { ... }",
  "sempkm:cardTitle": "http://purl.org/dc/terms/title",
  "sempkm:cardSubtitle": "urn:sempkm:model:basic-pkm:status"
}
```

The `cardTitle` and `cardSubtitle` values are full property IRIs that match variables in your query. They control which fields are displayed prominently on each card.

### Graph Views

Graph views use `CONSTRUCT` queries that return a sub-graph of triples. The graph renderer visualizes nodes and edges from this sub-graph:

```sparql
CONSTRUCT {
  ?s a <urn:sempkm:model:basic-pkm:Project> ;
     <http://purl.org/dc/terms/title> ?title ;
     <urn:sempkm:model:basic-pkm:hasParticipant> ?person ;
     <urn:sempkm:model:basic-pkm:hasNote> ?note .
  ?person <http://xmlns.com/foaf/0.1/name> ?pname .
  ?note <http://purl.org/dc/terms/title> ?ntitle
}
WHERE {
  ?s a <urn:sempkm:model:basic-pkm:Project> ;
     <http://purl.org/dc/terms/title> ?title .
  OPTIONAL {
    ?s <urn:sempkm:model:basic-pkm:hasParticipant> ?person .
    ?person <http://xmlns.com/foaf/0.1/name> ?pname
  } .
  OPTIONAL {
    ?s <urn:sempkm:model:basic-pkm:hasNote> ?note .
    ?note <http://purl.org/dc/terms/title> ?ntitle
  }
}
```

The `CONSTRUCT` template defines which triples are included in the graph visualization. Each subject becomes a node; each object property becomes an edge. Include label properties (`dcterms:title`, `foaf:name`, `skos:prefLabel`) so nodes display readable names instead of raw IRIs.

### View Naming Convention

For consistency with the Basic PKM model, name your views as `{prefix}:view-{type}-{renderer}`:

- `bpkm:view-project-table`
- `bpkm:view-project-card`
- `bpkm:view-project-graph`
- `bpkm:view-person-table`

## Seed Data

Seed data is an optional JSON-LD file containing starter objects that are loaded when the model is first installed. This gives new users something to explore immediately instead of staring at an empty workspace.

### Structure

The seed file uses the same JSON-LD structure as the ontology, with objects in the `@graph` array:

```json
{
  "@context": {
    "bpkm": "urn:sempkm:model:basic-pkm:",
    "dcterms": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "schema": "https://schema.org/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
  },
  "@graph": [
    {
      "@id": "bpkm:seed-project-sempkm",
      "@type": "bpkm:Project",
      "dcterms:title": "SemPKM Development",
      "dcterms:description": "Building a semantic PKM system.",
      "bpkm:status": "active",
      "bpkm:priority": "high",
      "schema:startDate": { "@value": "2026-01-15", "@type": "xsd:date" },
      "bpkm:tags": "semantic-web,knowledge-management,rdf",
      "dcterms:created": { "@value": "2026-01-15T09:00:00Z", "@type": "xsd:dateTime" },
      "bpkm:hasParticipant": [
        { "@id": "bpkm:seed-person-alice" },
        { "@id": "bpkm:seed-person-bob" }
      ]
    },
    {
      "@id": "bpkm:seed-person-alice",
      "@type": "bpkm:Person",
      "foaf:name": "Alice Chen",
      "foaf:mbox": "alice@example.com",
      "schema:jobTitle": "Lead Developer",
      "schema:worksFor": "SemPKM Labs"
    }
  ]
}
```

### Best Practices for Seed Data

- Use descriptive IRI slugs prefixed with `seed-` (e.g., `bpkm:seed-project-sempkm`) so seed objects are easily identifiable.
- Include cross-references between seed objects to demonstrate relationships in the graph view.
- Provide typed values for dates and URIs using the `{ "@value": "...", "@type": "xsd:..." }` syntax.
- Keep seed data modest -- 5 to 15 objects is enough to illustrate the model without overwhelming new users.
- Seed data is loaded once on model installation. Users can edit or delete seed objects freely.

## Testing Your Model

Before distributing your model, test it thoroughly in a local SemPKM instance.

### Install from Local Directory

Copy your model directory into the `models/` directory of your SemPKM installation:

```bash
cp -r my-research/ /path/to/SemPKM/models/my-research/
```

Then restart the API container:

```bash
docker compose restart api
```

SemPKM auto-detects and installs models from the `models/` directory on startup.

### Validate the Manifest

Check the API logs for manifest validation errors:

```bash
docker compose logs api | grep -i "manifest\|model\|error"
```

Common manifest issues:

- **modelId format**: Must be lowercase with hyphens only. No underscores, uppercase, or spaces.
- **namespace mismatch**: The `namespace` field must exactly match `urn:sempkm:model:{modelId}:`.
- **missing files**: All required entrypoint files must exist at the specified paths.
- **remote @context**: JSON-LD files must not reference remote context URLs.

### Check Forms

After installation, create a new object of each type your model defines. Verify that:

- All expected form fields appear in the correct order and groups.
- Required fields show the required marker.
- Dropdown fields (`sh:in`) display the correct options.
- Reference fields (`sh:class`) filter to the correct target type.
- Default values (`sh:defaultValue`) are pre-filled on new objects.

<!-- Screenshot: form fields generated from SHACL shapes -->

### Check Views

Open each view from the **Views** menu and verify:

- Table views show the expected columns with correct data.
- Card views display the correct title and subtitle.
- Graph views render nodes and edges with correct labels and icons.

<!-- Screenshot: table, card, and graph views side by side -->

### Check Validation

Create an object with intentionally invalid data (e.g., leave a required field empty, enter an invalid dropdown value) and check the **Lint Panel** in the right pane. SHACL validation results should appear after a brief delay.

## Packaging

For distribution, Mental Models are packaged as `.sempkm-model` archives. This is a ZIP file containing the model directory:

```bash
cd my-research/
zip -r ../my-research.sempkm-model .
```

The archive should contain the `manifest.yaml` at the root level (not nested inside a subdirectory):

```
my-research.sempkm-model
  manifest.yaml
  ontology/
    my-research.jsonld
  shapes/
    my-research.jsonld
  views/
    my-research.jsonld
  seed/
    my-research.jsonld
```

> **Warning:** Ensure the ZIP archive does not contain a wrapping directory. The `manifest.yaml` file should be at the top level inside the archive, not inside a `my-research/` subdirectory.

## Complete Walkthrough: A Research Model

To tie everything together, here is a minimal but complete example of a custom Mental Model for tracking research papers.

### manifest.yaml

```yaml
modelId: research
version: "1.0.0"
name: "Research Tracker"
description: "Track papers, authors, and research topics."
namespace: "urn:sempkm:model:research:"
prefixes:
  res: "urn:sempkm:model:research:"
entrypoints:
  ontology: "ontology/research.jsonld"
  shapes: "shapes/research.jsonld"
  views: "views/research.jsonld"
  seed: "seed/research.jsonld"
icons:
  - type: "res:Paper"
    icon: "book-open"
    color: "#e15759"
    tree:
      icon: "book-open"
      color: "#e15759"
      size: 16
    tab:
      icon: "book-open"
      color: "#e15759"
      size: 14
    graph:
      icon: "book-open"
      color: "#e15759"
```

### ontology/research.jsonld (excerpt)

```json
{
  "@context": {
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dcterms": "http://purl.org/dc/terms/",
    "res": "urn:sempkm:model:research:"
  },
  "@graph": [
    {
      "@id": "res:Paper",
      "@type": "owl:Class",
      "rdfs:label": "Paper",
      "rdfs:comment": "A research paper or publication"
    },
    {
      "@id": "res:venue",
      "@type": "owl:DatatypeProperty",
      "rdfs:label": "Venue",
      "rdfs:comment": "Conference or journal where the paper was published",
      "rdfs:domain": { "@id": "res:Paper" },
      "rdfs:range": { "@id": "xsd:string" }
    }
  ]
}
```

From here, you would create matching shapes (with `sh:targetClass` pointing to `res:Paper`), views (with SPARQL queries using the full `urn:sempkm:model:research:Paper` IRI), and optional seed data following the patterns shown throughout this chapter.

---

**Previous:** [Chapter 18: The SPARQL Endpoint](18-sparql-endpoint.md) | **Next:** [Chapter 20: Production Deployment](20-production-deployment.md)
