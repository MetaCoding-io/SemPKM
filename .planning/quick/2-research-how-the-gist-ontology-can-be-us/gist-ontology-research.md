# gist Ontology Research: Applicability to SemPKM Mental Models

**Date:** 2026-02-24
**Version researched:** gist 14.0.0 (released 2025-10-31)
**gist namespace:** `https://w3id.org/semanticarts/ns/ontology/gist/` (prefix: `gist:`)
**gist ontology IRI:** `https://w3id.org/semanticarts/ontology/gistCore`
**Sources fetched:** `gistCore.ttl` (develop branch), release notes v14.0.0, README, style guide

---

## 1. What is gist?

### Overview

gist is Semantic Arts' **minimalist upper ontology for the enterprise**. The design goal is maximum coverage of typical business and knowledge-domain concepts with the fewest primitives and the least ambiguity. It defines 96 OWL classes and ~60 object/datatype properties in a single cohesive ontology file (`gistCore.ttl`) — no sprawling module hierarchy. A small companion file (`gistMediaTypes.ttl`) provides IANA media type instances. A `gistPrefixDeclarations.ttl` file defines shared prefix declarations using SHACL's `sh:PrefixDeclaration` pattern.

### Version and License

| Field | Value |
|-------|-------|
| Latest release | v14.0.0 (October 2025) |
| License | **Creative Commons Attribution 4.0 International (CC BY 4.0)** |
| Namespace | `gist: <https://w3id.org/semanticarts/ns/ontology/gist/>` |
| OWL standard | OWL 2 DL |
| Serialization | RDF Turtle |

The CC BY 4.0 license requires attribution and that gist terms remain in the `gist:` namespace. Users may **not** define their own terms in the gist namespace.

### Design Philosophy

gist takes a deliberate minimalism stance:

- **Fewest primitives:** Only define a class if it meaningfully constrains how instances should be modeled. Avoid abstract classes users would never instantiate.
- **No domain-specific vocabulary:** gist covers general enterprise concepts (agents, events, time, content, agreements) and leaves domain-specific types to downstream ontologies built on gist.
- **Category vs. Class:** gist explicitly distinguishes between `gist:Category` (folksonomy-style tags, lightly structured) and `owl:Class` (formally constrained types). This is a key design pattern for flexible knowledge modeling.
- **OWL 2 DL conformance:** All axioms stay within OWL 2 DL to support reasoner compatibility. Importing `gistPrefixDeclarations.ttl` explicitly breaks DL conformance and must be done intentionally.

### Module Structure

gist is effectively a single-module ontology:

| File | Purpose |
|------|---------|
| `ontologies/gistCore.ttl` | All 96 classes, ~60 properties, instance data for Aspects |
| `ontologies/gistMediaTypes.ttl` | IANA media type instances as `gist:MediaType` individuals (imports gistCore) |
| `ontologies/gistPrefixDeclarations.ttl` | SHACL `sh:PrefixDeclaration` instances for tooling; breaks OWL DL if imported |
| `ontologies/gistValidationAnnotations.ttl` | Validation annotation properties |

There is no separate module for agents, events, time, etc. — everything is in `gistCore.ttl`. This is intentional: gist's modularity comes from selective use of classes, not from splitting the ontology.

---

## 2. Core Concepts Relevant to SemPKM

### 2.1 Agents: Person and Organization

**`gist:Person`**

```turtle
gist:Person a owl:Class ;
  skos:definition "A human being who was or is alive." ;
  skos:prefLabel "Person" .
```

`gist:Person` is a subclass of `gist:LivingThing`, which is a subclass of `gist:PhysicalIdentifiableItem`. The formal definition requires biological parents (OWL restriction), making it strictly biological persons. Fictional characters are an explicitly stated negative example.

*SemPKM relevance:* `bpkm:Person` could align with `gist:Person` via `rdfs:subClassOf` for real contacts. However, the biological-parent restriction means this is semantically narrower than "a person known to the user" — which may include fictional, historical, or abstract agents.

**`gist:Organization`**

```turtle
gist:Organization a owl:Class ;
  skos:definition "A structured entity formed to achieve specific goals, typically involving members with defined roles." ;
  skos:prefLabel "Organization" .
```

Top-level class. Examples include legal entities (companies), non-legal entities (clubs, committees, departments). Can also have organization-members (as in the United Nations).

*SemPKM relevance:* Highly relevant for future Mental Models tracking companies, teams, or institutions. No equivalent in current Basic PKM.

**`gist:TemporalRelation`**

