---
plan: 19-01
objective: Research SHACL and OWL logical inference capabilities for SemPKM mental models
tasks: 2
wave: 1
---

# Plan 19-01: Research SHACL and OWL Logical Inference for Mental Models

## Objective

Investigate how SHACL can be used beyond validation (inference rules, constraint-driven UI, mental model definitions) and how OWL reasoning could complement SHACL in SemPKM's architecture. Produce a comprehensive research document that maps theoretical capabilities to practical implementation paths given the current stack: RDF4J NativeStore (no reasoner configured), pyshacl for validation, rdflib for graph traversal, Python backend.

**Purpose:** SemPKM currently uses SHACL purely for form generation (shapes.py extracts sh:PropertyShape metadata for Jinja2 templates) and data validation (validation.py runs pyshacl.validate). OWL is used only for class/property declarations in ontology files. This research explores the much richer capabilities of both standards -- SHACL rules for materialization, OWL inference for implicit knowledge discovery, SHACL-AF for advanced constraints -- and identifies which are practical for a single-user PKM system vs. which are theoretical overkill.

**Output:** Research document at `.planning/research/shacl-owl-inference.md`

## Context

@.planning/PROJECT.md
@.planning/STATE.md
@backend/app/services/shapes.py (current SHACL shape extraction for forms)
@backend/app/services/validation.py (current pyshacl validation service)
@models/basic-pkm/ontology/basic-pkm.jsonld (current OWL ontology)
@models/basic-pkm/shapes/basic-pkm.jsonld (current SHACL shapes)
@config/rdf4j/sempkm-repo.ttl (RDF4J repo config -- NativeStore, no reasoner)

### Current Architecture Facts

- **Triplestore:** RDF4J with NativeStore + LuceneSail (no RDFS/OWL inference configured)
- **SHACL usage:** pyshacl validates data; ShapesService extracts sh:NodeShape/sh:PropertyShape for form generation
- **OWL usage:** ontology files declare owl:Class, owl:ObjectProperty, owl:DatatypeProperty, owl:inverseOf -- but no reasoner materializes inferences
- **Python libraries:** rdflib, pyshacl already in dependencies
- **Mental Model bundle:** manifest.yaml -> ontology/ + shapes/ + views/ + seed/

## Task 1: Deep web research on SHACL inference, OWL reasoning, and their interaction

**Files:** (research notes, no files created yet)

**Action:** Research the following areas using web sources. For each area, capture specific findings with source URLs:

1. **SHACL Rules (SHACL-AF / SHACL Advanced Features)**
   - sh:rule, sh:TripleRule, sh:SPARQLRule -- how SHACL shapes can generate new triples (not just validate)
   - pyshacl's support for SHACL rules (the `advanced=True` flag in pyshacl.validate)
   - Practical examples: inverse property materialization, transitive closure, derived properties
   - How SHACL rules differ from OWL inference (forward-chaining rules vs. open-world reasoning)

2. **OWL Reasoning in RDF4J**
   - RDF4J SchemaCachingRDFSInferencer and ForwardChainingRDFSInferencer
   - RDF4J's SPIN/SHACL support for custom rules
   - What OWL profiles exist (OWL 2 RL, EL, QL) and which are practical for a PKM
   - Cost of enabling inference in RDF4J: memory, query performance, data volume implications
   - Alternative: owlrl Python library for OWL 2 RL reasoning on rdflib graphs

3. **SHACL Beyond Validation**
   - SHACL as a schema language for UI generation (what SemPKM already does)
   - SHACL for query generation (deriving SPARQL from shapes)
   - SHACL for access control (data shapes as permission boundaries)
   - DASH extensions (DASH Data Shapes vocabulary) -- sh:viewer, sh:editor, dash:DatePickerEditor, etc.
   - TopBraid's SHACL extensions for form generation (relevant patterns even if proprietary)

4. **Mental Model Definitions via SHACL + OWL**
   - How a "mental model" could be formally defined as a combination of: OWL ontology (classes, properties, axioms) + SHACL shapes (constraints, UI hints, rules) + SPARQL views (queries)
   - What intelligence could a mental model carry? E.g., "if a Project has status=completed and all Notes are tagged 'archived', infer project is fully archived"
   - SHACL rules vs. SPARQL CONSTRUCT for derived properties
   - How inference enriches the graph view (showing implicit relationships)

5. **Practical Inference Patterns for PKM**
   - Inverse property materialization (owl:inverseOf -- hasParticipant/participatesIn already declared but not materialized)
   - Transitive closure (skos:broader/narrower chains for concept hierarchies)
   - Property inheritance (rdfs:subPropertyOf, rdfs:subClassOf)
   - "Smart" suggestions: if Note isAbout Concept and Concept is broader than X, suggest X as related
   - Consistency checking beyond SHACL validation (OWL disjointness, cardinality)

