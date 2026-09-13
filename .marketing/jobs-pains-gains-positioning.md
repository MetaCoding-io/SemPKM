# SemPKM Jobs / Pains / Gains & Positioning — Initial Beachhead

## Status

This is a first positioning synthesis grounded in the coded PKM complaint corpus in `pkm-complaint-corpus.csv` and direct review of SemPKM's current product capabilities.

The corpus is **purposive**, not statistically representative: discussions were selected because they were high-signal examples of structured-PKM problems. Use it to identify recurring patterns, vocabulary, and segment differences — not to estimate population prevalence.

---

# 1. Beachhead customer

## Structured-PKM System Builder

The initial beachhead is not "PKM power users" broadly and not "Obsidian users" broadly.

It is:

> **People using flexible PKM tools as structured information systems, whose metadata model has become important enough that simplifying it away would make their real work worse.**

The clearest acquisition pool is **schema-strained Obsidian system builders**.

They commonly have:

- multiple meaningful note/object types such as Paper, Person, Project, Meeting, Claim, Source, Book, Client, Server, Experiment, etc.;
- different properties expected for different types;
- templates that stand in for schemas;
- Bases, Dataview, queries, or dashboards;
- plugins such as Templater, Metadata Menu, Linter, QuickAdd, Meta Bind, or custom tooling;
- scripts/regex/AI-generated code for bulk metadata changes or migrations;
- conventions for meaningful relationships between notes;
- a strong preference for ownership, inspectability, and durable access to their information.

The qualification test is:

> **If your current PKM became too complicated, would removing most of its structure solve the problem?**

If yes, SemPKM is probably not the right product.

If no — because the domain genuinely requires Papers, Authors, Claims, Projects, People, Methods, Clients, Systems, etc. to have different properties and relationships — this is a strong prospect.

---

# 2. Customer Jobs

## Functional jobs

### J1. Represent different kinds of knowledge explicitly

The user wants the system to understand that a Paper, Person, Project, Meeting, Claim, Server, Book, Client, etc. are not merely interchangeable Markdown files with different templates.

They want different kinds of things to support different properties, relationships, constraints, and views.

### J2. Keep structured knowledge consistent as the system grows

They need to add/change properties, normalize values, change conventions, and evolve their model without manually repairing hundreds or thousands of objects.

### J3. Express meaningful relationships

They want more than "A links to B."

They want relationships such as:

- Paper **authored by** Person
- Claim **supported by** Evidence
- Project **has stakeholder** Person
- Server **runs** Service
- Book **part of** Series

and they want the system to understand those distinctions.

### J4. Query and view knowledge without rebuilding the same logic repeatedly

They want tables, boards, graphs, calendars, dashboards, queries, and filtered views over the same underlying objects.

### J5. Reuse a domain model instead of reinventing one

They want to start with a working research/project/CRM/Zettelkasten/etc. system and customize it rather than independently inventing every field, template, relationship, validation rule, and view.

### J6. Capture information without interrupting thought

They need fast notes and incomplete information to coexist with rigorous structure.

They do not want to solve an ontology problem every time they have an idea.

### J7. Preserve access and portability

They want confidence that adopting richer structure will not trap their knowledge inside one proprietary application.

For many Obsidian users, direct file access is an important part of this job.

### J8. Customize the system without becoming its full-time maintainer

They may enjoy tinkering and modeling.

They do not necessarily enjoy maintaining plugin dependencies, custom scripts, YAML migrations, duplicated query logic, and fragile conventions.

---

# 3. Customer Pains

## P1. The schema is implicit and scattered

Their "data model" is distributed across:

- YAML/frontmatter naming conventions;
- templates;
- folders;
- tags;
- Bases/Dataview queries;
- plugin configuration;
- scripts;
- documentation;
- rules remembered only by the user.

No single component actually represents the model.

**Pain language:**

> "I know these are all Books, but the application doesn't."

> "The template says what a Book looked like when I created it, not what a Book is."

## P2. Schema evolution becomes manual migration work

A new required property, renamed field, corrected value, or changed convention creates cleanup work across existing notes.

Users fall back to Python, regex, VS Code, Linter, one-off plugins, or AI-generated scripts.

**Pain language:**

> "I changed the template, but I still have 500 old notes."

## P3. Plugin composition becomes infrastructure

Different plugins supply form generation, validation, querying, metadata editing, templates, task aggregation, dashboards, etc.

