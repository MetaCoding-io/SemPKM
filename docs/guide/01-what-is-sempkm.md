# Chapter 1: What is SemPKM?

SemPKM is a **semantics-native Personal Knowledge Management** platform. It stores your knowledge -- notes, concepts, projects, people, and the relationships between them -- as structured, interconnected data using open Semantic Web standards (RDF, SHACL, SPARQL). But unlike academic tools that expose this complexity directly, SemPKM wraps it in a consumer-grade interface: forms, tables, cards, and interactive graphs that feel familiar to anyone who has used Notion, Obsidian, or a modern project tracker.

The result is a knowledge base that is both human-friendly and machine-readable from day one, without requiring you to learn a single line of SPARQL or understand what a triple is.

## The Problem

Personal knowledge management tools today fall into two camps, and neither is fully satisfying.

**Free-form tools** like Obsidian, Notion, and Roam give you speed and flexibility. You can jot down a note in seconds, link pages with `[[wiki-links]]`, and organize with tags or folders. But the structure is shallow. A wiki-link between "Alice Chen" and "SemPKM Development" tells you nothing about *how* they are related -- is Alice the lead developer? A stakeholder? A critic? Your data is trapped in flat text and ad-hoc conventions that only you understand, and that break the moment you try to query, filter, or integrate with other systems.

**Academic and enterprise tools** like Protege, TopBraid, or custom RDF editors solve the structure problem. They give you ontologies, formal relationships, and validation. But they demand expertise in knowledge engineering. Creating a simple "Person" record means navigating namespace IRIs, property constraints, and RDF serialization formats. These tools are built for ontologists, not for someone who just wants to capture that Alice works at SemPKM Labs and is leading the architecture.

SemPKM bridges these two worlds. It uses the same Semantic Web standards that power enterprise knowledge graphs and linked data -- but it generates its user interface automatically from the schema, so you interact with clean forms, sortable tables, and visual graphs instead of raw triples.

## Who is SemPKM For?

- **Researchers** who need to track papers, concepts, people, and the connections between them -- and want those connections to be queryable, not just implied by proximity in a folder.
- **Knowledge workers** who manage projects, contacts, meeting notes, and reference material, and want a single system where everything links together meaningfully.
- **Teams** who need a shared knowledge base with consistent structure, where "Project" always has a status, a priority, and a list of participants -- not a free-text page that each person formats differently.
- **Anyone curious about Semantic Web technology** who wants to use it productively without first earning a degree in knowledge engineering.

## Key Differentiators

### Structure Without Rigidity

SemPKM's structure comes from **Mental Models** -- installable packages that define what types of objects exist, what properties they have, how they relate, and how they should be displayed. The built-in "Basic PKM" Mental Model gives you four types out of the box: **Note**, **Concept**, **Project**, and **Person**. Each type has properties (a Project has a status and priority; a Person has a name and job title) and relationships (a Project has participants; a Note is about Concepts).

You work with these types through auto-generated forms -- no schema design required. But you can install additional Mental Models later to add new types (say, "Paper", "Dataset", or "Meeting") without disrupting your existing data.

### Relationships as First-Class Citizens

In most PKM tools, relationships are an afterthought -- a wiki-link, a backlink, or a tag. In SemPKM, every relationship is a **typed edge** with a defined meaning. When you link a Person to a Project, that edge carries the type "hasParticipant" or "participatesIn". When you link a Note to a Concept, the edge type is "isAbout". These typed relationships power real queries: "Show me all people participating in active projects" or "Find notes about Event Sourcing created this month."

### Full History, No Lock-In

Every change you make in SemPKM is recorded as an immutable **event** -- a timestamped, attributed snapshot of exactly what changed. This gives you a complete audit trail, the ability to see how any object evolved over time, and the foundation for undo. Your data is stored as standard RDF in an open-source triplestore (Eclipse RDF4J), not in a proprietary format.

### Validation That Helps, Not Blocks

SemPKM uses SHACL (Shapes Constraint Language) to validate your data against the rules defined in your Mental Models. If a Project is missing a required title, or a status field contains an invalid value, you will see a warning in the **Lint Panel**. But validation is assistive, not blocking -- you can always save your work and fix issues later. Think of it as a spell-checker for your knowledge structure.

### Multiple Ways to Browse

The same data can be viewed in different ways depending on what you need. SemPKM ships with three renderer types per type:

- **Table view** -- sortable, filterable rows for scanning and comparison.
- **Card view** -- visual cards showing title, subtitle, and key properties at a glance.
- **Graph view** -- an interactive node-and-edge visualization showing how objects connect.

Views are defined as SPARQL queries bundled with Mental Models, so new models can ship their own custom views.

## Feature Highlights

- **IDE-style workspace** with a navigation tree, tabbed object editor, and properties panel
- **Auto-generated forms** from SHACL shapes -- no form-building required
- **Markdown body** for rich-text content alongside structured properties
- **Command palette** for quick keyboard-driven navigation and actions
- **Passwordless authentication** via magic links (email or token-based)
- **Multi-user support** with owner and member roles
- **Webhook integrations** for outbound event notifications
- **SPARQL endpoint** for advanced queries and integrations
- **Docker-based deployment** -- a single `docker compose up` to run the full stack

## What is Next

Now that you understand what SemPKM is and why it exists, the next chapter introduces the core concepts you will encounter as you use it: Objects, Types, Properties, Edges, Mental Models, Views, Events, and Validation.

[Core Concepts](02-core-concepts.md)
