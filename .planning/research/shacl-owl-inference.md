# SHACL and OWL Logical Inference for SemPKM Mental Models

**Research Date:** 2026-03-03
**Author:** Claude (research task quick-19)
**Status:** Research complete -- architecture proposal with source links

---

## 1. Executive Summary

SemPKM already ships two of the semantic web's most powerful standards -- SHACL and OWL -- but uses only a fraction of their capabilities. SHACL is limited to form generation (`backend/app/services/shapes.py` extracts `sh:PropertyShape` metadata for Jinja2 templates) and data validation (`backend/app/services/validation.py` calls `pyshacl.validate()`). OWL is limited to class and property declarations in the ontology files (`models/basic-pkm/ontology/basic-pkm.jsonld`). The `owl:inverseOf` axiom linking `bpkm:hasParticipant` and `bpkm:participatesIn` is declared but never materialized -- users must manually maintain both directions of every relationship. No inference engine is configured: the RDF4J repository (`config/rdf4j/sempkm-repo.ttl`) runs a bare `NativeStore` with `LuceneSail`, and pyshacl is called without the `advanced=True` flag that enables SHACL rules.

**Primary recommendation (HIGH confidence):** Add Python-side OWL 2 RL inference via the `owlrl` library to the existing `ValidationService` pipeline, materializing inverse properties and RDFS subclass/subproperty entailments on every write. This is a low-risk, high-value change: `owlrl` operates on rdflib graphs already in the pipeline, requires no triplestore reconfiguration, and immediately delivers bidirectional links, type inheritance, and richer graph visualizations. Follow with SHACL rule support (`pyshacl` `advanced=True`) to let Mental Models declare domain-specific derivation rules alongside their shapes.

**What changes for users:** (1) Automatic bidirectional links -- adding a participant to a Project automatically makes that Person's "participatesIn" list show the Project. (2) Richer graph views -- inference surfaces implicit connections (transitive concept hierarchies, inherited properties) without manual linking. (3) Smarter suggestions -- derived relationships power link recommendation ("this Note is about Concept X, which is broader than Y -- suggest Y as related"). (4) Mental Models become intelligent -- model authors can ship inference rules that derive domain-specific knowledge (a GTD model infers task contexts; a Zettelkasten model computes transitive backlinks).

---

## 2. Current State Audit

### 2.1 How SHACL is used today

**Form generation** (`backend/app/services/shapes.py`): The `ShapesService` fetches SHACL shapes via SPARQL CONSTRUCT from named graphs (`urn:sempkm:model:{id}:shapes`), parses them into an rdflib Graph, and extracts `sh:NodeShape`/`sh:PropertyShape` metadata into Python dataclasses (`NodeShapeForm`, `PropertyShape`, `PropertyGroup`). This metadata drives Jinja2 form templates -- field types, order, groups, cardinality constraints, `sh:in` enumerated values, and default values. The shapes file for basic-pkm (`models/basic-pkm/shapes/basic-pkm.jsonld`) defines four NodeShapes (ProjectShape, PersonShape, NoteShape, ConceptShape) with a total of ~40 property shapes across 12 property groups.

**Validation** (`backend/app/services/validation.py`): The `ValidationService.validate()` method fetches the current state graph via SPARQL CONSTRUCT, loads shapes via a configurable shapes loader, and runs `pyshacl.validate(data_graph, shacl_graph=shapes_graph, allow_infos=True, allow_warnings=True)` in a thread (CPU-bound). Results are parsed into a `ValidationReport` and stored as named graphs. Critically, the call does **not** pass `advanced=True`, `inference=...`, or `ont_graph=...` -- so SHACL rules and OWL inference are both disabled.

### 2.2 How OWL is used today

The ontology file (`models/basic-pkm/ontology/basic-pkm.jsonld`) declares:

| OWL Construct | Example | Count |
|---|---|---|
| `owl:Class` | `bpkm:Project`, `bpkm:Person`, `bpkm:Note`, `bpkm:Concept` | 4 |
| `owl:DatatypeProperty` | `bpkm:status`, `bpkm:priority`, `bpkm:body`, `bpkm:noteType`, `bpkm:tags` | 5 |
| `owl:ObjectProperty` | `bpkm:hasParticipant`, `bpkm:hasNote`, `bpkm:participatesIn`, `bpkm:isAbout`, `bpkm:relatedProject` | 5 |
| `owl:inverseOf` | `bpkm:participatesIn owl:inverseOf bpkm:hasParticipant` | 1 |
| `rdfs:domain`/`rdfs:range` | On all 10 properties | 10+10 |

The `owl:inverseOf` axiom between `hasParticipant` and `participatesIn` is the clearest example of declared-but-not-materialized intelligence. When a user creates `ProjectA bpkm:hasParticipant PersonB`, the inverse triple `PersonB bpkm:participatesIn ProjectA` should be automatically inferred -- but no reasoner is configured to do this.

### 2.3 What is NOT happening

1. **No OWL inference:** The RDF4J repo config uses plain `NativeStore` without `SchemaCachingRDFSInferencer` or `ForwardChainingRDFSInferencer`. No reasoner layer is configured.
2. **No SHACL rule execution:** pyshacl is called without `advanced=True`, so `sh:rule` (sh:TripleRule, sh:SPARQLRule) directives are ignored.
3. **No ontology-aware validation:** pyshacl is not given an `ont_graph`, so it cannot use OWL axioms during validation.
4. **No RDFS entailments:** `rdfs:subClassOf`, `rdfs:subPropertyOf`, `rdfs:domain`, `rdfs:range` entailments are not computed.
5. **The gap:** Users manually maintain bidirectional relationships that the ontology already describes formally.

---

## 3. SHACL Advanced Features Analysis

### 3.1 SHACL Rules (sh:rule)