The user has effectively assembled an application stack whose components have different assumptions and maintenance lifecycles.

**Pain language:**

> "Which plugin is still maintained?"

> "If this plugin disappears, how much of my system disappears with it?"

## P4. Structure creates cognitive friction at capture time

Object-centric tools sometimes force the user to choose a Type, Collection, Set, Supertag, destination, or other abstraction before the information has earned that structure.

**Pain language:**

> "I just want to write this down."

## P5. Product-specific abstractions are hard to reason about

Users repeatedly struggle with overlapping/private vocabulary such as Sets vs Collections, Relations vs Properties, tags that behave like types, and folders that behave partly like categories.

**Pain language:**

> "What exactly is the difference between these two things?"

## P6. Relationships lose meaning

Plain links are excellent for connection but weak for expressing *how* two things are connected.

Database tools often expose richer relations but with confusing directionality or duplicated reciprocal fields.

## P7. Rich structure threatens portability

The more value users put into formulas, views, relations, schemas, plugins, and application-specific behaviors, the more they fear that an export will preserve documents but lose the system.

**Pain language:**

> "Yes, I can export Markdown — but did I export my knowledge system?"

## P8. The system becomes the hobby

Some users discover that they are spending more time perfecting metadata, queries, templates, and plugins than doing the work the PKM exists to support.

This pain splits the market in two:

- **Simplifiers:** remove the structure. Not our beachhead.
- **System builders:** the structure is genuinely useful; they need better infrastructure. Our beachhead.

## P9. Object/type proliferation creates a second organization problem

Once a user discovers types, they can create too many of them, turning the type system itself into another taxonomy to manage.

---

# 4. Desired Gains

## G1. The application actually understands the user's model

A Paper remains a Paper after creation. A type is not merely the template that happened to create it.

The system can use that fact for forms, validation, relationships, views, search, automation, and future evolution.

## G2. One explicit model replaces scattered conventions

The user wants a coherent definition of:

- what kinds of things exist;
- which properties describe them;
- how they may relate;
- what rules apply;
- which views/workflows are useful.

## G3. Changes to the model can be managed as model changes

Instead of treating a metadata change as a blind global text-editing problem, the user wants schema/model evolution to be a first-class operation.

(Migration/retyping capabilities are assumed as part of the target product direction and are being researched separately.)

## G4. Rich semantics without semantic-web homework

The user gets the benefits of RDF/SHACL/SPARQL without needing those concepts in order to create a Paper, Person, or Project.

Advanced users can inspect and use the standards layer when they want it.

## G5. Structure is progressive

The user can capture first and add structure when useful rather than making classification a toll gate before writing.

## G6. Relationships have explicit meaning

The user can distinguish `authoredBy`, `supports`, `contradicts`, `worksFor`, etc. instead of relying on generic links or naming conventions.

## G7. Reusable working systems

Installing a Mental Model can provide the coherent types, relationships, constraints, views, dashboards, and seed behavior for a domain.

The user begins from a functioning system rather than a blank collection of primitives.

## G8. Files remain available as an interface

Users who value files can mount SemPKM's knowledge through the VFS as Markdown files and directories over WebDAV while the canonical model remains semantic.

This provides a stronger answer than "trust our export button."

## G9. Open semantic portability

RDF/SHACL/SPARQL preserve more than document contents: they provide a standards-based representation of the model itself.

The desired promise is both:

- **human-readable access** through files/VFS;
- **machine-readable semantic portability** through open standards.

## G10. Tinkering moves up a level

Instead of tinkering with the plumbing required to emulate structured data, advanced users can tinker with the thing they actually care about: the model of their domain.

---

# 5. Job → Pain → SemPKM Value Map

