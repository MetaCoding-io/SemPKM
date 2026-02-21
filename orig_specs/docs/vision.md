# Project SemPKM — Vision Document v0.3

*Semantics-native PKM: RDF + SHACL at the core, Mental Models for instant experiences, IDE-grade web UI, filesystem projections for tool interoperability, and simple automation hooks.*

---

## 1) Purpose and problem statement

PKM tools force a tradeoff:

* **Markdown-first systems** are flexible and portable, but structure is implicit and semantics are informal.
* **Object-first systems** offer structure and views, but often lock users into a platform and do not align naturally with semantic web standards, extensibility, or federated sharing.

**SemPKM** aims to unify:

* a standards-native semantic datastore (**RDF + SPARQL + SHACL**),
* an IDE-grade UX that makes semantics usable,
* and projections that let existing tools (e.g., Obsidian) work with the graph as if it were files.

---

## 2) Vision

**Project SemPKM** is a web-first, local-first knowledge platform where users store any RDF data they want and interact with it as typed objects and typed relationships through a flexible “knowledge IDE.” Users install **Mental Models** (ontology + SHACL + views + projections) to avoid blank-page syndrome and instantly get powerful workflows. The system is **event-sourced** for auditability and automation, supports **simple webhooks** for external automations (n8n, etc.), and enables selective publishing/sharing via **SOLID** and outbound **ActivityPub** (v1 outbound-only).

---

## 3) Guiding principles

1. **RDF is the system of record**
2. **Event sourcing is foundational**
3. **Constraints are assistive (linting), not punitive**
4. **IDE-grade UX and extensibility**
5. **Mental Models eliminate blank-page syndrome**
6. **Interoperability by default (SPARQL, JSON-LD, projections)**
7. **Events everywhere for automation and integration**
8. **Keep v1 simple; push complex delivery/security architecture to v3**

---

## 4) Core concepts

* **Object:** a typed RDF resource intended for direct human interaction (e.g., Project, Person, Claim, Concept, Note).
* **Body (Markdown):** one primary Markdown representation per object, versioned over time.
* **Edge (relationship):** a first-class entity in the UX (clickable, annotatable, versionable).
* **Shape (SHACL):** constraints that drive validation + form generation + linting.
* **View:** a visualization defined by a query and a layout (table/cards/graph/form/object).
* **Dashboard:** a compositional workspace of panels, parameterized by a context object.
* **Projection:** a virtual filesystem view of the graph (read-only in v1).
* **Event:** immutable fact of change; automation substrate.
* **Mental Model:** installable bundle: ontology + shapes + views + projections (+ optional workflows later).

---

## 5) Architecture overview

### 5.1 Semantic Core

* RDF dataset storage + SPARQL endpoint (read surface)
* SHACL validation engine
* Named graphs + provenance-friendly patterns
* Materialized “current state” projections derived from the event log
* Validation reports persisted as immutable artifacts tied to commits

### 5.2 Event Log (Canonical Truth)

SemPKM is **event-sourced**: the event log is the authoritative record of all changes. “Current state” is a derived projection.

### 5.3 Web UI (Object Browser)

* IDE-grade workspace (panes, tabs, command palette, keyboard-first)
* Object inspector, relationship panels, SHACL linter, query-backed views, graph views
* Dashboard support (panel composition, parameterized)

### 5.4 Mental Model Manager + Marketplace

* Install/update/remove models
* Built-in starter models + open-source marketplace for community models
* No user overrides in v1

### 5.5 Projection Service (Virtual Filesystems)

* Read-only in v1
* Deterministic IRI→path mapping
* One markdown per object + optional sidecars

### 5.6 Automation (v1-simple)

* Simple outbound webhooks for event notifications to external automation systems (n8n)
* Complex delivery guarantees and security features are deferred to v3

### 5.7 Publishing/Interop Layer

* SOLID export/publish of shape-governed subsets (not primary datastore)
* Outbound ActivityPub publishing (v1 outbound-only)
* Export formats: JSON-LD, Turtle/TriG, etc.

You’re right — it’s **not** explicitly in the consolidated v0.3 doc. We discussed it and used `sh:declare`/prefixes in the starter models, but I didn’t add a named section/decision to v0.3.