```turtle
gist:TemporalRelation a owl:Class ;
  skos:definition "A relationship existing for a period of time." ;
  skos:prefLabel "Temporal Relation" .
```

Represents time-bounded relationships between agents — e.g., employment periods, address history. Requires `gist:startDateTime` and at least two `gist:hasParticipant` values.

*SemPKM relevance:* Parallels `sempkm:Edge` for time-bounded relationships, but carries OWL cardinality constraints that `sempkm:Edge` avoids.

---

### 2.2 Tasks and Projects

**`gist:Task`**

```turtle
gist:Task a owl:Class ;
  owl:equivalentClass [
    owl:intersectionOf (gist:Event
      [ owl:onProperty gist:hasGoal; owl:someValuesFrom gist:Intention ])
  ] ;
  skos:definition "An activity or piece of work that is either proposed, planned, scheduled, underway, or completed." ;
  skos:prefLabel "Task" .
```

Key insight: `gist:Task` is formally defined as a `gist:Event` that `gist:hasGoal` some `gist:Intention`. This means tasks are **events with purpose** — not just activities but purposeful ones. Use `gist:isBasedOn` to link a task to a `gist:TaskTemplate` (its process template).

**`gist:Project`**

```turtle
gist:Project a owl:Class ;
  owl:equivalentClass [
    owl:intersectionOf (gist:Task
      [ owl:inverseOf gist:isPartOf; owl:someValuesFrom gist:Task ])
  ] ;
  skos:definition "A task, usually of longer duration, made up of other tasks." .
```

A `gist:Project` is formally a `gist:Task` that has at least one sub-task. The hierarchy is: `gist:Project rdfs:subClassOf gist:Task rdfs:subClassOf gist:Event`.

*SemPKM relevance:* `bpkm:Project` maps naturally to `gist:Project`. However, gist's formal definition requires sub-tasks to be a project — a lone-task project would not qualify. For SemPKM's looser "project = initiative", this is either acceptable (use `gist:Task` instead) or should be an `rdfs:subClassOf gist:Task` without the equivalence axiom.

**`gist:ScheduledTask`**

```turtle
gist:ScheduledTask a owl:Class ;
  owl:equivalentClass [
    owl:intersectionOf (gist:ScheduledEvent gist:Task) ] ;
  skos:definition "A task with a planned start datetime." .
```

*SemPKM relevance:* Directly relevant for task-tracking Mental Models where due dates matter.

**`gist:TaskTemplate`**

```turtle
gist:TaskTemplate a owl:Class ;
  skos:definition "An outline of a task of a particular type, which is the basis for executing such tasks." .
```

Use `gist:isBasedOn` to link a task instance back to its template.

*SemPKM relevance:* Relevant for workflow/process Mental Models (not in Basic PKM but planned).

---

### 2.3 Events and Time

**`gist:Event`**

```turtle
gist:Event a owl:Class ;
  skos:definition "Something that occurs over a period of time, often characterized as an activity carried out by some person, organization, or software application or brought about by natural forces." .
```

`gist:Event` is **disjoint** with: `gist:Language`, `gist:Magnitude`, `gist:TimeInterval`, `gist:UnitOfMeasure`. Also disjoint with `gist:Category` (v14.0.0 added explicit disjointness axioms).

Event subclass hierarchy:
- `gist:Event`
  - `gist:ContemporaryEvent` — started but not ended
  - `gist:ContingentEvent` — has probability of happening in future
  - `gist:HistoricalEvent` — ended before now
  - `gist:PhysicalEvent` — occurred at a place
  - `gist:ScheduledEvent` — has a planned start datetime
    - `gist:ScheduledTask` (= ScheduledEvent + Task)
  - `gist:Task` (= Event + hasGoal some Intention)
    - `gist:Project` (= Task + has subtask)
  - `gist:Determination` — establishes a result by research/measuring
  - `gist:Transaction` — exchange or transfer of goods/services/funds

*SemPKM relevance:* `sempkm:Event` (the event-sourcing construct) is NOT the same as `gist:Event`. SemPKM's `sempkm:Event` is a write-path record (like a journal entry), while `gist:Event` is a domain occurrence. These should remain separate to avoid semantic collision.

**`gist:TimeInterval`**

```turtle
gist:TimeInterval a owl:Class ;
  skos:definition "A span of time with a known start time, end time, and duration." .
```

Requires exactly one `gist:startDateTime`, one `gist:endDateTime`, and one `gist:hasMagnitude` for duration. Ongoing states (unknown end) are explicitly excluded.

**Temporal property hierarchy** (datatype properties on Events):

