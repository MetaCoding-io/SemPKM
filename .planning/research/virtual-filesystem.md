# Virtual Filesystem over RDF Knowledge Graph

**Status:** Research / Early Design
**Date:** 2024-02-24
**Context:** SemPKM — Semantic Personal Knowledge Management

---

## 1. Vision

Expose the SemPKM knowledge graph as a virtual, mountable filesystem where:

- **Mount points** are configurable projections of graph shapes onto directory hierarchies.
- **Folders** represent grouping dimensions (tags, types, relationships, property values).
- **Files** are RDF resources rendered as Markdown with YAML frontmatter.
- **Edits** (writes, renames, moves) are translated back into SPARQL updates, validated against SHACL shapes before commit.
- A **declarative mapping language** describes how graph patterns project onto filesystem trees.

### Example: `/notes` Mount

```
/notes/
  by-tag/
    machine-learning/
      neural-networks-overview.md
      transformer-architecture.md
    philosophy/
      epistemology-notes.md
  by-type/
    observation/
      ...
    idea/
      ...
  all/
    neural-networks-overview.md
    ...
```

Each `.md` file contains:

```markdown
---
uri: "https://example.org/data/note-001"
type: Note
title: "Neural Networks Overview"
noteType: observation
tags:
  - machine-learning
  - deep-learning
isAbout:
  - uri: "https://example.org/data/concept-nn"
    label: "Neural Networks"
relatedProject:
  uri: "https://example.org/data/project-ai"
  label: "AI Research"
created: "2024-01-15T10:30:00Z"
modified: "2024-02-20T14:00:00Z"
---

# Neural Networks Overview

The body content of the note in Markdown...
```

---

## 2. Prior Art & Academic Research

### 2.1 Foundational Work: Semantic File Systems (1991)

The concept was proposed by **Gifford et al. at MIT** in 1991. Their system interpreted file paths as conjunctive queries against automatically extracted metadata, using "transducers" for type-specific metadata extraction. Virtual directories provided compatibility with existing filesystem protocols.

**Key insight:** Paths *are* queries. `/tag:ml/type:note/` is equivalent to `SELECT ?s WHERE { ?s bpkm:tags "ml" ; a bpkm:Note }`.