Here’s the exact **v0.3 patch** to include (two places: core services + specs).

---

## Add to v0.3 (recommended placement)

### 5) Architecture overview → add a subsection

**5.8 Prefix + QName Resolution Service**
SemPKM includes a **Prefix Registry and QName Resolver** used consistently across:

* SPARQL editor
* SHACL shape authoring/inspection
* View specs (SPARQL text and UI labels)
* UI rendering (tooltips, inspectors, debug panels)

**Prefix sources (priority order):**

1. **Mental Model declarations** (preferred): SHACL prefix declarations via `sh:declare` / `sh:prefixes`
2. **User workspace config** (local overrides)
3. **SemPKM built-ins** (rdf, rdfs, xsd, sh, skos, dcterms, prov, schema, etc.)

**Behavior:**

* Render IRIs as QNames when a prefix mapping exists
* Preserve full IRI display on hover/copy
* SPARQL editor auto-injects PREFIX blocks from the active model registry (optional toggle)

---

## 6) IDE-grade Object Browser

### 6.1 SOTA UX requirements

* Highly flexible layout, like an IDE or Obsidian
* Composable views (table, cards, form, object, graph)
* Saved searches and saved SPARQL views
* SHACL linting panel with guidance
* Fast navigation + command palette

### 6.2 Graph visualization

* Built-in graph views:

  * 2D graph (stable default)
  * 3D graph (experimental)
* Graph usefulness depends on semantic-aware customization:

  * node styling/layout rules by object type
  * edge styling by predicate / edge type
  * “lenses” for task-specific filtering and emphasis
    Graph customization is treated as a research-backed area.

---

## 7) Mental Models

### 7.1 Mental Model definition

A Mental Model is an installable “PKM experience” bundle:

* ontology (types and properties),
* SHACL shapes (constraints + UI-driving structure),
* view definitions (queries + layouts),
* projection rules (graph → filesystem),
* optional seed data,
* optional workflows folder reserved for v2+.

### 7.2 Packaging format

* Single `.sempkm-model` archive (ZIP internally)
* Required `manifest.yaml` containing:

  * `modelId` (globally unique)
  * `name`, `description`, `author`, `license`
  * `version` (SemVer) + compatibility bounds
  * entrypoints: ontology, shapes, views, projections, seed
  * dependencies (optional)
  * exports (cross-model embedding rules; see below)

### 7.3 Linked Open Data (LOD) preference for starter models

Starter Mental Models should preferentially reuse common standards where appropriate:

* SKOS (concepts/tags)
* DCTERMS (metadata)
* PROV-O (provenance)
  While keeping UX field names friendly and approachable.

### 7.4 Migration and overrides

* Model migration is a future research track (v2+).
* No user overrides in v1.

---

## 8) Views and Dashboards (C2)

### 8.1 View spec v1

A SemPKM View is a declarative spec combining:

* SPARQL query (SELECT/CONSTRUCT/ASK)
* renderer type
* renderer layout config
* optional parameters
* optional actions (invoke command API)

### 8.2 Core renderers (v1)

v1 includes these core renderers:

* **Object**: render a single object page (multi-subpanels)
* **Form**: shape-driven create/edit UI (writes via command API)
* **Table**: SPARQL SELECT → columns, sort, filter, paging
* **Cards**: SPARQL SELECT → gallery/summary cards, optional grouping
* **Graph**: SPARQL CONSTRUCT (preferred) → semantic-aware rendering rules
  Timeline/calendar are deferred (v1.1/v2).

### 8.3 Dashboard renderer (v1)

Dashboards are distinct from object rendering:

* **Object renderer** focuses on a single object.
* **Dashboard renderer** composes panels into a workspace.

Dashboards are **parameterized** by a `contextIri` (and optional additional params).

Supported dashboard panel types (v1):

* `objectSelf` — renders the context object using its object renderer
* `view` — embeds another view by id, with params
* `lintSummary` — validation summary panel
* `markdown` — static help/instructions

### 8.4 Dashboard registry (v1)

Mental Models may declare a dashboard registry mapping:

* class/type → default dashboard id
* additional dashboards available per type

Open behavior:

* if default dashboard exists for an object type, open that dashboard by default
* otherwise open object renderer
* allow “Open with…” dashboard switching