| Property | Precision | Use case |
|----------|-----------|----------|
| `gist:actualStartDateTime` | Full datetime | High-precision event logging |
| `gist:actualStartDate` | Day | Projects, tasks, milestones |
| `gist:actualStartMinute` | Minute | Meetings, calls |
| `gist:actualStartYear` | Year | Historical records |
| `gist:plannedStartDate` | Day | Planned tasks |
| `gist:plannedEndDate` | Day | Deadlines |
| `gist:actualStartMicrosecond` | Microsecond | System timestamps |

*SemPKM relevance:* `gist:actualStartMicrosecond` / `gist:actualEndMicrosecond` are designed for system timestamps — directly applicable to event sourcing timestamp precision.

---

### 2.4 Content and Notes

**`gist:Content`**

```turtle
gist:Content a owl:Class ;
  skos:definition "Information available in some medium." ;
  skos:example "A document, program, image." .
```

Top-level class. Disjoint with `gist:Organization`, `gist:PhysicalIdentifiableItem`, and others.

**`gist:ContentExpression`** (subclass of `gist:Content`)

```turtle
gist:ContentExpression a owl:Class ;
  skos:definition "Intellectual property reduced to text, audio, etc." .
```

Must be categorized by a `gist:GeneralMediaType`. It is the "rendered form" of intellectual property.

**`gist:Text`** (subclass of `gist:ContentExpression`)

```turtle
gist:Text a owl:Class ;
  skos:definition "Content expressed as a written sequence of characters." .
```

Formally: a `gist:ContentExpression` expressed in a `gist:Language` with `gist:containedText` value. Photographs of text are explicitly excluded.

**`gist:FormattedContent`** (subclass of `gist:ContentExpression`)

```turtle
gist:FormattedContent a owl:Class ;
  skos:definition "Content which is in a particular format." ;
  skos:example "An HTML website, a PDF document, a JPG image." .
```

Formally: a `gist:ContentExpression` expressed in a specific `gist:MediaType`.

**`gist:Message`** (subclass of `gist:ContentExpression`)

```turtle
gist:Message a owl:Class ;
  skos:definition "A specific instance of content sent from a sender to at least one other recipient." .
```

*SemPKM relevance:* `bpkm:Note` could use `rdfs:subClassOf gist:Text` or `gist:FormattedContent`. Since notes have Markdown bodies, `gist:FormattedContent` is the closer fit (Markdown is a media type: `text/markdown`). However, this would require gist import and OWL inference to realize class membership.

**`gist:IntellectualProperty`**

```turtle
gist:IntellectualProperty a owl:Class ;
  skos:definition "An intangible work, invention, or concept, independent of its being expressed in text, audio, video, image, or live performance." .
```

*SemPKM relevance:* Conceptually: the idea behind a note vs. its textual expression. Not directly useful in Basic PKM but foundational for document management Mental Models.

---

### 2.5 Knowledge Concepts and Classification

**`gist:KnowledgeConcept`** (new in v14.0.0)

```turtle
gist:KnowledgeConcept a owl:Class ;
  rdfs:subClassOf gist:IntellectualProperty ;
  skos:definition "An abstract concept that arises from the distillation of experience. It is similar to a category but, rather than being a simple tag, it has rich structure." ;
  skos:example "Most domains will define a few subclasses, such as gene, protein, chemical, disease, subject matter, industry, method." .
```

*SemPKM relevance:* **Directly maps to `bpkm:Concept`**. `bpkm:Concept` is currently a subclass of `skos:Concept`. `gist:KnowledgeConcept` provides an alternative or complementary superclass that more explicitly models the "rich structured concept" idea vs. the folksonomy-tag idea.

**`gist:Category`**

```turtle
gist:Category a owl:Class ;
  skos:definition "A concept or label used to categorize other instances without specifying any formal semantics." ;
  skos:scopeNote "Often a type can be modeled either as an owl:Class or as a gist:Category. Use the latter if you don't care much about the formal structure of the different types, or if there is a whole hierarchy of types that are going to be managed by a group separate from the ontology developers." .
```

*SemPKM relevance:* `gist:Category` is the gist way to express "tags and informal classification" — exactly what `bpkm:Concept` currently serves. The scope note explicitly addresses the owl:Class vs. gist:Category choice, which mirrors the same decision in SemPKM Mental Models.

**`gist:Tag`** (subclass of `gist:Category`)

```turtle
gist:Tag a owl:Class ;
  skos:definition "A term in a folksonomy used to categorize things. Tags can be made up on the fly by users." ;
  skos:prefLabel "Tag" .
```

