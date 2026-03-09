# SemPKM User Guide — Documentation Outline

> **Status:** IMPLEMENTED — all chapters written and up-to-date as of v2.5.
>
> This document describes the structure of the SemPKM user guide.
> Each section includes a brief description of what is covered.

---

## Part I: Introduction and Getting Started

### 1. What is SemPKM?
- **The elevator pitch:** A semantics-native personal knowledge management platform that uses RDF, SHACL, and installable "Mental Models" to give you structured, typed knowledge management without requiring you to understand any of those technologies.
- **The problem it solves:** Most PKM tools are either free-form (Obsidian, Notion) where structure is an afterthought, or rigidly academic (Protege, TopBraid) where usability is an afterthought. SemPKM bridges these worlds — install a Mental Model and you immediately get auto-generated forms, typed relationships, semantic views, and validation guidance.
- **Who it's for:** Researchers, knowledge workers, teams, and anyone who wants structured knowledge management without building schemas from scratch.
- **Key differentiators vs. other PKM tools** (brief comparison with Obsidian, Notion, Logseq — positioning, not bashing).

### 2. Core Concepts
A glossary-style section that introduces the mental model (no pun intended) users need before using the app. Each concept gets 2-3 paragraphs and a concrete example.

- **Objects** — The fundamental unit of knowledge. Everything you create (a Note, a Person, a Project, a Concept) is an object with a unique identity, typed properties, and an optional Markdown body.
- **Types** — Objects have types that determine what properties they have and how they're displayed. Types come from installed Mental Models (e.g., `Note`, `Person`, `Project`, `Concept` from Basic PKM).
- **Properties** — Typed fields on an object (title, status, description, etc.). Properties are defined by SHACL shapes and rendered automatically as form fields.
- **Edges (Relationships)** — First-class typed connections between objects. Unlike simple links in other PKM tools, edges in SemPKM have a type (e.g., "authored by," "related to," "part of") and can carry their own annotations.
- **Mental Models** — Installable packages that bundle an ontology (what types exist), shapes (what properties each type has), views (how to browse data), and seed data. Install one and you get an instant, fully-functional knowledge domain.
- **Views** — Saved ways to browse your data: tables, card grids, and graph visualizations. Views are defined by SPARQL queries (you don't need to write them — they come with Mental Models).
- **Events** — Every change you make is recorded as an immutable event. This gives you a full audit trail, the ability to see diffs of changes, and the ability to undo operations.
- **Validation (Linting)** — SemPKM validates your data against the shapes defined by your Mental Models and shows guidance (like a code linter). Validation is assistive — it helps you fill in missing fields — but never blocks you from saving.

### 3. Installation and Setup
Step-by-step instructions for getting SemPKM running.

- **Prerequisites**
  - Docker and Docker Compose
  - System requirements (RAM, disk)
  - Supported platforms (Linux, macOS, Windows via WSL)
- **Quick Start (5-minute path)**
  - Clone the repository
  - Run `docker compose up`
  - Access the application at `http://localhost:3000`
- **First-Run Setup Wizard**
  - The setup token (displayed in API logs on first run)
  - Claiming the instance as the owner
  - How the owner account is created (passwordless auth)
- **Configuration**
  - Environment variables (`.env` file)
  - `TRIPLESTORE_URL`, `REPOSITORY_ID`, `BASE_NAMESPACE`
  - `DATABASE_URL` (SQLite local vs. PostgreSQL cloud)
  - `SECRET_KEY` (auto-generated if blank)
  - SMTP settings (optional — for magic link emails and team invitations)
  - `SESSION_DURATION_DAYS`
- **Architecture Overview for Self-Hosters**
  - The three Docker services: `api` (FastAPI), `triplestore` (RDF4J), `frontend` (nginx)
  - How they connect (internal `sempkm` network)
  - Volume mounts: `rdf4j_data` (triplestore), `sempkm_data` (SQLite + secrets)
  - Which ports are exposed (3000 for frontend, 8001 for direct API access)

---

## Part II: Using the Workspace

### 4. The Workspace Interface
A visual tour of the main application.

- **Overall layout** — Sidebar, explorer panel, editor area, bottom panel
- **The Sidebar**
  - Navigation sections: Home, Admin, Meta, Apps, Debug
  - Collapsing to icon rail (Ctrl+B)
  - The user menu (bottom of sidebar): settings, theme toggle, logout
- **The Object Explorer**
  - Tree view of all objects organized by type
  - Type-specific icons and colors
  - Expanding/collapsing type groups
  - Creating new objects from the explorer
- **The Views Explorer**
  - Browsing available views (tables, cards, graphs)
  - Views organized by Mental Model
- **The Editor Area**
  - Tabs for open objects, views, and settings
  - Multiple editor groups (split panes) — Ctrl+\ to split, up to 4 groups
  - Dragging tabs between editor groups
  - Closing groups (close last tab to remove the group)
- **The Bottom Panel**
  - Toggle with Ctrl+J
  - Tabs: Event Log, SPARQL Console, AI Copilot (placeholder)
  - Collapse and maximize controls
- **The Command Palette**
  - Open with Ctrl+K
  - Quick actions: open objects, switch theme, open settings, toggle sidebar, etc.

### 5. Working with Objects
The core create-edit-browse workflow.

- **Creating an Object**
  - Selecting a type from the type picker
  - Understanding auto-generated forms (fields come from SHACL shapes)
  - Required vs. optional fields
  - Saving (Ctrl+S)
- **Reading an Object (Read-Only Mode)**
  - How objects open in read-only mode by default
  - Styled property display (key-value pairs, formatted values)
  - Rendered Markdown body
  - Clickable reference links that open related objects
- **Editing an Object (Edit Mode)**
  - Switching to edit mode (Edit button or Ctrl+E)
  - The SHACL-driven form: text fields, dropdowns, reference pickers
  - The Markdown body editor (CodeMirror)
  - Autocomplete for reference properties
  - Saving changes and returning to read-only mode
- **Understanding Validation**
  - How validation works (asynchronous — runs after you save)
  - The lint panel: violations, warnings, and info messages
  - What violations mean (e.g., "Title is required")
  - Validation is guidance, not enforcement — you can always save partial work

### 6. Edges and Relationships
How to connect knowledge.

- **What edges are and why they matter**
  - Typed vs. untyped links (SemPKM vs. wiki-links in other tools)
  - Examples: "authored by," "related to," "part of," "depends on"
- **Creating edges**
  - Using reference properties in object forms
  - How edges appear in the object view
- **Browsing relationships**
  - Viewing an object's outgoing and incoming edges
  - Following reference links to navigate between objects
  - Seeing relationships in the graph view

### 7. Browsing and Visualizing Data
How to explore your knowledge base.

- **Table View**
  - Sorting and filtering columns
  - Pagination
  - Column preferences
- **Card View**
  - Visual card layout for browsing objects
  - When cards work better than tables
- **Graph View**
  - Interactive 2D graph visualization (Cytoscape.js)
  - Node colors by type, edge styles by predicate
  - Expanding nodes to reveal connections
  - Navigating from graph nodes to object pages
- **Opening Views**
  - From the Views Explorer in the sidebar
  - Views provided by Mental Models
  - The view toolbar and view menu

### 8. Keyboard Shortcuts and Command Palette
Reference for power users.

- **Global shortcuts**
  - Ctrl+K — Command palette
  - Ctrl+S — Save current object
  - Ctrl+B — Toggle sidebar
  - Ctrl+J — Toggle bottom panel
  - Ctrl+E — Toggle read/edit mode
  - Ctrl+\ — Split editor
  - Ctrl+, — Open settings
- **Command palette actions**
  - Full list of available commands

---

## Part III: Mental Models

### 9. Understanding Mental Models
The core extension mechanism.

- **What a Mental Model contains**
  - Ontology — the types and vocabulary (what kinds of objects exist)
  - Shapes — the structure of each type (what properties each object has, validation rules)
  - Views — predefined ways to browse the data (tables, cards, graphs)
  - Seed data — starter objects that come pre-loaded
  - Icons — type-specific icons and colors for the explorer, tabs, and graph
  - Settings — model-contributed configuration options
- **The Basic PKM Mental Model**
  - What's included: Projects, People, Notes, Concepts
  - The types and their properties (walkthrough of each)
  - The views included (tables, cards, graph views per type)
  - How the starter seed data helps you get going
- **How Mental Models shape your experience**
  - Install a model and forms appear automatically
  - Views are pre-configured — no query writing needed
  - Validation rules guide you toward completeness
  - Type icons give visual identity to your objects

### 10. Managing Mental Models
Installing and removing models.

- **The Admin Portal**
  - Accessing Admin from the sidebar
  - The Models management page
- **Installing a Mental Model**
  - Uploading a `.sempkm-model` archive (or directory-based install)
  - What happens during installation (ontology loaded, shapes loaded, views registered, seed data imported)
  - The auto-install behavior: Basic PKM installs automatically on a fresh instance
- **Removing a Mental Model**
  - What removal does (unloads ontology, shapes, and views)
  - What it does NOT do (existing objects are not deleted)
- **Multiple Mental Models**
  - Installing additional models alongside Basic PKM
  - How models coexist: separate namespaces, private-by-default
  - Cross-model references and export policies (advanced)

---

## Part IV: Administration

### 11. User Management
Multi-user setup and role-based access.

- **Authentication Model**
  - Passwordless authentication (no passwords to manage)
  - Session-based cookies
  - How the setup wizard creates the owner account
- **Roles**
  - Owner — full control (manage models, webhooks, users)
  - Member — create and edit objects
  - Guest — read-only access
  - How role enforcement works (server-side on every request)
- **Inviting Users**
  - Generating invitation links
  - Magic links for login (when SMTP is configured)
  - Manual token-based login (when SMTP is not configured)
- **Managing Users**
  - Viewing current users and their roles
  - Changing roles
  - Revoking access

### 12. Webhooks
Event-driven integrations.

- **What webhooks do**
  - SemPKM sends HTTP POST notifications when things change
  - Event types: `object.changed`, `edge.changed`, `validation.completed`
- **Configuring webhooks**
  - The webhook management page in Admin
  - Setting a target URL, selecting event types
  - Testing webhook delivery
- **Integration ideas**
  - Connecting to n8n or Zapier for automation
  - Triggering external workflows on knowledge changes
  - Notification-only payloads (webhooks send event metadata, not full data dumps)

### 13. Settings
Configuration and personalization.

- **Accessing Settings** — Ctrl+, or user menu
- **How settings work**
  - Three layers: system defaults < mental model defaults < user overrides
  - "Modified" indicators show when you've overridden a default
  - Search/filter to find settings
- **Theme settings**
  - System, Light, and Dark modes
  - The anti-FOUC behavior (no flash of wrong theme on reload)
  - How dark mode applies across all components
- **Mental Model-contributed settings**
  - Models can add their own settings categories
  - These appear in the Settings page under the model's section

### 14. System Health and Debugging
Tools for understanding what's happening under the hood.

- **Health Check**
  - Triplestore connectivity status
  - API health endpoint
- **Debug Tools**
  - Commands page — raw command API interface
  - SPARQL Console — execute SPARQL queries directly (power users)
  - API Docs — auto-generated OpenAPI documentation
  - Event Log — browsable event history

---

## Part V: The Event Log

### 15. Understanding the Event Log
Your knowledge base's audit trail.

- **What gets logged**
  - Every create, edit, and relationship change
  - Each event records: operation type, affected object, user, timestamp, and the actual data changes
- **Browsing the event timeline**
  - Reverse chronological display
  - Pagination (cursor-based for consistent performance)
  - Operation type badges (object.create, object.patch, body.set, edge.create, edge.patch)
- **Filtering events**
  - By operation type
  - By user
  - By affected object
  - By date range
  - Combinable filters with removable chips
- **Viewing diffs**
  - Inline diffs for property changes (before/after)
  - Line-by-line diffs for body content changes
- **Undoing changes**
  - Which operations are reversible (object.patch, body.set, edge.create, edge.patch)
  - The Undo button and confirmation flow
  - How undo creates a compensating event (not a deletion — history is preserved)
- **Provenance**
  - Every event records who performed it and their role
  - Using the event log for accountability and understanding

---

## Part VI: Advanced Topics

### 16. The Data Model
For users who want to understand what's under the hood.

- **RDF fundamentals (brief, practical)**
  - Triples: subject-predicate-object
  - IRIs as identifiers
  - How SemPKM hides RDF complexity behind labels and forms
- **Named graphs in SemPKM**
  - `sempkm:current` — the live state of all your objects
  - `sempkm:events/<id>` — immutable event records
  - `sempkm:shapes/<modelId>` — SHACL shapes from installed models
  - `sempkm:ontology/<modelId>` — ontology definitions from installed models
  - `sempkm:validation/<id>` — validation reports
- **The event-sourced architecture**
  - Why writes go through a command API (not direct database edits)
  - How events are materialized into current state
  - Why this gives you undo, audit trails, and future sync capabilities
- **SHACL and validation**
  - How shapes define form fields and validation rules
  - The SHACL-UI profile (sh:name, sh:order, sh:group, sh:datatype, etc.)
  - How validation is assistive, not punitive

### 17. The Command API
For developers and power users who want to interact programmatically.

- **Overview**
  - All writes go through `POST /api/commands`
  - Commands are JSON with a `command` discriminator and `params` object
  - Batch support: send an array of commands in one request
- **Command reference**
  - `object.create` — create a new typed object
  - `object.patch` — update properties on an existing object
  - `body.set` — set or replace an object's Markdown body
  - `edge.create` — create a typed relationship between objects
  - `edge.patch` — update annotations on an existing edge
- **Response format**
  - `results` array with IRI, event IRI, and command type per result
  - Shared `event_iri` and `timestamp`
- **Authentication**
  - Session cookies (from the web UI)
  - How to obtain a session for API scripting
- **Example workflows**
  - Creating an object with properties
  - Creating two objects and linking them with an edge
  - Updating an object's body content

### 18. The SPARQL Endpoint
For power users who want to query their knowledge graph directly.

- **Accessing SPARQL**
  - The SPARQL Console in the Debug section
  - The API endpoint: `POST /api/sparql`
- **Query basics for SemPKM**
  - Queries run against the `sempkm:current` graph
  - Prefix injection — common prefixes are auto-available
  - Result formats (JSON, XML)
- **Example queries**
  - List all objects of a given type
  - Find objects with a specific property value
  - Traverse relationships between objects
  - Aggregate queries (counts, grouping)
- **Limitations**
  - Read-only — SPARQL UPDATE is not exposed (writes go through the Command API)
  - Why this is by design (event sourcing integrity)

### 19. Creating Mental Models (Model Author Guide)
For developers who want to create their own Mental Models.

- **The Mental Model bundle format**
  - Directory structure: `manifest.yaml`, `ontology/`, `shapes/`, `views/`, `seed/`
  - JSON-LD format for ontologies, shapes, views, and seed data
- **The manifest**
  - Required fields: `modelId`, `version`, `name`, `description`, `namespace`
  - `prefixes` — namespace prefix declarations
  - `entrypoints` — paths to ontology, shapes, views, seed files
  - `icons` — type-to-icon mappings for tree, tabs, and graph
  - `settings` — model-contributed settings (optional)
- **Defining an ontology**
  - Declaring types (classes)
  - Declaring properties with domains and ranges
  - Using standard vocabularies (dcterms, rdfs, skos, schema.org)
- **Writing SHACL shapes**
  - Targeting types with `sh:targetClass`
  - Defining properties with `sh:property`
  - Field labels (`sh:name`), ordering (`sh:order`), grouping (`sh:group`)
  - Data types (`sh:datatype`), cardinality (`sh:minCount`, `sh:maxCount`)
  - Dropdowns (`sh:in`), references (`sh:class` or `sh:nodeKind sh:IRI`)
  - Validation severity (`sh:severity` — Violation, Warning, Info)
  - Human-readable messages (`sh:message`)
- **Defining views**
  - View spec structure: SPARQL query + renderer + layout config
  - Table views, card views, graph views
  - Template parameters (`{{contextIri}}`)
- **Seed data**
  - Providing starter objects for new installs
- **Testing your Mental Model**
  - Installing from a local directory
  - Validating the manifest
  - Checking forms, views, and validation
- **Packaging and distribution**
  - The `.sempkm-model` archive format

---

## Part VII: Deployment and Operations

### 20. Production Deployment
Taking SemPKM beyond `docker compose up`.

- **Securing the instance**
  - Setting a strong `SECRET_KEY`
  - Configuring SMTP for magic link email delivery
  - Network considerations (reverse proxy, HTTPS)
  - Note: Cookie `secure=True` for production (future)
- **PostgreSQL for multi-user / cloud**
  - Switching `DATABASE_URL` from SQLite to PostgreSQL
  - Database migrations (Alembic)
- **Resource sizing**
  - Triplestore memory (`JAVA_OPTS` for RDF4J)
  - Expected resource usage at various scales
- **Backup and restore**
  - RDF4J data volume
  - SQLite / PostgreSQL auth database
  - The relationship between events and current state (events are the source of truth)
- **Resetting an instance**
  - The `scripts/reset-instance.sh` script
  - What it deletes (auth database, setup token, secret key)
  - What it preserves (triplestore data, installed models)

---

## Part IX: Identity and Federation

### 25. WebID Profiles
Personal identity on the decentralized web.

- **What is a WebID** — a URL that serves as both a human-readable profile and a machine-readable identity document
- **Your SemPKM WebID** — automatic profile at `{APP_BASE_URL}/id/{username}`
- **Profile content** — display name, links, public information
- **Content negotiation** — HTML for browsers, JSON-LD/Turtle for Linked Data clients
- **Configuring APP_BASE_URL** — required for WebID URIs to resolve correctly
- **WebID and the Linked Data ecosystem** — how your identity connects to the broader web

### 26. IndieAuth
Using your SemPKM identity to authenticate with other services.

- **What is IndieAuth** — an OAuth 2.0-based protocol for decentralized authentication
- **SemPKM as an IndieAuth provider** — sign into third-party services using your SemPKM URL
- **The authorization flow** — discovery, authorization request, consent, token exchange
- **PKCE security** — Proof Key for Code Exchange protects against code interception
- **Token lifetimes** — 60s authorization codes, 1h access tokens, 30d refresh tokens
- **Supported grant types** — authorization_code with PKCE
- **Client discovery** — how third-party services discover your IndieAuth endpoints
- **Troubleshooting** — common issues with IndieAuth flows

---

## Appendices

### A. Environment Variable Reference
Complete table of all environment variables with descriptions, defaults, and when they're required. Includes `APP_BASE_URL`, `CORS_ORIGINS`, `COOKIE_SECURE`, and PostHog analytics settings.

### B. Keyboard Shortcut Reference
Complete table of all keyboard shortcuts organized by context (global, editor, sidebar, bottom panel).

### C. Command API Reference
Complete reference for all command types with request/response schemas and examples.

### D. Glossary
Alphabetical definitions of all domain terms: Object, Edge, Mental Model, Shape, View, Event, Ontology, IRI, SHACL, SPARQL, Named Graph, Type, Property, Validation, Lint, WebID, IndieAuth, PKCE, Carousel View, Lint Dashboard, Entailment, Inference, SHACL-AF Rule, Obsidian Import, Content Negotiation, etc.

### E. Troubleshooting
Common issues and solutions:
- "The setup token isn't showing" — check `docker compose logs api`
- "Objects aren't loading" — triplestore health check
- "Validation isn't running" — async queue status
- "Magic links aren't being sent" — SMTP configuration check
- "I can't edit objects" — role/permissions check
- Container startup ordering issues
- Triplestore memory issues
- Obsidian import issues (zip upload, frontmatter mapping, stuck imports)
- WebID / identity issues (profile 404, content negotiation, IndieAuth failures)

### F. FAQ
- Can I use SemPKM with Obsidian? (Yes — built-in Obsidian Import wizard for vault migration)
- Can I import data from other tools? (Obsidian: built-in wizard; others: via Command API scripts)
- Can multiple users work at the same time? (Yes — multi-user with roles, but no real-time collaborative editing)
- How is my data stored? (RDF in a triplestore + SQLite/PostgreSQL for auth)
- Is my data locked in? (No — RDF is a W3C standard; JSON-LD export planned)
- Can I write my own Mental Model? (Yes — see Chapter 19)
- What's the difference between an edge and a property? (Properties are literal values on an object; edges are typed relationships to other objects)
- What is WebID and do I need it? (Personal identity URL, auto-created for each user)
- Can I sign into other services with SemPKM? (Yes — via IndieAuth provider)

---

## Document Conventions (to be used throughout)

- **Keyboard shortcuts** rendered as `Ctrl+K` inline code
- **UI element names** in **bold** on first mention in each section
- **File paths and IRIs** in `inline code`
- **Concrete examples** using the Basic PKM model (Projects, People, Notes, Concepts) so the reader always has familiar context
- **Screenshots/diagrams** — placeholders noted where visual aids would help (to be created separately)
- **Admonitions** — Tip, Note, Warning boxes for important callouts
- **Cross-references** between sections where concepts build on each other

---

*Outline version: 2.0 — updated for v2.5 (Parts I-IX complete)*