### 8) Views and Dashboards (C2) → add a subsection

**8.5 Prefix/QName integration in views**

* View execution and rendering uses the active model’s prefix registry.
* View specs may omit explicit `PREFIX` lines if SemPKM injects them automatically (implementation option). If omitted, SemPKM must still ensure queries are executed with correct prefixes.



---

## 9) Namespacing, exports, and cross-model embedding

### 9.1 Namespacing

All views/dashboards have stable IDs. SemPKM canonicalizes IDs as:

* `modelId::localId`

Local IDs are stable and file-name-independent.

### 9.2 Cross-model embedding: private-by-default

Cross-model embedding requires explicit exports:

* By default, nothing is exported.
* A model must list exported views/dashboards in `manifest.yaml`.
* Referencing non-exported views/dashboards from another model is an install-time error (v1 default).

---

## 10) Data model decisions (A)

### A1) Event sourcing is canonical (A1.3)

* All writes produce immutable events
* Current graph state is a projection
* Validation reports are derived artifacts tied to commits
* This supports automation, auditability, and future sync strategies

### A2) Edge model is hybrid

* Canonical UX identity uses edge resources (`sempkm:Edge`)
* Optional projection materializes corresponding simple triples for query ergonomics/visualization
* Triple-term/RDF-star style querying/export is treated as a projection/interchange capability, not the canonical UX identity

---

## 11) SHACL-driven UX contract (B)

### B3) SemPKM UI Profile for SHACL v1

SemPKM interprets a pragmatic subset of SHACL Core as UI-driving:

* targeting/fields: `sh:targetClass`, `sh:property`, `sh:path`
* labels/help: `sh:name`, `sh:description`, `sh:message`, `sh:severity`
* requiredness: `sh:minCount`, `sh:maxCount`
* value typing/pickers: `sh:datatype`, `sh:nodeKind`, `sh:class`, `sh:in`
* basic constraints: `sh:pattern`, min/max lengths and bounds
* defaults: `sh:defaultValue`
* layout hints: `sh:order`, `sh:group` / `sh:PropertyGroup`

### B4) Validation persistence

* Each commit produces an immutable SHACL Validation Report results graph
* SemPKM maintains a derived “current diagnostics” index for fast lint UX
* SemPKM can compute diffs between reports for “what changed” linting

### B5) Validation execution

* Validation runs **asynchronously** (non-blocking UI)
* UI shows pending validation state; completion updates lint panel

### B6) Gating policy

* **Violations block** “conformance-required operations”
* **Warnings do not block**
* No user overrides in v1; overrides are v2+

---

## 12) Projections (D)

### D0) Scope and guarantees (v1)

* Read-only v1
* Deterministic object IRI → file mapping
* One markdown per object
* Semantics exposed via sidecars and UI (no markdown syntax extensions)

### D1) IRI → path mapping

* FS root maps to user base namespace
* IRI path becomes filesystem path
* trailing slash → `index.md`
* query/fragment ignored for mapping
* non-base IRIs excluded by default (optional `_external/` stubs later)

### D2) Per-object projected files

For object file `X.md`, SemPKM may generate:

* `X.md` — markdown body
* `X.meta.json` — object metadata subset
* `X.edges.json` — edges + edge annotations for this object
* optional `X.versions.json` (likely v1.1)

### D3) Sidecar schemas

* `X.meta.json`: includes IRI, types, labels, selected properties, projection metadata
* `X.edges.json`: includes stable edge IDs, direction, predicate, target, and flattened annotations

### D6) Index strategy

* v1 uses per-object sidecars only; no global edge index (deferred to v2+).

---

## 13) Automation (v1 simple) and future workflow engine

### v1 automation

* Simple outbound webhooks to external systems (n8n)
* Best-effort delivery; minimal retry; failures visible in basic webhook log UI
* Complex delivery/security architecture deferred to v3

### Research track: embedded n8n (v2+)

An optional embedded workflow engine mode:

* SemPKM provides first-class actions (SPARQL queries, validation, create/update, publish)
* Workflows could be distributed within Mental Models (`workflows/` reserved)

---

## 14) Minimal API surface (writes) and SPARQL (reads)

### Reads