Has `gist:containedText` (its string value). `gist:Tag` instances can be created by users; `gist:Category` instances are managed/governed.

*SemPKM relevance:* `bpkm:tags` is currently a `xsd:string` datatype property (comma-separated). Replacing this with `gist:Tag` instances would give tags their own identity, reusability, and graph connectivity.

**`gist:ControlledVocabulary`**

```turtle
gist:ControlledVocabulary a owl:Class ;
  skos:definition "A collection of terms approved and managed by some organization or person." ;
  skos:scopeNote "A controlled vocabulary is similar to a skos:ConceptScheme, but it could also be used for things that are not concepts, such as organizations, US presidents, geographic regions, etc." .
```

*SemPKM relevance:* Useful for managed ontologies / lookup tables in Mental Models (e.g., a defined set of project statuses, relationship types).

---

### 2.6 Relationships and Graph Structure

**`gist:Network`** (subclass of `gist:Composite`)

```turtle
gist:Network a owl:Class ;
  skos:definition "A composite consisting of nodes connected by links." ;
  skos:example "A social network would consist of related person or organization members (or their proxies, such as accounts)." .
```

**`gist:NetworkNode`** — a node in a network. Member of a `gist:Network`.
**`gist:NetworkLink`** — connects exactly two `gist:NetworkNode` instances. Has `gist:links`, `gist:linksFrom`, `gist:linksTo` properties.

*SemPKM relevance:* The `gist:Network` / `gist:NetworkNode` / `gist:NetworkLink` pattern parallels `sempkm:Edge`. However, `sempkm:Edge` is a first-class event-sourced resource with its own subject/predicate/object triple, while `gist:NetworkLink` is a structural relationship. These are different concerns.

**Key structural properties:**

| Property | Type | Definition |
|----------|------|------------|
| `gist:isPartOf` | ObjectProperty (Transitive) | Part-whole where part has independent existence |
| `gist:isDirectPartOf` | ObjectProperty | Direct (non-transitive) part-whole |
| `gist:isMemberOf` | ObjectProperty | Member of a collection or organization |
| `gist:hasParticipant` | ObjectProperty | Something involved in an event or agreement |
| `gist:hasParty` | ObjectProperty | Person/org participating in event/agreement/obligation |
| `gist:isBasedOn` | ObjectProperty | Template-instance relationship |
| `gist:refersTo` | ObjectProperty | General reference/pointer |
| `gist:links` | ObjectProperty | NetworkLink connects to NetworkNode |
| `gist:precedes` | ObjectProperty | Generic ordering |
| `gist:precedesDirectly` | ObjectProperty | Immediate ordering (direct predecessor) |

---

### 2.7 Temporal and Magnitude System

**`gist:Magnitude`** — the amount of a measurable characteristic. Has `gist:numericValue` and `gist:hasAspect` (linking to a defined `gist:Aspect`).

**`gist:Aspect`** — a measurable characteristic (duration, area, mass). Pre-defined instances:
- `gistd:_Aspect_duration`
- `gistd:_Aspect_area`
- `gistd:_Aspect_altitude`
- `gistd:_Aspect_monetary_value`

**`gist:UnitGroup`** — a collection of units that measure the same aspect (e.g., all time units).

**`gist:UnitOfMeasure`** — standard amount for measurement.

*SemPKM relevance:* The magnitude/aspect system is designed for scientific/engineering use. For PKM event timestamps, the simpler `xsd:dateTime` (already used by SemPKM via `dcterms:created`/`dcterms:modified`) is sufficient. The magnitude system is overkill for PKM use cases.

---

### 2.8 Annotation and Labeling Properties

**`gist:name`** (DatatypeProperty) — relates an individual to its name(s).
**`gist:description`** (DatatypeProperty) — describes instance attributes/characteristics (not a definition; gist reserves `skos:definition` for ontological definitions).
**`gist:containedText`** (DatatypeProperty) — string closely associated with an individual.
**`gist:uniqueText`** (DatatypeProperty, subproperty of `gist:containedText`) — unique string for an individual; functional property.

*SemPKM relevance:* SemPKM's label service already uses `dcterms:title`, `rdfs:label`, `skos:prefLabel`, `schema:name`. These overlap conceptually with `gist:name`. No need to adopt `gist:name` unless aligning with gist classes that formally use it.

---

## 3. Alignment with SemPKM Mental Model Design

### 3.1 Class Alignment Map