| Customer job | Current pain | SemPKM mechanism | Customer value |
|---|---|---|---|
| Define meaningful kinds of things | Types are implicit in folders/tags/templates | Mental Models + RDF classes + SHACL shapes | The application knows what an object is |
| Keep objects consistent | Schema spread across templates/plugins/scripts | SHACL-driven forms and validation | Fewer silent inconsistencies; one explicit source of structure |
| Evolve the system | Existing notes do not follow new template conventions | Model/version migration direction | Treat changes as model evolution, not regex cleanup |
| Connect knowledge meaningfully | Generic links lose relationship semantics | Typed relationships / edges | Query and reason about *how* things connect |
| Get useful views | Repeated Dataview/Bases/plugin configuration | Model-defined and user-defined views/renderers | Multiple views over one semantic source |
| Start with a known methodology | Rebuild every workflow manually | Installable Mental Models | Reusable PKM systems rather than setup recipes |
| Capture quickly | Structured apps ask too many questions up front | Progressive formalization / simple capture direction | Structure does not block thought |
| Keep ownership/escape hatches | Rich structure often disappears on export | RDF standards + VFS Markdown/WebDAV projection | Preserve both semantic meaning and file access |
| Customize deeply | Plugin stacks become maintenance work | Explicit model + integrated platform | Tinker with meaning rather than plumbing |

---

# 6. Alternatives and Competitive Positioning Matrix

SemPKM should be positioned against the *customer's current way of solving the job*, not merely against named apps.

| Alternative | Why users choose it | Where it breaks for beachhead | SemPKM difference |
|---|---|---|---|
| **Plain/simple Obsidian** | Maximum simplicity, Markdown ownership, excellent linking | Not a problem if user does not need formal structure | Do not compete. This is often the correct solution for the wrong segment. |
| **Heavily customized Obsidian** | Files + flexibility + huge plugin ecosystem | Schema is distributed across YAML/templates/plugins/scripts; evolution and validation become engineering work | Make the model explicit and integrated while retaining a file interface through VFS |
| **Obsidian Bases + properties** | First-party structured views without abandoning Markdown | Useful structure, but note type/schema semantics remain weaker than a first-class model | Types, constraints and relationships are first-class semantics rather than inferred from query/filter conventions |
| **Tana** | Powerful typed Supertags, fields, queries, structured capture | Conceptual learning curve; structure can become rigid/proliferate | Open semantic foundation + simple vocabulary + progressive structure + self-hosting/file projection |
| **Capacities** | Friendly object-first UX | Users still struggle with object/type/tag/collection distinctions; closed application semantics | Explicit open model, typed relations, Mental Models, RDF/SHACL, VFS |
| **Anytype** | Local-first object system, types/properties/queries, ownership ethos | Private vocabulary/abstraction complexity; migration can preserve documents while losing linked semantics | Ordinary-language model over standard semantics; semantic portability + VFS |
| **Notion databases** | Mature database UI, relations, formulas, collaborative views | Export can preserve text while losing views/associations/system behavior; less local/open | Knowledge-model portability, typed graph relationships, self-hosting/open standards |
| **Build a custom database/app** | Exact domain model and behavior | Expensive; user becomes software maintainer | Many benefits of a domain application with a reusable PKM interface and model layer |

---

# 7. Positioning Hypothesis

## Market category

Do **not** lead with "RDF knowledge graph tool."

Do not reduce SemPKM to "another note-taking app" either.

A useful working category is:

> **Structured personal knowledge system**

or, for more technical audiences:

> **A personal knowledge application platform built around reusable semantic models.**

The category wording still needs testing.

## Target

> For advanced PKM users whose vault has become a structured information system...

## Problem

> ...and who are maintaining its schema through templates, properties, plugins, queries, and scripts...

## Differentiated solution

> SemPKM makes that model explicit through installable Mental Models: types, meaningful relationships, constraints, views, and workflows that the application actually understands.

## Reason to believe

> SemPKM is backed by RDF, SHACL, and SPARQL; provides typed relationships, validation, multiple views and an open query layer; can be self-hosted; and can project knowledge as Markdown files/directories through its WebDAV VFS.

## Positioning statement — working version

> **For PKM system builders whose vault has become a home-grown database or application, SemPKM turns scattered templates, YAML conventions, plugins, and scripts into an explicit Mental Model the application actually understands — while preserving open semantic data and a Markdown/file interface when you want it.**

This is deliberately descriptive rather than homepage copy.

---

# 8. Messaging Territories to Test

These are hypotheses for message testing, not final slogans.

## Territory A — "Your vault already has a schema"

> **Your PKM already has a schema. Make it explicit.**

Best for users already maintaining typed frontmatter, templates and queries.

### Supporting message

You've already decided what a Paper, Person, Project or Claim should contain. SemPKM lets the application understand those rules rather than scattering them across templates and plugins.

## Territory B — "Stop maintaining the system by hand"

> **You've designed a data model. Why are you maintaining it with YAML and scripts?**

Best for the schema-drift/migration pain.

