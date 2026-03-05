# Phase 36: SHACL-AF Rules Support - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Mental Models can declare SHACL-AF rules (sh:TripleRule, sh:SPARQLRule) that pyshacl executes with `advanced=True`. Rule-derived triples are stored in `urn:sempkm:inferred` alongside OWL-derived triples. basic-pkm ships example rules demonstrating the capability. Users see rule-derived data in object views without manual action.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

All decisions in this phase were delegated to Claude. The user trusts the builder to make choices consistent with Phase 35's patterns and the existing codebase conventions. Key areas where Claude has flexibility:

**Example rules for basic-pkm:**
- Claude selects which SHACL rules to ship (relationship expansion, computed properties, or both)
- Claude selects rule syntax (sh:SPARQLRule, sh:TripleRule, or both)
- Claude decides whether rules reuse existing bpkm: properties or introduce new derived-only properties
- Guidance: pick examples that demonstrate SHACL-AF value beyond what OWL 2 RL already handles

**Rule triples in the UI:**
- Claude decides whether rule-derived triples get the same "inferred" badge or a distinct "rule" badge
- Claude decides whether rule triples support dismiss/promote actions (same as OWL triples)
- Claude decides how rules appear in Inference panel entailment type filters
- Claude decides whether rule triples appear in the same inferred column on object read views or separately
- Guidance: prioritize consistency with Phase 35's established UX patterns

**Admin config granularity:**
- Claude decides toggle granularity (single per-model toggle vs per-rule toggles)
- Claude decides how manifest declares rule defaults (extend entailment_defaults vs separate section)
- Claude decides whether admin panel shows rule descriptions
- Claude decides whether to show/hide rules toggle for models without rules
- Guidance: match Phase 35's entailment config UX patterns

**Rules file format:**
- Claude decides file format (JSON-LD for consistency, Turtle for readability, or auto-detect both)
- Claude decides directory structure (dedicated rules/ dir vs inside shapes/)
- Claude decides loading strategy (merge with shapes graph vs separate graph)
- Claude decides where rule metadata lives (in the SHACL file via rdfs:label/rdfs:comment vs manifest.yaml)
- Guidance: keep model authoring simple and consistent with existing entrypoints

</decisions>

<specifics>
## Specific Ideas

No specific requirements — user fully delegated to Claude's discretion. Follow Phase 35's established patterns for inference infrastructure, admin UI, and object view integration.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/validation.py`: pyshacl.validate() call at line 95 — needs `advanced=True` parameter added
- `backend/app/models/manifest.py`: ManifestEntrypoints class (line 43) — add optional `rules` field
- `backend/app/models/loader.py`: load_archive() (line 103) — extend to load rules graph
- `backend/app/inference/service.py`: Full inference pipeline with entailment classification, inferred graph management, per-triple state tracking
- `backend/app/inference/models.py`: inference_triple_state SQLAlchemy model with status/entailment_type columns

### Established Patterns
- **Manifest entrypoints**: 4 current entrypoints (ontology, shapes, views, seed) with `{modelId}` placeholder resolution. `seed` is optional (nullable) — `rules` should follow the same optional pattern
- **Entailment config**: manifest `entailment_defaults` section with per-type booleans; user overrides via SettingsService; merged across all installed models
- **Entailment classification**: `classify_entailment()` function categorizes inferred triples by type (owl:inverseOf, rdfs:subClassOf, etc.)
- **Inferred graph lifecycle**: full recompute on each run — clear graph, insert new triples, update SQLite state
- **ModelArchive dataclass**: holds loaded rdflib.Graphs per entrypoint (ontology, shapes, views, seed)

### Integration Points
- Inference service `run_inference()` — add SHACL rule execution step (after OWL 2 RL closure or as separate pass)
- Model install/uninstall pipeline — load rules graph, clean up on uninstall
- Admin entailment config UI — add rules toggle section
- Inference panel frontend — new entailment type in filter chips

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 36-shacl-af-rules*
*Context gathered: 2026-03-04*