| SemPKM / Basic PKM | gist equivalent | Alignment strategy | Notes |
|--------------------|-----------------|-------------------|-------|
| `bpkm:Project` | `gist:Project` | `rdfs:subClassOf gist:Task` | gist:Project requires sub-tasks; use Task if stricter definition causes issues |
| `bpkm:Person` | `gist:Person` | `rdfs:subClassOf gist:Person` | gist:Person requires biological parents (OWL restriction) — acceptable for real people |
| `bpkm:Note` | `gist:Text` or `gist:FormattedContent` | `rdfs:subClassOf gist:FormattedContent` | Markdown body = formatted content; requires gist import |
| `bpkm:Concept` | `gist:KnowledgeConcept` | `rdfs:subClassOf gist:KnowledgeConcept` | Better fit than gist:Category for rich structured concepts |
| `sempkm:Edge` | `gist:NetworkLink` (partial) | None recommended | Different semantics; sempkm:Edge is event-sourced, gist:NetworkLink is structural |
| `sempkm:Event` | `gist:Event` (partial) | None recommended | Name collision; sempkm:Event = write record, gist:Event = domain occurrence |

### 3.2 Property Alignment Map

| SemPKM property | gist property | Recommendation |
|-----------------|---------------|---------------|
| `bpkm:hasParticipant` | `gist:hasParticipant` | Rename `bpkm:hasParticipant` to align with gist semantics (or import gist:hasParticipant directly) |
| `bpkm:body` | `gist:containedText` | bpkm:body is more specific (Markdown); keep as-is |
| `bpkm:isAbout` | `gist:refersTo` | Conceptually similar; keep `bpkm:isAbout` for clarity |
| `bpkm:tags` (string) | `gist:Tag` (class) | Migrate from string tags to `gist:Tag` instances for graph connectivity |
| `dcterms:created` | `gist:actualStartDate` | Keep dcterms:created for compatibility; use gist:actualStartDate only if adopting gist:Task |

### 3.3 Mental Model Bundle vs. gist Module Structure

SemPKM Mental Models bundle: ontology + SHACL shapes + views + seed data. gist is a single shared ontology with no bundled shapes or views.

The alignment question is: **where does gist fit in the SemPKM bundle architecture?**

Three options:

**Option A: Mental Model imports gist directly**
Each Mental Model's ontology file includes `owl:imports <https://w3id.org/semanticarts/ontology/gistCore14.0.0>`. The full gist ontology (96 classes, ~60 properties) is loaded into RDF4J as part of every model install.

- Pros: Full gist vocabulary available; OWL inference works
- Cons: Every Mental Model carries the full gist dependency; gist version pinning required; OWL inference cost

**Option B: gist as a system-level shared ontology**
gist is loaded once into a dedicated named graph in RDF4J, shared across all models. Mental Models declare `rdfs:subClassOf gist:SomeClass` without needing to import the ontology file.

- Pros: Single copy; version managed centrally; no import chains
- Cons: Outside the current Mental Model bundle model; requires system-level ontology management

**Option C: Vocabulary alignment without import**
Mental Model ontologies use `rdfs:subClassOf` and `owl:equivalentClass` to express relationships to gist IRIs without actually importing gist. This is "alignment" rather than "extension."

- Pros: No import dependency; works with SHACL-only approach; gist serves as documentation
- Cons: OWL inference won't realize gist class memberships; purely semantic annotation

**Recommendation:** Option C first, Option B later. For SemPKM v2.0, use alignment annotations (`rdfs:subClassOf gist:Task`) in Mental Model ontologies without importing gist. If/when OWL inference is added to SemPKM, revisit Option B.

### 3.4 OWL Inference Requirement

gist's formal definitions use `owl:equivalentClass` with complex class expressions. For example:

- `gist:Project` is formally equivalent to `gist:Task` with sub-tasks
- `gist:Task` is formally equivalent to `gist:Event` with a goal
- `gist:Message` is formally equivalent to `gist:ContentExpression` sent from/to an agent

To realize these inferences (e.g., for a `bpkm:Project` to be recognized as a `gist:Project`), an OWL 2 DL reasoner (HermiT, Pellet, Konclude) is required.

**RDF4J's built-in inference** supports only RDFS and basic OWL axioms (rdfs2-based). It will not fire `owl:equivalentClass` with complex intersection bodies.

**SHACL-only viability:** Yes. If SemPKM Mental Models use gist via subclass alignment (Option C) rather than equivalence axioms, SHACL shapes work fine without OWL inference. The `rdfs:subClassOf gist:Task` annotation documents the semantic intent; SHACL shapes enforce the constraints independently.

---

## 4. Potential gist-based Mental Models