* SPARQL endpoint is the primary read/query interface.

### Writes

* A **small command API** performs object/edge creation and updates and writes to the event log.
* External SPARQL UPDATE is not a supported write surface in v1.
* Exact event ontology/log schema deferred to implementation.

---

## 15) Publishing and federation

### SOLID

* SOLID is not the primary datastore.
* SemPKM exports/publishes shape-governed subsets to participate in the SOLID ecosystem.

### ActivityPub

* v1 supports outbound publishing of selected objects/collections (UI-driven selection).
* Bidirectional sync is v2+.

---

## 16) MVP scope (v1)

### Must-have v1 deliverables

* Event-sourced write path + durable event log
* Materialized current graph projection
* RDF store + SPARQL endpoint
* SHACL async validation + lint UI (violations gate conformance operations)
* IDE-grade UI shell
* Core renderers: object, form, table, cards, graph
* Dashboards: parameterized + registry
* Mental Model manager + starter models + external installs
* Read-only virtual filesystem projection + sidecars
* Simple webhook notifications to external automation systems
* Basic publishing/export: JSON-LD + minimal ActivityPub outbound + SOLID export subsets

### Non-goals v1

* Read/write filesystem round-trip (v2)
* Model migrations + user overrides (v2+)
* Offline multi-device sync (v2+)
* Embedded n8n (v2+)
* Advanced webhook delivery/security architecture (v3)

---

## 17) Roadmap (v2+ / v3)

### v2 targets

* Read/write projections with round-trip semantics
* Mental Model migration tooling + preview/rollback
* Offline/multi-device sync strategy built atop event log (research → implementation)
* Bidirectional ActivityPub syncing
* Optional user overrides (requires migration story)
* Embedded n8n option (if research proves viable)

### v3 targets (explicit)

* More complex webhook/event delivery architecture (DLQ, signing, scoped permissions, strict ordering, payload pointers)
* More advanced policy and sharing controls

---

## 18) Future research tracks

1. Mental Model migrations and evolution
2. Typed relations in Markdown that round-trip safely
3. 3D graph usefulness (semantic layout rules, lenses, UX studies)
4. Offline + multi-device sync strategies for event-sourced RDF
5. Statement-level metadata strategy and interoperability
6. Embedded n8n with first-class SemPKM actions and workflow distribution
7. Rich UI/action vocabularies for guidance and “quick fixes” (future)

---

## 19) Success criteria

### Wow-in-10-minutes

Install SemPKM → install a Mental Model → create objects via forms → see tables/cards/graph views immediately → linting guides structure → project filesystem in Obsidian for body editing.

### Metrics

* time-to-first-structured-object
* Mental Models installed/used
* violation resolution rate
* webhook automations configured/triggered
* export/publish adoption (JSON-LD / SOLID / ActivityPub)

---

## 20) Open v0.3 questions (non-blocking)

These are important next-tier decisions but do not block v1 vision:

1. **RDF store choice and portability promises**
2. **Auth / multi-user boundary** (single-user local-first v1 is assumed)
3. **Projection refresh strategy** (push vs pull; update frequency; minimizing churn)
4. **Import UX** (CSV/JSON-LD/manual; mapping from data to Mental Models)

---

# Appendix A — Decision Discussions (selected)

### Why event sourcing is canonical

Event sourcing aligns with automation, auditability, and future sync. It imposes discipline but provides long-term leverage.

### Why edges are first-class resources (hybrid model)

UX needs stable edge identity for inspection, annotation, provenance, and automation. Triple-term/RDF-star style is valuable as projection/export, but not enough alone for UX identity.

### Why SHACL drives UI and linting

SHACL already encodes field structure, constraints, severity, and layout hints. Using a subset as UI-driving gives structure without making the system punitive.

### Why projections use boring Markdown + sidecars

Markdown extensions break tooling. Sidecars preserve portability while exposing full semantic structure to tools and future write-back.

### Why webhooks stay simple in v1

External automations are valuable, but building a full event platform is complex. v1 focuses on “simple hooks”; v3 tackles robust delivery/security.

### Why dashboards are distinct and parameterized

Dashboards represent task workspaces; object pages represent object rendering. Parameterized dashboards enable reusable IDE-like workspaces across objects of the same type.