**Reference:** Gifford et al., "Semantic File Systems," 1991 — [ResearchGate](https://www.researchgate.net/publication/2503061_Semantic_File_Systems)

### 2.2 SemFS — Semantic File System via WebDAV

SemFS exposes an RDF knowledge base as a **WebDAV drive**, reinterpreting filesystem paths as RDF resource locations. Developed under the EU NEPOMUK and ACTIVE projects (2006-2010). Resources are accessed through hierarchical paths mapped to metadata attributes rather than physical directories.

**Relevance to SemPKM:** SemFS is the closest existing system to our vision. It uses WebDAV (widely supported by OS file managers), maps paths to RDF queries, and integrates with desktop environments.

**Reference:** [SemFS on semanticweb.org](http://semanticweb.org/wiki/SemFS.html)

### 2.3 TagFS — SPARQL-Backed Tag Filesystem

TagFS (Schenk & Staab, 2006) defines filesystem semantics directly in terms of **SPARQL queries over an RDF graph**. Each filesystem view translates into a SPARQL query; views compose functionally. For example, `hasTag(hasTag(/, 'paper'), 'WWW2006')` composes two SPARQL views to filter by two tags.

**Key insight:** Filesystem operations (ls, open, stat) can be formally defined as SPARQL query/update operations. This is the most rigorous mapping between filesystem semantics and RDF graph operations.

**Relevance to SemPKM:** TagFS's compositional view model directly informs our declarative mapping language design. Our `sempkm:ViewSpec` already maps SPARQL queries to UI renderers — a filesystem "renderer" is a natural extension.

**Reference:** [TagFS Paper (ESWC 2006)](https://kmi.open.ac.uk/events/eswc06/poster-papers/FP31-Schenk.pdf)

### 2.4 GFS — Graph-based File System

GFS (2017) is a FUSE filesystem that allows **semantic spaces** to be nested within a traditional directory hierarchy. Users can selectively enable semantic organization in chosen folders while leaving system directories unaltered.

**Relevance to SemPKM:** The hybrid approach (semantic spaces coexisting with regular folders) is appealing. Mount points could be nested into an existing filesystem.

**Reference:** [GFS on GitHub](https://github.com/danieleds/GFS) — [ACM Paper](https://dl.acm.org/doi/10.1145/3077584.3077591)

### 2.5 rdflib-fuse — RDF Store as FUSE Filesystem

A Python project (by Pierre-Antoine Champin) that mounts any RDFLib-backed store as a FUSE filesystem. Graph names become directory paths; files contain serialized graph data.

**Relevance to SemPKM:** Demonstrates the FUSE + RDFLib approach. However, it exposes raw RDF serializations (Turtle, N-Triples) rather than user-friendly Markdown. Our design goes beyond this by rendering resources as human-editable documents.

**Reference:** [rdflib-fuse on GitHub](https://github.com/pchampin/rdflib-fuse)

### 2.6 FS2KG — From File Systems to Knowledge Graphs

FS2KG (Tzitzikas, 2022) works in the **reverse direction**: automatically producing knowledge graphs from folder structures via small configuration files. Demonstrates the bidirectional potential between filesystem hierarchies and KGs.

**Relevance to SemPKM:** Informs the "import" direction. If we expose a virtual FS, users could also bootstrap graph data by placing files into mount points.

**Reference:** [FS2KG Paper (CEUR)](https://ceur-ws.org/Vol-3254/paper354.pdf)

### 2.7 Plan 9 Synthetic Filesystems & 9P Protocol

Plan 9 from Bell Labs (1990s) took "everything is a file" to its logical extreme. All system services (networking, hardware, processes) are exposed as **synthetic filesystems** using the 9P protocol. Per-user namespaces mean each user gets a custom view of the filesystem. The protocol is intentionally simple and network-transparent.

**Key insights:**
- Synthetic filesystems are a proven IPC and data access paradigm.
- Per-user namespaces map well to personalized mount configurations.
- The 9P protocol (now available on Linux via v9fs) could be an alternative transport.
- Well-known filesystem semantics provide a universal, scriptable interface.

**Reference:** [9P Protocol (Wikipedia)](https://en.wikipedia.org/wiki/9P_(protocol)) — [Synthetic Filesystems (HandWiki)](https://handwiki.org/wiki/Synthetic_file_system)

### 2.8 Solid Pods — Linked Data Personal Data Stores

Tim Berners-Lee's **Solid project** stores personal data in "pods" using Linked Data (RDF) technologies. Pods are essentially filesystem-like containers accessed via HTTP/REST, with WAC (Web Access Control) for permissions. While not a traditional filesystem, Solid demonstrates that RDF data can be organized in hierarchical container structures with standard protocols.

**Relevance to SemPKM:** Solid's container model (LDP containers as folders, resources as files) is analogous to our mount point concept. Our system could potentially expose data as a Solid-compatible pod.

**Reference:** [Solid Project](https://solidproject.org/) — [Solid on Wikipedia](https://en.wikipedia.org/wiki/Solid_(web_decentralization_project))

### 2.9 Mozilla GRAPH-TO-TREE Algorithm

Mozilla's archived RDF content model documentation describes a generic **GRAPH-TO-TREE** algorithm that recursively descends an RDF graph to produce a tree-shaped content model. The algorithm is parameterized by "hints" to handle the inherent ambiguity of projecting graphs onto trees. It can be performed **lazily** (on-demand per node).

**Key insight:** You need *one* generic graph-to-tree algorithm, not m×n custom converters. The hints/parameters are what we call the "declarative mapping."

**Reference:** [Mozilla RDF Content Model](https://www-archive.mozilla.org/rdf/content-model)

### 2.10 SHACL for Editing Interfaces

**Schímatos** generates web forms from SHACL shapes for knowledge graph editing. **SHAPEness** provides graph-based, form-based, and tree-based views for SHACL-constrained editing. The 2024 ACM Web Conference paper "From Shapes to Shapes" formally defines how SHACL constraints propagate through SPARQL CONSTRUCT queries.

**Key insight:** SHACL shapes can drive not just validation but also UI generation. In our case, SHACL shapes would determine which frontmatter fields are editable, what values are allowed, and which edits would be rejected.

**Relevance to SemPKM:** SemPKM already uses SHACL shapes for form generation. The same shapes can govern filesystem edit validation. **No existing work combines SHACL with filesystem-based editing** — this is a novel contribution.

**References:**
- [Schímatos on GitHub](https://github.com/schimatos/schimatos.org)
- [SHAPEness (ResearchGate)](https://www.researchgate.net/publication/373036851_SHAPEness_A_SHACL-Driven_Metadata_Editor)
- [From Shapes to Shapes (ACM 2024)](https://dl.acm.org/doi/10.1145/3589334.3645550)

---

## 3. Declarative Mapping Languages — Existing Work

### 3.1 R2RML & RML

**R2RML** (W3C) maps relational databases to RDF using declarative triples maps. **RML** extends R2RML to heterogeneous sources (CSV, JSON, XML). Both define Subject Maps, Predicate Maps, Object Maps, and Graph Maps — a vocabulary for describing how source structures become RDF terms.

**Relevance:** We need the *inverse* — mapping FROM RDF TO a hierarchical structure. But the R2RML/RML vocabulary for term maps, logical sources, and join conditions provides design patterns for our mapping language.

**References:**
- [R2RML W3C Recommendation](https://www.w3.org/TR/r2rml/)
- [RML Specification](https://rml.io/specs/rml/)

### 3.2 G2GML — Graph to Graph Mapping

G2GML maps RDF graphs to property graphs using declarative pattern pairs. Each mapping specifies an RDF graph pattern and a corresponding property graph pattern.

**Relevance:** G2GML demonstrates declarative graph-to-graph mapping. Our language is graph-to-tree, but the pattern-matching approach is transferable.

### 3.3 SPARQL CONSTRUCT as a Mapping Primitive

SPARQL CONSTRUCT already serves as a mapping language in SemPKM's `ViewSpec` system. The graph view specs use CONSTRUCT queries to project subgraphs. A filesystem mount could use a similar CONSTRUCT query to define "what data belongs in this mount."

**Key advantage:** SPARQL CONSTRUCT is well-understood, standardized, and already used in SemPKM.

---

## 4. Design Concepts for SemPKM

### 4.1 Architecture: Mount as ViewSpec Extension

SemPKM already has `sempkm:ViewSpec` with `rendererType` values of `table`, `card`, and `graph`. A virtual filesystem is conceptually a new renderer type: `filesystem`.

```jsonld
{
  "@id": "bpkm:mount-notes-by-tag",
  "@type": "sempkm:MountSpec",
  "rdfs:label": "Notes by Tag",
  "sempkm:mountPath": "/notes/by-tag",
  "sempkm:targetShape": { "@id": "bpkm:NoteShape" },
  "sempkm:directoryStrategy": "tag-groups",
  "sempkm:fileTemplate": "markdown-frontmatter",
  "sempkm:sparqlScope": "SELECT ?s WHERE { ?s a bpkm:Note }",
  "sempkm:directoryProperty": { "@id": "bpkm:tags" },
  "sempkm:fileNameProperty": { "@id": "dcterms:title" },
  "sempkm:bodyProperty": { "@id": "bpkm:body" },
  "sempkm:writable": true
}
```

### 4.2 Proposed Mapping Language: `sempkm:MountSpec`

A `MountSpec` would define:

| Field | Purpose |
|---|---|
| `mountPath` | Where this mount appears in the virtual FS |
| `targetShape` | SHACL NodeShape governing resources in this mount |
| `sparqlScope` | SPARQL query defining which resources appear |
| `directoryStrategy` | How to organize into folders: `flat`, `tag-groups`, `property-value`, `type-hierarchy`, `relationship-tree` |
| `directoryProperty` | Which RDF property defines folder grouping |
| `fileNameProperty` | Which property provides the filename (slugified) |
| `bodyProperty` | Which property holds the main file content (Markdown) |
| `fileTemplate` | How to render the file: `markdown-frontmatter`, `json`, `turtle` |
| `writable` | Whether edits are allowed |
| `shaclValidation` | Whether to validate edits against the target shape |

### 4.3 Directory Strategies

**`tag-groups`** — Each unique tag value becomes a folder; resources with that tag appear as files within:
```
/notes/by-tag/
  machine-learning/
    note-1.md
    note-2.md
  philosophy/
    note-3.md
    note-1.md    # same note can appear under multiple tags
```

**`property-value`** — Group by a property's distinct values:
```
/notes/by-type/
  observation/
    ...
  idea/
    ...
  meeting-note/
    ...
```

**`type-hierarchy`** — Directories mirror `rdfs:subClassOf` or `skos:broader/narrower`:
```
/concepts/
  artificial-intelligence/
    machine-learning/
      deep-learning/
        neural-networks.md
```

**`relationship-tree`** — Follow an object property to create nesting:
```
/projects/
  ai-research/
    notes/
      meeting-2024-01-15.md
    participants/
      alice.md
      bob.md
```

**`flat`** — All resources as files in a single directory:
```
/all-notes/
  note-1.md
  note-2.md
  ...
```

### 4.4 File Rendering: Markdown + YAML Frontmatter

The rendering pipeline:

1. **SPARQL query** retrieves all triples for the resource.
2. **SHACL shape** determines which properties are frontmatter fields vs. body content.
3. **Property groups** from SHACL organize the frontmatter sections.
4. **Object properties** (relationships) render as URIs with labels in frontmatter.
5. **The body property** (e.g., `bpkm:body`) becomes the Markdown content below the frontmatter separator.

### 4.5 Write Path: Edit → Validate → Update

When a file is saved:

1. **Parse** the Markdown+YAML back into property-value pairs.
2. **Diff** against the last-known state to identify changed triples.
3. **Validate** the proposed changes against the SHACL shape:
   - Cardinality constraints (`sh:minCount`, `sh:maxCount`)
   - Datatype constraints (`sh:datatype`)
   - Value constraints (`sh:in`, `sh:pattern`)
   - Class constraints for relationships (`sh:class`)
4. **If valid:** Execute SPARQL UPDATE to modify the graph.
5. **If invalid:** Reject the write (return an I/O error with a descriptive message in the log).

### 4.6 Transport Protocol Options

| Protocol | Pros | Cons |
|---|---|---|
| **FUSE** | Native OS integration, full POSIX semantics, transparent to all apps | Linux/macOS only, kernel module dependency, performance concerns |
| **WebDAV** | Cross-platform, supported by all OS file managers, HTTP-based | Limited semantics (no symlinks, limited xattr), needs HTTP server |
| **9P/v9fs** | Elegant, minimal, plan9-inspired, good Linux support | Less familiar, limited tooling outside Linux |
| **NFS** | Universal, mature | Complex to implement, heavy |
| **REST API + FUSE bridge** | SemPKM already has HTTP API, FUSE layer translates | Two-layer architecture, latency |

**Recommended initial approach:** WebDAV via the existing FastAPI backend, since:
- SemPKM is already an HTTP application
- WebDAV is supported natively by Windows Explorer, macOS Finder, and Linux file managers
- Python has mature WebDAV server libraries (wsgidav)
- SemFS demonstrated this approach successfully

### 4.7 Relationship to Existing SemPKM Architecture

```
┌─────────────────────────────────────────────────┐
│  SemPKM Backend (FastAPI)                       │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Browser  │  │ REST API │  │ VirtualFS    │  │
│  │ (HTML)   │  │ (JSON)   │  │ (WebDAV)     │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │               │          │
│  ┌────┴──────────────┴───────────────┴───────┐  │
│  │          Service Layer                    │  │
│  │  ┌─────────────┐  ┌──────────────────┐    │  │
│  │  │ ViewSpec    │  │ MountSpec        │    │  │
│  │  │ (table,card,│  │ (filesystem      │    │  │
│  │  │  graph)     │  │  projection)     │    │  │
│  │  └─────────────┘  └──────────────────┘    │  │
│  │          │               │                │  │
│  │  ┌───────┴───────────────┴──────────┐     │  │
│  │  │    SPARQL / Triplestore Layer    │     │  │
│  │  └──────────────┬───────────────────┘     │  │
│  │                 │                         │  │
│  │  ┌──────────────┴───────────────────┐     │  │
│  │  │    SHACL Validation Layer        │     │  │
│  │  └──────────────────────────────────┘     │  │
│  └───────────────────────────────────────────┘  │
│                    │                            │
│           ┌────────┴────────┐                   │
│           │   RDF4J Store   │                   │
│           └─────────────────┘                   │
└─────────────────────────────────────────────────┘
```

---

## 5. Novelty Assessment

Based on the literature survey, the following aspects appear **novel** (not found in existing work):

1. **SHACL-validated filesystem writes.** No existing system uses SHACL shapes to validate edits made through a filesystem interface. SemFS, TagFS, and GFS all support read-only or unconstrained writes.

2. **Declarative mount specs as RDF.** While TagFS defines views as SPARQL queries, and R2RML/RML define source-to-RDF mappings, no existing system defines filesystem-to-graph mappings as RDF resources using a declarative vocabulary.

3. **Markdown+frontmatter as a round-trippable RDF serialization.** Existing systems (rdflib-fuse) expose raw RDF serializations. Rendering RDF resources as human-friendly Markdown with YAML frontmatter, and parsing edits back into RDF updates, is not found in the literature.

4. **SHACL-driven frontmatter schema.** Using SHACL property shapes to determine which RDF properties appear in YAML frontmatter, their types, cardinalities, and allowed values — generating what is effectively a schema for the frontmatter — has no precedent.

5. **Integration with ViewSpec.** Treating the filesystem as another "renderer" alongside table, card, and graph views, sharing the same SPARQL and SHACL infrastructure, is architecturally novel.

---

## 6. Open Questions & Risks

### 6.1 Graph-to-Tree Ambiguity
RDF graphs are not trees. A resource with multiple tags appears in multiple directories. Options:
- **Symlinks / hardlinks** — One canonical location, links in others.
- **Duplicate files** — Same content in multiple folders (risk of conflicting edits).
- **Virtual copies with conflict resolution** — Writes to any copy update the same resource; conflicts are detected.

### 6.2 Filename Collisions
Multiple resources could have the same title within a directory. Strategies:
- Append a hash suffix: `neural-networks-overview-a1b2c3.md`
- Use the local part of the URI as filename
- Use title + disambiguator from another property

### 6.3 Performance
SPARQL queries on every `readdir()` or `stat()` call could be expensive.
- **Caching layer** with invalidation on graph changes (SemPKM's event system could drive cache invalidation).
- **Lazy enumeration** — Only query when a directory is actually listed.
- **Watch for SPARQL query cost** — Mount specs with broad scope could be slow.

### 6.4 Concurrency
Multiple processes editing the same file, or editing via the filesystem and the web UI simultaneously:
- Use ETags / last-modified timestamps for optimistic concurrency.
- SemPKM's event log could provide a conflict detection mechanism.

### 6.5 Mapping Language Evolution
Starting simple (static mount specs) but designing for extensibility:
- Phase 1: Fixed directory strategies (tag-groups, flat, property-value)
- Phase 2: Composable strategies (nested groupings)
- Phase 3: User-defined SPARQL-based directory generators
- Phase 4: Full declarative DSL or SPARQL-template language

### 6.6 Non-Markdown Resources
Some RDF resources may not naturally map to Markdown (e.g., a Person with no body text). Options:
- Render as YAML-only files (no body below frontmatter)
- Use `.yaml` extension for property-only resources
- Always include an empty body section

---

## 7. Recommended Next Steps

1. **Prototype a read-only WebDAV mount** using `wsgidav` integrated with FastAPI, serving a single hardcoded mount (Notes by tag).
2. **Define the `MountSpec` vocabulary** as JSON-LD in the model layer.
3. **Implement Markdown+frontmatter rendering** from SPARQL results + SHACL shapes.
4. **Add write support** with SHACL validation on the parse-back path.
5. **Design the declarative mapping language** iteratively based on real usage patterns.
6. **Evaluate FUSE as an alternative** if WebDAV proves limiting.

---

## 8. References

### Academic Papers
- Gifford et al., "Semantic File Systems," MIT, 1991 — [ResearchGate](https://www.researchgate.net/publication/2503061_Semantic_File_Systems)
- Schenk & Staab, "TagFS: Bringing Semantic Metadata to the Filesystem," ESWC 2006 — [Paper](https://kmi.open.ac.uk/events/eswc06/poster-papers/FP31-Schenk.pdf)
- Tzitzikas, "FS2KG: From File Systems to Knowledge Graphs," 2022 — [Paper](https://ceur-ws.org/Vol-3254/paper354.pdf)
- Danieleds et al., "GFS: a Graph-based File System Enhanced with Semantic Features," ACM 2017 — [Paper](https://dl.acm.org/doi/10.1145/3077584.3077591)
- "From Shapes to Shapes: Inferring SHACL Shapes for Results of SPARQL CONSTRUCT Queries," ACM Web Conference 2024 — [Paper](https://dl.acm.org/doi/10.1145/3589334.3645550)
- Van Assche et al., "Declarative RDF graph generation from heterogeneous data: A systematic literature review," 2022 — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1570826822000373)
- "A Declarative Formalization of R2RML Using Datalog," CEUR 2024 — [Paper](https://ceur-ws.org/Vol-4083/paper63.pdf)

### Standards & Specifications
- [R2RML: RDB to RDF Mapping Language (W3C)](https://www.w3.org/TR/r2rml/)
- [RML: RDF Mapping Language](https://rml.io/specs/rml/)
- [SPARQL 1.1 Query Language (W3C)](https://www.w3.org/TR/sparql11-query/)
- [9P Protocol (Wikipedia)](https://en.wikipedia.org/wiki/9P_(protocol))
- [SHACL (Wikipedia)](https://en.wikipedia.org/wiki/SHACL)

### Software Projects
- [SemFS — Semantic File System](http://semanticweb.org/wiki/SemFS.html)
- [rdflib-fuse — RDF Store as FUSE Filesystem](https://github.com/pchampin/rdflib-fuse)
- [GFS — Graph-based File System](https://github.com/danieleds/GFS)
- [Schímatos — SHACL-based Web-Form Generator](https://github.com/schimatos/schimatos.org)
- [Solid Project](https://solidproject.org/)
- [libferris — Virtual Filesystem](https://lwn.net/Articles/306860/)
- [D2RQ Platform](http://d2rq.org/)

### SemPKM Internal
- `models/basic-pkm/shapes/basic-pkm.jsonld` — SHACL shapes for Note, Concept, Project, Person
- `models/basic-pkm/views/basic-pkm.jsonld` — ViewSpec definitions using SPARQL
- `models/basic-pkm/ontology/basic-pkm.jsonld` — OWL ontology with `bpkm:tags`, `bpkm:body`
