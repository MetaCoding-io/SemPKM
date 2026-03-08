# Phase 35: OWL 2 RL Inference - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Automatic inverse property materialization via OWL 2 RL inference. Users trigger inference manually from a dedicated bottom panel tab, see inferred triples with visual distinction, and can dismiss or promote them. Inference scope is configurable per Mental Model in the admin panel. SHACL-AF rules are Phase 36 (separate).

</domain>

<decisions>
## Implementation Decisions

### Inferred data visibility
- Subtle "inferred" badge on inferred triples in the relations panel — small label or icon, not overwhelming
- Dashed lines for inferred edges in graph view (solid lines remain for user-created edges)
- Object read view: inferred properties in a right-hand column, user-created properties on the left
- Inferred relation links are fully clickable/navigable — behave identically to manually-created links

### Inference lifecycle & timing
- Manual trigger only for v2.4 — user clicks a "Refresh" button in the Inference bottom panel tab
- No automatic inference on every write (auto option deferred to future configuration)
- Stale inferred triples (source deleted) get a visual indicator with pop-up explanation describing what happened
- Manual/user-created triples always take precedence over inferred triples (no duplication, no override)
- Each inference run creates an entry in the event log for auditability

### Inference bottom panel tab
- New "Inference" tab in the bottom panel (alongside SPARQL, Event Log, AI Copilot)
- Contains a "Refresh" button to trigger inference
- Shows a global list of all inferred triples (not just summary counts)
- Filterable by object type and date range
- Groupable by: time inferred (chronological), object type, or property type
- Users can dismiss/hide individual inferred triples from this panel
- Users can "pin"/promote individual inferred triples to permanent user-created triples from this panel

### Inferred data editability
- Users can dismiss/hide specific inferred triples they don't want to see (per-triple opt-out)
- Users can promote ("pin") an inferred triple to a permanent user-created triple that persists even if the source is removed
- Inferred triples are otherwise read-only — cannot be directly edited, only dismissed or promoted

### Inference scope & configuration
- Configurable per Mental Model in admin panel (model management section)
- Mental Model author provides default entailment toggles in the manifest
- User can override defaults: check/uncheck which OWL RL entailment types to enable per model
- Available entailment types: `owl:inverseOf`, `rdfs:subClassOf`, `rdfs:subPropertyOf`, `owl:TransitiveProperty`, `rdfs:domain`/`rdfs:range`
- Admin UI shows concrete examples from the model's actual ontology (e.g., "hasParticipant ↔ participatesIn" not just "owl:inverseOf")
- Mental Model uninstall cleans up inferred triples following existing uninstall pattern (same as other model data)

### Claude's Discretion
- Named graph strategy for `urn:sempkm:inferred` (full recompute vs incremental on each run)
- Exact inference panel layout and table/list design
- Toast or inline feedback during inference run progress
- How to handle conflicting inferred triples from multiple Mental Models
- Badge styling and stale-triple pop-up implementation details

</decisions>

<specifics>
## Specific Ideas

- User wants the Inference tab to feel like a control center — see everything that was inferred, filter it, and act on individual triples
- Admin panel config should make OWL axioms approachable: show real examples from the ontology, not abstract RDF terms
- Event log integration: inference runs should be logged like any other system event so users can trace what happened and when

</specifics>

<deferred>
## Deferred Ideas

- Automatic inference on every write (user-configurable auto mode) — future enhancement after users understand manual workflow
- AI explainability for inferred triples ("why was this inferred?" — trace the axiom chain) — significant capability, own phase
- SHACL-AF rules (sh:TripleRule, sh:SPARQLRule) — Phase 36

</deferred>

---

*Phase: 35-owl2-rl-inference*
*Context gathered: 2026-03-04*