### 4.1 "Project Tracker" Mental Model (gist:Task + gist:Project)

**Name:** `project-tracker`
**Description:** A task and project management Mental Model with planned/actual dates, priorities, and assignees.

**gist modules used:**
- `gist:Task`, `gist:Project`, `gist:ScheduledTask`, `gist:TaskTemplate`
- `gist:Person`, `gist:Organization`
- `gist:Assignment` (new in v14.0.0) — temporal assignment of person to task
- `gist:plannedStartDate`, `gist:plannedEndDate`, `gist:actualStartDate`, `gist:actualEndDate`
- `gist:hasGoal`, `gist:hasParticipant`, `gist:isPartOf`, `gist:isBasedOn`

**Ontology sketch:**

```turtle
@prefix pt: <urn:sempkm:model:project-tracker:> .
@prefix gist: <https://w3id.org/semanticarts/ns/ontology/gist/> .

pt:Task rdfs:subClassOf gist:Task ;
  rdfs:label "Task" .

pt:Project rdfs:subClassOf gist:Task ;
  rdfs:label "Project" .

pt:Milestone rdfs:subClassOf gist:ScheduledEvent ;
  rdfs:label "Milestone" .

pt:Priority rdfs:subClassOf gist:Category ;
  rdfs:label "Priority" .
```

**SHACL shapes would define:**
- `pt:Task`: `dcterms:title` (required), `pt:status` (in: todo/doing/done), `gist:plannedEndDate` (optional), `gist:hasParticipant` (optional, range: pt:Person)
- `pt:Project`: same as Task plus `gist:isPartOf` for parent projects

**Seed data:** Priority categories (Low, Medium, High, Critical), Status categories (Todo, In Progress, Done, Cancelled)

---

### 4.2 "Contacts and Organizations" Mental Model (gist:Person + gist:Organization)

**Name:** `contacts`
**Description:** A rich contacts book supporting both persons and organizations with temporal relationships (employment, membership).

**gist modules used:**
- `gist:Person`, `gist:Organization`
- `gist:TemporalRelation`, `gist:Assignment`
- `gist:ElectronicAddress`, `gist:PhysicalAddress`
- `gist:hasAddress`, `gist:hasParticipant`, `gist:isMemberOf`
- `gist:birthDate`, `gist:name`

**Ontology sketch:**

```turtle
@prefix co: <urn:sempkm:model:contacts:> .
@prefix gist: <https://w3id.org/semanticarts/ns/ontology/gist/> .

co:Contact rdfs:subClassOf gist:Person ;
  rdfs:label "Contact" .

co:Company rdfs:subClassOf gist:Organization ;
  rdfs:label "Company" .

co:Employment rdfs:subClassOf gist:TemporalRelation ;
  rdfs:label "Employment" .
  # Employment links a Contact to a Company over a time period
```

**SHACL shapes would define:**
- `co:Contact`: `gist:name` (required), `foaf:email` or `gist:hasAddress` (optional), `gist:birthDate` (optional)
- `co:Company`: `gist:name` (required), `gist:hasAddress` (optional)
- `co:Employment`: `gist:startDateTime` (required), `gist:endDateTime` (optional), `gist:hasParticipant` min 2

**Integration with Basic PKM:** `bpkm:Person` could link to `co:Contact` via cross-model reference, or the `contacts` model could replace `bpkm:Person`.

---

### 4.3 "Knowledge Base" Mental Model (gist:KnowledgeConcept + gist:Text)

**Name:** `knowledge-base`
**Description:** A structured knowledge base with rich concept hierarchy, document types, and semantic tagging.

**gist modules used:**
- `gist:KnowledgeConcept`, `gist:Category`, `gist:Tag`, `gist:ControlledVocabulary`
- `gist:Text`, `gist:FormattedContent`, `gist:ContentExpression`
- `gist:isCategorizedBy`, `gist:hasBroader`, `gist:hasDirectBroader`, `gist:isBasedOn`

**Ontology sketch:**

```turtle
@prefix kb: <urn:sempkm:model:knowledge-base:> .
@prefix gist: <https://w3id.org/semanticarts/ns/ontology/gist/> .

kb:Article rdfs:subClassOf gist:FormattedContent ;
  rdfs:label "Article" .

kb:Topic rdfs:subClassOf gist:KnowledgeConcept ;
  rdfs:label "Topic" .

kb:Domain rdfs:subClassOf gist:Discipline ;
  rdfs:label "Domain" .
```