6. **Performance and Architecture Considerations**
   - On-demand inference (query-time) vs. materialization (write-time) vs. hybrid
   - pyshacl + owlrl combined pipeline: validate + infer in one pass
   - RDF4J config changes needed for RDFS inference (SchemaCachingRDFSInferencer as delegate layer)
   - Scale considerations for single-user PKM (thousands of triples, not millions)

**Verify:** Research notes captured with findings from all 6 areas, each with at least 2-3 source URLs

**Done:** Research complete with enough information to draft the architecture document

## Task 2: Write research document with architecture analysis and SemPKM-specific recommendations

**Files:** `.planning/research/shacl-owl-inference.md`

**Action:** Write a comprehensive research document structured as follows:

### Document structure:

**1. Executive Summary** (2-3 paragraphs)
- The opportunity: SHACL and OWL already in the codebase but underutilized
- Primary recommendation and confidence level
- What would change for users (richer graph views, smarter suggestions, derived properties)

**2. Current State Audit** (brief)
- How SHACL is used today: shapes.py (form metadata) + validation.py (pyshacl validation)
- How OWL is used today: ontology class/property declarations only
- What is NOT happening: no inference, no rule execution, owl:inverseOf declared but not materialized
- The gap: users manually maintain bidirectional relationships that the ontology already describes

**3. SHACL Advanced Features Analysis**
- SHACL Rules (sh:rule) -- triple generation from shapes
- SHACL-SPARQL constraints -- custom SPARQL-based validation
- DASH vocabulary extensions -- UI-aware shape metadata
- pyshacl's support matrix: what works, what does not, version requirements
- Code example: a SHACL rule that materializes bpkm:participatesIn from bpkm:hasParticipant using sh:TripleRule

**4. OWL Inference Analysis**
- OWL 2 profiles and which fits SemPKM (likely OWL 2 RL)
- RDF4J inference configuration options (RDFS vs. custom rules)
- Python-side inference with owlrl library
- What OWL axioms already in basic-pkm ontology could produce inferences (owl:inverseOf)
- What additional axioms would be valuable (transitivity, disjointness, domain/range inference)

**5. Combined Architecture: SHACL Rules + OWL Inference**
- Proposed pipeline: write -> OWL inference (materialize) -> SHACL validate -> SHACL rules (derive) -> store
- Where to run inference: Python-side (rdflib + owlrl + pyshacl) vs. triplestore-side (RDF4J config)
- Recommendation: Python-side for PKM scale, with option to move to triplestore for performance later
- How this integrates with the existing ValidationService

**6. Practical Applications in SemPKM**
For each, include: what it does, example in basic-pkm model, implementation sketch

a. **Inverse property materialization** -- automatic bidirectional links
b. **Transitive concept hierarchies** -- "show all ancestors of this concept"
c. **Derived property computation** -- "project completion %" from related notes
d. **Smart relationship suggestions** -- inference-powered link recommendations
e. **Consistency checking** -- OWL-level disjointness and cardinality beyond SHACL
f. **Shape-driven query generation** -- auto-generate SPARQL from SHACL shapes instead of manual ViewSpec queries

**7. Mental Model Intelligence**
- How models could declare inference rules alongside shapes
- Manifest extension: `entrypoints.rules` pointing to a rules file
- Example: a "GTD" mental model that infers task contexts from project associations
- Example: a "Zettelkasten" mental model with transitive linking rules
- Trust boundary: model-contributed rules execute in sandboxed pyshacl, not arbitrary Python

**8. Implementation Roadmap**
- **Phase A (low risk, high value):** Enable owlrl OWL 2 RL reasoning in ValidationService pipeline; materialize owl:inverseOf triples on write
- **Phase B (medium):** Add SHACL rule support to pyshacl calls (advanced=True); allow models to contribute rules files
- **Phase C (medium):** DASH vocabulary adoption for richer form generation; shape-driven SPARQL generation
- **Phase D (future):** RDF4J inference layer for query-time reasoning; federated inference across models

**9. Risks and Tradeoffs**
- Materialization bloat (more triples = more storage, slower FTS indexing)
- Rule debugging (why does this triple exist? provenance tracking)
- Model author complexity (writing OWL axioms and SHACL rules is harder than writing shapes)
- Backward compatibility (existing data needs re-inference on rule changes)

**10. Source Links**
- All URLs referenced in the research, organized by topic

Throughout the document, include source links inline (not just at the end) so every claim is traceable. Reference SemPKM-specific files and code patterns to ground the analysis in the actual system.

**Verify:** `wc -l .planning/research/shacl-owl-inference.md` shows 300+ lines; document contains all 10 sections; grep confirms source URLs present throughout; document references actual SemPKM files (shapes.py, validation.py, basic-pkm ontology)

**Done:** Research document committed with SHACL inference analysis, OWL reasoning options, combined architecture proposal, practical PKM applications, mental model intelligence design, implementation roadmap, and source links throughout
