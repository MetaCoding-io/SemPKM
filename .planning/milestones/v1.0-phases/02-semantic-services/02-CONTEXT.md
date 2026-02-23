# Phase 2: Semantic Services - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Backend services that resolve IRIs to human-readable labels, manage prefix mappings for QName rendering, and validate data against SHACL shapes asynchronously after every commit. These services are consumed by all downstream UI phases (4, 5) but are not directly user-facing in this phase. The label service, prefix registry, and SHACL validation engine must be complete and testable via API before Phase 3 begins.

</domain>

<decisions>
## Implementation Decisions

### IRI display fallback
- Primary fallback when no label found: **QName format** (prefix:localName)
- When prefix is unknown (no registry entry): **truncated IRI** (.../localName) with full IRI in tooltip
- Label service must support **configurable language preference** — user sets a preferred language list (e.g., en, fr) and system picks best match from language-tagged literals
- Display pattern: **label only** in UI surfaces, with QName shown on hover/tooltip for power users
- Label precedence chain: dcterms:title > rdfs:label > skos:prefLabel > schema:name > QName fallback > truncated IRI fallback

### Prefix registry defaults
- Built-in prefix set: **core + common vocabs** (~10-12 prefixes: rdf, rdfs, owl, xsd, sh, skos, dcterms, schema, foaf, prov, etc.)
- **LOV (Linked Open Vocabularies) integration**: one-time import from LOV REST API to add vocabulary prefixes to the registry, plus a CLI command for re-syncing
- Layer precedence: **User overrides > Model-provided > Built-in** — user has ultimate control
- Registry supports **both directions**: forward lookup (prefix -> namespace) for expanding QNames, and reverse lookup (namespace -> prefix) for compacting IRIs

### Validation report detail
- Three severity tiers: **Violation, Warning, Info** — shape authors control severity per constraint
- **Per-property detail**: each result includes object IRI + property path + constraint + failing value + human message
- Human messages: use **sh:message from the shape** when provided, otherwise **auto-generate a fallback message** from the constraint metadata (e.g., "Minimum 1 value required for dcterms:title")
- Storage: **summary + full report** — lightweight summary for quick status checks (commit badge, list views) plus detailed report for drill-down

### Validation trigger & feel
- Trigger: **every command** — each object.create, object.patch, edge.create, etc. triggers validation immediately after commit
- Scope: **full re-validation** — re-validate all objects against all shapes after each commit (catches cross-object constraint violations)
- UI notification: **polling endpoint** (GET /api/validation/latest or similar) — simple, works with htmx stack
- Concurrency: **queue and run sequentially** — if validation is running when the next commit arrives, new validation queues behind it. Every commit gets its own immutable report.

### Claude's Discretion
- Exact caching strategy for label resolution (TTL, invalidation approach)
- Internal batch resolution API design
- SHACL validation engine implementation (in-process vs subprocess, library choice)
- Auto-generated message templates and formatting
- LOV API integration details (endpoints, caching of LOV responses)
- Polling endpoint response format and timing

</decisions>

<specifics>
## Specific Ideas

- LOV integration: user wants to be able to discover and import prefix mappings from the Linked Open Vocabularies registry (lov.linkeddata.es) — one-time import via API, with a CLI command for re-syncing later
- Truncated IRI fallback with tooltip mirrors how tools like Protege handle unknown namespaces — familiar to semantic web users
- Configurable language preference acknowledges RDF's multi-language reality — the system shouldn't be English-only even in v1

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-semantic-services*
*Context gathered: 2026-02-21*