**SHACL shapes would define:**
- `kb:Article`: `dcterms:title` (required), `kb:body` (Markdown, required), `gist:isCategorizedBy` (range: `kb:Topic`)
- `kb:Topic`: `skos:prefLabel` (required), `gist:hasBroader` (range: `kb:Topic`, optional — for topic hierarchy)
- `kb:Domain`: `skos:prefLabel` (required)

**Seed data:** Top-level domains (Science, Technology, Philosophy, History, etc.), media type instances

---

## 5. Integration Considerations

### 5.1 License Compatibility

| License | Type | Attribution required | Namespace restriction |
|---------|------|---------------------|----------------------|
| gist 14.0.0 | CC BY 4.0 | Yes — credit Semantic Arts | Yes — do not define in `gist:` namespace |
| SemPKM | (private/TBD) | N/A | N/A |

**Result: Compatible.** CC BY 4.0 allows commercial use, modification, and distribution. The requirements are:
1. Include attribution to Semantic Arts in documentation/about pages
2. Never mint new IRIs in the `gist:` namespace (`https://w3id.org/semanticarts/ns/ontology/gist/`)

SemPKM Mental Models would define their own types in model-specific namespaces (e.g., `urn:sempkm:model:basic-pkm:`) and use `rdfs:subClassOf` to align with gist, which is explicitly permitted.

### 5.2 OWL Inference Requirement

**Summary:** gist's complex `owl:equivalentClass` expressions require OWL reasoning for full semantic benefit. Without a reasoner:

- `rdfs:subClassOf` annotations work — SPARQL queries for subclasses still return results if RDF4J's RDFS inference is enabled
- `owl:equivalentClass` used for documentation only — no automatic classification
- SHACL shapes provide constraint enforcement independently of OWL reasoning

**RDF4J inference options:**
- `schema:RDFS` — basic RDFS inference (subclass/subproperty chains); sufficient for `rdfs:subClassOf` alignment
- `schema:OWL_SCHEMAGEN` or custom ruleset — needed for `owl:equivalentClass` inference

**Recommendation:** Use RDF4J's RDFS inference (already likely active in SemPKM). This handles `rdfs:subClassOf` alignment chains. Defer OWL inference until there's a concrete use case requiring it (e.g., automatic classification of bpkm:Project as gist:Project).

### 5.3 Namespace Conflicts

SemPKM's existing namespaces:

| Prefix | Namespace |
|--------|-----------|
| `sempkm:` | `https://pkm.example.com/ont/` (system types: Edge, Event, Command) |
| `bpkm:` | `urn:sempkm:model:basic-pkm:` (Basic PKM model types) |
| `dcterms:` | `http://purl.org/dc/terms/` |
| `skos:` | `http://www.w3.org/2004/02/skos/core#` |
| `schema:` | `https://schema.org/` |

The `gist:` namespace (`https://w3id.org/semanticarts/ns/ontology/gist/`) does not conflict with any existing SemPKM namespace.

**Property name collision risk:** `bpkm:hasParticipant` replicates `gist:hasParticipant` by name. If gist alignment is adopted, the Basic PKM model should either:
- Use `gist:hasParticipant` directly (requires gist import or copy of the property definition)
- Keep `bpkm:hasParticipant` with `rdfs:subPropertyOf gist:hasParticipant`

### 5.4 Bundled vs. Shared Ontology

**Should gist be part of a Mental Model bundle or a system-level shared ontology?**

Arguments for **bundled** (inside each Mental Model):
- Self-contained: model works without system configuration
- Explicit versioning: model pins to `gistCore14.0.0`
- No cross-model dependency management

Arguments for **system-level shared**:
- Single copy in triplestore
- Enables cross-model reasoning (gist:Person in one model = gist:Person in another)
- Cleaner IRI resolution

**Recommendation:** For now, use alignment-without-import (Option C from Section 3.3). This avoids the bundling decision entirely. If SemPKM adds a "shared vocabulary layer" feature in the future, gist is a natural first candidate for that layer.

### 5.5 SKOS vs. gist for Concept Hierarchy

SemPKM already imports `skos:` vocabulary (`skos:Concept`, `skos:prefLabel`, etc.). gist uses SKOS annotations internally (e.g., `skos:definition`, `skos:prefLabel`, `skos:scopeNote`) and provides `gist:hasBroader`/`gist:hasDirectBroader` as alternatives to `skos:broader`/`skos:narrower`.

For concept hierarchies in SemPKM Mental Models, SKOS remains the primary vocabulary. gist complements SKOS for richer concept modeling:
- `skos:Concept` for concept schemes and simple tagging
- `gist:KnowledgeConcept` for domain concepts with richer structure
- `gist:Category` for user-managed classification without formal OWL structure