### Supporting message

Make your types, relationships, constraints and views part of the model rather than conventions only your current toolchain understands.

## Territory C — "Reusable PKM systems"

> **Mental Models turn a PKM methodology into an installable system.**

Best for explaining the product's differentiated abstraction.

### Supporting message

Install Research, CRM, Zettelkasten or another Mental Model and start with coherent types, relationships, rules and views instead of rebuilding the methodology from plugins and templates.

## Territory D — "Meaningful relationships"

> **Don't just link your notes. Say how they relate.**

Best for graph/research-oriented users.

### Supporting message

A Paper can `support` a Claim, a Person can `author` a Paper, and one Claim can `contradict` another. Those relationships remain queryable data rather than prose conventions.

## Territory E — "Structure without surrendering files"

> **A knowledge graph when you need meaning. Markdown files when you want files.**

Best for Obsidian/local-first audiences concerned about leaving file-native systems.

### Supporting message

SemPKM's VFS can project your objects into Markdown files and directories over WebDAV while open RDF preserves the richer semantic model underneath.

---

# 9. What NOT to say

## Avoid: "More powerful than Obsidian"

Wrong battle. Obsidian's simplicity and file model are genuine strengths, and many users should remain there.

## Avoid: "You need an ontology"

The user needs a coherent model of their information. The implementation being an ontology is a reason-to-believe for advanced users, not the initial job.

## Avoid: "Replace your files with objects"

Files are part of the beachhead's trust model. SemPKM can provide both an object model and a file projection.

## Avoid: "No more tinkering"

Many target users enjoy tinkering. The promise is not zero customization; it is moving customization from fragile plumbing to explicit domain modeling.

## Avoid: "Organize everything"

Too generic. The beachhead problem is specifically the point where meaningful structure has outgrown conventions.

## Avoid: leading with every SemPKM feature

AI, dashboards, canvas, federation, integrations, workflows, graph views, self-hosting, auth, etc. may all matter, but the wedge is the explicit reusable model.

---

# 10. Segment Disqualifiers

Do not spend early acquisition energy on users who say:

- "I really just need Markdown plus search."
- "Whenever my system gets complicated, I delete the metadata."
- "I do not care what kind of relationship connects two notes."
- "I never query my notes or use structured properties."
- "I mainly want a prettier writing app."
- "Any database-like behavior feels like unnecessary overhead."

These are not objections we need to overcome. They indicate a poor initial fit.

Strong fit signals include:

- "I have different note types with different fields."
- "I wish changing my template updated old notes."
- "I wrote a script to clean up frontmatter."
- "Dataview/Bases is central to my system."
- "I need to distinguish different kinds of links."
- "My PKM is basically a database now."
- "I want files, but I also want a real schema."
- "I enjoy designing the model; I am tired of maintaining the plumbing."

---

# 11. Current Strategic Recommendation

## Beachhead

**Schema-strained Obsidian system builders whose work genuinely requires structured types and relationships.**

## Primary problem

Their knowledge model is valuable but implicit, scattered and expensive to maintain.

## Primary value proposition

**Make the model explicit and reusable. Let the application enforce and use it.**

## Primary differentiated mechanism

**Mental Models** — backed by open semantic standards but presented through ordinary object/type/property/relationship language.

## Critical trust response

**VFS + open RDF** — users do not have to choose between richer semantics and durable/file-oriented access.

## Critical UX requirement

**Capture first; structure when useful.** The product must not recreate the classification friction that drives users away from other object-centric PKM systems.

---

# 12. Next Validation Work

Before turning this directly into homepage copy, test the following propositions with interviews, posts, demos, and landing-page variants:

1. Do target users recognize **"your vault already has a schema"** as their problem, or is that developer language?
2. Is **schema evolution/maintenance** painful enough to motivate migration, or merely annoying?
3. Does **Mental Model** communicate reusable domain system, or require too much explanation?
4. Does the **VFS/file projection** materially reduce resistance from Obsidian users?
5. Which is stronger: **explicit types/schema**, **typed relationships**, or **reusable Mental Models** as the entry wedge?
6. How much setup/migration friction will this segment tolerate for a substantially more coherent model?
7. Does "structured PKM system builder" correlate most strongly with research, technical operations, CRM/client work, worldbuilding, personal databases, or another concrete domain?

These questions should determine the next positioning iteration rather than polishing slogans prematurely.