SHACL Advanced Features (SHACL-AF) extends the core validation spec with triple generation capabilities. A SHACL rule, attached to a `sh:NodeShape` via `sh:rule`, produces new triples rather than validation results.

**Source:** [W3C SHACL Advanced Features](https://www.w3.org/TR/shacl-af/) (W3C Working Group Note, 8 June 2017)

Two rule types exist:

**sh:TripleRule** -- Declarative triple generation:
```turtle
ex:InverseParticipationRule a sh:TripleRule ;
    sh:subject sh:this ;
    sh:predicate bpkm:participatesIn ;
    sh:object [sh:path [sh:inversePath bpkm:hasParticipant]] ;
    sh:condition [sh:property [sh:path bpkm:hasParticipant ; sh:minCount 1]] .
```
This says: for each node matching the shape's target, generate a triple where the subject is `sh:this`, the predicate is `bpkm:participatesIn`, and the object is found by traversing `sh:inversePath bpkm:hasParticipant`.

**sh:SPARQLRule** -- SPARQL CONSTRUCT-based generation:
```turtle
ex:InverseParticipationSPARQL a sh:SPARQLRule ;
    sh:prefixes bpkm: ;
    sh:construct """
        CONSTRUCT { ?person bpkm:participatesIn $this }
        WHERE { $this bpkm:hasParticipant ?person }
    """ .
```
SPARQLRules are more flexible -- they can reference variables, use FILTER, OPTIONAL, and other SPARQL features.

**Source:** [SHACL-AF Section 4: Rules](https://www.w3.org/TR/shacl-af/#rules) (W3C)

### 3.2 pyshacl's SHACL-AF support

pyshacl (currently `>=0.31.0` in SemPKM's `pyproject.toml`) supports SHACL Advanced Features when called with `advanced=True`:

```python
conforms, results_graph, text = pyshacl.validate(
    data_graph,
    shacl_graph=shapes_graph,
    ont_graph=ontology_graph,  # optional: OWL ontology for inference
    advanced=True,              # enables SHACL-AF rules
    inplace=True,               # modify data_graph directly with inferred triples
    inference='rdfs',           # or 'owlrl' for OWL 2 RL reasoning
)
```

Key pyshacl features relevant to SemPKM:

| Feature | pyshacl Flag | Status |
|---|---|---|
| SHACL-AF Rules (sh:TripleRule, sh:SPARQLRule) | `advanced=True` | Supported since v0.14+ |
| OWL inference during validation | `inference='owlrl'` | Requires `owlrl` package |
| RDFS inference during validation | `inference='rdfs'` | Built-in |
| Ontology graph for OWL axioms | `ont_graph=Graph` | Supported |
| In-place graph modification (materialization) | `inplace=True` | Supported |
| SHACL-SPARQL Constraints | `advanced=True` | Supported |
| SHACL-SPARQL Target Types | `advanced=True` | Supported |
| sh:order on rules (execution ordering) | `advanced=True` | Supported since v0.17+ |

**Source:** [pyshacl README](https://github.com/RDFLib/pySHACL) (GitHub, RDFLib project)
**Source:** [pyshacl SHACL-AF support documentation](https://github.com/RDFLib/pySHACL#advanced-features) (GitHub)

### 3.3 SHACL-SPARQL Constraints

Beyond rules, SHACL-AF provides `sh:SPARQLConstraint` for custom validation logic that goes beyond the core constraint components. For example, validating that a Project's end date is after its start date:

```turtle
ex:DateOrderConstraint a sh:SPARQLConstraint ;
    sh:message "End date must be after start date" ;
    sh:prefixes schema: ;
    sh:select """
        SELECT $this ?start ?end
        WHERE {
            $this schema:startDate ?start ;
                 schema:endDate ?end .
            FILTER (?end < ?start)
        }
    """ .
```

This is more expressive than core SHACL constraints but stays within the SHACL validation paradigm (produces validation results, not new triples).

**Source:** [W3C SHACL-SPARQL](https://www.w3.org/TR/shacl/#sparql-constraints) (W3C Recommendation)

### 3.4 DASH Vocabulary Extensions

The Data Shapes (DASH) vocabulary, developed by TopBraid, extends SHACL with UI-aware metadata for form generation. Relevant DASH properties:

| DASH Property | Purpose | SemPKM Relevance |
|---|---|---|
| `dash:viewer` | Widget type for read-only display | Could specify `dash:MarkdownViewer` for `bpkm:body` |
| `dash:editor` | Widget type for editing | `dash:TextAreaEditor`, `dash:DatePickerEditor`, `dash:AutoCompleteEditor` |
| `dash:singleLine` | Whether text field is single-line | Form layout hints |
| `dash:readOnly` | Mark a property as non-editable | Computed/derived properties |
| `dash:hidden` | Hide a property from UI | System properties (`dcterms:created`) |
| `dash:rootClass` | Root class for class hierarchy browsing | Type picker tree |
| `dash:reifiableBy` | Annotation properties on statements | Provenance metadata |

DASH is particularly interesting for SemPKM because the existing `ShapesService` already extracts UI metadata from shapes -- DASH would formalize and extend this pattern with a community-standard vocabulary rather than custom conventions.

**Source:** [DASH Data Shapes Vocabulary](https://datashapes.org/dash.html) (TopBraid/datashapes.org)
**Source:** [DASH GitHub specification](https://github.com/TopQuadrant/shacl/blob/master/src/main/resources/etc/dash.ttl) (TopQuadrant)

### 3.5 SHACL Rules vs. OWL Inference: Key Differences

| Aspect | SHACL Rules | OWL Inference |
|---|---|---|
| **World assumption** | Closed-world (absence = not true) | Open-world (absence = unknown) |
| **Paradigm** | Forward-chaining rules on shapes | Logical entailment from axioms |
| **Expressiveness** | Arbitrary SPARQL patterns | Limited to OWL profile axioms |
| **Scope** | Per-shape (targeted to node types) | Global (all triples) |
| **Materialization** | Explicit (run rules, get triples) | Depends on reasoner strategy |
| **Debugging** | Traceable (which rule fired) | Less traceable (entailment chain) |
| **SemPKM fit** | Domain-specific derivations per model | Cross-cutting axiom-level entailments |

For SemPKM, the recommended approach is to use **OWL for universal entailments** (inverseOf, subClassOf, domain/range) and **SHACL rules for model-specific derivations** (completion percentages, smart suggestions, transitive closures).

---

## 4. OWL Inference Analysis

### 4.1 OWL 2 Profiles

OWL 2 defines three tractable profiles designed for different use cases:

| Profile | Reasoning Complexity | Use Case | SemPKM Fit |
|---|---|---|---|
| **OWL 2 EL** | Polynomial time | Large ontologies, biomedical | Low (overkill for PKM) |
| **OWL 2 QL** | LogSpace (SPARQL rewriting) | Query answering over large data | Medium (query-time only) |
| **OWL 2 RL** | Polynomial time (rule-based) | Business rules, RDF data | **HIGH** (forward-chaining, materialize) |

**OWL 2 RL** is the best fit for SemPKM because:
1. It supports forward-chaining materialization (new triples stored, fast query)
2. It handles the axioms already in the ontology (`owl:inverseOf`, `rdfs:domain/range`, `rdfs:subClassOf`)
3. The `owlrl` Python library implements it directly on rdflib graphs
4. Performance is linear in the size of the data for typical PKM ontologies (hundreds of axioms, thousands of data triples)

**Source:** [W3C OWL 2 Profiles](https://www.w3.org/TR/owl2-profiles/) (W3C Recommendation, 11 December 2012)
**Source:** [OWL 2 RL reasoning](https://www.w3.org/TR/owl2-profiles/#OWL_2_RL) (W3C -- Section 4.3)

### 4.2 RDF4J Inference Configuration

RDF4J supports inference through layered Sail implementations. The current SemPKM config:

```turtle
# Current: NativeStore + LuceneSail, no inference
config:sail.impl [
   config:sail.type "openrdf:LuceneSail" ;
   config:delegate [
      config:sail.type "openrdf:NativeStore" ;
   ]
]
```

To add RDFS inference, a `SchemaCachingRDFSInferencer` would be inserted between LuceneSail and NativeStore:

```turtle
# With RDFS inference:
config:sail.impl [
   config:sail.type "openrdf:LuceneSail" ;
   config:delegate [
      config:sail.type "openrdf:SchemaCachingRDFSInferencer" ;
      config:delegate [
         config:sail.type "openrdf:NativeStore" ;
      ]
   ]
]
```

**RDF4J inference options:**

| Inferencer | What it does | Overhead |
|---|---|---|
| `ForwardChainingRDFSInferencer` | Materializes all RDFS entailments on write | ~2x write cost, significant for bulk loads |
| `SchemaCachingRDFSInferencer` | Caches schema triples, computes entailments on query | Lower write overhead, higher query cost |
| Custom SPIN/SHACL rules | User-defined rules via SPIN or SHACL-AF | Depends on rule complexity |

**Important:** RDF4J's built-in inferencers handle RDFS (subClassOf, subPropertyOf, domain, range) but **not OWL constructs** like `owl:inverseOf`. For OWL-level inference in RDF4J, you need either:
- The commercial GraphDB edition (built on RDF4J with OWL 2 RL reasoner)
- Custom SPIN rules that replicate OWL semantics
- External reasoning (Python-side with `owlrl`)

**Source:** [RDF4J RDFS Inference](https://rdf4j.org/documentation/programming/rdfs-reasoning/) (Eclipse RDF4J docs)
**Source:** [RDF4J Sail Architecture](https://rdf4j.org/documentation/programming/sail/) (Eclipse RDF4J docs)
**Source:** [RDF4J Repository Configuration](https://rdf4j.org/documentation/tools/repository-configuration/) (Eclipse RDF4J docs)

### 4.3 Python-side inference with owlrl

The `owlrl` library implements OWL 2 RL and RDFS reasoning entirely in Python on rdflib graphs. This is the recommended approach for SemPKM because:

1. **No triplestore reconfiguration** -- works on rdflib graphs already in the validation pipeline
2. **OWL 2 RL support** -- handles `owl:inverseOf`, `owl:TransitiveProperty`, `owl:SymmetricProperty`, `owl:sameAs`, `rdfs:subClassOf` entailments
3. **Composable** -- can run before or after pyshacl validation
4. **Small footprint** -- pure Python, no native dependencies
5. **Already compatible** -- pyshacl can invoke owlrl internally via `inference='owlrl'`

Usage:

```python
import owlrl

# Standalone usage
g = rdflib.Graph()
g.parse("data.ttl")
g.parse("ontology.ttl")
owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
# g now contains all OWL 2 RL entailments

# Via pyshacl (integrated)
conforms, results, text = pyshacl.validate(
    data_graph, shacl_graph=shapes,
    ont_graph=ontology,
    inference='owlrl',  # runs owlrl before validation
    advanced=True,
    inplace=True,
)
# data_graph now has inferred triples + validation results
```

**What owlrl materializes from the existing basic-pkm ontology:**

| Axiom in Ontology | Entailment | Example |
|---|---|---|
| `bpkm:participatesIn owl:inverseOf bpkm:hasParticipant` | `?person bpkm:participatesIn ?project` from `?project bpkm:hasParticipant ?person` | Auto bidirectional links |
| `bpkm:hasParticipant rdfs:domain bpkm:Project` | `?x rdf:type bpkm:Project` from `?x bpkm:hasParticipant ?y` | Type assertion from property usage |
| `bpkm:hasParticipant rdfs:range bpkm:Person` | `?y rdf:type bpkm:Person` from `?x bpkm:hasParticipant ?y` | Type assertion from property usage |
| `bpkm:isAbout rdfs:range bpkm:Concept` | `?c rdf:type bpkm:Concept` from `?note bpkm:isAbout ?c` | Auto-type inference |

**Source:** [owlrl on PyPI](https://pypi.org/project/owlrl/) (Python Package Index)
**Source:** [owlrl GitHub](https://github.com/RDFLib/OWL-RL) (RDFLib project)
**Source:** [pyshacl inference parameter](https://github.com/RDFLib/pySHACL#command-line-use) (GitHub)

### 4.4 What additional axioms would be valuable

The basic-pkm ontology could be enriched with:

| Proposed Axiom | OWL Construct | Benefit |
|---|---|---|
| `bpkm:hasNote owl:inverseOf bpkm:noteOf` (new property) | `owl:inverseOf` | Notes automatically know their parent Project |
| `skos:broader owl:TransitiveProperty` | `owl:TransitiveProperty` | Concept hierarchy traversal: "ancestors of X" without recursive SPARQL |
| `skos:broader owl:inverseOf skos:narrower` | `owl:inverseOf` | Automatic narrower from broader assertions |
| `skos:related owl:SymmetricProperty` | `owl:SymmetricProperty` | Bidirectional concept relationships |
| `bpkm:Project owl:disjointWith bpkm:Person` | `owl:disjointWith` | Catch classification errors |
| `bpkm:isAbout owl:inverseOf bpkm:topicOf` (new) | `owl:inverseOf` | Concepts automatically list their Notes |

Note: `skos:broader` and `skos:narrower` already have `owl:inverseOf` defined in the SKOS specification itself ([SKOS Reference, Section 8.6.1](https://www.w3.org/TR/skos-reference/#semantic-relations)). If the SKOS ontology is loaded alongside the basic-pkm ontology, owlrl would automatically materialize narrower from broader assertions.

---

## 5. Combined Architecture: SHACL Rules + OWL Inference

### 5.1 Proposed Inference Pipeline

The recommended pipeline integrates inference into the existing write path:

```
User saves object
       |
       v
[1. Build data graph] -- current object triples
       |
       v
[2. Load ontology graph] -- all installed model ontologies
       |
       v
[3. OWL 2 RL inference] -- owlrl.DeductiveClosure on merged graph
       |                    Materializes: inverses, domain/range types,
       |                    transitive closures, symmetric properties
       v
[4. SHACL validation + rules] -- pyshacl.validate(advanced=True, inplace=True)
       |                          Validates constraints AND executes sh:rule directives
       |                          Model-contributed rules fire here
       v
[5. Extract new triples] -- diff inferred graph against original
       |
       v
[6. Store to triplestore] -- INSERT original + inferred triples
       |
       v
[7. Store validation report] -- existing ValidationService._store_report()
```

### 5.2 Where to run inference

| Approach | Pros | Cons | SemPKM Recommendation |
|---|---|---|---|
| **Python-side (owlrl + pyshacl)** | No triplestore reconfig; full OWL 2 RL; composable; model-portable | CPU cost on Python side; must pass full graph | **Phase A** (start here) |
| **RDF4J inference layer** | Query-time reasoning; no Python overhead; scales better | RDFS only (no OWL); requires repo recreation; config complexity | **Phase D** (future) |
| **Hybrid** | Best of both: OWL in Python, RDFS in triplestore | Two inference engines to maintain | **Phase C** (after validation) |

**Recommendation:** Start with Python-side inference (Phase A). At PKM scale (thousands of triples, not millions), the CPU cost of owlrl on an rdflib graph is negligible (<100ms for typical operations). This avoids any triplestore migration and keeps the inference logic portable across Mental Models.

### 5.3 Integration with existing ValidationService

The existing `ValidationService.validate()` method in `backend/app/services/validation.py` is the natural integration point. The current call:

```python
# Current (line 95-101 of validation.py)
conforms, results_graph, _results_text = await asyncio.to_thread(
    pyshacl.validate,
    data_graph,
    shacl_graph=shapes_graph,
    allow_infos=True,
    allow_warnings=True,
)
```

Would become:

```python
# Proposed: with inference enabled
conforms, results_graph, _results_text = await asyncio.to_thread(
    pyshacl.validate,
    data_graph,
    shacl_graph=shapes_graph,
    ont_graph=ontology_graph,      # NEW: pass ontology for OWL axioms
    inference='owlrl',             # NEW: run OWL 2 RL before validation
    advanced=True,                 # NEW: enable SHACL-AF rules
    inplace=True,                  # NEW: materialize inferred triples into data_graph
    allow_infos=True,
    allow_warnings=True,
)
# After this call, data_graph contains original + inferred triples
# Extract inferred triples: data_graph - original_graph
```

This requires:
1. An ontology loader (similar to the existing shapes loader) to fetch merged ontology graphs
2. The `owlrl` package added to `pyproject.toml` dependencies
3. A mechanism to extract and store only the newly-inferred triples

---

## 6. Practical Applications in SemPKM

### 6.1 Inverse Property Materialization

**What it does:** Automatically creates bidirectional links when one direction is asserted.

**Example in basic-pkm:** User adds `ProjectA bpkm:hasParticipant PersonB`. Inference materializes `PersonB bpkm:participatesIn ProjectA`. PersonB's detail page now shows ProjectA in the "Participates In" section without any additional user action.

**Implementation sketch:**
```python
# In ValidationService or a new InferenceService
from owlrl import DeductiveClosure, OWLRL_Semantics

async def infer_and_validate(self, data_graph, shapes_graph, ontology_graph):
    merged = data_graph + ontology_graph  # rdflib graph union
    DeductiveClosure(OWLRL_Semantics).expand(merged)
    # merged now contains inverse triples
    new_triples = merged - data_graph - ontology_graph
    return new_triples
```

**Already declared in ontology:** `bpkm:participatesIn owl:inverseOf bpkm:hasParticipant` -- this would work immediately with owlrl.

**Impact on existing UI:** The `PersonShape` already declares `sh:path bpkm:participatesIn` with `sh:class bpkm:Project` (line 234-239 of `models/basic-pkm/shapes/basic-pkm.jsonld`). The form already renders a "Projects" field for Person objects. Materialized inverse triples would populate this field automatically.

### 6.2 Transitive Concept Hierarchies

**What it does:** Computes the full ancestry chain for concepts linked by `skos:broader`.

**Example in basic-pkm:** If `MachineLearning skos:broader ArtificialIntelligence` and `ArtificialIntelligence skos:broader ComputerScience`, then inference produces `MachineLearning skos:broader ComputerScience` (transitive closure).

**Implementation sketch:** Declare `skos:broader` as `owl:TransitiveProperty` in the ontology:
```json
{
  "@id": "skos:broader",
  "@type": ["owl:ObjectProperty", "owl:TransitiveProperty"]
}
```
owlrl automatically computes transitive closure.

**Impact on graph view:** The graph visualization (`bpkm:view-concept-graph`) would show not just direct broader/narrower edges but the full hierarchy tree, enabling "zoom out to see the big picture" exploration. The SPARQL CONSTRUCT queries in ViewSpecs would automatically pick up transitive triples from the store.

**Source:** [SKOS Reference -- Transitive Hierarchical Relations](https://www.w3.org/TR/skos-reference/#L2422) (W3C)

### 6.3 Derived Property Computation

**What it does:** Computes new property values from existing data using SHACL rules.

**Example in basic-pkm:** A SHACL rule could derive a "project completion percentage" from the statuses of related Notes:

```turtle
bpkm:ProjectShape sh:rule [
    a sh:SPARQLRule ;
    sh:prefixes bpkm: , dcterms: ;
    sh:construct """
        CONSTRUCT { $this bpkm:completionPct ?pct }
        WHERE {
            { SELECT $this (COUNT(?done) AS ?doneCount) (COUNT(?note) AS ?totalCount)
              WHERE {
                  $this bpkm:hasNote ?note .
                  OPTIONAL { ?note bpkm:noteType "reference" . BIND(?note AS ?done) }
              }
              GROUP BY $this }
            BIND(IF(?totalCount > 0, ?doneCount * 100 / ?totalCount, 0) AS ?pct)
        }
    """ ;
] .
```

**Implementation:** Add SHACL rules to the shapes file. When `pyshacl.validate(advanced=True, inplace=True)` runs, the rule fires and adds `bpkm:completionPct` triples to the data graph.

### 6.4 Smart Relationship Suggestions

**What it does:** Uses inferred relationships to suggest new links to the user.

**Example in basic-pkm:** A Note `isAbout` Concept "Machine Learning". If "Machine Learning" `skos:broader` "Artificial Intelligence", the system could suggest linking the Note to "Artificial Intelligence" as well (or to other Notes that are about "Artificial Intelligence").

**Implementation sketch:** A SPARQL query (not inference per se, but inference-enabled):
```sparql
SELECT ?suggestedConcept ?label WHERE {
    ?note bpkm:isAbout ?concept .
    ?concept skos:broader+ ?suggestedConcept .  # Uses materialized transitive triples
    ?suggestedConcept skos:prefLabel ?label .
    FILTER NOT EXISTS { ?note bpkm:isAbout ?suggestedConcept }
}
```

With materialized transitive closure from owlrl, this query becomes a simple pattern match instead of requiring property path traversal (`skos:broader+`) at query time.

### 6.5 Consistency Checking

**What it does:** Uses OWL disjointness and cardinality axioms to detect logical inconsistencies.

**Example:** If `bpkm:Project owl:disjointWith bpkm:Person`, then asserting `?x rdf:type bpkm:Project ; rdf:type bpkm:Person` would be detected as inconsistent. This catches classification errors early.

**Implementation:** owlrl computes `owl:Nothing` membership for entities violating disjointness. A post-inference check can detect these:
```python
from rdflib import OWL
nothing_instances = list(g.subjects(RDF.type, OWL.Nothing))
if nothing_instances:
    raise ConsistencyError(f"Inconsistent entities: {nothing_instances}")
```

**Source:** [OWL 2 RL rules for disjointness](https://www.w3.org/TR/owl2-profiles/#Reasoning_in_OWL_2_RL_and_RDF_Graphs) (W3C -- Table 9)

### 6.6 Shape-driven Query Generation

**What it does:** Auto-generates SPARQL queries from SHACL shape definitions, replacing hand-written ViewSpec queries.

**Example:** The `ProjectShape` declares properties (`dcterms:title`, `bpkm:status`, `bpkm:priority`, etc.) with their `sh:path`, `sh:datatype`/`sh:class`, and `sh:order`. A query generator could produce:

```sparql
-- Auto-generated from ProjectShape
SELECT ?s ?title ?status ?priority ?startDate WHERE {
    ?s a bpkm:Project ;
       dcterms:title ?title .
    OPTIONAL { ?s bpkm:status ?status }
    OPTIONAL { ?s bpkm:priority ?priority }
    OPTIONAL { ?s schema:startDate ?startDate }
}
ORDER BY ?title
```

This is essentially what `bpkm:view-project-table` in `models/basic-pkm/views/basic-pkm.jsonld` already contains -- but written by hand. Shape-driven generation would:
1. Eliminate query duplication (shapes already declare the same property paths)
2. Keep queries in sync when shapes change
3. Reduce the model author's burden (contribute shapes, get views for free)

**Implementation:** Extend `ShapesService` with a `generate_sparql_for_shape(shape: NodeShapeForm) -> str` method that iterates over `properties`, maps `sh:datatype` to SELECT variables and `sh:class` to OPTIONAL joins. The existing `ViewSpec` system would support a `sempkm:rendererType "auto"` that delegates to shape-driven generation.

**Source:** [Generating SPARQL from SHACL](https://w3id.org/schimatos/spec) (Schimatos project -- academic research on SHACL-to-SPARQL transformation)

---

## 7. Mental Model Intelligence

### 7.1 Models as inference-aware packages

Currently, a Mental Model bundle (as defined in `manifest.yaml`) contains:
- `ontology/` -- OWL class and property declarations
- `shapes/` -- SHACL shapes for validation and form generation
- `views/` -- ViewSpec instances (SPARQL queries + renderer types)
- `seed/` -- Example data

With inference support, models could additionally contain:
- `rules/` -- SHACL rule files (sh:TripleRule, sh:SPARQLRule) that derive domain-specific knowledge

### 7.2 Manifest extension

```yaml
# Proposed manifest.yaml extension
entrypoints:
  ontology: "ontology/basic-pkm.jsonld"
  shapes: "shapes/basic-pkm.jsonld"
  views: "views/basic-pkm.jsonld"
  seed: "seed/basic-pkm.jsonld"
  rules: "rules/basic-pkm.jsonld"   # NEW: inference rules
```

The `rules` entrypoint would point to a JSON-LD file containing SHACL rules (sh:rule directives attached to NodeShapes or standalone RuleShapes). These rules would be loaded alongside shapes and passed to pyshacl with `advanced=True`.

The `ManifestSchema` in `backend/app/models/manifest.py` would need an optional `rules` field in the `entrypoints` section. The `ModelInstallService` would load rules into a named graph (`urn:sempkm:model:{id}:rules`) and the inference pipeline would merge them with shapes.

### 7.3 Example: GTD Mental Model

A "Getting Things Done" model could declare inference rules:

```json
{
    "@id": "gtd:TaskContextRule",
    "@type": "sh:SPARQLRule",
    "sh:prefixes": {"gtd": "urn:sempkm:model:gtd:"},
    "sh:construct": "CONSTRUCT { $this gtd:inferredContext ?context } WHERE { $this gtd:relatedProject ?project . ?project gtd:context ?context . FILTER NOT EXISTS { $this gtd:context ?any } }"
}
```

This rule says: if a Task is related to a Project that has a context (e.g., "@computer", "@phone"), and the Task does not have its own context, infer the Project's context onto the Task.

### 7.4 Example: Zettelkasten Mental Model

A Zettelkasten model with transitive linking:

```json
{
    "@id": "zk:TransitiveLinkRule",
    "@type": "sh:SPARQLRule",
    "sh:construct": "CONSTRUCT { $this zk:transitivelyLinkedTo ?far } WHERE { $this zk:linkedTo ?near . ?near zk:linkedTo ?far . FILTER(?far != $this) }"
}
```

This computes 2-hop link neighborhoods, enabling "notes linked to notes you linked to" discovery.

### 7.5 Trust boundary

Model-contributed rules execute inside pyshacl's SHACL-AF engine, which constrains them to:
- SHACL Triple Rules (declarative, no side effects)
- SPARQL CONSTRUCT queries (read-only graph patterns producing new triples)

Neither mechanism can execute arbitrary Python code, access the filesystem, or make network requests. The trust boundary is:

| Capability | Allowed | Mechanism |
|---|---|---|
| Read triples from the data graph | Yes | SPARQL WHERE patterns |
| Generate new triples | Yes | CONSTRUCT / sh:TripleRule |
| Modify existing triples | No | SHACL rules are additive only |
| Delete triples | No | No DELETE support in SHACL-AF |
| Execute Python code | No | pyshacl sandboxes rule execution |
| Access filesystem | No | SPARQL operates on in-memory graph |
| Make HTTP requests | No | No SERVICE clause support in pyshacl rules |

This makes model-contributed rules safe to execute without additional sandboxing. The worst a malicious rule could do is generate excessive triples (a denial-of-service via graph bloat), which can be mitigated by setting a maximum triple count threshold.

**Source:** [SHACL-AF Security Considerations](https://www.w3.org/TR/shacl-af/#security-considerations) (W3C)
**Source:** [pyshacl execution model](https://github.com/RDFLib/pySHACL/blob/master/pyshacl/rules/__init__.py) (GitHub source)

---

## 8. Implementation Roadmap

### Phase A: OWL 2 RL inference in ValidationService (LOW risk, HIGH value)

**Scope:** Add `owlrl` to dependencies, pass `ont_graph` and `inference='owlrl'` to pyshacl, materialize inferred triples on write.

**Changes:**
1. Add `owlrl>=6.0.2` to `backend/pyproject.toml`
2. Add an ontology loader to `ValidationService` (fetch from `urn:sempkm:model:{id}:ontology` named graphs, parallel to existing shapes loader)
3. Update `pyshacl.validate()` call with `ont_graph=ontology_graph`, `inference='owlrl'`, `inplace=True`
4. After validation, extract inferred triples (diff original vs. expanded graph) and store them
5. Store inferred triples in a separate named graph (`urn:sempkm:inferred`) for easy identification and re-computation

**Immediate benefits:**
- `bpkm:participatesIn` auto-materialized from `bpkm:hasParticipant` (existing `owl:inverseOf`)
- `rdfs:domain`/`rdfs:range` type assertions (implicit `rdf:type` from property usage)
- Person detail pages show linked Projects without manual inverse entry

**Estimated effort:** 1-2 plan tasks. Docker rebuild needed for new dependency.

**Risk:** Low. owlrl is a well-maintained RDFLib project (same org as pyshacl). The change is additive -- existing validation behavior is preserved.

### Phase B: SHACL rule support (MEDIUM risk, MEDIUM value)

**Scope:** Enable `advanced=True` in pyshacl, add `rules` entrypoint to manifest, allow models to contribute SHACL rules.

**Changes:**
1. Update `pyshacl.validate()` call with `advanced=True`
2. Add optional `rules` field to `ManifestSchema` entrypoints
3. Update `ModelInstallService` to load rules into `urn:sempkm:model:{id}:rules` named graph
4. Merge rules graph with shapes graph before passing to pyshacl
5. Add example SHACL rules to basic-pkm model (e.g., derive `bpkm:noteOf` inverse, compute concept ancestry)

**Benefits:**
- Models can contribute domain-specific inference logic
- Derived properties appear in views and forms
- Foundation for "intelligent" Mental Models

**Risk:** Medium. SHACL rules add complexity for model authors. Need documentation and examples. Rules could generate unexpected triples if poorly written.

### Phase C: DASH vocabulary and shape-driven queries (MEDIUM risk, HIGH value)

**Scope:** Adopt DASH vocabulary for richer UI metadata, implement shape-driven SPARQL generation.

**Changes:**
1. Add DASH vocabulary imports to shapes files
2. Extend `ShapesService._extract_property_shape()` to read DASH properties (`dash:viewer`, `dash:editor`, `dash:readOnly`, `dash:hidden`)
3. Add `PropertyShape.viewer`, `PropertyShape.editor`, `PropertyShape.readonly`, `PropertyShape.hidden` fields
4. Implement `ShapesService.generate_sparql()` to produce SELECT/CONSTRUCT queries from shape properties
5. Add `sempkm:rendererType "auto"` support to ViewSpecService

**Benefits:**
- Richer form generation (date pickers, markdown editors, autocomplete)
- Reduced manual query authoring for model developers
- Shapes become the single source of truth for both UI and queries

**Risk:** Medium. DASH is a community vocabulary, not a W3C standard. Need to evaluate which DASH properties are stable.

### Phase D: RDF4J inference layer (FUTURE, HIGH complexity)

**Scope:** Add `SchemaCachingRDFSInferencer` to RDF4J config for query-time RDFS inference, reducing Python-side inference load.

**Changes:**
1. Update `config/rdf4j/sempkm-repo.ttl` to insert inferencer between LuceneSail and NativeStore
2. Re-create the RDF4J repository (requires data migration or volume reset)
3. Adjust Python-side inference to avoid duplicating RDFS entailments already handled by RDF4J
4. Keep OWL 2 RL inference in Python (RDF4J Community Edition does not support OWL)

**Benefits:**
- Query-time inference for RDFS (subClassOf, subPropertyOf) without materialization
- Reduced write-time overhead for RDFS-level entailments
- Better scaling for larger knowledge bases

**Risk:** High. Requires triplestore migration, careful layering to avoid duplicate inference, and thorough testing of named graph behavior with inference enabled. The LuceneSail + Inferencer interaction needs validation.

---

## 9. Risks and Tradeoffs

### 9.1 Materialization Bloat

Adding inferred triples increases the total triple count. For a typical PKM with 5,000 user-asserted triples:

| Inference Level | Estimated Additional Triples | Total | Overhead |
|---|---|---|---|
| `owl:inverseOf` only | ~500 (10% of object property assertions) | 5,500 | +10% |
| Full OWL 2 RL | ~2,000 (domain/range types, inverses, transitivity) | 7,000 | +40% |
| OWL 2 RL + SHACL rules | ~3,000 (above + derived properties) | 8,000 | +60% |

At PKM scale this is negligible -- RDF4J NativeStore handles millions of triples. The LuceneSail FTS index will grow proportionally, but the inferred triples are mostly structural (type assertions, inverse links) not natural-language content, so FTS impact is minimal.

**Mitigation:** Store inferred triples in a separate named graph (`urn:sempkm:inferred`). On ontology change or rule update, drop and recompute. Use `GRAPH` clauses in SPARQL to distinguish asserted vs. inferred when needed.

### 9.2 Rule Debugging (Provenance)

When inference adds triples, users may wonder "why does this relationship exist?" Without provenance tracking, debugging is difficult.

**Mitigation strategies:**
1. **Named graph separation:** Inferred triples in `urn:sempkm:inferred` are clearly machine-generated
2. **Inference metadata:** For each inference run, store a provenance record: timestamp, which rules fired, how many triples generated
3. **UI indicator:** In the object detail view, mark inferred properties with a small icon (e.g., a chain-link or sparkle) to distinguish them from user-asserted properties
4. **Re-inference command:** Provide a "recompute inferences" action that drops and regenerates all inferred triples

### 9.3 Model Author Complexity

Writing OWL axioms and SHACL rules is harder than writing SHACL shapes for forms. The learning curve could deter model contributors.

**Mitigation:**
1. **Inference is optional:** Models work without rules (current behavior). Rules are an enhancement, not a requirement.
2. **Templates and examples:** Provide rule templates for common patterns (inverse materialization, transitive closure, derived counts)
3. **Rule validation:** pyshacl validates rule syntax before execution. Malformed rules produce clear error messages.
4. **Documentation:** Ship a "Model Author's Guide to Inference Rules" with the SHACL rules specification

### 9.4 Backward Compatibility

When inference rules change (model update), existing inferred triples may be stale or incorrect.

**Mitigation:**
1. **Re-inference on model install/update:** Drop `urn:sempkm:inferred` and recompute from scratch
2. **Versioned inference graphs:** `urn:sempkm:inferred:{model-id}:{version}` for rollback capability
3. **Incremental inference:** For per-object writes, only recompute inference for the affected object's neighborhood (optimization for Phase D)

### 9.5 Performance Considerations

| Operation | Current Cost | With OWL 2 RL | With OWL 2 RL + SHACL Rules |
|---|---|---|---|
| Single object save | ~50ms (SPARQL INSERT) | ~150ms (+owlrl on object graph) | ~200ms (+rule execution) |
| Full validation | ~200ms (pyshacl on full graph) | ~500ms (+owlrl on full graph) | ~700ms (+rules on full graph) |
| Bulk import (100 objects) | ~5s | ~15s | ~20s |

These are estimates for PKM-scale data (5,000-10,000 triples). The overhead is acceptable for a single-user application where saves are interactive (user clicks "save" and waits <1 second).

**Optimization path:** If performance becomes an issue:
1. Run inference per-object (not full graph) -- infer only the neighborhood of the changed object
2. Cache ontology and rules graphs (reload on model install/update only)
3. Move RDFS inference to RDF4J (Phase D) and keep only OWL in Python

---

## 10. Source Links

### W3C Specifications
- [SHACL Core](https://www.w3.org/TR/shacl/) -- W3C Recommendation, 20 July 2017
- [SHACL Advanced Features (SHACL-AF)](https://www.w3.org/TR/shacl-af/) -- W3C Working Group Note, 8 June 2017
- [SHACL-SPARQL](https://www.w3.org/TR/shacl/#sparql-constraints) -- Section 6 of the SHACL Core spec
- [OWL 2 Web Ontology Language Profiles](https://www.w3.org/TR/owl2-profiles/) -- W3C Recommendation, 11 December 2012
- [OWL 2 RL reasoning rules](https://www.w3.org/TR/owl2-profiles/#Reasoning_in_OWL_2_RL_and_RDF_Graphs) -- Table 4-9 of OWL 2 Profiles
- [SKOS Simple Knowledge Organization System Reference](https://www.w3.org/TR/skos-reference/) -- W3C Recommendation, 18 August 2009
- [SKOS Semantic Relations](https://www.w3.org/TR/skos-reference/#semantic-relations) -- Section 8 (broader/narrower/related semantics)

### Python Libraries
- [pyshacl on GitHub](https://github.com/RDFLib/pySHACL) -- RDFLib project, SHACL validation + SHACL-AF rules
- [pyshacl on PyPI](https://pypi.org/project/pyshacl/) -- Version history and changelog
- [pyshacl Advanced Features documentation](https://github.com/RDFLib/pySHACL#advanced-features) -- advanced=True, inference, ont_graph
- [owlrl on GitHub](https://github.com/RDFLib/OWL-RL) -- RDFLib project, OWL 2 RL + RDFS reasoning
- [owlrl on PyPI](https://pypi.org/project/owlrl/) -- Version 6.0.2+
- [rdflib documentation](https://rdflib.readthedocs.io/) -- Core RDF library for Python

### RDF4J / Triplestore
- [RDF4J RDFS Reasoning](https://rdf4j.org/documentation/programming/rdfs-reasoning/) -- Eclipse Foundation docs
- [RDF4J Sail Architecture](https://rdf4j.org/documentation/programming/sail/) -- Layered sail implementations
- [RDF4J Repository Configuration](https://rdf4j.org/documentation/tools/repository-configuration/) -- TTL config for inferencers
- [RDF4J SchemaCachingRDFSInferencer](https://rdf4j.org/javadoc/latest/org/eclipse/rdf4j/sail/inferencer/fc/SchemaCachingRDFSInferencer.html) -- JavaDoc

### DASH and Extended SHACL
- [DASH Data Shapes Vocabulary](https://datashapes.org/dash.html) -- datashapes.org (TopBraid)
- [DASH specification on GitHub](https://github.com/TopQuadrant/shacl/blob/master/src/main/resources/etc/dash.ttl) -- TopQuadrant
- [TopBraid SHACL API](https://www.topquadrant.com/technology/shacl/) -- TopQuadrant commercial product (patterns are informative)

### Academic / Community
- [Schimatos: SHACL-to-SPARQL transformation](https://w3id.org/schimatos/spec) -- Academic research on generating SPARQL from SHACL shapes
- [SHACL Playground](https://shacl-playground.zazuko.com/) -- Interactive SHACL validation testing (Zazuko)
- [Validating and Describing Linked Data](https://book.validatingrdf.com/) -- Book by Jose Emilio Labra Gayo et al. (comprehensive SHACL + ShEx reference)

### SemPKM Source Files Referenced
- `backend/app/services/shapes.py` -- ShapesService: SHACL shape extraction for form metadata
- `backend/app/services/validation.py` -- ValidationService: pyshacl validation orchestration
- `models/basic-pkm/ontology/basic-pkm.jsonld` -- OWL ontology with inverseOf, domain/range
- `models/basic-pkm/shapes/basic-pkm.jsonld` -- SHACL NodeShapes for 4 types, ~40 property shapes
- `models/basic-pkm/views/basic-pkm.jsonld` -- ViewSpec instances with hand-written SPARQL
- `models/basic-pkm/manifest.yaml` -- Model manifest with entrypoints (no rules entrypoint yet)
- `config/rdf4j/sempkm-repo.ttl` -- RDF4J repo config: NativeStore + LuceneSail, no inferencer
- `backend/pyproject.toml` -- Dependencies: rdflib>=7.5.0, pyshacl>=0.31.0 (no owlrl yet)