---

## 6. Recommendations

### Quick Reference

| Use case | Recommendation | Confidence |
|----------|---------------|------------|
| Align `bpkm:Person` with gist | **Yes** — `rdfs:subClassOf gist:Person` | High |
| Align `bpkm:Project` with gist | **Yes** — `rdfs:subClassOf gist:Task` (not gist:Project due to sub-task requirement) | High |
| Align `bpkm:Note` with gist | **Maybe** — `rdfs:subClassOf gist:FormattedContent` adds complexity for little current benefit | Medium |
| Align `bpkm:Concept` with gist | **Yes** — `rdfs:subClassOf gist:KnowledgeConcept` (new in v14) is an excellent fit | High |
| Import gist into Mental Models | **No, not yet** — use alignment without import until OWL inference is added | High |
| Use gist as system-level vocabulary | **Maybe** — good future direction; requires SemPKM architectural support | Medium |
| Use `gist:Task`/`gist:Project` in new tracker Mental Model | **Yes** — this is precisely gist's sweet spot | High |
| Replace `bpkm:tags` string with `gist:Tag` instances | **Yes** — provides graph connectivity; migration needed | Medium |
| Use `gist:TemporalRelation` for time-bounded edges | **Maybe** — only if Building temporal relationship tracking into a model | Low |
| Adopt gist magnitude/unit system for timestamps | **No** — `xsd:dateTime` + `dcterms:created` is simpler and already in use | High |

---

### Recommended Next Steps

**Immediate (can do now, low effort):**

1. **Add gist alignment annotations to Basic PKM ontology** — add `rdfs:subClassOf` triples to `basic-pkm.jsonld`:
   ```json
   {
     "@id": "bpkm:Project",
     "@type": "owl:Class",
     "rdfs:subClassOf": { "@id": "gist:Task" }
   }
   ```
   This is documentation-level alignment with no functional change. Provides semantic grounding for future tooling.

2. **Mint a "Project Tracker" Mental Model concept** — the gist `gist:Task` + `gist:ScheduledTask` + `gist:Assignment` combination is a ready-made vocabulary for a future task/project Mental Model. Document this as a planned future model.

3. **Replace `bpkm:tags` (string) with `gist:Tag` (class)** — `bpkm:tags` is a comma-separated string, an antipattern for an RDF knowledge graph. Replacing it with an object property linking to `gist:Tag` instances would enable:
   - SPARQL queries over tag-connected objects
   - Tag browsing in the graph view
   - Tag autocomplete from existing instances

**Medium-term (with system design):**

4. **System-level shared vocabulary named graph** — create a dedicated RDF4J named graph (e.g., `<https://sempkm.internal/graph/shared-ontologies>`) where gist and other shared vocabularies are loaded once. Mental Models reference but do not bundle them.

5. **SHACL shapes for gist-aligned types** — once alignment is in place, write SHACL shapes that reference gist properties directly (e.g., `sh:path gist:plannedEndDate` on a project shape). This uses gist vocabulary in constraint definitions, not just as inheritance annotations.

**Longer-term (if OWL inference is added):**

6. **Enable RDF4J RDFS inference** — with `rdfs:subClassOf gist:Task` in place, enabling RDFS inference means SPARQL queries for `gist:Task` will return `bpkm:Project` instances automatically. This enables cross-model queries when multiple Mental Models align to gist.

---

### Concluding Assessment

gist is a well-designed, actively maintained ontology with a stable community and clear upgrade path (v10 through v14 in five years). Its minimalist philosophy — 96 classes covering the most common enterprise knowledge domains — aligns well with SemPKM's Mental Model architecture.

The most valuable alignment targets for SemPKM today are:

- **`gist:Task` / `gist:Project`** for task/project tracking Mental Models
- **`gist:KnowledgeConcept`** for `bpkm:Concept` / knowledge management
- **`gist:Person` / `gist:Organization`** for agent-focused Mental Models
- **`gist:Tag`** as a replacement for string-based tagging

The primary risk is OWL inference complexity: gist's formal definitions use OWL 2 DL equivalence axioms that require a reasoner for full semantic benefit. SemPKM's SHACL-only approach sidesteps this risk — alignment is used for documentation and interoperability, not for automatic classification.

**Bottom line:** Adopt gist vocabulary through `rdfs:subClassOf` alignment in new Mental Models. Do not import the full ontology until OWL inference is a system feature. The "Project Tracker" Mental Model is the highest-priority candidate for a gist-grounded design.
